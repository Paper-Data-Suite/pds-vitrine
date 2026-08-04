# Portfolio Compliance and Policy Constraints

- **Research date:** 2026-08-04
- **Issue:** #2, “Research portfolio purposes, workflows, and compliance constraints”
- **Status:** Foundation research input; not legal advice, a final security design, or a compliance certification

## 1. Purpose

This document catalogs external constraints that must inform later Vitrine architecture. It does not settle institution-specific legal questions or define final enforcement mechanisms. Its purpose is to prevent later design from assuming that discovery, access, curation, disclosure, publication, retention, or regulatory approval are equivalent.

Sources are identified by the IDs in [source-register.md](source-register.md).

## 2. Governing separation of concerns

Vitrine should preserve the following distinctions throughout its contracts and workflows:

```text
source is discoverable
  != actor may access source
  != source is a valid candidate for this purpose
  != actor may select source
  != selected representation may be copied
  != copied representation may be disclosed to this audience
  != snapshot satisfies profile requirements
  != institution has approved issuance/submission
  != external authority has accepted or approved it
```

This separation is the most important compliance design constraint. Core discovery and producer publication establish technical discoverability and source identity; they do not grant portfolio access, disclosure authority, audience permission, or legal approval.

## 3. Student privacy and education-record constraints

### 3.1 Education-record status is contextual

Student work, scores, feedback, reflections, portfolio selections, generated reports, access logs, and associated metadata may be education records when they are directly related to a student and maintained by an educational agency, institution, or qualifying party acting for it. [FERPA-01]

Vitrine should not assign one universal privacy classification based solely on file type. Classification may depend on:

- relationship to a student;
- who maintains the record and for what purpose;
- whether the content is a formal record, working copy, or qualifying sole-possession note;
- whether other students are identifiable;
- audience and disclosure context;
- local policy and state law; and
- whether the parent or student is the current FERPA rights holder.

### 3.2 Access is role- and purpose-limited

FERPA does not authorize every employee to access every student record. Internal non-consensual access under the school-official exception is limited to officials with a legitimate educational interest, and schools must use reasonable administrative or technological controls to restrict access accordingly. [FERPA-04] [FERPA-05]

Likely later Vitrine responsibilities include:

- actor identity and authenticated session context;
- institutional role and profile-specific permissions;
- purpose or case context;
- subject and class/school scope;
- least-privilege candidate discovery;
- authorization result with reason and policy source;
- denial that does not leak sensitive metadata; and
- auditable access and export events where policy requires them.

A user with permission to curate one course portfolio must not gain access to unrelated classes, years, students, producer records, or sensitive Portia material.

### 3.3 Parent, guardian, and eligible-student rights

FERPA gives parents rights to inspect/review and seek amendment of education records, with rights transferring to the eligible student under the applicable rule. [FERPA-02]

A parent-conference portfolio is not automatically the complete response to a records-access request, and a conference participant is not automatically entitled to every internal note or record discovered by Vitrine. The system must distinguish:

- a purpose-limited conference edition;
- formal record-access workflow outside Vitrine;
- student-controlled showcase sharing;
- records involving multiple students; and
- internal preparation material.

### 3.4 Consent and external disclosure

When consent is the disclosure basis, authoritative federal guidance states that it must be signed and dated and identify the records, disclosure purpose, and recipient or recipient class. [FERPA-03]

Later design should be able to reference or record:

- consent authority and rights holder;
- exact records or portfolio edition covered;
- named audience or recipient class;
- purpose;
- signature and date;
- expiration or withdrawal policy;
- restrictions on redisclosure;
- whether the consent document itself is retained elsewhere; and
- which future editions are not covered.

A consent for one internal conference does not automatically authorize a public showcase, and a public-edition approval should not silently apply to a later edition containing different artifacts.

### 3.5 Disclosure records

FERPA generally requires a record of requests for and disclosures of personally identifiable information from education records, subject to listed exceptions, and the disclosure record is maintained as long as the education records are maintained. [FERPA-06]

Vitrine should not assume that every view or export is a federally recordable disclosure, but it should preserve enough event information for institutional policy to determine and produce the required record. Potential fields include:

- actor and recipient;
- subject;
- records or issued snapshot disclosed;
- purpose and legitimate interest;
- legal/policy basis;
- date and channel;
- downstream recipients when applicable;
- exception or reason no disclosure record was required; and
- authoritative disclosure-log reference.

