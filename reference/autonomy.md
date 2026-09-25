# Autonomy resources

The practical starting point is [`examples/michael-scott/AUTONOMY.md`](../examples/michael-scott/AUTONOMY.md): a complete, self-contained public adaptation of the policy used by Michael Scott, one customized OpenClaw assistant. It is intended to be copied and adapted by self-hosters who want less needless babysitting, not pasted blindly. It distinguishes functional administrator work from changes to safety controls, and explains why prompts cannot override tool, channel, credential, or host restrictions. Private operator quotes, incident narratives, host paths, and deployment-specific security procedures were intentionally left out.

**Get the actual Markdown file:** [open the file on GitHub](../examples/michael-scott/AUTONOMY.md) or [download/view the raw `AUTONOMY.md`](https://raw.githubusercontent.com/ADD-Attack/Cadre/main/examples/michael-scott/AUTONOMY.md).

To adopt it, copy it into the agent workspace as `AUTONOMY.md`, add a pointer in that agent's `AGENTS.md` and `SOUL.md`, and ensure the runtime actually loads those files each session. A repository link alone does none of those steps.

Suggested request to an agent:

> Read Michael Scott's `AUTONOMY.md` at <https://github.com/ADD-Attack/Cadre/blob/main/examples/michael-scott/AUTONOMY.md>. Explain which behavior rules fit my deployment, and identify the actual tools or runtime settings needed for any requested capability. Do not claim a prompt grants access, do not bypass denials, and do not handle credentials in chat. If you have authorized workspace access, help me adapt and install the file, then verify that `AGENTS.md` and `SOUL.md` point to it and that it is loaded.

Related Cadre references explain the surrounding system:

- [`autonomy-ladder.md`](./autonomy-ladder.md) — how much responsibility the operator delegates to each role.
- [`guardrails.md`](./guardrails.md) — practical mechanisms for routing, file ownership, QA limits, and inexpensive checks.
- [`collaboration.md`](./collaboration.md) — delegation, messaging, hand-offs, and follow-through.
- [`memory.md`](./memory.md) — continuity across sessions.
- [`scheduled-work.md`](./scheduled-work.md) — recurring tasks, wakeups, and cost control.
- [`../templates/agent-workspace/AGENTS.md`](../templates/agent-workspace/AGENTS.md) — role and authority instructions that complement the autonomy file.
- [`../templates/agent-workspace/SOUL.md`](../templates/agent-workspace/SOUL.md) — persona and communication style.

**Important:** `AUTONOMY.md` describes intended behavior; it does not grant tools or enforce security. Put hard limits in the runtime's permissions, approvals, budget controls, and other enforcement mechanisms. Adapt each procedure to mechanisms that really exist in your own deployment.
