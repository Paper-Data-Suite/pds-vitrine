# Portfolio Purposes and Workflows

- **Research date:** 2026-08-04
- **Issue:** #2, “Research portfolio purposes, workflows, and compliance constraints”
- **Status:** Foundation research input; not a final schema or implementation specification

## 1. Purpose of this document

This document compares four portfolio families that Vitrine is expected to support:

1. improvement portfolios;
2. showcase portfolios;
3. parent- or guardian-conference portfolios; and
4. regulated alternate-graduation-pathway portfolios.

The term *portfolio* is not sufficient to determine workflow, authority, mutability, audience, or evidentiary weight. Established portfolio literature describes a portfolio as a purposeful collection rather than a cumulative file, and repeatedly identifies selection, criteria, and reflection as distinguishing practices. It also recognizes materially different developmental, showcase, proficiency, and accountability uses. [PED-01] [PED-02] [PED-03] [PED-04]

For Vitrine, the operational consequence is:

> A discoverable artifact is not automatically a portfolio item, a selected item is not automatically approved for an audience, and a working portfolio is not automatically an issued snapshot.

The four families share infrastructure concepts, but their rules must be supplied by a purpose-specific and versioned profile rather than inferred from the word “portfolio.”

## 2. Scope and boundaries

This research describes human workflows and architecture inputs. It does not:

- define final JSON schemas or Python classes;
- establish a universal state machine;
- implement artifact discovery, authorization, copying, rendering, or validation;
- define grading or proficiency calculations;
- treat a portfolio as the authoritative source of producer records;
- grant access merely because Core can discover a publication;
- make an external legal, administrative, or graduation decision;
- make Portia records eligible by default;
- infer individual authorship or proficiency from a Concord group artifact;
- turn Meridian into an artifact manager; or
- establish a new Core publication kind.

## 3. Working definitions

### 3.1 Candidate

A **candidate** is an authorized, resolvable source record or artifact that may be considered for a particular portfolio. Candidate status means only that the item is available for consideration under the current actor, subject, purpose, and access context.

Candidate status does **not** mean:

- selected;
- shareable with the intended audience;
- suitable for the portfolio purpose;
- current or preferred;
- legally required;
- individually authored by the portfolio subject;
- evidence of individual proficiency; or
- safe to copy into an issued snapshot.

### 3.2 Selection

A **selection** is a deliberate decision by an authorized actor to place a candidate, or a purpose-appropriate representation of it, into a working portfolio section. The selection should preserve who selected it, why, when, under which profile, and with what relationship to the portfolio subject.

### 3.3 Working portfolio

A **working portfolio** is mutable. It may accumulate candidates, selections, annotations, reflections, requirements, review findings, replacements, and approvals. Its current view can change as source records become available, unavailable, superseded, withdrawn, or newly authorized.

### 3.4 Checkpoint

A **checkpoint** is a dated, reproducible capture used for reflection, review, progress comparison, or conference preparation. It may be retained, but it is not necessarily an externally issued or submitted artifact.

### 3.5 Issued snapshot

An **issued snapshot** is an immutable, purpose- and audience-specific package or record of what was issued at a particular time. It must not silently refresh when source artifacts, annotations, requirements, permissions, or profiles later change. Corrections require a new issued snapshot linked through replacement or supersession history.

### 3.6 External submission and external outcome

An **external submission** is the package or data actually sent to a receiving authority through an authorized process. An **external outcome** is the decision or response produced by that authority. Vitrine may record both, but it must not impersonate the receiving system or claim the authority’s decision as its own.

## 4. Shared workflow stages

The four families use different rules but can be analyzed through a common set of stages:

1. **Purpose and profile selection** — establish why the portfolio exists, for whom, and under which versioned requirements.
2. **Subject resolution** — identify whose work is represented, including explicit cross-class or cross-year associations.
3. **Actor authorization** — establish who may discover, view, select, annotate, review, approve, issue, or submit.
4. **Candidate discovery and resolution** — use Core and producer contracts to identify authorized source records, then resolve exact source meaning and artifact availability.
5. **Curation** — select, reject, replace, order, label, annotate, or reflect on items.
6. **Requirement and policy evaluation** — report what appears present, missing, prohibited, unavailable, or unresolved under the selected profile.
7. **Review and approval** — obtain any required human review, family/student acknowledgment, institutional approval, or attestation.
8. **Snapshot or export generation** — copy or render the approved representations, indexes, provenance, checksums, omissions, and audience metadata.
9. **Issuance or submission** — deliver the snapshot to the intended audience or external system through an authorized channel.
10. **Outcome and lifecycle follow-up** — record conference notes, external outcomes, corrections, supersession, withdrawal, retention, and disposition.

