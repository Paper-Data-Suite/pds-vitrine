from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from pds_core.academic_catalog import PublicationCatalogQuery

import vitrine.candidate_evidence_artifact_preview as artifact_preview
from scripts.candidate_fixture_support import (
    ACTOR,
    DeterministicIds,
    StaticAuthorizationGate,
    build_candidate_fixture_workspace,
    fixed_clock,
)
from vitrine.candidate_evidence_artifact_preview import (
    CandidateEvidenceArtifactPreview,
    acquire_candidate_evidence_artifact_preview,
)
from vitrine.candidate_evidence_preview import (
    CANDIDATE_EVIDENCE_PREVIEW_OPERATION,
    CandidateEvidencePreviewAuthorizationDecision,
    CandidateEvidencePreviewPreparedContext,
    CandidateEvidencePreviewRequest,
    prepare_candidate_evidence_preview_context,
)
from vitrine.candidate_inbox import (
    CandidateInboxQuery,
    get_candidate_inbox_detail,
    list_candidate_inbox,
)
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.concord_adapter import (
    CONCORD_ARTIFACT_MEDIA_TYPE,
    CONCORD_ARTIFACT_REPRESENTATION_KIND,
)
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.models import SourceArtifactReference
from vitrine.producer_adapters import (
    ProjectedProducerRelationship,
    ProjectionDisplaySnapshot,
    ProjectionField,
)
from vitrine.quillan_contract import (
    QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE,
    QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND,
    QUILLAN_FEEDBACK_PDF_MEDIA_TYPE,
    QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND,
    QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND,
    QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE,
    quillan_evidence_source_id,
    quillan_feedback_source_id,
)

PNG = b"\x89PNG\r\n\x1a\ncandidate preview evidence"
PNG_SHA256 = hashlib.sha256(PNG).hexdigest()
PDF = b"%PDF-1.4\ncandidate preview pdf\n%%EOF\n"
PDF_SHA256 = hashlib.sha256(PDF).hexdigest()
MARKDOWN = b"# Feedback\n\nCandidate preview feedback.\n"
MARKDOWN_SHA256 = hashlib.sha256(MARKDOWN).hexdigest()


def _discover(setup: object, module_id: str) -> None:
    result = discover_and_evaluate_candidates(
        getattr(setup, "workspace"),
        CandidateDiscoveryRequest(
            portfolio_id=getattr(setup, "portfolio_id"),
            requesting_actor=ACTOR,
            requested_purpose="improvement",
            catalog_query=PublicationCatalogQuery(
                module_id=module_id,
                state="current",
                limit=100,
            ),
            expected_state_revision=getattr(setup, "state_revision"),
        ),
        producer_registry=build_development_fixture_producer_registry(),
        adapter_registry=build_development_fixture_adapter_registry(),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    assert result.findings == ()


def _detail_artifact_kind(detail: object) -> str | None:
    evaluation = getattr(detail, "evaluation")
    candidate = getattr(detail, "candidate")
    endpoint = (
        evaluation.source_endpoint
        if evaluation is not None and evaluation.source_endpoint is not None
        else candidate.source_endpoint
        if candidate is not None
        else None
    )
    if endpoint is None or endpoint.source_artifact is None:
        return None
    return endpoint.source_artifact.artifact_kind


def _base_context(
    tmp_path: Path,
    *,
    module_id: str,
    artifact_kind: str,
) -> CandidateEvidencePreviewPreparedContext:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, module_id)
    item = next(
        item
        for item in list_candidate_inbox(
            setup.workspace,
            CandidateInboxQuery(
                portfolio_id=setup.portfolio_id,
                producer_module_id=module_id,
                limit=100,
            ),
        ).items
        if _detail_artifact_kind(
            get_candidate_inbox_detail(
                setup.workspace,
                item.entry_id,
            )
        )
        == artifact_kind
    )
    detail = get_candidate_inbox_detail(setup.workspace, item.entry_id)
    request = CandidateEvidencePreviewRequest(
        portfolio_id=item.portfolio_id,
        portfolio_subject_id=item.portfolio_subject_id,
        entry_id=item.entry_id,
        candidate_id=item.candidate_id,
        candidate_evaluation_id=item.current_evaluation_id,
        requesting_actor=ACTOR,
        requested_purpose="teacher_preview",
        observed_state_revision=detail.observed_state_revision,
    )
    return prepare_candidate_evidence_preview_context(
        setup.workspace,
        request,
        adapter_registry=build_development_fixture_adapter_registry(),
        source_read_authorization_gate=StaticAuthorizationGate("allowed"),
    )