### 3.6 Multi-student and group artifacts

An artifact can relate to more than one student. Photos, videos, peer feedback, collaborative writing, and Concord group artifacts may create overlapping education-record and authorship interests. FERPA guidance treats access and redaction as fact-specific and does not support simply assigning the whole artifact to each student. [FERPA-09]

Vitrine should therefore preserve:

- authoritative artifact author or group identity;
- each portfolio subject's explicit relationship to the artifact;
- whether individual contribution is established by an authoritative record or only by annotation;
- other identifiable students;
- redaction or constrained-view decision;
- collaborator-display permission; and
- a warning that inclusion does not itself prove individual proficiency.

### 3.7 De-identification and indirect identifiers

Removing names is not sufficient. FERPA de-identification requires a reasonable determination that a student's identity is not personally identifiable through direct or indirect information, considering other reasonably available information. [FERPA-07]

A future public or research-oriented Vitrine export needs a documented de-identification decision rather than a mechanical “remove name” option. Small cohorts, unique projects, filenames, embedded metadata, teacher comments, dates, images, voices, school identifiers, and provenance can re-identify a student.

### 3.8 Directory information is not a universal publication license

Directory-information disclosure depends on institutional designation, annual notice, any purpose limitation adopted by the institution, and the parent's or eligible student's opportunity to opt out. [FERPA-08]

Vitrine should not infer public-share permission from a field being commonly considered directory information. The institution's current notice and opt-out status must govern.

### 3.9 Contractors and local-first deployment

A contractor or service provider may qualify as a school official only under specified conditions involving institutional function, direct control, purpose-limited use/redisclosure, and the institution's annual notice. [FERPA-11]

Vitrine's local-first architecture can reduce unnecessary transfer, but “local-first” does not by itself establish lawful access or contractor status. Later deployment documentation should identify:

- data controller/custodian;
- hosting and processing locations;
- support-access boundaries;
- telemetry and update behavior;
- encryption and key custody;
- backup and recovery locations;
- vendor/contractor role; and
- deletion and return obligations.

### 3.10 Sole-possession notes

Teacher notes are not automatically outside FERPA. The sole-possession exclusion is narrow and applies to personal memory aids not accessible or revealed to others except a temporary substitute. [FERPA-10]

If Vitrine stores, synchronizes, shares, searches, exports, or exposes a note to another actor, the institution should not assume it remains a sole-possession note. Later design should distinguish private draft annotation from formal review, family-shareable summary, and institutional record without making a legal classification automatically.

## 4. Sensitive and special-category records

Portia behavior/intervention records, disability and accommodation details, multilingual-learner status, homelessness information, disciplinary records, health information, and assessment-security material may require stronger restrictions than ordinary student work.

Foundation rules should be:

- no automatic Portia inclusion;
- no automatic candidate exposure merely because an intervention publication exists;
- profile- and purpose-specific opt-in;
- minimum-necessary projection;
- explicit authorized actor and audience;
- separate sensitive-data classification;
- redaction/omission support;
- source and copied-artifact access controls; and
- no leakage through search results, counts, filenames, logs, thumbnails, or generated indexes.

A later policy system may need deny-by-default handling for designated source classes.

## 5. Records retention, disposition, and auditability

### 5.1 No universal retention period

Retention applies to record classes and institutional functions, not to the generic word “portfolio.” New Jersey, for example, distinguishes mandated student records retained for 100 years from permitted student records retained for seven years after graduation, while NJ regulation separately requires accurate Statewide-assessment performance records for 100 years. [NJ-REG-01] [NJ-RET-02]

That does not prove that every Vitrine object belongs to either class. The responsible records officer must classify:

- mutable working portfolio;
- rejected candidate list;
- annotations and reflections;
- conference checkpoint;
- issued family edition;
- public showcase edition;
- regulated evidence snapshot;
- external submission package;
- receipt and outcome letter;
- access/disclosure log;
- source cache; and
- backup copy.

### 5.2 Minimum retention versus disposal authority

Official schedules specify minimum retention and disposition authority. They do not require Vitrine to destroy a record autonomously at the first eligible date. Current New Jersey records guidance directs agencies to approved schedules and Artemis, and disposition may require institutional authorization or be suspended by audit, litigation, investigation, or legal hold. [NJ-RET-01]

Later design should support:

- schedule/profile identifier and version;
- record class and classifier;
- retention trigger date;
- minimum retention end;
- permanent/indefinite status where applicable;
- hold status and authority;
- disposition eligibility finding;
- approval and disposition event;
- preservation of a non-sensitive tombstone/audit reference when policy permits; and
- prohibition on deleting authoritative producer or Core records from Vitrine.

### 5.3 Mutable working state versus immutable issued state

Working portfolios may change. Issued snapshots, external submissions, receipts, and recorded outcomes must remain exact. A change to source content, profile rules, authorization, selection, or annotation should not silently rewrite what was previously issued.

Corrections should create a new immutable object linked to the prior one through correction, replacement, withdrawal, or supersession metadata. Audit history should explain:

- what changed;
- who authorized it;
- why;
- which source/profile versions changed;
- whether the old edition remains accessible; and
- which edition is operationally current.

### 5.4 Source withdrawal and retention conflict

A producer record may be withdrawn or become unavailable after inclusion. Vitrine must distinguish:

- current source availability;
- authority to access the live source;
- exact bytes copied into an already issued snapshot;
- policy requiring continued retention of the issued record;
- policy requiring future suppression or withdrawal; and
- inability to regenerate the snapshot.

Source withdrawal must not silently erase an issued regulated record that the institution must retain, but continued audience access to that record may need to change.

### 5.5 Audit and staff transition

Regulated workflows need durable retrieval independent of one teacher's account or workstation. Later design should capture institutional custody, responsible office, case/profile identity, indexable subject identity, issue/submission dates, checksums, approval chain, and current status. Local-first must include documented backup, restore, migration, and staff-transition procedures.

## 6. Accessibility and accommodation constraints

### 6.1 Digital accessibility baseline

The U.S. Department of Justice Title II rule establishes WCAG 2.1 Level AA as the technical standard for covered state and local government web content and mobile apps. Following the April 2026 interim extension, the cited federal guidance lists compliance dates of April 26, 2027 for governments serving 50,000 or more persons and April 26, 2028 for smaller governments and special district governments. School districts are not automatically treated as special district governments; the applicable city or county population method is used. [ADA-01] [ADA-03]

Applicability to a specific deployment and artifact should be confirmed by the institution. Vitrine should nevertheless treat accessible design as a foundation requirement rather than waiting for a deadline.

### 6.2 Product and export implications

Later architecture and implementation should support:

- semantic headings, lists, tables, landmarks, and reading order;
- full keyboard operation and visible focus;
- labeled controls and meaningful error messages;
- screen-reader-compatible status and validation output;
- sufficient contrast without relying on color alone;
- text alternatives for meaningful images;
- captions and transcripts for audio/video;
- scalable text and responsive layout;
- accessible authentication and sharing flows;
- tagged and properly structured PDFs where PDF is issued;
- accessible HTML as a preferred or parallel representation;
- accessible spreadsheets or alternate summaries where a spreadsheet is required;
- language metadata and pronunciation considerations;
- non-pointer alternatives for ordering/curation; and
- an accessibility-conformance review tied to each renderer/version.

### 6.3 Exceptions do not justify inaccessible default output

The DOJ guide describes limited exceptions, including certain archived content, preexisting documents, and individualized password-protected conventional documents, but also maintains effective-communication obligations. Content supplied through contractors or vendors is not automatically exempt. [ADA-02]

Vitrine should not build an “exception” toggle as a substitute for accessible output. A profile may record an institutionally approved exception determination, but the system should still support an accessible alternative and preserve who made the determination.

### 6.4 Individual accommodations and language access

Accessibility of the product is distinct from accommodations used to create or evaluate an artifact. A regulated profile may require:

- IEP or Section 504 accommodations;
- ASL interpretation, video, and transcription;
- translated prompts and responses;
- preservation of original and translated/transcribed versions;
- alternate input modality;
- extended time or other administration conditions; and
- evidence that required accommodations were provided. [NJ-SP-01] [NJ-ELA-01] [NJ-MATH-01]

The portfolio should store only the minimum accommodation detail needed for the authorized purpose and should prevent sensitive details from leaking into general editions.

## 7. Intellectual-property and permitted-use constraints

### 7.1 Possession is not ownership

Federal copyright law generally vests initial ownership in the author and distinguishes copyright ownership from ownership of the physical or digital copy. [COPY-01]

Vitrine should not assume that a school may publicly reproduce every student artifact merely because it maintains the education record, nor assume that the student owns every component of a submitted artifact. Relevant rights may involve:

- student author;
- collaborators or joint authors;
- teacher-created prompts or feedback;
- district or vendor license terms;
- third-party images, texts, music, video, datasets, or code;
- assessment-security restrictions; and
- contractual publication consent.

### 7.2 Educational use is not automatic fair use

Teaching and scholarship are listed as possible fair-use purposes, but fair use requires case-specific consideration of all four statutory factors. There is no fixed safe word count or percentage. [COPY-02] [COPY-03]

An internal instructional portfolio and a public showcase may have different rights analyses. Later design should support:

- rights holder or claimed author;
- rights basis: author permission, license, public domain, fair-use determination, institutional policy, unknown;
- permitted audience and uses;
- attribution requirement;
- expiration/withdrawal condition;
- embedded third-party content finding;
- restricted or secure assessment-content flag; and
- alternate representation or omission.

Vitrine should report an unresolved rights issue rather than make a legal fair-use conclusion.

### 7.3 Public display and derivative representations

Public portfolio publication may implicate reproduction, distribution, public display/performance, and derivative-work questions. [COPY-04]

Generated thumbnails, excerpts, translations, transcriptions, previews, PDF conversions, and offline packages are not legally neutral merely because they are technically convenient. Profiles and renderers should preserve rights metadata and permit content to be linked, summarized, redacted, or omitted instead of copied.

### 7.4 Assessment content

New Jersey's Class of 2026 appeal guides prohibit using actual released/practice assessment items as appeal evidence even though those materials may be used as design examples. [NJ-ELA-01] [NJ-MATH-01]

A regulated profile may therefore require task-origin review, secure-content controls, and exclusion from general showcase exports. Vitrine should not index or preview prohibited assessment material beyond what authorized local workflow requires.

## 8. Local and institutional policy variables

The following cannot be universalized:

- identity provider and authoritative student identifiers;
- cross-class/cross-year identity-link approval;
- school and district code mappings;
- staff roles and separation of duties;
- legitimate-educational-interest definitions;
- parent/guardian and eligible-student access procedures;
- consent and publication forms;
- public-web publication policy;
- records classification and retention;
- backup, disaster recovery, migration, and staff transition;
- local CRT design, scoring, moderation, and approval;
- translation/transcription process;
- accessibility review and exception approval;
- artifact ownership and license policy;
- external submission authority;
- incident response and breach notification;
- correction, withdrawal, and appeal processes; and
- approved storage and export channels.

These should enter Vitrine through explicit institutional configuration, versioned profile overlays, or external authorization services. They should not be inferred from names, filenames, course rosters, or common practice.

## 9. Responsibility and unresolved-decision matrix

| Constraint | Likely Vitrine responsibility | External/institutional responsibility | Unresolved decision for later tickets |
| --- | --- | --- | --- |
| Candidate discovery | Query Core and producer contracts only within authorized scope; preserve source identity | Core/producer authority and institutional identity/access policy | Where authorization is evaluated and how denials are represented |
| Education-record classification | Store classification/status metadata and enforce configured handling | Records custodian, counsel, policy owner | Whether classification is per object, artifact family, profile, or repository path |
| Legitimate educational interest | Require actor/purpose context; apply configured policy; audit sensitive access | Institution defines roles/interests and authenticates users | Policy engine boundary and offline authorization behavior |
| Consent | Bind an issued edition to a referenced consent basis | Institution obtains/verifies valid consent | Whether Vitrine stores consent bytes or only authoritative references |
| External disclosure | Produce minimum-necessary audience-specific snapshot and event record | Authorized human approves channel/recipient/legal basis | Disclosure-log integration and exception handling |
| Multi-student artifact | Preserve relationships; support redaction/limited view; avoid inferred ownership | Institution decides permitted access/disclosure | Granularity of redaction and collaborator permissions |
| De-identification | Provide tools/findings and preserve decision provenance | Authorized institutional reviewer makes determination | Whether public export can proceed with unresolved indirect identifiers |
| Sensitive Portia records | Deny automatic inclusion; require explicit opt-in and strict projection | Institution defines eligible cases and actors | Whether Vitrine foundation supports Portia candidates at all |
| Working-state mutation | Preserve selection/replacement history | Curator/reviewer follows profile | Event model and draft garbage-collection policy |
| Issued-snapshot immutability | Copy/render exact bytes, hash, timestamp, profile and audience | Issuer approves issuance | Package format, signature, and verification method |
| Retention | Store schedule reference, trigger, hold, and disposition state | Records officer classifies and authorizes disposition | Which Vitrine objects are official records and where authoritative custody resides |
| Source withdrawal | Surface current unavailability while preserving issued record under policy | Producer/Core controls current source; institution controls retained snapshot access | Reconciliation and reissue behavior |
| Accessibility | Generate accessible UI/exports; preserve renderer conformance data | Institution validates deployment and provides effective communication | Supported formats, audit standard, and exception workflow |
| Individual accommodations | Preserve minimum necessary requirement/evidence relationships | IEP/504 team and authorized staff determine/provide accommodations | Sensitive-data boundary and proof-of-provision representation |
| Translation/transcription | Link original and derivative exactly; preserve language and provenance | Institution selects qualified process and verifies accuracy | Required metadata and reviewer roles |
| Copyright/rights | Preserve rights findings, attribution, audience restrictions, omission | Rights holder/institution/counsel supplies permission or determination | Rights vocabulary and behavior for unknown status |
| Secure assessment content | Support restricted flags, no-preview/no-export projections | Assessment authority defines security rules | Whether source bytes can ever enter a Vitrine snapshot |
| Regulatory completeness | Evaluate versioned requirements and report pass/fail/unknown findings | Authorized staff reviews and attests | Rule-expression language and human override model |
| External submission | Preserve approved package, digest, event, and receipt reference | Authorized coordinator submits through official system | Whether any future direct integration is in scope |
| External outcome | Record exact authority/source and structured result | External authority issues decision | Outcome vocabulary and correction/appeal linkage |
| Retention/disposition | Prevent silent deletion and preserve audit events | Institution authorizes disposition/hold release | Backup deletion and cryptographic erasure behavior |

