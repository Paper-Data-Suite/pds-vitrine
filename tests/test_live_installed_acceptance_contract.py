from __future__ import annotations

from scripts.live_installed_acceptance_contract import (
    ACCEPTANCE_IDENTITY,
    AUDITED_RELEASE_WHEELS,
    CANDIDATE_DISCOVERY_SLICE_READY,
    CI_ENDPOINTS,
    CONCORD_CONTRACT,
    CURATED_SNAPSHOT_SLICE_READY,
    CUSTODY_VERIFIER_SLICE_READY,
    FIXTURE_PRODUCER_IDS,
    FULL_ACCEPTANCE_READY,
    HEAVY_SCENARIO_FAMILIES,
    LIVE_PRODUCERS,
    NEGATIVE_MATRIX_SLICE_READY,
    QUILLAN_CONTRACT,
    SCOREFORM_CONTRACT,
    validate_contract_constants,
)


def test_issue_71_exact_release_artifacts_are_frozen() -> None:
    validate_contract_constants()
    assert ACCEPTANCE_IDENTITY == "vitrine_live_installed_cross_producer_acceptance_v1"
    assert [item.distribution_name for item in AUDITED_RELEASE_WHEELS] == [
        "pds-core",
        "scoreform",
        "quillan",
        "pds-concord",
    ]
    assert [item.version for item in AUDITED_RELEASE_WHEELS] == [
        "0.6.3",
        "0.11.0",
        "0.10.0",
        "0.3.0",
    ]
    assert all(len(item.sha256) == 64 for item in AUDITED_RELEASE_WHEELS)
    assert all("/releases/download/v" in item.release_url for item in AUDITED_RELEASE_WHEELS)


def test_issue_71_preserves_three_different_materialization_rules() -> None:
    assert SCOREFORM_CONTRACT.materialization == "reference_only"
    assert SCOREFORM_CONTRACT.artifact_module is None
    assert QUILLAN_CONTRACT.materialization == "copied_source"
    assert QUILLAN_CONTRACT.artifact_module == "quillan.academic_result_artifacts"
    assert CONCORD_CONTRACT.materialization == "copied_source"
    assert CONCORD_CONTRACT.artifact_module == "concord.academic_result_artifacts"
    assert [item.producer_module_id for item in LIVE_PRODUCERS] == [
        "scoreform",
        "quillan",
        "concord",
    ]
    assert not FIXTURE_PRODUCER_IDS.intersection(
        item.producer_module_id for item in LIVE_PRODUCERS
    )


def test_issue_71_heavy_acceptance_inventory_and_ci_endpoints_are_explicit() -> None:
    assert HEAVY_SCENARIO_FAMILIES == (
        "healthy_cross_producer_portfolio",
        "publication_currentness_drift",
        "quillan_derived_source_drift",
        "concord_exact_source_removal",
        "denied_authorization",
        "export_tamper",
        "historical_reload",
        "producer_independent_sealed_verification",
    )
    assert CI_ENDPOINTS == (("ubuntu-latest", "3.11"), ("windows-latest", "3.14"))


def test_slice_4b_enables_custody_verifier_without_claiming_full_ticket() -> None:
    assert CANDIDATE_DISCOVERY_SLICE_READY is True
    assert CURATED_SNAPSHOT_SLICE_READY is True
    assert NEGATIVE_MATRIX_SLICE_READY is True
    assert CUSTODY_VERIFIER_SLICE_READY is True
    assert FULL_ACCEPTANCE_READY is False
