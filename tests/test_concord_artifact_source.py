from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import vitrine.concord_artifact_source as concord_source
from vitrine.concord_adapter import (
    CONCORD_ARTIFACT_REPRESENTATION_KIND,
    CONCORD_LIVE_PROJECTION_CONTRACT_VERSION,
)
from vitrine.concord_artifact_source import (
    CONCORD_ARTIFACT_AUTHORIZATION_OPERATION,
    CONCORD_ARTIFACT_SNAPSHOT_PURPOSE,
    CONCORD_ARTIFACT_SOURCE_PROVIDER_DESCRIPTOR,
    ConcordArtifactAuthorizationDecision,
    ConcordArtifactSourceContext,
    build_concord_artifact_source_provider,
)
from vitrine.models import DigestReference, SnapshotEntryPlan, SourceArtifactReference
from vitrine.snapshot_materialization import (
    SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT,
    SnapshotAuthorizedSourceBytesResult,
    SnapshotMaterializationError,
    SnapshotSourceProviderRegistry,
    SnapshotSourceRequest,
)

PDF = b"%PDF-1.4\nsynthetic concord artifact\n%%EOF\n"
PDF_SHA256 = hashlib.sha256(PDF).hexdigest()


@dataclass(frozen=True)
class _Work:
    module_id: str = "concord"
    class_id: str = "class_alpha"
    work_id: str = "activity_alpha"


@dataclass(frozen=True)
class _RecordSet:
    record_set_id: str = "academic_results"
    revision: int = 4


@dataclass(frozen=True)
class _Projection:
    source_snapshot_revision: int = 7


@dataclass(frozen=True)
class _Manifest:
    work: _Work = _Work()
    record_set: _RecordSet = _RecordSet()
    projection: _Projection = _Projection()


@dataclass(frozen=True)
class _Evidence:
    evidence_kind: str = "artifact_instance"
    owning_system: str = "concord"
    record_id: str = "artifact_alpha"


@dataclass(frozen=True)
class _ProducerRequest:
    work: object
    record_set_id: str
    record_set_revision: int
    source_snapshot_revision: int
    score_record_id: str
    score_evidence_link_id: str
    evidence_reference: _Evidence
    purpose: str


@dataclass(frozen=True)
class _Page:
    artifact_page_id: str


@dataclass(frozen=True)
class _Artifact:
    artifact_instance_id: str
    pages: tuple[_Page, ...]


@dataclass(frozen=True)
class _AuthorizedResult:
    representation: str
    work: object
    record_set_revision: int
    source_snapshot_revision: int
    score_record_id: str
    score_evidence_link_id: str
    evidence_reference: _Evidence
    artifact: _Artifact
    media_type: str
    sha256: str
    byte_size: int
    content: bytes


@dataclass(frozen=True)
class _ProducerDecision:
    status: str


class _AuthorizationError(Exception):
    pass


class _ValidationError(Exception):
    pass


class _NotFoundError(Exception):
    pass


class _UnavailableError(Exception):
    pass


class _AmbiguityError(Exception):
    pass


class _IntegrityError(Exception):
    pass


