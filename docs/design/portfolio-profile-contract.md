# Versioned Portfolio Profile Contract

- **Issue:** #5, “Define portfolio profiles and versioned requirements”
- **Design date:** 2026-08-04
- **Status:** Foundation design paired with proposed ADR 0003; not a final serialized schema or runtime implementation
- **Applies to:** `pds-vitrine` v0.1.0 foundation work

## 1. Purpose

This document defines the conceptual Portfolio Profile model Vitrine will use to describe purpose-specific and versioned Portfolio requirements.

It defines:

- Profile families, Profile series, and immutable Profile revisions;
- Profile lifecycle events;
- exact Portfolio-to-Profile bindings;
- purpose and applicability;
- jurisdiction, program, institution, cohort, and authority metadata;
- authoritative source references;
- stable requirement identity;
- required, optional, conditional, and prohibited obligations;
- bounded three-valued condition evaluation;
- section and document requirements;
- selection and reflection policy;
- audience and approval requirements;
- retention-policy references;
- flattened composition and local overlays;
- requirement findings and completeness boundaries;
- explicit migration;
- historical preservation;
- failure states;
- and downstream constraints for later Vitrine contracts.

The paired architectural decision is [ADR 0003: Versioned Portfolio Profiles](../decisions/0003-versioned-portfolio-profiles.md). It remains **Proposed** until maintainers explicitly accept it.

## 2. Governing boundary

A Portfolio Profile is Vitrine-owned policy. It describes what a Portfolio is for and which requirements apply.

It does not perform the actions it requires.

```text
Profile says a section is required
  != section exists
  != eligible candidate exists
  != actor selected an item
  != item may be disclosed
  != Portfolio is approved
  != snapshot was issued
  != external authority accepted it
```

```text
Profile requirement appears satisfied
  != actor is authorized
  != human review occurred
  != institutional approval exists
  != legal compliance is certified
  != external outcome is favorable
```

Vitrine may store, version, bind, and evaluate approved Profile inputs. It must not invent institutional policy, external authority, consent, signatures, retention classification, or regulated acceptance.

## 3. Scope and non-goals

This document is conceptual. It does not define:

- final JSON Schema;
- Python classes;
- filesystem writers;
- a Profile editor;
- activation commands;
- transaction or locking mechanics;
- candidate or source-reference records;
- producer readers;
- producer artifact exposure;
- selection, annotation, reflection, or approval records;
- privacy authorization or recipient verification;
- snapshot bytes, checksums, or exports;
- records disposition execution;
- external submission integration;
- an operational New Jersey Graduation Portfolio Appeal Profile;
- legal advice;
- or compliance certification.

Later issues will define those contracts. This design constrains them.

## 4. Cross-repository review baseline

The following repository state was reviewed on 2026-08-04. Commit links are immutable review anchors.

