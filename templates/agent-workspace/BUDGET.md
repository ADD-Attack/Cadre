# BUDGET.md — <agent name>

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
