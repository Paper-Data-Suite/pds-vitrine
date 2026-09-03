from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import vitrine.quillan_artifact_source as quillan_source
from vitrine.models import DigestReference, SnapshotEntryPlan, SourceArtifactReference
from vitrine.quillan_artifact_source import (
    QUILLAN_ARTIFACT_AUTHORIZATION_OPERATION,
    QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_DESCRIPTOR,
    QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_DESCRIPTOR,
    QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_DESCRIPTOR,
    QuillanArtifactAuthorizationDecision,
    QuillanArtifactSourceContext,
    build_quillan_artifact_source_provider,
    build_quillan_artifact_source_providers,
)
from vitrine.quillan_contract import (
    QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE,
    QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
    QUILLAN_FEEDBACK_PDF_MEDIA_TYPE,
    QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
    QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION,
    QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
    QUILLAN_STUDENT_WORK_CONCRETE_MEDIA_TYPES,
    QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE,
    quillan_evidence_source_id,
    quillan_feedback_source_id,
)
from vitrine.snapshot_materialization import (
    SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT,
    SNAPSHOT_AUTHORIZED_SOURCE_BYTES_DEFERRED_MEDIA_CONTRACT,
    SnapshotAuthorizedSourceBytesResult,
    SnapshotMaterializationError,
    SnapshotSourceProviderRegistry,
    SnapshotSourceRequest,
)

PNG = b"\x89PNG\r\n\x1a\nsynthetic quillan selected evidence"
PNG_SHA256 = hashlib.sha256(PNG).hexdigest()
JPEG = b"\xff\xd8\xffsynthetic quillan second evidence"
JPEG_SHA256 = hashlib.sha256(JPEG).hexdigest()
PDF = b"%PDF-1.4\nsynthetic quillan feedback\n%%EOF\n"
PDF_SHA256 = hashlib.sha256(PDF).hexdigest()
MARKDOWN = b"# Feedback\n\nPublic Quillan feedback.\n"
MARKDOWN_SHA256 = hashlib.sha256(MARKDOWN).hexdigest()


@dataclass(frozen=True)
class _Work:
    module_id: str = "quillan"
    class_id: str = "class_alpha"
    work_id: str = "assignment_alpha"


@dataclass(frozen=True)
class _RecordSet:
    record_set_id: str = "academic_results"
    revision: int = 5


@dataclass(frozen=True)
class _Evidence:
    evidence_id: str
    routed_evidence_sha256: str


@dataclass(frozen=True)
class _DigitalProvenance:
    evidence_references: tuple[_Evidence, ...]


@dataclass(frozen=True)
class _Submission:
    entry_method: str
    digital_provenance: _DigitalProvenance | None


@dataclass(frozen=True)
class _Student:
    student_id: str
    submission: _Submission


@dataclass(frozen=True)
class _Manifest:
    work: _Work
    record_set: _RecordSet
    students: tuple[_Student, ...]


def _manifest(*, plain_paper: bool = False) -> _Manifest:
    submission = (
        _Submission("plain_paper_manual", None)
        if plain_paper
        else _Submission(
            "pds2_response_pages",
            _DigitalProvenance(
                (
                    _Evidence("evidence_alpha", PNG_SHA256),
                    _Evidence("evidence_beta", JPEG_SHA256),
                )
            ),
        )
    )
    return _Manifest(_Work(), _RecordSet(), (_Student("student_alpha", submission),))


@dataclass(frozen=True)
class _ProducerRequest:
    work: object
    record_set_id: str
    record_set_revision: int
    student_id: str
    artifact_kind: str
    purpose: str


@dataclass(frozen=True)
class _ProducerDecision:
    status: str


@dataclass(frozen=True)
class _AuthorizedResult:
    artifact_kind: str
    work: object
    record_set_revision: int
    student_id: str
    relative_path: str
    media_type: str
    sha256: str
    byte_size: int
    data: bytes
    evidence_reference: _Evidence | None = None
    generated_at: str | None = None
    source_review_updated_at: str | None = None


class _AuthorizationError(Exception):
    pass


