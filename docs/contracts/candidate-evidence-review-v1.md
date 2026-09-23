# Candidate Evidence Review v1

- **Issue:** #96
- **Branch:** `96-candidate-discovery-evidence-review`
- **Presentation contract:** `vitrine_candidate_evidence_presentation_v1`
- **Discovery presentation:** `vitrine_candidate_discovery_presentation_v1`
- **Preview contract:** `vitrine_candidate_evidence_preview_v1`
- **Artifact preview contract:** `vitrine_candidate_evidence_artifact_preview_v1`
- **Status:** Slice 12 — installed acceptance closure

## Purpose

Issue #96 turns Candidate discovery and review into an instructional evidence
workflow without weakening canonical provenance.

The governing distinctions are:

```text
Candidate identity != Candidate display label
evidence title != source authority
representation grouping != Candidate merging
preview != Selection
preview != Placement
preview != disclosure authorization
current producer state != exact persisted Candidate provenance
Profile fit != currently actionable Placement target
```

Teacher-facing names are transient projections over exact Candidate/Evaluation
source state. They never become lookup, authorization, Selection, Placement, or
producer-file authority.

## Instructional evidence presentation

Candidate presentation derives recognizable evidence names from exact preserved
metadata, especially the Core Academic Work Registration title snapshot.

Representative vocabulary is:

```text
Assessment Attempt
Student Work
Review
Feedback
Assessment Evidence
Collaborative Work
```

ScoreForm attempt numbers are chronology labels only. Quillan PDF and Markdown
feedback remain distinct exact Candidate/source representations even when they
share a transient representation-family key. Concord presentation never infers
individual authorship from group membership, represented group, Artifact Subject,
or group Score target.

`PortfolioCandidate.display_snapshot` remains historical presentation state and
does not participate in rediscovery identity.

## Discovery workflow

The guided discovery preflight explains in ordinary language that Vitrine will
search current published evidence and evaluate it against the exact bound Profile.

Discovery may create or update Candidate/Evaluation state. It does not select,
place, approve, or build Portfolio evidence.

Completion is a transient summary of the exact discovery result:

```text
publications considered
evidence evaluated
new Candidates
already known
ineligible evidence
unresolved evidence
source/discovery problems
```

Finding codes, stages, Publication IDs, diagnostics, and committed state revision
remain Technical Details / Provenance.

## Candidate queues and Profile fit

`Ready to consider` requires `selected_state="unselected"`. Active Selections and
historical Selection state remain separate review categories.

Profile fit maps exact eligible section IDs through the exact bound Profile
revision to teacher-readable section labels. It means the current Candidate
Evaluation matched those Profile sections. It does not promise that every role is
currently a valid Placement target; issue #97 owns that domain-validity layer.

## Evidence preview

Preview is explicit through `V. View evidence`. Opening Candidate Inbox detail,
Candidate Review detail, or Technical Details / Provenance does not automatically
read producer manifests or acquire Artifact bytes.

The service resolves one exact persisted entry, revalidates its exact Core
Publication and registration, uses the audited public producer reader, reprojects
the exact source, and fails closed on mismatch, drift, ambiguity, or missing
authority.

Preview requests contain exact canonical references and never accept a display
title as authority.

Artifact-byte authorization is a distinct Vitrine operation:

```text
candidate_evidence_preview
```

Allowed, denied, and unresolved are explicit outcomes. Unconfigured authorization
fails closed.

## Producer boundaries

### ScoreForm

The audited ScoreForm release is metadata/reference-only for Candidate preview.
Vitrine renders a bounded structured summary from the validated public model and
does not fabricate an answer-sheet Artifact or open native files.

### Quillan

Byte-bearing preview uses only the released
`quillan.academic_result_artifacts` API for student work, feedback PDF, and
feedback Markdown. Returned student/work/revision/evidence/media/digest/size
facts must match exact Candidate provenance.

### Concord

Returned Artifact preview uses only the released
`concord.academic_result_artifacts` API. Existing author/subject/group/score and
collaborative privacy distinctions remain authoritative.

No Candidate preview fabricates Snapshot Build Plan or Attempt state.

## Structured-content policy

Structured preview is allowlisted. Ordinary preview does not dump:

```text
raw producer manifests
answer keys
private teacher notes
native absolute paths
unrelated student data
hidden collaborator information
hashes/contracts
raw base64
authorization-provider prose
```

## Transient bytes

Authorized Artifact bytes are materialized only in a temporary directory outside
canonical Vitrine state. Filename suffix comes from the verified media type.
The launcher is injectable so tests never need to open a desktop application.
The temporary file is removed when the teacher returns.

Preview creates no durable preview record, cache, path, last-viewed marker, or
Selection/Placement state.

## Privacy and provenance

Suppressed Evaluations are absent from the ordinary Inbox and cannot be resolved
through the preview authority service. Denied/unresolved preview fails closed.
Human-readable names never establish student identity or authorization.

The #95 Technical Details / Provenance layer remains available for the bounded
exact Candidate/Evaluation/Publication/producer/Artifact state.

## Sibling boundaries

Issue #97 owns Selection/Placement domain validity. Issue #98 owns the systematic
menu transition/confirmation audit. Issues #99-#103 retain their documented
Reflection, Composition, student-output, Edition, and Attention scopes. Issue
#104 remains the final umbrella synthetic acceptance.

## Installed acceptance endpoint note

Issue #96 began against the then-audited Quillan 0.10.0 contract. Quillan v0.10.1 was subsequently released as a compatible patch release and remains qualified with Core 0.6.3. Slice 12 therefore advances only the #96 installed qualification endpoint to the exact v0.10.1 wheel; issue #71's historical frozen 0.10.0 acceptance composition is not rewritten.

## Installed acceptance closure

Slice 12 extends the existing authenticated issue #71 wheel harness with:

```text
--candidate-evidence-review-only
```

The mode authenticates the exact Core 0.6.3, ScoreForm 0.11.0, Quillan
0.10.1, and Concord 0.3.0 wheels for Issue #96, installs the candidate Vitrine wheel
noneditably outside the repository, creates real producer-native synthetic
Publications, performs live Candidate discovery, then proves:

- ScoreForm presentation uses `Synthetic Baseline Assessment` and preserves
  attempts 1 and 2;
- Quillan presentation exposes Review, Student Work, Feedback PDF, and Feedback
  Markdown for `Synthetic Later Writing Evidence`;
- Concord exposes recognizable collaborative evidence for
  `Synthetic Collaborative Later Evidence`;
- ScoreForm preview remains a structured summary and cannot fabricate Artifact
  bytes;
- an authorized Quillan PDF preview returns verified producer bytes;
- an authorized Concord returned-Artifact preview returns verified PDF bytes;
- manifest and Artifact preview authorization use the #96 operation scopes;
- preview leaves Vitrine state revision unchanged.

The installed Core+Vitrine-only wheel smoke imports every #96 runtime contract
with ScoreForm, Quillan, and Concord absent, proving producer packages remain
optional/lazy rather than unconditional Vitrine dependencies.
