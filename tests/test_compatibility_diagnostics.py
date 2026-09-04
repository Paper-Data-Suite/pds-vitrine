from __future__ import annotations

from types import SimpleNamespace

import pytest
from pds_core.publication_compatibility import (
    PublicationContractSupport,
    PublicationProducerProfile,
    PublicationProducerRegistry,
    SourceRecordContractSupport,
)

import vitrine.compatibility_diagnostics as compatibility_diagnostics
from vitrine.compatibility_diagnostics import (
    CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION,
    diagnose_installed_producer_readiness,
    explain_live_adapter_support,
)
from vitrine.producer_adapters import (
    ProducerAdapterSupportKey,
    ProducerAdapterSupportRequest,
    ProducerProjectionAdapterRegistry,
    build_adapter_registry,
)
from vitrine.released_producer_contracts import (
    CONCORD_LIVE_SUPPORT_KEY,
    QUILLAN_LIVE_SUPPORT_KEY,
    RELEASED_PRODUCER_CONTRACTS,
    SCOREFORM_LIVE_SUPPORT_KEY,
)


def _request(
    key: ProducerAdapterSupportKey,
    *,
    producer_module_id: str | None = None,
    core_publication_schema_version: str | None = None,
    publication_kind: str | None = None,
    manifest_contract_version: str | None = None,
    producer_contract_version: str | None | object = ...,  # sentinel
    source_record_kind: str | None | object = ...,  # sentinel
    source_record_contract_version: str | None | object = ...,  # sentinel
    capabilities: tuple[str, ...] | None = None,
) -> ProducerAdapterSupportRequest:
    producer_contract = (
        key.producer_contract_version
        if producer_contract_version is ...
        else producer_contract_version
    )
    source_kind = (
        key.source_record_kind if source_record_kind is ... else source_record_kind
    )
    source_contract = (
        key.source_record_contract_version
        if source_record_contract_version is ...
        else source_record_contract_version
    )
    assert producer_contract is None or isinstance(producer_contract, str)
    assert source_kind is None or isinstance(source_kind, str)
    assert source_contract is None or isinstance(source_contract, str)
    return ProducerAdapterSupportRequest(
        producer_module_id=producer_module_id or key.producer_module_id,
        core_publication_schema_version=(
            core_publication_schema_version or key.core_publication_schema_version
        ),
        publication_kind=publication_kind or key.publication_kind,
        manifest_contract_version=(
            manifest_contract_version or key.manifest_contract_version
        ),
        producer_contract_version=producer_contract,
        source_record_kind=source_kind,
        source_record_contract_version=source_contract,
        capabilities=(key.required_capabilities if capabilities is None else capabilities),
    )


@pytest.mark.parametrize(
    ("key", "adapter_id"),
    (
        (CONCORD_LIVE_SUPPORT_KEY, "vitrine_concord_live_adapter"),
        (QUILLAN_LIVE_SUPPORT_KEY, "vitrine_quillan_live_adapter"),
        (SCOREFORM_LIVE_SUPPORT_KEY, "vitrine_scoreform_live_adapter"),
    ),
)
def test_exact_live_contracts_report_supported(
    key: ProducerAdapterSupportKey,
    adapter_id: str,
) -> None:
    result = explain_live_adapter_support(_request(key))

    assert (
        result.diagnostic_contract_version
        == CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION
    )
    assert result.scope == "contract_support"
    assert result.outcome == "supported"
    assert result.code == "compatibility.contract_supported"
    assert result.adapter_id == adapter_id
    assert result.reason_codes == ("compatibility.contract_supported",)


def test_unknown_producer_is_distinct_from_known_unsupported_contract() -> None:
    result = explain_live_adapter_support(
        _request(SCOREFORM_LIVE_SUPPORT_KEY, producer_module_id="unknown_producer")
    )

    assert result.outcome == "unsupported"
    assert result.code == "adapter.unsupported_contract"
    assert result.adapter_id is None
    assert result.reason_codes == ("compatibility.producer_not_registered",)
    fields = dict(result.safe_fields)
    assert fields["registered_live_producers"] == "concord,quillan,scoreform"


