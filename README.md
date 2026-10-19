# Muse Relay v2

Let a personal AI agent operate a Windows PC — screenshots,
mouse, keyboard — with a security posture designed for leaving it reachable
while the owner is away from home.

v2 is a rebuild of the single-file Muse Relay around three parts:

| Part | Runs where | What it does |
| --- | --- | --- |
| **hands** | Windows host, native (never in Docker) | The desktop driver: screenshot, mouse, keyboard, window control. A container has no interactive Windows desktop session, so the hands must live on the host — the same constraint every desktop agent (UFO², OmniTool) runs into. |
| **gateway** | Docker or native Python | The agent-facing API: token auth, failed-guess lockout, routing of screen/action calls to the hands and parse calls to the parser. This is the only surface the agent talks to. |
| **parser** | Docker or native Python (GPU optional) | Screen parsing (OmniParser-class): screenshot in → labeled, numbered UI elements out, for surfaces with no DOM and no UI Automation tree (games, canvas, custom UI). Optional component; the relay works without it. |

Roadmap (what we're stealing from browser-use, UFO², and OmniParser, and in
what order): [docs/ROADMAP.md](docs/ROADMAP.md).

## Packaged app (Windows) — the normal way to run it

One icon, one button. Build once:

```
build_app.bat   :: builds "Muse Relay v2.exe"
```

Then just double-click **Muse Relay v2.exe** and press **Start**. The one
window runs all three parts in-process — hands on 127.0.0.1:5000, gateway on
:5010, parser on :5011 — with a status line for each. **Stop** (or closing the
window) stops everything. No other app is needed: the v1 relay is retired,
and the hands run headless inside this app (no separate window, no tunnel —
the gateway is the only surface an agent talks to).

Secrets in the packaged app:

- The **gateway token** is minted fresh every launch and shown in the window
  with a Copy button. It is never saved anywhere.
- The **hands secret** is owned by the app and persists per machine at
  `%USERPROFILE%\.muse-relay-v2\hands-secret.txt` — generated on first run,
  reused after that (delete the file to rotate it). The app feeds the same
  value to the gateway and the hands, so the two can never disagree about
  it the way the old two-app setup could.

## Quickstart (services)

Docker is an option, never a requirement — both services are plain
Python and run natively just as well.

With Docker:

```
cp .env.example .env
docker compose up --build
```

Native (PowerShell, on the Windows PC itself):

```
cd services\parser;  pip install -r requirements.txt;  python app.py
cd services\gateway; pip install -r requirements.txt
$env:RELAY_GATEWAY_TOKEN = "<long random token>"
$env:HANDS_URL    = "http://127.0.0.1:5000"
$env:HANDS_SECRET = "<the hands app's current session secret>"
$env:PARSER_URL   = "http://127.0.0.1:5011"
python app.py
```

- Gateway: http://127.0.0.1:5010/health — agent API under /v1 (screen, screen/hash, act, act/queued, hands/claim, hands/release, parse, info, filedrop, wait)
- Parser: http://127.0.0.1:5011/health — reports whether the model is loaded

**Change detection without the pixels:** `GET /v1/screen/hash` returns a
SHA-256 of the current frame's pixels with the bottom `mask_bottom` px
(default 80 — the taskbar) excluded, so a watcher can poll a tiny JSON
response and only fetch the full PNG when the hash changes. With
`?stable=1` the gateway samples two frames ~0.65 s apart and hashes
their per-pixel minimum, so a blinking caret or spinner phase cannot
flip the result. `/v1/screen` also carries that hash as an `ETag` and
answers a matching `If-None-Match` with `304`. If the gateway lacks
Pillow, the hash route returns 501 and `/v1/screen` serves without an
ETag — never a wrong hash.

The parser answers /parse only once OmniParser v2 weights are in its
models directory (`python services/parser/fetch_weights.py`, heavy deps in
`services/parser/requirements-model.txt`). Until then it returns 501 —
deliberately: a driver must never mistake "no model" for "empty screen".

## Coordination: hands claim + queued act

Two gateway features keep multiple agent sessions (and the owner) from
fighting over one desktop. Both are covered by the gateway token, like
every other /v1 route.

**Hands claim (advisory).** A session that is about to drive takes a
claim first so other sessions can see who holds the desktop:

- `POST /v1/hands/claim` `{"holder", "purpose", "ttl_seconds"?, "queue"?}` —
  grants when free (`200 {"granted": true, "claim": {...}}`); the same
  holder re-claiming refreshes the lease. TTL defaults to 900 s, clamped
  30–3600 s; expiry is lazy (an expired claim is simply absent). If
  another holder holds it: `409` with the current claim — or, with
  `"queue": true`, a FIFO queue slot (`200 {"granted": false, "queued":
  true, "position": N}`).
