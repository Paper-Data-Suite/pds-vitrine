"""Validate the substantive Vitrine v0.3.0 release-audit boundary.

This is intentionally a lightweight release-audit guard. It freezes the accepted
privacy/provenance/usability conclusions and checks representative executable/source
boundaries without duplicating issue #71's expensive installed cross-producer gate.
"""

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path
from typing import Final

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_AUDIT_STATE: Final[str] = (
    "substantive_audit_complete_release_qualification_pending"
)

ADR_FILES: Final[tuple[tuple[str, str], ...]] = (
    ("ADR 0001", "docs/decisions/0001-vitrine-module-boundaries-and-authority.md"),
    ("ADR 0002", "docs/decisions/0002-portfolio-subject-identity-and-roster-linking.md"),
    ("ADR 0003", "docs/decisions/0003-versioned-portfolio-profiles.md"),
    ("ADR 0004", "docs/decisions/0004-candidate-discovery-and-source-references.md"),
    ("ADR 0005", "docs/decisions/0005-producer-artifact-exposure-boundaries.md"),
    ("ADR 0006", "docs/decisions/0006-selection-ordering-annotation-and-reflection.md"),
    ("ADR 0007", "docs/decisions/0007-snapshot-export-checksum-and-immutability.md"),
    ("ADR 0008", "docs/decisions/0008-privacy-redaction-and-audience-controls.md"),
    ("ADR 0009", "docs/decisions/0009-regulated-portfolio-and-compliance-profiles.md"),
)

MILESTONE_ISSUES: Final[tuple[int, ...]] = tuple(range(57, 72))


def _require_text(path: Path, *markers: str) -> None:
    text = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in text:
            raise RuntimeError(f"{path.relative_to(ROOT)} missing audit marker: {marker}")


def _validate_adrs() -> None:
    for label, relative in ADR_FILES:
        _require_text(ROOT / relative, f"# {label}:", "- **Status:** Accepted")

    _require_text(
        ROOT / ADR_FILES[0][1],
        "Core publication does not authorize portfolio access, selection, copying, disclosure, or approval.",
        "Portia material is excluded from ordinary Vitrine discovery and candidate presentation by default.",
        "Conservative behavior when contracts are unavailable",
    )
    _require_text(
        ROOT / ADR_FILES[3][1],
        "catalog-as-authority",
        "parsing before authorization",
        "attempt auto-selection",
        "in-place Candidate retargeting",
    )
    _require_text(
        ROOT / ADR_FILES[4][1],
        "Field exposure is allowlist-based",
        "ScoreForm attempts remain separate and unranked by Vitrine.",
        "Quillan private notes never enter exposure.",
        "Concord membership is not authorship.",
        "Portia is suppressed by default without existence leakage.",
    )
    _require_text(
        ROOT / ADR_FILES[5][1],
        "No stage is implied by the preceding stage.",
        "Reflection is interpretation, not proof",
        "Approval does not grant unrelated authority",
        "Working Portfolio Composition Revision freezes curation state",
    )
    _require_text(
        ROOT / ADR_FILES[6][1],
        "Source successors never silently replace planned sources",
        "Digest layers remain semantically distinct",
        "Audience policy and authorization remain separate",
        "Current Edition is explicit",
    )
    _require_text(
        ROOT / ADR_FILES[7][1],
        "An Audience Context does not authorize a recipient.",
        "Disclosure Authorization binds exact immutable content",
        "Internal Snapshot Manifests remain restricted",
        "issuance != delivery",
    )
    _require_text(
        ROOT / ADR_FILES[8][1],
        "Research-only and operational Profiles are distinct",
        "The Class of 2026 / 2025–2026 New Jersey Graduation Portfolio Appeal is documented as a research-only reference family.",
        "It is not activated operationally.",
    )


def _validate_release_audit_document() -> None:
    audit = ROOT / "docs/v0.3.0-release-audit.md"
    _require_text(
        audit,
        f"- **Current audit state:** `{EXPECTED_AUDIT_STATE}`",
        "## ADR conformance matrix",
        "## Milestone workstream ledger",
        "## Privacy audit",
        "## Provenance audit",
        "## Guided usability audit",
        "## Audit findings register",
        "V03-AUD-001",
        "V03-AUD-005",
        "V03-AUD-006",
        "V03-AUD-007",
        "No unresolved `BLOCKER` or `MAJOR` finding remains",
        "**Slice 2 disposition:** `CONFORMS — RELEASE QUALIFICATION PENDING`",
    )
    text = audit.read_text(encoding="utf-8")
    if "AUDIT PENDING" in text:
        raise RuntimeError("v0.3.0 audit ledger still contains AUDIT PENDING")
    for issue in MILESTONE_ISSUES:
        if f"| #{issue} |" not in text:
            raise RuntimeError(f"v0.3.0 audit ledger missing milestone issue #{issue}")
    for adr_number in range(1, 10):
        if f"| ADR 000{adr_number} |" not in text:
            raise RuntimeError(f"v0.3.0 audit ledger missing ADR 000{adr_number}")