@pytest.mark.parametrize(
    ("producer_module_id", "adapter_id"),
    (
        ("vitrine_concord_fixture", "vitrine_concord_fixture_adapter"),
        ("vitrine_quillan_fixture", "vitrine_quillan_fixture_adapter"),
        ("vitrine_scoreform_fixture", "vitrine_scoreform_fixture_adapter"),
    ),
)
def test_fixture_identities_never_masquerade_as_live_producers(
    producer_module_id: str,
    adapter_id: str,
) -> None:
    result = explain_live_adapter_support(
        _request(SCOREFORM_LIVE_SUPPORT_KEY, producer_module_id=producer_module_id)
    )

    assert result.scope == "fixture_boundary"
    assert result.outcome == "unsupported"
    assert result.code == "adapter.fixture_not_enabled"
    assert result.adapter_id == adapter_id
    assert result.reason_codes == ("compatibility.fixture_identity",)
    assert "development fixture" in result.summary


@pytest.mark.parametrize(
    ("kwargs", "reason_code", "actual_field", "expected_field"),
    (
        (
            {"core_publication_schema_version": "2"},
            "compatibility.core_publication_schema_mismatch",
            "actual_core_publication_schema_version",
            "expected_core_publication_schema_version",
        ),
        (
            {"publication_kind": "intervention_record_set"},
            "compatibility.publication_kind_mismatch",
            "actual_publication_kind",
            "expected_publication_kind",
        ),
        (
            {"manifest_contract_version": "scoreform_future_manifest_v2"},
            "compatibility.manifest_contract_mismatch",
            "actual_manifest_contract_version",
            "expected_manifest_contract_version",
        ),
        (
            {"producer_contract_version": "scoreform_future_work_v2"},
            "compatibility.producer_contract_mismatch",
            "actual_producer_contract_version",
            "expected_producer_contract_version",
        ),
    ),
)
def test_known_live_contract_scalar_mismatches_are_explained(
    kwargs: dict[str, object],
    reason_code: str,
    actual_field: str,
    expected_field: str,
) -> None:
    request = _request(SCOREFORM_LIVE_SUPPORT_KEY, **kwargs)  # type: ignore[arg-type]
    result = explain_live_adapter_support(request)

    assert result.code == "adapter.unsupported_contract"
    assert result.reason_codes == (reason_code,)
    fields = dict(result.safe_fields)
    assert actual_field in fields
    assert expected_field in fields


def test_scoreform_publication_source_presence_mismatch_is_explicit() -> None:
    result = explain_live_adapter_support(
        _request(
            SCOREFORM_LIVE_SUPPORT_KEY,
            source_record_kind="assignment",
            source_record_contract_version="1",
        )
    )

    assert result.reason_codes == (
        "compatibility.source_record_presence_mismatch",
    )
    fields = dict(result.safe_fields)
    assert fields["actual_source_record_kind"] == "assignment"
    assert fields["expected_source_record_kind"] == "<absent>"


def test_quillan_assignment_registration_source_does_not_expand_publication_support() -> None:
    result = explain_live_adapter_support(
        _request(
            QUILLAN_LIVE_SUPPORT_KEY,
            source_record_kind="assignment",
            source_record_contract_version="2",
        )
    )

    assert result.code == "adapter.unsupported_contract"
    assert result.reason_codes == (
        "compatibility.source_record_presence_mismatch",
    )
    assert "Academic Work Registration" in result.summary
    assert "does not expand" in result.summary
    assert "do not broaden QUILLAN_LIVE_SUPPORT_KEY" in result.next_action


def test_concord_missing_source_record_is_explained_as_presence_mismatch() -> None:
    result = explain_live_adapter_support(
        _request(
            CONCORD_LIVE_SUPPORT_KEY,
            source_record_kind=None,
            source_record_contract_version=None,
        )
    )

    assert result.reason_codes == (
        "compatibility.source_record_presence_mismatch",
    )
    assert "versioned Activity" in result.summary
    fields = dict(result.safe_fields)
    assert fields["actual_source_record_kind"] == "<absent>"
    assert fields["expected_source_record_kind"] == "activity"


def test_concord_wrong_source_kind_and_version_are_distinct() -> None:
    result = explain_live_adapter_support(
        _request(
            CONCORD_LIVE_SUPPORT_KEY,
            source_record_kind="assignment",
            source_record_contract_version="concord_activity_v2",
        )
    )

    assert result.reason_codes == (
        "compatibility.source_record_contract_mismatch",
        "compatibility.source_record_kind_mismatch",
    )


