from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from pds_core.academic_work_registration_storage import (
    AcademicWorkRegistrationNotFoundError,
)
from pds_core.publication_compatibility import (
    PublicationContractSupport,
    PublicationProducerProfile,
    PublicationProducerRegistry,
    SourceRecordContractSupport,
)
from pds_core.publication_records import PublicationRecord
from pds_core.registry_services import (
    AcademicWorkRegistrationRequest,
    PublicationManifestRequest,
    PublicationWithdrawalRequest,
    publish_manifest_revision,
    register_academic_work,
    supersede_manifest_revision,
    withdraw_publication,
)
from pds_core.routes import module_work_dir
from pds_core.routing_models import ModuleRecordRef, ModuleWorkRef
from pds_core.workspace import ensure_workspace_root

import vitrine.compatibility_diagnostics as compatibility_diagnostics
import vitrine.publication_diagnostics as publication_diagnostics
from vitrine.development_adapters import SCOREFORM_FIXTURE_SUPPORT_KEY
from vitrine.producer_adapters import (
    ProducerAdapterSupportKey,
    ProducerProjectionAdapterDeclaration,
    ProducerProjectionAdapterRegistry,
    ProducerProjectionBatch,
    ProducerProjectionError,
    ProducerReaderDescriptor,
    ProducerReaderError,
)
from vitrine.producer_reader_services import (
    SourceReadAuthorizationDecision,
    SourceReadAuthorizationRequest,
)
from vitrine.publication_diagnostics import (
    COMPATIBILITY_SOURCE_READ_OPERATION,
    diagnose_publication_compatibility,
    diagnose_publication_read_probe,
)
from vitrine.released_producer_contracts import (
    CONCORD_LIVE_SUPPORT_KEY,
    QUILLAN_LIVE_SUPPORT_KEY,
    RELEASED_PRODUCER_CONTRACTS,
    SCOREFORM_LIVE_SUPPORT_KEY,
)


def _profile_registry(
    *,
    scoreform_manifest_contract: str | None = None,
) -> PublicationProducerRegistry:
    profiles: list[PublicationProducerProfile] = []
    for audit in RELEASED_PRODUCER_CONTRACTS:
        key = audit.support_key
        source_contracts: tuple[SourceRecordContractSupport, ...] = ()
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
        manifest_contract = key.manifest_contract_version
        if audit.producer_module_id == "scoreform" and scoreform_manifest_contract:
            manifest_contract = scoreform_manifest_contract
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
                        manifest_contract_versions=frozenset({manifest_contract}),
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


def _ready_reader_module(name: str) -> object:
    if name.endswith("academic_result_reader"):
        return SimpleNamespace(read_academic_result_manifest=lambda value: value)
    raise AssertionError(f"unexpected producer module import: {name}")


def _publication_source(
    key: ProducerAdapterSupportKey,
) -> ModuleRecordRef | None:
    if key.source_record_kind is None:
        return None
    assert key.source_record_contract_version is not None
    return ModuleRecordRef(
        key.producer_module_id,
        key.source_record_kind,
        f"{key.source_record_kind}_alpha",
        key.source_record_contract_version,
    )


def _registration_sources(
    key: ProducerAdapterSupportKey,
    publication_source: ModuleRecordRef | None,
) -> tuple[ModuleRecordRef, ...]:
    if key.producer_module_id == "quillan":
        return (ModuleRecordRef("quillan", "assignment", "assignment_alpha", "2"),)
    return () if publication_source is None else (publication_source,)