The common stages are analytical, not a requirement that every portfolio use every stage or state name.

## 5. Improvement portfolios

### 5.1 Purpose and boundary

An improvement portfolio demonstrates development over time. It should make a learning trajectory intelligible by connecting baseline work, attempts, feedback, revision, reflection, and later performance. It is not simply a folder of all attempts and should not automatically identify the “best” or “official” attempt. Portfolio research supports growth tracking, student selection, criteria, and self-reflection as central practices. [PED-01] [PED-02] [PED-03] [PED-04]

Vitrine may organize evidence around standards, criteria, goals, or questions, but it must not calculate grades or replace Meridian’s grading/reporting responsibilities.

### 5.2 Typical actors and responsibilities

| Actor | Typical responsibilities | Authority limits |
| --- | --- | --- |
| Student | Selects or proposes artifacts; explains change; writes reflection; sets goals; may approve student-facing presentation | Cannot gain access to records outside authorized scope; cannot alter producer records or institutional attestations |
| Teacher | Defines instructional purpose and criteria; authorizes candidate pool; reviews selections; supplies feedback context; creates checkpoints | Does not convert discovery into blanket disclosure authority; cannot silently assign cross-class identity |
| Additional educator or reviewer | Reviews growth claim, criteria alignment, or moderation evidence when required | Sees only authorized records and should not become an artifact owner |
| Portfolio/profile administrator | Defines permitted sections, roles, retention, and issuance rules | Does not select artifacts on behalf of participants unless profile grants that role |
| Family or conference participant | May receive a purpose-limited snapshot or participate in a conference | Does not automatically receive teacher-private notes or every candidate record |

### 5.3 Trigger and candidate pool

Typical triggers include:

- beginning a unit, course, intervention, or standards cycle;
- receiving a baseline artifact;
- planning a revision sequence;
- preparing a checkpoint or progress review; or
- beginning a cross-course or multi-year growth inquiry.

Candidates may include:

- original work;
- later attempts or revisions;
- producer-owned feedback exports;
- question-level or criterion-level evidence summaries;
- student reflections;
- teacher-selected exemplars or context documents, subject to rights and policy;
- group artifacts with an explicit subject relationship; and
- unavailable-source markers when a previously selected source can no longer be resolved.

A Core Publication Record or producer manifest may help discover and resolve a candidate, but candidate access still requires authorization, and source semantics remain producer-owned.

### 5.4 Lifecycle

A representative improvement workflow is:

```text
purpose/profile chosen
  -> subject and actors confirmed
  -> baseline candidates discovered
  -> baseline selection and rationale recorded
  -> goals/criteria attached
  -> later attempts and feedback become candidates
  -> student/teacher compare and reflect
  -> selections are retained, replaced, or reordered
  -> checkpoint optionally issued
  -> instruction continues
  -> final reflection/review
  -> final purpose-specific snapshot optionally issued
  -> later correction or supersession creates a new snapshot
```

The working portfolio remains mutable. A checkpoint or final snapshot is immutable once issued.

### 5.5 Evidence relationships

An improvement portfolio needs more than chronological order. Later architecture should be able to represent claims such as:

- “revision of” or “later attempt related to” without altering producer history;
- “selected as baseline,” “selected as intermediate evidence,” or “selected as current evidence”;
- “feedback associated with this exact revision”;
- “student reflection compares these exact artifacts”;
- “goal or standard focus for this portfolio section”; and
- “source no longer available, but issued snapshot retained an exact copied representation.”

Relationships must distinguish portfolio interpretation from producer facts. For example, Vitrine may record that a student selected two ScoreForm attempts to illustrate a change, but it must not declare one the official grade-bearing attempt unless an authoritative producer or grading source says so.

### 5.6 Outputs

Possible outputs include:

- mutable working view;
- dated checkpoint for student/teacher review;
- conference-ready growth summary;
- student reflection packet;
- final improvement narrative; or
- immutable archive snapshot.

The output profile should decide whether to include full artifacts, extracts, thumbnails, rendered feedback, summaries, standards labels, or only provenance references.

### 5.7 Failure and edge states

| Condition | Required behavior |
| --- | --- |
| Earlier source withdrawn | Preserve the selection history and mark current source availability; do not silently remove it from prior issued snapshots |
| Source superseded | Surface successor information without automatically replacing the selected revision |
| Feedback refers to another revision | Report the mismatch; do not present the feedback as applying to the selected artifact |
| Cross-course identity unresolved | Block or flag the cross-course selection until an authorized association is confirmed |
| Group artifact discovered | Require explicit relationship such as participant, contributor, author, subject, or score target; do not infer individual ownership or proficiency |
| Sensitive Portia record appears | Exclude by default; require profile permission, authorization, and deliberate opt-in |
| Student and teacher disagree on selection | Preserve distinct proposals or decisions if the profile permits; do not overwrite one actor’s rationale with another’s |
| Candidate is inaccessible | Distinguish unauthorized, unavailable, missing, corrupt, incompatible, and withdrawn states |

