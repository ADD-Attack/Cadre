"""Fixes for muse-relay v3 R2. Loads the service modules by path."""
import importlib.util
import inspect
import os
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(rel):
    path = ROOT / rel
    name = "v3r2_" + "_".join(path.with_suffix("").parts[-3:])
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gateway():
    return _load("services/gateway/app.py")


@pytest.fixture(scope="module")
def hands():
    return _load("hands/muse_relay_hands.py")


@pytest.fixture(scope="module")
def parser():
    return _load("services/parser/app.py")


@pytest.fixture(scope="module")
def packaged():
    return _load("muse_relay_v2_app.py")


def _ui_class(mod):
    for value in vars(mod).values():
        if isinstance(value, type) and hasattr(value, "_note_health") and hasattr(value, "_poll"):
            return value
    raise AssertionError("packaged app class not found")


def test_yield_blocks_drag_and_skips_the_button(hands, monkeypatch):
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (False, 0.2))
    monkeypatch.delenv("HANDS_YIELD_IDLE_SECONDS", raising=False)
    called = {"down": 0}
    monkeypatch.setattr(hands.pyautogui, "mouseDown", lambda **k: called.__setitem__("down", 1))
    with hands.app.test_request_context(
        "/drag", method="POST", json={"x1": 0, "y1": 0, "x2": 1, "y2": 1, "duration": 0.2}
    ):
        resp = hands.drag()
    status = resp[1] if isinstance(resp, tuple) else resp.status_code
    body = resp[0].get_json() if isinstance(resp, tuple) else resp.get_json()
    assert status == 409
    assert "user active" in body["error"]
    assert called["down"] == 0


def test_yield_inactive_when_probe_is_none(hands, monkeypatch):
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (None, None))
    events = []
    monkeypatch.setattr(hands.pyautogui, "moveTo", lambda *a, **k: events.append(k.get("duration")))
    monkeypatch.setattr(hands.pyautogui, "mouseDown", lambda **k: None)
    monkeypatch.setattr(hands.pyautogui, "mouseUp", lambda **k: events.append("up"))
    with hands.app.test_request_context(
        "/drag", method="POST", json={"x1": 0, "y1": 0, "x2": 1, "y2": 1, "duration": 0, "human": False}
    ):
        hands.drag()
    assert 0 in events or 0.0 in events
    assert events[-1] == "up"


def test_drag_releases_button_when_move_raises(hands, monkeypatch):
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (None, None))
    calls = {"n": 0, "up": 0}

    def move_to(*_a, **_k):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("boom")

    monkeypatch.setattr(hands.pyautogui, "moveTo", move_to)
    monkeypatch.setattr(hands.pyautogui, "mouseDown", lambda **k: None)
    monkeypatch.setattr(hands.pyautogui, "mouseUp", lambda **k: calls.__setitem__("up", calls["up"] + 1))
    with hands.app.test_request_context(
        "/drag", method="POST", json={"x1": 0, "y1": 0, "x2": 3, "y2": 4, "duration": 0.2, "human": False}
    ):
        with pytest.raises(RuntimeError):
            hands.drag()
    assert calls["up"] == 1


def test_paste_restores_clipboard_when_hotkey_raises(hands, monkeypatch):
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (None, None))

    class Clip:
        def __init__(self):
            self.text = "ORIGINAL"

        def get_text(self):
            return self.text

        def set_text(self, value):
            self.text = value

    clip = Clip()
    monkeypatch.setattr(hands, "_clipboard_backend", lambda: clip)
    monkeypatch.setattr(hands.pyautogui, "hotkey", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nope")))
    monkeypatch.setattr(hands.pyautogui, "write", lambda *a, **k: None)
    with hands.app.test_request_context(
        "/type", method="POST", json={"text": "SECRET", "method": "paste", "jitter": False}
    ):
        hands.type_text()
    assert clip.text == "ORIGINAL"


def test_gate_yields_move_without_a_view(hands, monkeypatch):
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (False, 1))
    with hands.app.test_request_context("/move", method="POST", headers={"X-Secret": hands.SHARED_SECRET}):
        resp = hands.gate()
    assert resp[1] == 409
    assert "user active" in resp[0].get_json()["error"]


def test_empty_hands_secret_rejected(hands):
    saved = hands.SHARED_SECRET
    hands.SHARED_SECRET = ""
    try:
        with hands.app.test_request_context("/status", headers={"X-Secret": ""}):
            resp = hands.gate()
        assert resp[1] == 401
    finally:
        hands.SHARED_SECRET = saved