class _FakeConcordApi:
    def __init__(
        self,
        *,
        evidence_kind: str = "artifact_instance",
        evidence_record_id: str = "artifact_alpha",
        result_overrides: dict[str, object] | None = None,
    ) -> None:
        self.evidence_kind = evidence_kind
        self.evidence_record_id = evidence_record_id
        self.result_overrides = result_overrides or {}
        self.calls = 0
        self.native_io_calls = 0
        self.last_workspace_root: Path | None = None
        self.last_purpose: str | None = None

    def read(
        self,
        workspace_root: Path,
        manifest: _Manifest,
        score_evidence_link_id: str,
        *,
        purpose: str,
        authorization_gate: object,
    ) -> _AuthorizedResult:
        self.calls += 1
        self.last_workspace_root = workspace_root
        self.last_purpose = purpose
        evidence = _Evidence(
            evidence_kind=self.evidence_kind,
            owning_system="concord",
            record_id=self.evidence_record_id,
        )
        producer_request = _ProducerRequest(
            work=manifest.work,
            record_set_id=manifest.record_set.record_set_id,
            record_set_revision=manifest.record_set.revision,
            source_snapshot_revision=manifest.projection.source_snapshot_revision,
            score_record_id="score_alpha",
            score_evidence_link_id=score_evidence_link_id,
            evidence_reference=evidence,
            purpose=purpose,
        )
        authorize = getattr(authorization_gate, "authorize")
        decision = authorize(producer_request)
        if not isinstance(decision, _ProducerDecision) or decision.status != "allowed":
            raise _AuthorizationError("authorization not affirmed")

        # This counter represents the first producer-native I/O. It is
        # deliberately after the authorization callback.
        self.native_io_calls += 1

        artifact = (
            _Artifact(
                artifact_instance_id=self.evidence_record_id,
                pages=(_Page("artifact_page_alpha"),),
            )
            if self.evidence_kind == "artifact_instance"
            else _Artifact(
                artifact_instance_id="artifact_parent",
                pages=(_Page(self.evidence_record_id),),
            )
        )
        values: dict[str, object] = {
            "representation": "returned_artifact_pdf",
            "work": manifest.work,
            "record_set_revision": manifest.record_set.revision,
            "source_snapshot_revision": manifest.projection.source_snapshot_revision,
            "score_record_id": "score_alpha",
            "score_evidence_link_id": score_evidence_link_id,
            "evidence_reference": evidence,
            "artifact": artifact,
            "media_type": "application/pdf",
            "sha256": PDF_SHA256,
            "byte_size": len(PDF),
            "content": PDF,
        }
        values.update(self.result_overrides)
        return _AuthorizedResult(**values)  # type: ignore[arg-type]


def _fake_module(api: _FakeConcordApi) -> SimpleNamespace:
    return SimpleNamespace(
        AcademicResultArtifactAuthorizationDecision=_ProducerDecision,
        AuthorizedAcademicResultArtifact=_AuthorizedResult,
        read_authorized_academic_result_artifact=api.read,
        ConcordAcademicResultArtifactAuthorizationError=_AuthorizationError,
        ConcordAcademicResultArtifactValidationError=_ValidationError,
        ConcordAcademicResultArtifactNotFoundError=_NotFoundError,
        ConcordAcademicResultArtifactUnavailableError=_UnavailableError,
        ConcordAcademicResultArtifactAmbiguityError=_AmbiguityError,
        ConcordAcademicResultArtifactIntegrityError=_IntegrityError,
    )


class _ContextResolver:
    def __init__(
        self,
        *,
        workspace_root: Path,
        source_publication_id: str = "publication_alpha",
        score_evidence_link_id: str = "link_alpha",
    ) -> None:
        self.context = ConcordArtifactSourceContext(
            workspace_root=workspace_root,
            manifest=_Manifest(),
            source_publication_id=source_publication_id,
            score_evidence_link_id=score_evidence_link_id,
        )
        self.calls = 0

    def resolve(self, request: SnapshotSourceRequest) -> ConcordArtifactSourceContext:
        self.calls += 1
        return self.context


class _ArtifactGate:
    def __init__(
        self,
        outcome: str,
        *,
        raise_error: bool = False,
    ) -> None:
        self.outcome = outcome
        self.raise_error = raise_error
        self.calls = 0
        self.last_request: object | None = None

    def authorize(self, request: object) -> ConcordArtifactAuthorizationDecision:
        self.calls += 1
        self.last_request = request
        if self.raise_error:
            raise RuntimeError("synthetic policy failure")
        return ConcordArtifactAuthorizationDecision(
            outcome=self.outcome,
            authority_reference=(
                "artifact_authority_alpha" if self.outcome == "allowed" else None
            ),
            reason_codes=(),
        )


