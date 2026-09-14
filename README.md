<p align="center">
  <img src="cadre-wizard.png" alt="The Cadre Wizard" width="220">
</p>

# Cadre

**A downloadable system of agents and Markdown files that turns any OpenClaw deployment into a coordinated team.**

Cadre gives you a persistent, chat-native multi-agent hierarchy: a small nucleus of specialist agents with roles, budgets, mailboxes, and a project pipeline — installed by the guided **Cadre Wizard** and adapted to your preferences.

---

## Before you start — if you don't have OpenClaw yet

Cadre is an **overlay, not a standalone app.** It installs *into* an OpenClaw deployment, so there has to be one first. If you're arriving with a **ChatGPT, Gemini, or Claude** subscription, an OpenAI API key, or a coding assistant like **Codex** or **Hermes**, that's a great starting point — but it is not OpenClaw yet:

- **A model subscription or API key is a *model*** — the thing that generates the text. ChatGPT, Google **Gemini**, Anthropic **Claude**, DeepSeek, Groq, Mistral, or a local model all count here. **OpenClaw is the runtime** your agents live in: the process that gives them a workspace, memory, mailboxes, budgets, and a chat interface. Cadre builds a team *inside* that runtime.
- **Codex and Hermes are coding agents** — they work inside a repo. OpenClaw runs a *team* of agents with roles and a shared workspace. Different jobs, and both sit happily next door.
- OpenClaw talks to whichever provider you choose. **What you already pay for usually just works** — an OpenAI, Gemini, or Anthropic key — and onboarding can bring your existing setup across.

**1. Check the machine.** Node **24.16+** (Node 26 recommended) on **macOS, Linux, or Windows** (Windows via WSL2, or the Windows Hub app).

**2. Install OpenClaw.**

- macOS / Linux / WSL2:
  ```bash
  curl -fsSL https://openclaw.ai/install.sh | bash
  ```
- Windows (PowerShell):
  ```powershell
  iwr -useb https://openclaw.ai/install.ps1 | iex
  ```

