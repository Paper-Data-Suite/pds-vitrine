# Representative Regulated Portfolio and Compliance Examples

- **Issue:** #11, “Define regulated portfolio/compliance profiles”
- **Example date:** 2026-08-05
- **Status:** Synthetic foundation examples paired with proposed ADR 0009
- **Applies to:** `pds-vitrine` v0.1.0 conceptual design

## Purpose

These examples exercise the contracts in [regulated-portfolio-compliance-profiles.md](../design/regulated-portfolio-compliance-profiles.md).

They are intentionally synthetic.

They do not:

- contain real student identities;
- reproduce restricted New Jersey forms or portal content;
- establish an operational New Jersey Profile;
- determine graduation eligibility;
- certify compliance;
- create official attestations;
- submit to an external authority;
- or represent actual external outcomes.

## Synthetic conventions

All identifiers are opaque and invented:

```text
profile family: reg-family-demo
profile series: reg-profile-standard / reg-profile-streamlined
Profile revisions: 1, 2, 3
cases: case-001 through case-999
subjects: subject-a through subject-z
components: ela / mathematics
schools: school-alpha / school-beta
batches: batch-001 through batch-999
```

All scores, documents, dates, organizations, and outcomes are fictional.

The New Jersey-like examples use only public structural concepts and synthetic data. They do not reproduce official templates, field names, district codes, student identifiers, or signature text.

## Record shorthand

```text
AS = Authority Source
CASE = Regulated Portfolio Case
COMP = Case Component
PATH = Pathway Selection
ELIG = Eligibility Finding
CHK = Checklist Item Finding
REC = Supporting Record Instance
MISS = Missing or Defective Record Finding
ATT = Attestation Record
AV = Attestation Verification
DL = Deadline Instance
APP = Regulated Approval Decision
READY = Submission Readiness Finding
BATCH = Submission Batch
MEM = Case-to-Batch Membership
ROW = Generated Submission Projection
SNAP = Snapshot Edition
EXP = Export Artifact
SUB = Submission
RCPT = Receipt
OUT = External Outcome Reference
```

## Authority sources and Profile activation

### 1. Research-only Profile cannot activate

**Setup**

A synthetic `nj_gap_2026_reference` Profile contains public Class of 2026 guidance but lacks verified restricted Homeroom templates and local approval.

**Expected behavior**

- Authority Source Set marks required restricted entries `unknown`.
- Profile activation is blocked.
- The Profile remains usable only for documentation and test fixtures.

**Invariant exercised:** Authority and activation remain exact, attributable, and revisioned.

### 2. Operational activation after complete review

**Setup**

Authorized institutional reviewers verify public guidance, restricted forms, field definitions, local policy, actors, deadlines, and retention references.

**Expected behavior**

- A new operational Profile revision is activated explicitly.
- The research-only revision remains unchanged.
- Activation does not create any student case.

**Invariant exercised:** Authority and activation remain exact, attributable, and revisioned.

### 3. Public guidance becomes stale

**Setup**

A public ELA guide is replaced after Profile revision 1 was activated.

**Expected behavior**

- The source entry becomes `superseded` for current use but remains `verified_historical` for replay.
- Current operations require source revalidation and a successor Profile revision.
- Historical cases remain bound to revision 1.

**Invariant exercised:** Authority and activation remain exact, attributable, and revisioned.

### 4. Restricted source unavailable

**Setup**

The authorized reviewer cannot access the current data spreadsheet field definitions.

**Expected behavior**

- The source entry is `unavailable`.
- Profile activation remains blocked because exact field rules control external data generation.
- No guessed column definitions are introduced.

**Invariant exercised:** Authority and activation remain exact, attributable, and revisioned.

### 5. Public and restricted sources conflict

**Setup**

A public FAQ and restricted field-definition document appear to disagree about a score representation.

**Expected behavior**

- The Authority Source Set records `conflicting`.
- An authorized review resolves the conflict or blocks activation.
- Vitrine does not choose the easier interpretation.

**Invariant exercised:** Authority and activation remain exact, attributable, and revisioned.

### 6. Local overlay adds earlier deadline

**Setup**

The state Profile uses May 1 as a recommended submission date; the institution adds April 15 as an internal evidence-complete deadline.

**Expected behavior**

- Both rules remain separately attributable.
- The effective Profile preserves the state rule and local overlay.
- The local overlay does not rewrite the external deadline.

