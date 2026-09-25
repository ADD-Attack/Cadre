# Model routing policy — template

Use this file to make quota-triggered model changes explicit. Replace the example values, confirm
that each route is available in your runtime, and keep this policy beside the automation that
implements it.

## Policy

```yaml
normal_model: <provider/model>
alternate_model: <provider/model>
threshold_percent_remaining: 15
trigger_windows: [<provider-window>]
managed_agents: [<agent-id>, <agent-id>]
excluded_agents: [<agent-id>]
include_global_defaults: true
include_subagent_defaults: true
include_live_sessions: true
include_active_child_sessions: true
include_completed_sessions: false
```

The threshold and windows above are examples. Name the exact provider meter and windows; if a window
is missing or cannot be parsed, treat its value as unknown and make no route transition. Never turn an
unreadable meter into `0%`.

## Transition contract

1. Read and record every selected meter's remaining percentage and reset countdown from its source of
   truth.
2. When a selected window is below the configured threshold, record that window's absolute reset
   boundary. If multiple windows trigger, keep independent latches; do not slide a boundary forward
   on each poll.
3. Probe the alternate model through the same runtime and authentication path used by the managed
   agents. Require a successful real turn, the expected routed model, and an expected reply.
4. Change only the declared configuration scope, preserving cross-provider fallbacks. Then reconcile
   pinned live sessions and active child sessions recursively if those are in scope.
5. Remain on the alternate route until every triggering reset boundary has passed and the selected
   meters have recovered to the threshold.
6. Probe the normal model by the same criteria before restoring it. If either probe fails, leave the
   current route in place and record `BLOCKED`.

## Session and evidence rules

Configured defaults do not necessarily change existing session pins. Record the expected session scope,
including channels and active descendants; patch only that scope using supported session controls;
then re-list and verify each session. Leave completed/history-only sessions unchanged unless explicitly
included. Report `checked / expected` and list exceptions. A config write alone is not proof of a fleet
transition.

Keep a timestamped decision log and a small state file containing the current route, each reset latch,
and any pending session sweep. A scheduled controller should be idempotent, fail closed on missing
data, and report only actual transitions or blocks—not every unchanged poll. Do not let this routing
policy silently change provider credentials, authentication order, or agent exclusions.

See [`../../reference/usage-management.md`](../../reference/usage-management.md) for the complete
workflow and [`../../reference/budgets.md`](../../reference/budgets.md) for spend envelopes and
accounting.
