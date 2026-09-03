# Live Concord Projection and Artifact Adapter v1

- **Issue:** #61 — Implement the live Concord projection and artifact adapter
- **Milestone:** v0.3.0 — Consume released producer evidence and guide real improvement/showcase portfolios
- **Status:** Operational live integration contract
- **Adapter ID:** `vitrine_concord_live_adapter`
- **Adapter contract:** `vitrine_concord_live_adapter_v1`
- **Projection contract:** `vitrine_candidate_projection_v1`
- **Reader contract:** `vitrine_installed_producer_reader_v1`
- **Artifact provider ID:** `vitrine_concord_returned_artifact_source_provider`
- **Artifact provider version:** `vitrine_concord_returned_artifact_source_provider_v1`

## Purpose

Issue #61 implements Vitrine's live Concord Academic Result projection and the
separately authorized Concord Artifact source path used by copied-source
Snapshots.

The ownership sequence is:

```text
Core discovery
-> canonical Core Publication reload
-> exact historical Academic Work Registration
-> producer Profile compatibility
-> exact Vitrine adapter selection
-> source-read authorization
-> Core manifest containment/digest verification
-> immutable manifest bytes
-> installed Concord public reader
-> validated Concord AcademicResultManifest
-> pure Vitrine projection
-> Portfolio Subject/Profile/Candidate policy
-> explicit Selection
-> copied-source Snapshot Entry Plan
-> Snapshot build authority
-> exact Candidate/Evaluation/Selection/Core revalidation
-> Concord Artifact authorization
-> Concord public Artifact API
-> returned_artifact_pdf
-> SnapshotAuthorizedSourceBytesResult
-> Vitrine staging and digest verification
```

Concord owns Concord semantic validation, historical native Artifact resolution,
and the producer-approved returned PDF representation. Vitrine owns bounded
projection, Candidate policy, explicit curation, source-plan revalidation, and
Snapshot staging. Deployment/application policy owns the distinct Concord
Artifact authorization gate.

The adapter does not calculate Grades, proficiency, mastery, portfolio quality,
or automatic selection. It does not open Concord native storage directly.

## Qualification anchors

The implementation is qualified against:

```text
pds-core 0.6.3
pds_core-0.6.3-py3-none-any.whl
sha256:
98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5

pds-concord 0.3.0
pds_concord-0.3.0-py3-none-any.whl
sha256:
dd827f7059c91c79bd69b6190b3c673d6b3bbc02bc25fa666286bbf5883c5e12
```

Release versions and digests are reproducibility anchors only. They are not
semantic adapter-selection fields.

Vitrine adds no hard `pds-concord` runtime dependency.

## Frozen support key

The adapter reuses the one frozen Concord live support key:

```text
CONCORD_LIVE_SUPPORT_KEY
```

Its exact semantic fields are:

```text
producer_module_id              = concord
core_publication_schema_version = 1
publication_kind                = academic_result_set
manifest_contract_version       = concord_academic_result_manifest_v1
producer_contract_version       = concord_academic_work_v1
source_record_kind              = activity
source_record_contract_version  = concord_activity_v1
required_capabilities           = criterion_scores
```

`standards_ratings` and `moderated_scores` are conditional publication
capabilities. They are preserved whenever represented but are not required for
adapter selection.

The same adapter therefore accepts compatible publications containing:

```text
criterion_scores
criterion_scores + standards_ratings
criterion_scores + moderated_scores
criterion_scores + standards_ratings + moderated_scores
```

There is no wildcard, nearest-version rule, source-record substitution, package
version tie-break, or development-fixture fallback.

## Lazy installed reader

The declaration binds exactly to:

```text
public_reader_id:
vitrine_installed_concord_academic_result_reader

reader_contract_version:
vitrine_installed_producer_reader_v1

reader_package_identity:
pds-concord

integration_kind:
live
```

Construction of `vitrine.concord_adapter`, the ordinary adapter registry, CLI
adapter diagnostics, or the Concord Snapshot provider does not require Concord
to be installed. Producer import occurs only at explicit reader or Artifact API
invocation.

Missing or incompatible installed producer APIs fail through the established
privacy-safe reader/source diagnostics. They never fall back to the Concord
development fixture.

## Pure projection boundary

