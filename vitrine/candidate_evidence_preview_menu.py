"""Teacher-facing Candidate evidence preview interaction.

Issue #96 keeps preview optional and explicit. Merely rendering Candidate detail
never calls this module. Once the teacher chooses View evidence, this layer uses
the exact read-only preview services, renders bounded structured summaries, or
launches verified producer Artifact bytes from a temporary directory that is
removed when the teacher returns.
"""

from __future__ import annotations

import webbrowser
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final, TextIO, cast

from vitrine.candidate_evidence_artifact_preview import (
    CandidateEvidenceArtifactPreview,
    acquire_candidate_evidence_artifact_preview,
)
from vitrine.candidate_evidence_preview import (
    CandidateEvidencePreviewError,
    CandidateEvidencePreviewRequest,
    CandidateEvidenceStructuredPreview,
    prepare_candidate_evidence_preview_context,
)
from vitrine.candidate_inbox import CandidateInboxDetail
from vitrine.menu_types import ClearFunction, InputFunction
from vitrine.models import ActorAttribution
from vitrine.producer_reader_services import (
    SourceReadAuthorizationGate as SharedSourceReadAuthorizationGate,
)
from vitrine.workflow_context import VitrineWorkflowDependencies

CandidateEvidencePreviewLauncher = Callable[[Path], bool]

_MEDIA_SUFFIXES: Final[dict[str, str]] = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/tiff": ".tiff",
    "text/markdown; charset=utf-8": ".md",
}


def _write(output: TextIO, *lines: str) -> None:
    for line in lines:
        print(line, file=output)


def _default_launcher(path: Path) -> bool:
    return bool(webbrowser.open(path.resolve().as_uri(), new=2))


def _preview_actor(
    actor: ActorAttribution | None,
    input_fn: InputFunction,
) -> ActorAttribution | None:
    if actor is not None:
        return actor
    raw = input_fn("Teacher/actor ID for evidence preview (Enter to cancel): ").strip()
    if not raw or raw.casefold() in {"b", "m", "q"}:
        return None
    return ActorAttribution(
        actor_kind="authorized_adult",
        actor_id=raw,
        owning_system="local",
        role_snapshot="teacher",
    )


def _request(
    detail: CandidateInboxDetail,
    actor: ActorAttribution,
) -> CandidateEvidencePreviewRequest:
    item = detail.item
    return CandidateEvidencePreviewRequest(
        portfolio_id=item.portfolio_id,
        portfolio_subject_id=item.portfolio_subject_id,
        entry_id=item.entry_id,
        candidate_id=item.candidate_id,
        candidate_evaluation_id=item.current_evaluation_id,
        requesting_actor=actor,
        requested_purpose="teacher_candidate_evidence_preview",
        observed_state_revision=detail.observed_state_revision,
    )


def _render_structured(
    output: TextIO,
    preview: CandidateEvidenceStructuredPreview,
) -> None:
    _write(
        output,
        "Evidence Preview",
        "",
        preview.title,
        preview.evidence_kind,
        "",
    )
    if preview.fields:
        for field in preview.fields:
            _write(output, f"{field.label}: {field.value}")
    else:
        _write(
            output,
            "No additional instructional summary fields are represented by this source.",
        )
    _write(
        output,
        "",
        "This preview is read-only. Nothing was selected or placed in the Portfolio.",
    )


def _failure_message(error: CandidateEvidencePreviewError) -> str:
    if error.code == "candidate_evidence_preview.authorization_denied":
        return "Evidence preview was not authorized."
    if error.code == "candidate_evidence_preview.authorization_unresolved":
        return "Evidence preview authorization could not be established."
    if error.code in {
        "candidate_evidence_preview.source_unavailable",
        "candidate_evidence_preview.artifact_source_unavailable",
        "candidate_evidence_preview.artifact_contract_unavailable",
    }:
        return "The exact evidence source is not currently available for preview."
    if error.code in {
        "candidate_evidence_preview.source_drift",
        "candidate_evidence_preview.source_integrity_failed",
        "candidate_evidence_preview.artifact_source_integrity_failed",
        "candidate_evidence_preview.canonical_source_mismatch",
    }:
        return "The exact evidence source no longer matches its persisted provenance."
    if error.code == "candidate_evidence_preview.state_conflict":
        return "Candidate state changed while the preview was being prepared."
    if error.code == "candidate_evidence_preview.artifact_not_supported":
        return "This evidence has no supported byte-bearing preview."
    return "Evidence preview could not be prepared safely."


