# Autonomy resources

The practical starting point is [`examples/michael-scott/AUTONOMY.md`](../examples/michael-scott/AUTONOMY.md): a complete, self-contained public adaptation of the policy used by Michael Scott, one customized OpenClaw assistant. It is intended to be copied and adapted, not pasted blindly. Private operator quotes, incident narratives, host paths, and deployment-specific security procedures were intentionally left out.

Related Cadre references explain the surrounding system:

- [`autonomy-ladder.md`](./autonomy-ladder.md) — how much responsibility the operator delegates to each role.
- [`guardrails.md`](./guardrails.md) — practical mechanisms for routing, file ownership, QA limits, and inexpensive checks.
- [`collaboration.md`](./collaboration.md) — delegation, messaging, hand-offs, and follow-through.
- [`memory.md`](./memory.md) — continuity across sessions.
- [`scheduled-work.md`](./scheduled-work.md) — recurring tasks, wakeups, and cost control.
- [`../templates/agent-workspace/AGENTS.md`](../templates/agent-workspace/AGENTS.md) — role and authority instructions that complement the autonomy file.
- [`../templates/agent-workspace/SOUL.md`](../templates/agent-workspace/SOUL.md) — persona and communication style.

**Important:** `AUTONOMY.md` describes intended behavior; it does not grant tools or enforce security. Put hard limits in the runtime's permissions, approvals, budget controls, and other enforcement mechanisms. Adapt each procedure to mechanisms that really exist in your own deployment.
