"""Muse Relay v2 — gateway service.

The agent-facing API. Owns authentication (per-deployment token, constant-time
compare, failed-guess lockout) and routes control requests to the Windows
hands process and parse requests to the parser service.

Status: scaffold. Auth + health + routing contract are real; the hands link
(/v1/screen, /v1/act) returns 501 until the hands registration lands.
"""

import hmac
import os
import threading
import time

import requests
from flask import Flask, jsonify, request

TOKEN = os.environ.get("RELAY_GATEWAY_TOKEN", "")
HANDS_URL = os.environ.get("HANDS_URL", "http://host.docker.internal:5000")
PARSER_URL = os.environ.get("PARSER_URL", "http://parser:5011")

MAX_FAILS = 10
FAIL_WINDOW = 600
LOCKOUT_SECONDS = 300

_fail_lock = threading.Lock()
_fail_times: list = []
_lockout_until = 0.0

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


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "gateway"})


@app.get("/v1/info")
def info():
    return jsonify(
        {
            "ok": True,
            "hands_url_configured": bool(HANDS_URL),
            "parser_url": PARSER_URL,
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
    return jsonify({"ok": False, "error": "hands link not implemented yet"}), 501


@app.post("/v1/act")
def act():
    return jsonify({"ok": False, "error": "hands link not implemented yet"}), 501


if __name__ == "__main__":
    from waitress import serve

    serve(app, host="0.0.0.0", port=5010, threads=8)
