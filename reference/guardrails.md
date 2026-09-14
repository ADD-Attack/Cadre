# Reference — Guardrails

The paper this system comes from (*Persistent Agent Teams*) names four guardrails for the failure modes that **persistence** introduces. Pipelines don't have these problems because pipelines die. Teams do.

Every Cadre install should have all four. They are cheap; the failures they prevent are not.

---

## 1. Routing limit (hop cap)

**Problem.** Persistent agents that can message each other can also ping-pong. A dispatches to B, B asks A, A asks B… nothing breaks and nothing finishes. A pipeline terminates by construction; a team doesn't.

**Rule.** A hard cap on agent-to-agent hops within one unit of work. Default: **6 hops**.

When the cap is reached:

1. Stop routing.
2. Write a `kind: blocked` message to the outbox with the chain that hit the cap.
3. Escalate to the PM (or the operator).

**Why 6.** Deep enough for PM → worker → QA → PM → fix → QA. Shallow enough that a loop is obvious. The PM may raise it per project; nothing may raise it automatically.

**Anti-pattern it kills:** "the agents are still working" as a permanent state. A capped chain fails loudly; an uncapped one fails silently.

---

## 2. File-claim lease

**Problem.** Two agents writing one file is a data-loss bug. Last writer wins; the other's work vanishes with no error. This cannot happen in a pipeline (one process) and *must* be prevented in a team.

**Rule.** One writer per file at a time, **enforced — not advisory.**

### The mechanism

A claims directory in the project, one file per claim:

```
PROJECT/
  .claims/
    <path-hash>.claim
```

A claim file contains:

```
path: memory/SHARED.md
owner: project-manager
scope: write
leased_until: 2026-09-14T05:31:00Z
```

### Protocol

1. **Before writing** a shared file, create its claim. If a live claim exists, **do not write** — the file is owned.
2. **Lease, never own forever.** A lease expires (default **30 min**). Expiry is the recovery path for a crashed agent; without it, one dead agent blocks a file permanently.
3. **Renew** if the work is longer than the lease.
4. **Release** when done — the claim file is deleted. A released claim lets the next writer in without waiting for expiry.
5. **Contention is reported**, not silently resolved: if a claim is refused, that goes to the outbox as `kind: blocked`.

### Enforcement, honestly

A claim written only in prose is advisory. Enforcement needs teeth:

- **Preferred:** a small script that checks-then-writes (a pre-commit hook or a `claim`/`release` helper). Cadre does not ship one binary; adopt the convention your deployment can enforce — a hook, a wrapper, or a lock utility.
- **Minimum:** the file lock is checked by every agent before every shared write, and a violation is a reportable incident. Advisory is better than nothing; enforced is the goal. **Say which one you have.**

### What is shared vs private

- **Private** (one writer by definition): an agent's own `MEMORY.md`, its `inbox/`, its `outbox/`. No claim needed — only the owner writes these.
- **Shared** (claim required): `SHARED.md`, project files, `PROJECT.md`, any spec more than one agent touches.

---

## 3. Promotion gate

**Problem.** What enters long-term memory is a policy decision, and an unset policy still decides — by default. The paper's case study is exactly this: a gate with runtime defaults **promoted 0 of 1,229** entries for a week while every report said success.

**Rule.** An **explicit, authored** policy for what enters long-term memory. Never leave the gate to defaults.

- Set the thresholds on purpose, in the deployment's config or the workspace convention — not by omission.
- Use **loose** gates with **size-triggered eviction** (see [`memory.md`](./memory.md)), not a strict bar calibrated for a busier instance.
- **Loud on zero:** promoting zero while candidates existed is an **anomaly**, not a quiet week. It must warn.

**The test:** if your promotion report says `0 promoted` and nothing alerts, the gate is broken — even if the config looks fine.

---

## 4. No-op detector / heartbeat

**Problem.** The signature failure of a persistent team: **a pipeline that produces nothing throws; a team that produces nothing reports success.** Absence of errors is not evidence of work.

**Rule.** **Assert on the existence of the artifacts a healthy run must produce.** Not "were there errors" — "did the work land."

- A completed task must produce its output file. Missing output = failed task, regardless of status messages.
- A mailbox cycle that delivers "0 messages" must first confirm there were 0 messages to send.
- A memory cycle must show a visible change in some tier, or be reported as a no-op.

**Cadre's rule of thumb:** *assert-meaningful, not assert-noisy.* Check the few artifacts that prove work happened; don't log everything and call it monitoring.

---

## How they fit together

| Guardrail | Failure it prevents | Cost of skipping |
|---|---|---|
| Routing limit | infinite ping-pong | work never finishes, silently |
| File-claim lease | two writers, one file | silent data loss |
| Promotion gate | memory never promotes | the §6 case study |
| No-op detector | work that looks done and isn't | false success |

All four are properties **persistence** creates. Which is why the paper's thesis is short: **a persistent team is a distributed system, and it inherits distributed-systems failure modes.**