`vitrine/concord_adapter.py` receives an already validated public Concord model.
It does not parse Concord JSON, copy producer validators, discover producer
workspace state, or query Concord publication-management storage.

The projection preserves bounded manifest context including:

```text
record_set_id
record_set_revision
manifest_generated_at
source Activity identity
source_snapshot_revision
projection digest
projection revision reason
Activity class/title/scoring orientation
standards_profile_id
ordered focus_standard_ids
ordered criterion_set_ids
```

## Criterion Sets, Criteria, and Scales

Projected Score display metadata preserves exact represented Criterion Set and
Criterion semantics, including revision/lineage identity, local versus
standard-backed status, alignment, target kinds, and default Scale identity.

Scoring Scales preserve:

```text
scoring_scale_id
lineage_id
name
revision
scale_type
ordered levels
status
supersedes_scoring_scale_id
```

Native level values are type-sensitive:

```text
1 != 1.0 != "1" != true
```

The projection therefore carries both the scalar value and an explicit native
type tag where needed. Ordinary Python scalar equality must not collapse these
identities.

Scale values are not normalized into percentages, points, Grades, Vitrine
ratings, mastery, or proficiency.

## Score cardinality and history

The fundamental Score rule is:

```text
one represented Concord Score revision
=
one independently projected Score source
```

Current and superseded Score revisions both survive when represented.

Each Score source preserves bounded semantics equivalent to:

```text
score_record_id
activity_id
session_id
target_reference
criterion_id
score_kind
standard_id
scoring_scale_id
disposition
typed native value
basis
scorer
scored_at
moderation_complete
status_reason
supersedes_score_record_id
current_state
```

`current_state=current` is Concord history, not Vitrine selection. Vitrine does
not choose latest, highest, current, scored, individual, or standard-backed
Scores as preferred evidence.

The logical Score source is an `assessment_summary` with representation
`concord:score_summary`; it has no fabricated source locator, digest, or byte
size.

## Score targets and relationships

Exact Score target identity is preserved.

Where Vitrine already has established relationship vocabulary:

```text
core_student
-> individual_score_target

concord_group
-> group_score_target
```

the adapter uses it exactly.

A Group Score is not expanded to Group members. Artifact Author, Artifact
Subject, evidence subject context, Group membership, and Score target are never
inferred from one another.

Other Concord target kinds remain bounded producer metadata rather than causing
Vitrine to invent stronger relationships.

## Non-score semantics

Concord non-score dispositions remain distinct:

```text
insufficient_evidence
absent
excused
not_observed
not_applicable
deferred
```

For a non-scored disposition, `value=None` is meaningful evidence.

Vitrine never converts it into zero, the lowest Scale level, failure, missing
assignment, Grade exclusion, or portfolio ineligibility.

Public Status Reason metadata may be preserved. Private native Score rationale is
not projected.

## Standards relationships

Exact represented:

```text
score_record_id <-> standard_id
```

relationships survive without conversion into proficiency, mastery, best
evidence, growth, trend, or a standards Grade.

Multiple represented Scores for one standard remain multiple Scores.

## Score Evidence Links

The fundamental Evidence Link rule is:

```text
one represented Score Evidence Link
=
one independently projected evidence-link source
```

The projection preserves bounded public link semantics including:

```text
score_evidence_link_id
score_record_id
evidence_reference
evidence_locator
subject_context
relevance_description
significance
moderation_record_id
status
supersedes_score_evidence_link_id
```

Evidence subject context does not manufacture Artifact Subject, authorship,
Group membership, contribution, or Score target. For Concord-owned Artifact
links, the exact parent Score target relationship is retained so ordinary
Portfolio Subject/Profile policy can evaluate the source without inferring
Artifact ownership.

## External evidence boundary

Concord may reference ScoreForm, Quillan, or other external evidence.

Vitrine preserves the represented external reference metadata only. The Concord
adapter does not import a sibling producer, open an external publication, or
dereference external evidence.

## Moderation

Public Moderation fields remain producer evidence, including identity, target
evidence/subjects, status, permitted use, qualification, supersession, and
current state.

Private Concord Moderation rationale is not projected.

`permitted_use` is not reinterpreted as Grade eligibility, portfolio
eligibility, disclosure permission, or ownership.

## Concord-owned Artifact capability

Only represented evidence satisfying:

```text
owning_system = concord

evidence_kind =
  artifact_instance
  or artifact_page
```

becomes Concord Artifact-capable.

Teacher rationale, ScoreForm results, Quillan responses, and generic external
records do not become Concord Artifact-capable.

Artifact Evidence Links remain independent even when two links reference the
same Artifact.

## Projected Artifact reference

Before authorization, the projected Artifact reference is bounded to:

```text
artifact_id:
<exact evidence record_id>

artifact_kind:
collaborative_artifact

representation_kind:
concord:returned_artifact_pdf

media_type:
application/pdf

source_locator:
None

source_digest:
None

byte_size:
None
```

The projected Artifact `native_revision` is the exact
`manifest.projection.source_snapshot_revision`. This binds later acquisition to
the represented historical Concord snapshot.

No path, filename, Scan Reference, retained-source digest, or byte size is
fabricated.

## Privacy

Concord's public privacy classification and bounded subject/audience references
are preserved conservatively in `SourcePrivacyMetadata`.

Collaborative or multi-subject evidence remains marked for minimum-necessary
projection and multi-subject review where appropriate.

Privacy classification is not authorization:

```text
manifest source-read authorization
!= Concord Artifact authorization
!= Snapshot build authority
!= disclosure authorization
```

## Separate Concord Artifact authorization

Artifact acquisition uses only the released public API:

```python
concord.academic_result_artifacts.read_authorized_academic_result_artifact(
    workspace_root,
    manifest,
    score_evidence_link_id,
    *,
    purpose,
    authorization_gate,
)
```

The Vitrine-owned authorization request carries the exact Snapshot/Candidate
provenance needed by deployment policy. Outcomes remain:

```text
allowed
denied
unresolved
```

Only `allowed` may permit Concord native Artifact I/O.

The authorization bridge independently verifies the producer request against the
frozen Vitrine plan before forwarding it to the deployment-owned gate. A
producer/Vitrine identity mismatch fails closed without calling the deployment
gate.

Gate exceptions and invalid decisions become unresolved and do not authorize
I/O.

## Authorization-before-I/O

The provider performs only bounded Vitrine/Core/manifest consistency checks
before producer Artifact authorization. It never probes Concord native paths or
storage.

Concord 0.3.0 owns the stronger producer-native ordering:

```text
exact public Artifact request
-> authorization gate
-> exact historical native graph load
-> bounded returned Artifact rendering
```

Vitrine does not bypass or duplicate that producer boundary.

## Canonical Snapshot source revalidation

`vitrine/concord_artifact_context.py` supplies the production context resolver.

For one immutable copied-source `SnapshotEntryPlan`, it re-establishes:

```text
exact PortfolioCandidate
exact CandidateEvaluation
explicit PortfolioSelection
exact Placement when present
frozen Candidate source endpoint
canonical Core Publication
non-withdrawn publication state
exact historical Academic Work Registration
frozen Concord live support contract
separate source-read authorization
Core manifest verification
installed Concord reader
exact live Concord reprojection
frozen Candidate/source/Artifact equality
```

Only then does it return `ConcordArtifactSourceContext`.

This does not itself authorize Artifact bytes.

## Snapshot source provider

The provider identity is:

```text
provider_id:
vitrine_concord_returned_artifact_source_provider

provider_version:
vitrine_concord_returned_artifact_source_provider_v1
```

Its exact Snapshot provider support key is:

```text
producer_module_id              = concord
projection_kind                 = concord:returned_artifact_pdf
projection_contract_version     = vitrine_candidate_projection_v1
artifact_kind                   = collaborative_artifact
representation_kind             = concord:returned_artifact_pdf
```

This key follows the frozen `SnapshotEntryPlan` convention: copied-source plans
store the Artifact representation kind as `projection_kind`.

The provider is not a generic filesystem source provider.

## Returned result validation

After Concord returns an allowed result, Vitrine independently verifies:

```text
returned_artifact_pdf representation
exact work
record-set revision
source snapshot revision
exact Score
exact Score Evidence Link
exact evidence reference/owner/kind/record
Artifact Instance or exact Artifact Page identity
application/pdf
immutable bytes
PDF signature
byte_size == len(content)
sha256 == recomputed SHA-256
```

Artifact Page evidence remains page-bounded and is not silently expanded to the
whole Artifact Instance.