def _launch_artifact(
    *,
    output: TextIO,
    input_fn: InputFunction,
    artifact: CandidateEvidenceArtifactPreview,
    launcher: CandidateEvidencePreviewLauncher,
) -> None:
    suffix = _MEDIA_SUFFIXES.get(artifact.media_type)
    if suffix is None:
        _write(
            output,
            "Evidence Preview",
            "",
            "The evidence was authorized and verified, but this media type has no",
            "configured local preview viewer.",
        )
        input_fn("Press Enter to return...")
        return

    with TemporaryDirectory(prefix="pds-vitrine-preview-") as temp_root:
        path = Path(temp_root) / f"candidate-evidence{suffix}"
        path.write_bytes(artifact.content)
        try:
            opened = launcher(path)
        except Exception:
            opened = False
        if not opened:
            _write(
                output,
                "Evidence Preview",
                "",
                "The evidence was authorized and verified, but the local viewer",
                "could not be opened.",
            )
            input_fn("Press Enter to return...")
            return
        _write(
            output,
            "Evidence Preview",
            "",
            "The exact authorized evidence opened in your local viewer.",
            "Close the preview when you are finished reviewing it.",
            "",
            "Nothing was selected or placed in the Portfolio.",
        )
        input_fn("Press Enter after closing the preview to return...")


def run_candidate_evidence_preview(
    *,
    workspace_root: str | Path,
    detail: CandidateInboxDetail,
    dependencies: VitrineWorkflowDependencies,
    input_fn: InputFunction,
    output: TextIO,
    clear_fn: ClearFunction,
    actor: ActorAttribution | None = None,
    launcher: CandidateEvidencePreviewLauncher = _default_launcher,
) -> None:
    """Explicitly prepare and display one exact Candidate evidence preview."""

    preview_actor = _preview_actor(actor, input_fn)
    if preview_actor is None:
        return

    clear_fn()
    _write(
        output,
        "Preparing evidence preview...",
        "The exact persisted source will be revalidated before anything is shown.",
    )
    try:
        context = prepare_candidate_evidence_preview_context(
            workspace_root,
            _request(detail, preview_actor),
            adapter_registry=dependencies.adapter_registry,
            source_read_authorization_gate=cast(
                SharedSourceReadAuthorizationGate,
                dependencies.source_read_authorization_gate,
            ),
        )
        result = context.result
        clear_fn()
        if result.preview_kind == "structured_summary":
            assert result.structured_preview is not None
            _render_structured(output, result.structured_preview)
            input_fn("Press Enter to return...")
            return
        if result.preview_kind == "preview_unavailable":
            _write(
                output,
                "Evidence Preview",
                "",
                result.unavailable_reason
                or "This exact evidence has no supported preview representation.",
            )
            input_fn("Press Enter to return...")
            return

        artifact = acquire_candidate_evidence_artifact_preview(
            workspace_root,
            context,
            authorization_gate=(
                dependencies.candidate_evidence_preview_authorization_gate
            ),
        )
        _launch_artifact(
            output=output,
            input_fn=input_fn,
            artifact=artifact,
            launcher=launcher,
        )
    except CandidateEvidencePreviewError as error:
        clear_fn()
        _write(
            output,
            "Evidence Preview",
            "",
            _failure_message(error),
            "",
            "No Selection, Placement, or preview state was created.",
        )
        input_fn("Press Enter to return...")


__all__ = [
    "CandidateEvidencePreviewLauncher",
    "run_candidate_evidence_preview",
]
