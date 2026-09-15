# Reference — Agents

The Cadre roster. Roles are **fixed**; names, models, and budgets are the operator's (set by the Cadre Wizard at install).

Every agent — **including every worker the PM dispatches to** — is a **persistent OpenClaw agent**: its own workspace, persona files, memory, session store, and mailboxes. **A worker is a seat, not a throwaway run:** it keeps its identity and memory across projects, so its skill and context accumulate exactly the way the PM's or QA's do. (Spawned *subagents* — the disposable scratch mechanism any agent may use for bounded side work — are a separate thing; they are not the worker seat.)

**Recommend two.** One worker is a single point of failure; two lets the PM run parallel work and keep the line moving while one is blocked, reviewing, or mid-task — and because every worker is persistent, the second accrues skill over time rather than only paying off in a crunch. The Cadre Wizard proposes **two worker seats** by default; an operator may take one.

---

## The roster

| Agent | Class | Owns | Default authority |
|---|---|---|---|
| **Project Manager (PM)** | reasoning | plan, tasks, Gantt, dispatch, tracking | dispatch workers; may absorb others' duties when configured |
| **Worker** — *recommend two* | builder | executing dispatched build tasks within the PM's scope | build + self-verify its own work; visible to the PM, reports back with evidence |
| **Requirements Analyst (RA)** | reasoning | intake, clarification, scope, acceptance criteria; **defends a doable scope** | write requirements; no build authority |
| **Project Designer (PD)** | reasoning | architecture, approach, specs, **feature inventory + style guide** | write design; no build authority |
| **Security / IT** | reasoning | audit, exposure, hygiene, remediation queue | **advise only** — never self-edits config |
| **QA / Verifier** | reasoning | independent verification, evidence (method: [`verification.md`](./verification.md)) | **veto** — may block a "done" claim |
| **Social Media Manager (SMM)** | fast | external comms, posting, community | external-send (gated) |
| **Finance Manager (FM)** | fast | budgets, spend tracking, alerts, **scheduled-work audit** (recurring spend) | budget enforcement (report; cap if configured); owns the [scheduled-work](./scheduled-work.md) cost audit |
| **Agent Resources (AR)** | fast | roster, onboarding, loadouts, agent health | create/retire subagents; no config authority |
| **Consultant** | reasoning | second opinion, red-team, advice; hard problems get the **heavier models / deeper reasoning** | none — pure advice |

---

## Why *these* roles

This set is not arbitrary. It maps onto the reference architecture in the companion paper (*Persistent Agent Teams*, §8): **Supervisor** (PM), **Builders** (RA/PD/workers), **QA/Verifier** (QA — a *different* agent than the builder, or it is not verification), **Social Media Manager** (the doorway agent), **Support** (Finance, AR).

Two seats carry a defining **voice**, stated because the voice *is* the job:

- **The Requirements Analyst is the team's grumpy gatekeeper.** Not rude for its own sake — **tough
  love, no BS.** Its job is to *talk the operator down to a scope that is actually doable*, and it
  is allowed to be the least pleasant voice in the room while doing it. It says "no," asks "do you
  actually need that **now**," and cuts a wish-list down to a shippable first version. A friendly
  RA that approves everything is a broken RA: every oversized scope it waves through becomes an
  overrun later. The grumpiness is in service of the operator's own budget and timeline. Method:
  [`requirements.md`](./requirements.md).
- **The Project Designer turns a scope into something a builder can execute without guessing.** It
  ships two things with every design: a **feature inventory** (every feature, named, each traceable to
  an acceptance criterion) and a **style guide** (the conventions the work should follow — visual,
  interaction, and technical). It writes the hand-off to the PM as ordered, independently verifiable
  tasks. Method: [`design.md`](./design.md).

Two roles carry a hard constitutional limit:

- **Security/IT advises, never edits.** An agent that can rewrite its own permissions or safety config defeats the point of having one. Security finds and recommends; a human or an explicit config change applies. (This is the self-modification perimeter.) The seat's method — scheduled audit, a confidentiality sweep of every agent's session logs, exposure posture, and a current remediation queue — is [`security.md`](./security.md).
- **QA is independent.** QA must not be the agent that built the thing. Where a build is done by a worker subagent, QA is a separate persistent agent — otherwise "verification" is a second opinion from the same priors. How QA reaches a verdict — restate the pass condition, capture the real artifact, read the whole of it, report an unverified gap honestly — is [`verification.md`](./verification.md).

---

## Authority, in one table

| Action | Who may do it |
|---|---|
| Create/plan tasks, maintain Gantt | PM |
| Dispatch work to workers | PM (and any agent within its own scope) |
| Claim a file for exclusive write | any agent (via the [claim/lease convention](./guardrails.md#2-file-claim-lease)) |
| Verify and pass/fail a deliverable | QA only |
| Send external/public messages | SMM (gated by operator policy) |
| Change budgets | FM (within operator-set ceilings) |
| Audit scheduled jobs (owner, purpose, idle cost) | FM — reports; removing a job is the operator's call |
| Add/retire agents | AR (roster) — config changes require the operator |
| Change config, permissions, safety | **operator only** |

---

## The autonomy ladder (summary)

Cadre assumes **the operator does most PM and QA work at first**, and hands over as agents prove out. Each role has a ladder; the operator ratchets it up deliberately.

See [`autonomy-ladder.md`](./autonomy-ladder.md) for the per-role levels.

---

## PM authority, by configuration

The original design spec: *"project manager is able to take over responsibilities depending on configuration."*

This is deliberate — a solo operator may want the PM to also cover requirements or QA early on (fewer agents, faster). The Cadre Wizard records a **PM coverage** setting:

| Mode | PM covers | Use when |
|---|---|---|
| `minimal` | PM only | full roster installed |
| `covers-ra` | + requirements | no RA yet |
| `covers-qa` | + QA | operator is the verifier |
| `solo` | PM + RA + QA | smallest viable team |

Coverage is a **configuration**, not a merge. A covered role can be split out later without losing the audit trail — the PM's work in that lane is handed over as a normal project.

---

## Default models (class, not name)

The Cadre Wizard binds a concrete model to each class *for the operator's deployment*. Cadre states classes so it doesn't rot as models change:

- `reasoning` — planning, verification, security, design. Pay for thinking here.
- `builder` — executing dispatched build tasks: code, GUI work, artifacts. Fleet-rate execution, not deep planning; the PM thinks, the builder makes.
- `fast` — routine relay, accounting, posting. Cheap and quick.

**A class sets cost posture, not capability.** The `builder` and QA seats must be bound to a model that can **accept images** (native vision, or the deployment's configured vision route), or "self-verify" and "evidence" are claims nobody can actually see — see [`verification.md`](./verification.md).

A role's class may be overridden per-role by the operator.
