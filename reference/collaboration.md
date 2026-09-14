# Reference — Agent Collaboration

How persistent agents work *together*: who may contact whom, how work moves between them, and the
guards that keep a collaborating team from decaying into a loop, a collision, or a silent stall.

Companion to [`mailboxes.md`](./mailboxes.md) (the two channels), [`guardrails.md`](./guardrails.md)
(the failure modes and their caps), and [`autonomy.md`](./autonomy.md) (what an agent does alone).

---

## 1. There are two channels, and they are not interchangeable

| Channel | Direction | Mechanism | Lands in |
|---|---|---|---|
| **Peer** (agent ↔ agent) | either way | a direct message between agents | the **recipient's `inbox/`** |
| **Operator** (agent → human) | one way | the agent's **`outbox/`**, relayed by a doorway | the operator's chat |

Full detail in [`mailboxes.md`](./mailboxes.md). The one rule: **the outbox is operator-only;
peer work goes agent-to-agent.** Collaboration happens on the peer channel.

---

## 2. The peer channel has **two mechanisms**, and they are gated differently

This is the subtle part, and getting it wrong is a real bug: *spawning* an agent and *messaging* an
agent are **different operations with different allowlists**.

| Mechanism | What it does | Gate |
|---|---|---|
| **Dispatch (spawn)** | starts a fresh run *under the target agent's own brain* (its sessions, tools, eyes) | `agents.defaults.subagents.allowAgents` |
| **Message** | sends text to an existing/standing agent session | `tools.agentToAgent.allow` |

**They do not overlap by default.** A team can be configured so that agent A may *message* agent B
but may *not spawn* B — and vice versa. In the subject deployment, for example: the PM may spawn
only `worker` and `oscar`, while all six standing agents may message each other. So **"can they talk?"
and "can they be spawned?" are two separate questions.**

**Consequences to design for:**

1. **Do not write a dispatch brief that assumes spawn works for every agent.** Some lanes are
   *message-only*; a spawn to them is refused.
2. **A refusal is a routing fact, not a config bug.** When a spawn is refused unexpectedly, fall back
   to messaging that agent — don't conclude the config is wrong.
3. **A spawn gate may be cached in the running session.** After changing the allowlist, the live gate
   can still report the old list until the runtime reloads.

**Which mechanism to use.** Spawn when the work needs the target's *own* capabilities (its tools, its
verification, its context) and should run under its identity. Message when you need to *talk* to an
agent that already exists — a question, a handoff, a steering note.

---

## 3. The lifecycle of a delegated unit of work

Collaboration is not free-form chat; it is a pipeline with a defined shape:

```
Operator ──▶ Dispatch (spawn or message)
                │
                ▼
             Agent does the work ──▶ may collaborate with peers (message)
                │                        │
                │                        └──▶ routing limit caps the hops
                ▼
             Handoff: result + EVIDENCE ──▶ back to the dispatcher
                │
                ▼
             Dispatcher VERIFIES ──▶ retires the check-in ──▶ reports to operator
```

Each stage has a guard. The guards are what make the shape hold.

---

## 4. The guards on collaboration

### 4.1 Routing limit (hop cap) — collaboration cannot loop

Agents that can message each other can **ping-pong**: A asks B, B asks A, A asks B… nothing breaks
and nothing finishes. A pipeline terminates by construction; a *team* does not. So peer messaging
carries a hard cap — default **6 hops** per unit of work — after which the chain must stop and
escalate. (See [`guardrails.md`](./guardrails.md) §1.) The cap is what turns "the agents are still
working" from a permanent state into a loud failure.

### 4.2 File-claim lease — collaboration cannot collide

Two agents writing one file is a data-loss bug (last writer wins, the other's work vanishes silently).
So **shared-file writes require a claim**: a lane holds an exclusive scope, overlapping scopes are
refused at claim time, and a commit touching another lane's files is refused. *Enforced, not
advisory.* (See [`guardrails.md`](./guardrails.md) §2; in the subject deployment this ships as a
claim tool plus a pre-commit hook.)

The corollary for collaboration: **parallel lanes must hold disjoint scopes.** If two lanes truly
need the same file, they *serialize* — they do not share.

### 4.3 Dispatch-and-verify — collaboration cannot silently stall

Handing work off is **one step, not the whole job.** The dispatcher owns an **armed check-in** on
that lane until it is verified complete. A lane that stops with work remaining is the *dispatcher's*
failure to catch, not the worker's. Without this, "dispatched" quietly becomes "abandoned," and the
operator discovers it hours later. The check-in must be a real armed mechanism — never "I'll remember."

### 4.4 Evidence over status — collaboration cannot self-certify

A handoff carries a **result plus evidence**, never a status. "Running" is not "done." A verifying
agent must be a **different agent** than the builder — or it is not verification. (This is why the QA
role is a distinct seat, and why QA starts at a higher autonomy level.)

---

## 5. Escalation topology — who can reach the operator

Collaboration needs a defined route *out* as much as between peers.

The whole picture — who can reach whom, the optional doorway, and the rework loop — is drawn in [`../diagrams/topology.md`](../diagrams/topology.md).

- **The doorway.** In a single-interface deployment, one agent (often the Social Media Manager) is the
  doorway that batches outboxes to the operator. The operator talks to one agent; the team still runs.
- **The single-conduit risk.** If one agent is the only route to the operator, that agent is a
  single point of failure. The mitigation is a **designated relay**: a second agent the operator can
  route through when the primary is mid-run or unreachable.
- **Break-glass is not a default.** A direct "high-severity, reach the operator *now*" path for
  headless agents is tempting — and dangerous. **Do not treat one as live unless the operator has
  explicitly enabled it.** Until then, escalate through the normal route.

---

## 6. Headless safety — a collaborator that cannot be asked

An agent with no operator conversation surface must **deny `ask_user`** (or any blocking
human-input tool), or it will hang forever waiting for an answer. This is a collaboration
requirement: a headless agent escalates by *writing* a message (`kind: blocked` / `kind: question`),
never by opening a blocking prompt. Every headless agent must set this; new ones must too.

---

## 7. Channel silence — collaboration output, not narration

In a shared or visible channel, an agent's turn ends in **either one clean message or nothing**.
Chain-of-thought and routing commentary stay internal; only deliverables, status, and questions reach
the floor. A visible channel is a shared room — flooding it with intermediate reasoning is not
collaboration, it is noise, and it crowds out the messages that matter.

---

## 8. The design principle

**Collaboration is a topology, not a vibe.** A team of agents that *can* talk to each other will,
unless the topology bounds them: a cap on hops, a lease on files, an armed check-in on dispatches, a
defined route to the operator, and a defined way to be silent. Each guard removes one way a
collaborating team fails differently from a pipeline — loop, collision, stall, unreachable, hung.

> Two agents that can talk are not yet a team. A team is two agents that can talk **and** stop,
> split, hand off, and escalate on cue.