**Invariant exercised:** Authority and activation remain exact, attributable, and revisioned.

### 7. Local overlay attempts to weaken state requirement

**Setup**

A local overlay removes a required state attestation.

**Expected behavior**

- Composition validation reports a conflict.
- The effective Profile cannot activate.
- The state requirement remains unchanged.

**Invariant exercised:** Authority and activation remain exact, attributable, and revisioned.

### 8. Class of 2026 and Class of 2027 coexist

**Setup**

Two synthetic cases are active during an overlap period.

**Expected behavior**

- Each case binds its own cohort-specific Profile revision.
- The Class of 2026 rules do not flow into the Class of 2027 case.
- Dashboards may group them but cannot merge their policy state.

**Invariant exercised:** Authority and activation remain exact, attributable, and revisioned.

### 9. Wrong cohort Profile assignment

**Setup**

A Class of 2027 subject is opened under the Class of 2026 reference Profile.

**Expected behavior**

- The case receives `regulated_case_profile_mismatch`.
- The erroneous case is invalidated or explicitly migrated.
- The original case remains historical.

**Invariant exercised:** Authority and activation remain exact, attributable, and revisioned.

## Cases, components, pathways, and eligibility

### 10. Case opens under exact Profile revision

**Setup**

A synthetic subject enters a regulated workflow under Profile revision 3.

**Expected behavior**

- The Regulated Portfolio Case stores the exact Profile Binding.
- Later Profile revision 4 does not alter the case.
- Migration is a separate operation.

**Invariant exercised:** Case, component, pathway, and eligibility state remain separate.

### 11. ELA component only

**Setup**

The subject already met mathematics through another pathway but requires an ELA Portfolio Appeal.

**Expected behavior**

- Only the ELA Case Component is applicable.
- Mathematics is represented through an external-pathway finding, not a regulated component checklist.
- Case-wide completion does not imply mathematics was evaluated by Vitrine.

**Invariant exercised:** Case, component, pathway, and eligibility state remain separate.

### 12. Mathematics component only

**Setup**

The subject already met ELA but requires a mathematics Portfolio Appeal.

**Expected behavior**

- Only mathematics receives regulated pathway, evidence, readiness, submission, and outcome records.
- ELA remains outside this regulated component workflow.

**Invariant exercised:** Case, component, pathway, and eligibility state remain separate.

### 13. Both components use standard pathways

**Setup**

The subject needs regulated evidence for both ELA and mathematics.

**Expected behavior**

- Two independent components use explicit standard Pathway Selections.
- Each has its own checklist and readiness.
- One component may proceed while the other remains blocked.

**Invariant exercised:** Case, component, pathway, and eligibility state remain separate.

### 14. Both components use streamlined pathways

**Setup**

The subject has qualifying synthetic ASVAB evidence for both components.

**Expected behavior**

- Each component selects the streamlined pathway explicitly.
- The qualifying evidence is referenced exactly.
- Reduced task quantities come from the Profile, not inference.

**Invariant exercised:** Case, component, pathway, and eligibility state remain separate.

### 15. Only ELA qualifies for streamlined pathway

**Setup**

The Profile and institutional decision allow streamlined ELA, while mathematics remains standard.

**Expected behavior**

- ELA and mathematics retain different Pathway Selections.
- No case-wide pathway flag is used.
- Task requirements are evaluated by component.

**Invariant exercised:** Case, component, pathway, and eligibility state remain separate.

### 16. Qualifying evidence missing

**Setup**

A streamlined Pathway Selection is requested without the required external assessment record.

**Expected behavior**

- Eligibility is `indeterminate` or `not_eligible` according to the exact rule.
- Pathway activation is blocked.
- Vitrine does not silently fall back or fabricate evidence.

**Invariant exercised:** Case, component, pathway, and eligibility state remain separate.

### 17. Qualifying score below threshold

**Setup**

A synthetic authoritative score exists but is below the exact Profile threshold.

**Expected behavior**

- Eligibility is `not_eligible`.
- The streamlined pathway cannot become active.
- The source score remains preserved without reinterpretation.

**Invariant exercised:** Case, component, pathway, and eligibility state remain separate.

### 18. Eligibility expires

**Setup**

A pathway rule requires evidence valid within a defined period, and the evidence has expired.

**Expected behavior**

