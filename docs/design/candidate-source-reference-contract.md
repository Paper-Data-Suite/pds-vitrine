# Candidate and Source-Reference Contract

- **Issue:** #6, “Define candidate and source-reference contracts”
- **Design date:** 2026-08-05
- **Status:** Foundation design paired with proposed ADR 0004; not a final serialized schema or runtime implementation
- **Applies to:** `pds-vitrine` v0.1.0 foundation work

## 1. Purpose

This document defines the conceptual records and trust sequence Vitrine will use to discover, verify, resolve, evaluate, and preserve potentially portfolio-relevant source material.

It defines:

- Publication Discovery Runs and Findings;
- exact Core Publication Source References;
- referenced Academic Work Registration snapshots;
- publication-series and withdrawal observations;
- manifest-integrity observations;
- producer compatibility, reader, and Vitrine adapter support;
- Producer Source References;
- Source Artifact and Representation References;
- native attempt and standard references;
- Portfolio Subject Relationship Assertions;
- privacy and sensitivity metadata;
- multidimensional availability;
- immutable Candidate Evaluations;
- positive Portfolio Candidates;
- explicit current-evaluation pointers;
- correction, supersession, and historical behavior;
- canonical, derived, and transient state;
- deterministic duplicate handling;
- and downstream boundaries for selection, producer exposure, snapshots, and privacy enforcement.

The paired architectural decision is [ADR 0004: Candidate Discovery and Source References](../decisions/0004-candidate-discovery-and-source-references.md). It is **Accepted** following the issue #13 portfolio foundation audit.

## 2. Governing boundary

Vitrine discovers through Core but resolves educational meaning through producer-owned public contracts.

```text
bounded Core catalog discovery
  -> canonical Publication Record reload
  -> exact registration and series-state reload
  -> producer-profile compatibility evaluation
  -> exact Vitrine adapter selection
  -> source-access authorization
  -> exact manifest path and digest verification
  -> producer-owned public reader
  -> producer-native source projection
  -> Portfolio Subject relationship resolution
  -> exact Portfolio Profile eligibility evaluation
  -> Portfolio Candidate
```

Each arrow is a boundary. Success at one stage does not imply success at the next.

```text
catalog row
  != canonical publication
  != compatible publication
  != verified manifest
  != resolved producer source
  != authorized source
  != profile-eligible source
  != Portfolio Candidate
  != selected Portfolio item
  != copied representation
  != audience-approved disclosure
```

A valid Candidate means only:

> Under one exact Portfolio, Portfolio Subject, Profile revision, authorization context, and verified publication/source projection, this exact source representation may be considered for later curation.

It does not mean the source:

- is selected;
- is approved;
- is copied;
- is disclosed;
- proves proficiency;
- is Grade-bearing;
- is the producer’s official or preferred attempt;
- or satisfies an external authority.

## 3. Scope and non-goals

This is a conceptual design. It does not define:

- final JSON Schema;
- Python models;
- database tables;
- filesystem writers;
- locking or transaction mechanics;
- Core catalog query implementation;
- Core verification implementation;
- runtime Vitrine adapters;
- producer public readers;
- exact ScoreForm, Quillan, Concord, or Portia exposure projections;
- Selection, ordering, annotation, reflection, or approval records;
- copied bytes, generated files, snapshot manifests, or checksums;
- audience authorization, consent, redaction, or disclosure logging;
- an operational regulated Profile;
- Grade or proficiency calculation;
- or sibling-repository changes.

Issue #7 will decide producer-specific exposure. Issue #8 will define curation records. Issue #9 will define copied representations and issuance. Issue #10 will define authorization and disclosure controls.

## 4. Cross-repository review baseline

The following repository state was reviewed on 2026-08-05. Commit links are immutable review anchors.