## 10. Failure states that must remain explicit

Later Vitrine behavior should distinguish at least:

- source not found;
- source withdrawn;
- producer version unsupported;
- artifact missing or corrupt;
- checksum mismatch;
- actor not authorized;
- disclosure basis absent;
- rights status unknown;
- artifact contains another student's information;
- required redaction unresolved;
- profile source expired or superseded;
- restricted template not validated;
- eligibility evidence missing;
- requirement failed;
- requirement unknown;
- human review pending;
- approval denied;
- snapshot generation failed;
- accessible alternative missing;
- external submission not attempted;
- submitted but receipt missing;
- corrected/resubmitted;
- external outcome pending;
- record on hold; and
- disposition not authorized.

“Not found,” “not authorized,” “not applicable,” “failed,” and “unknown” are not interchangeable.

## 11. Architecture inputs for later tickets

This research supports later definition of:

1. explicit subject, actor, role, purpose, audience, and institutional context;
2. authorization separate from Core discovery and producer compatibility;
3. candidate, selection, requirement, finding, review, approval, snapshot, disclosure, submission, receipt, and outcome records;
4. audience-specific projections with omission/redaction reasons;
5. source, profile, renderer, and copied-byte version/digest provenance;
6. deny-by-default handling for sensitive source classes;
7. multi-student and group-artifact relationships without inferred ownership;
8. accessible rendering and alternate-representation contracts;
9. rights and permission metadata without automated legal conclusions;
10. records classification, retention, hold, disposition, and audit metadata;
11. immutable issued snapshots and explicit correction/supersession; and
12. policy/profile extension points instead of jurisdictional hard-coding.

## 12. Questions requiring authorized policy or counsel input

- Which Vitrine objects are official education records in a given deployment?
- Which role definitions satisfy the institution's legitimate-educational-interest policy?
- What disclosures require consent, and which require a disclosure record?
- How should parent access be handled for artifacts containing multiple students?
- What local forms authorize internal, limited external, and public showcase editions?
- What record schedule applies to each working and issued artifact family?
- May an issued snapshot retain copied source bytes after the producer record is withdrawn?
- What rights basis permits copying third-party content into each audience edition?
- Which assessment materials must be link-only, no-preview, or excluded?
- What accessibility conformance review is required for each renderer and document type?
- What restricted NJDOE artifacts must be validated before activating an NJ profile?
- Which external submission and outcome data may be copied into Vitrine?
- What incident-response, legal-hold, transfer, and end-of-service procedures apply?

## 13. Conclusion

Vitrine's compliance posture must be built around explicit authority, purpose limitation, exact provenance, human responsibility, audience-specific issuance, and durable uncertainty. It should help institutions perform and audit their workflows without claiming legal judgment or external authority that belongs elsewhere.