def _publish(
    base: Path,
    key: ProducerAdapterSupportKey,
    *,
    manifest_contract_version: str | None = None,
) -> tuple[Path, PublicationRecord, Path]:
    workspace = ensure_workspace_root(base / "workspace", create=True)
    work = ModuleWorkRef(
        key.producer_module_id,
        "class_alpha",
        f"{key.producer_module_id}_work",
    )
    publication_source = _publication_source(key)
    module_work_dir(workspace, work).mkdir(parents=True, exist_ok=True)
    assert key.producer_contract_version is not None
    registration = register_academic_work(
        workspace,
        AcademicWorkRegistrationRequest(
            work=work,
            producer_contract_version=key.producer_contract_version,
            title=f"Synthetic {key.producer_module_id} work",
            work_kind="assignment",
            academic_intent="formative",
            lifecycle="active",
            source_records=_registration_sources(key, publication_source),
        ),
    ).registration
    record_set_id = f"{key.producer_module_id}_results"
    manifest_path = (
        module_work_dir(workspace, work)
        / "exports"
        / "manifests"
        / record_set_id
        / "1.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(b"{}\n")
    publication = publish_manifest_revision(
        workspace,
        PublicationManifestRequest(
            work=work,
            source_record=publication_source,
            publication_kind=key.publication_kind,
            capabilities=key.required_capabilities,
            record_set_id=record_set_id,
            record_set_revision=1,
            manifest_contract_version=(
                manifest_contract_version or key.manifest_contract_version
            ),
            manifest_path=manifest_path.relative_to(workspace).as_posix(),
            academic_work_registration_revision=registration.registration_revision,
        ),
    ).publication
    return workspace, publication, manifest_path


def _supersede(
    workspace: Path,
    publication: PublicationRecord,
    key: ProducerAdapterSupportKey,
) -> PublicationRecord:
    first = publication
    work = first.work
    publication_source = _publication_source(key)
    manifest_path = (
        module_work_dir(workspace, work)
        / "exports"
        / "manifests"
        / first.record_set_id
        / "2.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(b'{"revision":2}\n')
    return supersede_manifest_revision(
        workspace,
        PublicationManifestRequest(
            work=work,
            source_record=publication_source,
            publication_kind=key.publication_kind,
            capabilities=key.required_capabilities,
            record_set_id=first.record_set_id,
            record_set_revision=2,
            manifest_contract_version=key.manifest_contract_version,
            manifest_path=manifest_path.relative_to(workspace).as_posix(),
            academic_work_registration_revision=(
                first.academic_work_registration_revision
            ),
        ),
        expected_current_publication_id=first.publication_id,
    ).publication


def _check(report: object, stage: str) -> object:
    return next(item for item in report.checks if item.stage == stage)


def test_metadata_preflight_is_ready_without_reading_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, publication, manifest_path = _publish(
        tmp_path, SCOREFORM_LIVE_SUPPORT_KEY
    )
    manifest_path.unlink()
    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        lambda _name: "99.123.456",
    )
    monkeypatch.setattr(
        compatibility_diagnostics,
        "import_module",
        _ready_reader_module,
    )

    report = diagnose_publication_compatibility(
        workspace,
        publication.publication_id,
        producer_registry=_profile_registry(),
    )

    assert report.ready
    assert report.overall.code == "compatibility.publication_ready"
    assert tuple(item.stage for item in report.checks) == (
        "canonical_publication",
        "registration",
        "series_state",
        "core_profile",
        "core_compatibility",
        "adapter_support",
        "reader_distribution",
        "reader_api",
    )
    assert (
        dict(_check(report, "reader_distribution").safe_fields)[
            "installed_distribution_version"
        ]
        == "99.123.456"
    )
    assert all(
        "manifest_path" not in dict(item.safe_fields)
        and "manifest_digest" not in dict(item.safe_fields)
        for item in report.checks
    )


def test_missing_canonical_publication_stops_immediately(tmp_path: Path) -> None:
    workspace = ensure_workspace_root(tmp_path / "workspace", create=True)

    report = diagnose_publication_compatibility(
        workspace,
        "pub_00000000000000000000000000000000",
        producer_registry=_profile_registry(),
    )

    assert report.overall.code == "candidate.canonical_publication_missing"
    assert len(report.checks) == 1
    assert report.checks[0].stage == "canonical_publication"


def test_withdrawn_publication_is_not_selectable_and_does_not_probe_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, publication, _ = _publish(tmp_path, SCOREFORM_LIVE_SUPPORT_KEY)
    withdraw_publication(
        workspace,
        PublicationWithdrawalRequest(
            publication_id=publication.publication_id,
            reason="Synthetic withdrawal",
        ),
    )
    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        lambda _name: (_ for _ in ()).throw(
            AssertionError("reader readiness must not run")
        ),
    )

    report = diagnose_publication_compatibility(
        workspace,
        publication.publication_id,
        producer_registry=_profile_registry(),
    )

    assert report.overall.outcome == "not_selectable"
    assert report.overall.code == "candidate.publication_not_selectable"
    series = report.checks[-1]
    assert series.stage == "series_state"
    assert series.reason_codes == ("compatibility.publication_withdrawn",)
    assert dict(series.safe_fields)["observed_series_state"] == "withdrawn_head"