- When a claim is released or expires, the queue head gets a 30 s
  reservation: only that holder's claim can be granted during the grace
  window; everyone else still gets `409` / a queue slot.
- `POST /v1/hands/release` `{"holder"}` — only the current holder can
  release (`403` otherwise; releasing an expired claim is an ok no-op).
  `{"holder", "cancel_queue": true}` instead drops that holder's queue
  entry.
- `GET /v1/hands/claim` — `{"claim": {...}|null, "queue": [...],
  "reserved_for": holder|null}`. `GET /v1/info` carries the same claim
  object as `hands_claim`.

The claim is **advisory coordination only — it does not gate
`/v1/act`**. A session that skips claiming can still act; well-behaved
sessions check the claim first and back off politely.

**Queued act (yielded-input accounting).** When the owner is actively
using the desktop, the hands answer an act with `409` (the act yielded).
Plain `POST /v1/act` surfaces that as-is and is unchanged.
`POST /v1/act/queued` takes the same body plus optional `hold_seconds`
(default 30, clamped 1–120):

- Any result other than a yield-`409` is returned exactly as `/v1/act`
  would return it — no receipt is filed.
- A yield-`409` (error mentions "yield" / "user active") files a
  receipt and answers `202 {"queued": true, "id": ..., "state":
  "held"}`. A retry thread re-forwards the act about once a second
  until the deadline: a non-`409` answer settles the receipt `applied`,
  still-`409` at the deadline settles it `refused-yielded`, and an
  unreachable hands settles it `failed`.
- `GET /v1/act/queued/<id>` returns the receipt; an unknown or evicted
  id answers `404` with `"state": "expired"`. `GET /v1/act/queued`
  lists receipt summaries (`id`, `op`, `state`, `submitted_at`), newest
  first. At most 200 receipts are kept.
- A receipt records the op and the payload's **key names only — never
  payload values** (typed text may be sensitive). The payload itself is
  held in memory only while the receipt is held and dropped when it
  settles.

**File-drop (gateway):** `POST /v1/filedrop` with
`{"folder", "filename", "data_b64", "sha256"?}` drops one file onto the
PC in a single call. The gateway computes the SHA-256 itself when it is
not supplied, verifies it against a supplied one before sending anything
(a mismatch is a 400), then runs the hands' chunked upload protocol
(256 KB raw chunks) and returns `{"ok", "path", "size", "sha256"}`.
Any hands error is surfaced with its status. On the hands side the
protocol is `POST /filedrop/begin` (returns an `upload_id` and
`chunk_max` 524288), `POST /filedrop/chunk` (strictly sequential
offsets; a wrong offset is a 409 carrying the expected offset),
`POST /filedrop/commit` (verifies size and SHA-256, then writes via a
temp file + atomic replace in the target folder), and
`POST /filedrop/abort`. Uploads are capped at 16 MB and expire after
10 minutes. Drops only land in allowlisted folders: the hands config
file key `"filedrop_dirs"` (a list of absolute paths), or the
`HANDS_FILEDROP_DIRS` environment variable (`os.pathsep`-separated,
which wins when set). With no allowlist configured, every filedrop
endpoint returns 501. Filenames must be bare names — no path separators
or `..`.

**Wait-for (gateway):** `POST /v1/wait` with
`{"condition": {...}, "timeout_seconds": 30, "poll_seconds": 1}` polls
until a condition holds or the deadline passes, returning
`{"ok": true, "held": true, "waited_seconds": ..., "condition": ...}`
or, on deadline, `{"ok": true, "held": false, "timeout": true, ...}`.
`timeout_seconds` clamps to 1–300 and `poll_seconds` to 0.2–10; an
unknown condition type is a 400 immediately. Condition types:
`{"type": "screen_hash_change", "stable": bool?}` (the masked frame
hash — see `/v1/screen/hash` — differs from the starting sample; 501 if
the gateway lacks Pillow), `{"type": "screen_region_change",
"region": [x, y, w, h]}` (only that region's pixels, clamped to the
frame, change), `{"type": "window_title", "contains": "..."}` (a
window title contains the text, via the hands' `GET /window_titles`;
if the hands answers 404/501 the wait returns
`{"ok": false, "error": "hands does not support window titles"}`
immediately instead of burning the timeout), and
`{"type": "parser_model_loaded"}` (the parser's `/health` reports
`model_loaded` true).

