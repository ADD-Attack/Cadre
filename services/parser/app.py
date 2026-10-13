"""Muse Relay v2 — parser service.

Screen parsing for surfaces with no DOM and no UI Automation tree (games,
canvas, custom-drawn UI): screenshot in, labeled + numbered elements out —
the set-of-marks contract a driving model can click against.

Contract:
  POST /parse {"image_b64": "<png base64>"}
    -> {"ok": true, "elements": [{"id": 0, "label": "...", "bbox": [x0,y0,x1,y1],
        "center": [x, y], "interactable": true}], "width": W, "height": H}

Model: OmniParser v2 weights (icon detector + optional Florence captioner),
expected under the models directory (PARSER_MODELS_DIR, default /models in
Docker, ./models next to this file when run natively). Fetch them with
fetch_weights.py; install the heavy deps from requirements-model.txt.

Honesty rule: with no detector loaded, /parse returns 501 — never a fake
"ok" with an empty element list, which would read to a driver as a blank
screen.
"""

import base64
import binascii
import io
import os
import threading

from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16_000_000

CONF = float(os.environ.get("PARSER_CONF", "0.25"))


def _default_models_dir():
    if os.path.isdir("/models"):
        return "/models"
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")


MODELS_DIR = os.environ.get("PARSER_MODELS_DIR", _default_models_dir())

_state_lock = threading.Lock()
_detector = None
_detector_state = "not_tried"  # -> loaded | weights_missing | deps_missing | load_error: ...
_captioner = None
_captioner_state = "not_tried"


def _find_detector_weights():
    for cand in (
        os.path.join(MODELS_DIR, "icon_detect", "model.pt"),
        os.path.join(MODELS_DIR, "icon_detect", "best.pt"),
        os.path.join(MODELS_DIR, "model.pt"),
    ):
        if os.path.isfile(cand):
            return cand
    return None


def _get_detector():
    global _detector, _detector_state
    if _detector is not None or _detector_state not in ("not_tried",):
        return _detector
    with _state_lock:
        if _detector is not None or _detector_state != "not_tried":
            return _detector
        weights = _find_detector_weights()
        if not weights:
            _detector_state = "weights_missing"
            return None
        try:
            from ultralytics import YOLO
        except ImportError:
            _detector_state = "deps_missing"
            return None
        try:
            _detector = YOLO(weights)
            _detector_state = "loaded"
        except Exception as exc:  # weights present but unreadable
            _detector_state = f"load_error: {exc}"
        return _detector


def _get_captioner():
    """Optional Florence-2 captioner (OmniParser's icon_caption_florence).

    Returns (model, processor) or None. Labels fall back to "icon" without it.
    """
    global _captioner, _captioner_state
    if _captioner is not None or _captioner_state != "not_tried":
        return _captioner
    with _state_lock:
        if _captioner is not None or _captioner_state != "not_tried":
            return _captioner
        cap_dir = os.path.join(MODELS_DIR, "icon_caption_florence")
        if not os.path.isdir(cap_dir):
            _captioner_state = "weights_missing"
            return None
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoProcessor
        except ImportError:
            _captioner_state = "deps_missing"
            return None
        try:
            model = AutoModelForCausalLM.from_pretrained(
                cap_dir, trust_remote_code=True
            ).eval()
            processor = AutoProcessor.from_pretrained(cap_dir, trust_remote_code=True)
            _captioner = (model, processor)
            _captioner_state = "loaded"
        except Exception as exc:
            _captioner_state = f"load_error: {exc}"
        return _captioner


def _caption(crop):
    cap = _get_captioner()
    if cap is None:
        return None
    model, processor = cap
    try:
        import torch

        task = "<CAPTION>"
        inputs = processor(text=task, images=crop, return_tensors="pt")
        with torch.no_grad():
            ids = model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=32,
            )
        text = processor.batch_decode(ids, skip_special_tokens=True)[0]
        return text.strip() or None
    except Exception:
        return None


def _model_status():
    _get_detector()
    _get_captioner()
    return {
        "detector": _detector_state,
        "captioner": _captioner_state,
        "models_dir": MODELS_DIR,
        "loaded": _detector is not None,
    }


@app.get("/health")
def health():
    status = _model_status()
    return jsonify(
        {"ok": True, "service": "parser", "model_loaded": status["loaded"], "model": status}
    )


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

    detector = _get_detector()
    if detector is None:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "parser model not loaded",
                    "model": _model_status(),
                    "hint": "run fetch_weights.py and install requirements-model.txt",
                }
            ),
            501,
        )

    try:
        from PIL import Image

        image = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        return jsonify({"ok": False, "error": "image bytes are not a readable image"}), 400

    width, height = image.size
    results = detector.predict(image, conf=CONF, verbose=False)
    boxes = []
    for r in results:
        if r.boxes is None:
            continue
        for b in r.boxes:
            x0, y0, x1, y1 = (int(v) for v in b.xyxy[0].tolist())
            boxes.append((x0, y0, x1, y1))
    boxes.sort(key=lambda b: (b[1], b[0]))  # reading order: top-to-bottom, left-to-right

    elements = []
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        label = None
        if _get_captioner() is not None:
            label = _caption(image.crop((x0, y0, x1, y1)))
        elements.append(
            {
                "id": i,
                "label": label or "icon",
                "label_source": "captioner" if label else "detector",
                "bbox": [x0, y0, x1, y1],
                "center": [(x0 + x1) // 2, (y0 + y1) // 2],
                "interactable": True,
            }
        )
    return jsonify({"ok": True, "elements": elements, "width": width, "height": height})


if __name__ == "__main__":
    from waitress import serve

    serve(app, host="0.0.0.0", port=5011, threads=4)
