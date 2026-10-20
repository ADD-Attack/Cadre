"""R7.2 release evidence (Astra Finding 4): the REAL Windows clipboard
backend, end to end. Runs only on the target Windows build, and only
when asked:

    set RELAY_LIVE_CLIPBOARD=1
    python -m pytest -q tests/test_windows_clipboard_real.py

It touches the operator's clipboard: the current text is saved first
and restored in a finally. Content is read back through an INDEPENDENT
path (raw user32 calls written here, not the backend's get_text).
"""
import ctypes
import importlib.util
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.name != "nt" or os.environ.get("RELAY_LIVE_CLIPBOARD") != "1",
    reason="live Windows clipboard test (set RELAY_LIVE_CLIPBOARD=1 on the PC)",
)

ROOT = Path(__file__).resolve().parents[1]
CASES = ["", "https://www.spotify.com/account/privacy/", "non-BMP: \U0001F600 \U00010348 end"]


def _independent_read():
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.GetClipboardData.restype = ctypes.c_void_p
    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalSize.restype = ctypes.c_size_t
    kernel32.GlobalSize.argtypes = [ctypes.c_void_p]
    assert user32.OpenClipboard(None)
    try:
        h = user32.GetClipboardData(13)
        if not h:
            return None
        size = kernel32.GlobalSize(h)
        p = kernel32.GlobalLock(h)
        try:
            raw = ctypes.string_at(p, size)
        finally:
            kernel32.GlobalUnlock(h)
    finally:
        user32.CloseClipboard()
    text = raw.decode("utf-16-le")
    return text.split("\x00", 1)[0]


def test_windows_clipboard_real_roundtrip():
    spec = importlib.util.spec_from_file_location("live_clip_hands", ROOT / "hands/muse_relay_hands.py")
    hands = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hands)
    backend = hands._WindowsClipboardBackend()
    saved = _independent_read()
    try:
        for text in CASES:
            backend.set_text(text)
            assert _independent_read() == text, repr(text)
            assert backend.get_text() == text, repr(text)
    finally:
        backend.set_text(saved or "")
    assert (_independent_read() or "") == (saved or "")