### 5.8 Improvement-specific architecture inputs

- explicit baseline/intermediate/current roles;
- artifact-to-artifact and reflection-to-artifact relationships;
- preserved replacement history;
- mutable curation plus immutable checkpoints;
- actor-specific rationales and reflections;
- standards/goals as organization, not grading authority;
- cross-course identity confirmation; and
- source-availability and compatibility findings.

## 6. Showcase portfolios

### 6.1 Purpose and boundary

A showcase portfolio presents deliberately selected work to a defined audience. It may highlight quality, range, identity, interests, accomplishment, or readiness. Established literature distinguishes showcase portfolios from developmental and proficiency portfolios. [PED-04]

“Showcase” must not be equated with “public website.” A classroom audience, admissions reviewer, scholarship committee, employer, family, school exhibition, and unrestricted public audience create different privacy, rights, accessibility, and disclosure requirements.

### 6.2 Typical actors and responsibilities

| Actor | Typical responsibilities | Authority limits |
| --- | --- | --- |
| Student curator | Proposes theme, sections, selections, ordering, display titles, annotations, reflections, and audience | Cannot disclose records or collaborators’ information without authority; cannot erase source provenance |
| Teacher/adviser | Coaches selection and reflection; confirms school-purpose requirements; reviews appropriateness and accuracy | Should not replace student voice unless the profile establishes teacher-curated presentation |
| Rights/privacy reviewer | Reviews third-party content, group work, names, peer feedback, images, and intended audience | Does not decide educational merit unless assigned another role |
| Institutional approver | Approves school-sponsored external publication where local policy requires | Approval is purpose- and audience-specific, not universal artifact approval |
| Audience member | Receives issued view or package | Access should match the issued audience, expiration, and redistribution rules |

### 6.3 Trigger and candidate pool

Triggers include:

- culminating course or program presentation;
- scholarship, admission, internship, or employment preparation;
- exhibition or celebration;
- student personal archive; or
- transition between schools or programs.

Candidates may include final products, selected process evidence, reflections, feedback excerpts, awards, project summaries, media, code, visual art, writing, assessment summaries, and group work. Profiles should identify prohibited or restricted source classes, especially secure assessment content, behavioral/intervention records, disability/accommodation details, private notes, and artifacts containing other students’ PII.

### 6.4 Lifecycle

```text
purpose and audience defined
  -> profile and selection authority established
  -> candidates discovered and authorized
  -> student/teacher curates sections and ordering
  -> display metadata, annotation, and reflection added
  -> privacy, rights, accessibility, and group-work review
  -> required approval or consent collected
  -> immutable audience-specific snapshot rendered
  -> snapshot issued through approved channel
  -> later correction, withdrawal, or reissue recorded
```

The working showcase may remain mutable, but every issued edition should preserve its exact content, audience, permissions, copied-byte checksums, and issuance time.

### 6.5 Presentation requirements

Showcase profiles may need:

- purpose statement and audience;
- theme and section structure;
- display titles distinct from canonical source titles;
- curator annotations;
- artifact captions and accessibility descriptions;
- student reflections;
- attribution and authorship statements;
- group-participation description;
- rights/permission status;
- redaction choices;
- media fallbacks;
- offline package or printable form; and
- portfolio version or edition statement.

Display metadata must not overwrite canonical source metadata. A student may provide a display title, but the exact source identity and revision remain traceable.

### 6.6 Rights and privacy review

Before external issuance, the workflow should distinguish:

1. authority to access the source record;
2. authority to select it for a working portfolio;
3. authority to disclose it to the named audience;
4. authority to reproduce or publicly display embedded third-party material; and
5. authority to identify collaborators, peers, teachers, or institutions.

School possession of a student artifact is not the same as copyright ownership, and educational use does not automatically make every public showcase use fair. [COPY-01] [COPY-02] [COPY-03] [COPY-04]

### 6.7 Group work

A showcase may display a Concord group artifact only with explicit relationship and permission treatment. Later architecture should be able to show:

- the group or artifact author identity;
- the portfolio subject’s documented relationship, such as participant, contributor, presenter, editor, or subject;
- whether individual contribution is described by an authoritative source or student annotation;
- collaborator-display permissions or redactions; and
- a warning that inclusion does not itself prove individual proficiency.

