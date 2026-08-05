# Producer Artifact Exposure Boundaries

## Status and purpose

This document defines the conceptual boundary between producer-owned source data and the exact producer-approved representations that Vitrine may evaluate as Portfolio Candidates.

It applies to the Vitrine v0.1.0 foundation and to the current Paper Data Suite producers reviewed for issue #7:

- ScoreForm;
- Quillan;
- Concord;
- and Portia.

It extends the [Candidate and source-reference contract](candidate-source-reference-contract.md). It does not define final JSON Schema, runtime adapters, public readers, persistence, source copying, Selection records, snapshot issuance, or recipient authorization.

The governing distinction is:

```text
producer manifest
  != producer-native record
  != producer-approved projection
  != Portfolio Candidate
  != Selection
  != copied Portfolio representation
  != audience-authorized disclosure
```

The required direction is:

```text
verified Core Publication
  -> verified producer manifest
  -> producer public reader
  -> exact producer-approved projection
  -> Vitrine Candidate Evaluation
  -> optional positive Portfolio Candidate
```

A producer source may be valid, current, and educationally meaningful while having no portfolio-safe projection.

## Governing authority

### Core authority

Core owns:

- Academic Work Registration;
- Publication Records and Withdrawals;
- publication-series identity;
- manifest-path containment;
- manifest digest binding;
- publication capabilities;
- compatibility Profiles;
- and the derived publication catalog.

Core does not decide whether a producer field, record, file, or rendering is suitable for a portfolio.

### Producer authority

Each producer owns:

- native record identity;
- native educational meaning;
- public manifest contracts;
- public reader behavior;
- source artifact and representation identity;
- source revision and correction;
- producer privacy classifications;
- projection kinds;
- projection field allowlists;
- and fields explicitly omitted from projections.

A Vitrine adapter may translate an approved producer projection into Vitrine references. It may not broaden the projection.

### Vitrine authority

Vitrine owns:

- exposure-policy interpretation under this design;
- exact Portfolio Profile eligibility;
- Candidate Evaluation;
- positive Portfolio Candidate creation;
- later Selection and curation;
- Portfolio-specific annotation and reflection;
- snapshot construction;
- and issued Portfolio provenance.

Vitrine does not acquire source ownership, producer mutation authority, or broader disclosure authority.

### Institutional and audience authority

Institutions and authorized actors remain authoritative for:

- source-access authorization;
- recipient identity;
- audience permission;
- consent;
- rights review;
- redaction;
- collaborator treatment;
- disclosure logging;
- and retention or disposition.

A producer-approved projection does not establish those decisions.

## Cross-repository review baseline

The following immutable anchors were reviewed for this design.

| Repository | Reviewed anchor | Authoritative areas reviewed | Current implementation status | Reusable pattern | Constraint for Vitrine |
| --- | --- | --- | --- | --- | --- |
| `pds-vitrine` | `84f1dcc76c8e5f0319c8485e62bd2d5c89fe80a4` | module boundaries, Portfolio Subject identity, Profiles, Candidate/source references | documentation-only foundation | staged verification and exact source references | this issue defines projection eligibility, not runtime exposure |
| `pds-core` | `6c507213618b68a6dd3ea096e1a898201ff029e6` | registrations, publications, withdrawals, compatibility, catalog, digest verification | Core v0.6 implemented | canonical reload and exact manifest binding | capabilities and Profiles do not define portfolio-safe projections |
| `pds-scoreform` | `f8fa1d705ce76b0bc0ade5b285807ef28750134e` | Academic Result Manifest v1, attempts, responses, provenance, privacy exclusions | pure manifest contract implemented; workspace publication incomplete | exact all-attempt manifest with explicit exclusions | manifest is source-only; attempt and question summaries require separate projections |
| `pds-quillan` | `05fecf23d29e56b45cba58ed97906f5353290033` | assignments, submissions, evidence states, reviews, private notes, feedback exports | executable producer and feedback exports; no accepted Core 0.6 public publication reader | selected-evidence and student-facing export boundaries | no native-file fallback; public portfolio projection remains unavailable |
| `pds-concord` | `87a8165845bc61ad188e78817ccb2415af3701e1` | Artifact, Page, Author, Subject, Group, Score, moderation, privacy, correction | immutable native models and validation implemented; no public projection | explicit relationships and privacy per artifact | Group Membership, authorship, subject, contribution, and Score target remain distinct |
| `pds-portia` | `8cd4b1f2ca80cc240693184c87e5df463ba375cf` | suite role, privacy, Events, participants, relationships, portfolio-safe projection direction | architecture and schemas; no executable publication or safe projection | deny-by-default sensitive-source boundary | ordinary records are suppressed without existence leakage |
| `pds-meridian` | `c7e9129f6547bca9953f8ae5c8718ce358341172` | consumer adapter architecture, producer readiness, native-semantics preservation | architecture; no production ingestion | producer-reader projection before consumer policy | grading evidence inventory is not a Portfolio projection catalog |

The review records current reality rather than planned capability as implemented behavior.

## Terminology

### Producer manifest

An immutable machine-readable producer projection bound to a Core Publication Record.

A manifest supports verified interpretation. It is not automatically:

- a visual artifact;
- student-facing;
- a Candidate representation;
- a Selection;
- or a snapshot file.

### Producer-native record

A canonical record owned by a producer, such as:

- a ScoreForm result-history row;
- a Quillan submission or review;
- a Concord Artifact Author or Score;
- or a Portia Event or intervention record.

Native-record existence does not imply direct exposure.

### Producer-approved projection

A contract-versioned representation of selected producer-native meaning.

A projection may be:

- structured data;
- producer-rendered bytes;
- a producer-authorized source file;
- or a minimum-necessary summary.

The producer defines the projection contract, field allowlist, relationship requirements, and exclusions.

### Original-work representation

A producer-approved representation of learner-created work.

