# SHARED.md — Team Ledger

> **Team-scoped truth**, one append-only ledger that every agent reads at session
> start and any agent may append to **under a claim lease**.
> A ledger, not a scratchpad. See [`reference/guardrails.md`](../reference/guardrails.md).

## What belongs here

- **Decisions with provenance** — what was decided, by whom, when, and why.
- **File ownership** — who owns which shared file right now.
- **Standing conventions** — team-wide rules agreed once.
- **Environment facts** — durable truths about this deployment.

## What does NOT belong here

- Per-persona notes (those live in the agent's own `MEMORY.md`).
- Scratch work, drafts, half-thoughts.
- Anything one agent should keep private.

## Write rule

**Claim before writing.** Append via the claim/lease protocol — create
`.claims/<path-hash>.claim` first. One writer at a time.

---

## Log

<!-- Newest last. One entry per addition. -->

### <date> — <topic>
- **By:** <agent>
- **Type:** decision | ownership | convention | environment
- **Entry:** <the fact>
