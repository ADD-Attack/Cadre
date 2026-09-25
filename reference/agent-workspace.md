# Michael: a customized OpenClaw assistant

This is a profile of **one particular OpenClaw deployment**: Michael, a persistent assistant configured to help its operator run a multi-agent team and keep projects moving. It is here because the Cadre repository is the public home available for this example—not because Michael is a Cadre role or because every OpenClaw agent behaves this way.

## Not just a character prompt

An OpenClaw model supplies the language and reasoning. The assistant people experience is the combination of that model with its role instructions, persistent workspace, tools, integrations, runtime permissions, and the operator's decisions. Michael's `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, and `AUTONOMY.md` give him a distinct role and working style; memory and operational records let him carry context forward. The deployed tools and permissions determine what he can actually do.

That combination is what makes this instance different from a newly created, minimally configured OpenClaw agent. The difference is **deployment-specific configuration and accumulated operating practice**, not a special capability guaranteed by a model name or by Cadre itself.

## What Michael does

- **Runs the operation, not just one project.** He tracks agent health, work routing, schedules, budgets, and operational issues across the deployment. He delegates sustained specialist work and stays available to the operator for steering and decisions.
- **Turns goals into coordinated delivery.** He can break a broad request into sequenced work, assign it through specialist agents, keep check-ins active, and bring evidence back to the operator. For a game project, for example, that can mean coordinating design, implementation, independent QA, and deployment rather than stopping at a plan.
- **Works with real artifacts and tools.** When configured, he can inspect and edit files, run commands, research current information, coordinate agents, and use approved integrations. He can check a built artifact or a served release instead of treating a status message as proof.
- **Keeps continuity in readable records.** Durable preferences, decisions, project state, and lessons can be recorded in workspace files so a later session can resume without pretending to remember what it cannot see.
- **Uses initiative inside explicit limits.** Routine, safe, reversible work can be completed and reported without asking for a ceremonial approval. High-impact, irreversible, externally visible, or operator-owned decisions remain at the human boundary unless the operator has already established a clear policy for them.
- **Can turn a verified failure into a better procedure.** When an incident exposes a repeatable process defect, he can document the lesson and update the relevant runbook so the next session has something better than a vague recollection.

## How the files shape him

These names describe the kinds of records used in this deployment; they are not a public dump of Michael's private instructions or memory.

- **`AGENTS.md`** defines the administrator role, workflow, boundaries, and local operating rules.
- **`SOUL.md`** sets his voice: direct, warm, resourceful, willing to push back, and not a sycophant.
- **`IDENTITY.md`** records who he is and the scope of his role.
- **`AUTONOMY.md`** explains when he should act, report, or stop for a real human decision.
- **Memory and project records** preserve selected durable context and the current state of work.

The files make the behavior legible and consistent; they do **not** grant authority. Runtime policy, tool permissions, approval gates, budget controls, and the operator's actual authorization are the hard boundaries. Michael must not treat an instruction file as permission to bypass a tool denial or enlarge his own access.

## What this is—and is not

Michael's setup is a concrete example of a deeply configured personal agent working alongside a Cadre team. It is not the Cadre installer, not a template that should be copied verbatim, and not a promise that a fresh OpenClaw install will have the same tools, access, memory, or autonomy. A safe adaptation starts with the operator's own goals and grants capabilities deliberately.

Nor is “autonomous” the same as “always right” or “unobserved.” Michael can misunderstand a request, misread state, or make a bad claim. The standard he is meant to meet is to inspect evidence, distinguish verified facts from assumptions, correct errors plainly, and leave consequential choices with the operator.

> **The aim:** a capable assistant that takes useful work off the operator's plate, remembers the right things, coordinates specialists, and stays accountable for what it did.
