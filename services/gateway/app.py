"""Muse Relay v2 — gateway service.

The agent-facing API. Owns authentication (per-deployment token, constant-time
compare, failed-guess lockout) and routes control requests to the Windows
hands process and parse requests to the parser service.

The hands link: the gateway holds the hands base URL (HANDS_URL) and the
hands' current session secret (HANDS_SECRET — the packaged hands app
generates a fresh secret every launch and shows it in its window; copy it
into the gateway's environment). Agent calls are translated:

  GET  /v1/screen            -> GET  {HANDS_URL}/screenshot  (PNG bytes back)
  GET  /v1/screen/hash       -> screenshot hash (see screen_hash below)
  POST /v1/act {"op": ...}   -> POST {HANDS_URL}/<op>        (move/click/
                                                              type/key/scroll)
"""

import hashlib
import hmac
import os
import threading
import time
import uuid
from io import BytesIO

import requests
from flask import Flask, Response, jsonify, request

TOKEN = os.environ.get("RELAY_GATEWAY_TOKEN", "")
HANDS_URL = os.environ.get("HANDS_URL", "http://host.docker.internal:5000").rstrip("/")
HANDS_SECRET = os.environ.get("HANDS_SECRET", "")
PARSER_URL = os.environ.get("PARSER_URL", "http://parser:5011").rstrip("/")

HANDS_OPS = {"move", "click", "type", "key", "scroll"}
HANDS_TIMEOUT = 30

# Screen hashing (wishlist #14): the bottom strip of the frame is the
# taskbar — clock, tray icons, notification churn — and must not change
# the hash. 80px matches the watcher convention the live walkthrough
# loop already uses on the client side.
DEFAULT_MASK_BOTTOM = 80
# Stable mode samples two frames this far apart and keeps only the
# pixels that agree, so a blinking caret or spinner phase cannot flip
# the hash (wishlist #14 addendum, 2026-10-19).
STABLE_SAMPLE_GAP = 0.65

MAX_FAILS = 10
FAIL_WINDOW = 600
LOCKOUT_SECONDS = 300

_fail_lock = threading.Lock()
_fail_times: list = []
_lockout_until = 0.0

_probe_lock = threading.Lock()
_probe_cache = {"hands": None, "parser": None, "at": 0.0}

# ---------------------------------------------------------------------------
# Hands claim coordination (wishlist #15).
#
# Advisory only: sessions read the claim before driving the desktop, but
# /v1/act is deliberately NOT gated on it — the claim coordinates polite
# agents, it is not an access control (the gateway token is that).
# State is in-memory and lock-guarded, with LAZY expiry: an expired claim
# is treated as absent the next time anything looks, via _current_claim.
# ---------------------------------------------------------------------------
CLAIM_TTL_DEFAULT = 900
CLAIM_TTL_MIN = 30
CLAIM_TTL_MAX = 3600
RESERVATION_GRACE = 30  # seconds the queue head alone may claim after a free-up

_claim_lock = threading.RLock()
_claim = None  # {"holder", "purpose", "since", "expires_at"} or None
_claim_queue = []  # FIFO of {"holder", "purpose", "enqueued_at"}
_reserved_for = None  # queue head holder with an exclusive claim window
_reserved_until = 0.0


def _clamp_number(value, default, lo, hi):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(default)
    return max(float(lo), min(float(hi), number))


def _active_reservation_locked(now):
    """Reserved holder if the grace window is still open, else None."""
    global _reserved_for, _reserved_until
    if _reserved_for is None:
        return None
    if now < _reserved_until:
        return _reserved_for
    _reserved_for = None
    _reserved_until = 0.0
    return None


def _reserve_head_locked(now):
    """Give the queue head an exclusive claim window, if none is active."""
    global _reserved_for, _reserved_until
    if _claim_queue and _reserved_for is None:
        _reserved_for = _claim_queue[0]["holder"]
        _reserved_until = now + RESERVATION_GRACE


def _current_claim_locked(now):
    global _claim
    if _claim is not None and now >= float(_claim.get("expires_at", 0.0)):
        # Lazy expiry: the claim is gone, and the queue head (if any)
        # earns a reservation from this moment of discovery.
        _claim = None
        _reserve_head_locked(now)
    return _claim


