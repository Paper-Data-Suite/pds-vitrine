"""Exact read-only review projection for returned paper Reflection evidence."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final

from pds_core.workspace import resolve_workspace_root

from vitrine.models import (
    ClassQualifiedStudentRef,
    CurationTargetRef,
    Portfolio,
    PortfolioCandidate,
    PortfolioSelection,
    ReflectionPromptIssuance,
    ReflectionResponsePage,
    ReflectionReturnedPaperEvidence,
)
from vitrine.storage import (
    VitrineStorageError,
    VitrineStorageNotFoundError,
    load_current_records_with_state,
)

PAPER_REFLECTION_REVIEW_CONTRACT_VERSION: Final[str] = (
    "vitrine_paper_reflection_review_v1"
)
_MEDIA_TYPE_BY_SUFFIX: Final[dict[str, str]] = {
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


class PaperReflectionReviewError(RuntimeError):
    """Exact returned-paper review context cannot be established safely."""


@dataclass(frozen=True, slots=True)
class PaperReflectionReviewTarget:
    target_reference: CurationTargetRef
    display_label: str


@dataclass(frozen=True, slots=True)
class PaperReflectionReviewOccurrence:
    returned_paper_evidence_id: str
    response_page_id: str
    logical_page_number: int
    total_pages: int
    source_scan_id: str
    source_filename: str
    source_page_number: int
    retained_source_relative_path: str
    source_sha256: str
    intake_timestamp: str
    media_type: str


@dataclass(frozen=True, slots=True)
class PaperReflectionReviewPage:
    response_page_id: str
    logical_page_number: int
    total_pages: int
    route_id: str
    occurrences: tuple[PaperReflectionReviewOccurrence, ...]


@dataclass(frozen=True, slots=True)
class PaperReflectionReviewContext:
    contract_version: str
    workspace_root: Path
    observed_state_revision: int
    portfolio_id: str
    portfolio_subject_id: str
    issuance_id: str
    reflection_requirement_id: str
    prompt_id: str
    prompt_version: str
    prompt_snapshot: str
    subject_link_id: str
    student_reference: ClassQualifiedStudentRef
    targets: tuple[PaperReflectionReviewTarget, ...]
    pages: tuple[PaperReflectionReviewPage, ...]

    def __post_init__(self) -> None:
        if self.contract_version != PAPER_REFLECTION_REVIEW_CONTRACT_VERSION:
            raise ValueError("unexpected paper Reflection review contract")
        if self.observed_state_revision <= 0:
            raise ValueError("observed_state_revision must be positive")
        if not self.pages:
            raise ValueError("paper Reflection review requires response pages")


@dataclass(frozen=True, slots=True)
class PaperReflectionEvidencePreview:
    occurrence: PaperReflectionReviewOccurrence
    content: bytes
    suffix: str


def prepare_paper_reflection_review_context(
    workspace_root: str | Path,
    *,
    portfolio_id: str,
    issuance_id: str,
    expected_state_revision: int,
) -> PaperReflectionReviewContext:
    """Resolve one complete returned issuance without choosing among rescans."""

    root = resolve_workspace_root(workspace_root)
    try:
        current, records = load_current_records_with_state(root)
    except (VitrineStorageNotFoundError, VitrineStorageError) as error:
        raise PaperReflectionReviewError(
            "Canonical Vitrine state is unavailable for returned-paper review."
        ) from error
    if current.state_revision != expected_state_revision:
        raise PaperReflectionReviewError(
            "Vitrine state changed after Student Reflection status was observed."
        )

    portfolios = tuple(
        item
        for item in records
        if isinstance(item, Portfolio) and item.portfolio_id == portfolio_id
    )
    if len(portfolios) != 1:
        raise PaperReflectionReviewError(
            "Exact Portfolio is missing or ambiguous during returned-paper review."
        )
    portfolio = portfolios[0]

    issuances = tuple(
        item
        for item in records
        if isinstance(item, ReflectionPromptIssuance)
        and item.issuance_id == issuance_id
        and item.portfolio_id == portfolio_id
        and item.portfolio_subject_id == portfolio.portfolio_subject_id
    )
    if len(issuances) != 1:
        raise PaperReflectionReviewError(
            "Exact Reflection issuance is missing or ambiguous."
        )
    issuance = issuances[0]

    page_records = tuple(
        item
        for item in records
        if isinstance(item, ReflectionResponsePage)
        and item.issuance_id == issuance.issuance_id
    )
    page_by_id = {item.response_page_id: item for item in page_records}
    if (
        len(page_by_id) != len(issuance.response_page_ids)
        or set(page_by_id) != set(issuance.response_page_ids)
    ):
        raise PaperReflectionReviewError(
            "Issued response-page records are incomplete or contradictory."
        )

    evidence_records = tuple(
        item
        for item in records
        if isinstance(item, ReflectionReturnedPaperEvidence)
        and item.issuance_id == issuance.issuance_id
    )
    pages: list[PaperReflectionReviewPage] = []
    for response_page_id in issuance.response_page_ids:
        page = page_by_id[response_page_id]
        occurrences = tuple(
            sorted(
                (
                    _occurrence(page, evidence)
                    for evidence in evidence_records
                    if evidence.response_page_id == response_page_id
                    and evidence.route_id == page.route_id
                    and evidence.class_id == page.class_id
                    and evidence.work_id == page.work_id
                ),
                key=lambda item: (
                    item.intake_timestamp,
                    item.returned_paper_evidence_id,
                ),
            )
        )
        if not occurrences:
            raise PaperReflectionReviewError(
                "Returned-paper review requires at least one routed occurrence "
                "for every issued response page."
            )
        pages.append(
            PaperReflectionReviewPage(
                response_page_id=page.response_page_id,
                logical_page_number=page.logical_page_number,
                total_pages=page.total_pages,
                route_id=page.route_id,
                occurrences=occurrences,
            )
        )

    ordered = tuple(sorted(pages, key=lambda item: item.logical_page_number))
    expected_numbers = tuple(range(1, len(ordered) + 1))
    if tuple(item.logical_page_number for item in ordered) != expected_numbers:
        raise PaperReflectionReviewError(
            "Response-page logical ordering is incomplete or contradictory."
        )
    if any(item.total_pages != len(ordered) for item in ordered):
        raise PaperReflectionReviewError(
            "Response-page total-page metadata is contradictory."
        )

    return PaperReflectionReviewContext(
        contract_version=PAPER_REFLECTION_REVIEW_CONTRACT_VERSION,
        workspace_root=root,
        observed_state_revision=current.state_revision,
        portfolio_id=portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        issuance_id=issuance.issuance_id,
        reflection_requirement_id=issuance.reflection_requirement_id,
        prompt_id=issuance.prompt_id,
        prompt_version=issuance.prompt_version,
        prompt_snapshot=issuance.prompt_snapshot,
        subject_link_id=issuance.subject_link_id,
        student_reference=issuance.student_reference,
        targets=tuple(
            PaperReflectionReviewTarget(
                target_reference=target,
                display_label=_target_label(records, target),
            )
            for target in issuance.target_references
        ),
        pages=ordered,
    )


def acquire_paper_reflection_evidence_preview(
    context: PaperReflectionReviewContext,
    returned_paper_evidence_id: str,
) -> PaperReflectionEvidencePreview:
    """Read and digest-verify one exact Core-retained occurrence for preview."""

    occurrence = next(
        (
            item
            for page in context.pages
            for item in page.occurrences
            if item.returned_paper_evidence_id == returned_paper_evidence_id
        ),
        None,
    )
    if occurrence is None:
        raise PaperReflectionReviewError(
            "Selected returned-paper occurrence is outside this review context."
        )

    relative = PurePosixPath(occurrence.retained_source_relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise PaperReflectionReviewError(
            "Returned-paper retained source path is not safely workspace-relative."
        )
    source = context.workspace_root.joinpath(*relative.parts)
    absolute = Path(os.path.abspath(source))
    if source != absolute:
        raise PaperReflectionReviewError(
            "Returned-paper retained source path is not canonical."
        )
    try:
        resolved = source.resolve(strict=True)
    except OSError as error:
        raise PaperReflectionReviewError(
            "Returned-paper retained source is unavailable."
        ) from error
    if resolved != source or source.is_symlink() or not source.is_file():
        raise PaperReflectionReviewError(
            "Returned-paper retained source is not an ordinary canonical file."
        )
    try:
        content = source.read_bytes()
    except OSError as error:
        raise PaperReflectionReviewError(
            "Returned-paper retained source cannot be read."
        ) from error
    if hashlib.sha256(content).hexdigest() != occurrence.source_sha256:
        raise PaperReflectionReviewError(
            "Returned-paper retained source no longer matches its canonical digest."
        )
    suffix = relative.suffix.lower()
    if _MEDIA_TYPE_BY_SUFFIX.get(suffix) != occurrence.media_type:
        raise PaperReflectionReviewError(
            "Returned-paper media type no longer matches its retained source."
        )
    return PaperReflectionEvidencePreview(
        occurrence=occurrence,
        content=content,
        suffix=suffix,
    )


def selected_occurrence_ids(
    context: PaperReflectionReviewContext,
    selected: tuple[str, ...],
) -> tuple[str, ...]:
    """Validate one exact occurrence per page and return persisted page order."""

    if len(selected) != len(context.pages):
        raise PaperReflectionReviewError(
            "Returned-paper selection must choose one occurrence for every page."
        )
    result: list[str] = []
    for page, evidence_id in zip(context.pages, selected, strict=True):
        if not any(
            item.returned_paper_evidence_id == evidence_id
            for item in page.occurrences
        ):
            raise PaperReflectionReviewError(
                "Returned-paper occurrence does not belong to its selected page."
            )
        result.append(evidence_id)
    return tuple(result)


def _occurrence(
    page: ReflectionResponsePage,
    evidence: ReflectionReturnedPaperEvidence,
) -> PaperReflectionReviewOccurrence:
    suffix = PurePosixPath(evidence.retained_source_relative_path).suffix.lower()
    media_type = _MEDIA_TYPE_BY_SUFFIX.get(suffix)
    if media_type is None:
        raise PaperReflectionReviewError(
            "Returned-paper evidence has an unsupported preview media type."
        )
    return PaperReflectionReviewOccurrence(
        returned_paper_evidence_id=evidence.returned_paper_evidence_id,
        response_page_id=evidence.response_page_id,
        logical_page_number=page.logical_page_number,
        total_pages=page.total_pages,
        source_scan_id=evidence.source_scan_id,
        source_filename=evidence.source_filename,
        source_page_number=evidence.source_page_number,
        retained_source_relative_path=evidence.retained_source_relative_path,
        source_sha256=evidence.source_sha256,
        intake_timestamp=evidence.intake_timestamp.isoformat(),
        media_type=media_type,
    )


def _target_label(
    records: tuple[object, ...],
    target: CurationTargetRef,
) -> str:
    if target.target_kind == "selection":
        selections = tuple(
            item
            for item in records
            if isinstance(item, PortfolioSelection)
            and item.selection_id == target.target_id
        )
        if len(selections) == 1:
            candidates = tuple(
                item
                for item in records
                if isinstance(item, PortfolioCandidate)
                and item.candidate_id == selections[0].candidate_id
            )
            if len(candidates) == 1:
                return candidates[0].display_snapshot
        return "Selected Portfolio evidence"
    if target.target_kind == "portfolio":
        return "Portfolio"
    if target.semantic_role is not None:
        return target.semantic_role.replace("_", " ").strip().title()
    return target.target_kind.replace("_", " ").strip().title()


__all__ = [
    "PAPER_REFLECTION_REVIEW_CONTRACT_VERSION",
    "PaperReflectionEvidencePreview",
    "PaperReflectionReviewContext",
    "PaperReflectionReviewError",
    "PaperReflectionReviewOccurrence",
    "PaperReflectionReviewPage",
    "PaperReflectionReviewTarget",
    "acquire_paper_reflection_evidence_preview",
    "prepare_paper_reflection_review_context",
    "selected_occurrence_ids",
]