It may be assembled from selected producer evidence. It is not synonymous with a raw retained scan.

### Rendered-feedback representation

A producer-generated student-facing presentation of teacher review or feedback.

It remains derived from, and distinct from, the canonical review record.

### Result-summary representation

A bounded presentation of producer-native result information.

It must not invent:

- Grade;
- proficiency;
- mastery;
- official-attempt status;
- or selection for formal reporting.

### Retained source scan

Source evidence preserved by Core’s scan-provenance workflow.

A retained scan may contain:

- several pages;
- several students;
- route or QR data;
- unrelated material;
- source filenames;
- or intake provenance.

It is not an ordinary Portfolio Candidate representation.

### Portfolio-safe projection

A purpose-limited producer projection explicitly designed for possible portfolio use.

Vitrine cannot designate arbitrary producer data as portfolio-safe.

### Exposure decision

A Vitrine interpretation of whether one exact projection kind may enter the Candidate pipeline under this architecture.

Exposure decision is not source authorization, Profile eligibility, Selection, or disclosure permission.

### Readiness observation

A statement about whether an exposure contract and reader are currently implemented and available.

Readiness does not determine policy eligibility.

## Governing principles

1. Producers control projection contracts.
2. Manifests are normally source-only.
3. Native records are not directly exposed.
4. A public reader is necessary but does not make every returned field exposable.
5. Every projection uses an explicit allowlist.
6. A missing projection never triggers native-file fallback.
7. Original source, projection, Candidate, and copied representation remain distinct.
8. Exposure does not authorize source access.
9. Exposure does not authorize recipient disclosure.
10. Exposure does not create a Selection.
11. Exposure does not claim that Vitrine copied bytes.
12. Multi-subject records require subject-specific or minimum-necessary projection.
13. A valid source may have no approved portfolio projection.
14. Unsupported or unavailable projections are reported honestly.
15. Producer-native educational meaning is preserved without universal normalization.
16. Sensitive-source suppression includes metadata and existence leakage.

## Conceptual model

```text
Producer Projection Descriptor
  identifies
    exact producer-owned projection kind
    exact contract version
    source manifest and source kinds
    semantic artifact family
    media and acquisition modes
    exposure disposition
    implementation readiness
    allowlisted and prohibited fields
    relationship requirements
    privacy and review requirements
    revision and availability behavior

Exposure Decision
  applies descriptor under
    Portfolio
    Portfolio Subject
    exact Profile revision
    requested purpose

Readiness Observation
  records
    contract and reader availability
    deployed support
    known limitations

Candidate Evaluation
  references
    exact descriptor
    exact source representation
    exposure and readiness observations
```

## Exposure-disposition vocabulary

### `candidate_eligible`

The projection may enter the ordinary Candidate pipeline when all other Candidate prerequisites are satisfied.

### `conditional_candidate`

The projection may become a Candidate only after one or more declared conditions are satisfied.

Common conditions include:

- collaborator review;
- multi-subject review;
- rights review;
- student confirmation;
- sanitization;
- accessible alternate generation;
- or sensitive-source approval.

### `supporting_metadata_only`

The projection may accompany another Candidate but may not become a standalone Candidate.

Examples include:

- assignment title;
- Activity label;
- Criterion text;
- Scoring Scale definition;
- or source relationship labels.

### `source_only`

The projection supports interpretation or provenance but cannot become a portfolio artifact representation.

Examples include:

- producer manifests;
- canonical review records;
- raw relationship graphs;
- or moderation records.

### `prohibited`

The source, field, or representation must not be exposed through Vitrine.

Examples include:

- answer keys;
- detector internals;
- private notes;
- unrestricted raw retained scans;
- and complete sensitive intervention records.

### `suppressed`

The source must not be revealed through ordinary discovery, counts, filters, previews, titles, diagnostics, or hidden-result placeholders.

Suppression is stronger than ordinary ineligibility.

### `unsupported`

The concept may be architecturally permitted, but no accepted producer projection contract exists.

Unsupported never authorizes private-file fallback.

## Implementation-readiness vocabulary

### `implemented`

The exact producer projection contract and public reader exist and are supported by the reviewed integration surface.

### `contract_defined`

The exact projection contract is documented, but end-to-end reader or publication support is incomplete.

### `planned`

The projection is an approved architectural direction but has no final contract.

### `unavailable`

The projection may be defined or implemented elsewhere, but the required reader, publication, package, or deployment support is unavailable to Vitrine.

### `retired`

The projection must not be used for new Candidates but remains historically resolvable where required.

Exposure and readiness combine independently:

```text
candidate_eligible + unavailable
conditional_candidate + planned
source_only + implemented
prohibited + implemented
```

## Producer Projection Descriptor

A Producer Projection Descriptor is a producer-owned contract declaration consumed by Vitrine.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `producer_module_id` | required | exact producer module |
| `projection_kind` | required | producer-owned namespaced projection identity |
| `projection_contract_version` | required | exact projection contract |
| `source_manifest_contracts` | required | exact compatible producer manifest contracts |
| `source_record_kinds` | conditional | exact native/public source kinds |
| `semantic_artifact_family` | required | broad Profile-matching family |
| `representation_kind` | required | exact structured, rendered, or authorized-source representation |
| `media_types` | required | exact supported media types, possibly empty for structured projections |
| `acquisition_mode` | required | how the projection is acquired |
| `standalone_candidate` | required | whether it may stand alone |
| `default_exposure_disposition` | required | architectural exposure rule |
| `allowed_fields` | required | closed allowlist for structured projections |
| `prohibited_fields` | required | explicit critical exclusions; not a substitute for allowlisting |
| `required_source_relationships` | required | producer relationships needed to resolve the projection |
| `required_subject_relationships` | required | relationship to the Portfolio Subject |
| `multi_subject_behavior` | required | single-subject, isolated, collaborative, or suppressed behavior |
| `privacy_classification` | required | producer-owned sensitivity classification or reference |
| `required_reviews` | required | additional reviews before candidacy or disclosure |
| `source_revision_behavior` | required | exact source revision and succession rules |
| `projection_revision_behavior` | required | exact projection revision and succession rules |
| `availability_semantics` | required | what availability means and how staleness is represented |
| `known_limitations` | optional | bounded implementation or semantic limitations |