def test_valid_hands_secret_not_locked_out(hands, monkeypatch):
    hands._lockout_by_peer["10.1.1.1"] = hands.time.monotonic() + 500
    with hands.app.test_request_context(
        "/status",
        headers={"X-Secret": hands.SHARED_SECRET},
        environ_base={"REMOTE_ADDR": "10.1.1.1"},
    ):
        assert hands.gate() is None
    with hands.app.test_request_context(
        "/status",
        headers={"X-Secret": "nope"},
        environ_base={"REMOTE_ADDR": "10.1.1.1"},
    ):
        assert hands.gate()[1] == 429
    with hands.app.test_request_context(
        "/status",
        headers={"X-Secret": "nope"},
        environ_base={"REMOTE_ADDR": "10.9.9.9"},
    ):
        assert hands.gate()[1] == 401


def test_gateway_valid_token_not_locked_out(gateway):
    gateway.TOKEN = "good-token"
    gateway._lockout_by_peer["10.2.2.2"] = gateway.time.monotonic() + 500
    with gateway.app.test_request_context(
        "/v1/info",
        headers={"X-Relay-Token": "good-token"},
        environ_base={"REMOTE_ADDR": "10.2.2.2"},
    ):
        assert gateway.gate() is None
    with gateway.app.test_request_context(
        "/v1/info",
        headers={"X-Relay-Token": "bad"},
        environ_base={"REMOTE_ADDR": "10.2.2.2"},
    ):
        assert gateway.gate()[1] == 429
    with gateway.app.test_request_context(
        "/v1/info",
        headers={"X-Relay-Token": "bad"},
        environ_base={"REMOTE_ADDR": "10.8.8.8"},
    ):
        assert gateway.gate()[1] == 401


def _receipt(gateway, now, status, body, deadline=None):
    receipt = {
        "id": "r1",
        "state": "held",
        "op": "click",
        "deadline": now + 100 if deadline is None else deadline,
        "updated_at": 0,
    }
    gateway._pending_payloads["r1"] = {"x": 1}
    gateway._forward_act = lambda op, payload: (status, body)
    return gateway._pump_receipt(receipt, now)


def test_pump_maps_2xx_yield_and_everything_else(gateway):
    now = 1_000.0
    applied = _receipt(gateway, now, 200, {"ok": True})
    assert applied["state"] == "applied"
    held = _receipt(gateway, now, 409, {"error": "user active — control yielded"})
    assert held["state"] == "held"
    assert "r1" in gateway._pending_payloads or held["state"] == "held"
    for status in (400, 500, 503, 502):
        failed = _receipt(gateway, now, status, {"ok": False, "error": "hands unreachable: x"})
        assert failed["state"] == "failed"
    other = _receipt(gateway, now, 409, {"error": "offset mismatch"})
    assert other["state"] == "failed"


def test_release_expired_claim_includes_reserved_for(gateway, monkeypatch):
    monkeypatch.setattr(gateway, "_current_claim_locked", lambda now: None)

    def snapshot(now):
        return None, [], "bob"

    monkeypatch.setattr(gateway, "_claim_snapshot", snapshot)
    with gateway.app.test_request_context(
        "/v1/claim/release", method="POST", json={"holder": "alice"}
    ):
        resp = gateway.hands_release()
    body = resp[0].get_json() if isinstance(resp, tuple) else resp.get_json()
    assert body["released"] is False
    assert body["claim"] is None
    assert body["reserved_for"] == "bob"


def test_window_title_non_200_is_a_fetch_error(gateway):
    # _check_window_title builds its error tuple with jsonify (the house
    # pattern for _WaitFetchError payloads), which needs an app context;
    # in production the wait routes always call it inside one.
    with gateway.app.app_context():
        with pytest.raises(gateway._WaitFetchError) as exc:
            gateway._check_window_title("x", fetch=lambda: (None, 500))
        assert exc.value.response[1] == 500
        with pytest.raises(gateway._WaitFetchError) as exc:
            gateway._check_window_title("x", fetch=lambda: (None, 401))
        assert exc.value.response[1] == 502
        with pytest.raises(gateway._WaitUnsupported):
            gateway._check_window_title("x", fetch=lambda: (None, 404))
        assert gateway._check_window_title("nope", fetch=lambda: ([], 200)) is False


def test_filedrop_aborts_when_a_later_chunk_fails(gateway):
    calls = []

    def post(path, payload):
        calls.append(path)
        if path.endswith("/begin"):
            return 200, {"ok": True, "upload_id": "u", "chunk_max": 4}
        if path.endswith("/chunk"):
            return 500, {"ok": False, "error": "disk"}
        return 200, {"ok": True}

    body, status = gateway._filedrop_via_hands("inbox", "a.bin", b"abcdef", "ab" * 32, post=post)
    assert status == 500
    assert body["error"] == "disk"
    assert calls[-1] == "/filedrop/abort"
    assert "/filedrop/commit" not in calls


