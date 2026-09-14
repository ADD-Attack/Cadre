# Reference — Design (the hand-off a builder can execute without guessing)

The Project Designer takes the Requirements Analyst's doable scope and turns it into the two artifacts
that make a build predictable: a **feature inventory** and a **style guide** — then an ordered,
verifiable hand-off to the PM.

**The test of a design:** could a competent builder execute it **without coming back to ask what was
meant?** If not, the design is not finished. Ambiguity passed downstream is a defect, and it is
cheaper to remove here than anywhere else.

---

## Artifact 1 — the feature inventory

Every feature, named, one row each, each traceable to an acceptance criterion. This is how scope stays
visible and how nothing gets silently dropped (or silently added) during the build.

| # | Feature | Acceptance criterion (from requirements) | Depends on | Notes |
|---|---|---|---|---|
| 1 | <name> | <the observable fact that proves it> | — | <constraints> |

Rules:

- **No orphan features.** Every row traces to a criterion; every criterion is covered by a row. A
  feature with no criterion is scope creep; a criterion with no feature is a hole.
- **Name the dependencies.** A feature that needs another first is a *sequence*, not a surprise.
- **Flag the unknowns explicitly.** If a feature's approach is uncertain, say so and mark it for a
  spike — do not paper over it with confident prose.

## Artifact 2 — the style guide

The conventions the work must follow, so "done" looks and behaves consistently instead of being one
designer's taste per screen. Cover the three layers that actually cause rework:

- **Visual** — palette, type scale, spacing, component look. Reference the existing system if there is
  one; do not invent a second one beside it.
- **Interaction** — how states behave: loading, empty, error, focus, disabled. Most "it feels broken"
  bugs live here, not in the happy path.
- **Technical** — naming, file layout, the patterns to reuse, the patterns to avoid. Keeps the build
  reviewable and the next change cheap.

A style guide is a **short, decisive document**, not a mood board. If it does not settle a choice a
builder would otherwise make alone, it is not earning its place.

## The hand-off to the PM

The design lands as an **ordered task list**, smallest verifiable increments first — this is the
sequence the PM dispatches, and the sequence QA checks against:

- **Foundation before chrome.** Structure, layout, the container layer first; the numerous fine pieces
  (buttons, labels, states) later. A big thing that is *stable* is worth more early than a small thing
  that is *pretty*.
- **Each task independently verifiable.** Every step ends in something a verifier can look at and
  pass or fail on its own — so a failed step is fixed at that step, not guessed at across the whole.
- **One source per decision.** The style guide holds the conventions; the inventory holds the scope;
  neither repeats the other.

## What the Designer does *not* do

It does not build, and it does not re-litigate scope (that is the RA's call — see
[`requirements.md`](./requirements.md)). If the design surfaces a new requirement, it goes **back to
the RA**, where requirements belong, rather than being absorbed into the plan by stealth.
