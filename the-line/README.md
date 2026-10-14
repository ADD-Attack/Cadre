# The Line

A pull-based app factory. One ticket at a time flows through four stations —
**Spec → Build → Verify → Ship** — and completion is declared by a sensor
verifying the live artifact, never by an agent saying "done."

The Line exists as a competing factory to Cadre (a 15-agent standing fleet).
Same owner, same operator, different bet: the intelligence lives in the
line's design, not in standing agents' memory. This folder is the line's
entire memory — tickets, charters, board, and receipts all live here.

Housing note (2026-10-14): The Line is chartered as its own project with its
own repo. Until a separate `the-line` repository can be created, it lives
here as a self-contained folder inside the Cadre repo — separate board,
separate tickets, separate receipts, no shared state with the fleet. It
moves out intact the day its own repo exists; nothing in its design
depends on the housing.

## Rules of the line

1. **Pull, never push.** A station takes the next ticket only when it is
   free. Nobody assigns work to a busy station.
2. **WIP = 1 per station.** At most one ticket occupies each station. The
   board (`board.md`) always shows the truth.
3. **Tickets are files.** A ticket enters as a file in `tickets/` with a
   one-paragraph order from the owner. It carries everything the line
   learns: spec, acceptance claims, build notes, verification results.
4. **Acceptance claims are the currency.** Spec writes checkable claims.
   Verify checks claims against the artifact, one by one. Nothing is
   "done" because someone says so.
5. **The sensor declares completion.** After Ship, a script (not an
   agent) independently fetches the live artifact, checks the claims'
   markers, writes a receipt to `receipts/`, and the owner is pinged.
   The sensor event *is* the completion ping.
6. **Andon on exceptions.** Any station that cannot proceed stops the
   line, writes the failing claim and evidence into the ticket, and the
   owner gets the exception. No silent retries, no improvisation around
   a failed claim. One retry after a spec fix; then the owner decides.
7. **Stations have no memory.** Each station runs as a fresh agent
   session per ticket, reading only its charter (`stations/`) and the
   ticket. What isn't in the ticket doesn't exist.
8. **Intake is the owner's.** Only Christopher (or the operator on his
   instruction) adds tickets to the queue. If the queue is empty, the
   line idles and the board says so. The line does not invent work.

## Layout

- `tickets/` — one file per order, in state order (queued → spec → build → verify → ship → done, or andon)
- `stations/` — the four station charters; these ARE the agents
- `conveyor/RUNBOOK.md` — how a ticket moves; the operator's procedure
- `conveyor/sensor.mjs` — the completion sensor
- `products/` — what the line ships (served via GitHub Pages)
- `receipts/` — one JSON receipt per shipped ticket, written by the sensor
- `board.md` — the line at a glance: which ticket sits at which station

## Placing an order

Open a ticket file (or tell the operator). One paragraph: what you want,
who it's for, what "working" looks like. The line does the rest — and
the first thing it does is argue with your paragraph until it's checkable.
