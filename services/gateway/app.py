"""Muse Relay v2 — gateway service.

The agent-facing API. Owns authentication (per-deployment token, constant-time
compare, failed-guess lockout) and routes control requests to the Windows
hands process and parse requests to the parser service.

The hands link: the gateway holds the hands base URL (HANDS_URL) and the
hands' current session secret (HANDS_SECRET — the packaged hands app
generates a fresh secret every launch and shows it in its window; copy it
into the gateway's environment). Agent calls are translated:

  GET  /v1/screen            -> GET  {HANDS_URL}/screenshot  (PNG bytes back)
  POST /v1/act {"op": ...}   -> POST {HANDS_URL}/<op>        (move/click/
                                                              type/key/scroll)
"""

import hmac
import os
import threading
import time

import requests
from flask import Flask, Response, jsonify, request

TOKEN = os.environ.get("RELAY_GATEWAY_TOKEN", "")
HANDS_URL = os.environ.get("HANDS_URL", "http://host.docker.internal:5000").rstrip("/")
HANDS_SECRET = os.environ.get("HANDS_SECRET", "")
PARSER_URL = os.environ.get("PARSER_URL", "http://parser:5011").rstrip("/")

HANDS_OPS = {"move", "click", "type", "key", "scroll"}
HANDS_TIMEOUT = 30

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


@app.get("/v1/screen")
def screen():
    """Current screenshot from the hands, proxied as PNG bytes."""
    if not HANDS_SECRET:
        return jsonify({"ok": False, "error": "HANDS_SECRET not configured on gateway"}), 503
    try:
        r = requests.get(
            f"{HANDS_URL}/screenshot", headers=_hands_headers(), timeout=HANDS_TIMEOUT
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
    if r.status_code != 200:
        return jsonify({"ok": False, "error": f"hands returned {r.status_code}"}), 502
    return Response(r.content, content_type=r.headers.get("Content-Type", "image/png"))


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