class _PreviewGate:
    def __init__(self, outcome: str) -> None:
        self.outcome = outcome
        self.calls = 0
        self.last_request: object | None = None

    def authorize(self, request: object) -> CandidateEvidencePreviewAuthorizationDecision:
        self.calls += 1
        self.last_request = request
        return CandidateEvidencePreviewAuthorizationDecision(
            outcome=self.outcome,
            authority_reference=(
                "candidate_preview_authority"
                if self.outcome == "allowed"
                else None
            ),
        )


@dataclass(frozen=True)
class _QWork:
    module_id: str = "quillan"
    class_id: str = "class_alpha"
    work_id: str = "assignment_alpha"


@dataclass(frozen=True)
class _RecordSet:
    record_set_id: str = "academic_results"
    revision: int = 5


@dataclass(frozen=True)
class _QEvidence:
    evidence_id: str
    routed_evidence_sha256: str


@dataclass(frozen=True)
class _QDigital:
    evidence_references: tuple[_QEvidence, ...]


@dataclass(frozen=True)
class _QSubmission:
    entry_method: str
    digital_provenance: _QDigital | None


@dataclass(frozen=True)
class _QStudent:
    student_id: str
    submission: _QSubmission


@dataclass(frozen=True)
class _QManifest:
    record_set: _RecordSet
    work: _QWork
    students: tuple[_QStudent, ...]


@dataclass(frozen=True)
class _QProducerRequest:
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
class _QResult:
    artifact_kind: str
    work: object
    record_set_revision: int
    student_id: str
    media_type: str
    sha256: str
    byte_size: int
    data: bytes
    evidence_reference: _QEvidence | None = None


class _QAuthorizationError(Exception):
    pass


class _QValidationError(Exception):
    pass


class _QUnavailableError(Exception):
    pass


class _QIntegrityError(Exception):
    pass


class _QReadError(Exception):
    pass


class _QApi:
    def __init__(
        self,
        *,
        content: bytes,
        media_type: str,
        result_sha256: str | None = None,
    ) -> None:
        self.content = content
        self.media_type = media_type
        self.result_sha256 = result_sha256
        self.calls = 0
        self.native_io_calls = 0

    def read(
        self,
        workspace_root: Path,
        manifest: _QManifest,
        student_id: str,
        artifact_kind: str,
        *,
        purpose: str,
        authorization_gate: object,
    ) -> tuple[_QResult, ...]:
        assert workspace_root.is_absolute()
        self.calls += 1
        producer_request = _QProducerRequest(
            work=manifest.work,
            record_set_id=manifest.record_set.record_set_id,
            record_set_revision=manifest.record_set.revision,
            student_id=student_id,
            artifact_kind=artifact_kind,
            purpose=purpose,
        )
        decision = getattr(authorization_gate, "authorize")(producer_request)
        if not isinstance(decision, _ProducerDecision) or decision.status != "allowed":
            raise _QAuthorizationError("authorization not affirmed")
        self.native_io_calls += 1
        evidence = (
            manifest.students[0].submission.digital_provenance.evidence_references[0]
            if artifact_kind == "student_work"
            else None
        )
        digest = (
            self.result_sha256
            if self.result_sha256 is not None
            else hashlib.sha256(self.content).hexdigest()
        )
        return (
            _QResult(
                artifact_kind=artifact_kind,
                work=manifest.work,
                record_set_revision=manifest.record_set.revision,
                student_id=student_id,
                media_type=self.media_type,
                sha256=digest,
                byte_size=len(self.content),
                data=self.content,
                evidence_reference=evidence,
            ),
        )


