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

```
cd hands
build_muse_relay.bat   :: builds "Muse Relay.exe" (v1 hands, carried forward)
```

The v1 hands app is carried into `hands/` unchanged as the starting point:
per-session generated secret, constant-time compare, lockout with phone
alerts (ntfy), Waitress, Tailscale Serve preferred over any public tunnel,
no public URL at all when Tailscale is present.

## Security model

- Nothing listens publicly by default. Preferred transport is Tailscale
  Serve (tailnet-only); a public tunnel is a fallback, never the design.
- The session secret is generated fresh on every launch (~190 bits) and
  destroyed on close. There is no stored credential to leak.
- Failed auth attempts are logged; 10 in 10 minutes pauses auth for
  5 minutes and pushes a phone alert.
- Design rule inherited from v1's audit: the URL is obscurity, not a
  control — the secret and the transport are the controls.

MIT © 2026 Christopher Moore