### Identity

A descriptor’s durable identity is:

```text
producer_module_id
+ projection_kind
+ projection_contract_version
```

The same broad semantic family may contain several projection kinds.

### Concept ownership and lifecycle summary

| Concept | Owner and authority | Durable identity | Cardinality | Forbidden content | Lifecycle and correction | Canonical status |
| --- | --- | --- | --- | --- | --- | --- |
| Producer Projection Descriptor | producer | exact producer, projection kind, and contract version | one descriptor per exact contract identity | Vitrine policy decisions, recipient authorization, copied bytes | immutable after publication; material change creates a new contract version | producer-canonical |
| Projection identity | producer | descriptor identity plus exact projection revision or immutable source state | one exact identity per representation | title-only, filename-only, timestamp-only, or array-position identity | explicit succession; never timestamp-inferred | producer-canonical |
| Projection field allowlist | producer | part of exact descriptor contract | one closed allowlist per descriptor | wildcard “all fields,” private native structures, undeclared extensions | material change creates a new descriptor contract | producer-canonical |
| Projection relationship requirements | producer, interpreted by Vitrine | part of exact descriptor contract | zero or more typed requirements | untyped `student_related`, inferred authorship, inferred individual Score target | material change creates a new descriptor contract | producer-canonical requirement; evaluation result is Vitrine-canonical |
| Projection review requirements | producer or controlling Profile | exact requirement IDs within descriptor/Profile context | zero or more explicit reviews | fabricated approval, consent, recipient identity, or completed review | requirement changes are versioned; review results remain separate | canonical policy requirement, not completed workflow state |
| Exposure Decision | Vitrine | opaque decision ID plus exact context | many decisions may evaluate one descriptor | producer-native mutation or broadened field access | immutable evaluation; correction or refresh creates a successor | Vitrine-canonical when relied upon |
| Readiness Observation | Vitrine deployment/integration observation | opaque observation ID | many historical observations per descriptor | policy eligibility or source-validity conclusions | refreshed append-preservingly; prior Candidate retains prior observation | Vitrine-canonical observation when relied upon; dashboards are derived |

Display snapshots and broad semantic families do not participate in descriptor identity.

### Namespaced projection kinds

Conceptual examples include:

```text
scoreform:attempt_summary
scoreform:question_evidence_summary
scoreform:sanitized_answer_sheet
quillan:student_work
quillan:student_feedback_pdf
quillan:student_feedback_markdown
quillan:student_feedback_summary
concord:artifact
concord:score_summary
portia:portfolio_safe_projection
```

These names are architectural examples, not implemented contract identifiers.

### Semantic artifact families

Initial broad families should be able to represent:

```text
original_work
feedback
result_summary
collaborative_work
reflection
growth_summary
context_summary
```

A semantic family supports Profile matching. It does not replace exact producer projection identity.

### Acquisition modes

```text
structured_projection
producer_rendered_file
producer_authorized_source_file
```

A private native path is never converted into `producer_authorized_source_file` by Vitrine.

### Standalone versus supporting

A projection marked `standalone_candidate = false` may accompany another Candidate but cannot create one alone.

Examples include:

- an assignment-title snapshot;
- a Criterion definition;
- a rating-scale legend;
- an Activity label;
- or a Group relationship summary.

## Exposure Decision

An Exposure Decision applies one descriptor to one exact evaluation context.

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `exposure_decision_id` | required | opaque Vitrine identity |
| `descriptor_reference` | required | exact producer projection contract |
| `portfolio_id` | required | exact Portfolio |
| `portfolio_subject_id` | required | exact subject |
| `profile_binding_id` | required | exact Profile binding |
| `requested_purpose` | required | candidate-consideration purpose |
| `disposition` | required | resulting exposure disposition |
| `condition_results` | required | explicit condition outcomes |
| `relationship_results` | required | required subject/authorship/contribution outcomes |
| `review_requirements` | required | remaining review obligations |
| `reason_codes` | required | privacy-safe explanation |
| `evaluated_at` | required | evaluation time |
| `evaluator_contract_version` | required | exact evaluator semantics |

An Exposure Decision is Vitrine-owned and derived from producer authority plus Portfolio context. It does not change the producer descriptor.

## Readiness Observation

### Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `readiness_observation_id` | required | opaque observation identity |
| `descriptor_reference` | required | exact projection contract or planned projection identity |
| `readiness` | required | implemented, contract-defined, planned, unavailable, or retired |
| `producer_reader_reference` | conditional | exact public reader when available |
| `vitrine_adapter_reference` | conditional | exact adapter support when available |
| `publication_support` | required | publication availability |
| `observed_at` | required | observation time |
| `limitations` | optional | bounded non-sensitive explanation |

Readiness observations are refreshable observations. Historical Candidate Evaluations preserve the observation used at evaluation time.

## Projection field allowlists

Structured projections must declare a closed allowlist.

The governing rule is:

```text
expose only declared fields
```

The rejected rule is:

```text
expose everything except known secrets
```

### Field classes

#### Identity fields

Exact source and representation identity required for provenance.

#### Display fields

Bounded title, label, and context snapshots.

Display fields are not identity.

#### Relationship fields

Typed subject, authorship, contribution, Group, or Score-target relationships.

#### Educational-meaning fields

Producer-native attempts, ratings, criteria, dispositions, or feedback.

They retain native meaning and are not normalized into universal proficiency or Grade.

#### Provenance fields

Exact publication, manifest, source, and revision references.

They may be preserved internally while omitted from audience rendering.

#### Operational fields