class _ValidationError(Exception):
    pass


class _UnavailableError(Exception):
    pass


class _IntegrityError(Exception):
    pass


class _ReadError(Exception):
    pass


class _FakeApi:
    def __init__(
        self,
        *,
        result_override: dict[str, object] | None = None,
        producer_request_override: dict[str, object] | None = None,
        raise_after_authorization: BaseException | None = None,
    ) -> None:
        self.result_override = result_override or {}
        self.producer_request_override = producer_request_override or {}
        self.raise_after_authorization = raise_after_authorization
        self.calls = 0
        self.native_io_calls = 0
        self.last_kind: str | None = None

    def read(
        self,
        workspace_root: Path,
        manifest: _Manifest,
        student_id: str,
        artifact_kind: str,
        *,
        purpose: str,
        authorization_gate: object,
    ) -> tuple[_AuthorizedResult, ...]:
        del workspace_root
        self.calls += 1
        self.last_kind = artifact_kind
        request_values: dict[str, object] = {
            "work": manifest.work,
            "record_set_id": manifest.record_set.record_set_id,
            "record_set_revision": manifest.record_set.revision,
            "student_id": student_id,
            "artifact_kind": artifact_kind,
            "purpose": purpose,
        }
        request_values.update(self.producer_request_override)
        producer_request = _ProducerRequest(**request_values)  # type: ignore[arg-type]
        authorize = getattr(authorization_gate, "authorize")
        decision = authorize(producer_request)
        if not isinstance(decision, _ProducerDecision) or decision.status != "allowed":
            raise _AuthorizationError("authorization not affirmed")

        # Represents the first producer-native read. It must occur after authorize().
        self.native_io_calls += 1
        if self.raise_after_authorization is not None:
            raise self.raise_after_authorization
        if artifact_kind == "student_work":
            results = (
                _AuthorizedResult(
                    artifact_kind="student_work",
                    work=manifest.work,
                    record_set_revision=manifest.record_set.revision,
                    student_id=student_id,
                    relative_path="opaque/selected-alpha.png",
                    media_type="image/png",
                    sha256=PNG_SHA256,
                    byte_size=len(PNG),
                    data=PNG,
                    evidence_reference=manifest.students[0]
                    .submission.digital_provenance.evidence_references[0],  # type: ignore[union-attr]
                ),
                _AuthorizedResult(
                    artifact_kind="student_work",
                    work=manifest.work,
                    record_set_revision=manifest.record_set.revision,
                    student_id=student_id,
                    relative_path="opaque/selected-beta.jpg",
                    media_type="image/jpeg",
                    sha256=JPEG_SHA256,
                    byte_size=len(JPEG),
                    data=JPEG,
                    evidence_reference=manifest.students[0]
                    .submission.digital_provenance.evidence_references[1],  # type: ignore[union-attr]
                ),
            )
        elif artifact_kind == "feedback_pdf":
            results = (
                _AuthorizedResult(
                    artifact_kind="feedback_pdf",
                    work=manifest.work,
                    record_set_revision=manifest.record_set.revision,
                    student_id=student_id,
                    relative_path="opaque/feedback.pdf",
                    media_type=QUILLAN_FEEDBACK_PDF_MEDIA_TYPE,
                    sha256=PDF_SHA256,
                    byte_size=len(PDF),
                    data=PDF,
                ),
            )
        else:
            results = (
                _AuthorizedResult(
                    artifact_kind="feedback_markdown",
                    work=manifest.work,
                    record_set_revision=manifest.record_set.revision,
                    student_id=student_id,
                    relative_path="opaque/feedback.md",
                    media_type=QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE,
                    sha256=MARKDOWN_SHA256,
                    byte_size=len(MARKDOWN),
                    data=MARKDOWN,
                ),
            )
        if not self.result_override:
            return results
        first = results[0]
        values = {
            field: getattr(first, field)
            for field in _AuthorizedResult.__dataclass_fields__
        }
        values.update(self.result_override)
        return (_AuthorizedResult(**values),)  # type: ignore[arg-type]