def _current_claim(now=None):
    """Copy of the live claim, or None if free / expired."""
    if now is None:
        now = time.time()
    with _claim_lock:
        current = _current_claim_locked(now)
        return dict(current) if current is not None else None


def _claim_snapshot(now=None):
    """(claim copy or None, queue copies, reserved holder or None)."""
    if now is None:
        now = time.time()
    with _claim_lock:
        current = _current_claim_locked(now)
        reserved = _active_reservation_locked(now)
        return (
            dict(current) if current is not None else None,
            [dict(entry) for entry in _claim_queue],
            reserved,
        )


def _enqueue_locked(holder, purpose, now):
    """Append to the FIFO queue (deduped by holder); returns 1-based position."""
    for idx, entry in enumerate(_claim_queue):
        if entry["holder"] == holder:
            return idx + 1
    _claim_queue.append({"holder": holder, "purpose": purpose, "enqueued_at": now})
    return len(_claim_queue)


def _dequeue_locked(holder):
    for idx, entry in enumerate(_claim_queue):
        if entry["holder"] == holder:
            del _claim_queue[idx]
            return True
    return False


def _reset_coordination_state():
    """Clear claim + receipt state. Test hook / internal use only."""
    global _claim, _reserved_for, _reserved_until
    with _claim_lock:
        _claim = None
        _claim_queue.clear()
        _reserved_for = None
        _reserved_until = 0.0
    with _receipts_lock:
        _receipts.clear()
        _pending_payloads.clear()


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8_000_000  # screenshots travel as responses


def _locked_out() -> bool:
    return time.monotonic() < _lockout_until


def _record_failure() -> None:
    global _lockout_until
    now = time.monotonic()
    with _fail_lock:
        _fail_times[:] = [t for t in _fail_times if now - t < FAIL_WINDOW]
        _fail_times.append(now)
        if len(_fail_times) >= MAX_FAILS:
            _lockout_until = now + LOCKOUT_SECONDS
            _fail_times.clear()
            app.logger.warning("LOCKOUT: too many bad tokens")


@app.before_request
def gate():
    if request.path == "/health":
        return
    if _locked_out():
        return jsonify({"ok": False, "error": "locked out"}), 429
    provided = request.headers.get("X-Relay-Token") or ""
    if not TOKEN or not hmac.compare_digest(provided, TOKEN):
        _record_failure()
        return jsonify({"ok": False, "error": "bad token"}), 401


@app.after_request
def noindex(resp):
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


def _hands_headers():
    return {"X-Secret": HANDS_SECRET}


def _probe(url, headers=None):
    try:
        r = requests.get(url, headers=headers or {}, timeout=2)
        return r.status_code == 200
    except requests.RequestException:
        return False


def _reachability():
    """Cached (5s) reachability of the two backends, for /v1/info."""
    now = time.monotonic()
    with _probe_lock:
        if now - _probe_cache["at"] < 5 and _probe_cache["hands"] is not None:
            return _probe_cache["hands"], _probe_cache["parser"]
    hands = _probe(f"{HANDS_URL}/health", _hands_headers())
    parser = _probe(f"{PARSER_URL}/health")
    with _probe_lock:
        _probe_cache.update({"hands": hands, "parser": parser, "at": now})
    return hands, parser


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "gateway"})


@app.get("/v1/info")
def info():
    hands_ok, parser_ok = _reachability()
    return jsonify(
        {
            "ok": True,
            "hands_url": HANDS_URL,
            "hands_secret_configured": bool(HANDS_SECRET),
            "hands_reachable": hands_ok,
            "parser_url": PARSER_URL,
            "parser_reachable": parser_ok,
            "hands_claim": _current_claim(),
        }
    )


@app.get("/v1/hands/claim")
def hands_claim_status():
    claim, queue, reserved = _claim_snapshot()
    return jsonify({"ok": True, "claim": claim, "queue": queue, "reserved_for": reserved})


