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

If the operator installs the **Finance Manager**, the Cadre Wizard runs the full budget interview instead of applying defaults. **Every question arrives pre-filled with a default**, so the operator can accept the whole block in one word ("use the defaults") or tune any single line. *An **envelope** is just a spend limit for one role — the most that role may use in a period.*

1. **Unit** — what are we counting? **Default: tokens** (what the model bills in; needs no price table). Currency requires a per-model price table.
2. **Period** — how long is one budget window? **Default: daily.**
3. **Per-role envelopes** — the spend limit for each role. **Default: the standard table above** (Project Manager 400k, QA 250k, …). "Bespoke" is optional tuning, never a blank the operator must fill — say so.
4. **Global ceiling** — the total that must never be crossed. **Default: 1.5M tokens/day.**
5. **Enforcement** — at a role's limit: keep going and report (`warn`), or stop the work (`cap`)? **Default: `warn`.**
6. **Alert routing** — who hears about a breach? **Default: the Finance Manager → the doorway → the operator.**
7. **Overflow policy** — a role has spent its envelope; then what? **Default: escalate to the operator for a top-up** (never silently borrow from another role).

The Finance Manager then **owns** the numbers, reports burn against them, and raises breaches. The Finance Manager does **not** silently raise a ceiling — only the operator can.

The Finance Manager also **owns the scheduled-work audit**: recurring jobs and watchers are where spend is *created*, so it audits every scheduled job for **owner, purpose, and $0 idle cost** ([`scheduled-work.md`](./scheduled-work.md)). Keep it **one batched pass on the Finance Manager's cadence** — an efficient audit, not a ceremony. The checks that matter run as sentinels, so the audit itself does not add spend.

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

## Switching models at a spend threshold (a gateway-layer pattern)

A tester asked whether **Finance Manager / Agent Resources can flag a model at 95% spend and move the
agent onto a different model**. It is a common, well-understood pattern — but it lives one layer
*above* the agent runtime, not inside it.

**Where it is implemented today.** AI **gateways** do exactly this:

- **LiteLLM** — `budget_fallbacks`: set a per-model `budget_limit`; when spend on that model crosses it,
  requests are *silently rerouted* to the first fallback model that still has budget. Set the limit at
  95% of your intended ceiling to get "switch at 95%". Spend is attributed to the fallback model.
- **Portkey / Edgee** — percentage-tier routing: e.g. 0–80% premium model, 80–95% mid-tier, 95%+ cheapest.

**What OpenClaw does natively.** `agents.defaults.model.fallbacks` exists — but it triggers on
**failover-worthy errors** (rate limits, provider outages), **not on budget**, and the fallback is
*turn-local* (it does not persist as the next turn's model). And per the section above, the platform
exposes **no spend cap and no cost-report command** — so there is nothing native to bind a
"95% of budget" trigger to.

**Consequence for Cadre — an operator-layer capability, exactly like `enforcement: cap`:**

1. **Flag at threshold** — the Finance Manager (or the operator) reads provider billing / per-model `cost` metadata and
   raises a breach at the configured threshold (default 80%; settable to 95%). This is a *role duty*
   Cadre already defines.
2. **Switch the model** — the switch needs a mechanism *outside* the model: either (a) route the
   deployment through an AI gateway (LiteLLM et al.) that does budget fallbacks, or (b) a deterministic
   checker that reads spend and rewrites the deployment's model config when the threshold trips.
   Cadre ships neither binary; it defines the duty and points at the pattern.

**Honest limit.** As with the cap, a threshold switch that relies on the agent *remembering* to check is
not enforcement. The switch must be made by something deterministic — a gateway rule or a scheduled
checker — or it will not fire at the moment it matters.

---

## Why not enforce purely in the prompt

Telling an agent "stay under 250k tokens" is a wish. The model cannot reliably count its own spend. Real enforcement is **accounting plus policy**:

- the operator's own usage/cost reporting (provider billing, or per-model `cost` metadata) is the source of truth — the platform ships no report of its own,
- The Finance Manager (or the operator, without one) reads it and compares to the envelope,
- a breach triggers the configured behaviour (warn or cap) via policy, not persuasion.

This mirrors Cadre principle #3: **real limits live outside the prompt.**

---

## The unbounded-autonomy failure this prevents

The valuable property of a persistent team is that it keeps working while you're away. The dangerous version of that is *it keeps spending while you're away*. A budget turns "away" from risky into fine — which is the entire point of granting autonomy in the first place.
