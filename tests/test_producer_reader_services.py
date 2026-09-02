from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from pds_core.registry_services import get_canonical_publication_record

import vitrine.producer_reader_services as producer_reader_services
from scripts.candidate_fixture_support import build_candidate_fixture_workspace
from vitrine.producer_adapters import ProducerReaderError, build_adapter_registry
from vitrine.producer_reader_services import (
    INSTALLED_PRODUCER_READER_CONTRACT_VERSION,
    PRODUCER_READER_SERVICE_CONTRACT_VERSION,
    InstalledProducerManifestReader,
    ProducerReaderServiceError,
    SourceReadAuthorizationDecision,
    SourceReadAuthorizationGate,
    SourceReadAuthorizationRequest,
    authorize_source_read,
    build_audited_installed_producer_reader,
    build_audited_installed_producer_readers,
    read_authorized_producer_manifest,
    read_verified_publication_manifest_bytes,
)
from vitrine.released_producer_contracts import (
    RELEASED_PRODUCER_CONTRACT_BY_MODULE,
    SCOREFORM_0_11_0_AUDIT,
)


def _request() -> SourceReadAuthorizationRequest:
    return SourceReadAuthorizationRequest(
        portfolio_id="portfolio_fixture",
        portfolio_subject_id="subject_fixture",
        publication_id="pub_0123456789abcdef0123456789abcdef",
        operation="candidate_source_read",
        purpose="improvement",
    )


class _StaticGate:
    def __init__(self, decision: object) -> None:
        self.decision = decision
        self.requests: list[SourceReadAuthorizationRequest] = []

    def authorize(
        self,
        request: SourceReadAuthorizationRequest,
    ) -> SourceReadAuthorizationDecision:
        self.requests.append(request)
        return cast(SourceReadAuthorizationDecision, self.decision)


class _FailingGate:
    def authorize(
        self,
        request: SourceReadAuthorizationRequest,
    ) -> SourceReadAuthorizationDecision:
        raise RuntimeError("PRIVATE authorization provider detail")


def test_source_read_contract_is_versioned_and_decisions_are_normalized() -> None:
    assert (
        PRODUCER_READER_SERVICE_CONTRACT_VERSION
        == "vitrine_producer_reader_service_v1"
    )
    decision = SourceReadAuthorizationDecision(
        outcome="allowed",
        reason_codes=("z_reason", "a_reason"),
    )
    assert decision.reason_codes == ("z_reason", "a_reason")
    with pytest.raises(ProducerReaderServiceError) as caught:
        SourceReadAuthorizationDecision(outcome="implicit")
    assert caught.value.code == "source_read.invalid_request"


def test_allowed_source_read_returns_the_exact_decision() -> None:
    request = _request()
    decision = SourceReadAuthorizationDecision(
        outcome="allowed",
        reason_codes=("fixture_permission",),
    )
    gate = _StaticGate(decision)
    assert authorize_source_read(gate, request) is decision
    assert gate.requests == [request]


@pytest.mark.parametrize(
    ("outcome", "code"),
    (
        ("denied", "source_read.authorization_denied"),
        ("unresolved", "source_read.authorization_unresolved"),
    ),
)
def test_non_allowed_source_read_fails_closed(outcome: str, code: str) -> None:
    gate = _StaticGate(SourceReadAuthorizationDecision(outcome=outcome))
    with pytest.raises(ProducerReaderServiceError) as caught:
        authorize_source_read(gate, _request())
    assert caught.value.code == code
    assert caught.value.stage == "source_authorization"


def test_gate_exception_is_sanitized_as_unresolved() -> None:
    gate = cast(SourceReadAuthorizationGate, _FailingGate())
    with pytest.raises(ProducerReaderServiceError) as caught:
        authorize_source_read(gate, _request())
    assert caught.value.code == "source_read.authorization_unresolved"
    assert "PRIVATE" not in str(caught.value)


def test_invalid_gate_result_is_unresolved() -> None:
    gate = cast(SourceReadAuthorizationGate, _StaticGate(object()))
    with pytest.raises(ProducerReaderServiceError) as caught:
        authorize_source_read(gate, _request())
    assert caught.value.code == "source_read.authorization_unresolved"


