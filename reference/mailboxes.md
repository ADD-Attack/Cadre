# Reference — Mailboxes & the Doorway

Every Cadre agent workspace contains two mailboxes:

```
<agent-workspace>/
  inbox/    ← messages and work addressed TO this agent (from other agents OR the operator)
  outbox/   ← messages this agent wants the OPERATOR to see — and only the operator
```

They are plain directories of small files. Inspectable, greppable, survive restarts, no database.

---

## Two channels: peers vs the operator

Cadre separates **two communication paths**, and conflating them is a real bug:

| Path | Direction | How it works | Purpose |
|---|---|---|---|
| **Agent ↔ agent** (peer) | either way | direct agent-to-agent messaging; the recipient finds it in its **`inbox/`** | collaboration — dispatch, questions, handoffs, reviews |
| **Agent → operator** | one way | the agent's **`outbox/`**, relayed by the doorway | what the *human* must see — decisions, blockers, deliverables, anomalies |

> **The rule in one line:** the outbox is for the operator, and *only* the operator. Anything an agent wants to say to **another agent** goes **directly to that agent** (and lands in the recipient's `inbox/`) — it never goes in the sender's `outbox/`.

**Why the split matters.** An operator reads their team the way a manager reads a status report; they do not want to be cc'd on every peer exchange. If agent-to-agent chatter goes through outboxes, the operator is flooded, the doorway batches noise, and **real blockers get missed**. Peers collaborate on their own channel; only operator-relevant items cross into the outbox.

The routing limit (see [`guardrails.md`](./guardrails.md) §1) governs the **peer** channel — it caps how many agent-to-agent hops one unit of work may take, so collaboration cannot loop silently without finishing.

---

## Message format

One file per message, Markdown with a YAML front-matter block:

```markdown
---
id: 2026-09-14T04-31-00Z-a3f
from: requirements-analyst
to: operator
created: 2026-09-14T04:31:00Z
priority: normal        # low | normal | high | urgent
kind: report            # report | question | blocked | handoff
delivered: false        # set true by whoever relays it
---

Short body. Plain text. What happened, and what the operator needs to decide.
```

Filename convention: `<ISO-timestamp>-<short-hash>.md`. Lexical sort = chronological sort.

---

## Two modes

### Direct mode (default)

The operator has a chat surface that reaches the agents (or reaches the main agent, which relays). Agents can surface things themselves; mailboxes are a **buffer and audit trail**, not the only path.

### Single-doorway mode

For an operator with **one interface** only. They pick one agent — commonly the Social Media Manager — to be the **doorway**.

Mechanics:

1. On a cadence (default **hourly**), the doorway reads the `outbox/` of every agent **within its scope**.
2. It batches all undelivered messages into **one** consolidated ping to the operator.
3. When the operator replies, the doorway routes the reply into the correct agent's `inbox/`.
4. The doorway marks relayed messages `delivered: true`.

```
 RA.outbox ─┐
 QA.outbox ─┼─▶ [SMM doorway] ──hourly batch──▶ Operator (one chat)
 FM.outbox ─┘         ▲                              │
                      └──────── reply routing ◀───────┘
```

**Why a doorway:** the operator talks to one agent; the rest of the team still runs. Without it, a single-interface operator becomes the bottleneck for every agent's output.

---

## Doorway rules (must be explicit)

A doorway without these is a message-loss bug:

1. **Read/ack state.** A message is delivered only when its relay is confirmed. The `delivered` flag is set **after** the operator's ping is sent, not before — otherwise a crash mid-relay silently drops it.
2. **Dedupe.** Relayed messages are never re-sent. The `id` is the dedupe key.
3. **Urgency lane.** `priority: urgent` (and `kind: blocked`) do **not** wait for the hourly batch. The doorway surfaces them immediately. Hourly is for the routine queue only.
4. **Scope.** The doorway reads only the outboxes it is configured to read. An SMM doorway does not read the Finance Manager's outbox unless the operator said so.
5. **Attribution.** Every relayed line is tagged with its origin agent, so the operator's reply can be routed back correctly.
6. **Missed cycles.** If the doorway is down, messages accumulate — they are **not** lost, because the `delivered` flag never got set. On recovery, the doorway sends everything undelivered.

---

## What goes in an outbox

Only things the **operator** must see: decisions needed, blockers, completed deliverables, anomalies. Not routine logs, **not chatter between agents** (that goes agent-to-agent directly, landing in the peer's `inbox/`), not "I'm still working".

An agent that fills its outbox with noise gets muted by the operator — and then real blockers are missed. **Assert-meaningful, not assert-noisy.**

---

## What goes in an inbox

Work assignments, **questions and messages from other agents**, and routed operator replies. An agent **checks its inbox at the start of any unit of work** — that is the contract that makes dispatch reliable without a live push.

Note the asymmetry, and that it is intentional: the **inbox accepts peer messages**, but the **outbox never sends them**. A peer exchange is written to the *recipient's* inbox, not the sender's outbox.

---

## The no-op guard

The failure this design exists to prevent: a mailbox that *looks* healthy while nothing flows. Cadre's rule (from the paper's §6.5): **assert on the existence of expected artifacts.**

- If an agent had work and its outbox is empty when the cycle runs, that is an **anomaly**, not a quiet hour.
- The doorway reports "0 messages" only when it has confirmed there *were* no messages to send.
