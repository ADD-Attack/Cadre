# Muse Relay v2

Let a personal AI agent operate a Windows PC — screenshots,
mouse, keyboard — with a security posture designed for leaving it reachable
while the owner is away from home.

v2 is a rebuild of the single-file Muse Relay around three parts:

| Part | Runs where | What it does |
| --- | --- | --- |
| **hands** | Windows host, native (never in Docker) | The desktop driver: screenshot, mouse, keyboard, window control. A container has no interactive Windows desktop session, so the hands must live on the host — the same constraint every desktop agent (UFO², OmniTool) runs into. |
| **gateway** | Docker | The agent-facing API: per-session secret auth, failed-guess lockout, request routing to the hands, audit log. This is the only surface the agent talks to. |
| **parser** | Docker (GPU optional) | Screen parsing (OmniParser-class): screenshot in → labeled, numbered UI elements out, for surfaces with no DOM and no UI Automation tree (games, canvas, custom UI). Optional component; the relay works without it. |

Roadmap (what we're stealing from browser-use, UFO², and OmniParser, and in
what order): [docs/ROADMAP.md](docs/ROADMAP.md).

## Quickstart (services)

```
cp .env.example .env
docker compose up --build
```

- Gateway: http://127.0.0.1:5010/health
- Parser: http://127.0.0.1:5011/health

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