def _fake_module(api: _FakeApi) -> SimpleNamespace:
    return SimpleNamespace(
        AcademicResultArtifactAuthorizationDecision=_ProducerDecision,
        AuthorizedAcademicResultArtifact=_AuthorizedResult,
        read_authorized_academic_result_artifacts=api.read,
        QuillanAcademicResultArtifactAuthorizationError=_AuthorizationError,
        QuillanAcademicResultArtifactValidationError=_ValidationError,
        QuillanAcademicResultArtifactUnavailableError=_UnavailableError,
        QuillanAcademicResultArtifactIntegrityError=_IntegrityError,
        QuillanAcademicResultArtifactReadError=_ReadError,
    )


class _Resolver:
    def __init__(
        self,
        *,
        tmp_path: Path,
        kind: str,
        evidence_id: str | None = None,
        manifest: _Manifest | None = None,
        source_publication_id: str = "publication_alpha",
    ) -> None:
        self.context = QuillanArtifactSourceContext(
            workspace_root=(tmp_path / "quillan-workspace").absolute(),
            manifest=_manifest() if manifest is None else manifest,
            source_publication_id=source_publication_id,
            student_id="student_alpha",
            artifact_request_kind=kind,
            evidence_id=evidence_id,
        )
        self.calls = 0

    def resolve(self, request: SnapshotSourceRequest) -> QuillanArtifactSourceContext:
        del request
        self.calls += 1
        return self.context


class _Gate:
    def __init__(self, outcome: str, *, raise_error: bool = False) -> None:
        self.outcome = outcome
        self.raise_error = raise_error
        self.calls = 0
        self.last_request: object | None = None

    def authorize(self, request: object) -> QuillanArtifactAuthorizationDecision:
        self.calls += 1
        self.last_request = request
        if self.raise_error:
            raise RuntimeError("synthetic policy failure")
        return QuillanArtifactAuthorizationDecision(
            outcome=self.outcome,
            authority_reference=(
                "quillan_artifact_authority_alpha"
                if self.outcome == "allowed"
                else None
            ),
        )


def _entry(kind: str, *, evidence_id: str = "evidence_alpha") -> SnapshotEntryPlan:
    if kind == "student_work":
        projection_kind = QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND
        artifact_kind = "original_student_work"
        media_type = QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE
        artifact_id = quillan_evidence_source_id(
            class_id="class_alpha",
            work_id="assignment_alpha",
            student_id="student_alpha",
            evidence_id=evidence_id,
        )
        target = "evidence/quillan-selected-work"
    elif kind == "feedback_pdf":
        projection_kind = QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND
        artifact_kind = "rendered_feedback"
        media_type = QUILLAN_FEEDBACK_PDF_MEDIA_TYPE
        artifact_id = quillan_feedback_source_id(
            class_id="class_alpha",
            work_id="assignment_alpha",
            student_id="student_alpha",
            artifact_request_kind=kind,
        )
        target = "feedback/quillan-feedback.pdf"
    else:
        projection_kind = QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND
        artifact_kind = "rendered_feedback"
        media_type = QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE
        artifact_id = quillan_feedback_source_id(
            class_id="class_alpha",
            work_id="assignment_alpha",
            student_id="student_alpha",
            artifact_request_kind=kind,
        )
        target = "feedback/quillan-feedback.md"
    return SnapshotEntryPlan(
        entry_plan_id=f"entry_plan_{kind}",
        plan_position=1,
        section_id="evidence",
        ordinal=1,
        semantic_role="student_work" if kind == "student_work" else "feedback",
        materialization_kind="copied_source",
        content_class="student_work" if kind == "student_work" else "feedback",
        selection_id="selection_alpha",
        placement_id="placement_alpha",
        candidate_id="candidate_alpha",
        candidate_evaluation_id="candidate_evaluation_alpha",
        source_publication_id="publication_alpha",
        producer_module_id="quillan",
        projection_kind=projection_kind,
        projection_contract_version=QUILLAN_LIVE_PROJECTION_CONTRACT_VERSION,
        source_artifact=SourceArtifactReference(
            artifact_id=artifact_id,
            artifact_kind=artifact_kind,
            representation_kind=projection_kind,
            media_type=media_type,
            source_locator=None,
            native_revision=5,
            source_digest=None,
            byte_size=None,
            language=None,
            accessibility_relationship=None,
        ),
        producer_source_digest_claim=None,
        target_relative_path=target,
        media_type=media_type,
    )