def test_missing_required_capabilities_reports_only_missing_values() -> None:
    result = explain_live_adapter_support(
        _request(
            SCOREFORM_LIVE_SUPPORT_KEY,
            capabilities=("multiple_attempts", "points"),
        )
    )

    assert result.reason_codes == (
        "compatibility.required_capability_missing",
    )
    fields = dict(result.safe_fields)
    assert fields["missing_required_capabilities"] == "question_evidence"
    assert fields["available_capabilities"] == "multiple_attempts,points"


@pytest.mark.parametrize(
    "capabilities",
    (
        ("criterion_scores",),
        ("criterion_scores", "standards_ratings"),
        ("criterion_scores", "moderated_scores"),
        ("criterion_scores", "standards_ratings", "moderated_scores"),
    ),
)
def test_concord_optional_capabilities_do_not_expand_required_support(
    capabilities: tuple[str, ...],
) -> None:
    result = explain_live_adapter_support(
        _request(CONCORD_LIVE_SUPPORT_KEY, capabilities=capabilities)
    )

    assert result.outcome == "supported"
    assert result.code == "compatibility.contract_supported"


def test_support_explainer_uses_existing_registry_selection_semantics() -> None:
    registry = build_adapter_registry()
    request = _request(QUILLAN_LIVE_SUPPORT_KEY)

    selected = registry.select_adapter(request)
    result = explain_live_adapter_support(request, registry=registry)

    assert result.adapter_id == selected.declaration.adapter_id
    assert result.code == "compatibility.contract_supported"



def _installed_profile_registry() -> PublicationProducerRegistry:
    profiles: list[PublicationProducerProfile] = []
    for audit in RELEASED_PRODUCER_CONTRACTS:
        key = audit.support_key
        source_contracts = ()
        if key.source_record_kind is not None:
            assert key.source_record_contract_version is not None
            source_contracts = (
                SourceRecordContractSupport(
                    record_kind=key.source_record_kind,
                    contract_versions=frozenset(
                        {key.source_record_contract_version}
                    ),
                    allows_unversioned=False,
                ),
            )
        assert key.producer_contract_version is not None
        profiles.append(
            PublicationProducerProfile(
                module_id=audit.producer_module_id,
                display_name=f"{audit.producer_module_id.title()} Test Profile",
                supported_core_publication_schema_versions=frozenset(
                    {key.core_publication_schema_version}
                ),
                supported_academic_work_contract_versions=frozenset(
                    {key.producer_contract_version}
                ),
                publication_contracts=(
                    PublicationContractSupport(
                        publication_kind=key.publication_kind,
                        manifest_contract_versions=frozenset(
                            {key.manifest_contract_version}
                        ),
                        supported_capabilities=frozenset(
                            audit.advertised_capabilities
                        ),
                        source_record_contracts=source_contracts,
                        allows_missing_source_record=(
                            key.source_record_kind is None
                        ),
                    ),
                ),
            )
        )
    return PublicationProducerRegistry(tuple(profiles))


def _ready_public_module(name: str) -> object:
    if name.endswith("academic_result_reader"):
        return SimpleNamespace(read_academic_result_manifest=lambda value: value)
    if name in {
        "quillan.academic_result_artifacts",
        "concord.academic_result_artifacts",
    }:
        return SimpleNamespace()
    raise AssertionError(f"unexpected public module probe: {name}")


def _check(report: object, stage: str) -> object:
    checks = getattr(report, "checks")
    return next(item for item in checks if item.stage == stage)


def test_installed_readiness_reports_three_audited_producers_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        lambda _name: "99.123.456",
    )
    monkeypatch.setattr(
        compatibility_diagnostics,
        "import_module",
        _ready_public_module,
    )

    reports = diagnose_installed_producer_readiness(
        producer_registry=_installed_profile_registry()
    )

    assert tuple(report.producer_module_id for report in reports) == (
        "concord",
        "quillan",
        "scoreform",
    )
    assert all(report.ready for report in reports)
    assert all(report.overall.code == "compatibility.producer_ready" for report in reports)
    assert all(
        dict(_check(report, "reader_distribution").safe_fields)[
            "installed_distribution_version"
        ]
        == "99.123.456"
        for report in reports
    )


