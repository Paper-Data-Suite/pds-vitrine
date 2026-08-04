# Vitrine Module Boundaries and Authority

- **Issue:** #3, “Define module boundaries and ownership”
- **Architecture date:** 2026-08-04
- **Status:** Foundation architecture paired with proposed ADR 0001
- **Applies to:** `pds-vitrine` v0.1.0 foundation work

## 1. Purpose

This document defines Vitrine's architectural role, ownership boundaries, authority hierarchy, permitted dependency directions, and required behavior at the boundaries with other Paper Data Suite modules and external systems.

Vitrine is a separate portfolio domain module. It is responsible for deliberate portfolio curation and purpose-specific portfolio issuance. It is not a shared registry, producer, gradebook, intervention case manager, archive orchestrator, identity authority, regulatory submission portal, or external decision-maker.

The paired Architecture Decision Record is [ADR 0001: Vitrine Module Boundaries and Authority](../decisions/0001-vitrine-module-boundaries-and-authority.md). The ADR is **Proposed** until explicitly accepted by the maintainers. This document provides the fuller system context, matrices, edge cases, and downstream design implications that support that decision.

## 2. Governing separation of concerns

The foundation research established the following non-equivalences:

```text
source is discoverable
  != actor may access source
  != source is eligible for this portfolio
  != source is selected
  != selected representation may be copied
  != copied representation may be disclosed
  != portfolio satisfies a profile
  != institution approved issuance or submission
  != package was transmitted externally
  != external authority accepted or approved it
```

Every later Vitrine contract and workflow must preserve those distinctions.

The central authority rule is:

> The originating system remains authoritative for source facts and lifecycle; Vitrine is authoritative only for its own portfolio decisions and the exact historical content of its issued portfolio editions.

## 3. Scope and non-goals

This architecture establishes ownership and dependency rules. It does not yet define:

- final JSON schemas or Python classes;
- persistence paths or transaction mechanics;
- the Portfolio or Portfolio Subject contract;
- cross-class identity-link records;
- portfolio profile schemas;
- candidate and source-reference schemas;
- producer artifact projections;
- selection, annotation, or reflection schemas;
- snapshot package formats;
- authorization or redaction engines;
- New Jersey compliance-profile rules;
- producer adapters;
- Core discovery implementation;
- Meridian, Sunset, or external-system integrations;
- a user interface;
- or production release behavior.

Those details remain assigned to later v0.1.0 issues. This document constrains them.

## 4. Terms used in this architecture

### 4.1 Canonical record

A **canonical record** is the authoritative persisted record for a concept within its owning module or external system. A Vitrine operation must not create a second competing canonical record for a source-owned concept.

Examples include:

- a Core Publication Record;
- a ScoreForm attempt;
- a Quillan review record;
- a Concord Artifact Author association;
- a Portia Event or Support Process record;
- a Meridian report snapshot;
- an institutional consent record;
- and an external outcome letter.

### 4.2 Derived record

A **derived record** is reproducible or replaceable output calculated or indexed from canonical records. Its loss or rebuild must not change canonical meaning.

Examples include:

- Core's disposable SQLite publication catalog;
- a Vitrine candidate search index;
- a Vitrine requirement summary;
- a preview thumbnail;
- or a current-view cache.

A derived record cannot authorize an operation or override canonical state by itself.

### 4.3 Source reference

A **source reference** identifies an exact upstream record, publication, revision, artifact, or external object without making Vitrine its owner.

A source reference may include Vitrine-owned metadata about:

- why the source was considered;
- how it relates to the portfolio subject;
- what representation was requested;
- and what availability or authorization finding applied.

Those Vitrine facts do not alter the source record.

### 4.4 Copied representation

A **copied representation** is a byte-exact copy or explicitly rendered derivative placed under Vitrine custody for a portfolio purpose when copying is authorized.

A copied representation must retain:

- exact source identity;
- source revision or publication identity;
- source and copied-byte digests;
- renderer identity and version when rendered;
- copy or render time;
- omission, transformation, and accessibility information;
- and the policy or authorization basis for copying.

The copied representation does not become the canonical producer record.

### 4.5 Working portfolio

A **working portfolio** is mutable Vitrine state. It may contain candidate findings, selections, rejected items, ordering, annotations, reflections, reviews, approvals, and pending snapshot requests.

### 4.6 Issued snapshot

An **issued snapshot** is an immutable, purpose- and audience-specific historical edition. It is authoritative for the exact content Vitrine issued at the recorded time. It is not authoritative for the current state of upstream sources.

### 4.7 External submission and outcome

An **external submission** is a package or data transmission made through an authorized external process. An **external outcome** is the response or decision produced by the receiving authority.

Vitrine may prepare a package and record transmission or outcome evidence. It must not claim that preparation equals transmission or that local validation equals external approval.

## 5. System context

The intended context is:

```text
                         institutional identity / policy
                                      |
                                      v
producer modules -> Core publication infrastructure -> Vitrine curation
      |                         |                   |
      |                         |                   v
      |                         |             issued snapshots
      |                         |                   |
      v                         v                   v
producer-native facts     canonical discovery   external delivery/submission
      |                                             |
      v                                             v
Meridian grading/reporting                     external receipt/outcome

future Sunset / institutional records systems may archive or dispose of
records only through separately authorized handoff and records-management rules.
```

The diagram is conceptual. It does not require one centralized service or networked deployment.

## 6. Cross-repository review baseline

The following repository state was reviewed on 2026-08-04. Commit links are immutable review anchors rather than claims that the repositories will remain unchanged.

