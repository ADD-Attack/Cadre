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


@app.post("/v1/act")
def act():
    """One desktop action, forwarded to the hands.

    Body: {"op": "move"|"click"|"type"|"key"|"scroll", ...op params}
    Op params match the hands API exactly: move/click {x, y}, type {text},
    key {key}, scroll {clicks}.
    """
    if not HANDS_SECRET:
        return jsonify({"ok": False, "error": "HANDS_SECRET not configured on gateway"}), 503
    body = request.get_json(force=True, silent=True) or {}
    op = body.get("op") or ""
    if op not in HANDS_OPS:
        return jsonify({"ok": False, "error": f"unknown op: {op!r}"}), 400
    payload = {k: v for k, v in body.items() if k != "op"}
    try:
        r = requests.post(
            f"{HANDS_URL}/{op}", json=payload, headers=_hands_headers(), timeout=HANDS_TIMEOUT
        )
    except requests.RequestException as exc:
        return jsonify({"ok": False, "error": f"hands unreachable: {exc}"}), 502
    if r.status_code == 401:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "hands rejected the gateway's secret — HANDS_SECRET does not match the hands app's current session secret",
                }
            ),
            502,
        )
    try:
        return jsonify(r.json()), r.status_code
    except ValueError:
        return jsonify({"ok": r.ok, "status": r.status_code}), r.status_code


if __name__ == "__main__":
    from waitress import serve

    serve(app, host="0.0.0.0", port=5010, threads=8)