def test_content_length_fits_16mb_filedrop(gateway):
    assert gateway.app.config["MAX_CONTENT_LENGTH"] == 32 * 1024 * 1024


def test_hash_stable_false_when_sizes_differ(gateway, monkeypatch):
    class Img:
        def __init__(self, w, h):
            self.size = (w, h)
            self.width = w
            self.height = h

        def tobytes(self):
            return b"px"

    monkeypatch.setattr(gateway, "_decode_masked", lambda png, mask: Img(*png))
    flag = []
    gateway._frame_hash((2, 2), (3, 2), 0, flag)
    assert flag == [False]


def test_screen_wait_timeout_and_change(gateway, monkeypatch):
    monkeypatch.setattr(gateway, "_screen_fetch_kwargs", lambda: ({}, None))
    monkeypatch.setattr(gateway, "_fetch_screenshot", lambda **k: (b"png", {}, None))
    monkeypatch.setattr(gateway.time, "sleep", lambda _s: None)
    hashes = iter(["same", "same"])

    def fake_hash(png, png_b, mask, out=None):
        if out is not None:
            out.append(True)
        return next(hashes), 1, 1

    monkeypatch.setattr(gateway, "_frame_hash", fake_hash)
    with gateway.app.test_request_context("/v1/screen/wait?since=same&timeout=0"):
        body = gateway.screen_wait().get_json()
    assert body["timed_out"] is True
    assert body["hash"] == "same"
    monkeypatch.setattr(gateway, "_frame_hash", lambda *a, **k: ("other", 1, 1))
    with gateway.app.test_request_context("/v1/screen/wait?since=same&timeout=25"):
        body = gateway.screen_wait().get_json()
    assert body["timed_out"] is False
    assert body["hash"] == "other"


def test_hands_post_maps_401_to_502(gateway, monkeypatch):
    class Resp:
        status_code = 401

        def json(self):
            return {"ok": False, "error": "bad secret"}

    monkeypatch.setattr(gateway.requests, "post", lambda *a, **k: Resp())
    status, body = gateway._hands_post("/click", {"x": 1})
    assert status == 502
    assert "HANDS_SECRET" in body["error"]


def test_relative_allowlist_entry_dropped(hands, monkeypatch, tmp_path):
    monkeypatch.setenv("HANDS_FILEDROP_DIRS", "relative" + os.pathsep + str(tmp_path))
    got = hands._filedrop_dirs()
    assert len(got) == 1
    assert os.path.isabs(got[0])


def test_closed_upload_rejects_chunk(hands, monkeypatch):
    monkeypatch.setattr(hands, "_filedrop_gate", lambda: None)
    hands._uploads["u"] = {
        "buffer": bytearray(),
        "size": 4,
        "closed": True,
        "sha256": "ab" * 32,
        "dir": ".",
        "filename": "a",
    }
    with hands.app.test_request_context(
        "/filedrop/chunk",
        method="POST",
        json={"upload_id": "u", "offset": 0, "data_b64": "YQ=="},
    ):
        resp = hands.filedrop_chunk()
    status = resp[1] if isinstance(resp, tuple) else resp.status_code
    assert status == 404
    hands._uploads.pop("u", None)


def test_focus_ok_only_when_activation_returns_true(hands, monkeypatch):
    monkeypatch.setattr(hands, "_probe_lock_state", lambda: (None, None))
    monkeypatch.setattr(hands, "_enum_windows", lambda: [{"title": "Notepad"}])
    monkeypatch.setattr(hands, "_shape_window", lambda win: {"title": win["title"]})
    monkeypatch.setattr(hands, "_activate_window", lambda win: False)
    with hands.app.test_request_context("/focus", method="POST", json={"title": "note"}):
        resp = hands.focus()
    status = resp[1] if isinstance(resp, tuple) else resp.status_code
    assert status == 409
    monkeypatch.setattr(hands, "_activate_window", lambda win: True)
    with hands.app.test_request_context("/focus", method="POST", json={"title": "note"}):
        resp = hands.focus()
    body = resp.get_json() if not isinstance(resp, tuple) else resp[0].get_json()
    assert body["ok"] is True


