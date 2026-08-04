# Vitrine Architecture

This directory contains system-level Vitrine architecture documents. Architecture documents explain boundaries, authority, data flow, and constraints in more detail than an ADR, but they do not replace accepted decisions or final contracts.

## Current documents

- [Module boundaries and authority](module-boundaries.md) — defines Vitrine's ownership, authority hierarchy, dependency directions, sibling-module boundaries, prohibited behavior, edge cases, and downstream implications.

## Reading order

1. Review the [foundation research](../research/portfolio-purpose-workflows.md).
2. Read [module boundaries and authority](module-boundaries.md).
3. Read the related [Architecture Decision Records](../decisions/README.md).
4. Use later contract documents for exact serialized structures once they are added.

## Document authority

When documents disagree:

1. an **Accepted** ADR governs the architectural decision;
2. a final accepted contract governs detailed record shape and validation while remaining subordinate to ADRs;
3. implementation documentation describes current behavior;
4. architecture documents provide consolidated context and constraints;
5. research documents provide evidence and design inputs but do not establish final contracts.

The current module-boundary ADR is **Proposed**. Until explicitly accepted, it records the reviewed recommendation and must not be represented as an accepted decision.
