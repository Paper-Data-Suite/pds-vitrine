"""Installed exact-wheel Candidate evidence-review acceptance for issue #96.

This runner is copied outside the source checkout and executed only inside the
authenticated live environment created by qualify_installed_live_portfolio.py.
It reuses the issue #71 producer-native builders, but stops after Candidate
presentation and explicit preview. No curation or Snapshot state is created.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.live_installed_acceptance_support import (
        DeterministicIds,
        ProducerPublication,
        build_concord_publication,
        build_quillan_publication,
        build_scoreform_publication,
        discover_live_candidates,
        install_improvement_portfolio,
        low_density_json,
        prepare_core_identity_sources,
    )
else:
    from live_installed_acceptance_support import (
        DeterministicIds,
        ProducerPublication,
        build_concord_publication,
        build_quillan_publication,
        build_scoreform_publication,
        discover_live_candidates,
        install_improvement_portfolio,
        low_density_json,
        prepare_core_identity_sources,
    )

from vitrine.candidate_evidence_artifact_preview import (
    CandidateEvidenceArtifactPreview,
    acquire_candidate_evidence_artifact_preview,
)
from vitrine.candidate_evidence_presentation import (
    build_candidate_evidence_presentation,
)
from vitrine.candidate_evidence_preview import (
    CANDIDATE_EVIDENCE_PREVIEW_MANIFEST_OPERATION,
    CANDIDATE_EVIDENCE_PREVIEW_OPERATION,
    CandidateEvidencePreviewAuthorizationDecision,
    CandidateEvidencePreviewAuthorizationRequest,
    CandidateEvidencePreviewError,
    CandidateEvidencePreviewPreparedContext,
    CandidateEvidencePreviewRequest,
    build_candidate_evidence_preview_authorization_request,
    prepare_candidate_evidence_preview_context,
)
from vitrine.candidate_inbox import (
    CandidateInboxDetail,
    CandidateInboxQuery,
    get_candidate_inbox_detail,
    list_candidate_inbox,
)
from vitrine.models import ActorAttribution
from vitrine.producer_adapters import build_adapter_registry
from vitrine.producer_reader_services import (
    SourceReadAuthorizationDecision,
    SourceReadAuthorizationRequest,
)
from vitrine.storage import load_current_state

EXPECTED_VERSIONS = {
    "pds-core": "0.6.3",
    "scoreform": "0.11.0",
    "quillan": "0.10.1",
    "pds-concord": "0.3.0",
    "pds-vitrine": "0.3.0",
}
PURPOSE = "issue_96_live_installed_candidate_evidence_review"


class CandidateEvidenceInstalledAcceptanceError(RuntimeError):
    pass


class PreviewSourceReadGate:
    def __init__(
        self,
        *,
        portfolio_id: str,
        portfolio_subject_id: str,
        publication_ids: set[str],
    ) -> None:
        self.portfolio_id = portfolio_id
        self.portfolio_subject_id = portfolio_subject_id
        self.publication_ids = frozenset(publication_ids)
        self.requests: list[SourceReadAuthorizationRequest] = []

    def authorize(
        self,
        request: SourceReadAuthorizationRequest,
    ) -> SourceReadAuthorizationDecision:
        self.requests.append(request)
        allowed = (
            request.portfolio_id == self.portfolio_id
            and request.portfolio_subject_id == self.portfolio_subject_id
            and request.publication_id in self.publication_ids
            and request.operation == CANDIDATE_EVIDENCE_PREVIEW_MANIFEST_OPERATION
            and request.purpose == PURPOSE
        )
        return SourceReadAuthorizationDecision(
            outcome="allowed" if allowed else "denied",
            reason_codes=("issue_96:exact_preview_manifest_scope",) if allowed else (),
        )


class ExactArtifactPreviewGate:
    def __init__(
        self,
        expected: CandidateEvidencePreviewAuthorizationRequest,
    ) -> None:
        self.expected = expected
        self.requests: list[CandidateEvidencePreviewAuthorizationRequest] = []

    def authorize(
        self,
        request: CandidateEvidencePreviewAuthorizationRequest,
    ) -> CandidateEvidencePreviewAuthorizationDecision:
        self.requests.append(request)
        if request != self.expected:
            return CandidateEvidencePreviewAuthorizationDecision(
                outcome="denied",
                reason_codes=("issue_96:preview_request_mismatch",),
            )
        if (
            request.operation != CANDIDATE_EVIDENCE_PREVIEW_OPERATION
            or request.purpose != PURPOSE
            or request.producer_module_id not in {"quillan", "concord"}
            or request.source_artifact_id is None
        ):
            return CandidateEvidencePreviewAuthorizationDecision(
                outcome="denied",
                reason_codes=("issue_96:preview_scope_denied",),
            )
        return CandidateEvidencePreviewAuthorizationDecision(
            outcome="allowed",
            authority_reference="issue_96:installed_exact_preview",
        )


def _actor() -> ActorAttribution:
    return ActorAttribution(
        actor_kind="authorized_adult",
        actor_id="issue96_teacher",
        owning_system="local",
        role_snapshot="teacher",
        display_label_snapshot="Synthetic Issue 96 Teacher",
    )


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CandidateEvidenceInstalledAcceptanceError(message)


def _require_installed_isolation(repository: Path) -> None:
    _require("PYTHONPATH" not in os.environ, "PYTHONPATH must be absent")
    for distribution, version in EXPECTED_VERSIONS.items():
        _require(
            metadata.version(distribution) == version,
            f"installed version mismatch for {distribution}",
        )
    prefix = Path(sys.prefix).resolve()
    for module_name in ("pds_core", "scoreform", "quillan", "concord", "vitrine"):
        module = __import__(module_name)
        raw = getattr(module, "__file__", None)
        if not isinstance(raw, str) or not raw:
            raise CandidateEvidenceInstalledAcceptanceError(
                f"{module_name} has no origin"
            )
        origin = Path(raw).resolve()
        _require(origin.is_relative_to(prefix), f"{module_name} is outside live venv")
        _require(
            "site-packages" in {part.casefold() for part in origin.parts},
            f"{module_name} is not installed from site-packages",
        )
        _require(
            not origin.is_relative_to(repository),
            f"{module_name} imported from source checkout",
        )


def _detail_module(detail: CandidateInboxDetail) -> str:
    endpoint = (
        detail.evaluation.source_endpoint
        if detail.evaluation is not None
        else detail.candidate.source_endpoint
        if detail.candidate is not None
        else None
    )
    if endpoint is None:
        raise CandidateEvidenceInstalledAcceptanceError(
            "Candidate detail has no exact source endpoint"
        )
    return endpoint.producer_source.producer_module_id


def _preview_request(detail: CandidateInboxDetail) -> CandidateEvidencePreviewRequest:
    item = detail.item
    return CandidateEvidencePreviewRequest(
        portfolio_id=item.portfolio_id,
        portfolio_subject_id=item.portfolio_subject_id,
        entry_id=item.entry_id,
        candidate_id=item.candidate_id,
        candidate_evaluation_id=item.current_evaluation_id,
        requesting_actor=_actor(),
        requested_purpose=PURPOSE,
        observed_state_revision=detail.observed_state_revision,
    )


def _prepare_preview(
    workspace: Path,
    detail: CandidateInboxDetail,
    *,
    source_gate: PreviewSourceReadGate,
) -> CandidateEvidencePreviewPreparedContext:
    return prepare_candidate_evidence_preview_context(
        workspace,
        _preview_request(detail),
        adapter_registry=build_adapter_registry(),
        source_read_authorization_gate=source_gate,
    )


def _acquire_artifact(
    workspace: Path,
    context: CandidateEvidencePreviewPreparedContext,
) -> tuple[CandidateEvidenceArtifactPreview, int]:
    expected = build_candidate_evidence_preview_authorization_request(
        context.result.authority
    )
    gate = ExactArtifactPreviewGate(expected)
    result = acquire_candidate_evidence_artifact_preview(
        workspace,
        context,
        authorization_gate=gate,
    )
    _require(len(gate.requests) == 1, "Artifact preview authorization was not exact-once")
    _require(gate.requests[0] == expected, "Artifact preview authorization request drifted")
    _require(result.byte_size == len(result.content), "Artifact byte size disagrees")
    _require(
        hashlib.sha256(result.content).hexdigest() == result.sha256,
        "Artifact digest disagrees",
    )
    return result, len(gate.requests)


def run(
    *,
    workspace: Path,
    repository: Path,
    work_root: Path,
) -> dict[str, object]:
    repository = repository.resolve(strict=True)
    workspace = workspace.resolve()
    work_root = work_root.resolve()
    _require(not workspace.exists(), "installed acceptance workspace must begin absent")
    _require(
        not workspace.is_relative_to(repository)
        and not work_root.is_relative_to(repository),
        "installed acceptance roots must remain outside repository",
    )
    work_root.mkdir(parents=True, exist_ok=True)
    _require_installed_isolation(repository)

    ids = DeterministicIds()
    standards = prepare_core_identity_sources(workspace)
    scoreform = build_scoreform_publication(workspace)
    quillan = build_quillan_publication(
        workspace,
        standards=standards,
        work_root=work_root,
    )
    concord = build_concord_publication(workspace, standards=standards)
    publications: tuple[ProducerPublication, ...] = (scoreform, quillan, concord)
    portfolio = install_improvement_portfolio(workspace, ids=ids)
    discovery, discovery_gate = discover_live_candidates(
        workspace,
        portfolio=portfolio,
        publications=publications,
        ids=ids,
    )
    _require(
        set(discovery) == {"scoreform", "quillan", "concord"},
        "live discovery did not cover all three producers",
    )
    _require(len(discovery_gate.requests) == 3, "live discovery authorization drifted")

    inbox = list_candidate_inbox(
        workspace,
        CandidateInboxQuery(
            portfolio_id=portfolio.portfolio_id,
            limit=100,
        ),
    )
    details = tuple(
        get_candidate_inbox_detail(workspace, item.entry_id)
        for item in inbox.items
    )
    by_module: dict[str, list[CandidateInboxDetail]] = {
        "scoreform": [],
        "quillan": [],
        "concord": [],
    }
    for detail in details:
        module_id = _detail_module(detail)
        if module_id in by_module:
            by_module[module_id].append(detail)

    presentations = {
        module_id: tuple(
            build_candidate_evidence_presentation(detail)
            for detail in module_details
        )
        for module_id, module_details in by_module.items()
    }
    scoreform_labels = tuple(
        sorted(item.primary_label for item in presentations["scoreform"])
    )
    _require(
        scoreform_labels
        == (
            "Assessment Attempt — Synthetic Baseline Assessment — Attempt 1",
            "Assessment Attempt — Synthetic Baseline Assessment — Attempt 2",
        ),
        f"ScoreForm instructional labels disagree: {scoreform_labels}",
    )

    quillan_labels = {item.primary_label for item in presentations["quillan"]}
    expected_quillan = {
        "Review — Synthetic Later Writing Evidence",
        "Student Work — Synthetic Later Writing Evidence",
        "Feedback — Synthetic Later Writing Evidence (PDF)",
        "Feedback — Synthetic Later Writing Evidence (Markdown)",
    }
    _require(
        expected_quillan.issubset(quillan_labels),
        f"Quillan instructional labels disagree: {sorted(quillan_labels)}",
    )

    concord_labels = {item.primary_label for item in presentations["concord"]}
    _require(
        "Collaborative Work — Synthetic Collaborative Later Evidence" in concord_labels,
        f"Concord collaborative label missing: {sorted(concord_labels)}",
    )
    all_labels = scoreform_labels + tuple(quillan_labels) + tuple(concord_labels)
    _require(
        all("Artifact capability" not in label for label in all_labels),
        "producer capability terminology leaked into instructional labels",
    )

    source_gate = PreviewSourceReadGate(
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        publication_ids={item.publication_id for item in publications},
    )
    before_preview = load_current_state(workspace).state_revision

    scoreform_detail = next(
        detail
        for detail in by_module["scoreform"]
        if build_candidate_evidence_presentation(detail).variant_label == "Attempt 1"
    )
    scoreform_context = _prepare_preview(
        workspace,
        scoreform_detail,
        source_gate=source_gate,
    )
    _require(
        scoreform_context.result.preview_kind == "structured_summary",
        "ScoreForm did not remain structured-summary only",
    )
    _require(
        not scoreform_context.result.artifact_authorization_required,
        "ScoreForm incorrectly requires Artifact-byte authorization",
    )
    structured = scoreform_context.result.structured_preview
    if structured is None:
        raise CandidateEvidenceInstalledAcceptanceError(
            "ScoreForm structured preview is missing"
        )
    _require(
        structured.title == "Synthetic Baseline Assessment",
        "ScoreForm structured preview lost exact registration title",
    )
    structured_labels = {item.label for item in structured.fields}
    _require("Attempt" in structured_labels, "ScoreForm attempt field is missing")
    try:
        acquire_candidate_evidence_artifact_preview(
            workspace,
            scoreform_context,
            authorization_gate=ExactArtifactPreviewGate(
                build_candidate_evidence_preview_authorization_request(
                    scoreform_context.result.authority
                )
            ),
        )
    except CandidateEvidencePreviewError as error:
        _require(
            error.code == "candidate_evidence_preview.artifact_not_supported",
            f"ScoreForm byte-preview failure changed: {error.code}",
        )
    else:
        raise CandidateEvidenceInstalledAcceptanceError(
            "ScoreForm fabricated byte-bearing Artifact preview"
        )

    quillan_pdf_detail = next(
        detail
        for detail in by_module["quillan"]
        if build_candidate_evidence_presentation(detail).representation_label == "PDF"
    )
    quillan_context = _prepare_preview(
        workspace,
        quillan_pdf_detail,
        source_gate=source_gate,
    )
    _require(
        quillan_context.result.preview_kind == "artifact_preview",
        "Quillan PDF did not classify as Artifact preview",
    )
    quillan_artifact, quillan_auth = _acquire_artifact(
        workspace,
        quillan_context,
    )
    _require(
        quillan_artifact.media_type == "application/pdf",
        "Quillan preview media type changed",
    )
    _require(
        quillan_artifact.content.startswith(b"%PDF"),
        "Quillan authorized preview is not the exact PDF bytes",
    )

    concord_detail = next(
        detail
        for detail in by_module["concord"]
        if build_candidate_evidence_presentation(detail).evidence_kind
        == "Collaborative Work"
    )
    concord_context = _prepare_preview(
        workspace,
        concord_detail,
        source_gate=source_gate,
    )
    _require(
        concord_context.result.preview_kind == "artifact_preview",
        "Concord collaborative evidence did not classify as Artifact preview",
    )
    concord_artifact, concord_auth = _acquire_artifact(
        workspace,
        concord_context,
    )
    _require(
        concord_artifact.media_type == "application/pdf",
        "Concord preview media type changed",
    )
    _require(
        concord_artifact.content.startswith(b"%PDF"),
        "Concord authorized preview is not the exact returned PDF bytes",
    )

    after_preview = load_current_state(workspace).state_revision
    _require(
        after_preview == before_preview,
        "Candidate evidence preview mutated Vitrine state",
    )
    _require(
        len(source_gate.requests) == 3,
        "preview manifest authorization was not exact-once per tested source",
    )
    _require(
        all(
            request.operation == CANDIDATE_EVIDENCE_PREVIEW_MANIFEST_OPERATION
            and request.purpose == PURPOSE
            for request in source_gate.requests
        ),
        "preview manifest authorization request scope drifted",
    )

    return {
        "mode": "issue96_live_candidate_evidence_review",
        "release_versions": dict(sorted(EXPECTED_VERSIONS.items())),
        "candidate_counts": {
            key: len(value)
            for key, value in sorted(by_module.items())
        },
        "scoreform_labels": list(scoreform_labels),
        "quillan_required_labels_present": True,
        "concord_collaborative_label_present": True,
        "scoreform_preview_kind": scoreform_context.result.preview_kind,
        "scoreform_artifact_bytes": False,
        "quillan_preview_media_type": quillan_artifact.media_type,
        "concord_preview_media_type": concord_artifact.media_type,
        "preview_manifest_authorization_requests": len(source_gate.requests),
        "artifact_preview_authorization_requests": quillan_auth + concord_auth,
        "preview_state_revision_unchanged": True,
        "fixture_registry_used": False,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        summary = run(
            workspace=args.workspace,
            repository=args.repository,
            work_root=args.work_root,
        )
    except Exception as error:
        print(
            json.dumps(
                {
                    "mode": "issue96_live_candidate_evidence_review",
                    "status": "failed",
                    "error_type": type(error).__name__,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(low_density_json(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