- The Eligibility Finding is `expired`.
- Prior historical eligibility remains visible.
- A new finding requires current evidence.

**Invariant exercised:** Case, component, pathway, and eligibility state remain separate.

### 19. Pathway changes before submission

**Setup**

A component initially uses standard requirements, then an authorized reviewer selects streamlined after qualifying evidence arrives.

**Expected behavior**

- A successor Pathway Selection supersedes the prior selection.
- Checklist applicability is reevaluated.
- Prior findings remain historical.

**Invariant exercised:** Case, component, pathway, and eligibility state remain separate.

### 20. Automatic easiest-path attempt

**Setup**

A workflow tries to select the pathway with fewer missing items.

**Expected behavior**

- The action is rejected.
- Pathway selection requires explicit actor authority and eligibility evidence.
- Derived readiness cannot create policy choice.

**Invariant exercised:** Case, component, pathway, and eligibility state remain separate.

## Checklists and supporting records

### 21. Checklist definition revision

**Setup**

A successor Profile revision changes one checklist item's evidence rule materially.

**Expected behavior**

- The changed item receives a new stable item ID or explicit replacement relationship.
- Old findings remain bound to the prior checklist revision.
- Cases do not silently inherit the new item.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

### 22. Checklist item satisfied with exact evidence

**Setup**

A required transcript record is present, current, verified, and matches the case.

**Expected behavior**

- Record presence is `present`.
- Record validation is `verified`.
- Requirement result may be `satisfied` with evaluator provenance.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

### 23. Checked box without evidence

**Setup**

A user marks a required checklist item complete but supplies no record or authority basis.

**Expected behavior**

- No canonical satisfied finding is created.
- The UI checkbox remains nonauthoritative.
- Readiness stays blocked.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

### 24. Present but stale transcript

**Setup**

A transcript exists but predates the Profile's recency rule.

**Expected behavior**

- Presence is `present`.
- Validation is `stale`.
- Requirement result is `not_satisfied`.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

### 25. Present but wrong subject

**Setup**

A valid transcript belongs to another synthetic subject.

**Expected behavior**

- Validation is `mismatched`.
- The record cannot satisfy the requirement.
- The incorrect association is preserved only as a rejected finding.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

### 26. Present but wrong component

**Setup**

A mathematics cover sheet is attached to an ELA requirement.

**Expected behavior**

- Validation is `mismatched`.
- ELA remains unsatisfied.
- The math record may be evaluated only under the correct component.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

### 27. Present but wrong cohort form

**Setup**

A form uses a prior cohort's template revision.

**Expected behavior**

- Validation is `record_wrong_cohort` or `record_wrong_revision`.
- The record remains present but not satisfying.
- A current form is required.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

### 28. Task exists without cover sheet

**Setup**

A CRT and response are present, but the required cover sheet is missing.

**Expected behavior**

- The task record may validate independently.
- The cover-sheet checklist item remains `missing` and `not_satisfied`.
- Overall readiness remains blocked if the item is required.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

### 29. Graded response without rubric

**Setup**

A response has a recorded score but no exact rubric reference.

**Expected behavior**

- The response record is present.
- Scoring validation remains `unverified` or `invalid`.
- Vitrine does not treat the score as satisfying the regulated requirement.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

### 30. Valid record still insufficient

**Setup**

A verified document exists but lacks one property required by the Profile.

**Expected behavior**

- Record validation may be `verified` as a document.
- Requirement result remains `not_satisfied`.
- Validity and satisfaction remain separate.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

### 31. Record unavailable

**Setup**

An authoritative external record cannot be retrieved.

**Expected behavior**

- Presence is `unavailable`.
- The finding records the bounded search scope and evaluator.
- Unknown availability is not converted to waived.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

### 32. Record withheld

**Setup**

A custodian confirms that a sensitive record exists but cannot be disclosed to the current reviewer.

**Expected behavior**

- Presence is `withheld`.
- Detailed reasons remain access-controlled.
- The requirement stays unknown or not satisfied according to Profile policy.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

### 33. Suppressed Portia source

**Setup**

A sensitive Portia record might contain relevant context.

**Expected behavior**

- Ordinary discovery reveals no source existence.
- No Supporting Record Instance is created from raw Portia data.
- Only a future exact safe projection may be evaluated.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

### 34. Missing finding later resolved

**Setup**

A required record is initially missing, then a verified replacement arrives.