| Repository | Reviewed state | Authority or status used by this architecture | Vitrine consequence |
| --- | --- | --- | --- |
| `pds-vitrine` | [`3098c62`](https://github.com/Paper-Data-Suite/pds-vitrine/commit/3098c620ba05da6e2748eecd806981f71306823e) | Foundation research in `docs/research/` | Research inputs are not final schemas, but their separation-of-concerns findings govern this work. |
| `pds-core` | [`6c50721`](https://github.com/Paper-Data-Suite/pds-core/commit/6c507213618b68a6dd3ea096e1a898201ff029e6), v0.6.0 | Shared Academic Work Registration, Publication Records, manifest binding, compatibility, catalog, audit, and recovery | Vitrine discovers and verifies through Core but must use producer contracts for semantics and separate authorization. |
| `pds-scoreform` | [`1045975`](https://github.com/Paper-Data-Suite/pds-scoreform/commit/10459751476f6d48d3c3a908a26d76732f00e340) | Academic Result Manifest v1 and producer revision policy are defined; full Core 0.6 publication workflow is still milestone work | Vitrine may plan for the public manifest/reader boundary but cannot assume every runtime reader or publication command already exists. |
| `pds-quillan` | [`05fecf2`](https://github.com/Paper-Data-Suite/pds-quillan/commit/05fecf23d29e56b45cba58ed97906f5353290033), v0.8.9 | Executable Quillan owns submissions, review, ratings, feedback, and assignment-local reports; Core 0.6 publication integration remains future work | Vitrine must not crawl private Quillan records; it must await or use a reviewed public producer projection. |
| `pds-concord` | [`e86e520`](https://github.com/Paper-Data-Suite/pds-concord/commit/e86e52002b0d6ffe0ff0fa65adca3d019a6b5721), `0.2.0.dev0` | Installable package baseline on Core 0.6; fifteen accepted ADRs and conceptual contracts govern semantics; runtime domain workflows remain future work | Vitrine must preserve Concord authorship, subject, group, contribution, score, and publication distinctions even before all runtime readers exist. |
| `pds-portia` | [`8cd4b1f`](https://github.com/Paper-Data-Suite/pds-portia/commit/8cd4b1f2ca80cc240693184c87e5df463ba375cf) | Architecture and versioned schemas for behavior-support records and cross-module references; no executable application or production intervention publication | Portia is deny-by-default for portfolios and cannot be treated as ordinary academic evidence. |
| `pds-meridian` | [`e6be420`](https://github.com/Paper-Data-Suite/pds-meridian/commit/e6be420c1ad650fa801cd16867fa18a30cb1050c) | Architecture-only grading and reporting boundary | Vitrine must not implement grading logic or use Meridian as an artifact manager. |
| `pds-sunset` | No repository or public contract found in the Paper Data Suite organization on 2026-08-04 | Only sibling documentation's stated future responsibility for suite-wide archival orchestration is available | This document defines a provisional handoff boundary and does not invent a Sunset API. |

### 6.1 Reviewed authoritative documents

#### Core

- [PDS Core README at the reviewed commit](https://github.com/Paper-Data-Suite/pds-core/blob/6c507213618b68a6dd3ea096e1a898201ff029e6/README.md)
- [Academic registry integration guide](https://github.com/Paper-Data-Suite/pds-core/blob/6c507213618b68a6dd3ea096e1a898201ff029e6/docs/academic_registry_integration.md)
- [Academic registry recovery guide](https://github.com/Paper-Data-Suite/pds-core/blob/6c507213618b68a6dd3ea096e1a898201ff029e6/docs/academic_registry_recovery.md)

#### ScoreForm

- [ScoreForm README at the reviewed commit](https://github.com/Paper-Data-Suite/pds-scoreform/blob/10459751476f6d48d3c3a908a26d76732f00e340/README.md)
- [Academic Result Manifest v1](https://github.com/Paper-Data-Suite/pds-scoreform/blob/10459751476f6d48d3c3a908a26d76732f00e340/docs/academic_result_manifest_v1.md)
- [Publication revision policy](https://github.com/Paper-Data-Suite/pds-scoreform/blob/10459751476f6d48d3c3a908a26d76732f00e340/docs/publication_revision_policy.md)

#### Quillan

- [Quillan README at the reviewed commit](https://github.com/Paper-Data-Suite/pds-quillan/blob/05fecf23d29e56b45cba58ed97906f5353290033/README.md)
- [Data contracts](https://github.com/Paper-Data-Suite/pds-quillan/blob/05fecf23d29e56b45cba58ed97906f5353290033/docs/data_contracts.md)
- [Workspace lifecycle](https://github.com/Paper-Data-Suite/pds-quillan/blob/05fecf23d29e56b45cba58ed97906f5353290033/docs/workspace_lifecycle.md)

#### Concord

- [Concord documentation index at the reviewed commit](https://github.com/Paper-Data-Suite/pds-concord/blob/e86e52002b0d6ffe0ff0fa65adca3d019a6b5721/docs/README.md)
- [ADR 0001: Concord Module Boundaries](https://github.com/Paper-Data-Suite/pds-concord/blob/e86e52002b0d6ffe0ff0fa65adca3d019a6b5721/docs/decisions/0001-concord-module-boundaries.md)
- [ADR 0005: Separate Artifact Authors and Subjects](https://github.com/Paper-Data-Suite/pds-concord/blob/e86e52002b0d6ffe0ff0fa65adca3d019a6b5721/docs/decisions/0005-separate-artifact-authors-and-subjects.md)
- [ADR 0007: Preserve Source Evidence and History](https://github.com/Paper-Data-Suite/pds-concord/blob/e86e52002b0d6ffe0ff0fa65adca3d019a6b5721/docs/decisions/0007-preserve-source-evidence-and-history.md)
- [ADR 0008: Separate Review, Moderation, Scoring, Grading, and Reporting](https://github.com/Paper-Data-Suite/pds-concord/blob/e86e52002b0d6ffe0ff0fa65adca3d019a6b5721/docs/decisions/0008-separate-review-moderation-scoring-grading-and-reporting.md)
- [ADR 0015: Publish Versioned Concord Academic Result Manifests Through the Core Registry](https://github.com/Paper-Data-Suite/pds-concord/blob/e86e52002b0d6ffe0ff0fa65adca3d019a6b5721/docs/decisions/0015-publish-versioned-concord-academic-result-manifests-through-the-core-registry.md)

#### Portia

- [Portia README at the reviewed commit](https://github.com/Paper-Data-Suite/pds-portia/blob/8cd4b1f2ca80cc240693184c87e5df463ba375cf/README.md)

#### Meridian

- [Meridian README at the reviewed commit](https://github.com/Paper-Data-Suite/pds-meridian/blob/e6be420c1ad650fa801cd16867fa18a30cb1050c/README.md)
- [ADR 0001: Policy-Driven Standards Proficiency and Grade Calculation](https://github.com/Paper-Data-Suite/pds-meridian/blob/e6be420c1ad650fa801cd16867fa18a30cb1050c/docs/decisions/0001-policy-driven-standards-proficiency-and-grade-calculation.md)
- [ADR 0002: Provenance-Bound Report Snapshots and Subscriptions](https://github.com/Paper-Data-Suite/pds-meridian/blob/e6be420c1ad650fa801cd16867fa18a30cb1050c/docs/decisions/0002-provenance-bound-report-snapshots-and-subscriptions.md)

### 6.2 Cross-repository integration review

| Module/system | Implementation status at review | Concepts owned outside Vitrine | Public contract Vitrine expects | Prohibited direct access or mutation | Unresolved integration dependency |
| --- | --- | --- | --- | --- | --- |
| Core | Released v0.6.0 shared infrastructure | Registration, publication, withdrawal, manifest binding, compatibility, canonical audit, derived catalog | Core v0.6 public APIs for canonical reload, path containment, digest verification, compatibility, and bounded queries | No catalog authority, canonical mutation, producer parsing, or portfolio workflow fields in Core | Authorization remains deployment/policy work rather than Core publication behavior |
| ScoreForm | Executable v0.9.1; Academic Result Manifest v1 and revision policy implemented; full Core 0.6 integration incomplete | Assignments, attempts, responses, points, response states, alignment, provenance, manifest revisions | Consumer-neutral Academic Result Manifest v1 reader planned under the ScoreForm v0.10.0 milestone | No direct `results.csv` or private workspace parsing; no attempt mutation or official-attempt selection | Publication, producer profile, and consumer reader issues must complete before production Vitrine ingestion |
| Quillan | Executable v0.8.9 on Core 0.5 line; publication milestone planned | Assignments, submissions, evidence, review, ratings, feedback, private notes, review state, exports | Planned privacy-safe academic-result manifest and consumer-neutral artifact reader | No direct private `review.json` parsing for portfolio access; no review mutation or private-note exposure | Core 0.6 migration, publication, and public reader remain future Quillan work |
| Concord | Installable `0.2.0.dev0` package baseline on Core 0.6; domain runtime incomplete | Activities, Groups, Artifacts, Authors, Subjects, contribution, Review, Moderation, Scores, result manifests | Accepted Concord manifest architecture plus planned consumer-neutral manifest/artifact reader | No inferred individual ownership, filesystem crawling, or mutation of Concord relationships and Scores | Persistence, publication producer, artifact reader, and end-to-end runtime remain future v0.2.0 work |
| Portia | Architecture and schema validation only; no executable app or production publication | Behavior-support Events, Support Processes, determinations, interventions, follow-ups, outcomes, privacy classifications | Future intervention publication plus explicit privacy-safe minimum-necessary projection | No ordinary candidate discovery, existence leakage, private schema parsing, or case mutation | Support Process contracts, Core 0.6 intervention publication, authorization, and projection are not yet complete |
| Meridian | Architecture-only | Grading evidence, proficiency, Grade items, Academic Period aggregation, overrides, formal reports | Future public immutable report-snapshot/output reader | No grading calculation, policy mutation, report rewriting, or artifact management through Meridian | Runtime package, policies, producer adapters, and report contracts remain future work |
| Sunset | No repository or public contract found | Intended future suite-wide archival orchestration and disposition coordination | Future archive-handoff descriptor and custody-status contract | No invented API, upstream deletion, retention execution, or snapshot rewriting | Repository ownership, contract shape, custody, legal hold, and disposition semantics are unresolved |
| External institutional systems | Deployment-specific and outside this repository | Identity, role, consent, signature, official submission, receipt, outcome, records authority | Explicit adapter or durable external reference with authoritative evidence | No vendor payload embedded as universal domain model; no fabricated external state | Authentication, policy integration, supported vendors, and human-out-of-band transmission evidence remain deployment decisions |

## 7. Vitrine's architectural role

Vitrine owns the portfolio domain.

Its purpose is to:

1. establish a portfolio purpose and profile;
2. bind the portfolio to explicitly resolved subjects and authorized actors;
3. discover potentially relevant source publications through Core;
4. verify canonical publication identity, manifest binding, withdrawal, and compatibility;
5. resolve source meaning through producer-owned public contracts;
6. apply separate authorization and portfolio-eligibility decisions;
7. record deliberate curation, interpretation, reflection, review, and approval;
8. create purpose- and audience-specific copied or rendered representations;
9. issue immutable portfolio snapshots;
10. record external transmission, receipt, correction, and outcome references when authorized;
11. preserve portfolio history and provenance; and
12. participate in a future archival handoff without becoming the suite-wide disposition authority.

## 8. Concepts owned by Vitrine

At the architectural level, Vitrine owns the following concept families. Later issues will define exact schemas and cardinalities.

### 8.1 Portfolio-purpose aggregates

Vitrine owns:

- the working portfolio aggregate;
- portfolio-purpose identity;
- portfolio profile references;
- portfolio-subject associations;
- portfolio actor and role associations;
- current portfolio lifecycle state;
- and links among earlier, successor, corrected, or superseded portfolios.

The source systems remain authoritative for any upstream person, class, work, or artifact identity referenced by those records.

### 8.2 Candidate evaluation

Vitrine owns portfolio-specific findings about whether an authorized source may be considered under a selected profile.

Examples include:

- candidate permitted;
- candidate prohibited by profile;
- source unavailable;
- source withdrawn;
- producer unsupported;
- manifest digest mismatch;
- subject relationship unresolved;
- authorization denied;
- rights review required;
- or sensitive-source opt-in required.

Candidate findings do not alter source state.

### 8.3 Curation decisions

Vitrine owns:

- selection and rejection;
- section placement;
- ordering;
- display title and caption;
- rationale;
- annotation;
- reflection;
- portfolio-specific relationship statements;
- replacement history;
- and portfolio review or approval records.

A Vitrine statement such as “selected as baseline evidence” is a portfolio interpretation, not a producer fact.

### 8.4 Portfolio requirements and findings

Vitrine owns evaluation of versioned portfolio-profile requirements and the resulting findings, such as present, missing, prohibited, unknown, or requires human review.

Vitrine does not own the external authority that created the requirement and does not transform a local finding into legal or regulatory approval.

### 8.5 Snapshot and issuance records

Vitrine owns:

- snapshot requests;
- generated indexes;
- copied representations;
- rendered derivatives;
- snapshot manifests;
- copied-byte and generated-file checksums;
- audience and purpose metadata;
- omission and redaction findings;
- issuance events;
- correction, withdrawal, and supersession relationships among Vitrine editions;
- and exact historical records of what Vitrine issued.

### 8.6 External-event references

Vitrine may own records that state:

- a package was prepared;
- local approval was recorded;
- an authorized actor reported transmission;
- an external receipt was imported or referenced;
- correction was requested;
- a new package superseded a prior submission;
- or an external outcome was recorded.

The referenced external receipt or outcome remains authoritative only when it originates from the responsible external system or actor.

### 8.7 Vitrine diagnostics and derived indexes

Vitrine may own rebuildable indexes, caches, previews, and diagnostics. These must never become the only source for portfolio history, authorization, source identity, or snapshot contents.

## 9. Concepts explicitly outside Vitrine

Vitrine does not own:

- canonical class rosters;
- institutional identity;
- parent or guardian identity;
- Core Academic Periods;
- Core Academic Work Registrations;
- Core Publication Records or withdrawals;
- producer manifests;
- producer-native records;
- source revision policy;
- source correction policy;
- source evidence or source artifact lifecycle;
- official assessment attempt selection;
- grading-evidence selection;
- standards-proficiency calculation;
- Grade-item membership;
- assignment, marking-period, or course Grade calculation;
- teacher overrides of Meridian-derived results;
- intervention case management;
- behavior determinations;
- suite-wide archive orchestration;
- legal-hold authority;
- institutional records classification;
- authorized destruction or disposition;
- official consent or signature systems;
- official regulatory submission portals;
- official submission receipts;
- graduation or diploma decisions;
- or authoritative external outcomes.

Vitrine may reference some of these concepts, but reference is not ownership.

## 10. Core boundary

### 10.1 Core authority

Core remains authoritative for shared suite infrastructure, including:

- identifier validation;
- module-qualified work identity;
- class- and school-year-qualified shared references;
- Academic Period calendars;
- Academic Work Registration;
- immutable Publication Records;
- publication series and explicit supersession;
- immutable withdrawal records;
- safe producer-manifest paths;
- exact SHA-256 manifest binding;
- publication capabilities;
- producer compatibility metadata;
- canonical registry audit;
- and the disposable discovery catalog.

### 10.2 Permitted Vitrine use of Core

Vitrine may use Core to:

1. query the disposable catalog for bounded discovery;
2. reload every selected canonical Publication Record;
3. load the exact referenced Academic Work Registration revision when applicable;
4. evaluate publication-series head and withdrawal state from canonical records;
5. resolve the exact producer work root and safe manifest path;
6. verify the manifest file is a non-symlink regular file within the correct work root;
7. compute and compare the exact SHA-256 digest;
8. evaluate producer-profile compatibility;
9. and obtain shared envelope metadata needed to choose a producer reader.

### 10.3 Prohibited Core interactions

Vitrine must not:

- treat a catalog row as canonical;
- write portfolio selections into Core registrations;
- write audience or approval decisions into Publication Records;
- mutate or replace Publication Records;
- mutate withdrawal records;
- alter recorded manifest paths or digests;
- repair Core canonical records from Vitrine;
- parse producer manifest bodies in Core;
- require Core to implement Vitrine profile logic;
- require Core to authorize portfolio access or disclosure;
- or add a new Core publication kind merely to represent a Vitrine portfolio.

### 10.4 Authority consequence

A valid, current, compatible Core publication proves only that Core can identify and verify a shared publication envelope. It does not prove:

- the actor may read it;
- the actor may read all source artifacts behind it;
- it is appropriate for the selected portfolio;
- the portfolio subject owns it;
- it may be copied;
- it may be disclosed;
- or it satisfies a portfolio requirement.

## 11. General producer boundary

Producer modules remain authoritative for their native records, domain vocabulary, revisions, corrections, source provenance, and public projection contracts.

### 11.1 Permitted producer interaction

Vitrine may:

- identify the producer from the verified Core publication;
- select a compatible public reader or Vitrine-owned adapter;
- request a documented public projection;
- receive exact producer-native identities and relationships;
- record portfolio-specific findings around that projection;
- and request authorized artifact representations exposed by the producer contract.

### 11.2 Prohibited producer interaction

Vitrine must not:

- import producer-private implementation modules as an architectural requirement;
- crawl arbitrary producer directories;
- parse undocumented JSON;
- infer record meaning from filenames;
- infer source state from modification time;
- invent missing relationships;
- flatten all producer records into one universal result object;
- change a producer record when a portfolio selection changes;
- or create a conflicting producer record inside Vitrine.

### 11.3 Adapter ownership

A Vitrine-owned adapter may translate a stable producer public contract into Vitrine's candidate model. The adapter may not redefine the producer's semantics.

An adapter must distinguish:

- source facts supplied by the producer;
- portfolio interpretation supplied by Vitrine;
- authorization decisions supplied by policy or deployment;
- and presentation decisions supplied by the selected profile.

## 12. ScoreForm boundary

### 12.1 ScoreForm authority

ScoreForm owns:

- managed selected-response assignment identity;
- answer-sheet issuance and page identity;
- native attempts;
- responses and response states;
- points earned and possible;
- question-level correctness;
- result origins;
- scan and manual-entry provenance;
- question-to-standard alignment;
- immutable academic-result manifest content;
- producer record-set revision allocation;
- append-preserved attempt history;
- producer supersession requirements;
- and producer withdrawal/republication policy.

### 12.2 Permitted Vitrine representations

Subject to the future public reader and authorization rules, Vitrine may represent:

- one or more exact attempts;
- an attempt comparison;
- selected, blank, or ambiguous response evidence;
- a points summary;
- question-level evidence;
- question-to-standard alignment;
- or a producer-approved rendered summary.

### 12.3 Mandatory limits

Vitrine must not:

- choose an official attempt;
- choose a Grade-bearing attempt;
- choose a “best” attempt as an upstream fact;
- treat latest attempt as official;
- rewrite an answer or score;
- collapse blank and ambiguous responses;
- expose answer keys through undocumented access;
- expose secure or restricted assessment content without authorization;
- convert alignment into standards proficiency;
- or convert points into a Grade.

A curator may select an attempt to illustrate growth. That selection is a portfolio decision only.

## 13. Quillan boundary

### 13.1 Quillan authority

Quillan owns:

- written-response assignment configuration;
- routed evidence and submission manifests;
- page and evidence state;
- teacher-entered minimum-requirement findings;
- review units;
- Focus Standard observations;
- overall Focus Standard ratings;
- feedback composition;
- private teacher notes;
- review lifecycle;
- student feedback exports;
- and assignment-local reports.

### 13.2 Permitted Vitrine representations

Subject to a reviewed public contract, Vitrine may represent:

- original student work;
- an exact submission or revision;
- a student-readable feedback export;
- selected observations or ratings included in the public projection;
- or a sequence showing writing development.

### 13.3 Mandatory limits

Vitrine must not:

- modify `assignment.json`, `submission.json`, or `review.json`;
- alter submission or review state;
- infer a rating that Quillan did not record;
- expose private teacher notes through a general portfolio reader;
- bypass a privacy-safe producer projection to obtain internal review details;
- treat a Vitrine annotation as a Quillan amendment;
- calculate a Grade from Quillan ratings;
- or make a Quillan export the only surviving source of teacher judgment.

Quillan remains responsible for distinguishing source evidence, teacher-review artifacts, and derived feedback/report exports. Vitrine must preserve that distinction.

## 14. Concord boundary

### 14.1 Concord authority

Concord owns:

- Activities and Sessions;
- Groups and Memberships;
- Roles and Responsibilities;
- Artifact Instances and Artifact Pages;
- Artifact Authors;
- Artifact Subjects;
- contribution and representation information;
- Review and Moderation;
- Criteria and Scoring Scales;
- Score Records;
- Score Evidence Links;
- non-score dispositions;
- and Concord Academic Result Manifests.

### 14.2 Relationships that must remain distinct

Vitrine must preserve the distinction among:

- route target;
- Artifact Author;
- Artifact Subject;
- Group Member;
- Role holder;
- contributor;
- physical recorder;
- represented Group;
- Score target;
- and portfolio subject.

No one relationship implies another.

### 14.3 Mandatory group-artifact invariants

1. Group Membership does not establish authorship of every group Artifact.
2. A group-level Artifact does not automatically become individually owned by each member.
3. A physical recorder is not automatically the sole Author.
4. An Artifact Subject is not automatically an Author.
5. An Artifact Author or Subject is not automatically a Score target.
6. Inclusion in an individual portfolio does not establish individual proficiency.
7. Current Group Membership must not rewrite historical authorship or contribution.
8. Vitrine must not duplicate one canonical group Artifact as several apparent individual source Artifacts.
9. Any relationship between an individual portfolio subject and a group Artifact must be explicit and typed.
10. A student-authored portfolio reflection about participation is not a producer-confirmed contribution record unless Concord or another authoritative source confirms it.

### 14.4 Permitted portfolio relationships

A future Vitrine selection may state that an Artifact is included because the portfolio subject is:

- a confirmed Author;
- a confirmed Subject;
- a confirmed contributor;
- a member of the represented Group;
- a presenter or editor under an authoritative relationship;
- or a participant who supplied a clearly labeled personal reflection.

The selection must preserve which of those relationships is authoritative and which is portfolio commentary.

## 15. Portia boundary

### 15.1 Portia authority

Portia owns behavior-support and intervention concepts, including:

- Events;
- Event Participants and Roles;
- Accounts and Observations;
- Positive Observations;
- Concerns and Referrals;
- Classifications and Hypotheses;
- Determinations;
- Responses;
- Supports and Interventions;
- Follow-Ups and Outcomes;
- communications;
- amendments and disagreement statements;
- Portia work relationships;
- and Portia-specific privacy classifications.

### 15.2 Default exclusion

Portia records are excluded from ordinary Vitrine candidate discovery and presentation by default.

This is stronger than merely hiding them from one interface. An unauthorized or ordinary portfolio workflow must not reveal Portia presence through:

- result counts;
- titles;
- timestamps;
- filenames;
- thumbnails;
- previews;
- search facets;
- source types;
- diagnostics;
- errors;
- or generated indexes.

### 15.3 Conditions for any future inclusion

A future profile may permit a minimum-necessary Portia-derived representation only when all of the following are satisfied:

1. the profile explicitly permits the Portia source class;
2. the portfolio purpose justifies the inclusion;
3. the actor is explicitly authorized;
4. the audience is explicitly authorized;
5. a deliberate opt-in action occurs;
6. the producer exposes an approved privacy-safe projection;
7. sensitive details are minimized or redacted;
8. the issued edition records the restricted classification;
9. the representation preserves Portia's contextual meaning;
10. and the selection does not reinterpret the record as academic evidence, a Grade, or a permanent student trait.

### 15.4 Mandatory limits

Vitrine must not:

- alter a Portia Event or Support Process;
- alter a determination, response, intervention, follow-up, or outcome;
- infer behavior patterns from portfolio presence;
- use a Portia record as standards evidence or a Grade component;
- automatically include Portia material because Core can discover an intervention publication;
- or require Portia to depend on Vitrine.

## 16. Meridian boundary

### 16.1 Meridian authority

Meridian owns:

- eligibility of evidence for grading;
- evidence-selection policy for grading;
- standards-proficiency calculation;
- Grade-item membership;
- reassessment and recency policy;
- conventional, standards-based, and hybrid Grade calculation;
- Academic Period aggregation;
- teacher overrides of derived results;
- formal report composition;
- provenance-bound report snapshots;
- and report subscriptions.

### 16.2 Mandatory distinction

```text
selected for a portfolio
  != selected as grading evidence
  != included in a Grade item
  != included in a Meridian report
```

### 16.3 Permitted Vitrine interaction

When Meridian later exposes a public output contract, Vitrine may include an authorized Meridian report or report snapshot as a source artifact.

Vitrine owns only:

- the decision to include that report in a portfolio;
- the portfolio display metadata;
- the copied representation if authorized;
- and the portfolio edition containing it.

### 16.4 Mandatory limits

Vitrine must not:

- calculate or recalculate proficiency;
- decide Grade-item membership;
- select evidence for grading;
- apply reassessment policy;
- calculate an assignment, period, or course Grade;
- change a Meridian override;
- rewrite a Meridian report;
- or silently refresh an issued Vitrine edition when Meridian recalculates.

Meridian must not become Vitrine's source-artifact store, curation engine, reflection system, or portfolio snapshot manager.

## 17. Sunset and records-management boundary

### 17.1 Current status

No `pds-sunset` repository or public contract was found on 2026-08-04. Several sibling documents describe Sunset as the future owner of suite-wide archival orchestration. This architecture treats that statement as an intended boundary, not an implemented dependency.

### 17.2 Vitrine lifecycle responsibility

Vitrine owns semantic portfolio lifecycle such as:

- working;
- checkpointed;
- issued;
- corrected;
- superseded;
- withdrawn from future audience access;
- or marked eligible for records review.

Vitrine may also store:

- record-classification metadata supplied by an authority;
- retention-profile references;
- legal-hold references;
- and a future archive handoff descriptor.

### 17.3 Sunset or institutional records authority

A future Sunset contract or institutional records system should own:

- suite-wide archive orchestration;
- cross-module package transfer;
- storage-tier movement;
- records-schedule execution;
- legal-hold coordination;
- disposition queues;
- institutionally authorized deletion;
- and archive/disposition reporting.

### 17.4 Mandatory limits

Vitrine must not:

- delete Core records;
- delete producer records;
- infer that “closed,” “superseded,” or “withdrawn” authorizes destruction;
- hard-code a universal retention period;
- destroy an issued snapshot solely because an upstream source was withdrawn;
- or move another module's canonical records into archival storage.

A future archive operation may change storage location or access state. It must not rewrite snapshot bytes, checksums, provenance, edition identity, or historical meaning.

## 18. External institutional systems

External systems are identified by authoritative function rather than vendor name.

### 18.1 Potential authoritative systems

Examples include:

- student-information systems;
- identity providers;
- staff directories;
- parent/guardian relationship systems;
- learning-management systems;
- consent and electronic-signature systems;
- institutional records repositories;
- secure delivery services;
- state submission portals;
- and government or institutional decision systems.

### 18.2 External authority may include

- official student identity;
- staff identity and role;
- enrollment;
- parent or guardian relationship;
- consent;
- institutional approval;
- official signature;
- records classification;
- legal hold;
- official transmission;
- receipt;
- accepted or rejected status;
- graduation determination;
- diploma status;
- and disposition approval.

### 18.3 Vitrine's permitted role

Vitrine may:

- store a durable external reference;
- prepare an export package;
- preserve the exact package bytes and digest;
- record local approval;
- record that an authorized actor reported or initiated transmission;
- ingest or reference an external receipt;
- ingest or reference an external outcome;
- and preserve correction or resubmission history.

### 18.4 Events that must remain separate

```text
package prepared by Vitrine
package approved locally
package transmitted externally
external system acknowledged receipt
external authority requested correction
corrected package transmitted
external authority accepted or rejected submission
external outcome recorded by Vitrine
```

No event implies the next.

### 18.5 Mandatory limits

Vitrine must not:

- impersonate an external portal;
- claim transmission from package generation alone;
- claim receipt without authoritative evidence;
- claim external acceptance from local validation;
- claim a graduation decision;
- fabricate a signature or attestation;
- or overwrite an external outcome with a Vitrine finding.

## 19. Human and policy authority

Vitrine records human decisions but does not manufacture authority.

A future actor record or action event must distinguish:

- actor identity;
- actor role;
- institution or deployment context;
- policy or profile granting authority;
- purpose;
- subject scope;
- action scope;
- effective time;
- and source/version of the authority.

An actor label such as `teacher`, `administrator`, or `coordinator` is not sufficient by itself.

Potential roles include:

- student curator;
- teacher;
- adviser;
- parent or guardian;
- privacy reviewer;
- rights reviewer;
- accessibility reviewer;
- school administrator;
- district coordinator;
- records officer;
- submitter;
- external reviewer;
- and external decision-maker.

Authentication and full authorization-engine design remain later work.

## 20. Authority matrix

| Concern | Authoritative owner | Vitrine may record or consume | Vitrine must not do |
| --- | --- | --- | --- |
| Shared module/class/work identity | Core | Validated references | Redefine or repair identity |
| Academic Work Registration | Core | Exact revision reference and lifecycle | Add portfolio membership fields or mutate registration |
| Publication identity, revision, digest, withdrawal | Core | Canonical publication envelope and verified manifest location | Treat catalog row as canonical or rewrite publication history |
| Producer manifest meaning | Originating producer | Public reader projection | Parse undocumented internals or normalize away producer distinctions |
| Source artifact content and revision | Producer or identified external source | Reference or authorized copied representation | Become competing canonical source |
| ScoreForm attempt and response facts | ScoreForm | Attempts, responses, points, provenance exposed publicly | Select official attempt or calculate Grade |
| Quillan submission and review facts | Quillan | Authorized source and feedback projection | Expose private notes or change review state |
| Concord Artifact authorship, subject, contribution, Score | Concord | Explicit relationships and approved representations | Infer individual ownership from group membership |
| Portia event, intervention, outcome | Portia | Minimum-necessary opt-in projection | Expose by default or reinterpret academically |
| Grading and proficiency | Meridian | Authorized Meridian report/output | Calculate or override grading results |
| Portfolio purpose and curation | Vitrine | Canonical Vitrine records | Move source semantics into portfolio records |
| Exact issued portfolio edition | Immutable Vitrine snapshot | Historical edition and provenance | Silently refresh or rewrite |
| Identity, consent, institutional approval | Responsible institution/system | References and recorded decisions | Infer authority from role labels |
| Suite-wide archive/disposition | Future Sunset or records authority | Handoff metadata and status | Delete upstream records or execute unauthorized disposition |
| Official transmission/receipt/outcome | Receiving external authority/system | Exact package, receipt, and outcome references | Fabricate or claim external decision |

## 21. Layered authority examples

### 21.1 Published ScoreForm attempt in a showcase

- ScoreForm is authoritative for the attempt, responses, and points.
- Core is authoritative for the publication identity and manifest digest binding.
- Vitrine is authoritative for the decision to include the attempt and the caption/reflection.
- The issued Vitrine snapshot is authoritative for what the showcase edition contained.
- None of those facts establishes which attempt Meridian uses for grading.

### 21.2 Concord group Artifact in an individual portfolio

- Concord is authoritative for Artifact identity, Authors, Subjects, Group, contribution records, and Scores.
- Vitrine is authoritative for the individual's selection and portfolio explanation.
- The explanation cannot transform Group Membership into individual authorship or proficiency.

### 21.3 Portia-derived support summary in a regulated packet

- Portia is authoritative for the intervention record.
- The institution is authoritative for access, necessity, and audience approval.
- Vitrine is authoritative for the exact minimum-necessary representation included in the packet.
- The external authority remains authoritative for the resulting decision.

### 21.4 Meridian report included in a parent-conference portfolio

- Meridian is authoritative for the report under its policy and source provenance.
- Vitrine is authoritative for the conference edition and any plain-language portfolio annotation.
- The annotation cannot replace the Meridian report or mutate its calculation.

## 22. Dependency directions

### 22.1 Permitted directions

```text
pds-vitrine -> pds-core public contracts
pds-vitrine -> producer public reader contracts
pds-vitrine -> Vitrine-owned adapters over stable public contracts
pds-vitrine -> optional Meridian public output contracts
pds-vitrine -> future Sunset handoff contract, when one exists
pds-vitrine -> external-system adapters at explicit boundaries
```

### 22.2 Prohibited required dependencies

```text
pds-core -> pds-vitrine workflow code
producer -> pds-vitrine as a required runtime dependency
pds-meridian -> pds-vitrine for Grade calculation
pds-portia -> pds-vitrine for intervention case state
pds-concord -> pds-vitrine for Artifact authorship or Scoring
pds-vitrine -> undocumented producer implementation internals
pds-vitrine -> one vendor-specific external payload as the universal domain model
```

### 22.3 Installation independence

Every producer must be able to operate and publish its records without Vitrine installed.

Vitrine must be able to report an unsupported or unavailable producer reader without corrupting working portfolios or prior issued snapshots.

### 22.4 Optional integration

A producer, Meridian, Sunset, or external connector may be absent. Absence must produce an explicit capability or availability state, not fallback parsing or silent omission.

## 23. Canonical, derived, copied, and issued state

| State class | Owner | May change? | Rebuildable? | Authoritative for |
| --- | --- | --- | --- | --- |
| Core canonical registry JSON | Core | Through Core-defined append/revision operations | No | Registration/publication identity and history |
| Producer canonical records | Producer | Through producer-defined lifecycle | No | Producer domain facts |
| Core catalog | Core derived state | Yes | Yes | Discovery convenience only |
| Vitrine candidate index | Vitrine derived state | Yes | Yes | Discovery convenience only |
| Vitrine working portfolio | Vitrine | Yes, with history | No | Current portfolio curation state |
| Source reference | Vitrine references upstream | May receive availability findings; identity must remain exact | N/A | Which upstream record was referenced |
| Copied representation | Vitrine | No after issuance; pre-issue replacement must be explicit | Regeneration may be impossible | Exact copied/rendered bytes under stated provenance |
| Issued Vitrine snapshot | Vitrine | No | No | Exact historical edition issued |
| Meridian report snapshot | Meridian | No once issued | No | Exact report generated under stated policy |
| External receipt/outcome | External authority; Vitrine may retain copy/reference | No except corrected external record | No | External acknowledgment or decision |
| Archive index | Sunset/records system derived or canonical per future contract | Contract-specific | Contract-specific | Location/custody, not source semantics |

## 24. Conceptual data flow

```text
1. Core discovery query
2. canonical Publication Record reload
3. exact registration/withdrawal/path/digest verification
4. producer compatibility evaluation
5. authorization to access producer publication
6. producer public reader resolves source facts
7. authorization to access underlying artifact or representation
8. Vitrine candidate evaluation under profile
9. authorized actor deliberately selects or rejects
10. Vitrine records placement, rationale, annotation, and reflection
11. privacy/rights/accessibility/profile review
12. authorized representation copied or rendered
13. exact bytes and generated files hashed
14. immutable Vitrine snapshot assembled
15. local issuance approval recorded
16. snapshot issued to named audience
17. optional external package prepared
18. optional transmission recorded from authoritative evidence
19. optional receipt/outcome recorded from external authority
20. optional future archive handoff
```

### 24.1 Authority at each transition

| Transition | Authoritative input | Responsible owner/actor | Output class |
| --- | --- | --- | --- |
| Discovery | Core catalog plus query | Vitrine using Core API | Derived candidates; nonauthoritative |
| Canonical reload | Core JSON | Core | Canonical envelope |
| Manifest verification | Publication path/digest plus exact file | Core contracts used by Vitrine | Integrity finding |
| Producer parse | Verified manifest and producer reader | Producer contract | Producer-native projection |
| Access authorization | Institution/deployment policy | Authorized policy layer | Permit/deny/unknown finding |
| Candidate evaluation | Producer facts plus portfolio profile | Vitrine | Portfolio-specific finding |
| Selection | Candidate plus authorized human decision | Student/teacher/reviewer per profile | Canonical Vitrine selection |
| Copy/render | Authorized source representation | Vitrine renderer/copy service | Copied representation |
| Snapshot issue | Approved selection set and generated package | Authorized issuer | Immutable Vitrine snapshot |
| External transmission | Approved package and authorized submitter | External connector/human | Submission event and external receipt reference |
| Outcome | External authority record | External authority | External outcome reference/copy |
| Archive handoff | Vitrine record descriptor and records authority | Future Sunset/records system | Custody/location state |

## 25. Working versus issued state

### 25.1 Working state may reflect current upstream information

A working portfolio may display:

- a newer producer revision;
- a successor publication;
- current withdrawal state;
- a newer Meridian report;
- a changed profile;
- a changed authorization finding;
- or an unavailable source.

Those current findings must not rewrite historical selection or issuance events.

### 25.2 Issued state is immutable

After issuance:

- selected identities remain fixed;
- copied bytes remain fixed;
- checksums remain fixed;
- display metadata remains fixed;
- profile version remains fixed;
- audience remains fixed;
- omissions and redactions remain fixed;
- and issuance time remains fixed.

Corrections create a successor edition. They do not modify the earlier edition.

### 25.3 Access may change without changing bytes

An institution may later restrict access to an issued snapshot because of consent withdrawal, legal hold, rights, or privacy policy. Access-state changes must not rewrite the historical bytes or claim the earlier edition contained different content.

## 26. Prohibited behavior catalog

Vitrine must not:

### Core and discovery

- use Core catalog rows as canonical records;
- skip canonical Publication Record reload;
- ignore withdrawal state;
- ignore manifest containment or digest verification;
- treat publication as access authorization;
- treat publication as portfolio approval;
- mutate Academic Work Registrations;
- mutate Publication Records or withdrawals;
- or add Vitrine fields to neutral Core records for convenience.

### Producer semantics

- crawl producer work directories for undocumented files;
- parse private schemas;
- infer semantics from paths or filenames;
- invent missing producer relationships;
- mutate producer-native records;
- flatten all producers into one universal score or artifact meaning;
- or replace a producer reader with heuristic interpretation.

### ScoreForm

- select an official or Grade-bearing attempt;
- rewrite attempt history;
- convert alignment into proficiency;
- or expose answer keys or secure assessment material without authority.

### Quillan

- change review state;
- modify teacher judgments;
- expose private notes through ordinary projection;
- or treat a portfolio annotation as a Quillan review amendment.

### Concord

- assign a group Artifact to every member;
- equate Group Membership with authorship;
- equate role with authorship;
- equate recorder with sole authorship;
- equate Artifact Subject with Author;
- equate Author or Subject with Score target;
- duplicate one source Artifact into false individual source copies;
- or claim individual proficiency from portfolio inclusion.

### Portia

- expose Portia records by default;
- reveal Portia presence through counts or diagnostics;
- automatically include intervention material;
- reinterpret Portia records as academic evidence or Grades;
- or modify Portia case state.

### Meridian

- calculate proficiency or Grades;
- decide Grade-item membership;
- select grading evidence;
- modify overrides;
- or use Meridian as a portfolio artifact manager.

### Snapshot and records management

- silently refresh an issued snapshot;
- change issued bytes in place;
- delete upstream records;
- infer destruction authority from lifecycle state;
- apply one universal retention period;
- or claim archive transfer changes historical content.

### External systems

- claim submission from package preparation;
- fabricate receipt or signature;
- claim external approval from local validation;
- claim legal compliance;
- claim graduation or diploma status;
- or overwrite an external decision with a Vitrine finding.

### Identity

- match students across classes or years solely by name;
- match solely by repeated unqualified `student_id`;
- or treat a display snapshot as authoritative identity.

Detailed identity contracts remain assigned to issue #4.

## 27. Edge-case ownership and behavior

### 27.1 Publication withdrawn after selection

- Core is authoritative for withdrawal.
- The working portfolio records current unavailability.
- Vitrine preserves selection history.
- Vitrine does not restore the publication or choose a prior revision automatically.
- An issued snapshot remains exact, subject to later access and retention policy.
- A new edition must explicitly omit, replace, or retain an authorized historical representation.

### 27.2 Manifest digest mismatch

- Treat the source as an integrity failure.
- Do not parse the mismatched manifest.
- Do not select new items from it.
- Do not alter Core's recorded digest.
- Preserve a minimal diagnostic that does not leak student-level contents.
- Existing issued snapshots remain verifiable by their own copied-byte digests.

### 27.3 Producer reader incompatible or unavailable

- Record an unsupported or unavailable state.
- Do not crawl directories or guess schema.
- Preserve current working references and prior snapshots.
- Permit later reconciliation when a compatible reader becomes available.

### 27.4 Several ScoreForm attempts

- Present attempts as ScoreForm describes them.
- Allow a curator to select an attempt for a portfolio purpose.
- Label the selection as portfolio-specific.
- Do not claim official or Grade-bearing status without an authoritative grading source.

### 27.5 Quillan private notes and feedback export coexist

- Use only the public, authorized projection.
- A student-readable feedback export may be eligible.
- Private notes remain unavailable unless a distinct approved contract and purpose permits them.
- Vitrine does not infer that a feedback export contains the complete Quillan review.

### 27.6 Concord group membership changes

- Preserve historical Concord relationships for the Artifact's context.
- Do not use current membership to rewrite past authorship or contribution.
- Require explicit relationship to the portfolio subject.
- Preserve collective scope when individual contribution is unresolved.

### 27.7 Portia publication technically discoverable

- Suppress it from ordinary candidate results.
- Do not reveal its existence to unauthorized actors.
- Require explicit profile opt-in and authorization before resolving the producer projection.
- Permit complete exclusion even when other producers are enabled.

### 27.8 Meridian recalculates a result

- A working portfolio may report that a newer report exists.
- The prior issued Vitrine snapshot remains unchanged.
- Reissue creates a new Vitrine edition with a new source reference and provenance.

### 27.9 External submission rejected

- Preserve the exact submitted package and receipt.
- Record the external rejection or correction request as an external fact.
- Do not rewrite the submitted package.
- A corrected package becomes a new submission event linked to the earlier one.
- Do not treat file rejection as final appeal denial unless the authority says so.

### 27.10 Snapshot transferred to archive storage

- Preserve snapshot identity, bytes, checksums, provenance, audience, and issuance history.
- Update custody or location through the future archive contract.
- Do not change historical meaning.
- Require separate authority for deletion or disposition.

### 27.11 Source artifact contains several students

- Preserve authoritative multi-student relationships.
- Do not make an unrestricted copy solely because one subject is in the portfolio.
- Require redaction, constrained access, omission, or a rights-holder/institutional decision.
- Record the chosen representation and review basis.

### 27.12 Source changed after snapshot preparation but before issuance

- Reverify source identity and copied representation before issuance.
- If copied bytes are already fixed and approved, issue only if the profile permits that exact prepared edition.
- Otherwise regenerate as a new preparation result.
- Do not silently combine old and new source states.

## 28. Cross-repository conflicts and conservative behavior

No direct ownership conflict was found among the reviewed documents. The repositories consistently separate:

- Core shared infrastructure;
- producer semantics;
- Meridian grading/reporting;
- Vitrine portfolio curation;
- Portia intervention meaning;
- and Concord collaborative relationships.

The primary uncertainty is implementation maturity rather than conceptual disagreement.

### 28.1 Runtime contracts are uneven

- Core v0.6 is implemented and released.
- ScoreForm's manifest and revision policy are implemented, while its complete Core 0.6 publication/reader integration remains active work.
- Quillan's producer publication and consumer-neutral reader remain future milestone work.
- Concord has a package baseline and accepted contracts, but domain persistence and public reader implementation remain future work.
- Portia has versioned schemas and architecture, but no executable application or production intervention publication.
- Meridian remains architecture-only.
- Sunset has no repository or public contract.

### 28.2 Conservative Vitrine rule

When a required public contract is unavailable, Vitrine must report the integration as unavailable or unsupported. It must not substitute direct filesystem parsing.

### 28.3 Cross-repository changes

This issue does not modify sibling repositories. A later implementation that requires a new or clarified public contract must open a focused sibling issue rather than weakening Vitrine's boundary.

## 29. Downstream implications

### Issue #4 — Portfolio identity, subject identity, and cross-class linking

Must define Vitrine-owned portfolio identity while referencing, not replacing, Core class-qualified student identity. Cross-class associations require explicit authority and correction history.

### Issue #5 — Portfolio profiles and versioned requirements

Must distinguish Vitrine profile ownership from external rule authority. Profiles may encode requirements but cannot manufacture institutional approval.

### Issue #6 — Candidate and source-reference contracts

Must represent exact Core publication and producer source identity, current availability, authorization, and explicit subject relationship without flattening producer semantics.

### Issue #7 — Producer artifact exposure boundaries

Must define public projections for ScoreForm, Quillan, Concord, and Portia. It must preserve this document's deny-by-default Portia rule and Concord relationship distinctions.

### Issue #8 — Selection, ordering, annotation, and reflection

Must keep portfolio interpretation separate from producer facts. Selection history cannot mutate source records.

### Issue #9 — Snapshot, export, checksum, and immutability

Must make issued editions immutable, preserve exact copied and rendered bytes, and separate access withdrawal from historical-byte mutation.

### Issue #10 — Privacy, redaction, and audience controls

Must implement authorization independently from Core discovery and prevent sensitive-source existence leakage.

### Issue #11 — Regulated portfolio/compliance profiles

Must separate local findings, institutional approval, external transmission, receipt, and external outcome. It must not claim Vitrine certifies compliance.

## 30. Open questions

The following are intentionally unresolved:

1. Which component evaluates authorization in an offline teacher-local deployment?
2. Which producer reader contracts will expose original artifacts versus summaries only?
3. Will Vitrine store consent bytes or only references to an authoritative consent system?
4. What public contract will Meridian eventually expose for report snapshots?
5. What minimum Portia projection, if any, should ever be eligible for a portfolio?
6. How will Concord expose authoritative contribution relationships when they exist?
7. What is the future Sunset handoff contract and custody model?
8. Which Vitrine records are official institutional records in each deployment?
9. How are external submission events authenticated when a human uploads outside Vitrine?
10. Which component owns cryptographic signing of issued snapshots, if signing is required?
11. How are access restrictions applied after an issued snapshot is archived?
12. Which sibling repository should host cross-module adapter contracts when more than one consumer needs them?

Open questions do not weaken the boundaries above. Until resolved, the conservative behavior is to deny or report unsupported operations rather than infer authority or semantics.

## 31. Conclusion

Vitrine is the owner of portfolio purpose, curation, interpretation, and immutable portfolio issuance. It is not the owner of the source facts it curates, the Grades or interventions that sibling modules calculate or record, the identities and permissions that institutions govern, the archive disposition that records authorities execute, or the outcomes that external authorities decide.

The architecture therefore follows this sequence:

```text
verify source authority
  -> preserve producer meaning
  -> obtain separate authorization
  -> record deliberate portfolio decisions
  -> issue an immutable audience-specific edition
  -> record, but never impersonate, external actions and outcomes
```