### 6.8 Outputs

Possible outputs include:

- secure reviewer package;
- school exhibition edition;
- student-controlled offline archive;
- application-specific PDF or HTML package;
- family edition; or
- public edition with stronger redaction and permission requirements.

A single working showcase may produce multiple issued snapshots with different audiences and omissions. Those are separate editions, not interchangeable links to one mutable current view.

### 6.9 Failure and edge states

| Condition | Required behavior |
| --- | --- |
| Audience changes from internal to public | Re-run disclosure, rights, redaction, and accessibility review; do not reuse prior approval automatically |
| Third-party text/image embedded | Require rights basis or omit/redact/replace representation |
| Peer or teacher feedback included | Evaluate whether identities and comments may be disclosed; provide an audience-safe projection where authorized |
| Link-only artifact may disappear | Prefer exact copied representation when permitted; otherwise record link availability and snapshot limitation |
| Media cannot render offline | Include fallback, transcript, still image, description, or explicit omission finding |
| Consent later withdrawn | Apply policy to future access/issuance and record withdrawal; do not silently rewrite an already issued regulated record |
| Source is revised after issuance | Preserve issued edition; create a new edition only through explicit reissue |

### 6.10 Showcase-specific architecture inputs

- audience-specific editions;
- display metadata separate from source metadata;
- rights, attribution, and permission findings;
- redaction and collaborator treatment;
- mixed-media rendering and accessible alternatives;
- withdrawal and reissue history; and
- explicit public/private/limited audience distinctions.

## 7. Parent- or guardian-conference portfolios

### 7.1 Purpose and boundary

A conference portfolio supports a scheduled conversation about progress, strengths, needs, goals, or next steps. Portfolio and student-led-conference research emphasizes student preparation, evidence selection, reflection, family understanding, and clear participant roles. [PED-03] [PED-05] [PED-06] [PED-07]

A family relationship does not grant unrestricted access to every discovered record. The conference package should be intentionally scoped to the subject, conference purpose, participant rights, and applicable school policy.

### 7.2 Typical actors and responsibilities

| Actor | Typical responsibilities | Authority limits |
| --- | --- | --- |
| Student | Selects or rehearses evidence; reflects; presents strengths, needs, and goals | Participation level may vary by age, profile, accommodation, or conference type |
| Teacher/adviser | Selects representative evidence where authorized; prepares plain-language context; facilitates discussion; identifies next steps | Must separate family-shareable content from sole-possession notes or other internal material |
| Parent/guardian or eligible student | Reviews authorized records, asks questions, acknowledges or contributes goals | Does not automatically receive records about another student or internal deliberative content |
| Interpreter/accessibility support | Provides language or communication access | Receives only the information needed for the role and is governed by applicable policy |
| Administrator/case manager/counselor | Participates when profile or student need calls for it | Role does not create blanket access outside legitimate educational interest |

### 7.3 Trigger and candidate pool

Triggers include scheduled conferences, progress reviews, student-led conferences, transition meetings, intervention follow-up, or family-requested discussion.

Candidates should be representative rather than exhaustive. A balanced packet may include:

- a purpose statement and agenda;
- student-selected work;
- evidence of growth;
- current work illustrating strengths or needs;
- accessible summaries of standards or goals;
- teacher feedback selected for family sharing;
- student reflection;
- next-step commitments; and
- exact provenance links for staff who are authorized to inspect the sources.

Sensitive material, teacher-private notes, Portia records, records about peers, and disability/accommodation information require separate authorization and purpose analysis.

### 7.4 Lifecycle

```text
conference scheduled and participants identified
  -> purpose and audience profile chosen
  -> authorized candidate pool assembled
  -> student/teacher select representative evidence
  -> plain-language summaries and reflections prepared
  -> privacy, translation, accessibility, and print/offline needs checked
  -> dated conference snapshot issued or printed
  -> conference occurs
  -> acknowledgments, questions, and next steps recorded separately
  -> correction or follow-up packet issued when needed
  -> retention/disposition follows local policy
```

The conference snapshot should remain an accurate record of what was presented on that date. Post-conference notes and later evidence should not mutate the issued packet.

### 7.5 Family-shareable versus internal content

Later Vitrine design must support separate projections for:

- family-shareable artifact and feedback content;
- student-only reflection drafts;
- teacher/internal preparation notes;
- formal education records to which access rights apply;
- records about multiple students requiring redaction or constrained inspection; and
- follow-up commitments or acknowledgments.

The distinction cannot be reduced to a single “private” flag. FERPA defines education records by relationship and maintenance, limits internal access to legitimate educational interests, and imposes special handling for records involving multiple students. [FERPA-01] [FERPA-04] [FERPA-05] [FERPA-09] [FERPA-10]