**Expected behavior**

- The original missing finding remains historical.
- A successor finding references the new record and may become satisfied.
- Readiness is recalculated from the new exact state.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

### 35. Fake placeholder file

**Setup**

A workflow creates a blank PDF named like the missing document.

**Expected behavior**

- The file is rejected as evidence.
- The missing finding remains unresolved.
- Filename and file count do not establish record identity or content.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

### 36. Authorized waiver

**Setup**

The Profile permits a waiver and an authorized actor grants it for one exact requirement and target.

**Expected behavior**

- The Checklist Item Finding is `waived` with an exact waiver Decision.
- The waiver scope and conditions are preserved.
- Other requirements are unaffected.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

### 37. Unauthorized waiver

**Setup**

A teacher attempts to waive a requirement reserved for an institutional administrator.

**Expected behavior**

- The waiver is rejected.
- The requirement remains unsatisfied or unknown.
- The attempted action may be recorded without creating authority.

**Invariant exercised:** Presence, validation, satisfaction, waiver, and history remain distinct.

## Attestations, deadlines, and approvals

### 38. Single-signer attestation

**Setup**

A Profile requires one content-area reviewer attestation.

**Expected behavior**

- The Attestation Record binds exact statement revision, target, signer, role evidence, and time.
- Verification is separate.
- The attestation does not approve submission by itself.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

### 39. Three-signer school assurance complete

**Setup**

A synthetic batch-level assurance requires coordinator, principal, and chief administrator roles.

**Expected behavior**

- Three distinct Attestation Records are verified.
- Separation-of-duties and signer-count rules pass.
- The batch may advance to the approval stage.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

### 40. Three-signer assurance incomplete

**Setup**

Only two required signers have attested.

**Expected behavior**

- The attestation requirement remains incomplete.
- Submission readiness is blocked.
- No partial Boolean `signed=true` is used.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

### 41. Signer role changed before signing

**Setup**

An actor's authoritative role ended before the attestation time.

**Expected behavior**

- Authority verification is rejected or indeterminate.
- The signature does not satisfy the requirement.
- A valid current signer is required.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

### 42. Signature image without authority reference

**Setup**

A PNG of a signature is attached to a document.

**Expected behavior**

- The bytes may be retained as part of a source document.
- Signature verification remains `indeterminate`.
- The image does not prove identity or authority.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

### 43. Attestation target changes

**Setup**

A data spreadsheet changes after signers attested to the prior batch revision.

**Expected behavior**

- Prior attestations remain valid only for the old target.
- The new batch revision triggers reattestation.
- The old signed document remains historical.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

### 44. Recommended and final deadlines

**Setup**

The Profile defines a recommended processing deadline and a later final submission deadline.

**Expected behavior**

- Two independent Deadline Rules and Instances are created.
- Missing the recommended date does not imply missing the final date.
- Each status remains attributable.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

### 45. Local internal deadline

**Setup**

A local overlay defines an evidence-complete date before the state submission date.

**Expected behavior**

- The local deadline is classified `internal_required`.
- The state date remains independently represented.
- A local late finding does not fabricate state denial.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

### 46. Authorized deadline extension

**Setup**

An external authority grants a documented extension for one batch.

**Expected behavior**

- A Deadline Extension references exact authority evidence and scope.
- The Deadline Instance recalculates or records the new deadline.
- Other cases or batches are unaffected.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

### 47. Unverified extension claim

**Setup**

A user enters a later date without authority evidence.

**Expected behavior**

- The extension is rejected or indeterminate.
- The original deadline remains operative.
- The system does not create external authority.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

### 48. Past deadline without external outcome

**Setup**

A final deadline has passed, but no authority decision exists.

**Expected behavior**

- The status is `past_due`.
- No denial outcome is created.
- Institutional follow-up remains separate.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

### 49. Evidence-review approval

**Setup**

An authorized content reviewer approves one exact component checklist state.

**Expected behavior**

- The Approval Decision binds the exact target revision.
- Later evidence changes make the approval stale under Profile rules.
- Approval does not authorize external disclosure.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

### 50. Approval actor unauthorized

**Setup**

A user without the required role attempts school approval.

**Expected behavior**

- The action fails `approval_actor_unauthorized`.
- No Approval Decision is created.
- The attempted request may remain auditable.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

### 51. Approval target becomes stale