@app.post("/v1/hands/claim")
def hands_claim():
    global _claim, _reserved_for, _reserved_until
    body = request.get_json(force=True, silent=True) or {}
    holder = str(body.get("holder") or "").strip()
    if not holder:
        return jsonify({"ok": False, "error": "holder is required"}), 400
    purpose = str(body.get("purpose") or "")
    ttl = _clamp_number(
        body.get("ttl_seconds", CLAIM_TTL_DEFAULT),
        CLAIM_TTL_DEFAULT,
        CLAIM_TTL_MIN,
        CLAIM_TTL_MAX,
    )
    want_queue = bool(body.get("queue"))
    now = time.time()
    with _claim_lock:
        current = _current_claim_locked(now)
        if current is not None and current["holder"] == holder:
            # Same holder re-claiming refreshes the lease.
            current["purpose"] = purpose or current["purpose"]
            current["expires_at"] = now + ttl
            return jsonify({"ok": True, "granted": True, "claim": dict(current)})
        if current is not None:
            if want_queue:
                position = _enqueue_locked(holder, purpose, now)
                return jsonify(
                    {
                        "ok": True,
                        "granted": False,
                        "queued": True,
                        "position": position,
                        "claim": dict(current),
                    }
                )
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": f"hands already claimed by {current['holder']!r}",
                        "claim": dict(current),
                    }
                ),
                409,
            )
        # Desktop is free. An active reservation (queue head's grace
        # window after a release/expiry) blocks everyone else.
        reserved = _active_reservation_locked(now)
        if reserved is not None and reserved != holder:
            if want_queue:
                position = _enqueue_locked(holder, purpose, now)
                return jsonify(
                    {
                        "ok": True,
                        "granted": False,
                        "queued": True,
                        "position": position,
                        "claim": None,
                        "reserved_for": reserved,
                    }
                )
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": f"hands reserved for {reserved!r} (queue head grace window)",
                        "claim": None,
                        "reserved_for": reserved,
                    }
                ),
                409,
            )
        if reserved == holder:
            _reserved_for = None
            _reserved_until = 0.0
            _dequeue_locked(holder)
        elif _claim_queue and _claim_queue[0]["holder"] == holder:
            _dequeue_locked(holder)
        elif _claim_queue:
            # A queue outlived its reservation window: the claim is a
            # free-for-all again, but a queued caller keeps no priority
            # it did not use — drop its stale entry if it jumps in.
            _dequeue_locked(holder)
        _claim = {
            "holder": holder,
            "purpose": purpose,
            "since": now,
            "expires_at": now + ttl,
        }
        return jsonify({"ok": True, "granted": True, "claim": dict(_claim)})


@app.post("/v1/hands/release")
def hands_release():
    global _claim, _reserved_for, _reserved_until
    body = request.get_json(force=True, silent=True) or {}
    holder = str(body.get("holder") or "").strip()
    if not holder:
        return jsonify({"ok": False, "error": "holder is required"}), 400
    now = time.time()
    with _claim_lock:
        if body.get("cancel_queue"):
            removed = _dequeue_locked(holder)
            if removed and _reserved_for == holder:
                _reserved_for = None
                _reserved_until = 0.0
                if _current_claim_locked(now) is None:
                    _reserve_head_locked(now)
            claim, queue, reserved = _claim_snapshot(now)
            return jsonify(
                {
                    "ok": True,
                    "cancelled_queue": removed,
                    "claim": claim,
                    "queue": queue,
                    "reserved_for": reserved,
                }
            )
        current = _current_claim_locked(now)
        if current is None:
            # Already expired (or never held): releasing is a no-op.
            return jsonify({"ok": True, "released": False, "claim": None})
        if current["holder"] != holder:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "only the current holder can release the claim",
                        "claim": dict(current),
                    }
                ),
                403,
            )
        _claim = None
        _reserve_head_locked(now)
        return jsonify(
            {
                "ok": True,
                "released": True,
                "claim": None,
                "reserved_for": _reserved_for,
            }
        )


@app.post("/v1/parse")
def parse():
    """Forward a screenshot (JSON {"image_b64": ...}) to the parser service."""
    try:
        r = requests.post(f"{PARSER_URL}/parse", json=request.get_json(force=True), timeout=120)
        return jsonify(r.json()), r.status_code
    except requests.RequestException as exc:
        return jsonify({"ok": False, "error": f"parser unreachable: {exc}"}), 502