### 7.6 Communication and accessibility

A conference profile may require:

- translated labels or narrative;
- interpreter logistics;
- alternative formats;
- accessible HTML or tagged PDF;
- captions/transcripts for media;
- image descriptions;
- keyboard-accessible digital presentation;
- high-contrast or large-print output;
- printable offline packet; and
- clear distinction between plain-language summary and canonical source values.

The summary may explain a source result, but it must not silently alter the source meaning or substitute an unsupported proficiency judgment.

### 7.7 Outputs

Possible outputs include:

- student-led presentation edition;
- teacher-led conference packet;
- family-language edition;
- accessible alternate-format edition;
- internal preparation view; and
- dated follow-up summary.

Each audience-specific edition should identify omissions, redactions, translation status, and whether it is an official education record, a working aid, or an issued conference snapshot under local policy.

### 7.8 Failure and edge states

| Condition | Required behavior |
| --- | --- |
| Guardian identity or access rights unresolved | Do not release the packet until the responsible institutional system/policy confirms access |
| Artifact contains another student | Redact or use a permitted limited-access process; do not issue an unreviewed copy |
| Translation unavailable by conference time | Record the gap and provide an authorized accommodation path rather than silently issuing inaccessible content |
| Source changed after packet generation | Preserve conference edition and optionally prepare a clearly dated correction/addendum |
| Teacher note is sole-possession only | Do not ingest or share it in a way that changes its treatment without policy review |
| Family requests exhaustive records | Route to the institution’s records-access process; a conference portfolio is not necessarily the complete education record |
| No parent/guardian attends | Profile may allow student-only, rescheduled, alternate-contact, or staff conference; record actual audience rather than intended audience |

### 7.9 Conference-specific architecture inputs

- participant and access-right confirmation;
- family-shareable and internal projections;
- plain-language summaries linked to exact sources;
- translation and accessibility variants;
- dated packet plus separate post-conference notes;
- participant acknowledgment and next-step records; and
- correction/addendum rather than silent refresh.

## 8. Regulated alternate-graduation-pathway portfolios

### 8.1 Purpose and boundary

A regulated portfolio is evidence used in an externally governed eligibility, proficiency, appeal, certification, or graduation decision. It differs from an instructional portfolio because required evidence, task composition, scoring, responsible officials, attestations, deadlines, retention, submission formats, and external outcomes are governed by an authority outside Vitrine.

New Jersey’s Class of 2026 Graduation Portfolio Appeal illustrates this workflow. The administrative code defines the portfolio appeals process as an alternative assessment of graduation proficiency and establishes its place among alternative means. Current NJDOE guidance then supplies cohort-specific ELA, mathematics, streamlined, special-population, submission, and local-retention requirements. [NJ-REG-01] [NJ-REQ-01] [NJ-APP-01]

Vitrine may help gather evidence, evaluate profile completeness, generate a local snapshot, and record external outcomes. It must not claim to approve the appeal, award a diploma, certify legal compliance, or replace NJDOE Homeroom.

### 8.2 Typical actors and separation of duties

| Actor | Typical responsibilities | Authority limits |
| --- | --- | --- |
| Student | Completes required tasks using authorized accommodations; may review permitted records | Does not attest institutional compliance or submit on behalf of the institution unless external rules explicitly permit |
| Teacher/task developer | Designs aligned local tasks; administers and scores them; prepares cover sheets and evidence | Cannot substitute ordinary classwork where the profile requires specific CRTs; should not approve own work where local policy requires review |
| Portfolio Appeals Coordinator | Obtains templates; coordinates records; uploads required submission documents; retrieves outcomes | Role and portal authority come from NJDOE/local assignment, not Vitrine |
| Principal | Reviews and signs required institutional assurance | Signature is an external/legal attestation, not a Vitrine-generated status |
| Chief School Administrator | Reviews and signs required institutional assurance | Same limitation |
| LEA/APSSD staff, case manager, ML/IEP support | Provides plans, records, accommodations, translation, intervention evidence, and coordination | Access and participation are role- and policy-dependent |
| NJDOE | Receives submission, reviews, requests correction where applicable, and issues outcome | External decision-maker; Vitrine may only record the returned outcome |
| Records officer/policy owner | Classifies and retains local records; governs disposition and legal hold | Retention cannot be hard-coded by Vitrine without policy/profile authority |

### 8.3 Trigger and eligibility

