# CADRE.md — Installed Team Index

> Written by the **Cadre Wizard** at the end of setup. This is the record of *what
> was actually installed* on this deployment — the source of truth for who exists,
> what they cost, and how they're reached.
>
> **Every agent reads this at session start**, alongside the shared ledger
> [`SHARED.md`](./SHARED.md). Each agent's `AGENTS.md` records its path, so an agent
> always knows who its teammates are and how they are reached — it does not guess.
>
> *This file installs at the **team root**, beside `reference/` and `SHARED.md`. Links are written for that layout.*

**Installed:** <date>
**Cadre version:** v0.1
**Team name:** <team name>
**Interface mode:** `<interface mode — direct, or single-doorway via one agent>`

---

## Roster

| Agent | Role | Model | Budget | Autonomy | Reports to |
|---|---|---|---|---|---|
| <name> | Project Manager | <model> | <ceiling>/<period> | L1 | operator |
| <name> | Worker | <model> | <ceiling>/<period> | L1 | PM |
| <name> | Requirements Analyst | <model> | … | L1 | PM |
| … | | | | | |

## Naming convention

<theme + pattern, so future additions match>

## PM coverage

<minimal | covers-ra | covers-qa | solo>

## Budgets

- **Global ceiling:** <amount> <unit>/<period>
- **Enforcement:** <warn | cap>
- **Overflow policy:** <stop | borrow | escalate>
- **Enforcement mechanism:** `<none (accounting-only) — or a LiteLLM gateway with per-model caps and fallback at a set threshold>`
- **Model routing:** <direct to providers | via the gateway>

## Doorway (if enabled)
- **Agent:** <name>
- **Cadence:** <every N hours>
- **Scope:** <which outboxes it reads>
- **Urgency lane:** immediate for `priority: urgent` / `kind: blocked`

## Guardrails

Record enforcement honestly — *advisory* is better than *unstated*.

| Guardrail | Setting | Enforcement |
|---|---|---|
| Routing limit (hop cap) | <n> | enforced \| advisory |
| File-claim lease | `.claims/` | enforced \| advisory |
| Promotion gate | <thresholds> | authored \| defaulted |
| No-op detector | on | enforced \| advisory |
| QA cap (max 2 review rounds) | 2 | enforced \| advisory |
| Zero-token checks | on | enforced \| advisory |

## Scheduled work

Recurring jobs and watchers. Every job names an **owner**, and idle must cost **$0** ([`./reference/scheduled-work.md`](./reference/scheduled-work.md)).

| Job | Owner | Kind | Cadence | Idle cost |
|---|---|---|---|---|
| <name> | <agent> | timer \| sentinel | <at / every / on-event> | $0 |

## Projects under <team name>

| Project | PM | Board | Phase |
|---|---|---|---|
| <name> | <agent> | <FlowBoard project> | <phase> |

## Autonomy log

Record every ladder change — a level without a date is folklore.

| Date | Role | From → To | Reason |
|---|---|---|---|

## Canary results

<pass/fail per created agent at install time>
