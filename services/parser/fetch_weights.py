#!/usr/bin/env python3
"""Fetch the OmniParser v2 weights into the parser's models directory.

Usage:
    pip install huggingface_hub
    python fetch_weights.py [models_dir]

models_dir defaults to PARSER_MODELS_DIR, then /models (Docker volume),
then ./models next to this file (native runs).

Downloads from microsoft/OmniParser-v2.0:
    icon_detect/model.pt        (~250 MB — the icon detector)
    icon_caption_florence/      (~1 GB — optional captioner; labels icons)
"""

import os
import sys


def default_dir():
    if os.environ.get("PARSER_MODELS_DIR"):
        return os.environ["PARSER_MODELS_DIR"]
    if os.path.isdir("/models"):
        return "/models"
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else default_dir()
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("huggingface_hub is not installed. Run: pip install huggingface_hub")
        return 1
    print(f"Downloading OmniParser v2 weights into {target} ...")
    snapshot_download(
        repo_id="microsoft/OmniParser-v2.0",
        local_dir=target,
        allow_patterns=["icon_detect/*", "icon_caption_florence/*"],
    )
    det = os.path.join(target, "icon_detect", "model.pt")
    if os.path.isfile(det):
        print(f"OK: detector weights at {det}")
        return 0
    print("Download finished but icon_detect/model.pt is missing — check the output above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
