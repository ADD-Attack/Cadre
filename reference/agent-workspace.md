# Inside a Cadre Agent Workspace

Cadre agents are shaped by a small set of readable files, plus the OpenClaw runtime that hosts them. The files provide role, continuity, and team conventions; they are not a substitute for runtime permissions, tool policy, or operator oversight.

## The core files

| File | What it contributes |
|---|---|
| `AGENTS.md` | The agent's role, place in the workflow, authority, working rules, hand-offs, and links to team conventions. Think of it as the role charter and operating manual. |
| `SOUL.md` | Voice and disposition: how the agent should communicate and approach its work. It personalizes behavior without changing the agent's assigned authority. |
| `IDENTITY.md` | Stable identity facts such as name, official role, team, model class, reporting line, and workspace. |
| `USER.md` | Operator preferences and standing context that the operator has chosen to share with that agent. |
| `MEMORY.md` | Curated long-term continuity: durable facts and decisions that should survive across sessions. It is separate from the live task record. |
| `BUDGET.md` | The agent's budget envelope and accounting policy. Platform usage data—not an agent's guess about its own tokens—is the source of truth for actual spend. |

The install templates live in [`templates/agent-workspace/`](../templates/agent-workspace/). The Cadre Wizard fills in role- and operator-specific details; these are templates, not universal prompts to copy unchanged.

## Team and project context

An agent also reads shared team conventions and the current project record. The team directory describes who exists, their roles, and reporting lines. Project files describe the goal, acceptance criteria, decisions, task ownership, and current status. This lets a persistent agent resume work without treating a past chat as the only record.

Cadre distinguishes **persistent worker seats** from **spawned subagents**. A worker is a continuing team member with its own identity and accumulated context. A subagent is a temporary, bounded helper for a piece of work; it does not replace the worker seat or become a new permanent role.

## Autonomy: initiative with boundaries

Cadre separates two questions:

- The **autonomy ladder** describes how much responsibility an operator has delegated to a role as trust is earned. See [`autonomy-ladder.md`](./autonomy-ladder.md).
- The **act-versus-ask contract** describes how an agent handles an individual decision. See [`autonomy.md`](./autonomy.md).

The short version is: agents should complete work that is safe, reversible, within their authority, and understood—then report what they did. They stop and escalate for consequential decisions reserved to the operator, destructive or irreversible actions, externally visible actions outside an approved workflow, or genuine information blockers. They must not treat autonomy as permission to bypass a denial or enlarge their own authority.

This is more than a personality prompt, but the Markdown files alone do not enforce every boundary. OpenClaw's runtime permissions, tool policy, budget controls, approval gates, and the operator's configuration provide the hard limits. Prompts explain how to work inside those limits; they cannot grant themselves new capabilities.

## Why this differs from a one-shot chatbot

A Cadre agent is a persistent role in a coordinated team, not just a fresh conversation with a character prompt. It has a defined responsibility, durable workspace, explicit hand-off relationships, and human-readable continuity. The project manager coordinates execution; builders produce artifacts; QA verifies independently; and support roles contribute within their charter. The operator remains the source of authority for decisions that have not been delegated.

The design goal is **bounded initiative**: less repetitive prompting for routine work, with evidence, ownership, and escalation still visible to the operator.

## Keep private context private

Workspace files are ordinary text and may be shared, reviewed, or committed. Only put information there that belongs in that workspace. Personal assistant memory, credentials, private conversations, and deployment-specific secrets should not be copied into a public Cadre repository or a shared project workspace.