**PC lock/sleep state:** the hands' `GET /state` returns
`{"ok": true, "platform": "windows"|"other", "locked": true|false|null,
"idle_seconds": number|null}` — on Windows the lock state comes from
the input desktop (`Winlogon` means locked) and idle time from the
last-input timestamp; off Windows, or on any probe failure, the values
are `null` (never a 500). The hands also expose `GET /window_titles`
(`{"ok": true, "titles": [...]}`). The gateway's `GET /v1/info` now
carries a `"pc_state"` field with the hands' `/state` payload, fetched
inside the same 5-second-cached reachability probe as the other info
fields; it is `null` when the hands is unreachable or `/state` errors,
and all existing `/v1/info` fields are unchanged.
## Actuation (v3 P4 — wishlist #3, #4, #6, #9, #19)

New hands routes, all behind the same X-Secret gate as the existing
routes (and, through the gateway, the same X-Relay-Token gate):

| Hands route | Gateway surface | What it does |
| --- | --- | --- |
| `POST /hotkey {keys: ["ctrl", "l"]}` | act op `hotkey` | Press a true key chord via `pyautogui.hotkey()`. |
| `POST /break {times?: 1..3}` | act op `break` | Ctrl+C chord(s), 0.15 s apart. |
| `POST /drag {x1, y1, x2, y2, button?, duration?}` | act op `drag` | Mouse-down at the start point, move, mouse-up at the end point. |
| `GET /windows` | `GET /v1/windows` | Open windows: title, process, pid, bounds, monitor index, visible, focused. Off Windows it returns an empty list with `"supported": false`. |
| `POST /focus {title, exact?}` | act op `focus` | Focus the first window whose title matches (substring, case-insensitive; full-title when `exact` is true); restores a minimised window first. No match → 404. |
| `POST /clipboard/set {text}` | act op `clipboard_set` | Set the clipboard (Windows: ctypes `CF_UNICODETEXT`; else pyperclip when importable; otherwise 501). |
| `GET /clipboard/get` | `GET /v1/clipboard` | Read the clipboard (same backends, same 501 when unavailable). |

**Clipboard read is sensitive.** It stays behind the same authentication
as every other hands/gateway route, and *every read writes a line to the
hands log queue* (`clipboard read via relay`), so the owner sees reads
in the app window as they happen.

**Why `/break` exists:** the older `/key` op calls `pyautogui.press()`
with ONE key name, so a chord string like `"ctrl+c"` sent to `/key` was
never a real chord — nothing was interrupted. `/break` and `/hotkey`
send true chords via `pyautogui.hotkey()`, so the interrupt lands.

**Fast `/type`:** `POST /type` now also accepts
`{method: "auto"|"paste"|"keys"}` (absent = the old behaviour for short
text). In `auto`, text over 120 chars goes through the clipboard when a
backend exists: the current clipboard is saved, replaced with the text,
pasted with Ctrl+V, then restored. Any clipboard failure falls back to
keystrokes rather than failing, and the response reports what happened:
`{"ok": true, "method_used": "paste"|"keys", "chars": n,
"elapsed_seconds": x}`. On the gateway, the act timeout for `type` is
sized to the payload — `max(30, min(600, 15 + len(text)/6))` seconds,
since the keystroke path runs at worst ~6 chars/s — while every other
op keeps the flat 30 s.

## Hands (Windows)

The hands run **inside the packaged app** (above) — same Flask routes from
`hands/muse_relay_hands.py`, served headless on 127.0.0.1:5000 by the app
process, with the app-owned persistent secret described above.

For a split deployment (services run separately, e.g. under Docker), the
standalone hands app is still available:

```
cd hands
build_muse_relay.bat   :: builds "Muse Relay.exe" (v1 hands, carried forward)
```

Standalone, the hands app works as it always did: per-session generated
secret shown in its window, constant-time compare, lockout with phone
alerts (ntfy), Waitress, Tailscale Serve preferred over any public tunnel,
no public URL at all when Tailscale is present. In that mode you copy its
session secret into the gateway's `HANDS_SECRET` yourself.

## Security model

- Nothing listens publicly by default. Preferred transport is Tailscale
  Serve (tailnet-only); a public tunnel is a fallback, never the design.
- The gateway token is generated fresh on every launch and destroyed on
  close. The hands secret in the packaged app is the one stored credential:
  app-owned, kept in the user's profile (`%USERPROFILE%\.muse-relay-v2\`),
  and only ever used on the localhost gateway↔hands link — it never
  crosses the network. (The standalone hands app still uses a per-session
  secret instead.)
- Failed auth attempts are logged; 10 in 10 minutes pauses auth for
  5 minutes and pushes a phone alert.
- Design rule inherited from v1's audit: the URL is obscurity, not a
  control — the secret and the transport are the controls.

MIT © 2026 Christopher Moore
