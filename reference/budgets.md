# Reference — Budgets

Autonomy is only safe if it is **bounded**. A budget is how Cadre bounds it: every agent gets an envelope, and the envelope is enforced by policy and accounting — not by asking the model to be careful.

---

## The model

A budget has three parts:

| Part | Meaning | Example |
|---|---|---|
| **Unit** | what is counted | tokens (default) or currency |
| **Period** | the window | per day (default) or per week |
| **Ceiling** | the amount allowed | e.g. 250k tokens/day |

Plus two behaviours:

| Behaviour | Options |
|---|---|
| **Enforcement** | `warn` (default) — report when exceeded; `cap` — stop work when exceeded |
| **Threshold** | a percentage of the ceiling that raises an alert (default 80%) |

---

## Defaults (when the operator does not install Finance Manager)

Cadre's default is **light, accurate, and cheap**: token units, daily period, warn-only enforcement, one global ceiling on top of per-role envelopes.

| Role | Default envelope |
|---|---|
| Project Manager | 400k tokens/day |
| Requirements Analyst | 200k tokens/day |
| Project Designer | 200k tokens/day |
| Security / IT | 150k tokens/day |
| QA / Verifier | 250k tokens/day |
| Social Media Manager | 100k tokens/day |
| Finance Manager | 100k tokens/day |
| Agent Resources | 100k tokens/day |
| Consultant | 100k tokens/day |
| **Global ceiling** | **1.5M tokens/day** |

These are **starting points, not science**. The Cadre Wizard states them plainly; the operator adjusts. A quiet solo deployment will sit far under them.

**Default enforcement is `warn`, not `cap`** — because an unexpected hard stop mid-project is worse than a cost surprise for a small operator. Turn on `cap` where you mean it.

---

## With Finance Manager

If the operator installs **FM**, the Cadre Wizard runs the full interview instead of applying defaults:

1. **Unit** — tokens or currency? (Currency requires a per-model price table.)
2. **Period** — daily, weekly, monthly?
3. **Per-role envelopes** — bespoke, role by role.
4. **Global ceiling** — the number that must never be crossed.
5. **Enforcement** — `warn` or `cap`, per role.
6. **Alert routing** — who hears about a breach? (FM's outbox → doorway → operator.)
7. **Overflow policy** — when a role is out of budget: stop, borrow from a pool, or escalate for a top-up?

FM then **owns** the numbers, reports burn against them, and raises breaches. FM does **not** silently raise a ceiling — only the operator can.

---

## Where budgets live

Each agent workspace carries a `BUDGET.md`:

```markdown
# Budget — <agent name>

unit: tokens
period: daily
ceiling: 250000
threshold: 80
enforcement: warn
last_reset: 2026-09-14T00:00:00Z
spent_this_period: 0
```

A team-level `CADRE.md` records the global ceiling and the overflow policy.

---

## Platform reality: there is no native spend cap

**Verified against `openclaw config schema` (2026-09-14).** This is the constraint that shapes everything above, so state it plainly:

- **No monetary ceiling primitive exists.** There is no `spendLimit`, `maxSpend`, `costCap`, `dollarBudget`, or `budgetUsd` key anywhere in the configuration schema. A budget cannot be *enforced by the platform* — there is nothing to bind the ceiling to.
- **No usage/cost report command exists** either. The CLI exposes no `usage`, `cost`, or `spend` report. The closest surfaces are telemetry (anonymous, not billing) and per-model `cost` metadata.
- **Per-model `cost` metadata** (`input` / `output` / `cacheRead` / `cacheWrite` / `tieredPricing`) exists — but it lets you **price** usage, not **stop** it.
- **`maxTokens` and context/compaction budgets** bound *context windows*, not dollars. They are not a spend control.
- Beware the near-miss key `suspendAfter`: it reads like a cap and is not one. It is *"Cloud Worker Idle Suspend Duration"* — it reclaims an idle cloud worker after e.g. `45m`; it has nothing to do with money.

**Consequence for Cadre:** the budget layer is **accounting plus convention, and nothing more**. `enforcement: cap` is a **team promise the operator's policy layer keeps** — a wrapper, a scheduled checker, or a manual review — *not* a platform guarantee. Cadre does not ship that checker (see below).

No one deploying Cadre should believe a hard stop will save them. It will not. The honest offer is: *you will know your spend, and you will decide what happens at the ceiling.*

### What Cadre ships — and what it deliberately does not

| Piece | Cadre ships it? |
|---|---|
| Budget schema (`BUDGET.md`, unit/period/ceiling/threshold/enforcement) | **Yes** — the format and the defaults |
| Team ledger of ceilings + overflow policy (`CADRE.md`) | **Yes** |
| Accounting discipline (who reads spend, who reports breaches) | **Yes** — as a role duty |
| An enforcement binary that reads platform usage and halts a role | **No** — and it cannot, because the platform exposes no cap to bind to |

If you want teeth, add them at the operator layer (a checker that reads your provider's billing API and mutates `BUDGET.md` enforcement to `cap` + suspends the role). Cadre will adopt such a checker as an optional component; it will not pretend to contain one.

---

## Why not enforce purely in the prompt

Telling an agent "stay under 250k tokens" is a wish. The model cannot reliably count its own spend. Real enforcement is **accounting plus policy**:

- the operator's own usage/cost reporting (provider billing, or per-model `cost` metadata) is the source of truth — the platform ships no report of its own,
- FM (or the operator, without FM) reads it and compares to the envelope,
- a breach triggers the configured behaviour (warn or cap) via policy, not persuasion.

This mirrors Cadre principle #3: **real limits live outside the prompt.**

---

## The unbounded-autonomy failure this prevents

The valuable property of a persistent team is that it keeps working while you're away. The dangerous version of that is *it keeps spending while you're away*. A budget turns "away" from risky into fine — which is the entire point of granting autonomy in the first place.