A regulated workflow begins only after profile-defined prerequisites are established. In the New Jersey example, the Class of 2026 guides describe grade 12 students who took the relevant NJGPA component and did not otherwise meet the graduation assessment requirement; regulation also identifies remediation/additional opportunity context. Different pathways may be used by subject, and the FAQ says a student need not first attempt a second-pathway substitute test before using the third pathway. [NJ-REG-01] [NJ-ELA-01] [NJ-MATH-01] [NJ-FAQ-01]

Vitrine should represent eligibility **findings and evidence**, not assert legal eligibility from incomplete data.

### 8.4 Candidate and required evidence

Regulated profiles must distinguish:

- required local evidence;
- required externally submitted documents or data;
- required institutional attestations;
- optional supporting context;
- prohibited evidence;
- conditionally required evidence; and
- evidence that must remain local but retrievable for audit.

The New Jersey example includes locally maintained EPP, transcript, assessment/substitute results, intervention plan, CRTs, graded responses, cover sheets, accommodations/translations, and qualifying ASVAB evidence where the streamlined option is used. The external submission described publicly is a school-specific SOA PDF and Portfolio Appeals Data Spreadsheet XLSX through NJDOE Homeroom. [NJ-APP-02] [NJ-ELA-01] [NJ-MATH-01] [NJ-STR-01] [NJ-FAQ-01]

### 8.5 Lifecycle

```text
profile version activated
  -> student/cohort/content-area eligibility evidence gathered
  -> pathway variant selected
  -> required plans, prior results, and intervention records confirmed
  -> local tasks designed/reviewed
  -> accommodations/translation process established
  -> tasks administered and scored
  -> cover sheets and local evidence assembled
  -> completeness and validation findings reviewed by humans
  -> institutional assurance prepared and signed
  -> required submission files produced
  -> authorized coordinator submits through external system
  -> receipt and external outcome retained
  -> correction/resubmission creates a new submission event
  -> local file retained and remains retrievable for audit
  -> profile later superseded for a new cohort or source version
```

### 8.6 Mutability and evidence integrity

Before submission, working records may be corrected under the controlling policy. After issuance or submission:

- the submitted package must remain reproducible;
- copied files and generated indexes should have checksums;
- signatory and approval history should be preserved;
- corrections should create a new submission event;
- the prior submission should remain linked and marked superseded or corrected;
- external receipts and outcomes should be retained as external records; and
- profile changes must not retroactively rewrite the rules used for the prior submission.

### 8.7 Findings versus decisions

Vitrine may report:

- `present`;
- `missing`;
- `not applicable`;
- `prohibited`;
- `unavailable`;
- `unauthorized`;
- `invalid format`;
- `score outside profile range`;
- `requires human verification`;
- `restricted source unavailable`; or
- `profile version superseded`.

It must not translate those findings into “NJDOE approved,” “student has graduated,” or “legally compliant.” Only the authorized external or institutional actor can produce those decisions.

### 8.8 Outputs

Potential Vitrine outputs are:

- local evidence inventory;
- profile completeness report;
- unresolved/restricted-source report;
- review packet;
- immutable local submission snapshot;
- generated copies of permitted submission documents;
- submission event record;
- receipt record; and
- recorded external outcome.

The actual upload must remain an explicit, authorized external-system action unless a future integration is separately approved and designed.

### 8.9 Failure and edge states

| Condition | Required behavior |
| --- | --- |
| Cohort profile not current | Block compliance assertion and require profile review/supersession |
| Restricted Homeroom template unavailable | Mark requirement unresolved; do not invent fields or attestation language |
| Student uses different pathways by subject | Model content-area pathways independently and preserve shared student/cohort context |
| Required local evidence exists but is not submitted | Classify it as locally retained; do not package it merely because it is required for audit |
| Required signatory has not signed | Report missing attestation; Vitrine cannot simulate signature or approval |
| Submission corrected | Preserve initial event and issue new corrected/resubmission event |
| Deadline missed | Report profile deadline finding; do not decide waiver, extension, or graduation status |
| Accommodation evidence incomplete | Require human review and preserve original/translated/transcribed relationships |
| External system rejects a file | Record external rejection and returned diagnostic; do not reinterpret as final appeal denial |
| Outcome letter unavailable | Preserve submission/receipt state and mark outcome unresolved |

### 8.10 Regulated-profile architecture inputs

- jurisdiction/program/cohort/profile version;
- authority and source versions;
- eligibility and prerequisite findings;
- required/optional/prohibited/conditional evidence;
- local-retention versus external-submission classification;
- scoring and format constraints as profile data;
- responsible roles and separation of duties;
- signatures/attestations as externally meaningful records;
- deadlines and submission windows;
- immutable submission events;
- correction/resubmission history;
- external receipt and outcome records; and
- explicit “Vitrine does not certify” boundaries.

## 9. Cross-workflow comparison

