"""Tests for the V3-R1 parser health fix (Grok review High #6).

The bug: _model_status() called the lazy loaders _get_detector() /
_get_captioner(), so a bare GET /health — which the gateway probes
every few seconds — could trigger a full model load and block behind
the load lock (and a supervisor acting on a slow probe could restart
the parser mid-load). Status is now a pure read of the state globals;
loading happens on the parse path only.

    python3 test_health_status.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app as parser  # noqa: E402


def run():
    failures = []

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    def forbidden(name):
        def _raise():
            raise AssertionError(f"{name} must not be called from a status read")

        return _raise

    orig_det, orig_cap = parser._get_detector, parser._get_captioner
    parser._get_detector = forbidden("_get_detector")
    parser._get_captioner = forbidden("_get_captioner")
    try:
        status = parser._model_status()
        check("model status is a pure read (loaders untouched)",
              status["loaded"] is False and status["detector"] == "not_tried")
        r = parser.app.test_client().get("/health")
        body = r.get_json()
        check("GET /health answers 200 without loading the model",
              r.status_code == 200 and body["ok"] is True
              and body["model_loaded"] is False)
    finally:
        parser._get_detector, parser._get_captioner = orig_det, orig_cap

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