| Repository | Reviewed state | Authoritative material | Reusable pattern | Incompatible assumption | Unresolved dependency |
| --- | --- | --- | --- | --- | --- |
| `pds-vitrine` | [`c1768a5`](https://github.com/Paper-Data-Suite/pds-vitrine/commit/c1768a5f54ae4ef2a66e5a9c7d66b98de75c8280); documentation-only foundation | Portfolio research, compliance research, module boundaries, identity design, proposed ADRs 0001-0002 | Purpose-specific Profiles, explicit authority, immutable historical identity | Research examples and proposed ADRs are not operational policy | Exact schemas, actor authorization, and runtime remain future work |
| `pds-core` | [`6c50721`](https://github.com/Paper-Data-Suite/pds-core/commit/6c507213618b68a6dd3ea096e1a898201ff029e6); released v0.6.0 | Standards contract, publication records, compatibility Profiles, registry integration | Stable series identity, immutable revisions, explicit supersession/withdrawal, exact references, no greatest-revision inference | Core Standards Profiles and producer compatibility Profiles are not Portfolio Profiles | Vitrine owns its Profile namespace; no Core change is required |
| `pds-meridian` | [`e6be420`](https://github.com/Paper-Data-Suite/pds-meridian/commit/e6be420c1ad650fa801cd16867fa18a30cb1050c); architecture-only | ADR 0001 policy-driven proficiency and Grade calculation | Explicit versioned policy before evidence contributes to derived output; unresolved states remain nonzero and nonfinal | Grading policy is not portfolio policy | No runtime grading-policy contract is consumed by this issue |
| `pds-concord` | [`e86e520`](https://github.com/Paper-Data-Suite/pds-concord/commit/e86e52002b0d6ffe0ff0fa65adca3d019a6b5721); package baseline and accepted ADRs | Separate Authors/Subjects, Criteria/Scales, source preservation, review/scoring separation | Durable identities, typed relationships, historical preservation | Group Membership or a Score target cannot be inferred from Profile eligibility | Candidate projections and consumer readers remain later work |
| `pds-portia` | [`8cd4b1f`](https://github.com/Paper-Data-Suite/pds-portia/commit/8cd4b1f2ca80cc240693184c87e5df463ba375cf); schemas and accepted architecture | Shared reference/relationship contracts and privacy boundaries | Explicit policy, append-preserving correction, minimum-necessary context | A generic Profile flag cannot make intervention records ordinary candidates | Portia publication and privacy-safe consumer projection remain unavailable |
| `pds-scoreform` | [`1045975`](https://github.com/Paper-Data-Suite/pds-scoreform/commit/10459751476f6d48d3c3a908a26d76732f00e340); manifest v1 and revision policy | Academic Result Manifest v1 and publication revision policy | Every attempt preserved; consumer policy selects use; revisions are explicit | A Profile cannot declare “latest” or “best” as producer truth | Candidate and selection contracts remain later Vitrine work |
| `pds-quillan` | [`05fecf2`](https://github.com/Paper-Data-Suite/pds-quillan/commit/05fecf23d29e56b45cba58ed97906f5353290033); executable prior Core line | Data contracts, submission/review/feedback boundaries | Private versus student-facing projections; exact class/work/student context | Profile policy cannot expose private notes or reinterpret review state | Core 0.6 publication and consumer-neutral reader remain future work |

### 4.1 Existing Profile concepts are distinct

Core currently uses “profile” for at least two separate concepts:

- a shared Standards Profile grouping standard definitions; and
- a Publication Producer Profile describing compatible contracts and capabilities.

Meridian proposes versioned grading policies.

Vitrine Portfolio Profiles are separate because they own:

- portfolio purpose;
- applicability;
- sections;
- document and selection requirements;
- audience variants;
- reflection;
- approvals;
- retention references;
- and output expectations.

No existing Core or Meridian Profile may be aliased as a Vitrine Portfolio Profile.

## 5. Terms

### 5.1 Portfolio Profile Family

A **Portfolio Profile Family** is a durable, non-rule-bearing grouping for related Profile series.

It may group several simultaneously valid pathways, content-area variants, or local implementations. It does not contribute inherited requirements and does not identify a current revision.

### 5.2 Portfolio Profile series

A **Portfolio Profile series** is one independently versioned logical policy identified by a stable `portfolio_profile_id`.

### 5.3 Portfolio Profile Revision

A **Portfolio Profile Revision** is one immutable complete rule set identified by:

```text
portfolio_profile_id + profile_revision
```

### 5.4 Profile lifecycle event

A **Profile lifecycle event** records activation, deprecation, supersession, withdrawal, or retirement without rewriting the Profile revision.

### 5.5 Portfolio Profile Binding

A **Portfolio Profile Binding** is a durable relationship connecting one Portfolio to one exact Profile revision.

### 5.6 Requirement

A **Requirement** is one stable policy statement within a Profile series. It identifies obligation, scope, condition, cardinality, and expected satisfaction type.

### 5.7 Requirement finding

A **Requirement finding** is a later evaluation result for one exact requirement against one Portfolio state.

The finding is derived from policy plus evidence. It is not the requirement itself.

### 5.8 Audience rule

An **Audience rule** describes an intended recipient class and the reviews, restrictions, and output treatment required for that class. It is not an authorization grant.

### 5.9 Effective Profile

An **Effective Profile** is a complete immutable Profile revision, including one produced by flattening exact component revisions and local overlays.

## 6. Conceptual graph

```text
Portfolio Profile Family
  -> Portfolio Profile series [0..*]
      -> Portfolio Profile Revision [1..*]
          -> Authority Source References [0..*]
          -> Requirements [0..*]
          -> Sections [0..*]
          -> Audience Rules [1..*]
          -> Approval Stages [0..*]
          -> Retention Rules [0..*]
          -> Lifecycle Events [1..*]

Portfolio
  -> Portfolio Profile Binding
      -> exact Portfolio Profile Revision
```

Composition adds:

```text
Component Profile Revisions [1..*]
  + Local Overlay Inputs [0..*]
  -> flattened Effective Profile Revision
```

No edge in this graph grants source access, disclosure authority, or external approval.

## 7. Governing principles

### 7.1 Purpose-specific policy

Portfolio purpose must be explicit. Requirements must not be inferred from the generic word “portfolio.”

### 7.2 Immutable activated meaning

Once activated, Profile content does not change. Corrections create successor revisions and lifecycle events.

### 7.3 Exact historical binding

Every operational Portfolio and issued snapshot identifies the exact Profile revision used.

### 7.4 No hidden authority

A Profile records policy supplied by an attributable authority. Vitrine does not invent the authority.

### 7.5 Unknown is preserved

Unavailable or restricted facts remain unknown or unresolved. They do not default to false, not applicable, or satisfied.

### 7.6 Stable requirement identity

Requirement IDs provide continuity across revisions. Material semantic changes require new IDs or explicit replacement relationships.

### 7.7 No dynamic inheritance

Activated meaning is self-contained. Mutable parents cannot change child behavior.

### 7.8 Completeness is advisory

Derived completeness supports review. It is not approval, compliance certification, or external acceptance.

## 8. Portfolio Profile Family conceptual contract

### 8.1 Decision

Profile Family is a separate durable Vitrine concept because several independently versioned series may belong to one program while remaining simultaneously valid.

The Family carries organizational metadata only.

### 8.2 Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `profile_family_id` | Required | Stable opaque or safe identifier within the Vitrine workspace |
| `record_type` | Required | Distinguishes the Family record |
| `contract_version` | Required | Serialized contract version, not policy revision |
| `display_name` | Required | Human-readable label; not durable identity |
| `description` | Optional | Non-rule-bearing summary |
| `jurisdiction_hint` | Optional | Organizational hint only; authority belongs to revisions |
| `program_hint` | Optional | Organizational hint only |
| `created_at` | Required | Aware timestamp |
| `created_by` | Required | Attributable actor or authority reference |
| `retired_at` | Optional | Organizational retirement metadata |

### 8.3 Forbidden Family behavior

A Family must not contain:

- sections;
- requirements;
- default audience grants;
- approvals;
- retention rules;
- conditions;
- or a mutable current Profile pointer that becomes authority.

### 8.4 Invariants

- Family ID is stable and never reused.
- Family membership does not imply revision order.
- Removing a series from a current index does not erase historical membership.
- Family retirement does not invalidate historical Profile revisions.

## 9. Portfolio Profile series conceptual contract

### 9.1 Purpose

The Profile series supplies stable logical policy identity across revisions.

### 9.2 Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `portfolio_profile_id` | Required | Stable series identity |
| `profile_family_id` | Optional | Organizational Family reference |
| `purpose_kind` | Required | Controlled purpose classification |
| `program_id` | Optional | Stable program identity supplied by governing authority |
| `variant_id` | Optional | Stable pathway or simultaneous variant identity |
| `content_area` | Optional | Content-area scope where relevant |
| `owning_authority` | Required | Authority responsible for the policy series |
| `created_at` | Required | Creation timestamp |
| `created_by` | Required | Attributable creator |

### 9.3 Series identity rules

A series should represent one coherent combination of:

- purpose;
- program;
- pathway or variant;
- and controlling authority.

A change that creates a simultaneous alternative generally creates a new series. A temporal correction to the same logical policy creates a new revision.

## 10. Portfolio Profile Revision conceptual contract

### 10.1 Ownership and authority

Vitrine owns the immutable record. The rule content remains attributable to the identified policy authorities and sources.

### 10.2 Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `record_type` | Required | Profile-revision record discriminator |
| `contract_version` | Required | Contract/schema version |
| `portfolio_profile_id` | Required | Stable series ID |
| `profile_revision` | Required | Positive immutable logical revision |
| `predecessor_revision` | Conditional | Exact direct predecessor for successor revisions |
| `purpose` | Required | Purpose definition |
| `applicability` | Required | Context and temporal scope |
| `authority_sources` | Required | Ordered or keyed exact source references; may be empty only for explicitly local instructional Profiles |
| `sections` | Required | Ordered section definitions; may be empty when justified |
| `requirements` | Required | Stable requirement definitions |
| `audience_rules` | Required | At least one named audience rule |
| `approval_stages` | Required | Explicit list, possibly empty |
| `retention_rules` | Required | Explicit list, possibly empty or unresolved |
| `component_revisions` | Required | Exact immutable composition inputs; empty for standalone Profiles |
| `known_limitations` | Required | Explicit unresolved or incomplete authority statements |
| `authored_at` | Required | Authoring timestamp |
| `authored_by` | Required | Attributable author or authority |
| `content_digest` | Future required | Digest of canonical serialized content once final serialization exists |

### 10.3 Forbidden fields or implications

A Profile revision must not contain:

- student-specific selections;
- source credentials;
- signatures;
- real consent documents;
- candidate search results;
- producer-private data;
- snapshot bytes;
- a mutable current flag used as sole authority;
- executable condition code;
- or an external approval result.

### 10.4 Revision invariants

- Revision is positive and unique within the series.
- Logical revision identity is never reused with different content.
- Activated content is immutable.
- Direct predecessor is explicit when applicable.
- Revision gaps are valid and consumed.
- Series head is not inferred from the largest number.
- Contract version and policy revision remain distinct.

## 11. Profile lifecycle event conceptual contract

| Field | Requirement | Meaning |
| --- | --- | --- |
| `profile_lifecycle_event_id` | Required | Opaque unique event ID |
| `portfolio_profile_id` | Required | Series reference |
| `profile_revision` | Required | Exact revision reference |
| `event_kind` | Required | `activated`, `deprecated`, `superseded`, `withdrawn`, or `retired` |
| `event_at` | Required | Recorded event time |
| `effective_at` | Required | Time the event governs operational use |
| `actor` | Required | Attributable actor or authority |
| `reason` | Required | Nonempty rationale |
| `successor_revision` | Conditional | Required for direct supersession when a successor exists |
| `authority_source_ref` | Optional | Supporting source or approval reference |

### 11.1 Lifecycle semantics

- `activated`: revision may be selected for new bindings when applicability and authorization permit.
- `deprecated`: revision remains usable for existing bindings but is not preferred for new bindings.
- `superseded`: an explicit successor exists; migration remains deliberate.
- `withdrawn`: revision cannot receive new operational bindings.
- `retired`: series or program has ended; historical resolution remains available.

Lifecycle events do not erase Profile content or bindings.

## 12. Draft and activation boundary

A mutable authoring draft may support review, but it has no operational authority.

Suggested conceptual authoring states are:

```text
draft
under_review
approved_for_activation
```

Activation produces or designates immutable revision content plus an activation event.

The draft itself should not be referenced by a Portfolio Profile Binding.

A research-only or restricted-source-incomplete Profile may be structurally valid but must remain non-operational.

## 13. Portfolio Profile Binding conceptual contract

### 13.1 Cardinality

```text
one Portfolio -> exactly one active Profile binding
one Profile revision -> zero or many Portfolios
```

### 13.2 Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `portfolio_profile_binding_id` | Required | Opaque stable binding ID |
| `portfolio_id` | Required | Exact Portfolio reference |
| `portfolio_profile_id` | Required | Exact Profile series |
| `profile_revision` | Required | Exact immutable revision |
| `audience_rule_id` | Optional | Default working-output target; does not authorize issuance |
| `bound_at` | Required | Binding timestamp |
| `bound_by` | Required | Attributable actor |
| `binding_basis` | Required | Rationale, program authority, or workflow basis |
| `status` | Required | `active`, `superseded`, `invalidated`, or justified equivalent |
| `predecessor_binding_id` | Conditional | Required for migration or correction |
| `migration_record_ref` | Optional | Explicit impact analysis reference |

### 13.3 Binding invariants

- Binding references an activated and applicable exact Profile revision.
- One Portfolio has at most one active binding.
- Endpoints are immutable after operational use.
- Profile migration creates a successor binding.
- Invalid binding correction preserves the original binding.
- Issued snapshots continue to reference their original binding.

## 14. Purpose definition

### 14.1 Initial controlled purpose kinds

```text
improvement
showcase
parent_guardian_conference
regulated
```

A purpose definition should include:

| Field | Requirement | Meaning |
| --- | --- | --- |
| `purpose_kind` | Required | Controlled classification |
| `display_name` | Required | Human-readable local label |
| `statement` | Required | Why the Portfolio exists |
| `intended_outcomes` | Required | Ordered statements; descriptive, not external decisions |
| `workflow_boundaries` | Required | Explicit non-goals and authority limits |
| `extensions` | Optional | Namespaced purpose metadata |

Purpose kind never expands into hidden rules. Every required rule must be present in the exact revision.

## 15. Applicability contract

A Profile revision must state where and when it may be selected.

| Field | Requirement | Meaning |
| --- | --- | --- |
| `jurisdiction` | Optional | Structured region or authority scope |
| `institution_scope` | Optional | Institution, district, school, or program scope |
| `program_id` | Optional | Program identity |
| `program_version` | Optional | External or local program version |
| `school_years` | Optional | Explicit school-year set or range |
| `cohorts` | Optional | Explicit cohort identifiers |
| `grade_bands` | Optional | Applicable grade bands |
| `courses_or_programs` | Optional | Course/program constraints |
| `content_areas` | Optional | Applicable content-area scope |
| `variant_id` | Optional | Pathway or simultaneous variant |
| `effective_from` | Required | Earliest applicable date |
| `effective_through` | Optional | Latest applicable date |
| `eligibility_input_refs` | Optional | Named facts required for applicability evaluation |
| `applicability_status` | Required | `complete`, `incomplete`, or `requires_human_verification` |

### 15.1 Temporal distinctions

The following are not interchangeable:

- authored date;
- activation date;
- effective date;
- school year;
- graduating cohort;
- Portfolio binding date;
- snapshot issuance date;
- source access date.

A new school year or cohort never inherits the prior Profile automatically.

## 16. Jurisdiction, program, and authority metadata

Requirements should retain authority level.

Initial authority-level vocabulary should support:

```text
law_or_regulation
public_government_guidance
restricted_operational_artifact
institutional_policy
local_implementation_rule
teacher_instructional_policy
research_template
```

A source’s authority level does not prove that Vitrine interpreted it correctly. Human and institutional review remain required where the Profile says so.

## 17. Authority Source Reference conceptual contract

| Field | Requirement | Meaning |
| --- | --- | --- |
| `authority_source_id` | Required | Stable source reference ID within the Profile revision |
| `title` | Required | Source title |
| `issuing_authority` | Required | Organization or policy owner |
| `authority_level` | Required | Controlled authority layer |
| `source_version` | Optional | Version, publication date, update marker, or citation |
| `effective_from` | Optional | Source effective date |
| `effective_through` | Optional | Source end date |
| `accessed_at` | Required | Review/access time |
| `access_status` | Required | `public`, `restricted_reviewed`, `restricted_unreviewed`, `unavailable`, or equivalent |
| `uri_or_external_ref` | Optional | Reviewable external reference |
| `copied_digest` | Optional | Digest if exact source bytes are retained lawfully |
| `supports_requirement_ids` | Required | Exact requirements supported by this source |
| `notes` | Optional | Bounded interpretation and known limitations |

### 17.1 Restricted-source rule

A controlling restricted source that has not been reviewed must make affected requirements unresolved and may make the Profile non-operational.

Vitrine must not invent restricted portal fields, attestation language, deadlines, or validation rules.

## 18. Requirement conceptual contract

### 18.1 Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `requirement_id` | Required | Stable requirement identity within the series |
| `requirement_kind` | Required | Section, document, selection, reflection, approval, audience, retention, eligibility, output, or namespaced extension |
| `obligation` | Required | `required`, `optional`, `conditional`, or `prohibited` |
| `title` | Required | Human-readable label |
| `statement` | Required | Complete policy statement |
| `scope` | Required | Portfolio, section, audience, output, content area, actor role, or record class |
| `condition` | Conditional | Required for `conditional` obligation |
| `cardinality` | Optional | Minimum, maximum, or exact counts |
| `satisfaction_rule` | Required | Abstract expected evidence/finding type |
| `authority_source_ids` | Required | Supporting authority references; may be empty for explicit local instructional policy |
| `replaces_requirement_id` | Optional | Explicit semantic replacement |
| `extensions` | Optional | Namespaced constrained metadata |

### 18.2 Stable identity rules

A requirement ID may remain stable across revisions when:

- the policy meaning remains equivalent;
- only labels or clarifying nonsemantic text change;
- or thresholds and scope remain unchanged.

A new ID is required when:

- obligation changes materially;
- scope changes materially;
- cardinality changes policy meaning;
- condition changes eligibility;
- satisfaction evidence changes class;
- or controlling authority changes the substantive rule.

A successor may explicitly replace the old requirement ID.

## 19. Obligation semantics

### 19.1 Required

The requirement applies and must receive a satisfactory finding before the relevant Profile gate can pass.

### 19.2 Optional

The item may be present but its absence does not create a missing finding.

Optional does not imply automatically authorized or audience-safe.

### 19.3 Conditional

Applicability is determined by a bounded condition with `true`, `false`, or `unknown` result.

- `true`: evaluate as required unless the rule explicitly defines another obligation.
- `false`: record not applicable for this evaluation context.
- `unknown`: record unresolved; do not collapse to false or not applicable.

### 19.4 Prohibited

Presence creates a prohibited-present or policy-violation finding for the relevant scope.

Prohibited does not authorize deletion of upstream source records.

## 20. Bounded condition model

### 20.1 Allowed structure

Conditions may use a bounded tree:

```text
all(condition...)
any(condition...)
not(condition)
predicate(name, operator, expected_value)
requirement_finding(requirement_id, expected_state)
human_verification(input_id, expected_state)
```

The final contract may choose a smaller exact set.

### 20.2 Permitted predicate inputs

Predicates may reference explicitly named Profile context such as:

- selected audience rule;
- Profile variant;
- content area;
- cohort;
- grade band;
- output kind;
- named eligibility fact;
- external finding state;
- human verification state;
- or another acyclic requirement finding.

### 20.3 Prohibited condition behavior

Conditions must not:

- run arbitrary Python, JavaScript, shell, SQL, or templates;
- read files directly;
- call external services implicitly;
- inspect producer-private data;
- infer identity;
- calculate a Grade;
- or select an official attempt.

### 20.4 Three-valued logic

Conditions use explicit three-valued logic.

For `all`:

- any false -> false;
- otherwise any unknown -> unknown;
- otherwise true.

For `any`:

- any true -> true;
- otherwise any unknown -> unknown;
- otherwise false.

For `not`:

- true -> false;
- false -> true;
- unknown -> unknown.

### 20.5 Cycle detection

Requirement-to-requirement condition dependencies must form an acyclic graph.

Self-reference and multi-node cycles are invalid Profile content.

## 21. Requirement scope and cardinality

### 21.1 Scope

A requirement may apply to:

- the whole Portfolio;
- one section;
- one audience rule;
- one output type;
- one content area;
- one variant;
- one actor role;
- one approval stage;
- or one retention record class.

Scope references must resolve exactly within the Profile revision.

### 21.2 Cardinality

Supported conceptual cardinality includes:

```text
minimum
maximum
exactly
one_per_section
one_per_selected_item
one_per_content_area
unbounded
```

Counts are Profile data and never universal Vitrine rules.

## 22. Section Definition conceptual contract

| Field | Requirement | Meaning |
| --- | --- | --- |
| `section_id` | Required | Stable section identity within the Profile series |
| `title` | Required | Display title |
| `description` | Required | Section purpose |
| `order` | Required | Deterministic relative order |
| `obligation` | Required | Required, optional, conditional, or prohibited |
| `condition` | Conditional | Conditional applicability |
| `minimum_selections` | Optional | Minimum count |
| `maximum_selections` | Optional | Maximum count |
| `parent_section_id` | Optional | Hierarchy reference when supported |
| `selection_rule_ids` | Required | Applicable abstract selection rules |
| `reflection_rule_ids` | Required | Applicable reflection rules |
| `approval_stage_ids` | Required | Applicable review/approval stages |
| `audience_rule_ids` | Required | Audience variants in which the section may appear |
| `presentation_notes` | Optional | Accessibility or display guidance |

### 22.1 Section identity

A label correction alone may preserve `section_id`. A material change in purpose or requirement meaning should create a new ID or explicit replacement.

The Profile defines the section. Actual section instances and selected items belong to later working-Portfolio contracts.

## 23. Document Requirement conceptual contract

| Field | Requirement | Meaning |
| --- | --- | --- |
| `document_requirement_id` | Required | Stable rule identity or embedded requirement ID |
| `document_class` | Required | Vitrine-authored, student-authored, producer source, producer export, institution record, external record, acknowledgment, consent reference, attestation reference, generated output, receipt, outcome, or namespaced extension |
| `obligation` | Required | Required, optional, conditional, or prohibited |
| `cardinality` | Optional | Count requirements |
| `section_id` | Optional | Section placement requirement |
| `custody_treatment` | Required | Local working, local retained, snapshot included, submission included, reference only, generated, or external outcome |
| `representation_modes` | Required | Allowed reference, copy, render, summary, link, or omission modes |
| `format_constraints` | Optional | Media type, extension, structured-data, print, or accessibility constraint |
| `audience_rule_ids` | Required | Audience treatment |
| `condition` | Conditional | Applicability condition |
| `authority_source_ids` | Required | Supporting sources |

### 23.1 Custody separation

The following are independent:

```text
required to exist locally
required to be retained locally
included in a Vitrine snapshot
included in external submission
referenced but not copied
generated by Vitrine
received from an external authority
```

A locally retained record is not automatically transmitted.

## 24. Selection Rule conceptual contract

A Selection Rule describes policy that later selection records must satisfy.

| Field | Requirement | Meaning |
| --- | --- | --- |
| `selection_rule_id` | Required | Stable rule ID |
| `actor_roles` | Required | Roles permitted or required to propose/select/reject/replace/order |
| `student_selection_mode` | Required | Required, optional, shared, or prohibited |
| `teacher_confirmation_required` | Required | Whether teacher confirmation is required |
| `rationale_required` | Required | Whether actor rationale is required |
| `minimum_count` | Optional | Minimum selected items |
| `maximum_count` | Optional | Maximum selected items |
| `required_portfolio_roles` | Optional | Baseline, intermediate, current, exemplar, context, or namespaced roles |
| `required_source_relationships` | Optional | Explicit author, contributor, subject, participant, or other relationship classes |
| `allowed_representation_modes` | Required | Reference, copy, render, summary, or other allowed modes |
| `replacement_policy` | Required | Whether replacement preserves prior selections and requires reason |
| `condition` | Optional | Applicability condition |

### 24.1 Selection authority boundaries

A Selection Rule does not:

- authenticate an actor;
- grant source access;
- make a Core publication eligible by itself;
- choose a ScoreForm official attempt;
- reinterpret Quillan review state;
- establish Concord authorship or proficiency;
- or opt Portia content into ordinary discovery.

### 24.2 Producer-neutrality

Profile constraints may refer to reviewed shared classes such as producer module, publication kind, artifact class, media class, subject relationship, or sensitivity class.

The final candidate fields and producer-specific exposure decisions belong to issues #6 and #7.

## 25. Reflection Rule conceptual contract

| Field | Requirement | Meaning |
| --- | --- | --- |
| `reflection_rule_id` | Required | Stable rule ID |
| `obligation` | Required | Required, optional, conditional, or prohibited |
| `author_roles` | Required | Roles allowed or required to author |
| `scope_kind` | Required | Whole Portfolio, section, item, item comparison, checkpoint, conference preparation, or final review |
| `prompt_id` | Required | Stable prompt identity |
| `prompt_version` | Required | Exact prompt revision |
| `prompt_text` | Optional | Exact text or external prompt reference |
| `minimum_count` | Optional | Minimum reflections |
| `maximum_count` | Optional | Maximum reflections |
| `related_selection_count` | Optional | Required selected-item relationship |
| `format_constraints` | Optional | Text, audio, video, language, accessibility, or length expectations |
| `review_required` | Required | Whether a later review record is required |
| `condition` | Optional | Applicability condition |

A reflection is actor-authored interpretation. Its existence does not establish growth, proficiency, approval, or producer truth.

Actual reflection records and replacement history belong to issue #8.

## 26. Audience Rule conceptual contract

### 26.1 Initial audience classes

```text
student
teacher_internal
parent_guardian
institutional_reviewer
external_reviewer
regulated_submission
public
```

The final contract may add namespaced classes.

### 26.2 Conceptual fields

| Field | Requirement | Meaning |
| --- | --- | --- |
| `audience_rule_id` | Required | Stable audience-rule ID |
| `audience_class` | Required | Controlled intended recipient class |
| `purpose` | Required | Why this edition exists |
| `allowed_output_kinds` | Required | Working view, checkpoint, packet, snapshot, submission, or namespaced kind |
| `required_approval_stage_ids` | Required | Required reviews and approvals |
| `privacy_review_required` | Required | Policy requirement only |
| `rights_review_required` | Required | Policy requirement only |
| `accessibility_requirements` | Required | Expected accessible variants or checks |
| `translation_requirements` | Optional | Required language/translation treatment |
| `prohibited_document_classes` | Required | Content classes excluded from this audience |
| `redistribution_constraints` | Optional | Policy statement; not technical enforcement by itself |
| `expiration_policy` | Optional | Audience-access policy reference |

### 26.3 Nonauthorization rule

Audience selection does not verify:

- recipient identity;
- parent/guardian relationship;
- eligible-student rights holder;
- legitimate educational interest;
- consent;
- source access;
- or lawful disclosure.

Those controls belong to issue #10 and institutional systems.

## 27. Approval Stage conceptual contract

| Field | Requirement | Meaning |
| --- | --- | --- |
| `approval_stage_id` | Required | Stable stage ID |
| `title` | Required | Human-readable stage label |
| `stage_kind` | Required | Review, acknowledgment, consent reference, attestation reference, signature reference, rights review, privacy review, accessibility review, records review, institutional approval, or namespaced extension |
| `required_actor_roles` | Required | Required role classes |
| `sequence` | Optional | Deterministic order when sequential |
| `quorum` | Optional | Required number or rule |
| `separation_of_duties` | Optional | Roles that must be distinct |
| `scope` | Required | Portfolio, section, item, audience edition, snapshot request, or submission package |
| `reapproval_triggers` | Required | Events invalidating or requiring new approval |
| `condition` | Optional | Applicability condition |

### 27.1 Approval boundaries

The Profile defines the stage. It does not create an approval, signature, consent, or attestation.

Approval for one scope does not transfer automatically to another.

```text
internal review
  != public issue approval
```

```text
working Portfolio approved
  != exact snapshot approved
```

## 28. Retention Rule conceptual contract

| Field | Requirement | Meaning |
| --- | --- | --- |
| `retention_rule_id` | Required | Stable rule ID |
| `record_class` | Required | Exact Vitrine-owned or referenced record class |
| `schedule_id` | Optional | Authoritative schedule or policy ID |
| `schedule_version` | Optional | Exact schedule version |
| `policy_owner` | Required | Institution or records authority |
| `classification_status` | Required | Confirmed, provisional, unresolved, or not applicable |
| `retention_trigger` | Optional | Event starting minimum retention |
| `minimum_duration` | Optional | Duration or permanent/indefinite marker |
| `hold_behavior` | Required | Legal/audit hold treatment |
| `disposition_approval_required` | Required | Whether separate approval is required |
| `archive_or_transfer_expectation` | Optional | Future handoff policy |
| `authority_source_ids` | Required | Supporting sources |

### 28.1 Retention limits

A Retention Rule must not:

- delete Core or producer records;
- classify every Portfolio object automatically;
- bypass legal hold;
- infer permission to destroy at the minimum date;
- or make Vitrine the records officer.

Profile definitions, bindings, working state, issued snapshots, external submissions, receipts, outcomes, and logs may require different record classes and rules.

## 29. Composition and local overlays

### 29.1 No live inheritance

An activated revision never resolves rules dynamically from a mutable parent or current pointer.

### 29.2 Component reference

A component reference must identify:

- exact Profile series and revision;
- expected digest once serialization exists;
- component role;
- source authority;
- and composition order only where order is semantically meaningful.

### 29.3 Local overlay

A local overlay is an attributable, versioned input containing additions or explicit replacements within the actor’s authority.

It must not silently weaken a controlling external requirement.

### 29.4 Flattening algorithm boundary

The conceptual process is:

```text
resolve exact components
  -> verify lifecycle and applicability
  -> validate stable IDs
  -> compare requirements, sections, audience rules, approvals, and retention
  -> identify conflicts
  -> require explicit conflict disposition
  -> produce one self-contained effective revision
  -> preserve component references and composition provenance
  -> activate explicitly
```

### 29.5 Conflict examples

Conflicts include:

- one component requires a section another prohibits;
- incompatible exact counts;
- one audience rule permits a document class another prohibits;
- a local overlay removes a controlling approval;
- duplicate IDs with different semantic meaning;
- or overlapping effective scopes with contradictory conditions.

Silent last-write-wins behavior is prohibited.

## 30. Requirement finding boundary

### 30.1 Conceptual finding states

Later contracts should support at least:

```text
satisfied
missing
not_applicable
prohibited_present
unresolved
unauthorized
unavailable
invalid
requires_human_verification
```

### 30.2 Finding provenance

Every finding must eventually preserve:

- exact Portfolio Profile Binding;
- Profile series and revision;
- requirement ID;
- Portfolio state or checkpoint;
- evaluation time;
- evaluation mode;
- evaluator or service version;
- evidence or source references;
- condition result;
- and reason.

### 30.3 Completeness

A completeness summary is derived from findings.

A Profile may define gates such as:

- all required machine-checkable requirements satisfied;
- no prohibited-present finding;
- no unresolved controlling requirement;
- required human approvals present.

The summary remains distinct from authorization, issuance, submission, external acceptance, and legal compliance.

## 31. Revision allocation and replay

The later Profile service should follow these conceptual rules:

- initial revision is explicit;
- successor revision is allocated under one series;
- predecessor is explicit;
- exact replay of identical revision content may return existing state;
- contradictory reuse of the same logical revision fails;
- revision gaps remain consumed;
- interrupted writes are reconciled from canonical state;
- and no mutable `latest` file is authoritative.

## 32. Supersession, deprecation, withdrawal, and retirement

### 32.1 Deprecation

A deprecated revision is discouraged for new bindings but may remain operational for existing Portfolios under policy.

### 32.2 Supersession

A superseded revision has an explicit successor. Existing Portfolios do not migrate automatically.

### 32.3 Withdrawal

A withdrawn revision cannot receive new operational bindings. Historical resolution remains available.

### 32.4 Retirement

Retirement indicates the program or series is no longer active. It does not erase records.

## 33. Profile migration

### 33.1 Migration input

Migration requires:

- current active binding;
- target exact Profile revision;
- target lifecycle and applicability validation;
- actor and authority;
- and a deterministic requirement comparison.

### 33.2 Requirement comparison

Classify requirements as:

```text
unchanged
added
removed
replaced
materially_changed
unresolved_mapping
```

Stable IDs support `unchanged`. Explicit replacement metadata supports `replaced`.

### 33.3 Migration effects

Migration must preserve existing:

- selections;
- reflections;
- annotations;
- approvals;
- findings;
- and issued snapshots.

It must not assume those records satisfy the target Profile.

New findings and reapproval may be required.

### 33.4 Migration output

Migration creates:

- impact analysis;
- successor Profile binding;
- supersession of the prior active binding;
- unresolved findings where needed;
- and an attributable migration record.

### 33.5 Migration blockers

Migration may be blocked when:

- applicability does not match;
- target source authority is unverified;
- restricted controlling material is unavailable;
- composition conflicts remain unresolved;
- or actor authority is insufficient.

## 34. Purpose-family validation

### 34.1 Improvement

A valid generic model must support:

- baseline, intermediate, and current evidence roles;
- comparisons among exact items;
- student reflection;
- teacher review;
- mutable curation;
- optional checkpoints;
- and no automatic official-attempt or Grade selection.

### 34.2 Showcase

A valid generic model must support:

- curated sections;
- display metadata rules;
- limited and public audiences;
- rights/privacy review;
- collaborator treatment;
- accessible alternatives;
- reflection;
- and audience-specific approvals.

### 34.3 Parent/guardian conference

A valid generic model must support:

- representative evidence;
- student or teacher selection;
- plain-language context;
- family and internal variants;
- translation/accessibility;
- participant acknowledgment;
- dated output;
- and separate follow-up records.

### 34.4 Generic regulated

A valid generic model must support:

- jurisdiction;
- program;
- cohort;
- content area;
- pathway;
- eligibility inputs;
- local-only evidence;
- externally submitted documents;
- approvals and attestations;
- deadlines;
- retention references;
- correction/resubmission;
- and external outcomes.

The generic model must not embed New Jersey-specific operational values.

## 35. Producer and sibling boundaries

### 35.1 Core

A Profile may use Core identifiers and references but does not modify Core canonical records or reinterpret publication compatibility as portfolio eligibility.

### 35.2 ScoreForm

A Profile may require deliberate selection among attempts. It must not declare the greatest attempt number, latest timestamp, or highest score as the official attempt unless an authoritative consumer policy or human decision supplies that meaning.

### 35.3 Quillan

A Profile may later permit a student-facing feedback export or another reviewed projection. It must not make private notes, internal review data, or direct workspace crawling eligible.

### 35.4 Concord

A Profile permitting group artifacts must require explicit relationship treatment. Portfolio Subject identity or Group Membership alone does not establish authorship, contribution, Score target, or proficiency.

### 35.5 Portia

Portia remains prohibited from ordinary Profile eligibility by default.

A later regulated or specialized Profile cannot use a broad boolean opt-in. It must identify a reviewed minimum-necessary projection, purpose, audience, authorization, sensitivity, and approval requirements under issues #7 and #10.

### 35.6 Meridian

Portfolio Profile requirements do not select grading evidence, calculate proficiency, create Grade-item membership, or replace Meridian policy.

## 36. Privacy, security, and integrity

- Profile IDs contain no student PII.
- Profile examples use synthetic organizations and records.
- Profile content contains no credentials or secret portal data.
- Restricted authority sources are referenced conservatively.
- Conditions cannot execute arbitrary code.
- Profiles cannot expose sensitive source presence through discovery.
- Audience rules do not grant access.
- Approval stages do not fabricate signatures.
- Retention rules do not execute deletion.
- Lifecycle and migration history are append-preserved.
- Error language must not claim external rejection, legal noncompliance, graduation failure, or institutional approval.

## 37. Failure-state vocabulary

The design preserves at least these distinct states:

```text
profile_not_found
profile_revision_not_found
profile_revision_conflict
profile_inactive
profile_not_effective
profile_deprecated
profile_superseded
profile_withdrawn
profile_incomplete
profile_authority_unverified
profile_context_mismatch
profile_variant_required
profile_composition_conflict
profile_source_unavailable
profile_source_version_unknown
profile_binding_conflict
profile_migration_required
profile_migration_blocked
profile_migration_unreviewed
requirement_not_found
duplicate_requirement_id
requirement_condition_unknown
requirement_condition_cycle
requirement_scope_invalid
audience_rule_not_found
audience_authorization_unresolved
approval_requirement_unsatisfied
retention_policy_unresolved
restricted_requirement_unverified
```

A final contract may refine names but must not collapse materially different conditions.

## 38. Edge-case behavior

### 38.1 Profile changes during curation

The existing binding remains exact. A new revision does not apply automatically. Migration requires explicit impact review.

### 38.2 Profile changes after issuance

The issued snapshot remains bound to the original revision. Reissue creates a new snapshot.

### 38.3 Simultaneous pathways

Use separate Profile series or explicit variants. Do not represent alternatives as chronological revisions unless one supersedes the other.

### 38.4 Audience changes from internal to public

Select the public audience rule, reevaluate prohibited content, rights, redaction, accessibility, and approval. Internal approval does not transfer automatically.

### 38.5 Conditional input unavailable

Return `unknown` and unresolved. Do not mark not applicable.

### 38.6 Restricted source unavailable

Mark controlling requirements unverified and the Profile incomplete or non-operational. Do not invent fields.

### 38.7 Overlay conflicts with controlling authority

Fail composition or require explicit authorized conflict disposition. Do not silently weaken the external rule.

### 38.8 Profile withdrawn

Reject new bindings. Preserve historical bindings, findings, and snapshots.

### 38.9 Retention schedule changes

Create a new Profile revision or separately versioned authoritative policy reference as the final contract determines. Preserve prior policy context.

### 38.10 Portia source class added broadly

Reject the broad rule. Require a specific reviewed projection and later authorization controls.

### 38.11 Concord group artifact permitted

Require explicit relationship policy and audience treatment. Do not infer individual ownership or proficiency.

### 38.12 “Latest ScoreForm attempt” requested

Reject ambiguous semantics. Require a deliberate actor or explicit consumer-owned selection rule.

### 38.13 Dynamic parent changes

The activated effective Profile remains unchanged. New composition creates a new revision.

### 38.14 Completeness without approval

Report complete machine-checkable requirements and missing approval stage separately. Do not call the Portfolio approved.

## 39. Validation invariants

1. Profile Family IDs are stable and never reused.
2. Profile Family carries no operative inherited rules.
3. Profile series IDs are stable and non-revisioned.
4. Profile revision identity is series plus positive revision.
5. Activated revisions are immutable.
6. Logical revision reuse with different content is invalid.
7. Current authority is not inferred from ordering.
8. Simultaneous variants are not revisions by default.
9. One Portfolio has at most one active Profile binding.
10. Binding references an exact activated revision.
11. Binding endpoints are immutable after operational use.
12. Migration creates a successor binding.
13. Issued snapshots retain their original binding.
14. Requirement IDs are unique within a revision.
15. Requirement continuity across revisions is explicit.
16. Required, optional, conditional, and prohibited are distinct.
17. Conditional evaluation supports unknown.
18. Condition dependencies are acyclic.
19. Conditions execute no arbitrary code.
20. Scope references resolve exactly.
21. Section IDs are unique and ordered deterministically.
22. Document custody and submission treatment are separate.
23. Selection rules do not grant source access.
24. Reflection rules do not create reflection records.
25. Audience rules do not authorize recipients.
26. Approval stages do not fabricate approvals.
27. Retention rules do not execute disposition.
28. Composition uses exact immutable components.
29. Composition conflicts cannot use last-write-wins.
30. Effective Profiles are self-contained.
31. Completeness remains derived and nonauthoritative.
32. Portia remains excluded by default.
33. Concord group eligibility does not imply individual ownership.
34. Profiles do not calculate Grades or proficiency.
35. Regulated examples remain generic until issue #11.

## 40. Downstream issue boundaries

### Issue #6

Defines exact candidate and source-reference records used to evaluate source eligibility.

### Issue #7

Defines producer-specific artifact and summary exposure.

### Issue #8

Defines actual selections, ordering, annotations, reflections, approvals, and replacement history.

### Issue #9

Defines snapshot bytes, exact Profile references, checksums, omissions, and immutable issuance.

### Issue #10

Defines authorization, recipient resolution, redaction, disclosure, consent, and audience enforcement.

### Issue #11

Defines regulated compliance Profile instances and the researched New Jersey Profile family.

## 41. Unresolved implementation questions

The final serialized contract must decide:

- exact safe-ID prefixes or namespaces;
- canonical JSON shape and serialization;
- digest calculation;
- canonical workspace paths;
- draft storage and activation transaction mechanics;
- lifecycle-event conflict handling;
- exact actor-reference contract;
- exact condition predicate vocabulary;
- whether retention policy references are embedded or separate versioned records;
- whether requirement findings are stored or fully derived;
- and whether Profile composition is performed by an authoring tool or a runtime service.

These questions do not alter the architectural decisions in this design.

## 42. References

- [Portfolio purposes and workflows](../research/portfolio-purpose-workflows.md)
- [Compliance and policy constraints](../research/compliance-constraints.md)
- [New Jersey Graduation Portfolio Appeal research](../research/new-jersey-graduation-portfolio-appeal.md)
- [Module boundaries and authority](../architecture/module-boundaries.md)
- [Portfolio Subject identity and cross-class linking](portfolio-subject-identity.md)
- [ADR 0003](../decisions/0003-versioned-portfolio-profiles.md)
- [Representative Portfolio Profile examples](../examples/portfolio-profile-examples.md)
