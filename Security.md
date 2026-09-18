# Security and Student Data

Vitrine is pre-1.0 local-first educational software. It is not a hosted service,
legal-compliance certification, production institutional authorization system, or
external delivery service.

## Student data

Do not commit, publish, attach, or use real student names, identifiers, work, scores,
feedback, signatures, disability information, disciplinary information, or other
education records in repository, test, example, screenshot, log, release, or
qualification evidence. Tests and release qualification must use synthetic data.

## v0.3.0 producer access

Vitrine v0.3.0 can consume released ScoreForm 0.11.0, Quillan 0.10.0, and Concord
0.3.0 evidence through Core-governed Publication discovery and the producers'
documented public reader/Artifact boundaries. Those live integrations do not make
the producer packages unconditional Vitrine runtime dependencies.

Protected source content is not read merely because a Publication exists. The accepted
sequence requires compatibility and explicit source-read authorization before Core
verifies and supplies immutable manifest bytes to a public producer reader.

For Quillan and Concord:

```text
source-read authorization != producer Artifact authorization
```

Copied student-work/feedback/Artifact bytes require a separate producer Artifact
authorization. Denied or unresolved authorization fails closed. Vitrine must not
reconstruct producer-native paths or use producer-private storage APIs. ScoreForm
Snapshot materialization remains `reference_only`.

Development fixture adapters remain explicit opt-in test infrastructure and must not
masquerade as live producer integrations.

## Curation, Snapshot, and disclosure authority

These are separate boundaries:

```text
Candidate eligibility != Selection authority
actor attribution != authorization
Selection != Snapshot build authority
Snapshot build authority != disclosure authorization
Audience Context != recipient identity / relationship / consent
local Export != external delivery
```

Vitrine may create and verify a purpose-specific local immutable Edition and local
directory Export after the accepted authority checks. Vitrine v0.3.0 does **not**
implement recipient/guardian relationship verification, consent management,
production disclosure authorization, secure delivery, public hosting, or external
submission.

A `directory_package` Export must not be described as sent, shared, submitted,
delivered, published, or authorized for disclosure merely because it exists.

## Diagnostic and attention privacy

Normal teacher, diagnostic, attention, and suite-operation output must remain bounded
and minimum-necessary. It must not emit raw manifest bodies, student response/work
bodies, feedback bodies, answer keys, teacher-private notes, moderation rationale,
authorization-provider prose, producer-native paths, credentials, tokens, or absolute
workspace paths.

Suppressed Candidate state must not leak through rows, counts, facets, hidden-result
messages, producer labels, attention totals, or placeholder records.

Suite-level attention receives only Vitrine's bounded projection. Class-scoped
Vitrine attention remains unavailable when Portfolio-wide meaning cannot be safely
attributed to one class.

## Backup and custody boundary

Suite backup/restore may copy workspace bytes, but:

```text
suite backup != Snapshot Export
suite restore != Vitrine repair
restored bytes != permission to reinterpret or redisclose Portfolio content
```

Sealed Snapshot custody remains Vitrine-owned and independently verifiable. Backup
or restored storage does not create new disclosure authority.

## Reporting concerns

Report suspected vulnerabilities privately to the repository maintainer. Do not
include real education records, credentials, access tokens, private configuration,
producer-native paths, or absolute workstation paths in a public report.
