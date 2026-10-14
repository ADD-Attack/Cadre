# Conveyor Runbook — for the operator

The conveyor is not a program the line runs by itself yet. The operator
(Muse) moves tickets, running each station as a fresh, isolated agent
session whose only inputs are the station charter and the ticket file.
That isolation is the design: a station that can't see the other
stations' reasoning can't collude with them, defer to them, or inherit
their mistakes.

## Running a ticket

1. **Check the board.** If any station is occupied, the incoming ticket
   waits in `queued`. The line never runs two tickets through a station
   at once.
2. **Spec.** Spawn a fresh session: charter `stations/spec.md` + the
   ticket. It writes the spec and acceptance claims into the ticket, or
   pulls the andon. Update `board.md`.
3. **Build.** Spawn a fresh session (a different one — never the Spec
   session): charter `stations/build.md` + the ticket. It builds into
   the working tree and records per-claim notes.
4. **Verify.** Spawn a fresh session that did not build: charter
   `stations/verify.md` + the ticket + access to the artifact. It checks
   every claim and records PASS/FAIL with evidence.
5. **Ship.** On `verify-passed`: commit + push the product files,
   confirm the live URL, then run the sensor:
   `node conveyor/sensor.mjs --ticket <id> --url <live-url> --expect <marker> [--expect <marker>...]`
   The sensor writes `receipts/<ticket-id>.json`. Sensor PASS = the
   ticket is `done` and the operator pings the owner with the receipt
   summary and live URL. That ping is the completion event. There is
   no other.
6. **Andon at any station.** Stop. The ticket file holds the failing
   claim and evidence. Ping the owner with the exception — what failed,
   what decision is needed. One rebuild retry is allowed after a spec
   fix (operator's call, recorded in the ticket); a second failure
   kills the ticket unless the owner revives it.

## Bookkeeping

- `board.md` is updated at every station change. If the board and the
  tickets disagree, the tickets win and the board gets fixed.
- Cycle times are recorded on the ticket at each state change
  (timestamps in the ticket header). The line's performance is read
  from tickets and receipts, never from anyone's recollection.
- Receipts are append-only. A re-ship after an andon writes a new
  receipt with an incremented `attempt` field; the failed sensor run
  stays on record.

## What the operator never does

- Carry a station's reasoning into another station's session.
- Override a FAIL, a sensor verdict, or an andon.
- Add tickets to the queue on anyone's word but the owner's.
- Report a ticket done before the sensor event exists.