Routes, private paths, detector output, lock state, intake diagnostics, and review failures.

Operational fields are normally prohibited from Candidate representations.

#### Sensitive fields

Private notes, allegations, disability information, intervention details, family information, and third-party data.

Sensitive fields require suppression or a producer-approved minimum-necessary projection.

## Representation and digest layers

The design distinguishes:

```text
Core Publication manifest digest
producer source-artifact digest
producer rendered-projection digest
future Vitrine copied-representation digest
```

These digests bind different bytes and must not be reused as substitutes for one another.

A manifest digest does not prove the bytes of:

- original student work;
- a feedback PDF;
- a sanitized answer sheet;
- or a copied snapshot file.

Copied-byte contracts remain assigned to issue #9.

## Revision and correction

A producer projection must identify one exact immutable projection revision or one exact immutable source state.

A material change to projection meaning requires one of:

- a new projection contract version;
- a new producer projection revision;
- a new source revision;
- or an explicit successor representation.

Vitrine must not silently refresh a Candidate to newer producer bytes.

A changed projection creates:

- a new Candidate Evaluation;
- and a new Candidate when the exact representation changes.

Earlier Selections and snapshots retain the exact historical projection reference.

## ScoreForm exposure boundary

### Reviewed source contract

ScoreForm Academic Result Manifest v1 exposes exact producer-native academic results for one managed assignment and one immutable record-set revision.

It preserves:

- assignment identity and title;
- question count;
- Standards Profile and question alignments;
- represented students;
- every represented attempt;
- attempt origin and recorded time;
- points earned and possible;
- response state, selected answer, and correctness;
- and origin-specific provenance.

It does not establish:

- official attempt;
- best attempt;
- Grade-bearing attempt;
- proficiency;
- mastery;
- Grade;
- or portfolio eligibility.

It deliberately excludes answer keys, detector internals, image coordinates, review notes, and private or absolute paths.

### ScoreForm projection matrix

| Native/public source | Projection concept | Family | Disposition | Readiness | Required relationship/review | Prohibited content |
| --- | --- | --- | --- | --- | --- | --- |
| Academic Result Manifest v1 | manifest itself | source interpretation | `source_only` | `implemented` as pure contract | authorized exact student/attempt parsing | direct artifact display |
| one exact attempt | `scoreform:attempt_summary` | `result_summary` | `conditional_candidate` | `planned` | exact attempt subject; Profile permission | answer key, detector internals, scan-review notes, private paths |
| one exact question response | `scoreform:question_evidence_summary` | `result_summary` | `conditional_candidate` | `planned` | exact attempt subject; usually restricted Profile | answer key; detector details; default selected-answer exposure |
| selected attempt pages | `scoreform:sanitized_answer_sheet` | `original_work` | `conditional_candidate` | `planned` | exact issuance/attempt; sanitization and privacy review | raw QR/route data, unrelated pages, detector overlays |
| `assignment.json` metadata | assignment context | `context_summary` | `supporting_metadata_only` | `implemented` natively | exact assignment | answer key |
| `results.csv` | direct native file | none | `prohibited` | `implemented` natively | none | entire direct file |
| Core retained scan | raw source scan | none | `prohibited` | `implemented` in Core custody | none | all direct scan bytes |
| scan-review failure/resolution | operational record | none | `prohibited` | `implemented` | none | all operational details |

### Academic Result Manifest

The manifest is `source_only`.

It may supply exact information used to create another projection. It must not ordinarily become:

- a displayed artifact;
- a downloadable portfolio item;
- a public file;
- or a complete snapshot member.

### Attempt summary

A future attempt-summary projection may include:

- exact assignment identity;
- assignment-title snapshot;
- exact student and attempt context;
- attempt number;
- attempt origin;
- recorded time;
- points earned and possible;
- counts of selected, blank, and ambiguous responses;
- question-standard alignment summary;
- exact publication and manifest provenance;
- and a statement that the result is producer-native rather than a Grade.

It must not include by default:

- answer keys;
- detector information;
- raw QR content;
- image coordinates;
- scan-review notes;
- private paths;
- selected-answer details;
- or inferred proficiency.

Every attempt remains separate.

Vitrine must not choose:

- highest;
- latest;
- earliest;
- official;
- preferred;
- replacement;
- summative;
- or Grade-bearing

unless a separate authoritative decision supplies that status.

### Question-evidence summary

A restricted question-evidence projection may include:

- exact attempt reference;
- question number;
- response state;
- correctness;
- question standard IDs;
- and exact provenance.

Selected-answer values require a narrower explicit contract and are omitted by default.

This projection is likely appropriate only for:

- teacher-internal review;
- a regulated Profile;
- or another Profile requiring item-level evidence.

Question alignment remains alignment, not proficiency.

### Sanitized answer sheet

Raw retained scan exposure is prohibited.

A future sanitized producer rendering would require ScoreForm to:

- isolate the exact student and attempt pages;
- preserve page order;
- remove or mask route and QR data where required;
- exclude unrelated source content;
- exclude detector overlays and review diagnostics;
- bind exact source and rendered bytes;
- and expose the result through a public projection contract.

Vitrine must never open `retained_source_path` directly to manufacture this representation.

### ScoreForm invariants

- Blank and ambiguous responses remain distinct.
- An absent student does not create a zero or missing-work Candidate.
- Points are not relabeled as Grade or proficiency.
- Answer keys remain prohibited.
- Detector and scan-review internals remain prohibited.
- Manifest source snapshots remain provenance, not artifact representations.

## Quillan exposure boundary

### Reviewed source contracts

Quillan currently distinguishes:

- assignment records;
- submission manifests;
- candidate, selected, replacement, and excluded evidence;
- duplicate and rescan states;
- retained-source provenance;
- review state;
- teacher observations and ratings;
- student-facing feedback;
- private notes;
- PDF and Markdown feedback exports;
- and assignment-level reports.

