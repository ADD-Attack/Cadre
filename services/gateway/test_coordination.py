"""Tests for the gateway coordination routes (wishlist #15 + #18).

POST/GET /v1/hands/claim + /release (advisory claim, FIFO queue,
reservation grace, lazy TTL expiry) and POST /v1/act/queued (yield-409
receipts with a synchronous retry pump).

Runs anywhere with the gateway's deps installed — no live hands needed:
the act forward is stubbed at the module boundary (_forward_act).

    python3 test_coordination.py

Covers: claim grant / conflict / queue / release rules / reservation
grace / TTL expiry / /v1/info hands_claim; queued act passthrough,
held -> applied, held -> refused-yielded past the deadline, held ->
failed, unknown receipt 404, and that a receipt never carries payload
values (a typed secret appears nowhere in its JSON).
"""

import os
import sys
import time

os.environ.setdefault("RELAY_GATEWAY_TOKEN", "test-token")
os.environ.setdefault("HANDS_SECRET", "test-secret")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app as gateway  # noqa: E402

TOKEN = {"X-Relay-Token": "test-token"}
YIELD_409 = (409, {"ok": False, "error": "hands yielded: user active on the desktop"})


class ActStub:
    """Scripted _forward_act: pops responses, then repeats the last one."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, op, payload):
        self.calls.append((op, dict(payload)))
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]


def run():
    client = gateway.app.test_client()
    failures = []

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    def claim(holder, **kw):
        body = {"holder": holder, "purpose": kw.pop("purpose", "test driving")}
        body.update(kw)
        return client.post("/v1/hands/claim", json=body, headers=TOKEN)

    def release(holder, **kw):
        body = {"holder": holder}
        body.update(kw)
        return client.post("/v1/hands/release", json=body, headers=TOKEN)

    def claim_state():
        return client.get("/v1/hands/claim", headers=TOKEN).get_json()

    original_forward = gateway._forward_act
    original_reachability = gateway._reachability
    gateway._reachability = lambda: (True, True, None)  # /v1/info without backends

    # ------------------------------------------------------------------
    # Claim: grant, conflict, queue, release rules, reservation grace.
    # ------------------------------------------------------------------
    gateway._reset_coordination_state()

    r = client.post("/v1/hands/claim", json={"holder": "alpha"}, headers={})
    check("claim endpoint requires the gateway token", r.status_code == 401)

    r = claim("alpha")
    body = r.get_json()
    check("free desktop grants the claim",
          r.status_code == 200 and body["ok"] and body["granted"]
          and body["claim"]["holder"] == "alpha")
    check("default TTL is 900s",
          abs(body["claim"]["expires_at"] - body["claim"]["since"] - 900) < 1)

    r = claim("alpha", purpose="still me")
    check("same holder re-claim refreshes (granted)",
          r.status_code == 200 and r.get_json()["granted"])

    r = claim("beta")
    check("second holder without queue gets 409 + current claim",
          r.status_code == 409 and r.get_json()["claim"]["holder"] == "alpha")

    r = claim("beta", queue=True)
    body = r.get_json()
    check("second holder with queue=true is queued at position 1",
          r.status_code == 200 and body["granted"] is False
          and body["queued"] and body["position"] == 1
          and body["claim"]["holder"] == "alpha")
    r = claim("beta", queue=True)
    check("queueing twice dedupes to the same position",
          r.get_json()["position"] == 1 and len(claim_state()["queue"]) == 1)

    r = release("gamma")
    check("release by a stranger is 403", r.status_code == 403)
    check("claim survives a stranger's release attempt",
          claim_state()["claim"]["holder"] == "alpha")

    r = release("alpha")
    state = claim_state()
    check("release by the holder frees the desktop",
          r.status_code == 200 and r.get_json()["released"]
          and state["claim"] is None)
    check("queue head is reserved after the release",
          state["reserved_for"] == "beta" and len(state["queue"]) == 1)

    r = claim("gamma")
    check("non-reserved holder is still blocked during the grace window",
          r.status_code == 409 and claim_state()["claim"] is None)

    r = claim("beta")
    state = claim_state()
    check("queued holder claiming within grace is granted",
          r.status_code == 200 and r.get_json()["granted"]
          and r.get_json()["claim"]["holder"] == "beta")
    check("grant dequeues the holder and clears the reservation",
          state["queue"] == [] and state["reserved_for"] is None)

    # A queued holder can cancel its queue entry.
    claim("delta", queue=True)
    claim("echo", queue=True)
    r = release("delta", cancel_queue=True)
    state = claim_state()
    check("cancel_queue removes only that holder's entry",
          r.status_code == 200 and r.get_json()["cancelled_queue"]
          and [e["holder"] for e in state["queue"]] == ["echo"]
          and state["claim"]["holder"] == "beta")
    release("beta")

    # ------------------------------------------------------------------
    # Claim: TTL expiry frees the desktop (lazy, deterministic).
    # ------------------------------------------------------------------
    gateway._reset_coordination_state()
    claim("alpha")
    claim("beta", queue=True)
    now = time.time()
    with gateway._claim_lock:
        gateway._claim = {
            "holder": "alpha",
            "purpose": "stale",
            "since": now - 1000,
            "expires_at": now - 1,
        }
    state = claim_state()
    check("an expired claim reads as absent",
          state["claim"] is None and state["reserved_for"] == "beta")
    r = claim("gamma")
    check("expiry-promoted reservation blocks a third holder",
          r.status_code == 409)
    r = claim("beta")
    check("expiry-promoted queue head can claim within grace",
          r.status_code == 200 and r.get_json()["granted"])

    gateway._reset_coordination_state()
    claim("alpha")
    with gateway._claim_lock:
        gateway._claim = {
            "holder": "alpha",
            "purpose": "stale",
            "since": now - 1000,
            "expires_at": now - 1,
        }
    r = claim("beta")
    check("expired claim with an empty queue frees the desktop for anyone",
          r.status_code == 200 and r.get_json()["claim"]["holder"] == "beta")

    r = release("alpha")
    check("releasing an already-taken-over claim is 403 for the stale holder",
          r.status_code == 403)
    r = client.get("/v1/info", headers=TOKEN)
    check("/v1/info exposes hands_claim",
          r.get_json()["hands_claim"]["holder"] == "beta")
    with gateway._claim_lock:
        gateway._claim = {
            "holder": "beta",
            "purpose": "stale",
            "since": now - 1000,
            "expires_at": now - 1,
        }
    r = release("beta")
    check("releasing one's own expired claim is an ok no-op",
          r.status_code == 200 and r.get_json()["ok"])

    # TTL clamp: a sub-minimum ttl lands on the 30s floor.
    gateway._reset_coordination_state()
    r = claim("alpha", ttl_seconds=1)
    body = r.get_json()
    check("ttl_seconds is clamped to the 30s floor",
          abs(body["claim"]["expires_at"] - body["claim"]["since"] - 30) < 1)

    # ------------------------------------------------------------------
    # Queued act.
    # ------------------------------------------------------------------
    gateway._reset_coordination_state()

    # Plain /v1/act still routes through the shared forward, untouched.
    gateway._forward_act = ActStub([(200, {"ok": True, "plain": True})])
    r = client.post("/v1/act", json={"op": "move", "x": 5, "y": 6}, headers=TOKEN)
    check("plain /v1/act is unchanged (200 passthrough, no receipt)",
          r.status_code == 200 and r.get_json() == {"ok": True, "plain": True}
          and client.get("/v1/act/queued", headers=TOKEN).get_json()["receipts"] == [])

    # (a) Immediate non-409 -> passthrough + receipt id, and a settled
    # "applied" receipt is filed (R4, F4: every queued act is
    # reconcilable afterwards, not only yields).
    gateway._forward_act = ActStub([(200, {"ok": True, "moved": True})])
    r = client.post("/v1/act/queued", json={"op": "move", "x": 1, "y": 2}, headers=TOKEN)
    body = r.get_json()
    direct_id = body.get("id")
    check("queued act passes an immediate 200 through with its receipt id",
          r.status_code == 200 and body.get("ok") is True
          and body.get("moved") is True
          and isinstance(direct_id, str) and len(direct_id) == 32)
    r = client.get("/v1/act/queued", headers=TOKEN)
    receipts = r.get_json()["receipts"]
    check("passthrough files a settled applied receipt",
          len(receipts) == 1 and receipts[0]["id"] == direct_id
          and receipts[0]["state"] == "applied")

    # A 409 that is NOT a yield is also passed through — with a
    # settled "failed" receipt filed (R4, F4).
    gateway._forward_act = ActStub([(409, {"ok": False, "error": "some other conflict"})])
    r = client.post("/v1/act/queued", json={"op": "click", "x": 1, "y": 2}, headers=TOKEN)
    conflict_id = r.get_json().get("id")
    check("non-yield 409 passes through with a receipt id",
          r.status_code == 409 and isinstance(conflict_id, str))
    receipts = client.get("/v1/act/queued", headers=TOKEN).get_json()["receipts"]
    check("non-yield 409 files a settled failed receipt",
          receipts[0]["id"] == conflict_id and receipts[0]["state"] == "failed")

    # (b) Yield-409 then success: 202 held, pump -> applied.
    typed_secret = "typed-text-that-must-not-leak"
    gateway._forward_act = ActStub([YIELD_409, (200, {"ok": True, "typed": True})])
    r = client.post(
        "/v1/act/queued",
        json={"op": "type", "text": typed_secret, "hold_seconds": 30},
        headers=TOKEN,
    )
    body = r.get_json()
    check("yield-409 answers 202 held with a receipt id",
          r.status_code == 202 and body["ok"] and body["queued"]
          and body["state"] == "held" and len(body["id"]) == 32)
    receipt_id = body["id"]
    with gateway._receipts_lock:
        receipt = gateway._receipts[receipt_id]
    check("receipt records op + sorted param key names",
          receipt["op"] == "type" and receipt["param_keys"] == ["text"])
    gateway._pump_receipt(receipt, time.time())
    check("pump settles held -> applied on the first non-409",
          receipt["state"] == "applied" and receipt["hands_status"] == 200
          and receipt["result"] == {"ok": True, "typed": True})

    # (e) The typed value appears NOWHERE in the receipt JSON.
    r = client.get(f"/v1/act/queued/{receipt_id}", headers=TOKEN)
    check("GET receipt returns it as JSON",
          r.status_code == 200 and r.get_json()["id"] == receipt_id
          and r.get_json()["state"] == "applied")
    check("typed payload value appears nowhere in the receipt JSON",
          typed_secret not in r.get_data(as_text=True))
    with gateway._receipts_lock:
        stored = repr(gateway._receipts) + repr(gateway._public_receipt(receipt))
        pending_left = receipt_id in gateway._pending_payloads
    check("typed payload value is not in the stored receipt either",
          typed_secret not in stored)
    check("pending payload is dropped once the receipt settles",
          pending_left is False)

    # (c) Always yielding: pump past the deadline -> refused-yielded.
    gateway._forward_act = ActStub([YIELD_409])
    r = client.post(
        "/v1/act/queued",
        json={"op": "click", "x": 3, "y": 4, "hold_seconds": 30},
        headers=TOKEN,
    )
    receipt_id_2 = r.get_json()["id"]
    with gateway._receipts_lock:
        receipt2 = gateway._receipts[receipt_id_2]
    gateway._pump_receipt(receipt2, time.time())
    check("pump before the deadline leaves the receipt held",
          receipt2["state"] == "held")
    gateway._pump_receipt(receipt2, receipt2["deadline"] + 60)
    check("pump past the deadline with a still-409 settles refused-yielded",
          receipt2["state"] == "refused-yielded"
          and receipt2["hands_status"] == 409)

    # Failed: a retry that finds the hands unreachable settles failed.
    gateway._forward_act = ActStub(
        [YIELD_409, (502, {"ok": False, "error": "hands unreachable: boom"})]
    )
    r = client.post(
        "/v1/act/queued",
        json={"op": "key", "key": "enter", "hold_seconds": 30},
        headers=TOKEN,
    )
    receipt_id_3 = r.get_json()["id"]
    with gateway._receipts_lock:
        receipt3 = gateway._receipts[receipt_id_3]
    gateway._pump_receipt(receipt3, time.time())
    check("pump settles held -> failed when the hands are unreachable",
          receipt3["state"] == "failed" and receipt3["hands_status"] == 502)

    # (d) Unknown receipt id -> 404 with state expired.
    r = client.get("/v1/act/queued/deadbeefdeadbeef", headers=TOKEN)
    body = r.get_json()
    check("unknown receipt id is 404 with state expired",
          r.status_code == 404 and body["ok"] is False
          and body["state"] == "expired")

    # Receipt list: newest first, summary fields only.
    r = client.get("/v1/act/queued", headers=TOKEN)
    receipts = r.get_json()["receipts"]
    check("receipt list is newest first with summary fields only",
          [x["id"] for x in receipts] == [receipt_id_3, receipt_id_2, receipt_id, conflict_id, direct_id]
          and all(set(x) == {"id", "op", "state", "submitted_at"} for x in receipts))

    gateway._forward_act = original_forward
    gateway._reachability = original_reachability
    gateway._reset_coordination_state()

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