def _quillan_module(api: _QApi) -> SimpleNamespace:
    return SimpleNamespace(
        AcademicResultArtifactAuthorizationDecision=_ProducerDecision,
        AuthorizedAcademicResultArtifact=_QResult,
        read_authorized_academic_result_artifacts=api.read,
        QuillanAcademicResultArtifactAuthorizationError=_QAuthorizationError,
        QuillanAcademicResultArtifactValidationError=_QValidationError,
        QuillanAcademicResultArtifactUnavailableError=_QUnavailableError,
        QuillanAcademicResultArtifactIntegrityError=_QIntegrityError,
        QuillanAcademicResultArtifactReadError=_QReadError,
    )


def _quillan_context(
    tmp_path: Path,
    kind: str,
) -> CandidateEvidencePreviewPreparedContext:
    artifact_kind = (
        "original_student_work"
        if kind == "student_work"
        else "rendered_feedback"
    )
    base = _base_context(
        tmp_path,
        module_id="vitrine_quillan_fixture",
        artifact_kind=artifact_kind,
    )
    source = base.result.verified_source
    student_id = next(
        relationship.source_subject_id
        for relationship in source.source_relationships
        if relationship.source_subject_kind == "core_student"
    )
    evidence = _QEvidence("evidence_alpha", PNG_SHA256)
    manifest = _QManifest(
        record_set=_RecordSet(),
        work=_QWork(),
        students=(
            _QStudent(
                student_id,
                _QSubmission(
                    "pds2_response_pages",
                    _QDigital((evidence,)),
                ),
            ),
        ),
    )
    if kind == "student_work":
        representation = QUILLAN_SELECTED_STUDENT_WORK_REPRESENTATION_KIND
        media_type = QUILLAN_STUDENT_WORK_PLANNED_MEDIA_TYPE
        artifact_id = quillan_evidence_source_id(
            class_id=manifest.work.class_id,
            work_id=manifest.work.work_id,
            student_id=student_id,
            evidence_id=evidence.evidence_id,
        )
        fields = (
            ProjectionField(key="artifact_request_kind", value=kind),
            ProjectionField(key="evidence_id", value=evidence.evidence_id),
        )
    else:
        representation = (
            QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND
            if kind == "feedback_pdf"
            else QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND
        )
        media_type = (
            QUILLAN_FEEDBACK_PDF_MEDIA_TYPE
            if kind == "feedback_pdf"
            else QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE
        )
        artifact_id = quillan_feedback_source_id(
            class_id=manifest.work.class_id,
            work_id=manifest.work.work_id,
            student_id=student_id,
            artifact_request_kind=kind,
        )
        fields = (ProjectionField(key="artifact_request_kind", value=kind),)

    producer = replace(
        source.producer_source,
        producer_module_id="quillan",
        producer_contract_version="quillan_academic_work_v1",
        source_record_kind="artifact_capability",
        source_record_id=artifact_id,
        source_record_contract_version=None,
        native_revision=manifest.record_set.revision,
        native_disposition=kind,
        projection_contract_version="vitrine_candidate_projection_v1",
    )
    artifact = SourceArtifactReference(
        artifact_id=artifact_id,
        artifact_kind=artifact_kind,
        representation_kind=representation,
        media_type=media_type,
        source_locator=None,
        native_revision=manifest.record_set.revision,
        source_digest=None,
        byte_size=None,
        language=None,
        accessibility_relationship=None,
    )
    live_source = replace(
        source,
        projection_kind=representation,
        producer_source=producer,
        source_artifact=artifact,
        source_relationships=(
            ProjectedProducerRelationship(
                source_subject_kind="core_student",
                source_subject_id=student_id,
                relationship_kind="submission_subject",
                relationship_authority="quillan",
                supporting_source_reference=artifact_id,
            ),
        ),
        display_snapshot=ProjectionDisplaySnapshot(
            title="Quillan preview fixture",
            summary="Synthetic live-shaped preview source.",
            fields=fields,
        ),
    )
    endpoint = replace(
        base.result.authority.source_endpoint,
        core_publication=replace(
            base.result.authority.source_endpoint.core_publication,
            work=replace(
                base.result.authority.source_endpoint.core_publication.work,
                module_id="quillan",
            ),
        ),
        producer_source=producer,
        source_artifact=artifact,
    )
    authority = replace(
        base.result.authority,
        producer_module_id="quillan",
        source_record_kind=producer.source_record_kind,
        source_record_id=producer.source_record_id,
        source_artifact_id=artifact.artifact_id,
        artifact_kind=artifact.artifact_kind,
        representation_kind=artifact.representation_kind,
        media_type=artifact.media_type,
        source_endpoint=endpoint,
    )
    result = replace(
        base.result,
        authority=authority,
        verified_source=live_source,
        preview_kind="artifact_preview",
        artifact_authorization_required=True,
        structured_preview=None,
        unavailable_reason=None,
    )
    return replace(
        base,
        result=result,
        producer_public_model=manifest,
    )


