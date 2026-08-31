# Released Producer Semantic Crosswalk and Vitrine Schema Audit v1

## Status

Issue #57 integration baseline for the released Phase 1 producer contracts.

Machine-readable companion:

```text
vitrine.released_producer_schema_audit
vitrine_released_producer_schema_audit_v1
```

This audit is a prerequisite specification only. It does not activate live adapters.

## Conclusion

The released ScoreForm 0.11.0, Quillan 0.10.0, and Concord 0.3.0 public
contracts do **not** require a general Vitrine schema redesign.

The existing Vitrine model is sufficient for:

- exact Core Publication and Academic Work Registration provenance;
- producer-native revision/lifecycle/disposition/lineage provenance;
- bounded Artifact identity, representation, media type, digest, and size;
- privacy/review metadata;
- explicit producer relationship values;
- persisted Portfolio Subject relationship assertions;
- Candidate source provenance;
- bounded transient producer display/projection fields;
- exact adapter contract identity.

One concrete deficiency was confirmed: v0.2 Snapshot copying assumed Vitrine
could reopen an approved producer filesystem path. Released Quillan and Concord
instead expose authorization-gated producer-owned APIs that return immutable
bytes without granting arbitrary path access.

Issue #57 therefore makes only two related additive Snapshot extensions:

```text
copied_source_without_required_source_locator_v1
authorized_source_bytes_v1
```

The pre-existing filesystem-provider path remains supported.

## Persistence boundary

Rich producer semantics do not need to be flattened into new persistent
`PortfolioCandidate` fields.

Persisted Candidate provenance is carried by:

```text
CandidateSourceEndpoint
  CorePublicationSourceReference
  ProducerSourceReference
  SourceArtifactReference | None
  PortfolioSubjectRelationshipAssertion[]
  SourcePrivacyMetadata
```

The producer adapter may carry bounded producer-native semantic detail in its
transient `ProjectedProducerSource` / `ProjectionDisplaySnapshot`. Candidate and
Profile evaluation then applies explicit Vitrine-owned consumer policy.

This preserves the ownership boundary:

```text
producer public reader owns producer semantic interpretation
Vitrine adapter preserves producer evidence
Vitrine Candidate/Profile layer owns portfolio policy
```

## Semantic disposition vocabulary

Every required producer semantic is classified as one of:

```text
preserved_directly
preserved_bounded_metadata
preserved_relationship_provenance
authorized_artifact_only
intentionally_omitted
deferred_consumer_policy
unsupported_by_release
```

`intentionally_omitted` means the public integration boundary deliberately does
not widen private/native state. It does not mean the data was casually ignored.

## ScoreForm crosswalk

| Semantic | Disposition | Vitrine surface / decision |
| --- | --- | --- |
| Core work identity | preserved directly | `CorePublicationSourceReference` |
| Assignment identity/title snapshot | preserved directly | `AcademicWorkRegistrationSnapshot`; bounded display |
| Student identity | relationship/provenance | explicit projected + subject assertion |
| Every exact attempt | bounded metadata | each attempt remains separately projectable |
| Attempt number | bounded metadata | never selection authority |
| Native attempt provenance | preserved directly | `ProducerSourceReference` |
| Attempt origin/time | bounded metadata | no latest/best inference |
| Points earned/possible | bounded metadata | not Vitrine Grade |
| Question identity/order | bounded metadata | producer order preserved |
| Question standard alignment | bounded metadata | alignment is not a standards rating |
| Response state | bounded metadata | `selected != blank != ambiguous` |
| Selected-answer presence | bounded metadata | does not expose/infer answer key |
| Native correctness evidence | bounded metadata | not proficiency |
| Manifest source snapshots | preserved directly | Core + producer provenance |
| Bounded lineage | preserved directly | no private storage traversal |
| `retained_source_path` | intentionally omitted as access | provenance is not an Artifact API |
| Attempt selection | deferred consumer policy | no latest/highest/best/official rule in adapter |
| Grade/proficiency | deferred consumer policy | no Grade/mastery calculation |
| Answer-key inference | intentionally omitted | not permitted from response evidence |

Key invariants:

```text
attempt 1 != attempt 2
blank != ambiguous != selected
question alignment != producer-created standards rating
response correctness != proficiency
highest score != portfolio-worthy attempt
latest attempt != selected attempt
```

ScoreForm exposes no consumer-neutral artifact resolver. Vitrine must not turn
`retained_source_path` into one.

## Quillan crosswalk

| Semantic | Disposition | Vitrine surface / decision |
| --- | --- | --- |
| Work/assignment identity | preserved directly | Core + registration provenance |
| Represented student | relationship/provenance | explicit subject relationship |
| Assignment/submission/review snapshots | preserved directly/bounded | producer lineage + display |
| Review-unit identity/order | bounded metadata | native order retained |
| Observations | bounded metadata | no semantic reinterpretation |
| Applicability/evidence states | bounded metadata | states stay distinct |
| Overall native ratings | bounded metadata | native scale |
| Standard-specific ratings | bounded metadata | native scale |
| Rating scale identity/ordinal | bounded metadata | minimum rating is not missing |
| Standard feedback | bounded metadata | student-facing producer text |
| `PublishedText` state | bounded metadata | `absent != withheld != included` |
| Selected PDS2 evidence | bounded metadata/artifact ref | selection is not widened |
| Review/source revision lineage | preserved directly | exact producer lineage |
| Student-feedback relationships | relationship/provenance | explicit |
| Artifact provenance/bytes | authorized artifact only | Quillan API -> authorized immutable bytes |
| `plain_paper_manual` digital work | unsupported by release | absence stays absence |
| Private teacher notes/hidden text | intentionally omitted | producer-private |
| Unselected/duplicate/excluded evidence | intentionally omitted | not widened by Vitrine |
| Rating normalization | deferred consumer policy | native ordinals remain native |

