from __future__ import annotations

import pytest

from vitrine.artifact_diagnostics import (
    diagnose_artifact_applicability,
    explain_artifact_failure,
)
from vitrine.compatibility_diagnostics import CompatibilityDiagnosticError
from vitrine.snapshot_materialization import SnapshotMaterializationError

PUB = "pub_00000000000000000000000000000000"
ARTIFACT = "artifact_alpha"
PRIVATE = "PRIVATE-STUDENT-CONTENT-C-SECRET"


def _error(
    code: str, stage: str, message: str = PRIVATE
) -> SnapshotMaterializationError:
    return SnapshotMaterializationError(code, message, stage=stage)


def test_scoreform_artifact_is_not_applicable() -> None:
    result = diagnose_artifact_applicability("scoreform", publication_id=PUB)
    assert result.outcome == "not_applicable"
    assert result.code == "compatibility.artifact_api_not_applicable"
    assert result.stage == "artifact_api"
    assert "Artifact provider is expected" not in result.summary


def test_scoreform_snapshot_provider_failure_is_still_not_applicable() -> None:
    result = explain_artifact_failure(
        "scoreform",
        _error("snapshot.source_provider_missing", "provider_selection"),
        publication_id=PUB,
    )
    assert result.outcome == "not_applicable"
    assert result.code == "compatibility.artifact_api_not_applicable"


@pytest.mark.parametrize("producer", ["quillan", "concord"])
def test_authorized_artifact_contract_is_applicable_not_source_available(
    producer: str,
) -> None:
    result = diagnose_artifact_applicability(producer, publication_id=PUB)
    assert result.outcome == "supported"
    assert result.code == "compatibility.artifact_api_ready"
    assert "availability" in result.next_action.lower()


@pytest.mark.parametrize("producer", ["quillan", "concord"])
def test_missing_public_artifact_api_is_unavailable(producer: str) -> None:
    result = explain_artifact_failure(
        producer,
        _error("snapshot.source_unavailable", f"{producer}_artifact_contract"),
        publication_id=PUB,
        source_artifact_id=ARTIFACT,
    )
    assert result.outcome == "unavailable"
    assert result.code == "snapshot.source_unavailable"
    assert result.stage == f"{producer}_artifact_contract"
    assert result.reason_codes == ("compatibility.artifact_api_unavailable",)


@pytest.mark.parametrize("producer", ["quillan", "concord"])
def test_artifact_authorization_denied_is_distinct(producer: str) -> None:
    result = explain_artifact_failure(
        producer,
        _error(
            "snapshot.source_unavailable",
            f"{producer}_artifact_authorization_denied",
        ),
    )
    assert result.outcome == "denied"
    assert result.reason_codes == ("compatibility.artifact_authorization_denied",)
    assert ("artifact_bytes_acquired", "no") in result.safe_fields


@pytest.mark.parametrize("producer", ["quillan", "concord"])
def test_artifact_authorization_unresolved_is_distinct(producer: str) -> None:
    result = explain_artifact_failure(
        producer,
        _error(
            "snapshot.source_unavailable",
            f"{producer}_artifact_authorization_unresolved",
        ),
    )
    assert result.outcome == "unresolved"
    assert result.reason_codes == (
        "compatibility.artifact_authorization_unresolved",
    )
    assert ("artifact_bytes_acquired", "no") in result.safe_fields


@pytest.mark.parametrize("producer", ["quillan", "concord"])
def test_artifact_source_unavailable_after_authorized_read_is_distinct(
    producer: str,
) -> None:
    result = explain_artifact_failure(
        producer,
        _error("snapshot.source_unavailable", f"{producer}_artifact_read"),
    )
    assert result.outcome == "unavailable"
    assert result.reason_codes == ("compatibility.artifact_source_unavailable",)


@pytest.mark.parametrize(
    ("producer", "stage"),
    [
        ("quillan", "quillan_artifact_read"),
        ("quillan", "quillan_artifact_result"),
        ("concord", "concord_artifact_read"),
        ("concord", "concord_artifact_result"),
    ],
)
def test_artifact_integrity_failure_is_distinct(producer: str, stage: str) -> None:
    result = explain_artifact_failure(
        producer,
        _error("snapshot.source_integrity_failed", stage),
    )
    assert result.outcome == "integrity_failed"
    assert result.reason_codes == ("compatibility.artifact_integrity_failed",)


def test_missing_vitrine_source_provider_is_not_misreported_as_producer_api_failure(
) -> None:
    result = explain_artifact_failure(
        "quillan",
        _error("snapshot.source_provider_missing", "provider_selection"),
    )
    assert result.outcome == "unavailable"
    assert result.reason_codes == ("compatibility.artifact_provider_missing",)
    assert "Vitrine" in result.summary


def test_private_snapshot_error_message_never_reaches_diagnostic_output() -> None:
    result = explain_artifact_failure(
        "concord",
        _error("snapshot.source_integrity_failed", "concord_artifact_result"),
    )
    rendered = repr(result)
    assert PRIVATE not in rendered
    assert PRIVATE not in result.summary
    assert PRIVATE not in result.next_action


def test_cross_producer_artifact_stage_is_rejected() -> None:
    with pytest.raises(CompatibilityDiagnosticError):
        explain_artifact_failure(
            "quillan",
            _error("snapshot.source_unavailable", "concord_artifact_read"),
        )


def test_unknown_producer_is_not_invented_as_artifact_support() -> None:
    with pytest.raises(CompatibilityDiagnosticError):
        diagnose_artifact_applicability("futureproducer")
