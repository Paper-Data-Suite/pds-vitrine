# Vitrine Attention and Next Actions v1

## Status and identity

Issue #69 defines the first-party, read-only Vitrine attention projection:

```text
vitrine_attention_next_actions_v1
```

The contract answers one bounded teacher question:

> What in Vitrine currently needs review, follow-up, recovery, integrity
> inspection, or explicit awareness?

It does not create a notification system, a readiness score, an urgency score,
or another workflow engine.

## Current release baseline

The contract is developed and qualified against the current released PDS
interoperability baseline:

| Component | Baseline | Relationship |
| --- | --- | --- |
| PDS Core | 0.6.3 | required runtime and owner-action lexical contract |
| ScoreForm | 0.11.0 | existing live producer compatibility anchor only |
| Quillan | 0.10.0 | existing live producer compatibility anchor only |
| Concord | 0.3.0 | existing live producer compatibility anchor only |
| Meridian | 0.2.0 | sibling attention precedent only |
| Paper Data Suite shell | 0.1.0 | later consumer through issue #70 |
| Portia | no published GitHub Release | no release compatibility claim |

Vitrine's runtime floor is:

```text
pds-core>=0.6.3,<0.7
```

ScoreForm, Quillan, Concord, Meridian, Portia, and the suite shell are not Vitrine
runtime dependencies for this contract.

## Ownership boundary

Vitrine owns interpretation of Vitrine state. Core owns neutral module-operation
value contracts. The suite owns later cross-module aggregation.

Issue #69 therefore implements:

```text
canonical Vitrine/Core state
-> Vitrine-owned interpretation
-> VitrineAttentionReport
-> Vitrine CLI / teacher presentation
```

Issue #70 may later adapt this report into Core 0.6.3 module-operation reports.
Issue #69 does **not** register `paper_data_suite.module_operations` and does not
add a Vitrine readiness provider.

The suite must not inspect Vitrine private storage to reproduce these semantics.

## Governing distinctions

The following distinctions are contractual:

```text
attention != urgency ranking
attention != educational risk
attention != readiness
attention != authorization
attention != automatic action
attention != workflow completion
attention != notification delivery

Candidate viewed != Candidate decided
stale != old by wall-clock time
current != greatest opaque identifier

Selection != Placement
Selection condition != Selection invalidity
Curation Review != disclosure authorization

working curation != Working Composition
acknowledged obligation != satisfied obligation

Build Attempt != Edition
Edition != Export
Export != delivery
verification != disclosure authorization
permitted omission != error
historical failed Attempt != current unresolved failure
```

No Score, rating, proficiency level, Grade, standards alignment, source age, or
producer feedback is converted into a priority, urgency, or risk score.

## Query

`VitrineAttentionQuery` supports:

```text
workspace-wide attention
exact Portfolio-scoped attention
```

The only query field is optional `portfolio_id`.

There is no class filter in v1. Vitrine Portfolios may deliberately span Core
classes. Cross-module class filtering belongs to issue #70.

Unknown exact Portfolio IDs fail with a stable Vitrine attention query error.
They do not silently become workspace-wide queries.

## Evaluation report

`VitrineAttentionReport` contains:

```text
contract_version
evaluation
observed_state_revision
summaries
notices
```

`evaluation` is one of:

```text
evaluated
unavailable
```

A valid inspectable workspace with no current attention returns:

```text
evaluation = evaluated
summaries = empty
```

An unavailable or unsafe canonical Vitrine context returns:

```text
evaluation = unavailable
observed_state_revision = null
summaries = empty
```

These states are deliberately distinct.

The bounded report notice codes are:

```text
vitrine_attention_partial
vitrine_attention_unavailable
```

A safely isolatable source failure may preserve unrelated summaries with
`vitrine_attention_partial`. A canonical state change during evaluation fails
closed rather than mixing revisions.

## Summary shape

Each `VitrineAttentionSummary` contains only:

```text
code
label
count
count_unit
attention_class
portfolio_id
reason_codes
next_action
```

`attention_class` is one of:

```text
workflow
recovery
integrity
notice
```

These values classify the nature of the response. They do not define a priority
ordering.

Counts are per-code counts using that code's frozen `count_unit`. Counts from
different codes may overlap and must not be summed as unique students, unique
works, or unique Portfolios unless a future contract explicitly defines such an
operation.

When all facts for one summary belong to one Portfolio, that exact `portfolio_id`
may be retained. When a workspace aggregate spans multiple Portfolios, the
summary `portfolio_id` is null.

## Next-action references

`VitrineNextActionRef` is an opaque route owned by Vitrine. It contains:

```text
action_id
portfolio_id
```

The v1 action vocabulary is:

```text
open_candidate_inbox
open_candidate_review
open_working_composition
open_build_export_current_portfolio
inspect_snapshot_recovery
inspect_snapshot_custody
inspect_snapshot_edition
verify_snapshot_export
```

These identifiers satisfy Core 0.6.3 `ModuleOwnerActionRef` lexical rules so
issue #70 can adapt them without inventing a second vocabulary.

