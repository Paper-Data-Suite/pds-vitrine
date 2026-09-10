# Attention and Next Actions development

Issue #69 adds one read-only Vitrine projection over existing workflow authority.
The contract is documented in
[Attention and Next Actions v1](../contracts/attention-next-actions-v1.md).

## Runtime files

The runtime surface is intentionally small:

```text
vitrine/attention.py
vitrine/attention_cli.py
vitrine/attention_menu.py
```

`vitrine/attention.py` owns semantic interpretation. CLI and menu code are
presentation adapters only.

No durable attention model family exists.

## Release baseline

Develop and qualify this code against:

```text
pds-core 0.6.3
ScoreForm 0.11.0 compatibility anchors
Quillan 0.10.0 compatibility anchors
Concord 0.3.0 compatibility anchors
```

Only Core is a runtime dependency. The other released modules remain optional
producer/sibling systems.

Portia has no published GitHub Release at this issue boundary and is not a
runtime dependency or compatibility requirement for issue #69.

## Evaluation flow

One evaluation follows this order:

```text
load exact current Vitrine state
-> resolve exact Portfolio scope
-> Candidate Inbox projection per Portfolio
-> curation Proposal/Selection state
-> guided Working Composition preparation per Portfolio
-> Snapshot state projection
-> exact current build-chain resolution
-> producer-independent custody/Export verification
-> re-check canonical Vitrine state revision
-> deterministic aggregation
```

The final state-revision recheck prevents one report from mixing facts derived
from different canonical revisions.

## Candidate source

Do not reimplement Candidate currentness in attention code.

Use `list_candidate_inbox()` for:

```text
current Evaluation
staleness
unresolved Evaluation-only entries
current Profile/Core source observations
```

Candidate review pending is a curation-state question layered over that inbox:
a current positive Candidate/Evaluation remains pending until the exact
Evaluation has an explicit curation disposition.

Do not add a seen/read acknowledgement simply to clear attention.

## Curation source

Use current curation projection for:

```text
Proposal heads
Proposal Decisions
active Selections
Selection conditions
active Placements
```

Review/Requirement/Composition interpretation should come from guided Working
Composition preparation rather than duplicated Profile parsing.

## Working Composition source

`prepare_working_composition()` is read-only and is the authority for:

```text
create_initial / create_successor / reuse_exact_current
structured Requirement statuses
Review requirements and follow-up
unplaced Selections
unresolved obligation codes
```

Do not infer completeness from display text.

## Snapshot source

Use `project_snapshot_state()` and predecessor links to identify current Series,
Request, and Plan heads.

Within one exact Plan, `attempt_number` is the canonical Attempt sequence. Do not
use `started_at`, `completed_at`, filesystem order, or opaque identifiers to pick
a current Attempt.

Historical failed Attempts remain durable history but should not produce current
attention after an exact later Attempt supersedes them.

Use `inspect_snapshot_custody()` for custody findings. Unscoped anomalies are
workspace-level unless canonical state ties them to a Portfolio.

## Export verification

Export Artifacts do not retain `export_plan_id`. Match a current Export to an
exact sealed Edition and the persisted immutable Export Plan commitments:

```text
export_format
export_contract_version
configuration_digest
```

Then resolve the Export predecessor head explicitly.

Use `verify_snapshot_export()` rather than building a second directory verifier.
The verifier is producer-independent and observational.

## Aggregation

Add new attention codes only by extending the frozen definition table in
`vitrine/attention.py` and the contract/validator together.

Every code needs:

```text
fixed label
count unit
attention class
owner action ID
semantic authority
```

Definition order controls output order. It is not priority order.

Workspace aggregation may collapse exact Portfolio scope when the same code
spans multiple Portfolios. Do not emit unbounded per-item identifiers in shared
summaries.

## Privacy

Keep shared summaries low density. Rich local drill-down stays in the existing
Vitrine owner workflow.

Do not add student names, Scores, writing, feedback bodies, source paths, raw
exceptions, manifests, credentials, or recipient details to the attention DTOs.

## CLI

The direct read-only command is:

```text
vitrine attention list
vitrine attention list --portfolio-id PORTFOLIO_ID
```

The CLI returns status 1 for `evaluation=unavailable` while still printing the
contract/evaluation envelope. It never prompts and never executes an owner
action.

## Teacher menu

Main menu option 6 shows workspace attention.
Portfolio option 7 shows the exact Portfolio scope.

The menu displays fixed owner-action labels and stable action IDs. It returns to
the caller after one current projection; existing workflow surfaces still own
all mutations and confirmations.

## Core module-operations handoff

Do not add a `paper_data_suite.module_operations` entry point in issue #69.

Issue #70 should adapt the Vitrine report into Core 0.6.3 neutral operation DTOs
without rereading Vitrine private storage or recreating interpretation.

`attention != readiness`; do not add a `ready` boolean here.

## Focused qualification

Run:

```powershell
python -m pytest `
  tests/test_attention.py `
  tests/test_attention_snapshot.py `
  tests/test_attention_cli.py `
  tests/test_attention_menu.py `
  tests/test_attention_acceptance_matrix.py `
  tests/test_validate_attention_next_actions.py

python scripts/validate_attention_next_actions.py

python -m ruff check `
  vitrine/attention.py `
  vitrine/attention_cli.py `
  vitrine/attention_menu.py `
  scripts/validate_attention_next_actions.py `
  scripts/smoke_test_attention_next_actions_wheel.py

python -m mypy `
  vitrine/attention.py `
  vitrine/attention_cli.py `
  vitrine/attention_menu.py `
  scripts/validate_attention_next_actions.py `
  scripts/smoke_test_attention_next_actions_wheel.py

python -m pip check

git diff --check
```

Complete acceptance is defined in
[Issue #69 validation](../validation/issue-69-attention-next-actions-validation.md).
