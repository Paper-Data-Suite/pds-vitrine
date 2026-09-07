# Guided Candidate Review and Selection development

Issue #66 implements teacher-guided Candidate review as orchestration over the
Candidate Inbox and canonical curation services. This document describes the
implementation boundary and the safe extension points.

## Module map

```text
vitrine/candidate_inbox.py
  authoritative persisted review listing/detail projection

vitrine/candidate_review.py
  presentation-independent #66 detail, plans, and executors

vitrine/candidate_review_menu.py
  teacher-facing Portfolio review/curation UI

vitrine/candidate_review_cli.py
  noninteractive task-level Candidate review CLI

vitrine/curation_services.py
  canonical Proposal/Decision/Selection/Placement/Annotation/Reflection/Review writes
```

`candidate_review.py` does not own Candidate discovery or producer reads. Do not
add ScoreForm/Quillan/Concord reader calls there to make a detail screen feel
"fresher". The teacher must explicitly run Discover Candidates when a new source
read/evaluation is intended.

## Read path

Use the Candidate Inbox as the only Candidate review entry algorithm:

```python
result = list_candidate_review_entries(
    workspace,
    CandidateInboxQuery(portfolio_id=portfolio_id),
)
detail = get_candidate_review_detail(workspace, entry_id)
```

The detail reloads canonical Vitrine curation state and requires its state
revision to match the Candidate Inbox observation. A concurrent change fails
with `candidate_review.state_changed`; callers should show the conflict and ask
the teacher to reopen/replan rather than silently retrying.

Evaluation-only `ineligible`/`unresolved` entries are intentionally returned by
the Inbox but `detail.selectable` is false. Suppressed entries never reach this
layer.

## Decision planning and execution

For a fresh Candidate decision, plan first:

```python
plan = plan_candidate_decision(
    workspace,
    entry_id=entry_id,
    decision="select",  # or "decline"
    proposed_section_ids=("later_work",),
    intended_profile_requirement_ids=(),
)
```

The plan freezes:

```text
observed state revision
Candidate identity
current review Evaluation
immutable curation provenance Evaluation
Candidate condition and stale state
exact explicit section intent
exact optional Profile requirement intent
operation and confirmation phrase
```

Execute that exact plan with the attributed actor and injected authority gate:

```python
result = execute_candidate_decision(
    workspace,
    plan,
    actor=actor,
    authority_gate=authority_gate,
)
```

Do not reconstruct a new plan inside the executor. Do not replace the observed
state revision with the current revision just before writing.

Fresh select uses `select_candidate_directly(...)`. Fresh decline uses
`reject_candidate_directly(...)`. Existing undecided Proposals remain exact
Proposal decisions rather than being silently replaced by a fresh Proposal.

## Placement

Acceptance is not Placement. Plan and execute Placement separately:

```python
placement_plan = plan_selection_placement(
    workspace,
    entry_id=entry_id,
    selection_id=selection_id,
    section_id="later_work",
)
result = execute_selection_placement(
    workspace,
    placement_plan,
    actor=actor,
    authority_gate=authority_gate,
)
```

The plan carries the exact observed Arrangement pointer revision. Never infer a
section from Proposal intent.

## Withdrawal

`plan_selection_withdrawal(...)` freezes the exact active Selection, reason,
affected active Placements, affected sections, and Arrangement pointer
observations. `execute_selection_withdrawal(...)` reuses the append-preserving
canonical service.

The UI confirmation phrase is presentation safety, not authorization. Authority
still comes from `CurationAuthorityGate`.

## Replacement

Guided replacement intentionally has stricter explicitness than the retained
low-level compatibility API. Callers must supply:

```text
successor entry
explicit proposed_section_ids
placement_dispositions for every active old Placement
reason
```

A disposition maps each old Placement to one exact successor section or `None`
(drop). Missing dispositions fail planning. The guided path always passes
explicit `proposed_section_ids` to `replace_selection(...)`; it must never enter
the legacy section-intent derivation branch.

## Annotation and Reflection

Use planner/executor pairs:

```text
plan_annotation_creation / plan_annotation_revision
execute_annotation_action

plan_reflection_creation / plan_reflection_revision
execute_reflection_action
```

Revision plans bind one exact current revision head. Annotation content and
Reflection content remain canonical bodies and are not projected into low-density
Candidate list/detail summaries.

Comparison Reflection target roles are explicit `CurationTargetRef` semantics;
do not infer baseline/later roles from timestamps, Arrangement order, or source
revision.

## Curation Review

`plan_curation_review(...)` requires exact immutable target references and, when
used, an exact Profile approval requirement ID. `execute_curation_review(...)`
reuses the canonical Review service and authority gate.

A Review of revision 1 never implicitly approves revision 2. Curation approval
is not recipient/disclosure authorization.

## Teacher menu

The Portfolio menu routes option 4 to `run_candidate_review_menu(...)`:

```text
3. Discover Candidates
4. Review Candidates / Selections
```

Keep those actions separate. The guided menu should call `candidate_review.py`
planners/executors rather than constructing canonical curation records directly.

## Direct CLI

The task-level commands are registered under `candidate` by
`candidate_review_cli.configure_candidate_review_parsers(...)` and dispatched
through `run_candidate_review_command(...)`.

The CLI is noninteractive and requires explicit IDs/targets. `candidate decide`
handles fresh `select|decline`; an existing undecided Proposal remains available
through the exact low-level `selection decide` command. Do not infer a Proposal
ID for the task-level command.

## Authority and conditions

Every mutation receives `dependencies.curation_authority_gate`. Production
defaults remain fail-closed. Never substitute actor identity, a confirmation
phrase, or a UI acknowledgement for authority.

`--acknowledge-condition` and menu acknowledgement only attest that the teacher
reviewed the displayed Candidate condition. They do not clear or satisfy the
condition. Positive Selection still requires the authority decision to permit
and acknowledge applicable conditions.

## Validation

Focused acceptance:

```powershell
python -m pytest `
  tests/test_candidate_review.py `
  tests/test_candidate_review_actions.py `
  tests/test_candidate_review_selection_management.py `
  tests/test_candidate_review_curation_content.py `
  tests/test_candidate_review_menu.py `
  tests/test_candidate_review_cli.py `
  tests/test_candidate_review_acceptance_matrix.py
```

Architectural validator:

```powershell
python scripts/validate_candidate_review_selection.py
```

Installed wheel smoke:

```powershell
python scripts/smoke_test_candidate_review_selection_wheel.py `
  .\dist\pds_vitrine-0.2.0-py3-none-any.whl `
  "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl"
```

Complete qualification:

```powershell
python scripts/validate_repository.py `
  --core-wheel "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl" `
  --allow-dirty `
  --reuse-static-caches
```