def _entry(
    *,
    evidence_record_id: str = "artifact_alpha",
    source_snapshot_revision: int = 7,
    source_publication_id: str = "publication_alpha",
    evidence_kind: str = "artifact_instance",
) -> SnapshotEntryPlan:
    return SnapshotEntryPlan(
        entry_plan_id="entry_plan_concord_artifact",
        plan_position=1,
        section_id="evidence",
        ordinal=1,
        semantic_role="student_work",
        materialization_kind="copied_source",
        content_class="student_work",
        selection_id="selection_alpha",
        placement_id="placement_alpha",
        candidate_id="candidate_alpha",
        candidate_evaluation_id="candidate_evaluation_alpha",
        source_publication_id=source_publication_id,
        producer_module_id="concord",
        projection_kind=CONCORD_ARTIFACT_REPRESENTATION_KIND,
        projection_contract_version=CONCORD_LIVE_PROJECTION_CONTRACT_VERSION,
        source_artifact=SourceArtifactReference(
            artifact_id=evidence_record_id,
            artifact_kind="collaborative_artifact",
            representation_kind=CONCORD_ARTIFACT_REPRESENTATION_KIND,
            media_type="application/pdf",
            source_locator=None,
            native_revision=source_snapshot_revision,
            source_digest=None,
            byte_size=None,
            language=None,
            accessibility_relationship=(
                "artifact_page"
                if evidence_kind == "artifact_page"
                else "artifact_instance"
            ),
        ),
        producer_source_digest_claim=None,
        target_relative_path="evidence/01-concord-artifact.pdf",
        media_type="application/pdf",
    )


def _request(**entry_kwargs: object) -> SnapshotSourceRequest:
    return SnapshotSourceRequest(
        snapshot_build_plan_id="snapshot_plan_alpha",
        snapshot_build_attempt_id="snapshot_attempt_alpha",
        entry_plan=_entry(**entry_kwargs),  # type: ignore[arg-type]
    )


def _provider(
    tmp_path: Path,
    gate: _ArtifactGate,
    *,
    source_publication_id: str = "publication_alpha",
    score_evidence_link_id: str = "link_alpha",
) -> tuple[object, _ContextResolver]:
    resolver = _ContextResolver(
        workspace_root=(tmp_path / "concord-workspace").absolute(),
        source_publication_id=source_publication_id,
        score_evidence_link_id=score_evidence_link_id,
    )
    return (
        build_concord_artifact_source_provider(
            context_resolver=resolver,
            authorization_gate=gate,
        ),
        resolver,
    )


def test_provider_descriptor_is_exact_and_construction_is_concord_lazy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imports = 0

    def fail_import(name: str) -> object:
        nonlocal imports
        imports += 1
        raise AssertionError(f"unexpected producer import: {name}")

    monkeypatch.setattr(concord_source, "import_module", fail_import)
    provider, resolver = _provider(tmp_path, _ArtifactGate("allowed"))

    assert provider.descriptor is CONCORD_ARTIFACT_SOURCE_PROVIDER_DESCRIPTOR
    assert provider.descriptor.support_key == (
        "concord",
        CONCORD_ARTIFACT_REPRESENTATION_KIND,
        CONCORD_LIVE_PROJECTION_CONTRACT_VERSION,
        "collaborative_artifact",
        CONCORD_ARTIFACT_REPRESENTATION_KIND,
    )
    assert resolver.calls == 0
    assert imports == 0


def test_exact_snapshot_provider_registry_selects_concord_artifact(
    tmp_path: Path,
) -> None:
    provider, _ = _provider(tmp_path, _ArtifactGate("allowed"))
    selected = SnapshotSourceProviderRegistry((provider,)).select(_entry())
    assert selected is provider


