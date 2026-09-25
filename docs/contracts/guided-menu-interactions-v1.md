# Guided Menu Interactions v1

- **Issue:** #98
- **Contract:** `vitrine_guided_menu_interaction_v1`
- **Status:** Implemented teacher-interaction contract

## Purpose

Issue #98 standardizes the interaction layer used by active Vitrine teacher
workflows without moving domain authority into menus.

The governing sequence is:

```text
show current state
-> teacher chooses
-> clear/redraw
-> show exact review state
-> controlled confirmation when a write is consequential
-> execute the already-planned exact write
-> clear/redraw
-> show resulting current state
-> offer contextual next action when one is available
```

Menus remain presentation/orchestration surfaces. Canonical services continue to
own identity, applicability, authorization, concurrency, persistence, and domain
validation.

## Controlled confirmation

`confirm_exact_phrase(...)` implements the shared confirmation behavior.

The expected phrase is exact after surrounding whitespace is stripped, with
capitalization ignored. No fuzzy matching, abbreviation, prefix matching, or
semantic inference is permitted.

```text
correct phrase, any capitalization -> confirm
wrong nonblank phrase -> explicit rejection, clear/redraw, retry
blank -> cancel
B -> cancel
M -> ReturnToMainMenu
Q -> QuitPDS
```

A wrong phrase must not silently abandon the action.

The helper may receive a non-mutating `handle_review_action` callback. This is
used for bounded actions such as `T. Technical details / provenance`; a handled
review action redraws the same current confirmation state and is not treated as a
mismatch.

## Required zero/one/many choices

`resolve_required_choice(...)` is cardinality-only guidance for choices that are
already required by the owning workflow:

```text
0 choices -> unavailable; do not prompt
1 choice -> carry the exact object forward; do not prompt
2+ choices -> require explicit teacher selection
```

The helper preserves exact object identity and ordering. It does not rank,
prefer, infer, or manufacture a choice.

It must not be used to bypass meaningful consent or identity decisions. Subject
class/student identity choices, merge/split allocation, Candidate Select versus
Decline, and optional Profile requirement intent remain explicit even when a
particular screen happens to have one visible option.

## Clear/redraw

Multi-step workflows must not accumulate obsolete menus above a consequential
review. The final review renderer owns the visible current state. Confirmation
retry clears and redraws that renderer.

After successful writes, teacher-facing workflows redraw a current-state result
rather than appending success text below obsolete pre-write state.

## Contextual continuation

Issue #98 adds explicit continuation where the next action is known without
changing domain semantics:

- Candidate Selection remains a separate write from Placement, but successful
  Selection may offer `Place now` from refreshed persisted state.
- Candidate discovery may route directly to persisted Candidate Review without
  rediscovery or producer reread.
- Create Portfolio for Student returns the exact newly created Portfolio ID so
  the existing Portfolio context opens it immediately.
- Technical-details drill-down during Current Portfolio confirmation returns to
  the same final review.

Contextual routing never implies hidden mutation.

## Active standardized surfaces

The shared contract is used by active teacher workflows for:

```text
Candidate Review / Selection / Placement / lifecycle / content / review
Candidate discovery
Create Portfolio for Student
Portfolio Profile Binding / migration
Working Composition freeze
Build and Export Current Portfolio
standalone Portfolio Profile mutations
standalone Portfolio Subject mutations
Workspace Settings mutations
```

## Deliberate exclusions

The legacy `_curation_workflow()` helper in `portfolio_menu.py` is dormant and is
not routed from the active Portfolio menu. Issue #98 does not rehabilitate or
expand that dead compatibility path.

Direct noninteractive CLI workflows remain noninteractive.

No confirmation helper grants Snapshot authority, source-read authorization,
Profile applicability, Subject identity, disclosure permission, or delivery
authority.