@dataclass(frozen=True)
class _CWork:
    module_id: str = "concord"
    class_id: str = "class_alpha"
    work_id: str = "activity_alpha"


@dataclass(frozen=True)
class _CProjection:
    source_snapshot_revision: int = 9


@dataclass(frozen=True)
class _CManifest:
    work: _CWork
    record_set: _RecordSet
    projection: _CProjection


@dataclass(frozen=True)
class _CEvidence:
    evidence_kind: str
    owning_system: str
    record_id: str


@dataclass(frozen=True)
class _CProducerRequest:
    work: object
    record_set_id: str
    record_set_revision: int
    source_snapshot_revision: int
    score_record_id: str
    score_evidence_link_id: str
    evidence_reference: _CEvidence
    purpose: str


@dataclass(frozen=True)
class _CPage:
    artifact_page_id: str


@dataclass(frozen=True)
class _CArtifact:
    artifact_instance_id: str
    pages: tuple[_CPage, ...]


@dataclass(frozen=True)
class _CResult:
    representation: str
    work: object
    record_set_revision: int
    source_snapshot_revision: int
    score_record_id: str
    score_evidence_link_id: str
    evidence_reference: _CEvidence
    artifact: _CArtifact
    media_type: str
    sha256: str
    byte_size: int
    content: bytes


class _CAuthorizationError(Exception):
    pass


class _CValidationError(Exception):
    pass


class _CNotFoundError(Exception):
    pass


class _CUnavailableError(Exception):
    pass


class _CAmbiguityError(Exception):
    pass


class _CIntegrityError(Exception):
    pass


