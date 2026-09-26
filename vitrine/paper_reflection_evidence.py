"""Capture immutable paper-Reflection evidence from Core-retained scans."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path, PurePosixPath

from pds_core.routes import class_dir, class_module_dir, module_work_dir
from pds_core.routing_models import RouteResolution
from pds_core.scan_retention import RetainedSourceScan
from pds_core.scan_routes import (
    build_retained_source_filename,
    retained_source_scan_path,
)

from vitrine.constants import VITRINE_MODULE_ID
from vitrine.models import (
    ReflectionPromptIssuance,
    ReflectionResponsePage,
    ReflectionReturnedPaperEvidence,
)
from vitrine.paper_reflection_routes import build_reflection_response_page_route
from vitrine.pds_module import (
    VitrineRegistrationValidationError,
    validate_vitrine_registration,
)
from vitrine.storage import (
    VitrineStorageConflictError,
    VitrineStorageError,
    commit_record_batch,
    load_current_records_with_state,
)

_IMAGE_EXTENSIONS = frozenset({".jpeg", ".jpg", ".png", ".tif", ".tiff"})


class PaperReflectionEvidenceError(RuntimeError):
    """Base error for returned-paper evidence capture."""


class PaperReflectionEvidenceContextError(PaperReflectionEvidenceError):
    """Raised when route/canonical Vitrine context is contradictory."""


class PaperReflectionRetainedSourceError(PaperReflectionEvidenceError):
    """Raised when Core retained-source provenance or bytes are invalid."""


class PaperReflectionEvidencePersistenceError(PaperReflectionEvidenceError):
    """Raised when immutable returned-paper evidence cannot be persisted."""


def capture_returned_paper_evidence(
    resolution: RouteResolution,
    retained_source: RetainedSourceScan,
    source_page_number: int,
    /,
) -> ReflectionReturnedPaperEvidence:
    """Capture one exact routed retained page as immutable Vitrine evidence.

    Routing identity establishes where the page belongs; it does not establish
    student authorship. No PortfolioReflection is created by this operation.
    """

    workspace_root = _resolution_workspace_root(resolution)
    _validate_source_page_number(source_page_number)
    retained = _validate_retained_source(
        workspace_root,
        retained_source,
        source_page_number,
    )

    try:
        current, records = load_current_records_with_state(workspace_root)
    except VitrineStorageError as error:
        raise PaperReflectionEvidenceContextError(
            "Canonical Vitrine state is unavailable for returned-paper capture."
        ) from error

    page = _exact_page(records, resolution.registration.target.record_id)
    issuance = _exact_issuance(records, page.issuance_id)
    expected_route = build_reflection_response_page_route(issuance, page)
    if (
        resolution.locator != expected_route.locator
        or resolution.registration != expected_route.registration
    ):
        raise PaperReflectionEvidenceContextError(
            "Resolved Core route contradicts immutable Vitrine issuance/page context."
        )

    evidence = _evidence_record(
        issuance,
        page,
        retained,
        source_page_number,
    )
    existing = _existing_evidence(records, evidence)
    if existing is not None:
        return existing

    try:
        commit_record_batch(
            workspace_root,
            (evidence,),
            expected_state_revision=current.state_revision,
        )
    except VitrineStorageConflictError as error:
        try:
            _latest, latest_records = load_current_records_with_state(workspace_root)
        except VitrineStorageError as reload_error:
            raise PaperReflectionEvidencePersistenceError(
                "Vitrine state changed and returned-paper evidence could not be rechecked."
            ) from reload_error
        replay = _existing_evidence(latest_records, evidence)
        if replay is not None:
            return replay
        raise PaperReflectionEvidencePersistenceError(
            "Vitrine state changed before returned-paper evidence was persisted."
        ) from error
    except VitrineStorageError as error:
        raise PaperReflectionEvidencePersistenceError(
            "Returned-paper evidence could not be persisted safely."
        ) from error

    return evidence


def _resolution_workspace_root(resolution: object) -> Path:
    if not isinstance(resolution, RouteResolution):
        raise PaperReflectionEvidenceContextError(
            "resolution must be a RouteResolution."
        )
    try:
        validate_vitrine_registration(resolution.registration)
        workspace_root = resolution.class_root.parent.parent
        absolute_root = Path(os.path.abspath(workspace_root))
        if workspace_root != absolute_root:
            raise ValueError("resolution workspace root must be absolute and canonical.")
        expected_class = class_dir(
            workspace_root,
            resolution.locator.class_id,
        )
        expected_module = class_module_dir(
            workspace_root,
            resolution.locator.class_id,
            VITRINE_MODULE_ID,
        )
        expected_work = module_work_dir(
            workspace_root,
            resolution.locator.work,
        )
        if (
            resolution.class_root != expected_class
            or resolution.module_root != expected_module
            or resolution.work_root != expected_work
        ):
            raise ValueError("resolution roots are not canonical Core roots.")
        return workspace_root
    except VitrineRegistrationValidationError as error:
        raise PaperReflectionEvidenceContextError(
            "Resolved Vitrine registration is invalid."
        ) from error
    except (ValueError, TypeError, AttributeError, OSError) as error:
        raise PaperReflectionEvidenceContextError(
            f"Invalid Vitrine route resolution context: {error}"
        ) from error


def _validate_source_page_number(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise PaperReflectionRetainedSourceError(
            "source_page_number must be a positive non-Boolean integer."
        )
    return value


def _validate_retained_source(
    workspace_root: Path,
    retained_source: object,
    source_page_number: int,
) -> RetainedSourceScan:
    if not isinstance(retained_source, RetainedSourceScan):
        raise PaperReflectionRetainedSourceError(
            "retained_source must be a RetainedSourceScan."
        )
    retained_path = retained_source.retained_source_path
    try:
        if not isinstance(retained_path, Path) or not retained_path.is_absolute():
            raise ValueError("retained_source_path must be an absolute Path.")
        absolute_path = Path(os.path.abspath(retained_path))
        if retained_path != absolute_path:
            raise ValueError("retained_source_path must be absolute and canonical.")
        if retained_path.resolve(strict=True) != retained_path:
            raise ValueError(
                "retained_source_path must not traverse a symlink or junction."
            )
        if not retained_path.is_file():
            raise ValueError("retained source must be an ordinary file.")
        if not os.access(retained_path, os.R_OK):
            raise ValueError("retained source must be readable.")

        timestamp = retained_source.intake_timestamp
        if not isinstance(timestamp, datetime):
            raise ValueError("intake_timestamp must be a datetime.")
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("intake_timestamp must be timezone-aware.")
        expected_filename = build_retained_source_filename(
            intake_timestamp=timestamp,
            original_filename=retained_source.source_filename,
            sha256_hex=retained_source.source_sha256,
        )
        expected_path = retained_source_scan_path(
            workspace_root,
            intake_date=retained_source.intake_date,
            retained_filename=expected_filename,
        )
        if retained_path != expected_path:
            raise ValueError(
                "retained_source_path does not match Core retention provenance."
            )
        expected_relative = expected_path.relative_to(workspace_root).as_posix()
        if retained_source.retained_source_relative_path != expected_relative:
            raise ValueError(
                "retained_source_relative_path does not match the Core path."
            )
        relative = PurePosixPath(retained_source.retained_source_relative_path)
        if relative.parts[:2] != ("scans", "source") or len(relative.parts) != 4:
            raise ValueError("retained source relative path has the wrong shape.")
        expected_scan_id = f"scan_{expected_path.stem}"
        if retained_source.source_scan_id != expected_scan_id:
            raise ValueError("source_scan_id contradicts Core retention provenance.")

        suffix = retained_path.suffix.lower()
        if suffix in _IMAGE_EXTENSIONS and source_page_number != 1:
            raise ValueError("image retained sources contain only source page 1.")
        if suffix != ".pdf" and suffix not in _IMAGE_EXTENSIONS:
            raise ValueError("retained source extension is unsupported.")

        actual_digest = _sha256_file(retained_path)
        if actual_digest != retained_source.source_sha256:
            raise ValueError(
                "retained source bytes no longer match the recorded SHA-256."
            )
    except PaperReflectionRetainedSourceError:
        raise
    except (ValueError, TypeError, AttributeError, OSError) as error:
        raise PaperReflectionRetainedSourceError(
            f"Invalid Core retained-source provenance: {error}"
        ) from error
    return retained_source


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _exact_page(
    records: tuple[object, ...],
    response_page_id: str,
) -> ReflectionResponsePage:
    matches = tuple(
        item
        for item in records
        if isinstance(item, ReflectionResponsePage)
        and item.response_page_id == response_page_id
    )
    if len(matches) != 1:
        raise PaperReflectionEvidenceContextError(
            "Registered Reflection response page is missing or ambiguous."
        )
    return matches[0]


def _exact_issuance(
    records: tuple[object, ...],
    issuance_id: str,
) -> ReflectionPromptIssuance:
    matches = tuple(
        item
        for item in records
        if isinstance(item, ReflectionPromptIssuance)
        and item.issuance_id == issuance_id
    )
    if len(matches) != 1:
        raise PaperReflectionEvidenceContextError(
            "Response page issuance is missing or ambiguous."
        )
    return matches[0]


def _evidence_record(
    issuance: ReflectionPromptIssuance,
    page: ReflectionResponsePage,
    retained_source: RetainedSourceScan,
    source_page_number: int,
) -> ReflectionReturnedPaperEvidence:
    replay_key = "\x1f".join(
        (
            page.route_id,
            page.response_page_id,
            retained_source.source_scan_id,
            str(source_page_number),
            retained_source.source_sha256,
        )
    )
    evidence_id = "paper_evidence_" + hashlib.sha256(
        replay_key.encode("utf-8")
    ).hexdigest()[:32]
    return ReflectionReturnedPaperEvidence(
        returned_paper_evidence_id=evidence_id,
        issuance_id=issuance.issuance_id,
        response_page_id=page.response_page_id,
        route_id=page.route_id,
        class_id=page.class_id,
        work_id=page.work_id,
        source_scan_id=retained_source.source_scan_id,
        source_filename=retained_source.source_filename,
        source_page_number=source_page_number,
        retained_source_relative_path=(
            retained_source.retained_source_relative_path
        ),
        source_sha256=retained_source.source_sha256,
        intake_timestamp=retained_source.intake_timestamp,
        intake_date=retained_source.intake_date,
    )


def _existing_evidence(
    records: tuple[object, ...],
    expected: ReflectionReturnedPaperEvidence,
) -> ReflectionReturnedPaperEvidence | None:
    matches = tuple(
        item
        for item in records
        if isinstance(item, ReflectionReturnedPaperEvidence)
        and item.returned_paper_evidence_id
        == expected.returned_paper_evidence_id
    )
    if not matches:
        return None
    if len(matches) != 1 or matches[0] != expected:
        raise PaperReflectionEvidencePersistenceError(
            "Existing returned-paper evidence contradicts exact replay identity."
        )
    return matches[0]


__all__ = [
    "PaperReflectionEvidenceContextError",
    "PaperReflectionEvidenceError",
    "PaperReflectionEvidencePersistenceError",
    "PaperReflectionRetainedSourceError",
    "capture_returned_paper_evidence",
]