Quillan does not yet publish an accepted Core 0.6 consumer-neutral portfolio contract.

### Quillan projection matrix

| Native/public source | Projection concept | Family | Disposition | Readiness | Required relationship/review | Prohibited content |
| --- | --- | --- | --- | --- | --- | --- |
| producer-selected evidence | `quillan:student_work` | `original_work` | `candidate_eligible` | `planned` | exact submission subject and selected evidence | candidate, duplicate, excluded, and unrelated replacement evidence |
| feedback PDF | `quillan:student_feedback_pdf` | `feedback` | `candidate_eligible` | `unavailable` to Vitrine | exact submission subject; approved student-facing export | private notes, source paths, internal IDs |
| feedback Markdown | `quillan:student_feedback_markdown` | `feedback` | `candidate_eligible` | `unavailable` to Vitrine | same as PDF | same exclusions |
| approved feedback fields | `quillan:student_feedback_summary` | `feedback` | `conditional_candidate` | `planned` | same student-facing inclusion decisions | complete `review.json`, private notes, unselected fields |
| exact rating/standard context | rating summary | `context_summary` | `supporting_metadata_only` | `implemented` natively | exact assignment-local scale | universal proficiency interpretation |
| `submission.json` | canonical submission | source interpretation | `source_only` | `implemented` | authorized producer reader only | direct exposure |
| `review.json` | canonical review | source interpretation | `source_only` | `implemented` | authorized producer reader only | direct exposure |
| `review.json.private_notes` | private teacher notes | none | `prohibited` | `implemented` | none | existence and content |
| class/standards reports | class aggregate | none | `prohibited` for individual Candidate use | `implemented` | none | other students and aggregate context |
| Core retained scan | raw source scan | none | `prohibited` | `implemented` in Core custody | none | all direct scan bytes |

### Original student work

A Quillan original-work projection must derive only from producer-confirmed selected evidence.

It must preserve:

- exact assignment and student context;
- selected page or evidence order;
- exact source-evidence identity;
- source revision;
- and representation identity.

It must exclude:

- candidate evidence;
- duplicate evidence;
- excluded evidence;
- unrelated replacement history;
- retained-source paths;
- route IDs;
- scan-intake records;
- source filenames unless expressly safe;
- and internal evidence-management fields.

The raw retained scan remains prohibited.

### Rendered feedback

Quillan’s PDF and Markdown feedback are appropriate conceptual Candidate representations because Quillan already applies a student-facing field boundary.

They remain unavailable to Vitrine until Quillan provides:

- an accepted Core publication contract;
- an exact public reader;
- exact projection identity;
- and source-to-export provenance.

A feedback projection may include teacher-approved student-facing:

- assignment context;
- Focus Standards;
- selected ratings and labels;
- selected rationales and observations;
- selected feedback comments;
- minimum-requirement notice;
- and recorded next steps.

It must exclude:

- private notes;
- unselected observations or comments;
- internal IDs;
- duplicate or candidate evidence;
- retained-source paths;
- routing metadata;
- and source-file paths.

### Structured feedback summary

A structured summary must use the same student-facing inclusion rules as the rendered exports.

It must not expose complete `review.json` or broaden selected fields.

### Rating and Standards metadata

A bare rating or standards summary is supporting metadata only.

It must preserve:

- the exact assignment-local scale;
- exact standard ID;
- teacher-selected inclusion status;
- and native meaning.

It must not become standalone universal proficiency.

### Quillan invariants

- Submission state, review state, original work, and feedback remain distinct.
- Private notes are prohibited without revealing their existence.
- Class reports are not individual student artifacts.
- Selected evidence is the only permitted basis for original-work projection.
- No native-file fallback is allowed while public publication support is absent.

## Concord exposure boundary

### Reviewed native model

Concord currently distinguishes:

- Artifact Instance;
- Artifact Page;
- Artifact Author;
- Artifact Subject;
- Activity;
- Session;
- Group;
- Group Membership;
- Role and Responsibility Assignment;
- Artifact Review;
- Moderation;
- Criterion;
- Scoring Scale;
- Score;
- Score target;
- Score Evidence Link;
- Correction Record;
- and Privacy Policy.

Concord has no accepted public artifact projection contract yet.

### Concord projection matrix

| Native/public source | Projection concept | Family | Disposition | Readiness | Required relationship/review | Prohibited content |
| --- | --- | --- | --- | --- | --- | --- |
| Artifact Instance and approved pages | `concord:artifact` | `original_work` or `collaborative_work` | `conditional_candidate` | `planned` | confirmed authorship/subject/contribution as required; privacy review | arbitrary surrounding record graph |
| rubric page or producer feedback rendering | Concord feedback projection | `feedback` | `conditional_candidate` | `planned` | exact Artifact and review relationship | raw Review or Moderation record |
| Score Record plus exact scale | `concord:score_summary` | `result_summary` | `conditional_candidate` | `planned` | exact Score target and scale; moderation state | Grade or universal proficiency inference |
| Activity/Session | context summary | `context_summary` | `supporting_metadata_only` | `implemented` natively | exact Artifact context | unrelated participants |
| Group | Group context | `context_summary` | `supporting_metadata_only` | `implemented` natively | exact represented Group | membership treated as authorship |
| Artifact Author/Subject | relationship metadata | relationship | `supporting_metadata_only` | `implemented` natively | exact confirmed record | standalone artifact use |
| Artifact Review | canonical review | source interpretation | `source_only` | `implemented` natively | authorized reader only | direct exposure |
| Moderation Record | moderation | source interpretation | `source_only` | `implemented` natively | authorized reader only | direct exposure |
| route or raw retained scan | operational/source bytes | none | `prohibited` | varies | none | direct exposure |

### Artifact projection

A Concord Artifact projection may expose:

- exact Artifact Instance;
- exact approved Artifact Pages;
- artifact category;
- Activity and Session context;
- confirmed authorship;
- confirmed subject relationships;
- represented Group where applicable;
- representation status;
- correction lineage;
- privacy classification;
- and bounded display metadata.

It must not expose the complete surrounding Concord graph.

### Artifact-category treatment

#### `student_work`

Ordinarily suitable for Candidate consideration when:

- Artifact status is complete enough;
- exact pages or digital representation are available;
- Portfolio Subject relationship is supported;
- authorship or contribution is established where required;
- and privacy permits consideration.

#### `project_record`

May represent individual, collaborative, or supporting work according to exact relationships.

#### `laboratory_record`

May be individual or collaborative. The projection must preserve Group, authorship, recorder, and represented-position context.

#### `discussion_record`

Conditional because it may represent several speakers or positions.

It requires exact attribution, multi-subject review, representation-status preservation, and minimum-necessary exposure.

#### `observation`

Not an ordinary original-work Candidate.

A producer-approved observation summary may be conditional under a Profile and privacy review. Raw teacher-restricted observation data remain source-only or prohibited.

### Page-kind treatment

| Page kind | Exposure treatment |
| --- | --- |
| `primary` | component of approved Artifact projection |
| `continuation` | component of approved Artifact projection |
| `rubric` | separate feedback/evaluation projection, not automatically original work |
| `cover` | supporting metadata only |
| `instructional` | supporting metadata or omitted |
| `observation` | conditional or source-only |
| `attachment_label` | supporting metadata only |

A page ID alone does not make a page a standalone Candidate.

### Group artifacts

A Group Artifact may become a Candidate for one Portfolio Subject only when the projection preserves:

- Group identity;
- complete Artifact identity;
- confirmed Artifact Author assertions;
- confirmed Artifact Subject assertions where relevant;
- documented contribution where available;
- authorship mode;
- representation status;
- multi-subject status;
- and privacy policy.

The following distinctions are invariant:

```text
Group Membership != Artifact Author
Artifact Author != contribution to every component
recorder_for_group != sole author
collective_group_author != individual Score target
Group Score != individual Score
```

Group Artifacts normally require collaborator and audience review.

### Authorship status

Unqualified individual authorship normally requires:

```text
attribution_status = confirmed
```

`proposed`, `disputed`, `unknown`, and `superseded` do not authorize a confirmed individual-authorship claim.

A disputed artifact may remain source-resolvable while being:

- unresolved;
- ineligible for individual presentation;
- or limited to a carefully labeled Group-context projection.

### Representation status

Concord representation values such as:

- individual view;
- recorder summary;
- majority position;
- unanimous position;
- multiple named positions;
- no consensus;
- and not applicable

must remain explicit.

Vitrine must not flatten them into one generic Group product.

### Score summary

A Concord Score summary may include:

- exact Score Record;
- exact Score target;
- Criterion;
- standard-backed or local Score kind;
- exact Scoring Scale revision and meanings;
- disposition;
- value only where disposition permits a value;
- scorer provenance where appropriate;
- moderation state;
- Score Evidence Links;
- and correction history.

It must not convert the Score into:

- Grade;
- percentage;
- universal proficiency;
- mastery;
- or individual result when the target is a Group.

A non-score disposition remains a non-score disposition.

### Concord invariants

- Raw Review and Moderation records remain source-only.
- Group Membership does not prove authorship or contribution.
- Role assignment does not prove Artifact authorship.
- Group Score does not create individual Score or proficiency.
- Instructional and cover pages are not student work.
- Privacy Policy remains producer authority and must be carried into exposure review.

## Portia exposure boundary

### Default suppression

All ordinary Portia records are suppressed.

Ordinary Vitrine discovery reveals:

```text
no result
no title
no count
no preview
no filename
no facet
no hidden-result placeholder
```

A matching Core intervention publication or capability does not override suppression.

### Prohibited direct Candidates

The following do not become direct Portfolio Candidates:

- Event;
- Event Participant;
- Event Participant Role;
- Account;
- Observation;
- Concern;
- Referral;
- Classification;
- Hypothesis;
- Determination;
- Response;
- Support Process;
- intervention plan;
- implementation or fidelity record;
- Communication;
- Follow-Up;
- Outcome;
- family communication;
- privacy report;
- student-history report;
- and complete intervention manifest.

### Future portfolio-safe projection

A future Portia projection may be architecturally represented as:

```text
portia:portfolio_safe_projection
```

Its disposition is `conditional_candidate` and readiness is `planned`.

Potential semantic kinds include:

- student-selected reflection;
- documented strength;
- progress toward a self-selected goal;
- successful use of a replacement skill;
- self-advocacy;
- voluntary restorative artifact;
- and teacher-approved growth statement.

These concepts require a later Portia-owned public contract.

### Required properties

A Portia-safe projection must be:

- explicitly created for portfolio use;
- opt-in;
- purpose-specific;
- separately permissioned;
- student-reviewable;
- revocable where policy permits;
- limited to the Portfolio Subject;
- free of unrelated participant information;
- free of unrelated Event history;
- free of hidden determination or intervention detail;
- and bound to an exact source and projection revision.

It must provide only a closed minimum-necessary allowlist.

It must not provide a generic pointer that allows Vitrine to reopen the complete Portia graph.

### Prohibited content

A Portia-safe projection must not include or imply:

- allegation;
- guilt;
- responsibility;
- disciplinary finding;
- Event or incident count;
- referral count;
- tier;
- compliance score;
- removal history;
- disputed account;
- behavior prediction;
- functional-behavior hypothesis;
- disability or accommodation status;
- counseling or mental-health information;
- safety or threat information;
- family communication;
- demographic comparison;
- or another participant’s information.

### Linked sibling artifacts

When Portia references a substantial reflection or restorative artifact owned by Quillan or Concord:

- Quillan or Concord remains source owner;
- Portia may provide minimum-necessary purpose context;
- Portia does not republish the artifact as Portia-owned;
- Portia’s reference does not broaden source access;
- and Vitrine preserves both relationships without merging ownership.