Quillan's authorization-gated artifact resolver owns historical source
verification and native I/O. Vitrine receives only bounded approved bytes.

## Concord crosswalk

| Semantic | Disposition | Vitrine surface / decision |
| --- | --- | --- |
| Activity/work identity | preserved directly | exact Core Activity + producer provenance |
| Activity scoring orientation | bounded metadata | native |
| Standards profile / ordered Focus Standards | bounded metadata | native order |
| Criterion Set identity/revision | bounded metadata/provenance | exact |
| Criterion identity | bounded metadata | exact |
| Standard-backed vs local Criterion | bounded metadata | distinction retained |
| Scoring Scale revision | bounded metadata | exact |
| Ordered Scale levels | bounded metadata | native order |
| Type-sensitive Scale values | bounded metadata | types must not collapse |
| Score identity | bounded metadata/provenance | every represented revision |
| Score target | relationship/provenance | individual vs Group explicit |
| Score disposition | bounded metadata | non-score has no synthetic zero |
| Score value | bounded metadata | native value |
| Scoring basis/scorer/time | bounded metadata | native |
| Current/superseded Score state | bounded metadata | no best/latest selection |
| Score Evidence Link | bounded metadata/artifact ref | exact represented evidence |
| External evidence ownership/reference | bounded metadata | no access widening |
| Moderation semantics | bounded metadata | native identity/status/permitted-use |
| Standards-result relationships | relationship/provenance | not Vitrine proficiency |
| Group identity | relationship/provenance | Group remains Group |
| Artifact / page identity | authorized artifact only | Concord represented-evidence API |
| Author relationship | relationship/provenance | Author != Subject by inference |
| Subject relationship | relationship/provenance | explicit |
| Contribution relationship | relationship/provenance | not inferred from membership |
| Recorder relationship | relationship/provenance | distinct from Author/Subject |
| `returned_artifact_pdf` | authorized artifact only | producer-approved immutable bytes |
| Producer-private paths/selectors | intentionally omitted | public API does not expose them |
| Grade/proficiency | deferred consumer policy | no Grade/mastery/portfolio-quality inference |

Required Vitrine relationship vocabulary already includes:

```text
artifact_author
artifact_subject
group_member
documented_contributor
recorder
represented_group
individual_score_target
group_score_target
```

Therefore Vitrine does not need to collapse Concord's Group, Author, Subject,
contribution, recorder, or Score-target distinctions to fit its schema.

Concord Scale values remain type-sensitive:

```text
1 != 1.0 != "1" != true
```

No adapter normalization may erase that distinction.

## Schema sufficiency matrix

| Surface | Decision | Reason |
| --- | --- | --- |
| `CorePublicationSourceReference` | sufficient | exact publication/work/source/capability/manifest/registration/lifecycle identity |
| `AcademicWorkRegistrationSnapshot` | sufficient | exact producer contract/title/work/lifecycle/source records |
| `ProducerSourceReference` | sufficient | native revision/lifecycle/disposition/lineage + reader/projection identity |
| `SourceArtifactReference` | sufficient | bounded artifact identity with optional locator and optional digest/size |
| `SourcePrivacyMetadata` | sufficient | privacy classification and review requirements |
| `ProjectedProducerRelationship` | sufficient | explicit source relationship identity/authority/provenance |
| `PortfolioSubjectRelationshipAssertion` | sufficient | persistent explicit subject relationships |
| `CandidateSourceEndpoint` | sufficient | exact source/provenance/privacy persistence |
| `ProjectionDisplaySnapshot` | sufficient | bounded transient producer-native display fields |
| copied-source Snapshot plan | **extended** | path locator is not required when producer owns artifact acquisition |
| Snapshot source provider | **extended** | `authorized_source_bytes_v1` carries producer-approved immutable bytes |

No additional persistent Vitrine wire shape is required by this audit.

## Snapshot authorized-byte consequence

For an authorized-byte provider:

```text
Core/Vitrine build authority
-> exact Snapshot provider selection
-> producer-owned authorization/artifact API
-> immutable producer-approved bytes + bounded metadata
-> Vitrine verifies identity/media/digest/size
-> Vitrine writes exact bytes to its own staging custody
```

Vitrine does not reconstruct or open a producer-native path.

For the existing filesystem provider:

```text
approved root + exact relative locator
-> Vitrine containment/link/reparse checks
-> read
-> digest/size verification
-> stage
-> provider stability confirmation
-> reread/re-hash
```

That behavior remains backward compatible.

## Deferred decisions

The following are intentionally **not** decided by #57:

- live installed reader discovery/invocation and dependency failure isolation (#58);
- ScoreForm projection implementation and any explicit attempt-selection UI/policy (#59);
- Quillan projection plus concrete artifact provider implementation (#60);
- Concord projection plus concrete artifact provider implementation (#61);
- user-facing unsupported/incompatible diagnostics and recovery (#62).

Those issues inherit this crosswalk; they must not reopen producer ownership or
silently weaken the frozen distinctions above.