class _CApi:
    def __init__(self, *, tamper_digest: bool = False) -> None:
        self.tamper_digest = tamper_digest
        self.calls = 0
        self.native_io_calls = 0

    def read(
        self,
        workspace_root: Path,
        manifest: _CManifest,
        score_evidence_link_id: str,
        *,
        purpose: str,
        authorization_gate: object,
    ) -> _CResult:
        assert workspace_root.is_absolute()
        self.calls += 1
        evidence = _CEvidence(
            "artifact_instance",
            "concord",
            "artifact_alpha",
        )
        request = _CProducerRequest(
            work=manifest.work,
            record_set_id=manifest.record_set.record_set_id,
            record_set_revision=manifest.record_set.revision,
            source_snapshot_revision=manifest.projection.source_snapshot_revision,
            score_record_id="score_alpha",
            score_evidence_link_id=score_evidence_link_id,
            evidence_reference=evidence,
            purpose=purpose,
        )
        decision = getattr(authorization_gate, "authorize")(request)
        if not isinstance(decision, _ProducerDecision) or decision.status != "allowed":
            raise _CAuthorizationError("authorization not affirmed")
        self.native_io_calls += 1
        digest = "0" * 64 if self.tamper_digest else PDF_SHA256
        return _CResult(
            representation="returned_artifact_pdf",
            work=manifest.work,
            record_set_revision=manifest.record_set.revision,
            source_snapshot_revision=manifest.projection.source_snapshot_revision,
            score_record_id="score_alpha",
            score_evidence_link_id=score_evidence_link_id,
            evidence_reference=evidence,
            artifact=_CArtifact("artifact_alpha", ()),
            media_type=CONCORD_ARTIFACT_MEDIA_TYPE,
            sha256=digest,
            byte_size=len(PDF),
            content=PDF,
        )


def _concord_module(api: _CApi) -> SimpleNamespace:
    return SimpleNamespace(
        AcademicResultArtifactAuthorizationDecision=_ProducerDecision,
        AuthorizedAcademicResultArtifact=_CResult,
        read_authorized_academic_result_artifact=api.read,
        ConcordAcademicResultArtifactAuthorizationError=_CAuthorizationError,
        ConcordAcademicResultArtifactValidationError=_CValidationError,
        ConcordAcademicResultArtifactNotFoundError=_CNotFoundError,
        ConcordAcademicResultArtifactUnavailableError=_CUnavailableError,
        ConcordAcademicResultArtifactAmbiguityError=_CAmbiguityError,
        ConcordAcademicResultArtifactIntegrityError=_CIntegrityError,
    )


def _concord_context(
    tmp_path: Path,
) -> CandidateEvidencePreviewPreparedContext:
    base = _base_context(
        tmp_path,
        module_id="vitrine_concord_fixture",
        artifact_kind="collaborative_artifact",
    )
    source = base.result.verified_source
    manifest = _CManifest(
        work=_CWork(),
        record_set=_RecordSet(),
        projection=_CProjection(),
    )
    producer = replace(
        source.producer_source,
        producer_module_id="concord",
        producer_contract_version="concord_academic_work_v1",
        source_record_kind="score_evidence_link",
        source_record_id="link_alpha",
        source_record_contract_version=None,
        native_revision=None,
        native_disposition="supporting",
        projection_contract_version="vitrine_candidate_projection_v1",
    )
    artifact = SourceArtifactReference(
        artifact_id="artifact_alpha",
        artifact_kind="collaborative_artifact",
        representation_kind=CONCORD_ARTIFACT_REPRESENTATION_KIND,
        media_type=CONCORD_ARTIFACT_MEDIA_TYPE,
        source_locator=None,
        native_revision=manifest.projection.source_snapshot_revision,
        source_digest=None,
        byte_size=None,
        language=None,
        accessibility_relationship=None,
    )
    live_source = replace(
        source,
        projection_kind="concord:artifact_evidence",
        producer_source=producer,
        source_artifact=artifact,
        display_snapshot=ProjectionDisplaySnapshot(
            title="Concord Artifact evidence",
            summary="Synthetic live-shaped Concord Artifact.",
            fields=(
                ProjectionField(
                    key="score_evidence_parent_score_record_id",
                    value="score_alpha",
                ),
                ProjectionField(
                    key="evidence_kind",
                    value="artifact_instance",
                ),
                ProjectionField(
                    key="evidence_owning_system",
                    value="concord",
                ),
                ProjectionField(
                    key="evidence_record_id",
                    value=artifact.artifact_id,
                ),
            ),
        ),
    )
    endpoint = replace(
        base.result.authority.source_endpoint,
        core_publication=replace(
            base.result.authority.source_endpoint.core_publication,
            work=replace(
                base.result.authority.source_endpoint.core_publication.work,
                module_id="concord",
            ),
        ),
        producer_source=producer,
        source_artifact=artifact,
    )
    authority = replace(
        base.result.authority,
        producer_module_id="concord",
        source_record_kind=producer.source_record_kind,
        source_record_id=producer.source_record_id,
        source_artifact_id=artifact.artifact_id,
        artifact_kind=artifact.artifact_kind,
        representation_kind=artifact.representation_kind,
        media_type=artifact.media_type,
        source_endpoint=endpoint,
    )
    result = replace(
        base.result,
        authority=authority,
        verified_source=live_source,
        preview_kind="artifact_preview",
        artifact_authorization_required=True,
        structured_preview=None,
        unavailable_reason=None,
    )
    return replace(
        base,
        result=result,
        producer_public_model=manifest,
    )


