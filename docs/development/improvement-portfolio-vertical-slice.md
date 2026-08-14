# Executable improvement Portfolio vertical slice

`python scripts/validate_improvement_portfolio.py` executes the representative
synthetic improvement story through the public runtime services introduced in
issues 30 through 35. It runs in disposable storage and prints no source bodies
or user-specific absolute paths.

## Exact fixture context

The runtime uses Portfolio `portfolio-improvement-syn-001` and Portfolio Subject
`portfolio-subject-syn-001`. Continuity is established by two separate confirmed
`PortfolioSubjectClassLink` records:

| Role | School year | Class | Student |
| --- | --- | --- | --- |
| baseline | `2023-2024` | `class-ela10-syn` | `student-syn-001` |
| later | `2024-2025` | `class-ela11-syn` | `student-syn-001` |

A same-looking roster row has a different local student ID and is never treated
as the Subject. Removing the later class link makes the later work and feedback
ineligible; names and repeated labels do not bridge that missing identity link.

The Subject and both class-qualified links are created through the #30 Subject
application services, which preserve exact roster resolution, display snapshots,
and attributable identity decisions. The Profile Family and Revision are created,
activated, and bound through the #31 Profile application services rather than by
constructing activation or Binding records directly.

The activated runtime Profile is `profile-improvement-rev-001` revision 1, bound
by `profile-binding-improvement-001`. Its required `baseline` section accepts one
student-work Placement. Its required `later_work` section accepts the separately
placed later work followed by student-facing feedback. Its required `reflection`
section accepts no producer Placement; instead, exact section-scoped requirement
`improvement-comparison-reflection` requires the student's comparison Reflection.
The Profile and its exact sections determine eligibility; `purpose=improvement`
does not choose evidence.

## Producer fixture and curation

Two canonical Core publications are created for the baseline and later class
contexts. Their runtime-generated Publication IDs are reloaded canonically during
bounded discovery. The byte manifests identify
`vitrine_quillan_fixture`, contract `vitrine_fixture_quillan_manifest_v1`, and
`integration_kind=development_fixture`. They are Vitrine-owned execution support,
not live Quillan contracts or a reader for a Quillan workspace.

Discovery verifies the exact Core-bound manifest bytes before the fixture reader
projects three positive and separate Candidates:

| Source record | Candidate kind | Placement |
| --- | --- | --- |
| `baseline_argument` | `student_work` | `baseline`, ordinal 1 |
| `revised_argument` | `student_work` | `later_work`, ordinal 1 |
| `revised_feedback` | `feedback` | `later_work`, ordinal 2 |

The later fixture also contains private teacher-shaped material. The exact reader
does not project it, so it cannot become a Candidate, Selection, Placement, or
Snapshot Entry. Candidate discovery creates no Selection. Three student
Proposals and three attributable teacher acceptance Decisions create exactly
three active Selections. Each Placement call creates a complete immutable
Arrangement Revision and advances that section's Arrangement pointer explicitly.

The synthetic student actor authors `reflection_1`, revision 1. Its ordered
comparison target is the exact baseline Selection with semantic role `baseline`,
then the exact revised-work Selection with semantic role `later`. The content is
the student's interpretation. Vitrine does not derive an improvement flag,
growth score, Grade, proficiency, or mastery.

Composition revision 1 freezes the three Selections, three Placements, current
baseline/later Arrangement Revisions, exact Profile Binding/Revision, and the
section-scoped Reflection revision in `WorkingPortfolioCompositionInventory`. Its
current pointer is advanced by the generic curation service. Later records cannot
retarget this immutable composition.

Audience Context `audience-imp-student` is the exact student-facing Profile policy
context. It permits `student_work`, `feedback`, and generated `reflection` content
and prohibits `private_teacher_note`. It is not recipient identity, consent,
disclosure authorization, or delivery permission. The local Snapshot authority
gate permits only the disposable build operation.

## Snapshot, Export, and source drift

The validator creates one Series, Build Request, immutable Build Plan, and Build
Attempt. The Plan's deterministic order is:

1. copied `baseline/argument.txt`;
2. copied `later/argument.txt`;
3. copied `later/student-feedback.txt`;
4. generated `reflection/student-comparison.md` in the Profile's `reflection`
   section from `reflection_1` revision 1.

All four items finish as successful Materializations and Entries. There are no
Omissions. Copied source and staged output hashes are independently recorded;
the Reflection renderer freezes its identity, contract, configuration digest,
template digest, exact Reflection revision, and Composition revision. The
validator reproduces the deterministic internal Manifest and logical-inventory
digests before sealing Edition 1.

One `directory_package` Export Artifact includes the four audience entries but
not the internal Snapshot Manifest. Edition and Export verification complete
before an explicit current-Edition pointer promotion. This local sealed Edition
is what issue 36 means by an issued Edition; no Issuance, delivery, Submission,
recipient authorization, or disclosure event is created.

After sealing and Export verification, the validator independently records the
Edition identity, Manifest and logical-inventory hashes, Seal identity, every
Entry path/size/output hash, Export identity and directory-inventory hash, and
the actual hash of every Edition and Export file. It then removes the disposable
producer source root. Producer-independent Edition and Export verification still
succeed, and a second independent inventory must equal the first exactly. The
Selection still names its predecessor Candidate and the current pointer remains
unchanged. There is no source refresh operation; changed audience content would
require a successor Candidate, Selection, Placement/Arrangement, Composition,
Plan, and Edition.

## Deterministic fixture bytes

Text payloads use the repository's byte-preserving `.gitattributes` rules. JSON
uses UTF-8, LF, canonical compact form, and a final newline.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `runtime/baseline-manifest.json` | 720 | `bfe8140e3d2d253306ffaf2fcff8688c936a644a25215023a581b376be8368be` |
| `runtime/later-manifest.json` | 1298 | `b67e1c6c1c61662ce27a5c6fe358d509dd8092c0bb4c4a5ba3fd658078dceed2` |
| `shared/.../baseline-argument.txt` | 270 | `66d20828ce14e1ae2222d0b0dd05a3efe239cc2ad559bd944512adff4d06058a` |
| `shared/.../revised-argument.txt` | 347 | `d9bc726f0d5b1779b2ec5e5fcc7f557d95cd83afc48780b60285f06fda0af8d0` |
| `shared/.../revised-feedback.txt` | 172 | `87c44d69b3366bef44358b1d75ffb54175dc35551042cfcb06294fa0a2e1d4f9` |

The two new manifests are the minimum descriptors needed to publish the existing
representative bytes through Core and the established fixture adapter. They are
not a public Vitrine interchange format.