def test_audited_installed_reader_catalog_is_lazy_and_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imports: list[str] = []

    def forbidden_import(name: str) -> object:
        imports.append(name)
        raise AssertionError("producer import must remain lazy")

    monkeypatch.setattr(producer_reader_services, "import_module", forbidden_import)

    readers = build_audited_installed_producer_readers()

    assert imports == []
    assert tuple(reader.audit.producer_module_id for reader in readers) == (
        "concord",
        "quillan",
        "scoreform",
    )
    assert all(reader.descriptor.integration_kind == "live" for reader in readers)
    assert all(
        reader.descriptor.reader_contract_version
        == INSTALLED_PRODUCER_READER_CONTRACT_VERSION
        for reader in readers
    )
    ordinary = build_adapter_registry()
    assert tuple(item.declaration.adapter_id for item in ordinary.adapters) == (
        "vitrine_scoreform_live_adapter",
    )
    assert all(
        name != "scoreform" and not name.startswith("scoreform.")
        for name in sys.modules
    )


def test_reader_binding_is_derived_from_authoritative_audit() -> None:
    reader = build_audited_installed_producer_reader("scoreform")
    audit = RELEASED_PRODUCER_CONTRACT_BY_MODULE["scoreform"]

    assert reader.audit is audit
    assert reader.descriptor.package_identity == audit.distribution_name
    assert (
        reader.descriptor.public_reader_id
        == "vitrine_installed_scoreform_academic_result_reader"
    )

    with pytest.raises(ProducerReaderError) as caught:
        build_audited_installed_producer_reader("unknown_producer")
    assert caught.value.code == "reader.incompatible"


def test_non_authoritative_reader_audit_is_rejected() -> None:
    altered = SCOREFORM_0_11_0_AUDIT.__class__(
        producer_module_id=SCOREFORM_0_11_0_AUDIT.producer_module_id,
        distribution_name=SCOREFORM_0_11_0_AUDIT.distribution_name,
        release_version=SCOREFORM_0_11_0_AUDIT.release_version,
        release_tag=SCOREFORM_0_11_0_AUDIT.release_tag,
        wheel_filename=SCOREFORM_0_11_0_AUDIT.wheel_filename,
        wheel_sha256=SCOREFORM_0_11_0_AUDIT.wheel_sha256,
        requires_python=SCOREFORM_0_11_0_AUDIT.requires_python,
        core_requirement=SCOREFORM_0_11_0_AUDIT.core_requirement,
        publication_producer_entry_point=(
            SCOREFORM_0_11_0_AUDIT.publication_producer_entry_point
        ),
        public_reader_module="scoreform.private_reader",
        public_reader_symbol=SCOREFORM_0_11_0_AUDIT.public_reader_symbol,
        advertised_capabilities=SCOREFORM_0_11_0_AUDIT.advertised_capabilities,
        support_key=SCOREFORM_0_11_0_AUDIT.support_key,
        artifact_reader_module=SCOREFORM_0_11_0_AUDIT.artifact_reader_module,
        artifact_request_kinds=SCOREFORM_0_11_0_AUDIT.artifact_request_kinds,
        artifact_representation_kinds=(
            SCOREFORM_0_11_0_AUDIT.artifact_representation_kinds
        ),
        artifact_authorization_outcomes=(
            SCOREFORM_0_11_0_AUDIT.artifact_authorization_outcomes
        ),
        artifact_access_mode=SCOREFORM_0_11_0_AUDIT.artifact_access_mode,
    )
    with pytest.raises(ProducerReaderError) as caught:
        InstalledProducerManifestReader(audit=altered)
    assert caught.value.code == "reader.incompatible"


def test_missing_distribution_is_reader_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = build_audited_installed_producer_reader("scoreform")

    def missing_distribution(_name: str) -> str:
        raise producer_reader_services.metadata.PackageNotFoundError

    monkeypatch.setattr(
        producer_reader_services.metadata,
        "version",
        missing_distribution,
    )

    with pytest.raises(ProducerReaderError) as caught:
        reader.read(b"{}\n")
    assert caught.value.code == "reader.unavailable"
    assert caught.value.stage == "reader_distribution"