def test_readiness_uses_core_profile_discovery_surface_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[tuple[object, ...], bool]] = []
    registry = _installed_profile_registry()

    def discover(*, explicit_profiles: tuple[object, ...], discover_installed: bool) -> PublicationProducerRegistry:
        seen.append((explicit_profiles, discover_installed))
        return registry

    monkeypatch.setattr(
        compatibility_diagnostics,
        "build_publication_producer_registry",
        discover,
    )
    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        lambda _name: "1.2.3",
    )
    monkeypatch.setattr(
        compatibility_diagnostics,
        "import_module",
        _ready_public_module,
    )

    reports = diagnose_installed_producer_readiness()

    assert seen == [((), True)]
    assert all(_check(report, "core_profile").outcome == "ready" for report in reports)


def test_missing_distributions_are_unavailable_without_public_api_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing(_name: str) -> str:
        raise compatibility_diagnostics.metadata.PackageNotFoundError

    imports: list[str] = []

    def forbidden_import(name: str) -> object:
        imports.append(name)
        raise AssertionError("producer module must not be imported without its distribution")

    monkeypatch.setattr(compatibility_diagnostics.metadata, "version", missing)
    monkeypatch.setattr(compatibility_diagnostics, "import_module", forbidden_import)

    reports = diagnose_installed_producer_readiness(
        producer_registry=_installed_profile_registry()
    )

    assert imports == []
    for report in reports:
        distribution = _check(report, "reader_distribution")
        reader_api = _check(report, "reader_api")
        artifact_api = _check(report, "artifact_api")
        assert distribution.code == "reader.unavailable"
        assert reader_api.code == "reader.unavailable"
        assert reader_api.outcome == "not_checked"
        if report.producer_module_id == "scoreform":
            assert artifact_api.outcome == "not_applicable"
            assert artifact_api.code == "compatibility.artifact_api_not_applicable"
        else:
            assert artifact_api.outcome == "not_checked"
            assert artifact_api.code == "compatibility.artifact_api_unavailable"
        assert not report.ready


def test_scoreform_artifact_api_is_not_applicable_not_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imports: list[str] = []

    def record_import(name: str) -> object:
        imports.append(name)
        return _ready_public_module(name)

    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        lambda _name: "4.5.6",
    )
    monkeypatch.setattr(compatibility_diagnostics, "import_module", record_import)

    reports = diagnose_installed_producer_readiness(
        producer_registry=_installed_profile_registry()
    )
    scoreform = next(report for report in reports if report.producer_module_id == "scoreform")
    artifact = _check(scoreform, "artifact_api")

    assert artifact.outcome == "not_applicable"
    assert artifact.code == "compatibility.artifact_api_not_applicable"
    assert "scoreform.academic_result_artifacts" not in imports


def test_core_profile_discovery_failure_is_sanitized_and_does_not_abort_independent_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_discovery(**_kwargs: object) -> PublicationProducerRegistry:
        raise RuntimeError("PRIVATE_ENTRY_POINT_PATH_AND_STUDENT_DATA")

    monkeypatch.setattr(
        compatibility_diagnostics,
        "build_publication_producer_registry",
        fail_discovery,
    )
    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        lambda _name: "7.8.9",
    )
    monkeypatch.setattr(
        compatibility_diagnostics,
        "import_module",
        _ready_public_module,
    )

    reports = diagnose_installed_producer_readiness()

    for report in reports:
        profile = _check(report, "core_profile")
        assert profile.code == "compatibility.core_profile_discovery_failed"
        assert profile.outcome == "failed"
        assert "PRIVATE" not in profile.summary
        assert "PRIVATE" not in profile.next_action
        assert _check(report, "reader_api").outcome == "ready"
        assert not report.ready


def test_reader_api_incompatibility_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def import_with_scoreform_failure(name: str) -> object:
        if name == "scoreform.academic_result_reader":
            raise RuntimeError("PRIVATE_STUDENT_RESPONSE_AND_NATIVE_PATH")
        return _ready_public_module(name)

    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        lambda _name: "99.0.0",
    )
    monkeypatch.setattr(
        compatibility_diagnostics,
        "import_module",
        import_with_scoreform_failure,
    )

    reports = diagnose_installed_producer_readiness(
        producer_registry=_installed_profile_registry()
    )
    scoreform = next(report for report in reports if report.producer_module_id == "scoreform")
    reader = _check(scoreform, "reader_api")

    assert reader.code == "reader.incompatible"
    assert reader.outcome == "unavailable"
    assert "PRIVATE" not in reader.summary
    assert "PRIVATE" not in reader.next_action
    assert all("PRIVATE" not in value for _, value in reader.safe_fields)


