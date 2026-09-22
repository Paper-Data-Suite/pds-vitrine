# Candidate Evidence Review development

Issue #96 implementation is split into transient presentation, exact preview
authority/revalidation, producer-authorized Artifact acquisition, and explicit
teacher-menu wiring.

## Runtime modules

```text
vitrine/candidate_discovery_presentation.py
vitrine/candidate_evidence_presentation.py
vitrine/candidate_evidence_preview.py
vitrine/candidate_evidence_artifact_preview.py
vitrine/candidate_evidence_preview_menu.py
```

The Candidate Inbox and guided Candidate Review consume those shared projections;
they do not maintain independent producer-specific naming systems.

## Authority flow

Structured preview:

```text
persisted Candidate/Evaluation source endpoint
-> exact Core Publication + registration replay
-> authorized verified producer manifest
-> audited public reader
-> exact reprojection
-> exact persisted source match
-> allowlisted structured summary
```

Byte-bearing preview:

```text
exact revalidated preview context
-> Vitrine candidate_evidence_preview authorization
-> producer public Artifact API authorization gate
-> producer-owned native I/O
-> exact returned identity/media/digest/size verification
-> transient bytes
```

Do not introduce a title-based lookup, producer-native path construction, Snapshot
Plan IDs, a Vitrine preview cache, or durable viewer materialization.

## Adding evidence fields

Structured fields must be deliberate instructional allowlists in
`candidate_evidence_preview.py`. Do not add a generic manifest serializer.
Consider privacy, unrelated identities, private notes, answer keys, raw payloads,
paths, hashes, and internal contracts before adding a field.

## Adding a byte-bearing representation

A new byte-bearing representation requires an audited released producer public
Artifact API. Extend the exact producer bridge only when Vitrine can verify the
returned representation against persisted Candidate provenance.

Do not implement a native-file fallback.

## Menu behavior

`V. View evidence` is optional and explicit. Candidate detail rendering itself
must stay producer-I/O free. After preview, the teacher returns to the exact
Candidate Review decision surface; preview never creates Selection or Placement.

## Focused qualification

Run:

```powershell
python scripts/validate_candidate_evidence_review.py
python -m pytest -q `
  tests/test_candidate_evidence_review_acceptance.py `
  tests/test_validate_candidate_evidence_review.py
python -m ruff check `
  scripts/validate_candidate_evidence_review.py `
  tests/test_candidate_evidence_review_acceptance.py `
  tests/test_validate_candidate_evidence_review.py
python -m mypy
python scripts/check_documentation.py
git diff --check
```

Slice 12 separately owns exact installed-producer and installed-Vitrine-wheel
acceptance required by Issue #96.
