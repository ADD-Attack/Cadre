# Reference — Agent Collaboration

How persistent agents work *together*: who may contact whom, how work moves between them, and the
guards that keep a collaborating team from decaying into a loop, a collision, or a silent stall.

Companion to [messaging.md](./messaging.md), [guardrails.md](./guardrails.md), and [autonomy.md](./autonomy.md).

---

## 1. Send directly to the intended recipient

Use the deployment's configured OpenClaw route to contact the operator or the specific teammate who
needs the information. The recipient inbox may preserve a durable handoff when that convention is
installed, but a file is not a delivery mechanism or a second canonical task record.

See [messaging.md](./messaging.md) for recipient routing, durable inboxes, and delivery verification.

## 2. The peer channel has **two mechanisms**, and they are gated differently

This is the subtle part, and getting it wrong is a real bug: *spawning* an agent and *messaging* an
agent are **different operations with different allowlists**.

| Mechanism | What it does | Gate |
|---|---|---|
| **Dispatch (spawn)** | starts a fresh run *under the target agent's own brain* (its sessions, tools, eyes) | `agents.defaults.subagents.allowAgents` |
| **Message** | sends text to an existing/standing agent session | `tools.agentToAgent.allow` |

**They do not overlap by default.** A team can be configured so that agent A may *message* agent B
but may *not spawn* B — and vice versa. A common shape: the supervisor may spawn **only the builder lanes**, while every standing agent may message every other. So **"can they talk?"
and "can they be spawned?" are two separate questions.**

**Consequences to design for:**

1. **Do not write a dispatch brief that assumes spawn works for every agent.** Some lanes are
   *message-only*; a spawn to them is refused.
2. **A refusal is a routing fact, not a config bug.** When a spawn is refused unexpectedly, fall back
   to messaging that agent — don't conclude the config is wrong.
3. **A spawn gate may be cached in the running session.** After changing the allowlist, the live gate
   can still report the old list until the runtime reloads. The trap: `openclaw config set` can report
   *"Change will apply without restarting the gateway"* even when the spawn gate is **not** actually
   hot-reloadable — so `config get` shows the new list while the spawn still refuses with the **old**
   one. Do not route around the refusal, and do not conclude the config is wrong: the value is already
   persisted, so **restart the gateway**, then **re-verify by attempting the spawn** — reading the config
   back is not proof the gate has reloaded.
4. **Wiring is a bootstrap order, not a single step.** The agent that *spawns* a teammate must be able
   to spawn it *before* that teammate exists to wire its own door — so the spawner adds the target to
   `allowAgents` (and to `agentToAgent.allow`) first, and confirms the change took effect, before the
   spawn. The spawner cannot delegate this one to the thing it is creating.

**Which mechanism to use.** Spawn when the work needs the target's *own* capabilities (its tools, its
verification, its context) and should run under its identity. Message when you need to *talk* to an
agent that already exists — a question, a handoff, a steering note.

---

## 3. The lifecycle of an owned outcome

Collaboration is not free-form chat. Keep one accountable owner and one canonical work record, then
pull in the roles needed for this outcome:

```
Operator ──▶ Accountable owner / PM
                │
                ▼
             Requirements / design / build / support as useful
                ▼
             Owner checks progress against acceptance points
                │
                ▼
             Result + EVIDENCE ──▶ focused independent review when risk or criteria warrant it
                │
                ▼
             Owner resolves findings and hands off to operator
```

Requirements, design, implementation, and review are functions—not required approval gates in every
project. Keep operational board status synchronized with the canonical task and acceptance record;
FlowBoard, when integrated, is a mirror until an explicit board migration.

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
advisory.* (See [`guardrails.md`](./guardrails.md) §2: adopt a claim tool plus a pre-commit hook — the
enforcement surface is the operator's, and it must be labeled *enforced* or *advisory*.)

The corollary for collaboration: **parallel lanes must hold disjoint scopes.** If two lanes truly
need the same file, they *serialize* — they do not share.

### 4.3 Dispatch-and-verify — collaboration cannot silently stall

Handing work off is **one step, not the whole job.** The dispatcher owns an **armed check-in** on
that lane until it is verified complete. A lane that stops with work remaining is the *dispatcher's*
failure to catch, not the worker's. Without this, "dispatched" quietly becomes "abandoned," and the
operator discovers it hours later. The check-in must be a real armed mechanism — never "I'll remember."

### 4.4 Evidence over status — collaboration cannot self-certify

A handoff carries a **result plus evidence**, never a status. "Running" is not "done." The outcome
owner checks work against its acceptance points as it proceeds. When the risk or acceptance target
requires an independent verdict, the reviewer must be a **different agent** than the builder. A
separate QA seat makes that review available; it does not make every low-risk change wait for QA.

Preserve the identity of the artifact that was reviewed and report any criterion that remains
unverified. There is no fixed pass-count ceiling: continue while a check adds useful evidence or
resolves a finding, and stop repeating unchanged checks that do not.

---

## 5. Escalation topology — direct, authorized routes

The operator's configured OpenClaw channel reaches the main agent or the explicitly designated outcome
owner. Agents send blockers, decisions, and handoffs directly to the intended recipient through the
supported route. If durable workspaces are used, preserve the recipient-side record in that agent's
inbox and keep the canonical state in the task/project record.

A missing route is a real blocker. Preserve the exact delivery failure and notify the accountable
owner. Use another already-authorized route only when it preserves the same recipient and privacy
boundary; only an authorized owner may change route allowlists. Keep emergency routes disabled unless
the operator explicitly configures and tests them.

See the [team topology](../diagrams/topology.md).

## 6. Headless safety — a collaborator that cannot be asked

An agent with no operator conversation surface must **deny `ask_user`** (or any blocking
human-input tool), or it will hang forever waiting for an answer. This is a collaboration
requirement: a headless agent escalates through a non-blocking direct message or canonical task record, never by opening a blocking prompt. Every headless agent must set this; new ones must too.

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
