# Reference — provider usage management

How to give a persistent agent team predictable usage, quota-aware model routing, and honest status
reports. This is an implementation pattern to adapt to your providers and runtime—not a ready-made
quota switcher or a spend guarantee.

## Downloadable starting points

These are adaptable examples, not drop-in configuration. Review the policy, replace the example
agents and models, and validate the status parser and route probe for your installation before
enabling writes. The script defaults to dry-run mode (`APPLY=0`); it may still send a harmless real
model probe when a transition is due, but it will not write routing configuration.

- [Model-routing policy template](../examples/usage-management/MODEL-ROUTING.md) · [raw download](https://raw.githubusercontent.com/ADD-Attack/Cadre/main/examples/usage-management/MODEL-ROUTING.md)
- [Quota-routing script template](../examples/usage-management/token-balance.sh) · [raw download](https://raw.githubusercontent.com/ADD-Attack/Cadre/main/examples/usage-management/token-balance.sh)

## Keep three signals separate

- **Provider quota/headroom:** how much of a provider's time-window allowance remains, and when that
  window resets. One provider may expose several windows (for example, a short rolling window and a
  weekly window).
- **Route health:** whether the exact model, account, and runtime can complete a real request now.
  Quota remaining does not prove authentication or route health.
- **Spend:** money or tokens attributable to your deployment. This is not the same as provider
  headroom. OpenClaw model fallbacks are generally error-based, not a spend cap; check what your
  billing source and runtime actually expose. For team envelopes and spend accounting, see
  [`budgets.md`](./budgets.md).

Decide which signal is authoritative for each action. Do not treat a quota percentage as spend, or a
successful catalog lookup as proof that a model can serve a turn.

## Write the policy before automating it

Record these choices in one place:

1. **Normal and alternate routes:** exact provider/model/runtime pairs, including the authentication
   mechanism each route uses.
2. **Meter and trigger:** the provider's source of truth, the threshold, and exactly which window or
   windows trigger a change. A deployment may use only a short window or combine short and weekly
   windows; that is an operator policy choice, not an assumption to leave implicit.
3. **Managed scope:** agent IDs, global and subagent defaults, whether existing sessions are included,
   and explicit exclusions. Do not infer scope from a display name or a partial roster.
4. **Recovery rule:** which reset(s) must pass, what headroom must recover to, and what live test must
   succeed before returning to the normal route.
5. **Unknown and failure behavior:** what to do when a meter is missing, malformed, stale, or a route
   probe fails. Prefer a visible `SKIP`/`BLOCKED` state over an invented zero or a claimed transition.

For example, one deployment might use a 15%-remaining threshold and move a defined group from a normal
OpenAI route to a Claude route. Treat that number and provider pair as example policy, not a universal
recommendation; set the trigger windows and scope explicitly for your own account.

## Use a small state machine

| State | Condition | Action |
| --- | --- | --- |
| Normal | Required meter is readable; no selected window is below threshold | Keep the normal route; log the reading and reset time. |
| Failover candidate | A selected window is below threshold | Record that window's reset boundary; test the alternate route with a real turn. |
| On alternate | Alternate route passed and the scoped config/session transition completed | Stay on the alternate route through the recorded reset boundary. |
| Recovery candidate | Every triggering window has reset and required readings have recovered | Test the normal route with a real turn; restore only after it passes. |
| Unknown or blocked | Required usage data is missing/unparseable, or the target route test fails | Make no new transition; log `SKIP` or `BLOCKED` with the reason. |

If you monitor more than one window, keep a separate reset latch for each window that triggered a
failover. Preserve its first observed reset boundary rather than moving it forward on every poll. Clear
that latch only after the recorded reset has passed and that meter has recovered. Restore the normal
route only after all triggering latches clear and the normal route passes its probe.

## Prove the route, not just the meter

Before changing the fleet, send a harmless probe through the same OpenClaw runtime and authentication
path that the managed agents will use. Check all of the following:

- the call completed successfully;
- the actual routed model/provider matches the intended target; and
- the response matches a known probe value.

Use a dedicated disposable probe session, not a user's conversation or a production task. A quota
number, provider status page, configured model name, or catalog entry alone is not a liveness test.
Keep credentials out of the probe text and logs.

## Move configuration and sessions together

Changing defaults does not necessarily change existing conversations: a session can retain a pinned
model. For a declared transition:

1. Apply the configuration update as one scoped batch: global defaults, subagent defaults, and the
   named agent entries. Preserve working cross-provider fallbacks.
2. Inventory the existing live/continuable sessions in scope, including user-facing channel sessions
   and active child/subagent sessions recursively. Apply the target to those session pins using the
   runtime's supported session control.
3. Leave completed, history-only sessions unchanged unless the operator explicitly includes them.
4. Re-list and verify every expected session. Report `checked / expected` and enumerate exceptions;
   do not claim a fleet-wide migration from a config write alone.

Keep explicit exclusions out of both the config batch and the session sweep. A session sweep is a
separate part of the transition, not an optional inference from changed defaults.

## Run it predictably

- Put quota sampling and state transitions in a deterministic host scheduler or gateway-level
  controller—not a model turn that wakes hourly just to poll.
- Start in dry-run mode. Compare parsed readings with the provider's displayed values; verify reset
  parsing, threshold comparisons, state persistence, and failure behavior before enabling writes.
- Keep the controller idempotent: unchanged settings should not be rewritten on each poll. Log each
  decision, probe result, config result, reset latch, and session-sweep result with timestamps.
- Notify the operator on actual transitions or blocked transitions, not on every unchanged poll.
- Give the scheduled job only the capabilities required to perform its declared work. Inspect the
  scheduler's effective tool scope rather than assuming it is minimal by default.
- Keep an operator-readable state record and document how to disable or manually recover the
  controller without deleting its audit history.

## Report usage honestly

When asked for status, quote the provider's reported percentages and reset countdowns exactly. Label
which provider and window each number belongs to. Say when a value is unavailable; do not substitute
another provider's balance, infer historical usage without a snapshot, or present a threshold policy as
a hard spend cap.

The detailed budget concepts and Finance Manager workflow are in [`budgets.md`](./budgets.md). The
reusable autonomy contract for carrying out authorized operations and reporting real blockers is in
[`autonomy.md`](./autonomy.md).