| Dimension | Improvement | Showcase | Parent/guardian conference | Regulated pathway |
| --- | --- | --- | --- | --- |
| Primary purpose | Explain growth and learning over time | Present selected accomplishments or identity to an audience | Support a time-bounded progress conversation | Supply governed evidence for an external decision |
| Typical initiator | Student or teacher | Student, adviser, or program | Teacher, student, school, or family | Institution under external rules |
| Student selection | Usually central | Usually central, profile-dependent | Often central in student-led formats; may be shared | Limited by exact required evidence and institutional process |
| Candidate breadth | Attempts, revisions, feedback, reflections | Best/representative work and context | Representative evidence for discussion | Only authorized evidence classes under profile |
| Required criteria | Learning goals or reflection prompts | Theme, audience, quality, range, permission | Conference goals, strengths, needs, next steps | Eligibility, task, score, document, attestation, and deadline rules |
| Working mutability | High | High until issue | High during preparation | Controlled; corrections require traceability |
| Issued output | Checkpoint or growth snapshot | Audience-specific edition | Dated conference packet | Submission snapshot plus receipt/outcome history |
| Public sharing | Usually unnecessary | Possible but separately authorized | Usually no | No, except as external rules require |
| External approval | Usually no | Sometimes institutional publication approval | Usually no | Essential; decision belongs to external authority |
| Retention | Instructional/local policy | Purpose and consent/policy dependent | Often local and time-bounded, but policy dependent | Governed by profile, records schedule, and audit needs |
| Core architectural risk | Confusing latest/best/official attempt | Confusing possession with permission/publication rights | Over-sharing internal or multi-student records | Hard-coding current rules or claiming compliance/approval |

## 10. Actor and responsibility matrix across families

| Responsibility | Student | Teacher/adviser | Institutional approver/coordinator | External authority | Vitrine |
| --- | --- | --- | --- | --- | --- |
| Define universal product semantics | No | No | No | No | Maintains product contracts, not local policy |
| Define purpose/profile requirements | May propose | May propose | Usually approves local/profile use | Defines regulated requirements | Stores/version-resolves approved profile inputs |
| Authorize source access | No blanket authority | Within assigned role | Policy/system authority | May govern submitted access | Enforces supplied authorization context; does not invent authority |
| Select artifacts | Often | Often | Sometimes | Rarely | Records authorized selections |
| Explain/reflect | Usually | May annotate | May attest/review | May return findings | Preserves actor-authored records |
| Approve family/public issue | May consent/acknowledge | May recommend | Often required by policy | Not usually | Records approval evidence; does not create authority |
| Submit regulated package | No, unless rule permits | Usually no | Authorized coordinator | Receives | Generates/records permitted package, but does not impersonate portal |
| Make external decision | No | No | No | Yes | Records outcome as external |
| Retain/dispose official records | No | Operational role only | Institution/records officer | May impose requirements | Applies configured policy; cannot classify records unilaterally |

## 11. Concepts supported across all four families

The research supports later modeling of the following shared concepts:

1. **Purpose-specific, versioned profile** — purpose, audience, requirements, authority, effective dates, and supersession.
2. **Portfolio subject** — explicit identity and class/course/year relationships; no name-only or repeated-ID matching.
3. **Actors and roles** — curator, reviewer, approver, signer, issuer, submitter, recipient, external decision-maker.
4. **Authorized candidate** — exact source and relationship metadata plus current access/availability findings.
5. **Selection record** — who selected what, when, why, for which section, and with what display metadata.
6. **Source provenance** — producer, work identity, publication, manifest digest, source record, revision, artifact kind, media type, and checksum where copied.
7. **Subject relationship** — individual author, participant, contributor, subject, score target, reviewer, or other explicit relationship.
8. **Annotation and reflection** — actor-authored interpretation distinct from producer truth.
9. **Requirement finding** — present/missing/prohibited/conditional/unresolved without external approval claims.
10. **Audience and authorization** — artifact access, selection authority, disclosure permission, and issued audience remain separate.
11. **Working versus issued state** — mutable curation and immutable issued snapshots.
12. **Replacement and supersession** — source successor, selection replacement, snapshot reissue, and profile supersession are distinct.
13. **Availability state** — available, unauthorized, missing, withdrawn, corrupt, incompatible, unresolved, or retained only in prior snapshot.
14. **Copy/export provenance** — exact copied bytes, generated derivatives, checksums, rendering metadata, omissions, and redactions.
15. **External event** — submission, receipt, correction, outcome, or withdrawal recorded without impersonating the external authority.

## 12. Concepts that must remain profile-driven

The following must not become universal Vitrine rules:

- who owns or initiates curation;
- whether student selection is required;
- required sections or artifact counts;
- grading, score, threshold, or rubric rules;
- eligibility prerequisites;
- allowed source modules or artifact kinds;
- whether feedback, scans, raw responses, group work, or intervention records may be included;
- whether an artifact is copied, rendered, summarized, linked, or omitted;
- approval and signature chains;
- public, family, internal, or external-reviewer audience rules;
- redaction and attribution requirements;
- retention and disposition periods;
- deadlines, naming conventions, file formats, and submission fields;
- accommodation and translation requirements;
- correction/resubmission semantics; and
- whether an output is a checkpoint, issued packet, official record, or external submission.

## 13. Discovery, access, selection, issuance, and approval are separate

Later tickets should preserve this order of questions:

1. **Discovery:** Does Core identify a potentially relevant publication or work?
2. **Compatibility:** Can Vitrine evaluate the producer profile and use the producer’s public reader?
3. **Resolution:** Can the exact canonical record and artifact be loaded and verified?
4. **Access authorization:** May the current actor access the record for this purpose?
5. **Candidate eligibility:** Does the selected profile permit the source class and subject relationship?
6. **Selection:** Has an authorized actor deliberately selected it?
7. **Disclosure authorization:** May the selected representation be shown to the intended audience?
8. **Issue approval:** Have required reviews, permissions, and attestations been satisfied?
9. **Snapshot issuance:** What exact immutable package was produced and delivered?
10. **External submission/decision:** Was it sent, received, corrected, and decided by the external authority?

A positive answer at one stage must not imply a positive answer at a later stage.

## 14. Cross-cutting edge cases and unresolved questions

### 14.1 Identity and cross-class work

- Which institutional authority may confirm that two class-qualified student references represent the same portfolio subject?
- How is a mistaken association revoked without rewriting issued snapshots?
- Can a portfolio span institutions, and what authority validates the link?

### 14.2 Producer availability

- What minimum public-reader contract will each producer provide?
- What happens when a historical manifest remains valid but the producer reader version is no longer installed?
- Which artifact representations may be copied versus only referenced?

### 14.3 Group artifacts

- Which producer relationships distinguish group author, participant, contributor, subject, and score target?
- How are collaborator permissions represented for external showcase editions?
- How can a student reflect on participation without creating an unsupported individual proficiency claim?

### 14.4 Sensitive material

- Which profile authority may opt Portia material into a portfolio?
- Which Portia projections are permitted for family, student, teacher, or external audiences?
- Are accommodation details needed to interpret evidence, or should only an accommodation-applied finding be exposed?

### 14.5 Rights and withdrawal

- Can a student withdraw consent for future showcase access while the school retains an official issued record?
- How should rights restrictions affect copied bytes already included in a lawful prior snapshot?
- Which institution policy controls student-created work after graduation?

### 14.6 Accessibility variants

- Is an alternate accessible rendering a representation of the same selected artifact or a separately selected derivative?
- How are transcript/translation authorship, accuracy review, and checksum relationships preserved?
- Which generated formats can Vitrine validate versus merely report as created?

### 14.7 Retention

- Which Vitrine records are mandated student records, permitted student records, instructional working files, or administrative submission records in a given jurisdiction?
- Does deletion of a working portfolio affect retained issued snapshots?
- How are legal holds, records transfers, and disposition approvals represented?

## 15. Architecture inputs for later tickets

The research supports later architecture work on:

- purpose-specific, versioned portfolio profiles;
- mutable working portfolios and immutable issued snapshots;
- explicit subjects, actors, roles, approvals, attestations, and external outcomes;
- required, optional, prohibited, and conditionally required sections/documents;
- eligibility and prerequisite findings;
- completeness findings that do not claim external approval;
- jurisdiction, program, school year/cohort, source version, effective date, and supersession metadata;
- local-retention versus external-submission classifications;
- audience and authorization constraints;
- accommodations, translations, transcripts, and alternate accessible representations;
- exact source provenance, revisions, publication/manifests, checksums, and unavailable-source states;
- corrections, resubmissions, selection replacement history, and superseded snapshots;
- deliberate opt-in and privacy governance for sensitive Portia material; and
- explicit Concord group relationships without automatic individual ownership or proficiency attribution.

These are design inputs, not final contracts. Subsequent issues must define ownership boundaries and representations without weakening producer authority, Core verification, privacy controls, or external decision boundaries.

## 16. Sources

See [Portfolio Research Source Register](source-register.md), especially PED-01 through PED-07, NJ-REG-01 through NJ-SP-01, FERPA-01 through FERPA-11, ADA-01 through ADA-03, and COPY-01 through COPY-04.
