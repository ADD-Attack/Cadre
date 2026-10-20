"""Tests for the packaged app's persistent gateway token (wishlist #1).

The token load-or-create shipped on the PC line 2026-10-17 (patch:
token load-or-create at ~/.muse-relay-v2/gateway-token.txt) but was
missing from the v3 tree, whose _start_all minted a fresh token per
launch — a swap would have locked the agent out until the owner
pasted the new token from the window. V3-R3 ports the shipped
implementation verbatim; these checks pin the behavior:

  * first call creates the file and returns ("created")
  * second call returns the SAME token with origin "saved"
  * a pre-existing token file is loaded verbatim (never rotated)
  * a too-short file is treated as absent and replaced

Runs on Linux like test_app.py: tkinter / pyautogui / winreg are
stubbed before the app module is loaded from its file path, and HOME
is redirected to a temp dir so the real ~/.muse-relay-v2 is untouched.

    python3 test_gateway_token.py
"""

import importlib.util
import os
import sys
import tempfile
import types

# --- fake tkinter (+ scrolledtext submodule) ------------------------------
_fake_tk = types.ModuleType("tkinter")
_fake_tk.Tk = object
_fake_tk.TclError = Exception
_fake_scrolled = types.ModuleType("tkinter.scrolledtext")
_fake_scrolled.ScrolledText = object
_fake_tk.scrolledtext = _fake_scrolled
sys.modules["tkinter"] = _fake_tk
sys.modules["tkinter.scrolledtext"] = _fake_scrolled

# --- fake pyautogui --------------------------------------------------------
_fake_gui = types.ModuleType("pyautogui")
_fake_gui.FAILSAFE = False
_fake_gui.PAUSE = 0
sys.modules["pyautogui"] = _fake_gui

# --- fake winreg (the app only touches it inside functions) ---------------
sys.modules["winreg"] = types.ModuleType("winreg")

HERE = os.path.dirname(os.path.abspath(__file__))
APP_PATH = os.path.join(HERE, "muse_relay_v2_app.py")

spec = importlib.util.spec_from_file_location("relay_app_under_test", APP_PATH)
appmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(appmod)


def run():
    failures = []

    def check(name, cond):
        if not cond:
            failures.append(name)

    old_home = os.environ.get("HOME")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HOME"] = tmp
        try:
            path = appmod._gateway_token_path()
            check("path is under HOME/.muse-relay-v2",
                  path == os.path.join(tmp, ".muse-relay-v2", "gateway-token.txt"))

            token1, origin1 = appmod._load_or_create_gateway_token()
            check("first call origin is created", origin1 == "created")
            check("first token is 32 hex chars",
                  len(token1) == 32 and all(c in "0123456789abcdef" for c in token1))
            check("token file written", os.path.isfile(path))

            token2, origin2 = appmod._load_or_create_gateway_token()
            check("second call origin is saved", origin2 == "saved")
            check("second call returns the same token", token2 == token1)

            # A pre-existing token (e.g. minted by the shipped app) is
            # loaded verbatim — the swap must not rotate it.
            known = "fa90cd059d69eed11e2ad26f117ce73f"
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(known + "\n")
            token3, origin3 = appmod._load_or_create_gateway_token()
            check("pre-existing token origin is saved", origin3 == "saved")
            check("pre-existing token loaded verbatim", token3 == known)

            # A too-short file is not a token; it is replaced.
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("short\n")
            token4, origin4 = appmod._load_or_create_gateway_token()
            check("short file replaced with created", origin4 == "created")
            check("replacement token differs from short file",
                  token4 != "short" and len(token4) == 32)
        finally:
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
