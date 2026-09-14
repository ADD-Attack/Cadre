# CADRE.md — Installed Team Index

> Written by the **Cadre Wizard** at the end of setup. This is the record of *what
> was actually installed* on this deployment — the source of truth for who exists,
> what they cost, and how they're reached.

**Installed:** <date>
**Cadre version:** v0.1
**Interface mode:** <direct | single-doorway via <agent>>

---

## Roster

| Agent | Role | Model | Budget | Autonomy | Reports to |
|---|---|---|---|---|---|
| <name> | Project Manager | <model> | <ceiling>/<period> | L1 | operator |
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

## Doorway (if enabled)

- **Agent:** <name>
- **Cadence:** <every N hours>
- **Scope:** <which outboxes it reads>
- **Urgency lane:** immediate for `priority: urgent` / `kind: blocked`

## Projects under Cadre

| Project | PM | Board | Phase |
|---|---|---|---|
| <name> | <agent> | <FlowBoard project> | <phase> |

## Autonomy log

Record every ladder change — a level without a date is folklore.

| Date | Role | From → To | Reason |
|---|---|---|---|

## Canary results

<pass/fail per created agent at install time>
