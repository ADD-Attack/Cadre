# Reference — Verification (evidence, not ceremony)

"The handoff carries evidence, not status" is a rule. This file is the **method** — how an agent actually
produces evidence a verifier can accept, and how a verifier decides. It is distilled from a real team's
hardest lessons: the bug this prevents is *shipping something that functioned but did not match what was
asked*, and passing it off as done.

The QA / Verifier role owns the verdict (`agents.md`). This is what that verdict must rest on.

---

## 1. Restate the request as the pass condition

Before building or verifying, write the pass condition in the requester's **own words**:

> *Pass = [what they asked for], and [what must NOT be true].*

If you cannot write that sentence, you do not yet know what "done" means — ask, don't guess. **Functioning
is not the bar.** "It works" and "it is what they described" are different claims, and only the second one
counts.

The failure it prevents: verifying that a feature *runs* while missing that it does not *look like* what was
described. The check passes; the brief fails.

## 2. Capture the real artifact, not a proxy

Evidence is the thing itself, at the moment the requester would see it — not a computed proxy for it.
**This requires a verifier that can accept images.** The evidence for anything visual is a screenshot or
render, so bind QA to a vision-capable model (native, or the deployment's configured vision route). A
text-only verifier cannot capture what it cannot see — it will pass a blank screen. (`agents.md` — models.)

- **Drive the actual action.** If they will click a button, click that button and capture *that* frame.
- **Not** "element X has class Y" or "the function returned 200" when the claim is about what a person
  sees or receives.
- If the artifact is a file, **open the file**. If it is a page, **load the page**. If it is a command's
  output, **run the command**.

## 3. Check the whole artifact, not one element

A claim about a whole (a screen, a document, a finished build) fails if *any* part of it is wrong — even
when the part you were watching is right. Read the full result as a composition: what else is visible,
present, or missing? "The thing I changed is correct" is not "the artifact is correct."

## 4. "Could not verify" is a required report, never a success

If you genuinely cannot produce the evidence (no browser, no access, no way to run it), **say so
explicitly** — *"not visually verified"*, *"not executed"* — instead of claiming success on a weaker check.
An honest gap is cheap; a false pass is the failure this whole file exists to prevent.

## 5. Independence

The verifier must be a **different agent than the builder**, or it is not verification — it is the same
priorities agreeing with themselves (`agents.md`). Where a build came from a worker agent, QA is always a separate
persistent agent — a dedicated seat, never the builder.

## 6. Bound the loop

Verification is a loop, and an unbounded loop is a bill. Verification is **risk-tiered, with no fixed
round cap** (`guardrails.md` §5): each pass must test a concrete criterion, resolve a finding, or add
decision-relevant evidence. When a loop stops producing value, timebox it: ship with the remaining gap
named, or escalate a genuine hard stop — with the attempts side by side and the gap named. A silent
further pass is the failure.

## 7. One ledger, written once — and claims are not verdicts

*Added 2026-10-13 (see [`overhaul-2026-10-13.md`](./overhaul-2026-10-13.md)).*

Each task has **one evidence ledger**, written **once** by the producer: the pass condition, the
artifact paths, and their hashes. The ledger is not rewritten per checkpoint, and no reconciliation
pass is run unless a concrete discrepancy appears.

A producer's report — "bundle complete" — is a **claim, not a verdict**. Before a claim is reported
complete upward, a different agent **spot-verifies** it: re-open or re-run a sample of the artifacts
and compare hash/output against the ledger. This is the standard control for internal evidence —
**dual verification** (producer output + independent re-run with hash/output comparison) — and it
replaces attestation machinery for anything whose only consumer is the team itself
(`guardrails.md` §7).

The case that earned this section, 2026-10-13: a producer reported a complete four-screenshot
evidence bundle; reconciliation found one file was a **byte-identical alias** of an earlier capture
and one stage had never been reached. The artifacts were real; the *completeness claim* was not.
Spot-verification is cheap. Reporting an unearned "complete" upward is not.

---

## The one-line habit

For any claim worth checking: **did I restate their words as the pass condition, capture the real artifact,
and read the whole of it?** If yes, report what you verified. If no, report that you could not — never the
stronger claim you did not earn.
