# Reference — Memory (tiered)

Cadre's memory design follows the companion paper's §10. It exists because of a real failure: a promotion gate tuned for a busy instance **promoted 0 of 1,229** staged entries for a week, while every nightly report said success.

The fix is an **inversion**: the old design was **strict in, permanent out** (a high bar, and whatever clears it stays forever). Cadre uses **loose in, size-bounded out**.

> **Loose promotion. Quality by eviction. Recall is the only vote that counts.**

---

## The three tiers

| Tier | Store | Churn | Size cap | Contents |
|---|---|---|---|---|
| **STM** — short-term | staged candidates / session recall | high | ~256 KB | raw snippets, recent observations |
| **MTM** — mid-term | `memory/midterm.md` | moderate | ~128 KB | consolidated, recurring knowledge |
| **LTM** — long-term | `MEMORY.md` | low (budget-bounded) | ~64 KB | curated, append-only, human-readable |

Caps are tunable defaults. Size caps — not the platform's default thresholds — bound each tier.

**Why a middle tier.** `MEMORY.md` should be curated, not a dumping ground; the raw store is too noisy to read. `midterm.md` is the consolidation space between them. Platform note: OpenClaw's `memory-core` exposes a **single** deep phase and **no native middle tier** (verified 2026-09-14), so MTM is a **workspace convention** — a plain file with exactly one writer.

---

## The cascade

```
STM  ──recalled──▶  MTM  ──recalled again──▶  LTM
 │                    │
 └── over budget ─────┴──────▶ evicted
```

Promotion is driven by **recall**; the weighted score is a **tie-breaker, never the trigger**. LTM is **exempt from automatic eviction** — exceeding its cap flags for human curation instead.

---

## Adaptive gates (deliberately loose)

Thresholds are **percentiles of the instance's own distribution**, not fixed constants:

```
STM → MTM:  τ = clamp(P60(scores), 0.30, 0.55)
            promote if score ≥ τ and recallCount ≥ 1 and uniqueQueries ≥ 1

MTM → LTM:  τ = clamp(P75(scores), 0.40, 0.70)
            promote if score ≥ τ and recallCount ≥ 2 and uniqueQueries ≥ 1
```

**Small windows.** Below ~20 candidates a percentile is meaningless. Fall back to **loose absolutes** (0.30 / 0.40) — **never** to a strict default, which is the original failure reproduced.

⚠️ **Known limitation (inherited, unresolved).** At very low volume the fallback is still a *constant* — looser than the one that failed, but a constant nonetheless. A future revision should replace the small-window case with **admit-all + evict** (no threshold at all). Until then, prefer the loosest value your cycle tolerates and lean on eviction.

---

## Eviction — size-triggered, never time-based

An entry is not dropped for being **old**. It is dropped when a tier **exceeds its size cap** and something has to give:

```
value = recallCount     # primary
      , score           # secondary
      , recency         # tie-break only
```

Lowest value goes first. **A frequently-recalled old entry outlives a rarely-recalled new one** — that is the whole point. Age alone never evicts.

---

## Making silence loud

The original failure wasn't a wrong gate; it was an **invisible** wrong gate. Two valves:

1. **No-op alert.** Promoting 0 while the window held ≥ 20 candidates is an anomaly, not a quiet week.
2. **Assert on artifacts.** A healthy cycle produces a visible change in some tier. No change = failed run, not silent success.

---

## Writer discipline

- **STM:** the memory system (one writer, as configured).
- **MTM:** exactly **one** writer — the PM or a designated consolidator. Never two.
- **LTM:** append-only by its one writer; promotions land here, curations are visible edits.

Shared entries that are *team-scoped* (decisions, conventions, file ownership) do **not** go in a private tier — they belong in `SHARED.md` at the team root. See [`guardrails.md`](./guardrails.md) §2 for the claim lease that guards it.