def test_shellexecute_restype_is_pointer_sized(hands, monkeypatch):
    class Fn:
        def __init__(self):
            self.restype = None

        def __call__(self, *args):
            self.args = args
            return 40

    fn = Fn()
    monkeypatch.setattr(hands.os, "name", "nt")
    monkeypatch.setattr(
        hands.ctypes, "windll", type("W", (), {"shell32": type("S", (), {"ShellExecuteW": fn})()})()
    )
    assert hands._run_elevated({"exe": "notepad.exe", "args": ""}) is True
    assert fn.restype is hands.ctypes.c_void_p


def test_elevation_log_is_resulting_state(packaged, monkeypatch):
    # R9 (#23): the request is shown in the web window; only the
    # window's decision (resolve_elevation) reaches the hands resolver,
    # and the log line reports the RESULTING state, not the click.
    logs = []

    class Hands:
        def __init__(self):
            self._elevations = {"1": {"state": "pending"}}
            self._elevations_lock = threading.Lock()
            self.calls = []

        def _resolve_elevation(self, eid, approved):
            self.calls.append((eid, approved))
            self._elevations[eid]["state"] = "expired"
            return False

    cls = _ui_class(packaged)
    hands = Hands()
    app_obj = type("A", (), {})()
    app_obj.log_line = logs.append
    app_obj._view_lock = threading.Lock()
    app_obj._pending_elevations = {}
    app_obj._elevation_dialog_open = False
    app_obj._hands_module = hands
    app_obj._elevation_state = cls._elevation_state
    cls._handle_elevation_request(
        app_obj, hands, {"id": "1", "name": "demo", "exe": "cmd.exe", "args": "/c echo"}
    )
    assert hands.calls == []  # showing it decides nothing
    assert app_obj._elevation_dialog_open is True
    assert "1" in app_obj._pending_elevations
    assert cls.resolve_elevation(app_obj, "1", True) == "expired"
    assert hands.calls == [("1", True)]
    assert "state=expired" in logs[-1]
    assert "approved by the operator" not in logs[-1]
    assert app_obj._elevation_dialog_open is False
    assert cls.resolve_elevation(app_obj, "1", True) is None  # one decision only


def test_one_poll_in_flight_and_no_restart_while_pending(packaged):
    cls = _ui_class(packaged)
    started = []

    class T:
        def __init__(self, target, daemon=True):
            started.append(target)

        def start(self):
            return None

    obj = type("A", (), {})()
    obj._poll_running = False
    obj._poll_logged = True
    obj.token = "t"
    obj.root = type("R", (), {"after": lambda *a, **k: None})()
    obj.log_line = lambda *a: None
    obj.set_status = lambda *a: None
    # _poll re-schedules itself via self.root.after(POLL_MS, self._poll);
    # the bare fake object needs the attribute the real instance gets
    # from its class.
    obj._poll = lambda: None
    real_thread = packaged.threading.Thread
    packaged.threading.Thread = T
    try:
        cls._poll(obj)
        cls._poll(obj)
    finally:
        packaged.threading.Thread = real_thread
    assert len(started) == 1
    logs = []
    obj.log_line = logs.append
    obj.servers = {"hands": object()}
    obj._hands_module = type(
        "M", (), {"_elevations": {"1": {"state": "pending"}}, "_elevations_lock": threading.Lock()}
    )()
    obj._elevation_dialog_open = False
    health = type("H", (), {"note": lambda self, ok: "restart"})()
    obj._health = {"hands": health}
    # _note_health consults the real _skip_restart; bind it to the fake
    # object the way the class would (its getattr guards handle the rest).
    obj._skip_restart = lambda name: cls._skip_restart(obj, name)
    cls._note_health(obj, "hands", False)
    assert "hands" in obj.servers
    assert any("not restarting" in line for line in logs)


def test_captioner_does_not_trust_remote_code(parser):
    src = inspect.getsource(parser._get_captioner)
    assert "trust_remote_code" not in src


def test_predict_runs_under_infer_lock(parser, monkeypatch):
    class Rec:
        def __init__(self):
            self.depth = 0

        def __enter__(self):
            self.depth += 1

        def __exit__(self, *args):
            self.depth -= 1

    rec = Rec()
    monkeypatch.setattr(parser, "_infer_lock", rec)

    class Det:
        def predict(self, *args, **kwargs):
            assert rec.depth >= 1
            return []

    class Fake:
        size = (2, 2)

        def convert(self, mode):
            return self

    monkeypatch.setattr(parser, "_get_detector", lambda: Det())
    monkeypatch.setattr(parser, "_get_captioner", lambda: None)
    from PIL import Image

    monkeypatch.setattr(Image, "open", lambda raw: Fake())
    assert parser._run_parse(b"x") == ([], 2, 2)
