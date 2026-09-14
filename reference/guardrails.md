# Reference — Guardrails

The paper this system comes from (*Persistent Agent Teams*) names four guardrails for the failure modes that **persistence** introduces. Pipelines don't have these problems because pipelines die. Teams do.

Two more come from the *cost* side, where a persistent team's real risk isn't a crash — it is **quiet, recurring spend**. They are guards 5 and 6 below.

Every Cadre install should have all six. They are cheap; the failures they prevent are not.

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

## 5. QA cap (the retry loop has a ceiling)

**Problem.** Verification is a loop, and an unbounded loop is a bill. With no cap, the cheapest available action is always *check it again* — so it is taken until a human notices. The motivating case: one agent captured the same screen **30 times in a single day** because nothing bounded the retry.

**Rule.** **At most two review rounds per artifact.** A round = render the artifact, check it against the spec, give a verdict, and apply the fix the verdict implies. The second round is the last one.

- **Pass** → ship it.
- **Still failing on round 2** → **stop and escalate to the operator** with both attempts side by side and the remaining gap named. A third pass is refused.

**Enforcement.** Where a script can hold the counter, have it refuse the third round outright rather than trusting memory. Escalating at the cap is the correct cheap move, not a failure — a silent fourth pass is the failure.

---

## 6. Zero-token checks (idleness must be free)

**Problem.** A continuous check — "is there new mail?", "did the build finish?" — is usually written as a model turn: wake, call a tool, report. That makes *idleness itself* expensive, and the cost scales with how many things you watch and how often, **not** with how many events actually happen. A watcher built this way burned **≈$8.03 across 312 turns** while nothing was happening.

**Rule.** Run routine checks as a **deterministic headless script** (a *sentinel*), not a model turn. The model wakes **only when the condition is true**.

- Idle must cost **$0**. If a check costs tokens when the answer is "nothing to do", it is the wrong mechanism.
- De-duplicate on observed **state**, so a condition that stays true does not re-fire every tick.
- A recurring watcher needs a purpose and a cadence that makes sense. An hourly-forever wakeup "just in case" is not a watcher; it is a leak.

**Litmus:** *does this tick cost tokens when nothing is happening?* If yes, rewrite it as a sentinel.

---

## How they fit together

| Guardrail | Failure it prevents | Cost of skipping |
|---|---|---|
| Routing limit | infinite ping-pong | work never finishes, silently |
| File-claim lease | two writers, one file | silent data loss |
| Promotion gate | memory never promotes | the §6 case study |
| No-op detector | work that looks done and isn't | false success |
| QA cap | an unbounded review loop | a bill that grows while nothing improves |
| Zero-token checks | idleness billed as work | recurring spend with no event to show for it |

All six come from **persistence** — the first four from its *failure* modes, the last two from its *cost* modes. Which is why the paper's thesis is short: **a persistent team is a distributed system, and it inherits distributed-systems failure modes.** A team that stays up is also a team that keeps *billing*, so its cost discipline is a guardrail, not an optimisation.