**Setup**

A Supporting Record is replaced after approval.

**Expected behavior**

- The prior approval remains historical for the old target.
- A new review is required.
- The current readiness finding becomes blocked or indeterminate.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

### 52. Checklist complete but not approved

**Setup**

All required findings are satisfied, but no institutional approval exists.

**Expected behavior**

- Checklist completion may be complete.
- Submission readiness remains `not_ready` or `conditionally_ready`.
- No approval is inferred.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

### 53. Approved but not authorized for submission

**Setup**

Institutional approval exists, but the exact privacy Disclosure Authorization is missing.

**Expected behavior**

- Submission readiness remains blocked.
- Approval and disclosure authorization remain separate.
- No package is delivered.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

### 54. Case ready, batch not ready

**Setup**

A student component is locally ready, but the school Statement of Assurance is missing.

**Expected behavior**

- Case readiness may be `ready`.
- Batch readiness is `not_ready`.
- Student-level and batch-level requirements remain separate.

**Invariant exercised:** Attestation, verification, deadline, approval, and readiness remain separate.

## Batches, projections, submissions, and outcomes

### 55. School batch contains several cases

**Setup**

A synthetic school submits five component memberships in one batch.

**Expected behavior**

- One Submission Batch references five exact memberships.
- Each membership preserves case and component provenance.
- The batch is not treated as one student case.

**Invariant exercised:** Case, batch, projection, Submission, Receipt, and Outcome remain distinct.

### 56. Single case in multiple rolling submissions

**Setup**

ELA is submitted in January and mathematics is added in March.

**Expected behavior**

- The case has two exact batch memberships or submissions.
- Earlier ELA submission history remains unchanged.
- Mathematics membership references the later exact batch.

**Invariant exercised:** Case, batch, projection, Submission, Receipt, and Outcome remain distinct.

### 57. Duplicate membership in one batch

**Setup**

The same case/component is added twice accidentally.

**Expected behavior**

- Validation reports `submission_membership_duplicate`.
- The batch cannot seal until corrected.
- No duplicate external row is generated.

**Invariant exercised:** Case, batch, projection, Submission, Receipt, and Outcome remain distinct.

### 58. Generated row with exact provenance

**Setup**

A synthetic spreadsheet row is generated from case and component facts.

**Expected behavior**

- Each value identifies its Profile field rule and source record.
- The row and generated file receive digests.
- The row is not the canonical case.

**Invariant exercised:** Case, batch, projection, Submission, Receipt, and Outcome remain distinct.

### 59. Rubric score where percentage required

**Setup**

A generated field receives a rubric value but the exact field rule requires a whole-number percentage.

**Expected behavior**

- Validation reports `submission_row_invalid`.
- The batch remains not ready.
- No silent conversion is performed.

**Invariant exercised:** Case, batch, projection, Submission, Receipt, and Outcome remain distinct.

### 60. Restricted field-definition version changes

**Setup**

A new restricted spreadsheet definition is verified.

**Expected behavior**

- A successor Profile or batch-rule revision records the exact new version/digest.
- Old generated files remain bound to the old rule.
- Existing submissions are not rewritten.

**Invariant exercised:** Case, batch, projection, Submission, Receipt, and Outcome remain distinct.

### 61. Initial external submission

**Setup**

An approved batch with exact Export Artifacts is handed off.

**Expected behavior**

- An immutable Submission records destination, submitter, artifacts, and time.
- Submission does not create a Receipt.
- The batch and package remain exact.

**Invariant exercised:** Case, batch, projection, Submission, Receipt, and Outcome remain distinct.

### 62. Upload succeeds but no receipt

**Setup**

The portal reports local success, but no receipt is available.

**Expected behavior**

- The Submission remains recorded.
- Receipt status is missing or pending.
- Vitrine does not fabricate confirmation.

**Invariant exercised:** Case, batch, projection, Submission, Receipt, and Outcome remain distinct.

### 63. Receipt without approval

**Setup**

The external system acknowledges receipt.

**Expected behavior**

- A Receipt reference is recorded.
- No substantive approval is inferred.
- External outcome remains pending.

**Invariant exercised:** Case, batch, projection, Submission, Receipt, and Outcome remain distinct.

### 64. Corrected resubmission

**Setup**

A data error is fixed after the first submission.

**Expected behavior**

