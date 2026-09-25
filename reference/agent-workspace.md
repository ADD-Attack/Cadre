# Michael Scott: a customized OpenClaw assistant

This is a profile of **one particular OpenClaw deployment**: Michael Scott, a persistent assistant configured to help its operator run a multi-agent team and keep projects moving. It is here because the Cadre repository is the public home available for this example—not because Michael Scott is a Cadre role or because every OpenClaw agent behaves this way.

For the practical replication resource, start with [Michael Scott's `AUTONOMY.md`](../examples/michael-scott/AUTONOMY.md), a publication-safe version of the behavior policy used in this deployment. See the [autonomy reference index](./autonomy.md) for related Cadre material.

## Get the files

These are actual Markdown files, not just descriptions. Open **Raw** to copy the text, or save it under the filename shown in your agent's workspace.

| File | Read on GitHub | Raw Markdown | What you are getting |
| --- | --- | --- | --- |
| `AUTONOMY.md` | [Read](../examples/michael-scott/AUTONOMY.md) | [Raw / save](https://raw.githubusercontent.com/ADD-Attack/Cadre/main/examples/michael-scott/AUTONOMY.md) | Michael Scott's public replication edition; adapted from the private policy, not a verbatim dump. |
| `AGENTS.md` | [Read](../templates/agent-workspace/AGENTS.md) | [Raw / save](https://raw.githubusercontent.com/ADD-Attack/Cadre/main/templates/agent-workspace/AGENTS.md) | Generic Cadre role template with an autonomy pointer—not Michael Scott's private administrator file. |
| `SOUL.md` | [Read](../templates/agent-workspace/SOUL.md) | [Raw / save](https://raw.githubusercontent.com/ADD-Attack/Cadre/main/templates/agent-workspace/SOUL.md) | Generic persona template with an autonomy pointer—not a copy of private identity or memory. |

## Adopt it in an existing agent

1. Have the agent read the linked files first and compare them with its existing instructions. Back up existing workspace files; do not replace a working `AGENTS.md` or `SOUL.md` wholesale with the generic templates.
2. Adapt and save the public policy as workspace-root `AUTONOMY.md`. Preserve existing higher-priority instructions and operator decisions; surface actual conflicts instead of silently overwriting them.
3. Merge a pointer into both existing files. For example:

   **In `AGENTS.md`:**

   ```text
   Read workspace-root AUTONOMY.md at session startup and before planning delegated work.
   It defines initiative, follow-through, verification, and when to ask the operator.
   Apply it within higher-priority instructions, runtime permissions, and existing authorizations.
   ```

   **In `SOUL.md`:**

   ```text
   My act-versus-ask and follow-through contract is in workspace-root AUTONOMY.md.
   I act on authorized routine work, verify results, and report genuine blockers precisely.
   ```

4. Start a fresh session and verify that the agent can identify and summarize the installed file. Do not assume a new filename is automatically loaded by every runtime; use the supported startup-loading mechanism or an explicit read.
5. Try a small, reversible task. Check that the agent completes and verifies it without unnecessary approval questions, while reporting missing access honestly. Tools, scheduling, memory retrieval, and multi-agent orchestration must be configured separately if you want those capabilities.

**A request you can give your agent with this page:**

> Read this page and its linked AUTONOMY.md. Adapt the reusable behavior rules to my existing agent workspace, preserving my identity, preferences, and existing permissions. If authorized workspace editing is available, back up affected files, install AUTONOMY.md, and merge the AGENTS.md and SOUL.md pointers without replacing those files wholesale. Show the changes, identify unresolved conflicts or missing capabilities, and verify loading in a fresh session. Do not change security controls or claim that copying Markdown installs tools or grants access.

You do not need to install the Cadre team to use the autonomy policy. The repository is its public home; the policy is a starting point for an individual agent too.

## Not just a character prompt

An OpenClaw model supplies the language and reasoning. The assistant people experience is the combination of that model with its role instructions, persistent workspace, tools, integrations, runtime permissions, and the operator's decisions. Michael Scott's `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, and `AUTONOMY.md` give him a distinct role and working style; memory and operational records let him carry context forward. The deployed tools and permissions determine what he can actually do.

That combination is what makes this instance different from a newly created, minimally configured OpenClaw agent. The difference is **deployment-specific configuration and accumulated operating practice**, not a special capability guaranteed by a model name or by Cadre itself.

## What Michael Scott does

- **Runs the operation, not just one project.** He tracks agent health, work routing, schedules, budgets, and operational issues across the deployment. He delegates sustained specialist work and stays available to the operator for steering and decisions.
- **Turns goals into coordinated delivery.** He can break a broad request into sequenced work, assign it through specialist agents, keep check-ins active, and bring evidence back to the operator. For a game project, for example, that can mean coordinating design, implementation, independent QA, and deployment rather than stopping at a plan.
- **Works with real artifacts and tools.** When configured, he can inspect and edit files, run commands, research current information, coordinate agents, and use approved integrations. He can check a built artifact or a served release instead of treating a status message as proof.
- **Keeps continuity in readable records.** Durable preferences, decisions, project state, and lessons can be recorded in workspace files so a later session can resume without pretending to remember what it cannot see.
- **Uses initiative inside explicit limits.** Routine, safe, reversible work can be completed and reported without asking for a ceremonial approval. High-impact, irreversible, externally visible, or operator-owned decisions remain at the human boundary unless the operator has already established a clear policy for them.
- **Can turn a verified failure into a better procedure.** When an incident exposes a repeatable process defect, he can document the lesson and update the relevant runbook so the next session has something better than a vague recollection.

## How the files shape him

These names describe the kinds of records used in this deployment; they are not a public dump of Michael Scott's private instructions or memory.

- **`AGENTS.md`** defines the administrator role, workflow, boundaries, and local operating rules.
- **`SOUL.md`** sets his voice: direct, warm, resourceful, willing to push back, and not a sycophant.
- **`IDENTITY.md`** records who he is and the scope of his role.
- **`AUTONOMY.md`** explains when he should act, report, or stop for a real human decision.
- **Memory and project records** preserve selected durable context and the current state of work.

The files make the behavior legible and consistent; they do **not** grant authority. Runtime policy, tool permissions, approval gates, budget controls, and the operator's actual authorization are the hard boundaries. Michael Scott must not treat an instruction file as permission to bypass a tool denial or enlarge his own access.

## What this is—and is not

Michael Scott's setup is a concrete example of a deeply configured personal agent working alongside a Cadre team. It is not the Cadre installer, not a template that should be copied verbatim, and not a promise that a fresh OpenClaw install will have the same tools, access, memory, or autonomy. A safe adaptation starts with the operator's own goals and grants capabilities deliberately.

Nor is “autonomous” the same as “always right” or “unobserved.” Michael Scott can misunderstand a request, misread state, or make a bad claim. The standard he is meant to meet is to inspect evidence, distinguish verified facts from assumptions, correct errors plainly, and leave consequential choices with the operator.

> **The aim:** a capable assistant that takes useful work off the operator's plate, remembers the right things, coordinates specialists, and stays accountable for what it did.