def _replay_exact(
    monkeypatch: pytest.MonkeyPatch,
    context: CandidateEvidencePreviewPreparedContext,
) -> list[object]:
    calls: list[object] = []

    def replay(_workspace_root: object, request: object) -> object:
        calls.append(request)
        return context.result.authority

    monkeypatch.setattr(
        artifact_preview,
        "resolve_candidate_evidence_preview_authority",
        replay,
    )
    return calls


def test_prepared_context_retains_authorized_public_model(tmp_path: Path) -> None:
    context = _base_context(
        tmp_path,
        module_id="vitrine_scoreform_fixture",
        artifact_kind="assessment_summary",
    )

    assert context.workspace_root.is_absolute()
    assert context.producer_public_model is not None
    assert context.result.preview_kind == "structured_summary"


def test_quillan_student_work_preview_bridges_exact_authorization_before_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _quillan_context(tmp_path, "student_work")
    replay_calls = _replay_exact(monkeypatch, context)
    api = _QApi(content=PNG, media_type="image/png")
    monkeypatch.setattr(
        artifact_preview,
        "import_module",
        lambda name: _quillan_module(api),
    )
    gate = _PreviewGate("allowed")

    result = acquire_candidate_evidence_artifact_preview(
        context.workspace_root,
        context,
        authorization_gate=gate,
    )

    assert isinstance(result, CandidateEvidenceArtifactPreview)
    assert result.content == PNG
    assert result.media_type == "image/png"
    assert result.sha256 == PNG_SHA256
    assert result.byte_size == len(PNG)
    assert result.source_artifact_id == context.result.authority.source_artifact_id
    assert gate.calls == 1
    assert api.calls == 1
    assert api.native_io_calls == 1
    assert len(replay_calls) == 2
    auth_request = gate.last_request
    assert auth_request is not None
    assert getattr(auth_request, "operation") == CANDIDATE_EVIDENCE_PREVIEW_OPERATION
    assert getattr(auth_request, "candidate_id") == context.result.authority.candidate_id
    assert not hasattr(auth_request, "snapshot_build_plan_id")
    assert not hasattr(auth_request, "snapshot_build_attempt_id")


@pytest.mark.parametrize(
    ("kind", "content", "media_type"),
    (
        ("feedback_pdf", PDF, QUILLAN_FEEDBACK_PDF_MEDIA_TYPE),
        ("feedback_markdown", MARKDOWN, QUILLAN_FEEDBACK_MARKDOWN_MEDIA_TYPE),
    ),
)
def test_quillan_feedback_preview_preserves_exact_representation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    content: bytes,
    media_type: str,
) -> None:
    context = _quillan_context(tmp_path, kind)
    _replay_exact(monkeypatch, context)
    api = _QApi(content=content, media_type=media_type)
    monkeypatch.setattr(
        artifact_preview,
        "import_module",
        lambda name: _quillan_module(api),
    )

    result = acquire_candidate_evidence_artifact_preview(
        context.workspace_root,
        context,
        authorization_gate=_PreviewGate("allowed"),
    )

    assert result.content == content
    assert result.media_type == media_type
    assert result.representation_kind == (
        QUILLAN_FEEDBACK_PDF_REPRESENTATION_KIND
        if kind == "feedback_pdf"
        else QUILLAN_FEEDBACK_MARKDOWN_REPRESENTATION_KIND
    )


