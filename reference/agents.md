# Reference — Agents

The Cadre roster. Roles are **fixed**; names, models, and budgets are the operator's (see [`../WIZARD.md`](../WIZARD.md)).

Every agent is a **persistent OpenClaw agent**: its own workspace, persona files, memory, session store, and mailboxes. None are ephemeral subagents — subagents are spawned *by* these agents for disposable work.

---

## The roster

| Agent | Class | Owns | Default authority |
|---|---|---|---|
| **Project Manager (PM)** | reasoning | plan, tasks, Gantt, dispatch, tracking | dispatch workers; may absorb others' duties when configured |
| **Requirements Analyst (RA)** | reasoning | intake, clarification, scope, acceptance criteria | write requirements; no build authority |
| **Project Designer (PD)** | reasoning | architecture, approach, specs | write design; no build authority |
| **Security / IT** | reasoning | audit, exposure, hygiene, remediation queue | **advise only** — never self-edits config |
| **QA / Verifier** | reasoning | independent verification, evidence | **veto** — may block a "done" claim |
| **Social Media Manager (SMM)** | fast | external comms, posting, community | external-send (gated) |
| **Finance Manager (FM)** | fast | budgets, spend tracking, alerts | budget enforcement (report; cap if configured) |
| **Agent Resources (AR)** | fast | roster, onboarding, loadouts, agent health | create/retire subagents; no config authority |
| **Consultant** | reasoning | second opinion, red-team, advice | none — pure advice |

---

## Why *these* roles

This set is not arbitrary. It maps onto the reference architecture in the companion paper (*Persistent Agent Teams*, §8): **Supervisor** (PM), **Builders** (RA/PD/workers), **QA/Verifier** (QA — a *different* agent than the builder, or it is not verification), **Liaison** (the doorway agent — usually SMM), **Support** (Finance, AR).

Two roles carry a hard constitutional limit:

- **Security/IT advises, never edits.** An agent that can rewrite its own permissions or safety config defeats the point of having one. Security finds and recommends; a human or an explicit config change applies. (This is the self-modification perimeter.)
- **QA is independent.** QA must not be the agent that built the thing. Where a build is done by a worker subagent, QA is a separate persistent agent — otherwise "verification" is a second opinion from the same priors.

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
| Add/retire agents | AR (roster) — config changes require the operator |
| Change config, permissions, safety | **operator only** |

---

## The autonomy ladder (summary)

Cadre assumes **the operator does most PM and QA work at first**, and hands over as agents prove out. Each role has a ladder; the operator ratchets it up deliberately.

See [`autonomy-ladder.md`](./autonomy-ladder.md) for the per-role levels.

---

## PM authority, by configuration

The original design spec: *"project manager is able to take over responsibilities depending on configuration."*

This is deliberate — a solo operator may want the PM to also cover requirements or QA early on (fewer agents, faster). The wizard records a **PM coverage** setting:

| Mode | PM covers | Use when |
|---|---|---|
| `minimal` | PM only | full roster installed |
| `covers-ra` | + requirements | no RA yet |
| `covers-qa` | + QA | operator is the verifier |
| `solo` | PM + RA + QA | smallest viable team |

Coverage is a **configuration**, not a merge. A covered role can be split out later without losing the audit trail — the PM's work in that lane is handed over as a normal project.

---

## Default models (class, not name)

The wizard binds a concrete model to each class *for the operator's deployment*. Cadre states classes so it doesn't rot as models change:

- `reasoning` — planning, verification, security, design. Pay for thinking here.
- `fast` — routine relay, accounting, posting. Cheap and quick.

A role's class may be overridden per-role by the operator.
