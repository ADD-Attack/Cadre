# Manual verification — gateway coordination (wishlist #15, #18)

These steps need the owner's Windows PC (a live hands process and a
real desktop the owner can touch). They are **live-unverified**: the
gateway logic is covered by `services/gateway/test_coordination.py`
with the hands link stubbed, but the end-to-end behavior below has not
been run against the real hands yet.

Setup: start the packaged app (or the services natively, per the
README quickstart) so the gateway answers on port 5010, and note the
gateway token shown in the app window. In PowerShell below, set
`$T = "<gateway token>"` and use header `X-Relay-Token: $T` on every
call (`curl.exe -H "X-Relay-Token: $T" ...`).

## Hands claim (#15)

1. Claim as session A:
   `curl.exe -X POST http://127.0.0.1:5010/v1/hands/claim -H "X-Relay-Token: $T" -H "Content-Type: application/json" -d "{\"holder\":\"session-a\",\"purpose\":\"manual check\"}"`
   Expect `200` with `"granted": true`.
2. Claim as session B (second terminal): same call with
   `"holder":"session-b"`. Expect `409` naming session-a's claim.
   Repeat with `"queue": true` added. Expect `200`, `"queued": true`,
   `"position": 1`.
3. Release as a stranger: `POST /v1/hands/release` with
   `{"holder":"session-c"}`. Expect `403`.
4. Release as session A: `{"holder":"session-a"}`. Expect `200`,
   `"released": true`.
5. Within 30 s, claim as session C. Expect `409` (reserved for the
   queue head, session-b). Then claim as session B. Expect `200`
   granted.
6. `GET http://127.0.0.1:5010/v1/hands/claim` — expect session-b's
   claim, an empty queue, `"reserved_for": null`. Also check
   `GET /v1/info` carries the same object as `"hands_claim"`.
7. Leave the claim alone past its TTL (or claim with
   `"ttl_seconds": 30` and wait ~35 s), then `GET /v1/hands/claim` —
   expect `"claim": null` (lazy expiry; nothing proactively clears it).

## Queued act (#18)

1. While nobody is touching the PC, send
   `POST http://127.0.0.1:5010/v1/act/queued` with
   `{"op":"move","x":100,"y":100}`. Expect a plain `200` hands answer
   (passthrough, no receipt), and `GET /v1/act/queued` shows no new
   receipt.
2. Have the owner actively use the desktop (moving the mouse /
   typing) and immediately send the same queued act with
   `"hold_seconds": 60` added. If the hands yield, expect `202` with a
   receipt `"id"` and `"state": "held"`.
3. Poll `GET http://127.0.0.1:5010/v1/act/queued/<id>`:
   - Owner stops touching the desktop → the retry lands and the
     receipt settles `"state": "applied"` with `"hands_status": 200`.
   - Owner keeps using the desktop past the hold deadline → the
     receipt settles `"state": "refused-yielded"`.
4. `GET /v1/act/queued/<id>` with a made-up id — expect `404` and
   `"state": "expired"`.
5. Sanity: plain `POST /v1/act` with the same body during owner use
   still returns the hands' `409` immediately (unchanged behavior, no
   receipt).
