# Vitrine Architecture Decision Records

Architecture Decision Records document significant Vitrine decisions, their context, consequences, alternatives, and required follow-up.

## Current decisions

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-vitrine-module-boundaries-and-authority.md) | Vitrine Module Boundaries and Authority | Proposed |
| [0002](0002-portfolio-subject-identity-and-roster-linking.md) | Portfolio Subject Identity and Roster Linking | Proposed |

## Status meanings

### Proposed

The decision is under review and does not yet govern as an accepted project decision.

### Accepted

The decision governs later contracts and implementation unless explicitly superseded.

### Superseded

A later ADR replaces the decision. The earlier ADR remains part of project history and links to its replacement.

### Deprecated

The decision should not guide new work but has no single complete replacement.

### Rejected

The proposal was considered but not adopted. It may remain documented when the reasoning is useful.

## ADR maintenance rules

- Use the next unused four-digit number.
- Do not reuse numbers.
- Begin a new architectural decision as **Proposed** unless maintainers explicitly accept it.
- Do not silently reverse or materially expand an Accepted ADR.
- Use a new ADR to supersede an earlier accepted decision.
- Preserve the earlier decision and rationale.
- Link supporting research, architecture, contracts, examples, and sibling decisions.

## Relationship to other documentation

- [Architecture index](../architecture/README.md)
- [Portfolio Subject identity design](../design/portfolio-subject-identity.md)
- [Representative identity examples](../examples/portfolio-subject-identity-examples.md)
- [Foundation research](../research/portfolio-purpose-workflows.md)
- [Repository documentation index](../README.md)

When documents disagree, an Accepted ADR governs the architectural decision. Exact accepted contracts may add detail but must remain consistent with the ADR set.
