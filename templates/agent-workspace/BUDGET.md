# BUDGET.md — <agent name>

> **Deprecated (2026-10-13):** this per-role envelope format is a DeepSeek-token-era system and is no longer in force. It is superseded by one shared Codex quota pool (5-hour + weekly windows) for the whole fleet, with headroom tracked by Agent Resources. Kept for history only.

unit: tokens            # tokens | currency
period: daily           # daily | weekly | monthly
ceiling: 100000
threshold: 80           # percent at which to alert
enforcement: warn       # warn | cap
last_reset: <ISO-date>
spent_this_period: 0

<!--
This file is accounting + policy, not persuasion.
An agent cannot reliably count its own spend; the platform's usage reporting is
the source of truth. Finance Manager (or the operator, without FM) reads that,
compares to `ceiling`, and acts per `enforcement`.

Only the operator may raise a ceiling.
-->
