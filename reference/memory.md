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
| **LTM** — long-term | `MEMORY.md` | low (budget-bounded) | ≤20,000 characters by default* | curated, append-only, human-readable |

Caps are tunable defaults. Size caps — not the platform's default thresholds — bound each tier.
**Bootstrap is also a size boundary:** OpenClaw's default per-file `bootstrapMaxChars` is 20,000
characters (with a separate 60,000-character aggregate budget). Therefore the effective LTM cap is
the lower of Cadre's chosen cap and the live per-file bootstrap limit. A 64 KB `MEMORY.md` can be
partly omitted from the agent's injected context even if it is within a local byte budget. Check the
runtime's configured limit before setting a deployment-specific cap; count characters, not UTF-8
bytes. Leave headroom for deliberate edits rather than targeting the exact boundary.

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

1. **Report the outcome, not just process success.** Distinguish no candidates, candidates ranked,
   candidates passing numeric gates, candidates rejected by source/provenance policy, candidates
   selected for durable consolidation, and candidates actually written. OpenClaw's `DREAMS.md`
   summary may report ranked/promoted totals without explaining every rejection; do not infer the
   exact failure stage from those two totals alone.
2. **No-promotion is an observable no-op, not automatically a broken gate.** If candidates were
   ranked but none were promoted, report `NO_PROMOTION` and preserve the counts. Escalate as a gate
   anomaly when durable candidates passed the authored gates but none were written, when a large
   candidate window repeatedly yields zero, or when the run fails to emit its expected report.
   A high-scoring transient chat line can pass numeric thresholds and still correctly fail the
   durability test. “Ranked” is not the same as “eligible durable memory.”
3. **Assert on artifacts.** A cycle must leave a visible outcome record even when no tier changes.
   A legitimate no-op is reported as a no-op; a missing report or failed write is a failed run.

---

## Writer discipline

- **STM:** the memory system (one writer, as configured).
- **MTM:** exactly **one** writer — the PM or a designated consolidator. Never two.
- **LTM:** one writer; promotions land here and curations are visible edits. Keep the curated file
  within its *effective injected-context cap*; archive/raw history does not belong in the injected
  `MEMORY.md` merely to preserve an append-only trail.

Shared entries that are *team-scoped* (decisions, conventions, file ownership) do **not** go in a private tier — they belong in `SHARED.md` at the team root. See [`guardrails.md`](./guardrails.md) §2 for the claim lease that guards it.