def _fetch_screenshot():
    """One screenshot from the hands.

    Returns (png_bytes, content_type, None) on success, or
    (None, None, error_response) with the same failures /v1/screen has
    always surfaced.
    """
    if not HANDS_SECRET:
        return None, None, (
            jsonify({"ok": False, "error": "HANDS_SECRET not configured on gateway"}),
            503,
        )
    try:
        r = requests.get(
            f"{HANDS_URL}/screenshot", headers=_hands_headers(), timeout=HANDS_TIMEOUT
        )
    except requests.RequestException as exc:
        return None, None, (jsonify({"ok": False, "error": f"hands unreachable: {exc}"}), 502)
    if r.status_code == 401:
        return None, None, (
            jsonify(
                {
                    "ok": False,
                    "error": "hands rejected the gateway's secret — HANDS_SECRET does not match the hands app's current session secret",
                }
            ),
            502,
        )
    if r.status_code != 200:
        return None, None, (
            jsonify({"ok": False, "error": f"hands returned {r.status_code}"}),
            502,
        )
    return r.content, r.headers.get("Content-Type", "image/png"), None


class _HashUnavailable(Exception):
    """Pillow is not installed on the gateway, so frames cannot be decoded."""


def _decode_masked(png_bytes, mask_bottom):
    """PNG bytes -> RGB image with the bottom mask_bottom rows removed."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise _HashUnavailable() from exc
    img = Image.open(BytesIO(png_bytes)).convert("RGB")
    mask = max(0, min(int(mask_bottom), img.height - 1))
    if mask:
        img = img.crop((0, 0, img.width, img.height - mask))
    return img


def _frame_hash(png_a, png_b, mask_bottom):
    """SHA-256 of a screenshot's masked pixels.

    With png_b given (stable mode), the two frames are composited first
    with a per-pixel minimum (ImageChops.darker). The minimum is
    symmetric, so the result does not depend on which sample caught a
    blink's bright phase — and a bright transient on a darker ground
    (a terminal caret) drops out entirely, leaving the untouched
    frame. Only persistent content moves the hash.
    Returns (hex_digest, width, height) of the masked frame.
    """
    img_a = _decode_masked(png_a, mask_bottom)
    if png_b is not None:
        from PIL import ImageChops

        img_b = _decode_masked(png_b, mask_bottom)
        if img_b.size == img_a.size:
            img_a = ImageChops.darker(img_a, img_b)
    return hashlib.sha256(img_a.tobytes()).hexdigest(), img_a.width, img_a.height


@app.get("/v1/screen")
def screen():
    """Current screenshot from the hands, proxied as PNG bytes.

    Carries an ETag (the masked-frame hash, as in /v1/screen/hash) when
    the gateway can decode images; a matching If-None-Match gets a 304
    so pollers can skip re-downloading unchanged frames.
    """
    png, content_type, err = _fetch_screenshot()
    if err is not None:
        return err
    resp = Response(png, content_type=content_type)
    try:
        digest, _, _ = _frame_hash(png, None, DEFAULT_MASK_BOTTOM)
    except _HashUnavailable:
        return resp
    etag = f'"{digest}"'
    resp.headers["ETag"] = etag
    inm = (request.headers.get("If-None-Match") or "").strip()
    if inm and inm.strip('"') == digest:
        resp.status_code = 304
        resp.set_data(b"")
    return resp


@app.get("/v1/screen/hash")
def screen_hash():
    """Hash of the current screenshot, without moving the PNG.

    A watcher polls this (tiny JSON) instead of the full frame and only
    fetches /v1/screen when the hash changes. The bottom mask_bottom px
    (default 80, the taskbar) are excluded. With ?stable=1 the gateway
    samples two frames ~0.65s apart and hashes only the pixels that
    agree, so a blinking caret cannot flip the result.
    """
    stable = (request.args.get("stable") or "").lower() in ("1", "true", "yes")
    try:
        mask_bottom = int(request.args.get("mask_bottom", DEFAULT_MASK_BOTTOM))
    except ValueError:
        return jsonify({"ok": False, "error": "mask_bottom must be an integer"}), 400
    mask_bottom = max(0, min(mask_bottom, 2000))

    png_a, _, err = _fetch_screenshot()
    if err is not None:
        return err
    png_b = None
    if stable:
        time.sleep(STABLE_SAMPLE_GAP)
        png_b, _, err = _fetch_screenshot()
        if err is not None:
            return err
    try:
        digest, width, height = _frame_hash(png_a, png_b, mask_bottom)
    except _HashUnavailable:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "image decoding unavailable on gateway (pillow not installed)",
                }
            ),
            501,
        )
    return jsonify(
        {
            "ok": True,
            "hash": digest,
            "stable": stable,
            "mask_bottom": mask_bottom,
            "width": width,
            "height": height,
        }
    )


# ---------------------------------------------------------------------------
# Queued act (wishlist #18): yielded-input accounting.
#
# The hands answer 409 when the desktop's owner is actively using it and
# an act yields. /v1/act surfaces that as-is; /v1/act/queued instead
# files a receipt and retries until a hold deadline, so the caller can
# account for the input later instead of guessing whether it landed.
#
# Privacy: a receipt records the op and the payload's key NAMES only —
# never payload values (typed text may be sensitive). The payload itself
# lives in a separate transient map, only while the receipt is held, and
# is dropped the moment the receipt reaches a terminal state; it never
# appears in any receipt response.
# ---------------------------------------------------------------------------
RECEIPT_MAX = 200
RECEIPT_RETRY_INTERVAL = 1.0
HOLD_DEFAULT = 30
HOLD_MIN = 1
HOLD_MAX = 120

_receipts_lock = threading.RLock()
_receipts = {}  # id -> receipt dict, insertion-ordered (oldest first)
_pending_payloads = {}  # receipt id -> payload, held receipts only
_receipt_thread = None


def _is_yield_conflict(status, result):
    if status != 409 or not isinstance(result, dict):
        return False
    error = str(result.get("error") or "").lower()
    return "yield" in error or "user active" in error


def _store_receipt(receipt, payload):
    with _receipts_lock:
        _receipts[receipt["id"]] = receipt
        _pending_payloads[receipt["id"]] = payload
        while len(_receipts) > RECEIPT_MAX:
            oldest = next(iter(_receipts))
            del _receipts[oldest]
            _pending_payloads.pop(oldest, None)


def _public_receipt(receipt):
    return {k: v for k, v in receipt.items() if not k.startswith("_")}


def _pump_receipt(receipt, now):
    """One retry step for a held receipt. Returns the receipt.

    Synchronous and thread-free so tests can drive it directly: attempts
    the forward once; a non-409 answer settles the receipt (applied, or
    failed when the hands turned out unreachable), a 409 past the
    deadline settles it as refused-yielded, otherwise it stays held.
    """
    with _receipts_lock:
        if receipt.get("state") != "held":
            return receipt
        payload = dict(_pending_payloads.get(receipt["id"]) or {})
        op = receipt["op"]
    try:
        status, result = _forward_act(op, payload)
    except Exception as exc:  # a stubbed / broken forward must not kill the pump
        status, result = None, {"ok": False, "error": f"forward failed: {exc}"}
        failed = True
    else:
        failed = (
            status == 502
            and isinstance(result, dict)
            and "hands unreachable" in str(result.get("error") or "").lower()
        )
    with _receipts_lock:
        receipt["updated_at"] = now
        if status is not None:
            receipt["hands_status"] = status
        if status == 409:
            if now >= receipt["deadline"]:
                receipt["state"] = "refused-yielded"
                _pending_payloads.pop(receipt["id"], None)
            return receipt
        if failed or status is None:
            receipt["state"] = "failed"
            receipt["result"] = None
            _pending_payloads.pop(receipt["id"], None)
            return receipt
        receipt["state"] = "applied"
        receipt["result"] = result
        _pending_payloads.pop(receipt["id"], None)
        return receipt


def _receipt_loop():
    while True:
        time.sleep(RECEIPT_RETRY_INTERVAL)
        with _receipts_lock:
            held = [r for r in _receipts.values() if r.get("state") == "held"]
        for receipt in held:
            try:
                _pump_receipt(receipt, time.time())
            except Exception:
                continue


def _ensure_receipt_thread():
    global _receipt_thread
    with _receipts_lock:
        if _receipt_thread is not None and _receipt_thread.is_alive():
            return
        _receipt_thread = threading.Thread(
            target=_receipt_loop, name="queued-act-retry", daemon=True
        )
        _receipt_thread.start()


def _forward_act(op, payload):
    """Forward one act to the hands. Returns (status_code, json_dict).

    This is exactly the forwarding /v1/act has always done, factored out
    so /v1/act/queued (and its retry pump) share the one code path.
    """
    if not HANDS_SECRET:
        return 503, {"ok": False, "error": "HANDS_SECRET not configured on gateway"}
    if op not in HANDS_OPS:
        return 400, {"ok": False, "error": f"unknown op: {op!r}"}
    try:
        r = requests.post(
            f"{HANDS_URL}/{op}", json=payload, headers=_hands_headers(), timeout=HANDS_TIMEOUT
        )
    except requests.RequestException as exc:
        return 502, {"ok": False, "error": f"hands unreachable: {exc}"}
    if r.status_code == 401:
        return 502, {
            "ok": False,
            "error": "hands rejected the gateway's secret — HANDS_SECRET does not match the hands app's current session secret",
        }
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {"ok": r.ok, "status": r.status_code}


@app.post("/v1/act")
def act():
    """One desktop action, forwarded to the hands.

    Body: {"op": "move"|"click"|"type"|"key"|"scroll", ...op params}
    Op params match the hands API exactly: move/click {x, y}, type {text},
    key {key}, scroll {clicks}.
    """
    body = request.get_json(force=True, silent=True) or {}
    op = body.get("op") or ""
    payload = {k: v for k, v in body.items() if k != "op"}
    status, result = _forward_act(op, payload)
    return jsonify(result), status


@app.post("/v1/act/queued")
def act_queued():
    """Like /v1/act, but a yield-409 is held and retried (wishlist #18).

    Same body as /v1/act plus optional hold_seconds (default 30, clamp
    1..120). Any non-yield result is returned exactly as /v1/act would
    return it. A 409 whose error says the act yielded (the owner is
    actively using the desktop) files a receipt, starts the retry
    engine, and answers 202; poll GET /v1/act/queued/<id> for the
    outcome (applied / refused-yielded / failed).
    """
    body = request.get_json(force=True, silent=True) or {}
    op = body.get("op") or ""
    hold = _clamp_number(body.get("hold_seconds", HOLD_DEFAULT), HOLD_DEFAULT, HOLD_MIN, HOLD_MAX)
    payload = {k: v for k, v in body.items() if k not in ("op", "hold_seconds")}
    status, result = _forward_act(op, payload)
    if not _is_yield_conflict(status, result):
        return jsonify(result), status
    now = time.time()
    receipt = {
        "id": uuid.uuid4().hex,
        "op": op,
        "param_keys": sorted(payload.keys()),
        "state": "held",
        "submitted_at": now,
        "updated_at": now,
        "deadline": now + hold,
        "hold_seconds": hold,
        "hands_status": status,
        "result": None,
    }
    _store_receipt(receipt, payload)
    _ensure_receipt_thread()
    return (
        jsonify({"ok": True, "queued": True, "id": receipt["id"], "state": "held"}),
        202,
    )


@app.get("/v1/act/queued")
def act_queued_list():
    with _receipts_lock:
        receipts = [
            {
                "id": r["id"],
                "op": r["op"],
                "state": r["state"],
                "submitted_at": r["submitted_at"],
            }
            for r in reversed(list(_receipts.values()))
        ]
    return jsonify({"ok": True, "receipts": receipts})


@app.get("/v1/act/queued/<receipt_id>")
def act_queued_get(receipt_id):
    with _receipts_lock:
        receipt = _receipts.get(receipt_id)
        if receipt is None:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "unknown or expired receipt id",
                        "state": "expired",
                    }
                ),
                404,
            )
        body = _public_receipt(receipt)
    body["ok"] = True
    return jsonify(body)


if __name__ == "__main__":
    from waitress import serve

    serve(app, host="0.0.0.0", port=5010, threads=8)
