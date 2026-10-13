"""Muse Relay v2 — parser service.

Screen parsing for surfaces with no DOM and no UI Automation tree (games,
canvas, custom-drawn UI): screenshot in, labeled + numbered elements out —
the set-of-marks contract a driving model can click against.

Contract:
  POST /parse {"image_b64": "<png base64>"}
    -> {"ok": true, "elements": [{"id": 0, "label": "...", "bbox": [x0,y0,x1,y1],
        "center": [x, y], "interactable": true}], "width": W, "height": H}

Status: scaffold. The endpoint validates input and returns an empty element
list until the OmniParser weights are integrated (weights land in /models,
see docker-compose volume parser-weights).
"""

import base64
import binascii

from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16_000_000


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "parser", "model_loaded": False})


@app.post("/parse")
def parse():
    body = request.get_json(force=True, silent=True) or {}
    image_b64 = body.get("image_b64") or ""
    if not image_b64:
        return jsonify({"ok": False, "error": "image_b64 required"}), 400
    try:
        raw = base64.b64decode(image_b64, validate=True)
    except binascii.Error:
        return jsonify({"ok": False, "error": "image_b64 is not valid base64"}), 400
    # TODO(omniparser): decode PNG, run detector + captioner, return elements.
    return jsonify(
        {
            "ok": True,
            "elements": [],
            "note": "parser model not integrated yet",
            "image_bytes": len(raw),
        }
    )


if __name__ == "__main__":
    from waitress import serve

    serve(app, host="0.0.0.0", port=5011, threads=4)
