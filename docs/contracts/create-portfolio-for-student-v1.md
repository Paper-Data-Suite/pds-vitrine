# Create Portfolio for Student v1

- **Issue:** #65
- **Contract:** `vitrine_create_portfolio_for_student_v1`
- **Status:** Implemented guided setup contract

## Purpose

`Create Portfolio for Student` is a transient orchestration workflow over
existing Portfolio Subject, Portfolio, and Portfolio Profile records.

```text
school year + class ID + student ID = exact roster endpoint
same student ID across classes != same Portfolio Subject
same display name != same Portfolio Subject
purpose != hidden Profile policy
starter available != starter installed
setup preview != canonical state
Portfolio created != Candidates discovered
```

No canonical `PortfolioSetup` record exists.

## Planning

`plan_create_portfolio_for_student()` is read-only. It records the observed
Vitrine revision, exact roster student, Subject resolution, current/proposed
Subject links, existing Portfolios, exact bindable Profile choices, effective
Profile Binding context, proposed durable IDs, record kinds, and blocking codes.

An exact reference already linked to one current Subject is reused. An unlinked
reference requires explicit `create_new` or `link_existing`. Subject conflict
blocks setup. Names and repeated local student IDs are never identity authority.

## Profile policy

The teacher chooses `improvement` or `showcase`, then one exact bindable
Profile Revision whose purpose matches. School year comes from the exact roster
endpoint when absent from caller context. Other applicability context remains
explicit when required.

Setup never installs, activates, reactivates, or upgrades a starter Profile.

## Atomic creation

`create_portfolio_for_student()` accepts one ready reviewed plan. It revalidates
the Vitrine revision, exact Core roster student, Subject resolution, and exact
Profile bindability/applicability, then validates prospective state and performs
one `commit_record_batch(...)`.

The reviewed proposed IDs are the IDs persisted. Failure leaves no partial
Subject/link/Portfolio/Profile Binding.

## Interfaces

Teacher menu:

```text
1. Create Portfolio for Student
```

Canonical creation requires the exact final confirmation `CREATE PORTFOLIO`.

Direct CLI:

```text
vitrine portfolio create-for-student ...
vitrine portfolio create-for-student ... --dry-run
```

`--dry-run` must produce a ready plan and writes nothing. Primitive
`vitrine portfolio create --subject-id ...` remains supported.

## Boundaries

Setup does not infer cross-class identity, repair Subject identity, install
starter Profiles, discover Candidates, create Candidate/Selection/Placement/
Composition/Snapshot state, read producer-native content, or infer grading,
proficiency, improvement, portfolio worth, or disclosure.

## Validation

```powershell
python scripts/validate_portfolio_setup.py
```
