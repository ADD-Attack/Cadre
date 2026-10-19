"""Tests for the V3-R1 receipt-eviction fix (Grok review High #4).

The bug: _store_receipt evicts the oldest receipt past RECEIPT_MAX and
drops its payload — but the retry loop may already hold a reference to
the evicted dict, and _pump_receipt would forward the op with an EMPTY
body (an empty break fires a real Ctrl+C at the desktop; an empty
scroll scrolls by the hands' defaults) while the caller's poll reads
404 "expired". The fix: eviction marks the receipt "expired", and the
pump never forwards an op whose payload is gone.

    python3 test_receipt_eviction.py
"""

import os
import sys
import time

os.environ.setdefault("RELAY_GATEWAY_TOKEN", "test-token")
os.environ.setdefault("HANDS_SECRET", "test-secret")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app as gateway  # noqa: E402


class ActStub:
    """Counts forwards; replies with a scripted (status, result)."""

    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def __call__(self, op, payload):
        self.calls.append((op, payload))
        return self.reply


def make_receipt(rid, op="break"):
    now = time.time()
    return {
        "id": rid,
        "op": op,
        "state": "held",
        "created_at": now,
        "updated_at": now,
        "deadline": now + 3600,
    }


def run():
    failures = []

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    original_forward = gateway._forward_act
    try:
        # --- eviction marks the receipt and the pump never fires it ---
        gateway._reset_coordination_state()
        stub = ActStub((200, {"ok": True}))
        gateway._forward_act = stub
        first = make_receipt("r-first")
        gateway._store_receipt(first, {"confirmed": True})
        for i in range(gateway.RECEIPT_MAX):
            gateway._store_receipt(make_receipt(f"r-{i}"), {"n": i})
        check("evicted receipt is marked expired", first["state"] == "expired")
        check("evicted receipt is out of the registry",
              "r-first" not in gateway._receipts)
        gateway._pump_receipt(first, time.time())
        check("pump performs NO forward for an evicted receipt",
              stub.calls == [])

        # --- a held receipt whose payload vanished settles, never fires ---
        gateway._reset_coordination_state()
        stub = ActStub((200, {"ok": True}))
        gateway._forward_act = stub
        orphan = make_receipt("r-orphan", op="scroll")
        gateway._store_receipt(orphan, {"clicks": -3})
        gateway._pending_payloads.pop("r-orphan", None)
        gateway._pump_receipt(orphan, time.time())
        check("payload-less held receipt settles as expired",
              orphan["state"] == "expired")
        check("payload-less held receipt is never forwarded",
              stub.calls == [])

        # --- control: a normal held receipt still forwards and applies ---
        gateway._reset_coordination_state()
        stub = ActStub((200, {"ok": True}))
        gateway._forward_act = stub
        normal = make_receipt("r-normal", op="scroll")
        gateway._store_receipt(normal, {"clicks": -3})
        gateway._pump_receipt(normal, time.time())
        check("normal held receipt forwards exactly once with its payload",
              stub.calls == [("scroll", {"clicks": -3})])
        check("normal held receipt settles applied",
              normal["state"] == "applied")
    finally:
        gateway._forward_act = original_forward
        gateway._reset_coordination_state()

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