def test_quillan_and_concord_artifact_module_failures_are_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def import_with_artifact_failure(name: str) -> object:
        if name in {
            "quillan.academic_result_artifacts",
            "concord.academic_result_artifacts",
        }:
            raise RuntimeError("PRIVATE_ARTIFACT_PATH_AND_FEEDBACK")
        return _ready_public_module(name)

    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        lambda _name: "2.0.0",
    )
    monkeypatch.setattr(
        compatibility_diagnostics,
        "import_module",
        import_with_artifact_failure,
    )

    reports = diagnose_installed_producer_readiness(
        producer_registry=_installed_profile_registry()
    )

    for producer in ("concord", "quillan"):
        report = next(item for item in reports if item.producer_module_id == producer)
        artifact = _check(report, "artifact_api")
        assert artifact.code == "compatibility.artifact_api_unavailable"
        assert artifact.outcome == "unavailable"
        assert "PRIVATE" not in artifact.summary
        assert "PRIVATE" not in artifact.next_action
        assert not report.ready


def test_missing_live_adapter_is_reported_without_fixture_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordinary = build_adapter_registry()
    without_quillan = ProducerProjectionAdapterRegistry(
        adapters=tuple(
            adapter
            for adapter in ordinary.adapters
            if adapter.declaration.support_key.producer_module_id != "quillan"
        )
    )
    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        lambda _name: "3.0.0",
    )
    monkeypatch.setattr(
        compatibility_diagnostics,
        "import_module",
        _ready_public_module,
    )

    reports = diagnose_installed_producer_readiness(
        adapter_registry=without_quillan,
        producer_registry=_installed_profile_registry(),
    )
    quillan = next(report for report in reports if report.producer_module_id == "quillan")
    adapter = _check(quillan, "adapter_registry")

    assert adapter.code == "compatibility.live_adapter_missing"
    assert adapter.outcome == "unavailable"
    assert "fixture" in adapter.next_action
    assert not quillan.ready


@pytest.mark.parametrize("reader_value", (SimpleNamespace(), SimpleNamespace(read_academic_result_manifest=object())))
def test_reader_symbol_missing_or_noncallable_is_incompatible(
    monkeypatch: pytest.MonkeyPatch,
    reader_value: object,
) -> None:
    def import_with_bad_quillan_reader(name: str) -> object:
        if name == "quillan.academic_result_reader":
            return reader_value
        return _ready_public_module(name)

    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        lambda _name: "8.8.8",
    )
    monkeypatch.setattr(
        compatibility_diagnostics,
        "import_module",
        import_with_bad_quillan_reader,
    )

    reports = diagnose_installed_producer_readiness(
        producer_registry=_installed_profile_registry()
    )
    quillan = next(report for report in reports if report.producer_module_id == "quillan")
    reader = _check(quillan, "reader_api")

    assert reader.code == "reader.incompatible"
    assert reader.outcome == "unavailable"
    assert not quillan.ready


def test_missing_core_profile_is_distinct_from_reader_readiness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    full = _installed_profile_registry()
    without_concord = PublicationProducerRegistry(
        tuple(profile for profile in full.profiles if profile.module_id != "concord")
    )
    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        lambda _name: "5.5.5",
    )
    monkeypatch.setattr(
        compatibility_diagnostics,
        "import_module",
        _ready_public_module,
    )

    reports = diagnose_installed_producer_readiness(producer_registry=without_concord)
    concord = next(report for report in reports if report.producer_module_id == "concord")

    profile = _check(concord, "core_profile")
    assert profile.code == "compatibility.core_profile_missing"
    assert profile.outcome == "unavailable"
    assert _check(concord, "reader_api").outcome == "ready"
    assert _check(concord, "artifact_api").outcome == "ready"
    assert not concord.ready


def test_quillan_and_concord_artifact_modules_are_applicable_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        lambda _name: "6.6.6",
    )
    monkeypatch.setattr(
        compatibility_diagnostics,
        "import_module",
        _ready_public_module,
    )

    reports = diagnose_installed_producer_readiness(
        producer_registry=_installed_profile_registry()
    )

    for producer in ("concord", "quillan"):
        report = next(item for item in reports if item.producer_module_id == producer)
        artifact = _check(report, "artifact_api")
        assert artifact.code == "compatibility.artifact_api_ready"
        assert artifact.outcome == "ready"
        assert dict(artifact.safe_fields)["artifact_access_mode"] == "producer_authorized_bytes"
