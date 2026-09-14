<p align="center">
  <img src="cadre-wizard.png" alt="The Cadre Wizard" width="220">
</p>

# Cadre

**A downloadable system of agents and Markdown files that turns any OpenClaw deployment into a coordinated team.**

Cadre gives you a persistent, chat-native multi-agent hierarchy: a small nucleus of specialist agents with roles, budgets, mailboxes, and a project pipeline — installed by a guided wizard and adapted to your preferences.

---

## What this is

Cadre is **not** a framework you install as a package. It is a **folder of Markdown conventions + a setup procedure** that your OpenClaw main agent reads and executes. You get:

- A **role roster** — requirements analyst, project designer, project manager, plus standing functions (security/IT, social media, finance, QA, agent resources, consultant).
- A **project pipeline** — requirements → design → plan → execution, with a Gantt chart maintained in `PROJECT.md`.
- **Mailboxes** — every agent has an `inbox/` and `outbox/`, so a team can be run from a single chat interface.
- **Budgets** — per-role spend/effort envelopes so autonomy never means runaway cost.
- **An autonomy ladder** — the operator starts doing most PM and QA work; agents take over as they prove out.

Everything is plain files. Nothing is hidden in a database you can't read.

---

## Quick start

1. **Get the files** onto the machine running OpenClaw:
   ```bash
   git clone https://github.com/ADD-Attack/Cadre.git
   ```
2. **Tell your OpenClaw main agent:**
   > Read `Cadre/README.md` and set up Cadre on this deployment.

3. **Follow the wizard.** The main agent reads this file, then creates and runs the **Cadre Wizard** (see [`WIZARD.md`](./WIZARD.md)). The wizard interviews you, confirms every choice, and only then writes anything.

That's it. The wizard does the rest.

---

## The flow

![How a project runs: wizard once, then Requirements Analyst to Project Designer to Project Manager (workers in its scope) to QA to the finished product, with support roles on call beside the line and a rework path from the finished product back to the Requirements Analyst](./diagrams/project-pipeline.svg)

```
 Operator
    │  "set up Cadre"
    ▼
 OpenClaw main agent ──reads──▶ README.md
    │
    ▼
 Cadre Wizard ──interviews──▶ you (agents, models, names, budgets, interface)

                            new product, or scope change / new feature
      ┌────────────────────────────────────────────────────────────────┐
      │                                                                │
      ▼                                                                │
 Requirements Analyst ─▶ Project Designer ─▶ Project Manager ─▶ QA / Verifier ─▶ Finished product
                                                   │
                            tasks + Gantt + worker tracking (FlowBoard)
                            workers sit in the PM's scope
```

Every project enters at the **Requirements Analyst** and moves through **Project Designer → Project Manager → QA / Verifier → finished product**. The PM owns execution: it breaks work into tasks, maintains the Gantt chart, and dispatches/tracks worker agents — **the workers sit in the PM's scope**.

**Rework.** Once something ships, two things send work back to the start: a **scope change or new feature** to what just shipped, or a **new product** entirely. Either way it re-enters at the Requirements Analyst and runs the pipeline again — never patched in mid-stream.

**Support roles ride beside the line, never on it.** Security/IT, Consultant, Social Media Manager, Finance Manager and Agent Resources attach to whichever project needs them and go quiet when it doesn't.

---

## The agents

| Agent | Owns | Default model class |
|---|---|---|
| **Project Manager** | plan, tasks, Gantt, dispatch, tracking | reasoning |
| **Requirements Analyst** | intake, clarification, scope | reasoning |
| **Project Designer** | architecture, approach, specs | reasoning |
| **Security / IT** | audit, exposure, hygiene (advises, never self-edits) | reasoning |
| **QA / Verifier** | independent verification, evidence | reasoning |
| **Social Media Manager** | external comms; can be the *doorway* agent | fast |
| **Finance Manager** | budgets, spend tracking (optional) | fast |
| **Agent Resources (AR)** | agent roster, onboarding, loadouts | fast |
| **Consultant** | second opinion, red-team, advice | reasoning |

Full charters, budgets, and authority: [`reference/agents.md`](./reference/agents.md). The wizard confirms which of these to create — you don't have to take all nine.

---

## Reference

- [`WIZARD.md`](./WIZARD.md) — the setup interview, step by step.
- [`reference/agents.md`](./reference/agents.md) — roster, charters, budgets, authority.
- [`reference/guardrails.md`](./reference/guardrails.md) — the four guardrails: routing limit, file-claim lease, promotion gate, no-op detector.
- [`reference/memory.md`](./reference/memory.md) — tiered memory (STM/MTM/LTM), loose gates, size-triggered eviction.
- [`reference/mailboxes.md`](./reference/mailboxes.md) — inbox/outbox format, the doorway pattern, delivery guarantees.
- [`reference/budgets.md`](./reference/budgets.md) — budget model, defaults, enforcement.
- [`reference/autonomy-ladder.md`](./reference/autonomy-ladder.md) — how the operator hands work over.
- [`templates/`](./templates) — the files copied into each agent workspace and each project.

---

## Principles

1. **Confirm before writing.** The wizard proposes; the operator disposes.
2. **Evidence over status.** "Running" is not "done". QA returns proof.
3. **Real limits live outside the prompt.** Budgets are enforced by policy and accounting, not by asking the model nicely.
4. **Security advises, never self-edits.** No agent may modify its own permissions, prompt, or safety config.
5. **Cheap by default, escalate to reasoning.** Most work is routine; pay for thinking only where it matters.
6. **Plain files.** If you can't `cat` it, don't trust it.

---

## Status

Early. This is v0.1 — the conventions are stable enough to build on, and the wizard is the intended entry point. Contributions and issue reports welcome.

## License

MIT — see [`LICENSE`](./LICENSE).
