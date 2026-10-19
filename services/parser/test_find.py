"""Tests for POST /find and the _find_matches filter (wishlist #12).

Runs anywhere with the parser's light deps installed — no model needed:
with no detector the honesty rule gives 501 from both routes, and the
detector/captioner are then stubbed for the success paths.

    python3 test_find.py
"""

import base64
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app as parser  # noqa: E402
from PIL import Image  # noqa: E402


def tiny_png_b64():
    img = Image.new("RGB", (50, 40), (10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


class _XY:
    def __init__(self, coords):
        self._coords = coords

    def tolist(self):
        return list(self._coords)


class _Box:
    def __init__(self, coords):
        self.xyxy = [_XY(coords)]


class _Result:
    def __init__(self, boxes):
        self.boxes = boxes


class _Detector:
    def predict(self, image, conf=None, verbose=False):
        return [_Result([_Box([0, 0, 10, 10]), _Box([20, 20, 40, 30])])]


def run():
    client = parser.app.test_client()
    failures = []

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    img_b64 = tiny_png_b64()

    # No model loaded: honesty rule — /find 501 and /parse still 501,
    # in the same body style.
    r = client.post("/find", json={"image_b64": img_b64, "text": "icon"})
    check("no model: /find returns 501", r.status_code == 501)
    check(
        "no model: /find 501 body matches /parse style",
        r.get_json()["ok"] is False and "model" in r.get_json(),
    )
    r = client.post("/parse", json={"image_b64": img_b64})
    check("no model: /parse still returns 501", r.status_code == 501)

    # Empty text -> 400 (checked before the model).
    r = client.post("/find", json={"image_b64": img_b64, "text": ""})
    check("empty text returns 400", r.status_code == 400)
    r = client.post("/find", json={"image_b64": img_b64})
    check("missing text returns 400", r.status_code == 400)

    # Stub the detector; no captioner -> labels fall back to "icon".
    parser._get_detector = lambda: _Detector()
    parser._get_captioner = lambda: None

    r = client.post("/parse", json={"image_b64": img_b64})
    body = r.get_json()
    check(
        "/parse via _run_parse returns 2 elements",
        r.status_code == 200 and body["ok"] and len(body["elements"]) == 2,
    )
    check(
        "/parse reports image size",
        body["width"] == 50 and body["height"] == 40,
    )

    r = client.post("/find", json={"image_b64": img_b64, "text": "icon"})
    body = r.get_json()
    check(
        "/find 'icon' returns 2 matches",
        r.status_code == 200 and body["ok"] and body["count"] == 2
        and len(body["matches"]) == 2,
    )
    m = body["matches"][1]
    check(
        "match keeps bbox/center/interactable shape",
        m["bbox"] == [20, 20, 40, 30] and m["center"] == [30, 25]
        and m["interactable"] is True and m["label"] == "icon"
        and m["id"] == 1,
    )
    check(
        "/find reports image size",
        body["width"] == 50 and body["height"] == 40,
    )

    r = client.post("/find", json={"image_b64": img_b64, "text": "nope"})
    body = r.get_json()
    check(
        "/find 'nope' returns 0 matches, ok true",
        r.status_code == 200 and body["ok"] and body["count"] == 0
        and body["matches"] == [],
    )

    # Case sensitivity: the pure filter.
    elements = [{"label": "Save File"}, {"label": "open"}]
    check(
        "_find_matches is case-insensitive by default",
        len(parser._find_matches(elements, "save")) == 1,
    )
    check(
        "_find_matches honours case_sensitive=True",
        parser._find_matches(elements, "save", True) == [],
    )
    check(
        "_find_matches case-sensitive exact substring still matches",
        len(parser._find_matches(elements, "Save", True)) == 1,
    )
    r = client.post(
        "/find",
        json={"image_b64": img_b64, "text": "ICON", "case_sensitive": True},
    )
    check(
        "/find case_sensitive=True does not match 'icon'",
        r.status_code == 200 and r.get_json()["count"] == 0,
    )
    r = client.post("/find", json={"image_b64": img_b64, "text": "ICON"})
    check(
        "/find default is case-insensitive",
        r.status_code == 200 and r.get_json()["count"] == 2,
    )

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