def test_historical_publication_reports_current_head_without_substitution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, first, _ = _publish(tmp_path, SCOREFORM_LIVE_SUPPORT_KEY)
    second = _supersede(workspace, first, SCOREFORM_LIVE_SUPPORT_KEY)
    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        lambda _name: (_ for _ in ()).throw(
            AssertionError("reader readiness must not run")
        ),
    )

    report = diagnose_publication_compatibility(
        workspace,
        first.publication_id,
        producer_registry=_profile_registry(),
    )

    series = report.checks[-1]
    assert series.reason_codes == ("compatibility.publication_historical",)
    assert dict(series.safe_fields)["current_series_head_publication_id"] == (
        second.publication_id
    )
    assert report.publication_id == first.publication_id


def test_core_contract_codes_remain_authoritative(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    future = "scoreform_academic_result_manifest_v2"
    workspace, publication, _ = _publish(
        tmp_path,
        SCOREFORM_LIVE_SUPPORT_KEY,
        manifest_contract_version=future,
    )
    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        lambda _name: (_ for _ in ()).throw(
            AssertionError("reader readiness must not run")
        ),
    )

    report = diagnose_publication_compatibility(
        workspace,
        publication.publication_id,
        producer_registry=_profile_registry(),
    )

    core = report.checks[-1]
    assert core.stage == "core_compatibility"
    assert core.code == "contracts.manifest_version_incompatible"
    assert core.reason_codes == ("contracts.manifest_version_incompatible",)
    assert not any(item.stage == "adapter_support" for item in report.checks)


def test_core_compatible_future_contract_can_still_be_vitrine_unsupported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    future = "scoreform_academic_result_manifest_v2"
    workspace, publication, _ = _publish(
        tmp_path,
        SCOREFORM_LIVE_SUPPORT_KEY,
        manifest_contract_version=future,
    )
    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        lambda _name: (_ for _ in ()).throw(
            AssertionError("reader readiness must not run")
        ),
    )

    report = diagnose_publication_compatibility(
        workspace,
        publication.publication_id,
        producer_registry=_profile_registry(scoreform_manifest_contract=future),
    )

    assert _check(report, "core_compatibility").outcome == "supported"
    adapter = report.checks[-1]
    assert adapter.stage == "adapter_support"
    assert adapter.code == "adapter.unsupported_contract"
    assert adapter.reason_codes == ("compatibility.manifest_contract_mismatch",)


def test_missing_producer_profile_is_distinct_from_adapter_support(
    tmp_path: Path,
) -> None:
    workspace, publication, _ = _publish(tmp_path, SCOREFORM_LIVE_SUPPORT_KEY)

    report = diagnose_publication_compatibility(
        workspace,
        publication.publication_id,
        producer_registry=PublicationProducerRegistry(profiles=()),
    )

    assert report.checks[-1].stage == "core_profile"
    assert report.checks[-1].code == "candidate.producer_profile_missing"
    assert not any(item.stage == "adapter_support" for item in report.checks)