### Portia projection matrix

| Native/public source | Projection concept | Family | Disposition | Readiness | Required relationship/review | Prohibited content |
| --- | --- | --- | --- | --- | --- | --- |
| ordinary Portia records | none | none | `suppressed` | n/a | no ordinary discovery | all existence metadata |
| exact student-authored reflection approved for portfolio use | safe reflection projection | `reflection` | `conditional_candidate` | `planned` | explicit opt-in, subject, privacy, and student review | surrounding Event or intervention graph |
| strength or goal-progress statement | safe growth projection | `growth_summary` | `conditional_candidate` | `planned` | explicit approved projection and purpose | allegations, counts, tiers, disability, family data |
| voluntary restorative artifact owned by Quillan/Concord | sibling artifact plus Portia context | producer-native family | governed by source producer | depends on source producer | source producer relationship plus Portia purpose context | ownership transfer and broadened access |
| complete intervention manifest | none | none | `suppressed` | future publication possible | none | all direct content and existence leakage |

## Group and multi-subject behavior

A projection containing several students must declare one of:

```text
single_subject
subject_isolated
collaborative_multi_subject
suppressed_multi_subject
```

### `single_subject`

The projection contains only the Portfolio Subject’s information.

### `subject_isolated`

The producer creates a bounded subject-specific projection from a multi-subject source.

### `collaborative_multi_subject`

The projection intentionally preserves collaborator context and requires additional review.

### `suppressed_multi_subject`

The producer cannot safely isolate or disclose the source, so it cannot become a Candidate for the requested context.

Vitrine must not perform ad hoc field deletion to convert a multi-subject source into a supposedly safe individual projection.

## Required relationship declarations

A descriptor may require exact relationships such as:

- attempt subject;
- submission subject;
- confirmed Artifact Author;
- confirmed Artifact Subject;
- documented contributor;
- represented Group;
- individual Score target;
- Group Score target;
- student-selected Portia projection subject;
- or producer-approved report subject.

Relationship absence or conflict must remain explicit.

## Required review declarations

Initial review kinds should be able to represent:

- teacher confirmation;
- student review;
- collaborator review;
- multi-subject review;
- rights review;
- privacy review;
- sanitization review;
- accessibility review;
- and regulated-profile review.

A descriptor declares required review. It does not create the review result.

## Availability and staleness

Projection availability must distinguish:

- source resolved but projection not declared;
- projection contract declared but reader unavailable;
- reader available but representation missing;
- representation generated and exact;
- representation stale relative to source;
- representation withdrawn;
- and representation superseded.

A stale projection must not be silently regenerated or substituted under the prior projection identity.

## Failure vocabulary

The conceptual failure vocabulary includes:

```text
projection_not_declared
projection_contract_unsupported
projection_reader_unavailable
projection_not_implemented
projection_source_only
projection_metadata_only
projection_prohibited
projection_suppressed
projection_condition_unsatisfied
projection_relationship_unresolved
projection_authorship_unconfirmed
projection_group_review_required
projection_collaborator_review_required
projection_rights_review_required
projection_student_review_required
projection_sanitization_required
projection_multi_subject
projection_private_field_present
projection_operational_field_present
projection_representation_unavailable
projection_representation_stale
projection_withdrawn
projection_superseded
raw_native_record_prohibited
raw_retained_scan_prohibited
manifest_not_candidate_representation
portia_projection_not_approved
portia_source_suppressed
```

These failures remain distinct from:

- catalog or Publication failure;
- manifest-integrity failure;
- source-access denial;
- Profile prohibition;
- Selection rejection;
- and snapshot-generation failure.

## Edge cases

### Valid manifest with no projection

The source remains valid. Vitrine records `projection_not_declared` and creates no Candidate.

It does not read native files.

### User requests the manifest itself

Vitrine rejects ordinary artifact selection because the manifest is source-only and offers only declared producer projections.

### ScoreForm has several attempts

Each exact attempt may be evaluated separately. No automatic highest, latest, first, or official attempt is selected.

### Raw ScoreForm scan requested

Direct exposure is rejected. Only a future sanitized ScoreForm rendering may be considered.

### ScoreForm selected-answer details requested

The ordinary attempt summary omits them. An exact restricted question-evidence contract is required.

### ScoreForm alignment mistaken for proficiency

Vitrine preserves alignment and explicitly rejects proficiency or mastery inference.

### Quillan submission has selected and duplicate pages

The original-work projection includes selected evidence only. Duplicate, candidate, replacement, and excluded evidence remain out of the projection unless a specific producer rule says otherwise.

### Quillan feedback has private notes

The student-facing feedback projection remains eligible. Private notes and their existence remain undisclosed.

### Quillan feedback becomes stale

Vitrine records staleness. It does not regenerate the export or retarget the Candidate silently.

### Quillan class report mentions the subject

The report is not treated as the subject’s artifact and is prohibited for individual Candidate use.

### Concord authorship is proposed or disputed

Vitrine does not present confirmed individual authorship. The source may remain unresolved or limited to a labeled Group-context projection.

### Group Member is not Artifact Author

Membership alone creates no individual Artifact Candidate.

### Recorder represented a Group position

The projection preserves `recorder_for_group` and representation status. The recorder is not labeled sole author.

### Multiple named positions

The projection preserves that status and requires collaborator and audience review.

### Group Artifact has a Group Score

The Artifact may be a collaborative Candidate. The Score remains Group-targeted and does not create individual proficiency.

### Instructional or cover page appears with an Artifact

It is supporting metadata or omitted, not student-authored work.

### Portia publication appears in Core discovery

The source is suppressed before ordinary candidate presentation. No count, title, preview, or hidden-result indicator is shown.

### Portia has a positive Observation

The raw Observation remains suppressed. Only a future explicit safe projection may become a Candidate.

