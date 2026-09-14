# Reference — Scheduled work (timers, sentinels, and what a team may run on its own)

Persistence means the team can wake itself: reminders, recurring sweeps, watchers. That is also the
main way a quiet team becomes a quiet **bill**. This file is the policy for *what may run on a
schedule, in what form, and who is accountable for it.*

**Owner: the Finance Manager** (`agents.md`) owns the cost side of this file, because scheduled work
is where recurring spend is created.

---

## The two mechanisms — pick by the question, not by habit

| The work is… | Mechanism | Idle cost |
|---|---|---|
| "do X **at time T**" (a reminder, a daily digest) | **Timer** — a scheduled task at a wall-clock time or interval | $0 between ticks *if* the payload is a script; a model turn costs on every tick |
| "do X **when condition C becomes true**" (new mail, build finished) | **Sentinel** — a headless condition check that fires the payload only on the transition | **$0** — the check is deterministic and runs without the model |

**The rule:** *a condition is watched by a sentinel, never by a timer polling it.* An hourly model
turn that wakes to ask "anything new?" is the expensive mistake (`guardrails.md` §6 — the case that
burned ≈$8.03 across 312 turns while nothing was happening).

## Timers (scheduled tasks)

Use a timer when the *time* is the trigger. These are the gateway's automations:
`schedule { kind: "at" | "every" | "cron" }` with a `payload` of `systemEvent`, `agentTurn`, or
`script`.

- **A one-shot reminder** is `kind: "at"` — it fires once and is removed after it succeeds.
- **A recurring agent turn is a recurring cost.** `kind: "every"` or `"cron"` with an `agentTurn`
  payload bills on every fire, whether or not there was anything to do. Schedule one only when the
  work genuinely must happen on the clock.
- **Prefer a `script` payload** for routine scheduled work: it is deterministic and does not spend
  model tokens just to report "nothing to report".

## Sentinels (condition watchers)

A sentinel is a small, **read-only** check that runs headless and **costs nothing while the answer is
"nothing to do".** The primitive is a **trigger**: a `trigger.script` attached to a scheduled job,
returning `{fire, message, state}`.

- **Read-only.** The check observes; the *payload* is what acts. A sentinel never mutates state.
- **Dedupe on state.** Return the new `state` so a condition that stays true does not re-fire every
  tick — a fire-once latch, not a level alarm. Dedupe from recorded state, never from model memory.
- **Self-contained message.** The model wakes only when `fire` is true, and the trigger's `message`
  is that run's *entire* context — so it must say what happened without the model re-deriving it.
- **Fire on failure too.** A watcher that only fires on success goes silent exactly when it is
  broken.
- **A supervised `stream` schedule** (fires on a process's output lines) is the other zero-token
  form: the process runs, and the model wakes only on a matching line.

## What a Cadre team must not do

- **No model turn as a timer.** "Wake every 10 minutes and check" is banned — that is a sentinel's
  job.
- **No `sleep` / poll loop as a scheduler.** Waiting is the gateway's job; a shell loop that sleeps
  and re-checks is both a stray process and a hidden meter.
- **No hourly-forever wakeup "just in case."** A recurring job owes a purpose and a cadence. If
  neither can be stated, it is a leak, not a watcher.
- **No unattributed job.** Every scheduled job names an **owner**, so a cost question always has an
  answer.

## Finance Manager: the scheduled-work audit

FM owns this file's cost side. On its cadence, FM lists the deployment's scheduled jobs and checks
each against three questions:

1. **Owner?** Every job names the agent responsible. An orphaned job is a finding.
2. **Purpose + cadence?** The job can state why it exists and why that often. "Just in case" is a
   finding.
3. **Idle cost $0?** A job whose tick spends tokens while nothing is happening is a finding — rewrite
   it as a sentinel (`guardrails.md` §6).

Findings go in FM's report and the remediation queue. FM **reports and recommends** — it does not
delete another agent's job unilaterally (that is an operator decision, like every other config
change).

---

## The one-line rule

**A timer is for something that must happen at a time. A sentinel is for something that must happen
on an event. Paying model rates to wait is a bug you can choose not to write.**