def _request(kind: str, *, evidence_id: str = "evidence_alpha") -> SnapshotSourceRequest:
    return SnapshotSourceRequest(
        snapshot_build_plan_id="snapshot_plan_alpha",
        snapshot_build_attempt_id="snapshot_attempt_alpha",
        entry_plan=_entry(kind, evidence_id=evidence_id),
    )


def _provider(
    tmp_path: Path,
    kind: str,
    gate: _Gate,
    *,
    evidence_id: str | None = None,
    manifest: _Manifest | None = None,
    source_publication_id: str = "publication_alpha",
) -> tuple[object, _Resolver]:
    resolver = _Resolver(
        tmp_path=tmp_path,
        kind=kind,
        evidence_id=(
            (evidence_id or "evidence_alpha") if kind == "student_work" else None
        ),
        manifest=manifest,
        source_publication_id=source_publication_id,
    )
    return (
        build_quillan_artifact_source_provider(
            artifact_request_kind=kind,
            context_resolver=resolver,
            authorization_gate=gate,
        ),
        resolver,
    )


def test_provider_family_has_three_exact_support_keys_and_construction_is_lazy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imports = 0

    def fail_import(name: str) -> object:
        nonlocal imports
        imports += 1
        raise AssertionError(f"unexpected producer import: {name}")

    monkeypatch.setattr(quillan_source, "import_module", fail_import)
    resolver = _Resolver(tmp_path=tmp_path, kind="feedback_pdf")
    providers = build_quillan_artifact_source_providers(
        context_resolver=resolver,
        authorization_gate=_Gate("allowed"),
    )

    assert tuple(provider.descriptor for provider in providers) == (
        QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_DESCRIPTOR,
        QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_DESCRIPTOR,
        QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_DESCRIPTOR,
    )
    assert QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_DESCRIPTOR.concrete_media_types == tuple(
        sorted(QUILLAN_STUDENT_WORK_CONCRETE_MEDIA_TYPES)
    )
    assert imports == 0
    assert resolver.calls == 0


@pytest.mark.parametrize("kind", ("student_work", "feedback_pdf", "feedback_markdown"))
def test_snapshot_registry_selects_each_exact_quillan_provider(
    tmp_path: Path, kind: str
) -> None:
    resolver = _Resolver(
        tmp_path=tmp_path,
        kind=kind,
        evidence_id="evidence_alpha" if kind == "student_work" else None,
    )
    providers = build_quillan_artifact_source_providers(
        context_resolver=resolver,
        authorization_gate=_Gate("allowed"),
    )
    selected = SnapshotSourceProviderRegistry(providers).select(_entry(kind))
    expected = {
        "student_work": QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_DESCRIPTOR,
        "feedback_pdf": QUILLAN_FEEDBACK_PDF_SOURCE_PROVIDER_DESCRIPTOR,
        "feedback_markdown": QUILLAN_FEEDBACK_MARKDOWN_SOURCE_PROVIDER_DESCRIPTOR,
    }[kind]
    assert selected.descriptor is expected