def test_missing_reader_distribution_is_reported_after_supported_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, publication, _ = _publish(tmp_path, SCOREFORM_LIVE_SUPPORT_KEY)

    def missing_distribution(_name: str) -> str:
        raise compatibility_diagnostics.metadata.PackageNotFoundError

    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        missing_distribution,
    )

    report = diagnose_publication_compatibility(
        workspace,
        publication.publication_id,
        producer_registry=_profile_registry(),
    )

    assert _check(report, "adapter_support").outcome == "supported"
    assert _check(report, "reader_distribution").code == "reader.unavailable"
    assert _check(report, "reader_api").outcome == "not_checked"
    assert report.overall.code == "reader.unavailable"


def test_fixture_publication_identity_never_masquerades_as_live(
    tmp_path: Path,
) -> None:
    workspace, publication, _ = _publish(
        tmp_path, SCOREFORM_FIXTURE_SUPPORT_KEY
    )

    report = diagnose_publication_compatibility(
        workspace,
        publication.publication_id,
        producer_registry=PublicationProducerRegistry(profiles=()),
    )

    fixture = report.checks[-1]
    assert fixture.stage == "fixture_boundary"
    assert fixture.code == "adapter.fixture_not_enabled"
    assert fixture.producer_module_id == "vitrine_scoreform_fixture"
    assert not any(item.stage == "core_profile" for item in report.checks)


def test_registration_missing_stops_before_series_and_compatibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, publication, _ = _publish(tmp_path, SCOREFORM_LIVE_SUPPORT_KEY)

    def missing_registration(*_args: object, **_kwargs: object) -> object:
        raise AcademicWorkRegistrationNotFoundError("PRIVATE registration path")

    monkeypatch.setattr(
        publication_diagnostics,
        "load_academic_work_registration_revision",
        missing_registration,
    )

    report = diagnose_publication_compatibility(
        workspace,
        publication.publication_id,
        producer_registry=_profile_registry(),
    )

    assert report.checks[-1].stage == "registration"
    assert report.checks[-1].code == "candidate.registration_missing"
    assert "PRIVATE" not in report.checks[-1].summary
    assert len(report.checks) == 2


def test_series_conflict_stops_before_profile_and_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, publication, _ = _publish(tmp_path, SCOREFORM_LIVE_SUPPORT_KEY)
    second = SimpleNamespace(
        publication_id="pub_11111111111111111111111111111111",
        supersedes_publication_id=None,
    )
    monkeypatch.setattr(
        publication_diagnostics,
        "list_publication_record_set",
        lambda *_args: (publication, second),
    )

    report = diagnose_publication_compatibility(
        workspace,
        publication.publication_id,
        producer_registry=_profile_registry(),
    )

    assert report.checks[-1].stage == "series_state"
    assert report.checks[-1].code == "candidate.series_conflict"
    assert dict(report.checks[-1].safe_fields)["head_count"] == "2"
    assert len(report.checks) == 3


class _ProbeReader:
    def __init__(self, *, failure: ProducerReaderError | None = None) -> None:
        self.failure = failure
        self.seen: list[bytes] = []
        self.descriptor = ProducerReaderDescriptor(
            public_reader_id="test_compatibility_probe_reader",
            reader_contract_version="test_compatibility_probe_reader_v1",
            package_identity="synthetic compatibility probe reader",
            integration_kind="live",
        )

    def read(self, value: bytes) -> object:
        self.seen.append(value)
        if self.failure is not None:
            raise self.failure
        return SimpleNamespace(validated=True)


