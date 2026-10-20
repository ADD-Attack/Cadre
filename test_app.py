"""Tests for the packaged app's module-level helpers (wishlist #7).

Runs on Linux: tkinter, pyautogui and winreg are stubbed in
sys.modules before the app module is loaded via importlib from its
file path. RelayApp itself is never instantiated (it builds UI) —
only the autostart helpers and the pure ServiceHealth state machine
are exercised, against a dict-backed fake winreg.

    python3 test_app.py
"""

import importlib.util
import os
import sys
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

# --- dict-backed fake winreg ----------------------------------------------
_fake_reg = types.ModuleType("winreg")
_fake_reg.HKEY_CURRENT_USER = "HKCU"
_fake_reg.REG_SZ = 1
_fake_reg.KEY_READ = 0x20019
_fake_reg.KEY_SET_VALUE = 0x2
_fake_reg.KEY_WRITE = 0x20006
_reg_values = {}


class _FakeKey:
    pass


def _reg_open_key(hive, subkey, reserved=0, access=None):
    return _FakeKey()


def _reg_create_key(hive, subkey):
    return _FakeKey()


def _reg_set_value_ex(key, name, reserved, kind, value):
    _reg_values[name] = value


def _reg_query_value_ex(key, name):
    if name not in _reg_values:
        raise FileNotFoundError(name)
    return _reg_values[name], _fake_reg.REG_SZ


def _reg_delete_value(key, name):
    if name not in _reg_values:
        raise FileNotFoundError(name)
    del _reg_values[name]


def _reg_close_key(key):
    pass


_fake_reg.OpenKey = _reg_open_key
_fake_reg.CreateKey = _reg_create_key
_fake_reg.SetValueEx = _reg_set_value_ex
_fake_reg.QueryValueEx = _reg_query_value_ex
_fake_reg.DeleteValue = _reg_delete_value
_fake_reg.CloseKey = _reg_close_key
sys.modules["winreg"] = _fake_reg

# --- load the app module from its file path --------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "muse_relay_v2_app_under_test", os.path.join(_HERE, "muse_relay_v2_app.py")
)
appmod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = appmod
_spec.loader.exec_module(appmod)


def run():
    failures = []

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            failures.append(name)

    saved_executable = sys.executable
    had_frozen = hasattr(sys, "frozen")
    saved_frozen = getattr(sys, "frozen", None)
    try:
        # --- _autostart_command shape ---------------------------------
        sys.frozen = True
        sys.executable = r"C:\Relay\Muse Relay v2.exe"
        check("frozen command is the quoted executable",
              appmod._autostart_command() == r'"C:\Relay\Muse Relay v2.exe"')

        sys.frozen = False
        sys.executable = r"C:\Python\python.exe"
        expected = '"{}" "{}"'.format(
            r"C:\Python\python.exe", os.path.abspath(appmod.__file__)
        )
        check("dev command is quoted python + quoted script",
              appmod._autostart_command() == expected)
    finally:
        sys.executable = saved_executable
        if had_frozen:
            sys.frozen = saved_frozen
        elif hasattr(sys, "frozen"):
            del sys.frozen

    # --- _set_autostart / _autostart_enabled via fake winreg ----------
    _reg_values.clear()
    check("autostart starts disabled", appmod._autostart_enabled() is False)
    check("set(True) succeeds", appmod._set_autostart(True) is True)
    check("set(True) writes the Run value",
          _reg_values.get(appmod.AUTOSTART_VALUE_NAME)
          == appmod._autostart_command())
    check("enabled() is True after set(True)",
          appmod._autostart_enabled() is True)
    check("value name is 'Muse Relay v2'",
          appmod.AUTOSTART_VALUE_NAME == "Muse Relay v2")
    check("set(False) succeeds", appmod._set_autostart(False) is True)
    check("set(False) removes the Run value",
          appmod.AUTOSTART_VALUE_NAME not in _reg_values)
    check("enabled() is False after set(False)",
          appmod._autostart_enabled() is False)
    check("set(False) when already absent still succeeds",
          appmod._set_autostart(False) is True)

    # --- off-Windows: seam returns None -------------------------------
    real_winreg = appmod._winreg
    appmod._winreg = lambda: None
    try:
        check("off-Windows enabled() is False",
              appmod._autostart_enabled() is False)
        check("off-Windows set(True) is False without raising",
              appmod._set_autostart(True) is False)
        check("off-Windows set(False) is False without raising",
              appmod._set_autostart(False) is False)
    finally:
        appmod._winreg = real_winreg

    # --- ServiceHealth --------------------------------------------------
    h = appmod.ServiceHealth()
    check("1st failure -> none", h.note(False) == "none")
    check("2nd failure -> none", h.note(False) == "none")
    check("3rd consecutive failure -> restart", h.note(False) == "restart")

    h = appmod.ServiceHealth()
    check("failure then success resets (1)", h.note(False) == "none")
    check("failure then success resets (2)", h.note(False) == "none")
    check("success -> none", h.note(True) == "none")
    check("after reset, 1st failure -> none", h.note(False) == "none")
    check("after reset, 2nd failure -> none", h.note(False) == "none")
    check("after reset, 3rd failure -> restart", h.note(False) == "restart")

    h = appmod.ServiceHealth()
    results = [h.note(False) for _ in range(3 * 5)]
    check("restarts happen on streaks 1-3",
          results[2] == "restart" and results[5] == "restart"
          and results[8] == "restart")
    check("after the restart budget, give_up once",
          results[11] == "give_up")
    check("give_up is not repeated",
          all(r == "none" for r in results[12:]))

    print("FAILED: " + ", ".join(failures) if failures else "ALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