| Repository | Reviewed state | Authoritative material | Reusable pattern | Incompatible assumption | Unresolved dependency |
| --- | --- | --- | --- | --- | --- |
| `pds-vitrine` | [`7474ac8`](https://github.com/Paper-Data-Suite/pds-vitrine/commit/7474ac87fe3c3601b943660c414ed34050804272); documentation-only foundation | Research, module boundaries, Portfolio Subject identity, versioned Profile contract, proposed ADRs 0001-0003 | Explicit authority, exact historical bindings, purpose-specific policy | No runtime adapter, persistence, authorization, or snapshot implementation exists | Candidate schemas and implementation remain future work |
| `pds-core` | [`6c50721`](https://github.com/Paper-Data-Suite/pds-core/commit/6c507213618b68a6dd3ea096e1a898201ff029e6); released v0.6.0 | Academic registry integration guide, public Publication Record and compatibility APIs | Derived discovery, canonical reload, immutable publications, exact digest binding, explicit supersession/withdrawal | Catalog rows and capabilities are not source authority or authorization | Vitrine must build its own candidate and policy layer |
| `pds-scoreform` | [`f8fa1d7`](https://github.com/Paper-Data-Suite/pds-scoreform/commit/f8fa1d705ce76b0bc0ade5b285807ef28750134e); Core 0.6 registration plus manifest models | Academic Result Manifest v1, revision policy, registration implementation | Every attempt preserved, exact response states, question alignment, deterministic manifest reader | No workspace manifest generation, publication producer Profile, or complete publication workflow yet | Issue #7 must choose portfolio-safe projections after producer publication completes |
| `pds-quillan` | [`05fecf2`](https://github.com/Paper-Data-Suite/pds-quillan/commit/05fecf23d29e56b45cba58ed97906f5353290033); executable v0.8.9 on prior Core line | Assignment, submission, review, feedback-export, and reporting contracts | Original work, review state, student-facing feedback, and private notes are distinct | Private native files are not a consumer contract | Core 0.6 publication and consumer-neutral reader remain future work |
| `pds-concord` | [`87a8165`](https://github.com/Paper-Data-Suite/pds-concord/commit/87a8165845bc61ad188e78817ccb2415af3701e1); native model implementation started | Native models, relationship validation, accepted ADR 0015 | Artifact Author/Subject, Group, Score target, scale revision, evidence lineage, corrections remain explicit | Membership is not authorship; package has no publication Profile or public manifest yet | Storage, publication, public reader, and artifact exposure remain future work |
| `pds-portia` | [`8cd4b1f`](https://github.com/Paper-Data-Suite/pds-portia/commit/8cd4b1f2ca80cc240693184c87e5df463ba375cf); architecture and schemas | Typed references, Event Participant relations, privacy boundaries | Exact references, append-preserving history, minimum-necessary handling | Intervention records are not ordinary portfolio candidates | No executable publication or privacy-safe projection exists |
| `pds-meridian` | [`c7e9129`](https://github.com/Paper-Data-Suite/pds-meridian/commit/c7e9129f6547bca9953f8ae5c8718ce358341172); ingestion architecture | Core v0.6 publication-ingestion architecture and consumer-adapter decision | Ordered verification stages, exact adapter selection, multidimensional failures, provenance | Meridian’s evidence inventory and grading policy are not Vitrine candidate policy | No production ingestion implementation exists |

### 4.1 Core consumer obligations

The active Core integration guide requires a consumer to:

1. use the catalog only for candidate discovery;
2. reload the canonical Publication Record;
3. reload registration state where applicable;
4. evaluate producer compatibility;
5. verify the exact manifest path and digest;
6. parse only through the producer’s public contract;
7. preserve native scales, attempts, dispositions, and intervention states;
8. check supersession and withdrawal;
9. record exact provenance;
10. apply authorization;
11. and apply consumer-owned policy afterward.

Vitrine adopts this trust sequence and adds Portfolio Subject, Profile, rights, privacy, and curation context.

### 4.2 Uneven producer readiness

The contract must honestly represent current readiness.

- ScoreForm has a pure public manifest model and decoder, but publication to Core is not yet complete.
- Quillan has mature native records and privacy-separated exports, but no accepted Core 0.6 publication contract.
- Concord has implemented native models and accepted publication architecture, but no public producer Profile or manifest.
- Portia has no executable publication and is suppressed by default.
- Meridian has consumer architecture only; a future report snapshot is a separate possible source family.

No Vitrine adapter may invent a missing producer contract.

## 5. Terms

### 5.1 Publication Discovery Run

A **Publication Discovery Run** is one bounded Vitrine operation that queries the disposable Core catalog for possible publications under one Portfolio context.

### 5.2 Publication Discovery Finding

A **Publication Discovery Finding** is a derived observation that a catalog row proposed a `publication_id` or that discovery infrastructure failed.

It is not a verified publication.

### 5.3 Core Publication Source Reference

A **Core Publication Source Reference** is a Vitrine-held immutable provenance snapshot copied from one verified canonical Core Publication Record and, when applicable, the exact referenced Academic Work Registration revision.

Core remains authoritative.

### 5.4 Manifest Verification Observation

A **Manifest Verification Observation** records whether the exact path and bytes bound by the canonical Publication Record were verified.

### 5.5 Producer Source Reference

A **Producer Source Reference** identifies one exact producer-native item exposed by an exact verified manifest and producer public reader.

### 5.6 Source Artifact Reference

A **Source Artifact Reference** identifies an exact producer-exposed artifact or file related to the Producer Source Reference.

It does not mean Vitrine copied the bytes.

### 5.7 Source Representation Reference

A **Source Representation Reference** distinguishes one original, rendered, translated, accessible, summary, or other producer-exposed representation.

### 5.8 Candidate Evaluation

A **Candidate Evaluation** is an immutable record of the full source-evaluation pipeline under one exact Portfolio, Subject, Profile, purpose, and authorization context.

It may have a positive or negative outcome.

### 5.9 Portfolio Candidate

A **Portfolio Candidate** is a positive Vitrine record for one exact source representation that may be considered for later curation.

### 5.10 Candidate Current Pointer

A **Candidate Current Pointer** explicitly identifies which Candidate Evaluation currently governs working use of one Candidate series.

Currency is never inferred from timestamps or greatest revision.

## 6. Conceptual graph

```text
Publication Discovery Run
  -> Publication Discovery Finding [0..*]
      -> canonical publication_id proposal
          -> Core Publication Source Reference
              -> Registration Snapshot [0..1]
              -> Publication Series Observation
              -> Manifest Verification Observation
              -> Compatibility Observation
              -> Authorization Decision Reference
              -> Producer Reader Observation
                  -> Producer Source Reference [0..*]
                      -> Source Artifact Reference [0..*]
                          -> Source Representation Reference [1..*]
                      -> Native Attempt Reference [0..*]
                      -> Candidate Standard Reference [0..*]
                      -> Portfolio Subject Relationship Assertion [1..*]
                      -> Source Privacy Metadata
                          -> Candidate Evaluation
                              -> Portfolio Candidate [0..1]
                                  -> Candidate Current Pointer
```

The graph contains references and observations. It does not transfer authority from Core or the producer to Vitrine.

## 7. Foundational invariants

1. A catalog row is never canonical.
2. Canonical Publication reload precedes source-reference creation.
3. Exact referenced registration revision is preserved where applicable.
4. An intervention publication has no fabricated registration.
5. Canonical series relationships determine lifecycle state.
6. Authorization precedes student-level manifest parsing.
7. Manifest verification precedes producer parsing.
8. Producer parsing uses an exact public reader.
9. Unknown contracts never use a fallback parser.
10. Adapter identity and projection version are preserved.
11. Core facts remain distinguishable from producer facts.
12. Producer facts remain distinguishable from Vitrine interpretation.
13. Access authorization remains distinct from Profile eligibility.
14. Profile eligibility remains distinct from Selection.
15. Selection remains distinct from disclosure.
16. One Candidate identifies one exact representation under one exact Portfolio context.
17. Candidate IDs are opaque and never reused.
18. Titles and filenames never provide durable source identity.
19. Candidate source endpoints are immutable.
20. Candidate refresh creates a new Evaluation.
21. Source replacement creates a new Candidate.
22. Historical and withdrawn publications remain historically resolvable.
23. Attempt identity and meaning remain producer-owned.
24. No attempt is automatically official, best, latest for grading, or Grade-bearing.
25. Standard alignment is not proficiency.
26. Subject relationships are typed and attributable.
27. Group Membership is not Artifact authorship, contribution, or individual proficiency.
28. Portia is suppressed by default without existence leakage.
29. Private Quillan records cannot be reached through direct file parsing.
30. Source Artifact References do not claim copied bytes.
31. Source, manifest, and future copied-byte digests remain distinct.
32. Availability is multidimensional.
33. Candidate indexes are derived and rebuildable.
34. Deterministic ordering never establishes authority.
35. Duplicate handling uses exact identity and producer lineage.
36. One producer source may have several distinct representations.
37. One source may evaluate differently under different Profiles.
38. Issued snapshots preserve exact historical Candidate provenance.
39. Diagnostics do not dump student-level manifest data.
40. Vitrine does not mutate sibling repositories.

## 8. Ordered candidate pipeline

The eventual implementation must expose ordered stages rather than one opaque `load_candidate()` operation.

### 8.1 Stage 1 — bounded catalog discovery

Query the Core catalog using bounded typed filters.

Permitted filters may include:

- class;
- producer module;
- publication kind;
- capability;
- work;
- publication state;
- or other Core-supported metadata.

Catalog ordering must be explicit and deterministic.

Catalog results may narrow work. They do not establish:

- canonical identity;
- current lifecycle;
- authorization;
- producer validity;
- subject relationship;
- or Profile eligibility.

### 8.2 Stage 2 — canonical Publication reload

Reload by exact `publication_id`.

Every copied field must come from the canonical Publication Record, not the catalog row.

Candidate drift is recorded when the row and canonical record differ or the publication no longer exists.

### 8.3 Stage 3 — exact registration reload

For `academic_result_set`, load the exact `academic_work_registration_revision` referenced by the Publication Record.

Validate:

- exact work agreement;
- producer contract;
- registration schema;
- source-record compatibility;
- and historical revision existence.

Current registration state may be observed for diagnostics, but it does not replace the historical referenced revision.

For `intervention_record_set`, registration must be absent.

### 8.4 Stage 4 — series and withdrawal observation

Reload enough canonical publication and withdrawal state to determine:

- current selectable head;
- withdrawn head;
- historical predecessor;
- explicit successor;
- contradictory branching;
- or cycle.

Do not infer the head from greatest revision, newest time, filename, or ID.

### 8.5 Stage 5 — producer compatibility

Evaluate the installed Core `PublicationProducerProfile`.

Compatibility covers exact:

- Core publication schema;
- producer module;
- Academic Work producer contract where applicable;
- publication kind;
- manifest contract;
- capabilities;
- and source-record contract.

A missing Profile and an incompatible Profile are separate failures.

A compatible Profile contains no parser and grants no access.

### 8.6 Stage 6 — Vitrine adapter selection

Select one exact Vitrine consumer adapter.

No generic adapter may claim unknown manifest versions.

Adapter selection precedes reading student-level content but follows canonical envelope compatibility.

### 8.7 Stage 7 — source-access authorization

Before opening the manifest, obtain an authorization decision for:

- the publication;
- the Portfolio Subject or requested target scope;
- the operation;
- the Portfolio purpose;
- and any known sensitive source family.

A denial or unresolved authorization stops parsing.

Privacy-minimized envelope metadata may be used to ask the authorization question.

### 8.8 Stage 8 — manifest verification

Use Core’s public path and verification surfaces to require:

- workspace-relative POSIX path;
- containment beneath the exact work root;
- regular nonsymlink file;
- recorded digest algorithm;
- exact recorded SHA-256 bytes;
- and agreement with canonical state.

A digest mismatch is an integrity failure, not a request to regenerate under the same publication ID.

### 8.9 Stage 9 — producer parsing

Invoke the producer’s exact public reader or pure contract API.

The adapter receives validated producer public models.

It must not:

- duplicate the producer validator;
- parse arbitrary JSON first;
- inspect native files;
- infer hidden fields;
- continue after partial parse;
- or print manifest content in diagnostics.

### 8.10 Stage 10 — source projection

Translate public producer models into exact Vitrine source references.

Projection may normalize storage shape, such as immutable tuples and tagged unions, but must preserve native meaning.

### 8.11 Stage 11 — subject relationship resolution

Resolve how the exact source relates to the Portfolio Subject.

The relationship must be supported by:

- producer-native relationship records;
- exact class-qualified student identity;
- or a separately attributable Vitrine relationship assertion allowed by policy.

No generic “student-related” boolean is sufficient.

### 8.12 Stage 12 — Profile eligibility

Evaluate the exact bound Portfolio Profile revision.

Preserve:

- matched requirement and rule IDs;
- allowed representations;
- prohibited source classes;
- conditional requirements;
- human-review requirements;
- and unresolved conditions.

### 8.13 Stage 13 — Candidate creation

Create a positive Candidate only if all mandatory stages permit consideration.

Negative outcomes remain Candidate Evaluations without a positive Candidate.

## 9. Publication Discovery Run contract

### 9.1 Ownership and status

A Publication Discovery Run is Vitrine-owned operational context.

It is canonical only when retained because later Candidate Evaluations cite it. Disposable search telemetry may remain transient.

### 9.2 Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `discovery_run_id` | Required | Opaque Vitrine identity |
| `record_type` | Required | Distinguishes the record |
| `contract_version` | Required | Serialized contract version |
| `portfolio_id` | Required | Exact Portfolio context |
| `portfolio_subject_id` | Required | Exact subject context |
| `profile_binding_id` | Required | Exact Profile binding |
| `portfolio_profile_id` | Required | Stable Profile series |
| `profile_revision` | Required | Exact immutable Profile revision |
| `requested_by` | Required | Attributable actor or service |
| `requested_purpose` | Required | Portfolio operation purpose |
| `query_filters` | Required | Privacy-minimized bounded Core catalog filters |
| `started_at` | Required | Aware timestamp |
| `completed_at` | Optional | Completion time |
| `catalog_observation` | Required | Health and schema observation |
| `finding_ids` | Required | Ordered references to derived findings |
| `diagnostic_summary` | Optional | Privacy-safe counts and codes |

### 9.3 Forbidden fields and behavior

A Discovery Run must not contain:

- manifest content;
- student names;
- private source titles when unauthorized;
- source previews;
- arbitrary SQL;
- authorization grants;
- selections;
- or a copied catalog database.

It must not trigger automatic catalog repair unless a later explicit operational contract authorizes that behavior.

## 10. Publication Discovery Finding contract

### 10.1 Purpose

A finding preserves what discovery proposed and what happened during canonical reload.

### 10.2 Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `discovery_finding_id` | Required | Opaque identity |
| `discovery_run_id` | Required | Parent run |
| `finding_kind` | Required | Candidate-row or discovery-infrastructure outcome |
| `proposed_publication_id` | Conditional | Minimal catalog proposal |
| `catalog_row_fingerprint` | Optional | Privacy-safe drift aid, not authority |
| `catalog_snapshot_id` | Optional | Core catalog inventory/snapshot metadata |
| `observed_at` | Required | Aware time |
| `canonical_reload_outcome` | Required | Reload disposition |
| `core_publication_source_reference_id` | Conditional | Present only after canonical verification |
| `reason_codes` | Required | Ordered privacy-safe diagnostics |

### 10.3 Finding kinds

Initial conceptual kinds include:

```text
catalog_candidate_found
catalog_candidate_drifted
canonical_publication_missing
canonical_publication_loaded
catalog_unavailable
catalog_stale
catalog_incompatible
catalog_locked
catalog_corrupt
no_matching_publication
```

### 10.4 Derived status

Discovery Findings are derived unless cited by a retained Candidate Evaluation. Even when retained, they remain observations rather than source authority.

## 11. Core Publication Source Reference contract

### 11.1 Purpose

The reference preserves the exact Core envelope used by one Candidate Evaluation.

### 11.2 Complete publication fields

| Field | Requirement | Authority |
| --- | --- | --- |
| `core_publication_schema_version` | Required | Core |
| `publication_id` | Required | Core |
| `work` | Required | Core `ModuleWorkRef` |
| `source_record` | Optional | Core `ModuleRecordRef` |
| `publication_kind` | Required | Core |
| `capabilities` | Required | Ordered Core values |
| `record_set_id` | Required | Producer value bound by Core |
| `record_set_revision` | Required | Producer revision bound by Core |
| `manifest_contract_version` | Required | Producer contract ID bound by Core |
| `manifest_path` | Required | Exact Core-bound path |
| `manifest_digest_algorithm` | Required | Core-controlled algorithm |
| `manifest_digest` | Required | Exact bound digest |
| `published_at` | Required | Core Publication time |
| `academic_work_registration_revision` | Conditional | Required for academic publication |
| `supersedes_publication_id` | Optional | Explicit predecessor |
| `canonical_loaded_at` | Required | Vitrine observation |
| `core_compatibility_context` | Required | Core contract/package range checked |

### 11.3 Registration snapshot

For an academic publication, preserve a nested exact registration snapshot with:

| Field | Requirement |
| --- | --- |
| `registration_schema_version` | Required |
| `registration_revision` | Required |
| `work` | Required and equal to publication work |
| `producer_contract_version` | Required |
| `title_snapshot` | Required but nonauthoritative display |
| `work_kind` | Required |
| `academic_intent` | Required |
| `lifecycle` | Required |
| `created_at` / `updated_at` | Required |
| `source_records` | Required, possibly empty only where Core permits |

Current registration state, if observed, belongs in a separate availability observation.

### 11.4 Immutability

The source reference is immutable after a Candidate Evaluation cites it.

A later canonical change creates a new reference and Evaluation.

## 12. Publication series observation

### 12.1 Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `series_observation_id` | Required | Opaque Vitrine identity |
| `publication_id` | Required | Observed publication |
| `series_identity` | Required | Complete Core series key |
| `logical_revision_identity` | Required | Complete Core revision key |
| `state` | Required | Explicit lifecycle observation |
| `observed_predecessor_id` | Optional | Canonical predecessor |
| `observed_successor_id` | Optional | Explicit canonical successor |
| `withdrawal_id` | Optional | Canonical withdrawal reference |
| `observed_at` | Required | Aware time |
| `source_inventory` | Required | Bounded canonical records considered |
| `reason_codes` | Required | Conflict or lifecycle details |

### 12.2 States

```text
current_selectable_head
current_withdrawn_head
historical_predecessor
superseded
withdrawn
series_conflict
series_cycle
state_unavailable
```

Historical and withdrawn are lifecycle states, not generic malformed states.

## 13. Manifest Verification Observation contract

### 13.1 Conceptual fields

| Field | Requirement |
| --- | --- |
| `manifest_verification_id` | Required |
| `publication_id` | Required |
| `work_root` | Required, safe workspace-relative form |
| `manifest_path` | Required and exact |
| `path_contained` | Required |
| `regular_file` | Required |
| `symlink_rejected` | Required |
| `digest_algorithm` | Required |
| `expected_digest` | Required |
| `observed_digest` | Conditional and privacy-safe |
| `verified_at` | Required |
| `verifier_contract_version` | Required |
| `outcome` | Required |
| `reason_codes` | Required |

### 13.2 Outcomes

```text
verified
path_invalid
outside_work_root
missing
not_regular_file
symlink_rejected
unreadable
digest_mismatch
canonical_state_changed
```

### 13.3 Security behavior

The observation must not retain:

- absolute home paths;
- temporary paths;
- file contents;
- partial manifest excerpts;
- or operating-system usernames.

## 14. Producer compatibility and adapter support

### 14.1 Core producer compatibility observation

Preserve:

- producer module ID;
- Profile presence;
- exact Profile identity or package source;
- Core publication schema support;
- producer contract support;
- publication-kind support;
- manifest-contract support;
- capability support;
- source-record contract support;
- evaluation time;
- and exact result.

### 14.2 Vitrine adapter support key

At minimum:

```text
producer_module_id
publication_kind
manifest_contract_version
producer_contract_version where applicable
source_record_kind/version where required
required capabilities where required
```

### 14.3 Adapter declaration fields

| Field | Requirement |
| --- | --- |
| `adapter_id` | Required |
| `adapter_contract_version` | Required |
| `candidate_projection_contract_version` | Required |
| `support_key` | Required |
| `public_reader_id` | Required |
| `reader_provider/package_identity` | Required |
| `supported_source_families` | Required |
| `supported_representation_families` | Required |
| `diagnostic_contract_version` | Required |

### 14.4 Exact selection

Adapter selection must be deterministic.

When more than one adapter claims the same exact support key, selection fails with a conflict. Package discovery order is not a tiebreaker.

## 15. Producer Reader Observation

### 15.1 Conceptual fields

| Field | Requirement |
| --- | --- |
| `producer_reader_observation_id` | Required |
| `adapter_id` / version | Required |
| `public_reader_id` / version | Required |
| `manifest_contract_version` | Required |
| `parse_started_at` / `parse_completed_at` | Required |
| `outcome` | Required |
| `producer_diagnostic_codes` | Optional and privacy-safe |
| `projected_source_count` | Optional and suppressible |
| `projection_contract_version` | Required |

### 15.2 Outcomes

```text
parsed
reader_missing
reader_incompatible
decode_failed
validation_failed
projection_failed
```

A parse failure must not expose manifest payloads.

## 16. Producer Source Reference contract

### 16.1 Purpose

One Producer Source Reference identifies one exact producer-native item within one exact verified publication.

### 16.2 Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `producer_source_reference_id` | Required | Opaque Vitrine reference identity |
| `producer_module_id` | Required | Exact producer |
| `work` | Required | Complete module-qualified work |
| `publication_id` | Required | Exact Core publication |
| `manifest_contract_version` | Required | Producer contract |
| `manifest_digest` | Required | Exact manifest binding |
| `source_reference_kind` | Required | Core record, producer-native, or manifest-local |
| `source_record_kind` | Required | Producer vocabulary |
| `source_record_id` | Required when producer supplies durable ID |
| `source_record_contract_version` | Conditional | Exact version |
| `manifest_local_item_id` | Conditional | Durable producer-defined item identity |
| `native_revision` | Optional | Producer revision, not Core revision |
| `native_lineage_id` | Optional | Producer lineage |
| `native_predecessor_reference` | Optional | Producer correction/supersession |
| `native_lifecycle` | Optional | Producer state |
| `native_disposition` | Optional | Producer state, not Vitrine outcome |
| `source_generated_at` | Optional | Producer timestamp |
| `source_provenance_refs` | Optional | Producer-native references |
| `adapter_id` / version | Required | Projection provenance |
| `projected_at` | Required | Vitrine time |

### 16.3 Reference kinds

```text
core_module_record
producer_native_record
manifest_local_item
```

A manifest array index is never a valid durable item ID by itself.

### 16.4 Authority

The producer owns source identity and semantics. Vitrine owns only the immutable reference and portfolio-specific evaluation.

## 17. Source Artifact Reference contract

### 17.1 Conceptual fields

| Field | Requirement |
| --- | --- |
| `source_artifact_reference_id` | Required |
| `producer_source_reference_id` | Required |
| `producer_artifact_id` | Required when supplied |
| `artifact_kind` | Required |
| `native_artifact_revision` | Optional |
| `safe_relative_locator` | Optional and producer-controlled |
| `source_filename_snapshot` | Optional display only |
| `media_type` | Required |
| `source_byte_digest` | Optional |
| `source_byte_digest_algorithm` | Conditional |
| `byte_size` | Optional |
| `page_or_component_reference` | Optional |
| `language` | Optional |
| `native_availability` | Required |
| `rights_metadata_reference` | Optional |

### 17.2 Forbidden locators

Do not preserve as durable identity:

- absolute paths;
- drive-qualified paths;
- home-directory paths;
- temporary files;
- traversal paths;
- arbitrary private native paths;
- symlink targets;
- or filename alone.

## 18. Source Representation Reference contract

### 18.1 Purpose

One producer source or artifact may have several representations.

### 18.2 Conceptual fields

| Field | Requirement |
| --- | --- |
| `source_representation_reference_id` | Required |
| `producer_source_reference_id` | Required |
| `source_artifact_reference_id` | Optional |
| `representation_kind` | Required |
| `media_type` | Required |
| `producer_representation_id` | Conditional |
| `derived_from_representation_id` | Optional |
| `language` | Optional |
| `accessibility_features` | Optional |
| `translation_status` | Optional |
| `display_label_snapshot` | Optional |
| `availability` | Required |

### 18.3 Representation kinds

The generic architecture may accommodate:

```text
original
producer_summary
rendered_feedback
result_projection
accessible_alternate
translation
transcript
thumbnail
producer_report
```

Issue #7 decides which exact producer representations exist and may be exposed.

### 18.4 Identity consequence

The original and rendered feedback remain separate Candidates even when they share one source.

## 19. Native Attempt Reference contract

### 19.1 Conceptual fields

| Field | Requirement |
| --- | --- |
| `native_attempt_reference_id` | Required |
| `producer_module_id` | Required |
| `work` | Required |
| `source_student_or_target_ref` | Required |
| `attempt_identity_kind` | Required |
| `attempt_id_or_number` | Required |
| `attempt_contract_version` | Optional |
| `recorded_at` | Optional |
| `origin_or_kind` | Optional |
| `source_provenance_refs` | Optional |

### 19.2 Prohibited inferred status

A Native Attempt Reference must not add:

```text
official
best
preferred
latest_for_grading
replacement
summative
Grade_bearing
```

unless an authoritative producer or other system explicitly provides that semantic field.

## 20. Candidate Standard Reference contract

### 20.1 Conceptual fields

| Field | Requirement |
| --- | --- |
| `candidate_standard_reference_id` | Required |
| `standard_id` | Required |
| `relationship_kind` | Required |
| `source_authority` | Required |
| `producer_source_reference_id` | Required |
| `source_field_or_record_ref` | Required |
| `order` | Optional where contract-significant |

### 20.2 Relationship kinds

```text
focus
alignment
governing
evidence_context
```

Namespaced extensions require documented semantics.

### 20.3 Non-equivalence

```text
question alignment
  != producer rating
  != selected standards evidence
  != Meridian proficiency
```

## 21. Portfolio Subject Relationship Assertion contract

### 21.1 Purpose

The assertion identifies why one exact source may be associated with the Portfolio Subject.

### 21.2 Conceptual fields

| Field | Requirement |
| --- | --- |
| `subject_relationship_assertion_id` | Required |
| `portfolio_subject_id` | Required |
| `subject_roster_association_id` | Required when roster-based |
| `producer_source_reference_id` | Required |
| `producer_person_or_target_ref` | Required |
| `relationship_kind` | Required |
| `relationship_authority` | Required |
| `supporting_record_refs` | Required |
| `asserted_by` | Required |
| `asserted_at` | Required |
| `status` | Required |
| `supersedes_assertion_id` | Optional |
| `rationale` | Optional and privacy-minimized |

### 21.3 Initial relationship kinds

The generic model must support producer-specific values such as:

```text
attempt_subject
submission_subject
artifact_author
artifact_subject
group_member
documented_contributor
recorder
individual_score_target
group_score_target
event_participant
represented_person
report_subject
vitrine_asserted_relationship
```

### 21.4 Authority classes

```text
producer_native
core_roster_resolution
institutional_crosswalk
teacher_confirmed
subject_authored_statement
```

A subject-authored or teacher-authored assertion remains distinct from producer-native authorship.

### 21.5 Prohibited inference

The following implications are invalid without another authoritative relationship:

```text
Group Member -> Artifact Author
Group Member -> documented contributor
Artifact Author -> individual Score target
Artifact Subject -> Artifact Author
Event Participant -> academic artifact owner
Portfolio Subject -> source author
```

## 22. Source privacy and sensitivity metadata

### 22.1 Conceptual fields

| Field | Requirement |
| --- | --- |
| `privacy_metadata_id` | Required |
| `producer_source_reference_id` | Required |
| `producer_privacy_classification` | Optional |
| `sensitivity_categories` | Required, possibly empty |
| `subject_scope_kind` | Required |
| `contains_other_students` | Required |
| `contains_third_party_information` | Required |
| `metadata_visibility` | Required |
| `minimum_necessary_projection_required` | Required |
| `restricted_source` | Required |
| `rights_review_required` | Required |
| `redaction_review_required` | Required |
| `classification_authority` | Required |
| `classification_observed_at` | Required |

### 22.2 Required distinctions

```text
source sensitivity
  != access authorization
  != Profile eligibility
  != disclosure permission
  != audience-specific redaction
```

### 22.3 Suppression

A suppressed source must not leak through:

- result counts;
- titles;
- hidden placeholders;
- filenames;
- candidate IDs;
- previews;
- facets;
- producer labels;
- or diagnostic text.

## 23. Availability Observation contract

### 23.1 Multidimensional matrix

The Evaluation must preserve separate dimensions:

| Dimension | Example states |
| --- | --- |
| `catalog` | available, missing, stale, locked, incompatible, corrupt |
| `canonical_publication` | loaded, missing, invalid, drifted |
| `registration` | loaded, absent_by_contract, missing, mismatched |
| `series` | current, historical, superseded, withdrawn, conflict |
| `producer_profile` | compatible, missing, incompatible |
| `adapter` | selected, missing, conflict, incompatible |
| `reader` | available, missing, incompatible |
| `manifest_integrity` | verified, missing, digest_mismatch, invalid_path |
| `producer_parse` | parsed, decode_failed, validation_failed |
| `source_resolution` | resolved, missing, invalid, superseded |
| `artifact` | available, missing, unsupported_media |
| `authorization` | allowed, denied, unknown |
| `subject_relationship` | supported, unresolved, conflict |
| `profile_eligibility` | permitted, conditional, prohibited, unresolved |
| `disclosure_review` | not_evaluated, allowed, denied, unresolved |

### 23.2 Overall status

An overall display status may be derived, but it must never replace the matrix.

## 24. Candidate Evaluation contract

### 24.1 Ownership and identity

A Candidate Evaluation is canonical Vitrine state when retained for curation, correction, or snapshot provenance.

It has an opaque, never-reused `candidate_evaluation_id`.

### 24.2 Conceptual fields

| Field | Requirement |
| --- | --- |
| `candidate_evaluation_id` | Required |
| `record_type` / `contract_version` | Required |
| `portfolio_id` | Required |
| `portfolio_subject_id` | Required |
| `profile_binding_id` | Required |
| `portfolio_profile_id` / `profile_revision` | Required |
| `requested_by` | Required |
| `requested_purpose` | Required |
| `discovery_finding_id` | Required where catalog-discovered |
| `core_publication_source_reference_id` | Conditional |
| `series_observation_id` | Conditional |
| `manifest_verification_id` | Conditional |
| `compatibility_observation_id` | Conditional |
| `authorization_decision_ref` | Conditional |
| `producer_reader_observation_id` | Conditional |
| `producer_source_reference_id` | Conditional |
| `source_artifact_reference_id` | Optional |
| `source_representation_reference_id` | Conditional for positive evaluation |
| `native_attempt_reference_ids` | Optional |
| `candidate_standard_reference_ids` | Optional |
| `subject_relationship_assertion_ids` | Conditional |
| `privacy_metadata_id` | Conditional |
| `availability_observation` | Required |
| `matched_requirement_ids` | Required, possibly empty |
| `eligible_section_ids` | Required, possibly empty |
| `outcome` | Required |
| `reason_codes` | Required |
| `evaluated_at` | Required |
| `evaluator_contract_version` | Required |
| `supersedes_candidate_evaluation_id` | Optional |
| `correction_reason` | Optional |

### 24.3 Outcomes

```text
eligible
conditionally_eligible
ineligible
unresolved
suppressed
```

### 24.4 Positive prerequisites

An `eligible` or `conditionally_eligible` Evaluation requires:

- canonical publication loaded;
- exact registration loaded or correctly absent;
- valid series observation;
- compatible producer Profile;
- one exact adapter;
- allowed source-access authorization;
- verified manifest;
- successful producer reader;
- exact source and representation;
- supported subject relationship;
- and Profile permission.

A conditional outcome may preserve later review requirements such as:

- rights review;
- collaborator treatment;
- accessible alternate required;
- or explicit teacher confirmation.

It may not bypass a denied authorization or integrity failure.

## 25. Portfolio Candidate contract

### 25.1 Identity and scope

A Portfolio Candidate is one immutable positive record.

Its scope includes:

```text
Portfolio
+ Portfolio Subject
+ exact Profile binding/revision
+ exact Core publication
+ exact producer source
+ exact representation
+ authorized purpose context
```

### 25.2 Conceptual fields

| Field | Requirement |
| --- | --- |
| `candidate_id` | Required opaque ID |
| `record_type` / `contract_version` | Required |
| `portfolio_id` | Required |
| `portfolio_subject_id` | Required |
| `profile_binding_id` | Required |
| `candidate_evaluation_id` | Required |
| `core_publication_source_reference_id` | Required |
| `producer_source_reference_id` | Required |
| `source_artifact_reference_id` | Optional |
| `source_representation_reference_id` | Required |
| `native_attempt_reference_ids` | Optional |
| `candidate_standard_reference_ids` | Optional |
| `subject_relationship_assertion_ids` | Required |
| `eligible_requirement_ids` | Required |
| `eligible_section_ids` | Required |
| `condition_state` | Required |
| `source_display_snapshot` | Optional |
| `privacy_metadata_id` | Required |
| `created_at` | Required |
| `created_by` | Required |
| `predecessor_candidate_id` | Optional |
| `source_successor_candidate_id` | Optional |

### 25.3 Candidate meaning

An eligible section means only “may be considered for this section.”

It does not perform section placement.

### 25.4 ID rules

The Candidate ID must not encode:

- student name;
- title;
- filename;
- work ID;
- attempt number;
- publication revision;
- digest;
- or Profile label.

## 26. Candidate Current Pointer

### 26.1 Decision

Current working evaluation is explicit.

The conceptual pointer is canonical Vitrine state and should use expected-revision or equivalent concurrency control in a later implementation.

### 26.2 Conceptual fields

| Field | Requirement |
| --- | --- |
| `candidate_id` | Required |
| `pointer_revision` | Required positive integer |
| `current_candidate_evaluation_id` | Required |
| `previous_candidate_evaluation_id` | Optional |
| `updated_at` | Required |
| `updated_by` | Required |
| `reason` | Required |

### 26.3 Rules

- The pointer references an Evaluation for the same Candidate source endpoint and context.
- A source endpoint change cannot be expressed through pointer movement; it requires a new Candidate.
- Greatest Evaluation revision or newest time never implies current state.
- Historical pointer revisions remain auditable.

## 27. Candidate refresh and correction

### 27.1 Refresh with same source

Create a new Candidate Evaluation when:

- canonical lifecycle changes;
- availability changes;
- authorization changes;
- Profile rules are re-evaluated without changing the binding;
- subject relationship status changes;
- rights or privacy review changes;
- or the adapter/reader observation is renewed.

The Candidate may remain the same only when its exact source endpoint and context remain the same.

### 27.2 New source

Create a new Candidate when any of these change:

- Publication Record;
- producer source item;
- representation;
- native attempt endpoint;
- Portfolio;
- Portfolio Subject;
- Profile binding/revision;
- or authorized purpose context in a way that changes Candidate meaning.

### 27.3 Correction

Material corrections preserve:

- erroneous Candidate;
- erroneous Evaluation;
- correcting actor;
- correcting time;
- reason;
- replacement Candidate or Evaluation;
- and downstream impact.

An operational Candidate is never retargeted in place.

## 28. Canonical, derived, and transient state

### 28.1 Canonical Vitrine state

Canonical state includes:

- retained Candidate Evaluations;
- Portfolio Candidates;
- Candidate Current Pointers and revisions;
- correction and supersession links;
- exact source-reference snapshots used by Selections;
- and source references embedded in issued-snapshot provenance.

### 28.2 Derived state

Derived state includes:

- candidate search indexes;
- faceted lists;
- thumbnails;
- cached summaries;
- duplicate suggestions;
- current availability dashboards;
- and aggregate discovery statistics.

A derived index may be deleted and rebuilt.

### 28.3 Transient state

Transient state includes:

- in-memory catalog rows;
- unretained parse models;
- temporary previews;
- manifest read buffers;
- locks;
- incomplete discovery runs;
- and temporary adapter values.

## 29. Duplicate and equivalence handling

### 29.1 Prohibited deduplication keys

Do not deduplicate solely by:

- title;
- filename;
- student ID;
- recorded time;
- source byte digest;
- manifest digest;
- record-set revision;
- or latest status.

### 29.2 Distinct cases

The following may be legitimately distinct:

- identical bytes issued to two students;
- identical bytes under two producer artifact identities;
- original work and rendered feedback;
- two attempts with identical responses;
- two Concord Artifacts with the same title;
- historical publication and successor;
- one source exposed through two record-set series;
- one group artifact related to several Portfolio Subjects;
- and two representations with different accessibility features.

### 29.3 Exact replay

Exact canonical replay of the same Publication Record and source endpoint should not create a second source authority.

It may create a new Evaluation when observation context changes.

### 29.4 Equivalence

Only producer-declared lineage or an explicit Vitrine equivalence record may relate two source references as equivalent.

Equivalence does not erase distinct provenance.

## 30. Deterministic ordering

Candidate lists must use explicit stable ordering.

A conceptual ordering key may include:

```text
producer_module_id
class_id
work_id
publication_kind
record_set_id
record_set_revision
source_record_kind
source_record_id or manifest_local_item_id
representation_kind
candidate_id
```

Ordering supports presentation only. It does not select current authority.

## 31. ScoreForm constraints

The generic architecture must preserve:

- exact assignment work;
- exact Publication Record;
- exact manifest revision;
- source assignment snapshot;
- class/work-qualified student identity;
- every attempt number;
- attempt origin;
- recorded time;
- points earned and possible;
- selected, blank, and ambiguous response states;
- question evidence;
- question-to-standard alignment;
- and exposed scan/manual provenance.

It must not:

- read `results.csv` directly;
- choose an official attempt;
- choose the highest attempt;
- choose the latest attempt for grading;
- fabricate a zero for an absent student;
- convert blank or ambiguous responses;
- treat alignment as proficiency;
- expose answer keys;
- expose detector internals;
- or treat the complete manifest as a student-facing artifact.

Issue #7 decides which ScoreForm projections can become representation Candidates.

## 32. Quillan constraints

Once Quillan exposes an accepted public reader, the architecture must preserve:

- assignment identity;
- submission identity;
- exact evidence/revision identity;
- submission state;
- review state;
- native scale;
- Focus Standards;
- observations;
- overall ratings;
- original-work representation;
- rendered feedback representation;
- and privacy-safe availability.

It must keep separate:

```text
submission state
review state
original student work
rendered feedback
teacher-private notes
assignment-local reports
```

Until a public contract exists:

- no Candidate is created;
- no private `submission.json` or `review.json` fallback is permitted;
- and no planned contract identifier is treated as implemented.

## 33. Concord constraints

The generic model must preserve separate references for:

- Activity;
- Session;
- Group;
- Group Membership;
- Artifact Instance;
- Artifact Page;
- Artifact Author;
- Artifact Subject;
- documented contribution;
- recorder;
- individual Score target;
- Group Score target;
- Criterion;
- Scoring Scale revision;
- Score Record;
- Score Evidence Link;
- Moderation;
- and correction history.

A group artifact associated with a Portfolio Subject requires an explicit relationship assertion.

Neither Vitrine inclusion nor student reflection turns Group evidence into individual proficiency.

## 34. Portia constraints

Portia is suppressed from ordinary discovery.

A matching Core catalog row must not produce a user-visible result.

Default behavior:

```text
no ordinary Candidate
no title
no count
no preview
no facet
no filename
no source-existence diagnostic
```

A future Portia Candidate requires:

- a specific Profile rule for one defined minimum-necessary projection;
- source-access authorization;
- explicit subject relationship;
- sensitivity treatment;
- deliberate opt-in;
- and later audience/privacy review.

A generic `intervention_record_set` match is insufficient.

## 35. Meridian constraints

A future immutable Meridian report may be a source only when Meridian exposes a public provenance-bound report reader.

Vitrine must not:

- read Meridian private calculations;
- reconstruct reports from internal evidence inventories;
- use Meridian to discover ordinary producer artifacts;
- or treat the evidence inventory as the Vitrine Candidate contract.

A Meridian report Candidate remains distinct from its underlying producer evidence.

## 36. Failure taxonomy

### 36.1 Discovery

```text
catalog_missing
catalog_stale
catalog_locked
catalog_incompatible
catalog_corrupt
candidate_drift
no_matching_publication
```

### 36.2 Canonical Core state

```text
publication_missing
publication_invalid
registration_missing
registration_invalid
registration_mismatch
series_state_invalid
series_cycle
withdrawal_state_invalid
canonical_state_changed
```

### 36.3 Publication lifecycle

```text
current
historical
superseded
withdrawn
withdrawn_head
series_state_unknown
```

### 36.4 Compatibility and support

```text
producer_profile_missing
producer_profile_incompatible
adapter_missing
adapter_conflict
reader_missing
publication_kind_unsupported
manifest_contract_unsupported
producer_contract_unsupported
source_record_contract_unsupported
capability_mismatch
```

### 36.5 Manifest integrity

```text
manifest_path_invalid
manifest_outside_work_root
manifest_missing
manifest_unreadable
manifest_not_regular_file
manifest_symlink_rejected
manifest_digest_mismatch
manifest_decode_failed
manifest_validation_failed
```

### 36.6 Producer resolution

```text
source_resolved
source_not_found
source_invalid
source_superseded
source_withdrawn
source_revision_unknown
artifact_missing
artifact_unavailable
artifact_media_unsupported
relationship_missing
relationship_conflict
```

### 36.7 Authorization and privacy

```text
access_allowed
access_denied
access_unknown
subject_scope_denied
purpose_scope_denied
artifact_scope_denied
sensitive_source_suppressed
privacy_review_required
rights_review_required
multi_subject_review_required
```

### 36.8 Profile eligibility

```text
profile_permitted
profile_conditionally_permitted
profile_prohibited
profile_rule_unresolved
profile_revision_mismatch
section_rule_unresolved
human_verification_required
```

### 36.9 Candidate outcome

```text
eligible
conditionally_eligible
ineligible
unresolved
suppressed
candidate_invalidated
candidate_superseded
```

No implementation may collapse these into one generic `unavailable` or `invalid_candidate` condition.

## 37. Edge-case decisions

### 37.1 Stale catalog row

- Record drift.
- Do not construct a Core reference from the row.
- Do not create a Candidate.

### 37.2 Missing catalog with canonical publications

- Report discovery unavailable.
- Do not claim canonical publications are invalid.
- A canonical fallback requires a later bounded operational decision.

### 37.3 Digest mismatch

- Stop before producer parsing.
- Preserve an integrity finding.
- Do not repair or overwrite historical bytes.
- Do not create a Candidate.

### 37.4 Compatible producer Profile, missing adapter

- Report consumer integration unsupported.
- Do not parse generic JSON.

### 37.5 Installed adapter, missing reader

- Record deployment unavailability.
- Do not report producer source invalidity.

### 37.6 Unknown manifest version

- Fail explicitly.
- Do not choose a nearby version.

### 37.7 Publication superseded after Candidate creation

- Preserve historical Candidate.
- Create a new Evaluation.
- Do not retarget the Candidate.
- Do not rewrite issued snapshots.

### 37.8 Publication withdrawn after Selection

- Preserve Candidate and Selection history.
- Mark future working use for review.
- Preserve lawful issued history.
- Do not equate withdrawal with deletion.

### 37.9 Artifact disappears while manifest remains valid

- Keep manifest integrity and artifact availability separate.
- Create a new Evaluation.
- Do not claim the Candidate never existed.

### 37.10 Original and rendered feedback

- Preserve separate representations.
- Do not deduplicate by source ID.

### 37.11 Same bytes in two issuances

- Preserve distinct issuance/artifact identity.
- Do not merge by digest.

### 37.12 Several ScoreForm attempts

- Preserve each exact attempt.
- No automatic highest or latest selection.

### 37.13 ScoreForm student absent

- No placeholder Candidate.
- No zero or incomplete inference.

### 37.14 Quillan private note beside public feedback

- Public feedback may be projected by a public reader.
- Private note remains invisible, including metadata.

### 37.15 Concord Group Member without authorship

- Individual-artifact relationship remains unsupported.
- Another authoritative assertion is required.

### 37.16 Group Score

- Preserve Group target.
- Do not convert to individual Score or proficiency.

### 37.17 Standard alignment

- Preserve alignment.
- Do not claim demonstrated proficiency.

### 37.18 Portia accidental filter match

- Suppress completely.
- Do not reveal hidden-result count.

### 37.19 Access allowed, disclosure unresolved

- Candidate consideration may proceed only when Profile permits.
- Audience disclosure remains unresolved.

### 37.20 Profile permits summary, prohibits original

- Evaluate each representation separately.
- Summary permission does not authorize original bytes.

### 37.21 Subject association corrected

- Re-evaluate.
- Preserve historical Candidate.
- Do not silently attach source to corrected subject.

### 37.22 Student annotation supplies relationship

- Mark as Vitrine-authored or subject-authored assertion.
- Do not elevate to producer-native authorship.

### 37.23 Adapter projection version changes

- Create a new Evaluation.
- Preserve earlier adapter version and projection.

## 38. Security, privacy, and logging

Implementations guided by this contract must:

- use synthetic test data;
- avoid logging manifest bodies;
- avoid student data in exception messages;
- authorize before parsing;
- suppress unauthorized source existence;
- avoid absolute or private native paths;
- scope caches to authorization context;
- reject generic parsers;
- avoid private producer imports;
- preserve privacy classifications without broadening disclosure;
- avoid ScoreForm answer keys and detector internals;
- exclude Quillan private notes;
- avoid inferred Concord ownership;
- and prevent Portia metadata leakage.

Diagnostics should identify:

- stage;
- contract;
- invariant;
- privacy-safe IDs;
- and remediation category

without reproducing source content.

## 39. Downstream issue boundaries

### 39.1 Issue #7 — producer artifact exposure

Issue #7 decides exact producer projections, including:

- ScoreForm attempt/result representations;
- Quillan original work, feedback, scans, and reports;
- Concord artifacts, Scores, and summaries;
- and any Portia minimum-necessary projection.

This document defines the generic envelope only.

### 39.2 Issue #8 — curation records

Issue #8 defines:

- Selection;
- rejection;
- section placement;
- ordering;
- display metadata;
- rationale;
- annotation;
- reflection;
- approval;
- and replacement.

Candidate creation performs none of those actions.

### 39.3 Issue #9 — snapshots and copied bytes

Issue #9 defines:

- copied representations;
- generated derivatives;
- copied-byte digests;
- indexes;
- omissions;
- snapshot manifests;
- and issuance.

Source references do not claim Vitrine possesses bytes.

### 39.4 Issue #10 — privacy and audience controls

Issue #10 defines:

- actor authorization;
- recipient identity;
- consent;
- disclosure;
- redaction;
- collaborator treatment;
- metadata suppression;
- and access logging.

This issue records decision references and privacy metadata only.

### 39.5 Issue #11 — regulated Profiles

Issue #11 instantiates exact regulated source/document requirements using this Candidate architecture.

## 40. Required later validation

A final serialized contract and implementation should test:

- exact key sets;
- identifier safety;
- aware timestamps;
- immutable collections;
- exact Core field copying;
- academic/intervention registration rules;
- canonical series traversal and cycle rejection;
- authorization-before-parse ordering;
- path containment and symlink rejection;
- exact digest verification;
- exact adapter support keys;
- adapter conflict detection;
- no fallback parsing;
- source identity and representation uniqueness;
- typed subject relationships;
- privacy suppression;
- three-stage distinction among ineligible, unresolved, and suppressed;
- pointer expected-revision behavior;
- correction and supersession acyclicity;
- deterministic ordering;
- and synthetic producer boundary scenarios.

## 41. Open implementation questions

These questions are intentionally deferred without weakening the conceptual boundary:

1. Whether Discovery Runs are retained by default or only when cited.
2. Exact serialized shape of authorization decision references.
3. Exact adapter entry-point or registry mechanics.
4. Whether producer readers are imported directly or supplied through deployment providers.
5. Exact Core API calls used for bounded canonical fallback.
6. Exact Candidate storage namespace under the Vitrine workspace.
7. Exact expected-revision mechanics for Candidate Current Pointers.
8. Exact namespaced artifact and representation vocabularies.
9. Whether source-byte digests may be retained for every artifact under privacy policy.
10. Which Candidate Evaluation fields are copied into issued snapshots versus referenced.

No open question permits:

- catalog authority;
- parsing before authorization;
- private producer crawling;
- generic fallback parsing;
- automatic attempt selection;
- Portia existence leakage;
- or in-place Candidate retargeting.