def test_allowed_artifact_authorization_returns_exact_authorized_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _FakeConcordApi()
    monkeypatch.setattr(
        concord_source,
        "import_module",
        lambda name: _fake_module(api),
    )
    gate = _ArtifactGate("allowed")
    provider, resolver = _provider(tmp_path, gate)

    result = provider.resolve(_request())

    assert isinstance(result, SnapshotAuthorizedSourceBytesResult)
    assert result.provider_id == provider.descriptor.provider_id
    assert result.provider_version == provider.descriptor.provider_version
    assert result.source_publication_id == "publication_alpha"
    assert result.source_artifact_id == "artifact_alpha"
    assert result.content == PDF
    assert result.media_type == "application/pdf"
    assert result.source_digest == DigestReference(value=PDF_SHA256)
    assert result.byte_size == len(PDF)
    assert (
        result.acquisition_contract_version
        == SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT
    )
    assert resolver.calls == 1
    assert gate.calls == 1
    assert api.calls == 1
    assert api.native_io_calls == 1
    assert api.last_purpose == CONCORD_ARTIFACT_SNAPSHOT_PURPOSE

    request = gate.last_request
    assert request is not None
    assert getattr(request, "operation") == CONCORD_ARTIFACT_AUTHORIZATION_OPERATION
    assert getattr(request, "source_publication_id") == "publication_alpha"
    assert getattr(request, "source_artifact_id") == "artifact_alpha"
    assert getattr(request, "source_snapshot_revision") == 7
    assert getattr(request, "score_record_id") == "score_alpha"
    assert getattr(request, "score_evidence_link_id") == "link_alpha"
    assert getattr(request, "evidence_kind") == "artifact_instance"
    assert getattr(request, "evidence_record_id") == "artifact_alpha"


@pytest.mark.parametrize(
    ("outcome", "raise_error", "expected_stage"),
    (
        ("denied", False, "concord_artifact_authorization_denied"),
        ("unresolved", False, "concord_artifact_authorization_unresolved"),
        ("unresolved", True, "concord_artifact_authorization_unresolved"),
    ),
)
def test_non_allowed_artifact_authorization_fails_before_native_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
    raise_error: bool,
    expected_stage: str,
) -> None:
    api = _FakeConcordApi()
    monkeypatch.setattr(
        concord_source,
        "import_module",
        lambda name: _fake_module(api),
    )
    gate = _ArtifactGate(outcome, raise_error=raise_error)
    provider, resolver = _provider(tmp_path, gate)

    with pytest.raises(SnapshotMaterializationError) as captured:
        provider.resolve(_request())

    assert captured.value.code == "snapshot.source_unavailable"
    assert captured.value.stage == expected_stage
    assert resolver.calls == 1
    assert gate.calls == 1
    assert api.calls == 1
    assert api.native_io_calls == 0


def test_manifest_or_snapshot_context_is_not_artifact_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _FakeConcordApi()
    monkeypatch.setattr(
        concord_source,
        "import_module",
        lambda name: _fake_module(api),
    )
    provider, resolver = _provider(tmp_path, _ArtifactGate("denied"))

    with pytest.raises(SnapshotMaterializationError) as captured:
        provider.resolve(_request())

    assert resolver.calls == 1
    assert captured.value.stage == "concord_artifact_authorization_denied"
    assert api.native_io_calls == 0


def test_producer_authorization_request_must_match_planned_artifact_before_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _FakeConcordApi(evidence_record_id="different_artifact")
    monkeypatch.setattr(
        concord_source,
        "import_module",
        lambda name: _fake_module(api),
    )
    gate = _ArtifactGate("allowed")
    provider, _ = _provider(tmp_path, gate)

    with pytest.raises(SnapshotMaterializationError) as captured:
        provider.resolve(_request())

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "concord_artifact_authorization"
    assert gate.calls == 0
    assert api.native_io_calls == 0


def test_context_publication_mismatch_fails_before_concord_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imports = 0

    def fail_import(name: str) -> object:
        nonlocal imports
        imports += 1
        raise AssertionError("Concord should not be imported for mismatched context")

    monkeypatch.setattr(concord_source, "import_module", fail_import)
    provider, _ = _provider(
        tmp_path,
        _ArtifactGate("allowed"),
        source_publication_id="other_publication",
    )

    with pytest.raises(SnapshotMaterializationError) as captured:
        provider.resolve(_request())

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "concord_artifact_context"
    assert imports == 0


def test_projected_snapshot_revision_must_match_context_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imports = 0

    def fail_import(name: str) -> object:
        nonlocal imports
        imports += 1
        raise AssertionError("Concord should not be imported for drifted history")

    monkeypatch.setattr(concord_source, "import_module", fail_import)
    provider, _ = _provider(tmp_path, _ArtifactGate("allowed"))

    with pytest.raises(SnapshotMaterializationError) as captured:
        provider.resolve(_request(source_snapshot_revision=8))

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "concord_artifact_context"
    assert imports == 0