def test_package_version_is_not_a_semantic_reader_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = build_audited_installed_producer_reader("scoreform")
    payload = b'{"synthetic":"manifest"}\n'
    seen: list[bytes] = []

    def public_reader(value: bytes) -> object:
        seen.append(value)
        return {"validated": True}

    monkeypatch.setattr(
        producer_reader_services.metadata,
        "version",
        lambda _name: "99.123.456",
    )
    monkeypatch.setattr(
        producer_reader_services,
        "import_module",
        lambda name: SimpleNamespace(
            **{reader.audit.public_reader_symbol: public_reader}
        ),
    )

    assert reader.read(payload) == {"validated": True}
    assert seen == [payload]


def test_missing_or_noncallable_public_api_is_reader_incompatible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = build_audited_installed_producer_reader("scoreform")
    monkeypatch.setattr(
        producer_reader_services.metadata,
        "version",
        lambda _name: SCOREFORM_0_11_0_AUDIT.release_version,
    )

    def missing_module(_name: str) -> object:
        raise ModuleNotFoundError("PRIVATE package path")

    monkeypatch.setattr(producer_reader_services, "import_module", missing_module)
    with pytest.raises(ProducerReaderError) as missing:
        reader.read(b"{}\n")
    assert missing.value.code == "reader.incompatible"
    assert "PRIVATE" not in str(missing.value)

    monkeypatch.setattr(
        producer_reader_services,
        "import_module",
        lambda _name: SimpleNamespace(),
    )
    with pytest.raises(ProducerReaderError) as missing_symbol:
        reader.read(b"{}\n")
    assert missing_symbol.value.code == "reader.incompatible"

    monkeypatch.setattr(
        producer_reader_services,
        "import_module",
        lambda _name: SimpleNamespace(
            **{reader.audit.public_reader_symbol: object()}
        ),
    )
    with pytest.raises(ProducerReaderError) as noncallable:
        reader.read(b"{}\n")
    assert noncallable.value.code == "reader.incompatible"


def test_reader_failure_is_privacy_safe_and_bytes_are_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = build_audited_installed_producer_reader("scoreform")
    monkeypatch.setattr(
        producer_reader_services.metadata,
        "version",
        lambda _name: SCOREFORM_0_11_0_AUDIT.release_version,
    )

    def failing_reader(_value: bytes) -> object:
        raise ValueError("PRIVATE_STUDENT_RESPONSE")

    monkeypatch.setattr(
        producer_reader_services,
        "import_module",
        lambda _name: SimpleNamespace(
            **{reader.audit.public_reader_symbol: failing_reader}
        ),
    )

    with pytest.raises(ProducerReaderError) as caught:
        reader.read(b"{}\n")
    assert caught.value.code == "reader.validation_failed"
    assert caught.value.stage == "producer_reader"
    assert "PRIVATE_STUDENT_RESPONSE" not in str(caught.value)

    with pytest.raises(ProducerReaderError) as mutable:
        reader.read(cast(bytes, bytearray(b"{}\n")))
    assert mutable.value.code == "reader.validation_failed"
    assert mutable.value.stage == "reader_input"


class _RecordingReader:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.seen: list[bytes] = []

    @property
    def descriptor(self) -> producer_reader_services.ProducerReaderDescriptor:
        return producer_reader_services.ProducerReaderDescriptor(
            public_reader_id="test_recording_reader",
            reader_contract_version="test_reader_v1",
            package_identity="test-reader",
            integration_kind="live",
        )

    def read(self, value: bytes) -> object:
        self.events.append("reader")
        self.seen.append(value)
        return {"validated": True}


class _RecordingAuthorizationGate:
    def __init__(self, events: list[str], outcome: str = "allowed") -> None:
        self.events = events
        self.outcome = outcome

    def authorize(
        self,
        request: SourceReadAuthorizationRequest,
    ) -> SourceReadAuthorizationDecision:
        self.events.append("authorization")
        return SourceReadAuthorizationDecision(
            outcome=self.outcome,
            reason_codes=("test_permission",),
        )


def _fixture_authorization_request(
    setup: object,
    publication_id: str,
) -> SourceReadAuthorizationRequest:
    return SourceReadAuthorizationRequest(
        portfolio_id=getattr(setup, "portfolio_id"),
        portfolio_subject_id=getattr(setup, "portfolio_subject_id"),
        publication_id=publication_id,
        operation="candidate_source_read",
        purpose="improvement",
    )


