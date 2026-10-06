# Reference — Direct Messaging and Durable Inboxes

Cadre uses the deployment's configured OpenClaw messaging route to contact the intended recipient.
Messages go directly to the operator or teammate through configured routes.

## Delivery paths

| Path | Default | Record |
|---|---|---|
| Operator → team | Operator contacts the configured main agent or Project Manager. | Canonical project/task record for durable decisions and acceptance. |
| Agent → peer | Send directly to the intended agent/session through the supported route. | The recipient inbox may preserve a durable handoff when the deployment uses it. |
| Agent → operator | Send directly to the operator through the configured private route, or to the accountable PM when that is the designated path. | Record material decisions, blockers, and evidence in the canonical task/project artifact. |

An inbox is durable recipient-side storage, not a transport service. A saved record does not prove
that the recipient saw it. Verify admission/delivery through the configured messaging mechanism when
the tool exposes that result.

## Durable inbox convention

When a deployment uses agent workspaces with inbox directories:

- Write durable handoffs only to the intended recipient's inbox.
- Keep it concise: sender, recipient, timestamp, subject/kind, priority if useful, and actionable body.
- Store project status and acceptance evidence in the canonical task or project record; the inbox message
  is a notification or handoff pointer, not a second source of truth.
- Check the inbox at the start of a unit of work if the agent's workspace instructions require it.
- Keep private context out of shared/group channels and out of inboxes that other roles can read.

## Routing and failure handling

- Use only configured, authorized routes. A recipient's existence in the roster does not prove it can be
  messaged or spawned; those capabilities may have separate runtime allowlists.
- Distinguish message delivery from agent dispatch. Messaging an existing session is not the same as
  spawning a new run under another agent's identity.
- If a route refuses or times out, preserve the exact result, notify the accountable owner through an
  available authorized path, and do not claim the handoff was delivered.
- Do not repeat a failed send blindly. Inspect delivery state first and retry only when safe and idempotent.
- Headless agents must use a non-blocking message or durable task record for escalation; they must not
  wait on a human-input prompt that cannot reach the operator.

See collaboration.md for dispatch, claims, and verification, and guardrails.md for routing and write-safety limits.