Producer-private paths, Scan References, and routing metadata are not accepted
as Vitrine source locators.

## Authorized-byte Snapshot path

Successful acquisition returns:

```text
SnapshotAuthorizedSourceBytesResult
acquisition_contract = authorized_source_bytes_v1
```

The shared Snapshot materializer then independently verifies producer digest and
size claims, stages bytes exclusively, rereads the staged bytes, and recomputes
the staged digest.

Authorized immutable bytes never enter the generic filesystem stability path;
their stability result is `not_applicable`.

## Candidate and curation behavior

Live Candidate acceptance proves:

- every represented Score revision remains independently evaluated;
- every represented Evidence Link remains independently evaluated;
- student-targeted Artifact evidence can become a conditional Candidate through
  normal Subject/Profile policy;
- Group-targeted Artifact evidence remains Group-targeted and is not expanded to
  an individual Portfolio Subject;
- external evidence remains metadata and is not dereferenced;
- Candidate discovery creates no automatic `PortfolioSelection`.

```text
Candidate != Selection
```

Snapshot acceptance begins only after an explicit Selection.

## Author, Subject, Group, and recorder protections

The released Concord Artifact result may expose bounded Artifact, Artifact Page,
Author, Subject, Group, Session, and privacy projections.

Vitrine preserves those released identities when validating the returned result,
but does not crawl unrelated native Group Membership or contribution records.

The following remain distinct:

```text
Artifact Author != Artifact Subject
Artifact Subject != Score target
Group membership != authorship
Group membership != individual Score
Group Score != individual Score
recorder/scorer != Artifact Author
privacy classification != disclosure authorization
```

## Registry and CLI

After issue #60, the completed ordinary live registry contains:

```text
vitrine_concord_live_adapter
vitrine_quillan_live_adapter
vitrine_scoreform_live_adapter
```

The three development fixture adapters remain isolated behind explicit fixture
opt-in.

Default workflow dependencies remain fail-closed with an empty producer Profile
registry, empty adapter registry, and unresolved authorization decisions.
Installing Concord therefore does not automatically enable workspace reads.

`vitrine adapters list` and `vitrine adapters show
vitrine_concord_live_adapter` work without Concord installed.

## Packaging and exact-wheel qualification

The runtime wheel includes:

```text
vitrine/concord_adapter.py
vitrine/concord_artifact_context.py
vitrine/concord_artifact_source.py
```

Normal Vitrine runtime requirements remain Core-only.

The source distribution includes this contract, the dedicated validator, and
the exact-wheel Concord Artifact qualification harness:

```text
scripts/qualify_concord_artifact_source.py
```

Run:

```powershell
python scripts/qualify_installed_producer_readers.py `
  --wheel-dir "$HOME\Downloads"
```

The exact-wheel gate authenticates the audited Core/producer wheels, invokes the
released Concord public reader, qualifies the live Score projection, creates
real synthetic producer-native Artifact state through Concord production APIs,
and proves:

```text
released Concord Artifact API
-> returned_artifact_pdf
-> Vitrine authorization bridge
-> authorized_source_bytes_v1
```

The denied authorization case is also required to fail closed.

## Validation

Focused validation includes:

```powershell
python scripts/validate_concord_adapter.py
python scripts/validate_producer_reader_services.py
python scripts/validate_producer_adapters.py
python scripts/validate_released_producer_contracts.py
python -m pytest tests/test_concord_adapter.py
python -m pytest tests/test_concord_artifact_source.py
python -m pytest tests/test_concord_artifact_context.py
python -m ruff check .
python -m mypy
python scripts/check_documentation.py
```

The complete repository validator additionally builds and checks the wheel and
sdist, runs isolated installed-wheel smokes, and executes the exact release
qualification surface.

## Downstream handoff

Issue #62 may expose compatibility and unsupported-contract diagnostics over the
stable exact-match, authorization, reader, projection, and Artifact-source
failure boundaries.

No downstream integration may:

- turn conditional Concord capabilities into required support-key fields;
- treat producer package version as semantic adapter identity;
- collapse Score or Evidence Link history;
- normalize native Scale values;
- infer Group membership, authorship, Subject, Score target, or disclosure
  authority from one another;
- use a development fixture as a live fallback;
- bypass Concord Artifact authorization by opening producer-native storage.