### Portia references Quillan or Concord work

The sibling producer remains source owner. Portia context does not broaden the sibling projection.

### Same source has original-work and feedback representations

The representations have separate projection identities and separate Candidates.

### Multi-subject source must be narrowed

Vitrine requires a producer-approved subject-isolated or collaborative projection. It does not redact native data ad hoc.

### Projection contract exists but reader is unavailable

Readiness is `unavailable`; no private parsing fallback is used.

### Projection is permitted but not implemented

Exposure may be `candidate_eligible` or `conditional_candidate`, while readiness is `planned`.

### Projection is superseded

Historical Candidates retain the prior exact projection. New evaluation uses the explicit successor.

### Source and rendering digests differ

Both digests are preserved for their respective byte layers. The difference is not a corruption finding.

### Issued snapshot uses historical projection

The snapshot retains the exact historical projection and Candidate references. Later producer changes do not rewrite it.

## Canonical versus derived state

### Producer-canonical

- native records;
- public manifest;
- projection contract;
- producer-rendered representation;
- producer projection revision;
- producer privacy classification.

### Vitrine-canonical

- exact descriptor reference used by a Candidate Evaluation;
- Exposure Decision relied upon by curation;
- readiness observation snapshot used by the evaluation;
- exact Candidate representation reference;
- and correction or supersession relationships.

### Derived

- projection catalogs;
- display matrices;
- search facets;
- previews;
- current-readiness dashboards;
- and compatibility summaries.

Derived state must be rebuildable and must not reveal suppressed sources.

## Downstream issue boundaries

### Issue #8: Selection, ordering, annotation, and reflection

Defines:

- who selects or rejects a Candidate;
- section placement;
- ordering;
- display title and caption;
- rationale;
- annotation;
- reflection;
- approval;
- replacement;
- and curation history.

This design defines only what may be selected.

### Issue #9: Snapshot, export, checksum, and immutability

Defines:

- approved representation retrieval;
- copied bytes;
- rendered derivatives;
- source and copied digests;
- generated indexes;
- omission records;
- snapshot manifests;
- and immutable issuance.

This design does not claim copied bytes.

### Issue #10: Privacy, redaction, and audience controls

Defines:

- source-access authorization;
- recipient identity;
- audience permission;
- consent;
- collaborator treatment;
- redaction;
- metadata suppression;
- disclosure review;
- and disclosure logging.

This design declares review requirements without implementing them.

### Issue #11: Regulated Profiles

Defines concrete evidence and document requirements. A regulated Profile may permit restricted projection kinds but must still use the producer-approved catalog.

## Security and privacy constraints

- Use exact allowlists.
- Never use native-file fallback.
- Never treat filesystem readability as exposure authority.
- Never expose raw retained scans directly.
- Never expose ScoreForm answer keys or detector internals.
- Never expose Quillan private notes or their existence.
- Never expose other students through class reports.
- Never infer Concord individual authorship or Score targeting.
- Never reveal suppressed Portia existence through counts or diagnostics.
- Never copy complete Portia graphs into safe projections.
- Never represent planned projections as implemented.
- Preserve minimum-necessary output and exact provenance.

## Unresolved questions

1. Which exact projection identifiers and contracts will each producer accept?
2. Which package owns the eventual Vitrine adapter registry?
3. How will producers publish rendered projection digests and media metadata?
4. Which ScoreForm item-level details are permitted for regulated Profiles?
5. How will Quillan publish selected original-work bytes independently from feedback exports?
6. Which Concord contribution record will support individual portfolio attribution?
7. How will collaborator review be represented before issue #10?
8. Which Portia safe-projection kinds will Portia itself accept?
9. Should a shared Core capability vocabulary eventually describe representation classes without defining exposure policy?
10. How will retired projection contracts remain available for historical snapshot verification?

None of these questions permits Vitrine to invent a projection before its producer defines one.

## Validation invariants

1. Producer manifests are source-only unless an explicit exceptional contract says otherwise.
2. Native records are not directly exposed.
3. Producers own projection contracts.
4. Vitrine cannot invent a missing projection.
5. Exact allowlists govern exposed fields.
6. Exposure policy and implementation readiness remain separate.
7. Projection identity is producer-owned and versioned.
8. Broad semantic family does not replace exact projection identity.
9. Supporting metadata cannot become a standalone Candidate.
10. Exposure does not establish source authorization.
11. Exposure does not establish audience authorization.
12. Exposure does not create Selection.
13. Exposure does not claim copied bytes.
14. Raw retained scans are not ordinary Candidates.
15. Sanitized renderings require producer-owned contracts.
16. Operational fields are excluded.
17. Sensitive fields require suppression or explicit minimum-necessary projection.
18. Multi-subject sources require subject-specific or collaborative projection.
19. ScoreForm preserves every attempt.
20. ScoreForm does not select official, best, latest, or Grade-bearing attempts.
21. ScoreForm alignment is not proficiency.
22. ScoreForm answer keys and detector internals remain prohibited.
23. Quillan original work uses selected evidence only.
24. Quillan private notes never enter a projection.
25. Quillan retained-source paths never enter student-facing projections.
26. Quillan feedback remains distinct from canonical review.
27. Concord Group Membership is not authorship.
28. Concord authorship status is preserved.
29. Concord representation status is preserved.
30. Concord Group Scores remain Group-targeted.
31. Concord Review and Moderation remain source-only.
32. Portia is suppressed by default.
33. Portia exposure requires an explicit safe projection.
34. Portia safe projections contain no unrelated graph.
35. Portia safe projections exclude allegations, determinations, disability, safety, and family detail.
36. Linked sibling artifacts retain source ownership.
37. Projection changes do not silently rewrite Candidates.
38. Historical Selections retain exact projection references.
39. Manifest, source-artifact, rendered-projection, and copied-representation digests remain distinct.
40. No sibling repository is modified by this issue.