- New bytes create a new Export Artifact.
- A new Submission links to the prior Submission as a correction.
- Prior bytes and Receipt remain historical.

**Invariant exercised:** Case, batch, projection, Submission, Receipt, and Outcome remain distinct.

### 65. Rolling submission adds new students

**Setup**

The school later submits additional completed cases.

**Expected behavior**

- A new batch revision or new batch is created according to Profile rules.
- Earlier memberships remain unchanged.
- Only completed components enter the new handoff.

**Invariant exercised:** Case, batch, projection, Submission, Receipt, and Outcome remain distinct.

### 66. External returned-for-correction outcome

**Setup**

The authority requests corrected data for one component.

**Expected behavior**

- The raw outcome is preserved.
- The normalized mapping is `returned_for_correction`.
- A later resubmission does not erase the outcome.

**Invariant exercised:** Case, batch, projection, Submission, Receipt, and Outcome remain distinct.

### 67. Partial external approval

**Setup**

ELA is approved while mathematics is denied.

**Expected behavior**

- The outcome references exact affected components.
- Case-level summaries derive mixed status.
- One component's approval does not complete the other.

**Invariant exercised:** Case, batch, projection, Submission, Receipt, and Outcome remain distinct.

### 68. Outcome letter corrected

**Setup**

The authority replaces an earlier outcome letter.

**Expected behavior**

- A successor External Outcome Reference links to the prior one.
- The raw old outcome remains historical.
- Current summaries use the explicit successor.

**Invariant exercised:** Case, batch, projection, Submission, Receipt, and Outcome remain distinct.

### 69. Local checklist complete, external denial

**Setup**

The institution submitted a locally complete package that the external authority denied.

**Expected behavior**

- Local findings remain historically accurate.
- The external denial is recorded separately.
- Vitrine does not rewrite local completion into false.

**Invariant exercised:** Case, batch, projection, Submission, Receipt, and Outcome remain distinct.

## Privacy, producer, retention, and historical behavior

### 70. Source publication withdrawn after issuance

**Setup**

A producer withdraws a source after a regulated Snapshot Edition was issued.

**Expected behavior**

- The historical Snapshot and Submission remain exact.
- Future use is reevaluated under privacy, retention, and source lifecycle policy.
- The issued bytes are not silently removed or refreshed.

**Invariant exercised:** Privacy, producer authority, retention, and historical replay boundaries remain intact.

### 71. Translated response with original retained

**Setup**

A synthetic student responds in another language and an authorized translation is produced.

**Expected behavior**

- Original and translation are separate linked records with language and digest provenance.
- The translation does not replace the original.
- Both are evaluated according to Profile policy.

**Invariant exercised:** Privacy, producer authority, retention, and historical replay boundaries remain intact.

### 72. Translation missing original

**Setup**

Only the translated response is available where the Profile requires both.

**Expected behavior**

- The translation may be present and verified.
- The original-record requirement remains missing.
- Readiness remains blocked.

**Invariant exercised:** Privacy, producer authority, retention, and historical replay boundaries remain intact.

### 73. Accommodation evidence minimized

**Setup**

The regulated workflow needs proof that an accommodation was provided.

**Expected behavior**

- A bounded safe finding references external authority evidence.
- The complete IEP is not copied.
- General audience packages exclude sensitive details.

**Invariant exercised:** Privacy, producer authority, retention, and historical replay boundaries remain intact.

### 74. Excess accommodation detail

**Setup**

A complete sensitive plan is attached unnecessarily.

**Expected behavior**

- Disclosure review rejects or requires a minimum-necessary projection.
- The raw source remains protected.
- Regulated purpose does not override privacy.

**Invariant exercised:** Privacy, producer authority, retention, and historical replay boundaries remain intact.

### 75. ScoreForm result used as bounded evidence

**Setup**

An exact privacy-safe ScoreForm projection supports a Profile requirement.

**Expected behavior**

- The exact attempt/result provenance is preserved.
- Vitrine does not choose the official attempt automatically.
- Secure items and answer keys remain excluded.

**Invariant exercised:** Privacy, producer authority, retention, and historical replay boundaries remain intact.

### 76. Quillan work is relevant but insufficient

**Setup**

A reviewed Quillan response is educationally relevant but lacks the externally required rubric evidence.

**Expected behavior**

- The record may be valid as Quillan work.
- The regulated checklist remains not satisfied.
- Producer review state is not institutional approval.

