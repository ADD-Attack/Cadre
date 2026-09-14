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
priors agreeing with themselves (`agents.md`). Where a build came from a worker subagent, QA is a separate
persistent agent.

## 6. Bound the loop

Verification is a loop, and an unbounded loop is a bill. Review is capped at **two rounds per artifact**;
a third is refused, forcing ship-or-escalate (`guardrails.md` §5). Escalating at the cap — with both
attempts side by side and the remaining gap named — is the correct, cheap move. A silent further pass is
the failure.

---

## The one-line habit

For any claim worth checking: **did I restate their words as the pass condition, capture the real artifact,
and read the whole of it?** If yes, report what you verified. If no, report that you could not — never the
stronger claim you did not earn.