def _validate_package_boundary() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        raise RuntimeError("pyproject project table is missing")
    if project.get("dependencies") != ["pds-core>=0.6.3,<0.7"]:
        raise RuntimeError("v0.3.0 audit requires Core-only runtime dependency")
    if project.get("scripts") != {"vitrine": "vitrine.cli:main"}:
        raise RuntimeError("v0.3.0 console-script boundary drifted")
    expected = {
        "paper_data_suite.module_operations": {
            "vitrine": "vitrine.pds_operations:get_module_operations_profile"
        }
    }
    if project.get("entry-points") != expected:
        raise RuntimeError("v0.3.0 module-operations entry-point boundary drifted")


def _validate_authorization_and_producer_boundaries() -> None:
    reader = ROOT / "vitrine/producer_reader_services.py"
    text = reader.read_text(encoding="utf-8")
    authorize_index = text.index("authorization = authorize_source_read(")
    read_index = text.index("manifest_bytes = read_verified_publication_manifest_bytes(")
    producer_index = text.index("public_model = reader.read(manifest_bytes)")
    if not authorize_index < read_index < producer_index:
        raise RuntimeError(
            "producer manifest read ordering no longer authorizes before protected I/O"
        )
    _require_text(
        reader,
        '"source_read.authorization_denied"',
        '"source_read.authorization_unresolved"',
        "Producer public reader rejected the verified manifest bytes.",
    )

    _require_text(
        ROOT / "vitrine/quillan_artifact_source.py",
        "Snapshot build authority",
        "Artifact authorization",
        '"denied"',
        '"unresolved"',
    )
    _require_text(
        ROOT / "vitrine/concord_artifact_source.py",
        "does not inspect Concord native storage",
        "Snapshot build authority as Artifact",
        "ConcordArtifactAuthorizationRequest",
        "ConcordArtifactAuthorizationDecision",
        '"allowed"',
        '"denied"',
        '"unresolved"',
    )


def _validate_candidate_privacy() -> None:
    _require_text(
        ROOT / "vitrine/candidate_inbox.py",
        'VISIBLE_EVALUATION_OUTCOMES: Final[frozenset[str]] = EVALUATION_OUTCOMES - {',
        '"suppressed"',
        'if evaluation is not None and evaluation.outcome == "suppressed":',
        'if evaluation.outcome == "suppressed":',
    )


def _validate_guided_usability_boundaries() -> None:
    _require_text(
        ROOT / "vitrine/portfolio_setup_menu.py",
        "School year + class ID + student ID is the exact roster identity.",
        "Matching names or repeated student IDs never link classes automatically.",
        "Nothing is written until the final CREATE PORTFOLIO confirmation.",
        "Purpose filters Profile choices; it does not install hidden policy.",
    )
    _require_text(
        ROOT / "vitrine/current_portfolio_menu.py",
        "The Audience Rule constrains content; it does not identify a recipient.",
        "It does not satisfy, clear, approve, or authorize disclosure.",
        "and create/verify a local directory Export.",
        "It will not advance the current Edition pointer or deliver the Export.",
        "Export creation is not disclosure permission or delivery.",
    )
    _require_text(
        ROOT / "vitrine/working_composition.py",
        "preparation_fingerprint",
        "unplaced_selection_ids",
        "source_observations",
        "audience_rules",
    )


def _validate_suite_operations_boundary() -> None:
    _require_text(
        ROOT / "vitrine/pds_operations.py",
        "MODULE_OPERATIONS_CONTRACT_VERSION",
        "readiness_provider=evaluate_vitrine_readiness",
        "attention_provider=evaluate_vitrine_attention_for_core",
        "validate_module_operations_profile",
    )
    _require_text(
        ROOT / "vitrine/operations_provider.py",
        "evaluate_vitrine_readiness",
        "evaluate_vitrine_attention_for_core",
    )


def validate() -> None:
    _validate_adrs()
    _validate_release_audit_document()
    _validate_package_boundary()
    _validate_authorization_and_producer_boundaries()
    _validate_candidate_privacy()
    _validate_guided_usability_boundaries()
    _validate_suite_operations_boundary()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    try:
        validate()
    except (OSError, RuntimeError, ValueError) as error:
        print(f"v0.3.0 substantive release audit validation failed: {error}")
        return 1
    print("PASS v0.3.0 substantive privacy/provenance/usability audit validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