def test_artifact_page_result_remains_page_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _FakeConcordApi(
        evidence_kind="artifact_page",
        evidence_record_id="artifact_page_alpha",
    )
    monkeypatch.setattr(
        concord_source,
        "import_module",
        lambda name: _fake_module(api),
    )
    provider, _ = _provider(tmp_path, _ArtifactGate("allowed"))

    result = provider.resolve(
        _request(
            evidence_record_id="artifact_page_alpha",
            evidence_kind="artifact_page",
        )
    )

    assert result.source_artifact_id == "artifact_page_alpha"
    assert result.content == PDF
    assert api.native_io_calls == 1


@pytest.mark.parametrize(
    "overrides",
    (
        {"representation": "other_representation"},
        {"source_snapshot_revision": 8},
        {"score_record_id": "other_score"},
        {"score_evidence_link_id": "other_link"},
        {"media_type": "text/plain"},
        {"sha256": "f" * 64},
        {"byte_size": len(PDF) + 1},
        {"content": b"not a PDF"},
        {
            "artifact": _Artifact(
                artifact_instance_id="other_artifact",
                pages=(_Page("artifact_page_alpha"),),
            )
        },
    ),
)
def test_provider_independently_rejects_inconsistent_producer_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict[str, object],
) -> None:
    api = _FakeConcordApi(result_overrides=overrides)
    monkeypatch.setattr(
        concord_source,
        "import_module",
        lambda name: _fake_module(api),
    )
    provider, _ = _provider(tmp_path, _ArtifactGate("allowed"))

    with pytest.raises(SnapshotMaterializationError) as captured:
        provider.resolve(_request())

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "concord_artifact_result"
    assert api.native_io_calls == 1


def test_provider_maps_producer_integrity_failure_privacy_safely(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _FakeConcordApi()
    module = _fake_module(api)

    def fail_read(*args: Any, **kwargs: Any) -> object:
        raise _IntegrityError("PRIVATE retained path C:/secret/student.pdf")

    module.read_authorized_academic_result_artifact = fail_read
    monkeypatch.setattr(concord_source, "import_module", lambda name: module)
    provider, _ = _provider(tmp_path, _ArtifactGate("allowed"))

    with pytest.raises(SnapshotMaterializationError) as captured:
        provider.resolve(_request())

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "concord_artifact_read"
    assert "PRIVATE" not in str(captured.value)
    assert "secret" not in str(captured.value)


def test_missing_concord_artifact_package_fails_without_fixture_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing(name: str) -> object:
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(concord_source, "import_module", missing)
    provider, _ = _provider(tmp_path, _ArtifactGate("allowed"))

    with pytest.raises(SnapshotMaterializationError) as captured:
        provider.resolve(_request())

    assert captured.value.code == "snapshot.source_unavailable"
    assert captured.value.stage == "concord_artifact_contract"


def test_authorized_provider_does_not_offer_filesystem_stability(
    tmp_path: Path,
) -> None:
    provider, _ = _provider(tmp_path, _ArtifactGate("allowed"))

    with pytest.raises(SnapshotMaterializationError) as captured:
        provider.confirm_stability(_request(), object())  # type: ignore[arg-type]

    assert captured.value.code == "snapshot.invalid_request"
    assert captured.value.stage == "concord_artifact_stability"


def test_authorization_decision_requires_reference_only_when_allowed() -> None:
    denied = ConcordArtifactAuthorizationDecision(outcome="denied")
    unresolved = ConcordArtifactAuthorizationDecision(outcome="unresolved")
    assert denied.authority_reference is None
    assert unresolved.authority_reference is None

    with pytest.raises(SnapshotMaterializationError) as captured:
        ConcordArtifactAuthorizationDecision(outcome="allowed")
    assert captured.value.code == "snapshot.invalid_request"
    assert captured.value.stage == "concord_artifact_authorization"
