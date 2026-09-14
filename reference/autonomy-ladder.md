# Reference — The Autonomy Ladder

Cadre's working assumption: **the operator starts by doing most PM and QA work, and hands over as agents prove out.** Autonomy is *earned in steps*, not granted on install.

This is not a limitation. It is the mechanism that makes delegation safe — you extend trust as evidence accumulates.

---

## The levels

Each role climbs the same ladder. The operator ratchets a role up deliberately; a role can also be dropped a level after a bad call.

| Level | Who decides | Who executes | Who verifies |
|---|---|---|---|
| **L0 — Observe** | operator | operator | operator |
| **L1 — Propose** | operator | agent drafts, operator approves | operator |
| **L2 — Execute** | operator sets the goal | agent executes | operator |
| **L3 — Verify** | operator sets the goal | agent executes | **agent verifies, operator spot-checks** |
| **L4 — Decide** | agent, within policy | agent | agent, with audit |

**Rule:** a role may not reach **L3** until it has a clean L2 track record, and no role reaches **L4** in a domain with external or irreversible effects without the operator saying so explicitly.

---

## Starting points (default install)

| Role | Starts at | Rationale |
|---|---|---|
| Project Manager | L1 | planning is easy to review, costly to get wrong |
| Requirements Analyst | L1 | scope errors propagate |
| Project Designer | L1 | same |
| QA / Verifier | **L3** | verification *is* the agent's job; operator spot-checks |
| Security / IT | L2 | executes audits, never decides config |
| Social Media Manager | L1 → L2 | external effects — climb slowly |
| Finance Manager | L2 | tracks and reports; cannot raise ceilings |
| Agent Resources | L2 | roster changes reviewed |
| Consultant | L4 | advice has no side effects |

Note **QA starts highest**: an operator doing QA themselves is the bottleneck, and QA is the one role whose whole purpose is independent judgement.

---

## Ratcheting up

To move a role up a level, the operator should have:

1. **Evidence of a clean run** at the current level (a track record, not one success).
2. **A defined boundary** for the next level (what the agent may now do alone).
3. **A rollback** (how to drop back and what happens to in-flight work).

Record the level and the date in the team index. A level without a date is folklore.

---

## Ratcheting down

Drop a level when: a wrong call with real cost, a boundary crossed, or the operator simply wants to re-watch. **Dropping is not punishment** — it is the ladder working. Record it the same way.

---

## The anti-pattern this avoids

Granting full autonomy on day one to save time, then having to claw it back after damage — which destroys trust in both directions. Cadre's ladder front-loads the operator's involvement *while it is cheap*, so that by the time the operator steps back, the evidence is already there.

> **Trust is not the absence of oversight; it is the residue of oversight that was paid for early.**
