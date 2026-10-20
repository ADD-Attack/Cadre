"""Operator test harness for the R2 verification run.

The repo's existing hands tests inject fake pyautogui / tkinter modules
into sys.modules before loading the hands module (see
hands/test_actuation.py). tests/test_v3r2_remaining.py loads the hands
and packaged-app modules directly, so it needs the same fakes present
when its module-scoped fixtures execute. On the Windows build host both
modules import for real; in the operator's Linux test venv they do not.
These fakes mirror the established pattern: attribute access returns a
recorder no-op so monkeypatch.setattr(..., raising=True) finds the
attributes it expects to replace.
"""
import sys
import types

import pytest
from _pytest.monkeypatch import MonkeyPatch


class _LenientMonkeyPatch(MonkeyPatch):
    """setattr defaults to raising=False.

    Several R2 tests patch Windows-only attributes (ctypes.windll) that
    do not exist on this Linux test host at all; pytest's default
    raising=True makes the patch itself fail before the code under test
    runs. On the Windows build host the attributes exist and the default
    never matters.
    """

    def setattr(self, target, name, value=None, raising=False):
        return super().setattr(target, name, value, raising=raising)


@pytest.fixture
def monkeypatch():
    mp = _LenientMonkeyPatch()
    yield mp
    mp.undo()


def _recorder(*args, **kwargs):
    return None


class _FakeModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        fn = _recorder
        self.__dict__[name] = fn
        return fn


def _install(name):
    if name not in sys.modules:
        mod = _FakeModule(name)
        sys.modules[name] = mod
    return sys.modules[name]


_pag = _install("pyautogui")
_pag.FAILSAFE = False
_pag.PAUSE = 0
_install("tkinter")
_install("tkinter.messagebox")