def test_authorized_manifest_read_preserves_trust_order_and_exact_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    publication = get_canonical_publication_record(
        setup.workspace,
        setup.scoreform_publication_id,
    )
    expected = setup.manifest_paths["vitrine_scoreform_fixture"].read_bytes()
    events: list[str] = []
    reader = _RecordingReader(events)
    gate = _RecordingAuthorizationGate(events)
    original_verify = producer_reader_services.verify_publication_manifest

    def recording_verify(
        workspace_root: str | Path,
        record: object,
    ) -> Path:
        events.append("manifest_verify")
        return original_verify(workspace_root, record)  # type: ignore[arg-type]

    monkeypatch.setattr(
        producer_reader_services,
        "verify_publication_manifest",
        recording_verify,
    )

    result = read_authorized_producer_manifest(
        setup.workspace,
        publication=publication,
        authorization_gate=gate,
        authorization_request=_fixture_authorization_request(
            setup,
            publication.publication_id,
        ),
        reader=reader,
    )

    assert events == ["authorization", "manifest_verify", "reader"]
    assert result.manifest_bytes == expected
    assert reader.seen == [expected]
    assert result.public_model == {"validated": True}
    assert result.authorization.outcome == "allowed"


@pytest.mark.parametrize("outcome", ("denied", "unresolved"))
def test_non_allowed_authorization_prevents_manifest_inspection_and_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    publication = get_canonical_publication_record(
        setup.workspace,
        setup.scoreform_publication_id,
    )
    setup.manifest_paths["vitrine_scoreform_fixture"].unlink()
    events: list[str] = []
    reader = _RecordingReader(events)
    gate = _RecordingAuthorizationGate(events, outcome=outcome)

    def forbidden_verify(*_args: object, **_kwargs: object) -> Path:
        raise AssertionError("manifest must not be inspected")

    monkeypatch.setattr(
        producer_reader_services,
        "verify_publication_manifest",
        forbidden_verify,
    )

    with pytest.raises(ProducerReaderServiceError) as caught:
        read_authorized_producer_manifest(
            setup.workspace,
            publication=publication,
            authorization_gate=gate,
            authorization_request=_fixture_authorization_request(
                setup,
                publication.publication_id,
            ),
            reader=reader,
        )

    expected_code = (
        "source_read.authorization_denied"
        if outcome == "denied"
        else "source_read.authorization_unresolved"
    )
    assert caught.value.code == expected_code
    assert events == ["authorization"]
    assert reader.seen == []


def test_post_verification_manifest_change_fails_before_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    publication = get_canonical_publication_record(
        setup.workspace,
        setup.scoreform_publication_id,
    )
    events: list[str] = []
    reader = _RecordingReader(events)
    original_verify = producer_reader_services.verify_publication_manifest

    def changing_verify(
        workspace_root: str | Path,
        record: object,
    ) -> Path:
        verified = original_verify(
            workspace_root,
            record,  # type: ignore[arg-type]
        )
        verified.write_bytes(b"{}\n")
        return verified

    monkeypatch.setattr(
        producer_reader_services,
        "verify_publication_manifest",
        changing_verify,
    )

    with pytest.raises(ProducerReaderServiceError) as caught:
        read_authorized_producer_manifest(
            setup.workspace,
            publication=publication,
            authorization_gate=_RecordingAuthorizationGate(events),
            authorization_request=_fixture_authorization_request(
                setup,
                publication.publication_id,
            ),
            reader=reader,
        )
    assert caught.value.code == "source_read.manifest_integrity_failed"
    assert reader.seen == []


def test_shared_verified_manifest_bytes_reports_missing_source(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    publication = get_canonical_publication_record(
        setup.workspace,
        setup.scoreform_publication_id,
    )
    setup.manifest_paths["vitrine_scoreform_fixture"].unlink()

    with pytest.raises(ProducerReaderServiceError) as caught:
        read_verified_publication_manifest_bytes(
            setup.workspace,
            publication,
        )
    assert caught.value.code == "source_read.manifest_missing"
    assert caught.value.stage == "manifest_integrity"