def test_preview_denial_happens_inside_producer_gate_before_native_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _quillan_context(tmp_path, "student_work")
    _replay_exact(monkeypatch, context)
    api = _QApi(content=PNG, media_type="image/png")
    monkeypatch.setattr(
        artifact_preview,
        "import_module",
        lambda name: _quillan_module(api),
    )

    with pytest.raises(Exception) as captured:
        acquire_candidate_evidence_artifact_preview(
            context.workspace_root,
            context,
            authorization_gate=_PreviewGate("denied"),
        )

    assert getattr(captured.value, "code") == (
        "candidate_evidence_preview.authorization_denied"
    )
    assert api.calls == 1
    assert api.native_io_calls == 0


def test_quillan_tampered_digest_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _quillan_context(tmp_path, "student_work")
    _replay_exact(monkeypatch, context)
    api = _QApi(
        content=PNG,
        media_type="image/png",
        result_sha256="0" * 64,
    )
    monkeypatch.setattr(
        artifact_preview,
        "import_module",
        lambda name: _quillan_module(api),
    )

    with pytest.raises(Exception) as captured:
        acquire_candidate_evidence_artifact_preview(
            context.workspace_root,
            context,
            authorization_gate=_PreviewGate("allowed"),
        )

    assert getattr(captured.value, "code") == (
        "candidate_evidence_preview.artifact_source_integrity_failed"
    )


def test_concord_preview_returns_exact_authorized_pdf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _concord_context(tmp_path)
    replay_calls = _replay_exact(monkeypatch, context)
    api = _CApi()
    monkeypatch.setattr(
        artifact_preview,
        "import_module",
        lambda name: _concord_module(api),
    )
    gate = _PreviewGate("allowed")

    result = acquire_candidate_evidence_artifact_preview(
        context.workspace_root,
        context,
        authorization_gate=gate,
    )

    assert result.content == PDF
    assert result.media_type == CONCORD_ARTIFACT_MEDIA_TYPE
    assert result.sha256 == PDF_SHA256
    assert result.source_artifact_id == "artifact_alpha"
    assert result.representation_kind == CONCORD_ARTIFACT_REPRESENTATION_KIND
    assert api.native_io_calls == 1
    assert gate.calls == 1
    assert len(replay_calls) == 2


def test_concord_tampered_bytes_metadata_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _concord_context(tmp_path)
    _replay_exact(monkeypatch, context)
    api = _CApi(tamper_digest=True)
    monkeypatch.setattr(
        artifact_preview,
        "import_module",
        lambda name: _concord_module(api),
    )

    with pytest.raises(Exception) as captured:
        acquire_candidate_evidence_artifact_preview(
            context.workspace_root,
            context,
            authorization_gate=_PreviewGate("allowed"),
        )

    assert getattr(captured.value, "code") == (
        "candidate_evidence_preview.artifact_source_integrity_failed"
    )


def test_unreleased_or_fixture_artifact_bridge_is_not_used(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _base_context(
        tmp_path,
        module_id="vitrine_quillan_fixture",
        artifact_kind="original_student_work",
    )
    replay_calls = _replay_exact(monkeypatch, context)

    def fail_import(name: str) -> object:
        raise AssertionError(f"unexpected producer import: {name}")

    monkeypatch.setattr(artifact_preview, "import_module", fail_import)

    with pytest.raises(Exception) as captured:
        acquire_candidate_evidence_artifact_preview(
            context.workspace_root,
            context,
            authorization_gate=_PreviewGate("allowed"),
        )

    assert getattr(captured.value, "code") == (
        "candidate_evidence_preview.artifact_not_supported"
    )
    assert len(replay_calls) == 1