An action reference is not an executable command. It does not carry shell text,
URLs, filesystem paths, serialized callables, credentials, authorization tokens,
or arbitrary command arguments.

## Frozen attention taxonomy

| Code | Count unit | Class | Owner action | Semantic authority |
| --- | --- | --- | --- | --- |
| `vitrine_candidate_review_pending` | `candidates` | workflow | `open_candidate_inbox` | Candidate Inbox + explicit curation history |
| `vitrine_candidate_evaluation_stale` | `candidate_entries` | workflow | `open_candidate_inbox` | Candidate Inbox staleness |
| `vitrine_candidate_evaluation_unresolved` | `candidate_entries` | workflow | `open_candidate_inbox` | Candidate Inbox unresolved Evaluation state |
| `vitrine_selection_decision_pending` | `selection_proposals` | workflow | `open_candidate_review` | curation Proposal/Decision heads |
| `vitrine_selection_follow_up_required` | `selection_proposals` | workflow | `open_candidate_review` | exact current Proposal Decision |
| `vitrine_selection_condition_unresolved` | `selections` | workflow | `open_candidate_review` | active Selection condition state |
| `vitrine_selection_unplaced` | `selections` | workflow | `open_candidate_review` | active Selection/Placement state |
| `vitrine_curation_review_required` | `profile_requirements` | workflow | `open_candidate_review` | Working Composition review projection |
| `vitrine_curation_review_follow_up` | `curation_reviews` | workflow | `open_candidate_review` | exact current Review target/revision |
| `vitrine_working_composition_refresh_needed` | `portfolios` | workflow | `open_working_composition` | guided Working Composition preparation |
| `vitrine_composition_requirement_unresolved` | `profile_requirements` | workflow | `open_working_composition` | structured Requirement status |
| `vitrine_composition_requirement_human_review` | `profile_requirements` | workflow | `open_working_composition` | not-machine-evaluable Requirement status |
| `vitrine_composition_obligation_unresolved` | `obligation_codes` | workflow | `open_working_composition` | frozen unresolved obligation codes |
| `vitrine_snapshot_recovery_required` | `snapshot_builds` | recovery | `inspect_snapshot_recovery` | current exact Snapshot chain + custody |
| `vitrine_snapshot_build_failed` | `snapshot_builds` | recovery | `inspect_snapshot_recovery` | current exact Attempt Result |
| `vitrine_snapshot_durability_uncertain` | `snapshot_builds` | integrity | `inspect_snapshot_recovery` | explicit durability uncertainty |
| `vitrine_snapshot_integrity_problem` | `snapshot_findings` | integrity | `inspect_snapshot_custody` | Snapshot custody audit |
| `vitrine_omission_audience_prohibited` | `snapshot_omissions` | notice | `inspect_snapshot_edition` | exact current sealed Edition |
| `vitrine_omission_rights_review_unresolved` | `snapshot_omissions` | workflow | `open_candidate_review` | exact current sealed Edition |
| `vitrine_omission_privacy_review_unresolved` | `snapshot_omissions` | workflow | `open_candidate_review` | exact current sealed Edition |
| `vitrine_omission_source_unavailable` | `snapshot_omissions` | workflow | `open_build_export_current_portfolio` | exact current sealed Edition |
| `vitrine_omission_representation_unavailable` | `snapshot_omissions` | workflow | `open_build_export_current_portfolio` | exact current sealed Edition |
| `vitrine_omission_profile_excluded` | `snapshot_omissions` | notice | `inspect_snapshot_edition` | exact current sealed Edition |
| `vitrine_omission_explicitly_not_included` | `snapshot_omissions` | notice | `inspect_snapshot_edition` | exact current sealed Edition |
| `vitrine_export_pending_after_seal` | `snapshot_exports` | recovery | `open_build_export_current_portfolio` | current Plan/Edition/Export chain |
| `vitrine_export_verification_problem` | `snapshot_exports` | integrity | `verify_snapshot_export` | producer-independent Export verifier |

The definition order above is also the deterministic presentation order.
It is not an urgency ranking.

## Candidate semantics

### Review pending is not seen/unseen

Vitrine does not persist a `CandidateSeenRecord` or equivalent notification
acknowledgement.

`vitrine_candidate_review_pending` means a current positive Candidate/Evaluation
has no explicit curation disposition for that exact current Evaluation.

Positive outcomes are:

```text
eligible
conditionally_eligible
```

An exact Selection or decided select/decline Proposal is an explicit curation
disposition. Merely rendering Candidate Inbox is not.

A successor Evaluation may legitimately require review again.

### Staleness

Candidate staleness is delegated to Candidate Inbox. The attention projection
does not implement a second Publication-currentness algorithm.

Staleness is caused by authoritative source/Profile/current-use changes, not the
age of `evaluated_at`.

### Unresolved Evaluations

Evaluation-only unresolved entries remain visible without fabricating a
positive Candidate.

## Curation semantics

Selection Proposal heads are resolved through explicit predecessor links.
Undecided exact Proposal heads produce decision-pending attention.
`changes_requested` produces follow-up attention rather than becoming resolved.