def test_allowed_student_work_selects_exact_evidence_from_producer_tuple(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _FakeApi()
    monkeypatch.setattr(quillan_source, "import_module", lambda name: _fake_module(api))
    gate = _Gate("allowed")
    resolver = _Resolver(
        tmp_path=tmp_path,
        kind="student_work",
        evidence_id="evidence_beta",
    )
    provider = build_quillan_artifact_source_provider(
        artifact_request_kind="student_work",
        context_resolver=resolver,
        authorization_gate=gate,
    )

    result = provider.resolve(_request("student_work", evidence_id="evidence_beta"))

    assert isinstance(result, SnapshotAuthorizedSourceBytesResult)
    assert result.content == JPEG
    assert result.media_type == "image/jpeg"
    assert result.source_digest == DigestReference(value=JPEG_SHA256)
    assert result.byte_size == len(JPEG)
    assert result.acquisition_contract_version == (
        SNAPSHOT_AUTHORIZED_SOURCE_BYTES_DEFERRED_MEDIA_CONTRACT
    )
    assert gate.calls == 1
    assert api.calls == 1
    assert api.native_io_calls == 1
    auth_request = gate.last_request
    assert auth_request is not None
    assert getattr(auth_request, "operation") == QUILLAN_ARTIFACT_AUTHORIZATION_OPERATION
    assert getattr(auth_request, "artifact_kind") == "student_work"
    assert getattr(auth_request, "evidence_id") == "evidence_beta"
    assert getattr(auth_request, "source_artifact_id") == (
        _entry("student_work", evidence_id="evidence_beta").source_artifact.artifact_id  # type: ignore[union-attr]
    )


@pytest.mark.parametrize(
    ("kind", "expected_content", "expected_media"),
    (
        ("feedback_pdf", PDF, QUILLAN_FEEDBACK_PDF_MEDIA_TYPE),
        ("feedback_markdown", MARKDOWN, QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE),
    ),
)
def test_allowed_feedback_returns_exact_requested_representation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    expected_content: bytes,
    expected_media: str,
) -> None:
    api = _FakeApi()
    monkeypatch.setattr(quillan_source, "import_module", lambda name: _fake_module(api))
    gate = _Gate("allowed")
    provider, _ = _provider(tmp_path, kind, gate)

    result = provider.resolve(_request(kind))

    assert result.content == expected_content
    assert result.media_type == expected_media
    assert result.acquisition_contract_version == SNAPSHOT_AUTHORIZED_SOURCE_BYTES_CONTRACT
    assert api.last_kind == kind
    assert getattr(gate.last_request, "evidence_id") is None


@pytest.mark.parametrize(
    ("outcome", "raise_error", "expected_stage"),
    (
        ("denied", False, "quillan_artifact_authorization_denied"),
        ("unresolved", False, "quillan_artifact_authorization_unresolved"),
        ("unresolved", True, "quillan_artifact_authorization_unresolved"),
    ),
)
def test_non_allowed_decision_fails_before_producer_native_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
    raise_error: bool,
    expected_stage: str,
) -> None:
    api = _FakeApi()
    monkeypatch.setattr(quillan_source, "import_module", lambda name: _fake_module(api))
    gate = _Gate(outcome, raise_error=raise_error)
    provider, _ = _provider(tmp_path, "feedback_pdf", gate)

    with pytest.raises(SnapshotMaterializationError) as captured:
        provider.resolve(_request("feedback_pdf"))

    assert captured.value.code == "snapshot.source_unavailable"
    assert captured.value.stage == expected_stage
    assert gate.calls == 1
    assert api.calls == 1
    assert api.native_io_calls == 0


def test_producer_request_mismatch_fails_before_deployment_gate_and_native_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _FakeApi(producer_request_override={"student_id": "student_other"})
    monkeypatch.setattr(quillan_source, "import_module", lambda name: _fake_module(api))
    gate = _Gate("allowed")
    provider, _ = _provider(tmp_path, "feedback_pdf", gate)

    with pytest.raises(SnapshotMaterializationError) as captured:
        provider.resolve(_request("feedback_pdf"))

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "quillan_artifact_authorization"
    assert gate.calls == 0
    assert api.native_io_calls == 0


def test_publication_context_mismatch_fails_before_quillan_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imports = 0

    def fail_import(name: str) -> object:
        nonlocal imports
        imports += 1
        raise AssertionError("Quillan must not import for invalid Vitrine context")

    monkeypatch.setattr(quillan_source, "import_module", fail_import)
    provider, _ = _provider(
        tmp_path,
        "feedback_pdf",
        _Gate("allowed"),
        source_publication_id="publication_other",
    )

    with pytest.raises(SnapshotMaterializationError) as captured:
        provider.resolve(_request("feedback_pdf"))

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "quillan_artifact_context"
    assert imports == 0


