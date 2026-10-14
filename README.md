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

- Gateway: http://127.0.0.1:5010/health — agent API under /v1 (screen, act, parse, info)
- Parser: http://127.0.0.1:5011/health — reports whether the model is loaded

The parser answers /parse only once OmniParser v2 weights are in its
models directory (`python services/parser/fetch_weights.py`, heavy deps in
`services/parser/requirements-model.txt`). Until then it returns 501 —
deliberately: a driver must never mistake "no model" for "empty screen".

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