**Invariant exercised:** Privacy, producer authority, retention, and historical replay boundaries remain intact.

### 77. Concord Group Artifact lacks individual attribution

**Setup**

A collaborative Artifact is proposed for an individual requirement.

**Expected behavior**

- Group Membership alone is insufficient.
- The record remains ineligible or conditional until individual contribution is established.
- Group Score is not converted to an individual result.

**Invariant exercised:** Privacy, producer authority, retention, and historical replay boundaries remain intact.

### 78. Concord individual contribution verified

**Setup**

The producer projection establishes authorship and individual contribution accepted by the Profile.

**Expected behavior**

- The Artifact may become a Supporting Record Instance.
- Privacy and external-program rules still apply.
- A Checklist Finding separately evaluates satisfaction.

**Invariant exercised:** Privacy, producer authority, retention, and historical replay boundaries remain intact.

### 79. Meridian report projection

**Setup**

A future public Meridian report is referenced as supporting documentation.

**Expected behavior**

- The exact report identity and digest are preserved.
- Vitrine does not inspect Meridian's private evidence inventory.
- The report does not itself establish external acceptance.

**Invariant exercised:** Privacy, producer authority, retention, and historical replay boundaries remain intact.

### 80. Staff transition

**Setup**

The assigned coordinator leaves during an active case.

**Expected behavior**

- A transition event records successor assignment.
- Custody references and retrieval verification remain institution-owned.
- The case is not tied solely to the departed account.

**Invariant exercised:** Privacy, producer authority, retention, and historical replay boundaries remain intact.

### 81. Retention classification unresolved

**Setup**

The institution has not classified a generated working report.

**Expected behavior**

- Retention state remains unresolved.
- No autonomous deletion occurs.
- The responsible records authority must decide.

**Invariant exercised:** Privacy, producer authority, retention, and historical replay boundaries remain intact.

### 82. Derived dashboard deleted

**Setup**

The local case dashboard is lost.

**Expected behavior**

- Canonical records rebuild the dashboard.
- No checklist, approval, submission, or outcome changes.
- Derived state remains nonauthoritative.

**Invariant exercised:** Privacy, producer authority, retention, and historical replay boundaries remain intact.

### 83. Historical replay

**Setup**

An auditor reviews a prior submitted package years later.

**Expected behavior**

- The exact old Profile revision, Authority Source Set, findings, attestations, approvals, Snapshot Edition, Export Artifacts, Submission, Receipt, and Outcome are resolved.
- Current policy is not substituted.
- Replay does not grant access without current authorization.

**Invariant exercised:** Privacy, producer authority, retention, and historical replay boundaries remain intact.

## Coverage summary

The scenarios cover:

- research-only and operational Profile separation;
- source verification, staleness, conflict, and restricted dependencies;
- local overlays;
- cohort changes;
- separate ELA and mathematics components;
- standard and streamlined pathways;
- explicit eligibility;
- checklist revisions;
- present, missing, unavailable, withheld, stale, invalid, and mismatched records;
- waiver authority;
- attestation statement versions, signer counts, roles, and verification;
- recommended, internal, and external deadlines;
- extensions;
- exact-target approvals;
- readiness;
- school-level batches;
- rolling submissions;
- resubmissions;
- generated row provenance;
- exact Snapshot and Export Artifact references;
- receipts and external outcomes;
- partial component outcomes;
- translation and accommodation minimization;
- ScoreForm, Quillan, Concord, Portia, and Meridian boundaries;
- source withdrawal;
- staff transition;
- retention uncertainty;
- derived-view rebuilding;
- and historical replay.

## Example-set invariants

1. Every example is synthetic.
2. Research-only Profiles never become operational by implication.
3. Cases always bind exact Profile revisions.
4. Components remain independently evaluable.
5. Pathway selection remains explicit.
6. Unknown fails closed.
7. Checklist findings remain immutable and evidence-backed.
8. Missing evidence does not create placeholder documents.
9. Attestation, verification, approval, readiness, and outcome remain distinct.
10. Deadlines preserve exact authority and scope.
11. Student cases and school batches remain separate.
12. Changed external bytes create new immutable artifacts and submissions.
13. Receipts and outcomes remain externally grounded.
14. Producer-native authority remains unchanged.
15. Portia suppression remains intact.
16. Historical records remain reproducible.