class _ProbeAdapter:
    def __init__(
        self,
        key: ProducerAdapterSupportKey,
        reader: _ProbeReader,
        *,
        projection_failure: ProducerProjectionError | None = None,
    ) -> None:
        self._reader = reader
        self._failure = projection_failure
        self.seen: list[object] = []
        self._declaration = ProducerProjectionAdapterDeclaration(
            adapter_id=f"test_{key.producer_module_id}_compatibility_probe_adapter",
            adapter_contract_version="test_compatibility_probe_adapter_v1",
            candidate_projection_contract_version="vitrine_candidate_projection_v1",
            support_key=key,
            public_reader_id=reader.descriptor.public_reader_id,
            reader_contract_version=reader.descriptor.reader_contract_version,
            reader_package_identity=reader.descriptor.package_identity,
            supported_source_families=("result",),
            supported_representation_families=("result_summary",),
            diagnostic_contract_version="vitrine_adapter_diagnostic_v1",
            integration_kind="live",
        )

    @property
    def declaration(self) -> ProducerProjectionAdapterDeclaration:
        return self._declaration

    @property
    def reader(self) -> _ProbeReader:
        return self._reader

    def project(self, public_model: object) -> ProducerProjectionBatch:
        self.seen.append(public_model)
        if self._failure is not None:
            raise self._failure
        return ProducerProjectionBatch(
            adapter_id=self.declaration.adapter_id,
            adapter_contract_version=self.declaration.adapter_contract_version,
            reader_id=self.declaration.public_reader_id,
            reader_contract_version=self.declaration.reader_contract_version,
            candidate_projection_contract_version=(
                self.declaration.candidate_projection_contract_version
            ),
            support_key=self.declaration.support_key,
            projected_sources=(),
            diagnostic_codes=(),
        )


class _ProbeAuthorizationGate:
    def __init__(self, outcome: str = "allowed", *, raises: bool = False) -> None:
        self.outcome = outcome
        self.raises = raises
        self.requests: list[SourceReadAuthorizationRequest] = []

    def authorize(
        self, request: SourceReadAuthorizationRequest
    ) -> SourceReadAuthorizationDecision:
        self.requests.append(request)
        if self.raises:
            raise RuntimeError("PRIVATE authorization provider detail")
        return SourceReadAuthorizationDecision(
            outcome=self.outcome,
            reason_codes=("fixture_permission",),
        )


def _probe_registry(
    key: ProducerAdapterSupportKey,
    reader: _ProbeReader,
    *,
    projection_failure: ProducerProjectionError | None = None,
) -> tuple[ProducerProjectionAdapterRegistry, _ProbeAdapter]:
    adapter = _ProbeAdapter(
        key,
        reader,
        projection_failure=projection_failure,
    )
    return ProducerProjectionAdapterRegistry(adapters=(adapter,)), adapter


def _ready_probe_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    reader: _ProbeReader,
) -> None:
    monkeypatch.setattr(
        compatibility_diagnostics.metadata,
        "version",
        lambda _name: "99.123.456",
    )
    monkeypatch.setattr(
        compatibility_diagnostics,
        "import_module",
        _ready_reader_module,
    )
    monkeypatch.setattr(
        publication_diagnostics,
        "build_audited_installed_producer_reader",
        lambda _producer: reader,
    )


@pytest.mark.parametrize(
    "key",
    (
        SCOREFORM_LIVE_SUPPORT_KEY,
        QUILLAN_LIVE_SUPPORT_KEY,
        CONCORD_LIVE_SUPPORT_KEY,
    ),
)
def test_authorized_read_probe_succeeds_for_all_live_contract_shapes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    key: ProducerAdapterSupportKey,
) -> None:
    workspace, publication, _ = _publish(tmp_path, key)
    reader = _ProbeReader()
    registry, adapter = _probe_registry(key, reader)
    _ready_probe_dependencies(monkeypatch, reader)
    gate = _ProbeAuthorizationGate()

    report = diagnose_publication_read_probe(
        workspace,
        publication.publication_id,
        portfolio_id="portfolio_probe",
        portfolio_subject_id="subject_probe",
        purpose="improvement",
        authorization_gate=gate,
        producer_registry=_profile_registry(),
        adapter_registry=registry,
    )

    assert report.ready
    assert report.overall.code == "compatibility.read_probe_ready"
    assert report.projected_source_count == 0
    assert reader.seen == [b"{}\n"]
    assert len(adapter.seen) == 1
    assert len(gate.requests) == 1
    assert gate.requests[0].operation == COMPATIBILITY_SOURCE_READ_OPERATION
    assert gate.requests[0].publication_id == publication.publication_id
    assert _check(report, "source_authorization").code == (
        "compatibility.source_read_allowed"
    )
    assert _check(report, "manifest_integrity").code == (
        "compatibility.manifest_verified"
    )
    assert _check(report, "producer_reader").code == (
        "compatibility.reader_invocation_succeeded"
    )
    assert _check(report, "projection").code == "compatibility.projection_succeeded"