Active Selection conditions remain explicit. Teacher acknowledgement does not
clear a condition.

An active Selection without an active Placement is reported separately. Vitrine
never invents a section.

Curation Review attention uses exact target/revision semantics. Approval of a
predecessor revision does not approve a successor revision.

## Working Composition semantics

Issue #67 guided preparation remains the semantic authority.

```text
create_initial -> refresh needed
create_successor -> refresh needed
reuse_exact_current -> no refresh-needed summary
```

Structured Requirement statuses are reused directly. In particular:

```text
unresolved_missing
conditional_unresolved
not_machine_evaluable
```

remain distinct. Optional absence is not attention.

Frozen `unresolved_obligation_codes` remain attention until the canonical state
changes. Acknowledging obligations for a Snapshot Plan does not satisfy them.

See [Guided Working Composition v1](guided-working-composition-v1.md).

## Snapshot currentness

Snapshot attention must not promote retained history into permanent attention.

For each exact Portfolio, the current chain is resolved by canonical predecessor
heads:

```text
Snapshot Series head
-> Build Request head
-> Build Plan head
-> greatest unique attempt_number within that exact Plan
-> exact Attempt Result
```

`attempt_number` is a canonical sequence field. Event timestamps, filename
order, opaque IDs, and filesystem enumeration do not determine the current
Attempt.

A failed Attempt superseded by a later sealed Attempt for the same exact Plan is
historical and does not remain `vitrine_snapshot_build_failed`.

An Attempt with no terminal Result is recovery attention. Explicit
`durability_uncertain` is both recovery and integrity attention.

Snapshot custody findings are reused from existing custody inspection. Unscoped
filesystem anomalies such as orphan staging are workspace-level only and are
not attributed to an exact Portfolio without canonical ownership.

See [Build and Export Current Portfolio v1](build-export-current-portfolio-v1.md)
and [Snapshot build workflows v1](snapshot-build-workflows-v1.md).

## Omissions

Omissions are evaluated only for the exact sealed Edition associated with the
current build-chain head. Historical Edition omissions are not accumulated
forever.

Intentional exclusions remain notices where appropriate:

```text
audience_prohibited
profile_excluded
explicitly_not_included
```

Review/source/representation omissions may require a workflow response.
A sealed Edition is never mutated to repair an omission; any remediation occurs
through later curation/build state.

## Export verification

The matching Export head is resolved using the exact sealed Edition plus the
immutable Export Plan commitments available on the persisted Export Artifact:

```text
export_format
export_contract_version
configuration_digest
```

Export predecessor links determine the exact Export head. Vitrine does not use
filesystem presence or greatest identifier as a substitute.

`verify_snapshot_export()` and custody audit are observational. A current Export
verification failure is deduplicated when both surfaces report the same exact
Artifact problem.

There is no durable `last_verified` attention record. Lack of historical
verification metadata is not itself attention.

## Determinism

For identical canonical state and query, semantic output is deterministic.

Domain/order is frozen by the taxonomy definition order. Reason codes are
bounded and sorted. Display labels, timestamps, source scores, and random IDs do
not determine attention ordering.

## Privacy

The shared low-density contract does not expose student names, student IDs,
student writing, scores, percentages, producer feedback bodies, private
rationales, Artifact bytes, source filenames, private source paths, absolute
paths, manifests, tracebacks, credentials, tokens, or recipient information.

Fixed code-owned labels and bounded reason codes are the shared surface. Opaque
Portfolio IDs may be retained for exact Vitrine-local routing.

## Read-only guarantee

Attention evaluation must not create or repair state. It must not:

- discover Candidates;
- create Candidate Evaluations or pointers;
- select, decline, place, withdraw, replace, or invalidate curation;
- create Annotations, Reflections, or Reviews;
- create/freeze Working Compositions;
- acknowledge obligations;
- create Audience Contexts or Snapshot Series;
- request, plan, start, execute, retry, recover, or seal Snapshot builds;
- acquire producer bytes;
- create or repair Exports;
- advance Current Edition pointers;
- delete staging or release locks;
- create caches or notification records.

The canonical Vitrine state revision observed before and after one successful
attention evaluation must be identical.

Snapshot/Export verification may read Vitrine-owned sealed custody but does not
consult producer packages or producer bytes.

## Teacher and CLI surfaces

The direct command is:

```text
vitrine attention list
vitrine attention list --portfolio-id PORTFOLIO_ID
```

The teacher menu exposes workspace attention as main option 6 and exact
Portfolio attention as Portfolio option 7.

These surfaces share `evaluate_vitrine_attention()` and display stable action
IDs. They do not execute those actions.

## Explicit non-goals

V1 does not implement durable notifications, seen/unseen state, automatic
workflow actions, external delivery, risk/urgency scoring, student ranking,
Grade/proficiency interpretation, cross-module aggregation, Vitrine readiness,
suite doctor/launcher integration, backup orchestration, or generic remote
action execution.

Those suite-facing concerns remain issue #70 where applicable.
