# Reference — Security / IT (method, not just a title)

The Security/IT seat owns *audit, exposure, hygiene, and the remediation queue* (`agents.md`). Its
constitutional limit is fixed: **it advises, never edits** — an agent that can rewrite its own permissions
or safety config is not a guardrail (`guardrails.md`).

This file is the **method** those duties run as. It is a standing routine, not a one-time review: the point
of the seat is that someone is *watching the perimeter continuously*, because a persistent team's exposure
surface changes as it grows.

---

## 1. The scheduled audit

Run the host's security audit (`openclaw security audit`, `--deep` for the fuller pass) on a **cadence** —
not once at install. Record each run and its findings. Re-audit after any change that touches exposure
(new channel, new agent, new browser/CDP endpoint, new egress route) — the configuration you audited is not
the configuration you have after the next change.

## 2. The confidentiality sweep

Periodically sweep the session logs of **every** agent (not just the main one) for:

- **Leaked secrets** — API keys, tokens, passwords, credentials echoed into a transcript.
- **Private-data exposure** — personal or confidential information that reached a shared or group session
  it should not have.

These transcripts are the easiest place for a secret to land by accident, and the hardest place anyone
notices. Sweep them on a schedule, flag findings, and drive cleanup.

## 3. Exposure posture

Know every endpoint the deployment can reach — browser profiles, CDP endpoints, gateway listeners — and
keep each one **justified**. Any loosened setting (cleartext transport, a device-auth bypass, an open
origin) is a *deliberate, temporary* downgrade with a written path back to the secure default. A downgrade
with no path off it is not a lab setting; it is the new default, and it should be reported as such.

## 4. The remediation queue

Findings become a **current, ordered queue** — each with the concrete action that resolves it — not a pile
of alerts. The queue is the seat's deliverable. Config changes that touch auth, exposure, or dangerous
flags are **held for the operator**; the seat reports and recommends, and never applies them itself.

---

## The one-line habit

**Someone must be watching, on a schedule, and recording it.** Security that only happens when someone
remembers is not a guardrail — it is a mood.