@pytest.mark.parametrize("outcome", ("denied", "unresolved"))
def test_nonallowed_probe_stops_before_manifest_inspection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    workspace, publication, _ = _publish(tmp_path, SCOREFORM_LIVE_SUPPORT_KEY)
    reader = _ProbeReader()
    registry, _ = _probe_registry(SCOREFORM_LIVE_SUPPORT_KEY, reader)
    _ready_probe_dependencies(monkeypatch, reader)
    monkeypatch.setattr(
        publication_diagnostics,
        "read_verified_publication_manifest_bytes",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("manifest must not be inspected")
        ),
    )
    gate = _ProbeAuthorizationGate(outcome)

    report = diagnose_publication_read_probe(
        workspace,
        publication.publication_id,
        portfolio_id="portfolio_probe",
        portfolio_subject_id="subject_probe",
        purpose="improvement",
        authorization_gate=gate,
        producer_registry=_profile_registry(),
        adapter_registry=registry,
    )

    expected = (
        "source_read.authorization_denied"
        if outcome == "denied"
        else "source_read.authorization_unresolved"
    )
    assert report.overall.code == expected
    assert report.checks[-1].code == expected
    assert dict(report.checks[-1].safe_fields)["protected_source_inspected"] == "no"
    assert reader.seen == []


def test_authorization_gate_exception_is_sanitized_and_stops_before_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, publication, _ = _publish(tmp_path, SCOREFORM_LIVE_SUPPORT_KEY)
    reader = _ProbeReader()
    registry, _ = _probe_registry(SCOREFORM_LIVE_SUPPORT_KEY, reader)
    _ready_probe_dependencies(monkeypatch, reader)
    monkeypatch.setattr(
        publication_diagnostics,
        "read_verified_publication_manifest_bytes",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("manifest must not be inspected")
        ),
    )

    report = diagnose_publication_read_probe(
        workspace,
        publication.publication_id,
        portfolio_id="portfolio_probe",
        portfolio_subject_id="subject_probe",
        purpose="improvement",
        authorization_gate=_ProbeAuthorizationGate(raises=True),
        producer_registry=_profile_registry(),
        adapter_registry=registry,
    )

    assert report.overall.code == "source_read.authorization_unresolved"
    assert "PRIVATE" not in report.overall.summary
    assert "PRIVATE" not in report.checks[-1].summary


def test_manifest_missing_is_reported_only_after_allowed_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, publication, manifest_path = _publish(
        tmp_path, SCOREFORM_LIVE_SUPPORT_KEY
    )
    reader = _ProbeReader()
    registry, _ = _probe_registry(SCOREFORM_LIVE_SUPPORT_KEY, reader)
    _ready_probe_dependencies(monkeypatch, reader)
    manifest_path.unlink()
    gate = _ProbeAuthorizationGate()

    report = diagnose_publication_read_probe(
        workspace,
        publication.publication_id,
        portfolio_id="portfolio_probe",
        portfolio_subject_id="subject_probe",
        purpose="improvement",
        authorization_gate=gate,
        producer_registry=_profile_registry(),
        adapter_registry=registry,
    )

    assert report.overall.code == "source_read.manifest_missing"
    assert _check(report, "source_authorization").outcome == "ready"
    assert report.checks[-1].code == "source_read.manifest_missing"
    assert reader.seen == []