Prefer an app download over the CLI? There are desktop companions for Windows and macOS — see the [install docs](https://docs.openclaw.ai/install).

**3. Run onboarding.** The installer walks you through it: choose a model provider (your **OpenAI, Gemini, or Anthropic** key goes here — or point it at a local model), name your main agent, and connect a chat channel (Discord, Telegram, or similar). **Cadre is chat-native** — a connected channel is what makes the team usable.

> **Coming from Codex or Hermes?** Onboarding can **import detected memories from Codex, Hermes, or Claude Code** into the agent workspace, so the new agent starts out knowing what you've been working on.

**4. Come back here.** Once `openclaw` is installed and your main agent answers you in a chat, you're ready — continue with *Installing it* below.

Full details: [docs.openclaw.ai/install](https://docs.openclaw.ai/install).

---

## Installing it — a decision for the operator

Cadre is installed by a dedicated **`CadreWizard` agent** that your **main agent spawns** — the install is a conversation, and the installer runs *outside* the team it is building. Installing also changes your deployment — it writes agent entries and creates agent workspaces — so it should be an explicit choice the operator makes, never something that happens because a file said so.

> **Naming, because the two look alike.** The guided install *procedure* is the **Cadre Wizard**. The *separate agent that runs it* is named `CadreWizard`. Same job, two names: the concept, and the agent identifier you'll see in `openclaw agents add cadre-wizard`.

**The operator's part** is one sentence, said to their main agent:

> Read `Cadre/README.md`, tell me what Cadre is, and set it up if I agree.

**The agent's part** — if you are that main agent, and the operator has asked you to look into Cadre, work through this *with them*:

1. **Explain before anything else.** Say what Cadre is, what installing it will create (agents, config entries, workspaces), and that it is reversible. Then **ask the operator for permission to proceed** — and wait for a yes.
2. **Clone the files** only once they agree:
   ```bash
   git clone https://github.com/ADD-Attack/Cadre.git
   ```
3. **Spawn the `CadreWizard`** — do **not** run the install inline as yourself. Create a **separate agent** whose only job is the interview: a visible, thread-bound spawn so the operator can talk to it directly (`sessions_spawn`, `visible: true`), or a persistent agent via `openclaw agents add cadre-wizard` if you want a reusable installer. Point it at [`WIZARD.md`](./WIZARD.md).
4. **Let the `CadreWizard` interview the operator** (WIZARD.md Step 0 onward). It **proposes and waits** at every step — nothing is written to OpenClaw config or to a workspace until the operator confirms that step. If they say stop, it stops.
5. **It writes only what was approved**, via `openclaw config set` (never hand-edit JSON), runs the canary check (WIZARD.md Step 8), then **hands back and retires**. You resume the operator's normal work.

Nothing here runs on its own. This repo describes a procedure; **the operator decides whether to run it.**

---

## What this is

Cadre is **not** a framework you install as a package. It is a **folder of Markdown conventions + a setup procedure** that a spawned **`CadreWizard` agent** carries out for your deployment. You get:

- A **role roster** — requirements analyst, project designer, project manager, plus standing functions (security/IT, social media, finance, QA, agent resources, consultant).
- A **project pipeline** — requirements → design → plan → execution, with a Gantt chart maintained in `PROJECT.md`.
- **Mailboxes** — every agent has an `inbox/` and `outbox/`, so a team can be run from a single chat interface.
- **Budgets** — per-role spend/effort envelopes so autonomy never means runaway cost.
- **An autonomy ladder** — the operator starts doing most PM and QA work; agents take over as they prove out.

Everything is plain files. Nothing is hidden in a database you can't read.

**Not a teammate: your personal assistant.** Cadre is the *work* team. A **personal assistant** — the agent that knows your calendar, your messages, your life outside any project — carries private, unbounded context and belongs in its **own separate environment**, not in the Cadre install. Keep the two apart: the team works in project-scoped, shared files, and folding private context into them is how the wrong things end up in shared artifacts. Your PA is not a seat and not on the roster.

---

## Quick start

1. **Get the files** onto the machine already running OpenClaw (if it isn't installed yet, start with *Before you start* above):
   ```bash
   git clone https://github.com/ADD-Attack/Cadre.git
   ```
2. **Tell your OpenClaw main agent:**
   > Read `Cadre/README.md`, tell me what Cadre is, and set it up if I agree.

3. **The main agent spawns the `CadreWizard`.** It reads this file, then creates a **separate `CadreWizard` agent** to run the install (see [`WIZARD.md`](./WIZARD.md)) — the wizard is not the main agent wearing a hat. The `CadreWizard` interviews you, confirms every choice, and only then writes anything.

That's it. The Cadre Wizard does the rest.

---

## The flow

![How a project runs: the Cadre Wizard once, then Requirements Analyst to Project Designer to Project Manager (workers in its scope) to QA to the finished product; QA can return work to the PM, the PM can return new requirements to the Requirements Analyst, and a rework path runs from the finished product back to the Requirements Analyst, with support roles on call beside the line](./diagrams/project-pipeline.svg)

```
 Operator
    │  "set up Cadre"
    ▼
 OpenClaw main agent ──reads──▶ README.md
    │  explains + asks permission
    │  spawns
    ▼
 CadreWizard (separate agent) ──interviews──▶ you (agents, models, names, budgets, interface)
    │  writes on confirmation, verifies, then retires
    │  hands back
    ▼
 Cadre team (installed)

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

Full charters, budgets, and authority: [`reference/agents.md`](./reference/agents.md). The Cadre Wizard confirms which of these to create — you don't have to take all nine.

A **personal assistant** is deliberately *not* on this list. It is a separate agent in its own environment, not a Cadre role (see *What this is* above).

---

## Reference

- [`WIZARD.md`](./WIZARD.md) — the setup interview, step by step.
- [`reference/agents.md`](./reference/agents.md) — roster, charters, budgets, authority.
- [`reference/guardrails.md`](./reference/guardrails.md) — the guardrails: routing limit, file-claim lease, promotion gate, no-op detector, **QA cap**, **zero-token checks**.
- [`reference/verification.md`](./reference/verification.md) — how to produce evidence: restate the pass condition, capture the real artifact, check the whole of it, report "could not verify" honestly.
- [`reference/requirements.md`](./reference/requirements.md) — the Requirements Analyst's method: tough-love scope defense, want-vs-need, acceptance criteria, the doable first version.
- [`reference/design.md`](./reference/design.md) — the Project Designer's method: the feature inventory, the style guide, and the ordered hand-off a builder can execute without guessing.
- [`reference/security.md`](./reference/security.md) — the Security/IT seat's method: scheduled audit, confidentiality sweep, exposure posture, remediation queue (advises, never edits).
- [`reference/scheduled-work.md`](./reference/scheduled-work.md) — what may run on a schedule: timers vs sentinels, idle must cost $0, and FM audits every job.
- [`reference/memory.md`](./reference/memory.md) — tiered memory (STM/MTM/LTM), loose gates, size-triggered eviction.
- [`reference/collaboration.md`](./reference/collaboration.md) — how agents work together: the two peer mechanisms (dispatch vs message), the guards that stop a team looping/colliding/stalling, escalation topology.
- [`reference/mailboxes.md`](./reference/mailboxes.md) — inbox/outbox format, the doorway pattern, delivery guarantees.
- [`reference/budgets.md`](./reference/budgets.md) — budget model, defaults, enforcement.
- [`reference/autonomy-ladder.md`](./reference/autonomy-ladder.md) — how the operator hands work over (who decides, per level).
- [`reference/autonomy.md`](./reference/autonomy.md) — the act-vs-ask contract: when an agent acts alone, the four reasons to stop, and how it reports.
- [`templates/`](./templates) — the files copied into each agent workspace and each project.
- [`templates/CADRE.md`](./templates/CADRE.md) — the **team directory** the wizard writes: who exists, roles, models, budgets, and who reports to whom. Read by every agent at session start.
- [`templates/project/`](./templates/project) — the per-project files: `PROJECT.md` (goal, status, Gantt) and `DECISIONS.md` (the append-only decision log).
- [`diagrams/topology.md`](./diagrams/topology.md) — the team topology as a diagram: who can reach whom, the optional doorway, and the rework loop.

---

## Principles

1. **Confirm before writing.** The Cadre Wizard proposes; the operator disposes.
2. **Evidence over status.** "Running" is not "done". QA returns proof.
3. **Real limits live outside the prompt.** Budgets are enforced by policy and accounting, not by asking the model nicely.
4. **Security advises, never self-edits.** No agent may modify its own permissions, prompt, or safety config.
5. **Cheap by default, escalate to reasoning.** Most work is routine; pay for thinking only where it matters.
6. **Plain files.** If you can't `cat` it, don't trust it.

---

## Where this comes from

Cadre is the architecture realized from a research paper and its plain-language adaptation, in the companion repo [`ADD-Attack/agent-team-research`](https://github.com/ADD-Attack/agent-team-research):

- [**Building an AI Team That Lasts**](https://add-attack.github.io/agent-team-research/article.html) — the plain-language article: what a persistent team is, and why it's built this way. No CS background needed.
- [`PAPER.md`](https://github.com/ADD-Attack/agent-team-research/blob/main/PAPER.md) — *Persistent Agent Teams*: prior art, the case study, and the reference architecture this system implements.

---

## Status

Early. This is v0.1 — the conventions are stable enough to build on, and the Cadre Wizard is the intended entry point. Contributions and issue reports welcome.

## License

MIT — see [`LICENSE`](./LICENSE).