def test_plain_paper_plan_cannot_fabricate_student_work_capability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imports = 0

    def fail_import(name: str) -> object:
        nonlocal imports
        imports += 1
        raise AssertionError("Quillan must not import for fabricated plain-paper work")

    monkeypatch.setattr(quillan_source, "import_module", fail_import)
    resolver = _Resolver(
        tmp_path=tmp_path,
        kind="student_work",
        evidence_id="evidence_alpha",
        manifest=_manifest(plain_paper=True),
    )
    provider = build_quillan_artifact_source_provider(
        artifact_request_kind="student_work",
        context_resolver=resolver,
        authorization_gate=_Gate("allowed"),
    )

    with pytest.raises(SnapshotMaterializationError) as captured:
        provider.resolve(_request("student_work"))

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "quillan_artifact_context"
    assert imports == 0


def test_student_work_digest_must_match_public_selected_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wrong = b"different bytes"
    api = _FakeApi(
        result_override={
            "data": wrong,
            "byte_size": len(wrong),
            "sha256": hashlib.sha256(wrong).hexdigest(),
        }
    )
    monkeypatch.setattr(quillan_source, "import_module", lambda name: _fake_module(api))
    provider, _ = _provider(tmp_path, "student_work", _Gate("allowed"))

    with pytest.raises(SnapshotMaterializationError) as captured:
        provider.resolve(_request("student_work"))

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "quillan_artifact_result"



def test_producer_historical_integrity_failure_maps_to_snapshot_integrity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _FakeApi(raise_after_authorization=_IntegrityError("historical drift"))
    monkeypatch.setattr(quillan_source, "import_module", lambda name: _fake_module(api))
    provider, _ = _provider(tmp_path, "feedback_pdf", _Gate("allowed"))

    with pytest.raises(SnapshotMaterializationError) as captured:
        provider.resolve(_request("feedback_pdf"))

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "quillan_artifact_read"
    assert api.native_io_calls == 1

def test_feedback_media_mismatch_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _FakeApi(result_override={"media_type": "text/plain"})
    monkeypatch.setattr(quillan_source, "import_module", lambda name: _fake_module(api))
    provider, _ = _provider(tmp_path, "feedback_pdf", _Gate("allowed"))

    with pytest.raises(SnapshotMaterializationError) as captured:
        provider.resolve(_request("feedback_pdf"))

    assert captured.value.code == "snapshot.source_integrity_failed"
    assert captured.value.stage == "quillan_artifact_result"


def test_vitrine_never_reopens_returned_quillan_relative_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _FakeApi()
    monkeypatch.setattr(quillan_source, "import_module", lambda name: _fake_module(api))

    def fail_open(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        raise AssertionError("Vitrine reopened a producer-owned Artifact path")

    monkeypatch.setattr(Path, "open", fail_open)
    provider, _ = _provider(tmp_path, "feedback_markdown", _Gate("allowed"))
    result = provider.resolve(_request("feedback_markdown"))
    assert result.content == MARKDOWN


def test_provider_rejects_unknown_artifact_kind_without_quillan_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imports = 0

    def fail_import(name: str) -> object:
        nonlocal imports
        imports += 1
        raise AssertionError(name)

    monkeypatch.setattr(quillan_source, "import_module", fail_import)
    resolver = _Resolver(tmp_path=tmp_path, kind="feedback_pdf")
    with pytest.raises(SnapshotMaterializationError) as captured:
        build_quillan_artifact_source_provider(
            artifact_request_kind="feedback_html",
            context_resolver=resolver,
            authorization_gate=_Gate("allowed"),
        )
    assert captured.value.code == "snapshot.invalid_request"
    assert imports == 0


def test_student_work_descriptor_advertises_only_released_concrete_media() -> None:
    assert set(QUILLAN_STUDENT_WORK_SOURCE_PROVIDER_DESCRIPTOR.concrete_media_types) == {
        "image/jpeg",
        "image/png",
        "image/tiff",
    }