def test_manifest_integrity_failure_stops_before_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, publication, manifest_path = _publish(
        tmp_path, SCOREFORM_LIVE_SUPPORT_KEY
    )
    reader = _ProbeReader()
    registry, _ = _probe_registry(SCOREFORM_LIVE_SUPPORT_KEY, reader)
    _ready_probe_dependencies(monkeypatch, reader)
    manifest_path.write_bytes(b'{"tampered":true}\n')

    report = diagnose_publication_read_probe(
        workspace,
        publication.publication_id,
        portfolio_id="portfolio_probe",
        portfolio_subject_id="subject_probe",
        purpose="improvement",
        authorization_gate=_ProbeAuthorizationGate(),
        producer_registry=_profile_registry(),
        adapter_registry=registry,
    )

    assert report.overall.code == "source_read.manifest_integrity_failed"
    assert reader.seen == []


def test_reader_failure_preserves_code_and_sanitizes_private_exception_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, publication, _ = _publish(tmp_path, SCOREFORM_LIVE_SUPPORT_KEY)
    failure = ProducerReaderError(
        "reader.validation_failed",
        "producer_reader",
        "PRIVATE_STUDENT_RESPONSE",
        producer_module_id="scoreform",
    )
    reader = _ProbeReader(failure=failure)
    registry, _ = _probe_registry(SCOREFORM_LIVE_SUPPORT_KEY, reader)
    _ready_probe_dependencies(monkeypatch, reader)

    report = diagnose_publication_read_probe(
        workspace,
        publication.publication_id,
        portfolio_id="portfolio_probe",
        portfolio_subject_id="subject_probe",
        purpose="improvement",
        authorization_gate=_ProbeAuthorizationGate(),
        producer_registry=_profile_registry(),
        adapter_registry=registry,
    )

    assert report.overall.code == "reader.validation_failed"
    assert report.checks[-1].code == "reader.validation_failed"
    assert "PRIVATE_STUDENT_RESPONSE" not in report.checks[-1].summary
    assert not any(item.stage == "projection" for item in report.checks)


def test_projection_failure_preserves_code_and_sanitizes_private_exception_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, publication, _ = _publish(tmp_path, SCOREFORM_LIVE_SUPPORT_KEY)
    reader = _ProbeReader()
    projection_failure = ProducerProjectionError(
        "projection.failed",
        "projection",
        "PRIVATE_PROJECTED_CONTENT",
        adapter_id="test_scoreform_compatibility_probe_adapter",
        producer_module_id="scoreform",
    )
    registry, _ = _probe_registry(
        SCOREFORM_LIVE_SUPPORT_KEY,
        reader,
        projection_failure=projection_failure,
    )
    _ready_probe_dependencies(monkeypatch, reader)

    report = diagnose_publication_read_probe(
        workspace,
        publication.publication_id,
        portfolio_id="portfolio_probe",
        portfolio_subject_id="subject_probe",
        purpose="improvement",
        authorization_gate=_ProbeAuthorizationGate(),
        producer_registry=_profile_registry(),
        adapter_registry=registry,
    )

    assert report.overall.code == "projection.failed"
    assert report.checks[-1].code == "projection.failed"
    assert "PRIVATE_PROJECTED_CONTENT" not in report.checks[-1].summary


def test_metadata_failure_stops_before_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, publication, _ = _publish(tmp_path, SCOREFORM_LIVE_SUPPORT_KEY)
    withdraw_publication(
        workspace,
        PublicationWithdrawalRequest(
            publication_id=publication.publication_id,
            reason="Synthetic withdrawal before probe",
        ),
    )
    reader = _ProbeReader()
    registry, _ = _probe_registry(SCOREFORM_LIVE_SUPPORT_KEY, reader)
    _ready_probe_dependencies(monkeypatch, reader)
    gate = _ProbeAuthorizationGate()

    report = diagnose_publication_read_probe(
        workspace,
        publication.publication_id,
        portfolio_id="portfolio_probe",
        portfolio_subject_id="subject_probe",
        purpose="improvement",
        authorization_gate=gate,
        producer_registry=_profile_registry(),
        adapter_registry=registry,
    )

    assert report.overall.code == "candidate.publication_not_selectable"
    assert gate.requests == []
    assert reader.seen == []
