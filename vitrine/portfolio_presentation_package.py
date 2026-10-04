"""Create-only human-readable file packages for student Portfolio presentations."""

from __future__ import annotations

import hashlib
import json
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from vitrine.models.common import require_identifier
from vitrine.models.errors import VitrineModelValidationError
from vitrine.path_policy import (
    PRESENTATION_DIRECTORY_MAX_LENGTH,
    PRESENTATION_FILENAME_MAX_LENGTH,
    VitrinePathPolicyError,
    require_generated_component,
    require_unique_presentation_components,
)
from vitrine.portfolio_presentation import (
    PORTFOLIO_PRESENTATION_CUSTODY_NAMESPACE,
    STUDENT_PORTFOLIO_PRESENTATION_CLASS,
    PortfolioPresentationPreparationError,
    StudentPortfolioPresentationItem,
    StudentPortfolioPresentationPreparation,
    presentation_artifact_custody_relative_path,
)
from vitrine.portfolio_presentation_html import (
    STUDENT_PORTFOLIO_HTML_FILENAME,
    PortfolioPresentationHtmlError,
    StudentPortfolioHtmlRenderResult,
    render_student_portfolio_html,
)
from vitrine.snapshot_custody import (
    SnapshotCustodyError,
    snapshot_export_path_from_relative,
)
from vitrine.snapshot_distribution import (
    SnapshotDistributionError,
    SnapshotExportVerification,
    verify_snapshot_export,
)
from vitrine.storage.errors import VitrineStorageValidationError
from vitrine.storage.paths import safe_vitrine_descendant

STUDENT_PORTFOLIO_FILE_PACKAGE_CONTRACT_VERSION: Final[str] = (
    "vitrine_student_portfolio_file_package_v1"
)
PRESENTATION_MANIFEST_FILENAME: Final[str] = "portfolio-presentation-manifest.json"
_PRESENTATION_FILE_INVENTORY_CONTRACT_VERSION: Final[str] = (
    "vitrine_student_portfolio_file_inventory_v1"
)
_INLINE_TEXT_MEDIA_TYPES: Final[frozenset[str]] = frozenset(
    {"text/markdown", "text/plain"}
)

PORTFOLIO_PRESENTATION_PACKAGE_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "portfolio_presentation_package.invalid_request",
        "portfolio_presentation_package.preparation_invalid",
        "portfolio_presentation_package.verification_failed",
        "portfolio_presentation_package.custody_conflict",
        "portfolio_presentation_package.source_mismatch",
        "portfolio_presentation_package.render_failed",
        "portfolio_presentation_package.write_failed",
        "portfolio_presentation_package.durability_uncertain",
    }
)


class PortfolioPresentationPackageError(RuntimeError):
    """Expected student Portfolio package failure with stable machine metadata."""

    def __init__(self, code: str, message: str, *, stage: str) -> None:
        if code not in PORTFOLIO_PRESENTATION_PACKAGE_ERROR_CODES:
            raise ValueError(f"unsupported Portfolio presentation package code: {code}")
        super().__init__(message)
        self.code = code
        self.stage = stage


@dataclass(frozen=True, slots=True)
class StudentPortfolioFilePackageResult:
    presentation_artifact_id: str
    relative_path: str
    manifest_relative_path: str
    manifest_sha256: str
    html_relative_path: str
    html_sha256: str
    package_inventory_sha256: str
    copied_file_paths: tuple[str, ...]
    reference_only_count: int
    omitted_count: int
    preparation_fingerprint: str


@dataclass(frozen=True, slots=True)
class _CopiedFile:
    relative_path: str
    byte_size: int
    sha256: str


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _is_plain(path: Path) -> bool:
    try:
        if path.is_symlink():
            return False
        attrs_raw = getattr(path.lstat(), "st_file_attributes", 0)
        attrs = attrs_raw if isinstance(attrs_raw, int) else 0
        flag_raw = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        flag = flag_raw if isinstance(flag_raw, int) else 0
        return not bool(flag and attrs & flag)
    except OSError:
        return False


def _read_verified_export_file(export_root: Path, relative_path: str) -> bytes:
    parts = relative_path.split("/")
    if (
        not relative_path
        or "\\" in relative_path
        or ":" in relative_path
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.source_mismatch",
            "Verified Export inventory exposed an unsafe relative file path.",
            stage="copy",
        )
    current = export_root
    if not current.exists() or not current.is_dir() or not _is_plain(current):
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.source_mismatch",
            "Verified technical Export custody is unavailable or unsafe.",
            stage="copy",
        )
    for component in parts[:-1]:
        current = current / component
        if not current.exists() or not current.is_dir() or not _is_plain(current):
            raise PortfolioPresentationPackageError(
                "portfolio_presentation_package.source_mismatch",
                "Verified technical Export contains an unsafe directory path.",
                stage="copy",
            )
    source = current / parts[-1]
    if not source.exists() or not source.is_file() or not _is_plain(source):
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.source_mismatch",
            "Verified technical Export source file is missing or unsafe.",
            stage="copy",
        )
    try:
        return source.read_bytes()
    except OSError as error:
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.source_mismatch",
            "Verified technical Export source file could not be read.",
            stage="copy",
        ) from error


def _item_manifest_value(
    item: StudentPortfolioPresentationItem,
    *,
    presentation_relative_path: str | None,
) -> dict[str, object]:
    return {
        "entry_plan_id": item.entry_plan_id,
        "plan_position": item.plan_position,
        "section_id": item.section_id,
        "ordinal": item.ordinal,
        "semantic_role": item.semantic_role,
        "content_class": item.content_class,
        "materialization_kind": item.materialization_kind,
        "disposition": item.disposition,
        "display_title": item.display_title,
        "display_caption": item.display_caption,
        "source_credit": item.source_credit,
        "presentation_note": item.presentation_note,
        "candidate_id": item.candidate_id,
        "selection_id": item.selection_id,
        "placement_id": item.placement_id,
        "snapshot_entry_id": item.snapshot_entry_id,
        "materialization_id": item.materialization_id,
        "omission_id": item.omission_id,
        "media_type": item.media_type,
        "presentation_relative_path": presentation_relative_path,
        "byte_size": item.byte_size if presentation_relative_path is not None else None,
        "sha256": item.output_sha256 if presentation_relative_path is not None else None,
    }


def _package_inventory_value(files: tuple[_CopiedFile, ...]) -> dict[str, object]:
    return {
        "contract_version": _PRESENTATION_FILE_INVENTORY_CONTRACT_VERSION,
        "files": [
            {
                "relative_path": item.relative_path,
                "byte_size": item.byte_size,
                "sha256": item.sha256,
            }
            for item in sorted(files, key=lambda item: item.relative_path)
        ],
    }


def _html_manifest_value(
    render: StudentPortfolioHtmlRenderResult,
) -> dict[str, object]:
    return {
        "relative_path": render.filename,
        "byte_size": render.byte_size,
        "sha256": render.sha256,
        "renderer_id": render.renderer_id,
        "renderer_version": render.renderer_version,
        "renderer_contract_version": render.renderer_contract_version,
        "renderer_configuration_sha256": render.renderer_configuration_sha256,
    }


def _manifest_value(
    preparation: StudentPortfolioPresentationPreparation,
    *,
    presentation_artifact_id: str,
    copied_by_entry_plan: dict[str, _CopiedFile],
    html_render: StudentPortfolioHtmlRenderResult,
    package_inventory_sha256: str,
    package_file_count: int,
) -> dict[str, object]:
    sections: list[dict[str, object]] = []
    for section in preparation.sections:
        item_values: list[dict[str, object]] = []
        for item in section.items:
            copied = copied_by_entry_plan.get(item.entry_plan_id)
            item_values.append(
                _item_manifest_value(
                    item,
                    presentation_relative_path=(
                        None if copied is None else copied.relative_path
                    ),
                )
            )
        sections.append(
            {
                "section_id": section.section_id,
                "label": section.label,
                "purpose": section.purpose,
                "order": section.order,
                "obligation": section.obligation,
                "presentation_directory_name": section.presentation_directory_name,
                "items": item_values,
            }
        )
    return {
        "file_package_contract_version": (
            STUDENT_PORTFOLIO_FILE_PACKAGE_CONTRACT_VERSION
        ),
        "presentation_contract_version": preparation.contract_version,
        "presentation_artifact_id": presentation_artifact_id,
        "presentation_class": preparation.presentation_class,
        "portfolio": {
            "portfolio_id": preparation.portfolio_id,
            "portfolio_subject_id": preparation.portfolio_subject_id,
            "student_display_name": preparation.student_display_name,
            "title": preparation.portfolio_title,
            "profile_label": preparation.profile_label,
        },
        "profile": {
            "profile_binding_id": preparation.profile_binding_id,
            "portfolio_profile_id": preparation.profile_revision.portfolio_profile_id,
            "profile_revision": preparation.profile_revision.profile_revision,
            "composition_revision": preparation.composition_revision,
        },
        "audience": {
            "audience_context_id": preparation.audience_context_id,
            "audience_presentation_class": preparation.audience_presentation_class,
            "purpose": preparation.purpose,
        },
        "snapshot": {
            "snapshot_series_id": preparation.snapshot_edition.snapshot_series_id,
            "edition_number": preparation.snapshot_edition.edition_number,
            "manifest_sha256": preparation.snapshot_manifest_sha256,
            "logical_inventory_sha256": (
                preparation.snapshot_logical_inventory_sha256
            ),
        },
        "technical_export": {
            "snapshot_export_artifact_id": preparation.snapshot_export_artifact_id,
            "directory_inventory_sha256": (
                preparation.technical_export_inventory_sha256
            ),
        },
        "package_inventory": {
            "contract_version": _PRESENTATION_FILE_INVENTORY_CONTRACT_VERSION,
            "sha256": package_inventory_sha256,
            "file_count": package_file_count,
        },
        "sections": sections,
        "generated_outputs": {
            "html": _html_manifest_value(html_render),
            "printable_pdf": None,
        },
        "preparation_fingerprint": preparation.preparation_fingerprint,
    }


def _validate_preparation(
    preparation: StudentPortfolioPresentationPreparation,
) -> None:
    if not isinstance(preparation, StudentPortfolioPresentationPreparation):
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.preparation_invalid",
            "Student Portfolio file package requires exact presentation preparation.",
            stage="request",
        )
    if preparation.presentation_class != STUDENT_PORTFOLIO_PRESENTATION_CLASS:
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.preparation_invalid",
            "Prepared presentation is not a student_portfolio output.",
            stage="request",
        )
    digest_fields = (
        preparation.snapshot_manifest_sha256,
        preparation.snapshot_logical_inventory_sha256,
        preparation.technical_export_inventory_sha256,
        preparation.preparation_fingerprint,
    )
    if any(
        len(value) != 64 or any(char not in "0123456789abcdef" for char in value)
        for value in digest_fields
    ):
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.preparation_invalid",
            "Prepared presentation contains an invalid SHA-256 binding.",
            stage="request",
        )


def _verify_exact_export(
    root: str | Path,
    preparation: StudentPortfolioPresentationPreparation,
) -> SnapshotExportVerification:
    try:
        verification = verify_snapshot_export(
            root,
            snapshot_export_artifact_id=preparation.snapshot_export_artifact_id,
        )
    except SnapshotDistributionError as error:
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.verification_failed",
            "The exact technical Snapshot Export no longer verifies.",
            stage="verification",
        ) from error
    if (
        verification.snapshot_series_id
        != preparation.snapshot_edition.snapshot_series_id
        or verification.edition_number != preparation.snapshot_edition.edition_number
        or verification.directory_inventory_digest.value
        != preparation.technical_export_inventory_sha256
    ):
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.verification_failed",
            "Verified Snapshot Export does not match the prepared Portfolio history.",
            stage="verification",
        )
    return verification


def _rollback_partial(path: Path) -> None:
    try:
        shutil.rmtree(path)
    except OSError as error:
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.durability_uncertain",
            "A failed presentation package could not be removed completely.",
            stage="rollback",
        ) from error


def _validate_root_components(
    preparation: StudentPortfolioPresentationPreparation,
) -> None:
    try:
        require_generated_component(
            PRESENTATION_MANIFEST_FILENAME,
            maximum=PRESENTATION_FILENAME_MAX_LENGTH,
            field_name="presentation_manifest_filename",
        )
        require_generated_component(
            STUDENT_PORTFOLIO_HTML_FILENAME,
            maximum=PRESENTATION_FILENAME_MAX_LENGTH,
            field_name="student_portfolio_html_filename",
        )
        root_components = (
            PRESENTATION_MANIFEST_FILENAME,
            STUDENT_PORTFOLIO_HTML_FILENAME,
            *(section.presentation_directory_name for section in preparation.sections),
        )
        require_unique_presentation_components(tuple(root_components))
        seen_entry_plan_ids: set[str] = set()
        for section in preparation.sections:
            require_generated_component(
                section.presentation_directory_name,
                maximum=PRESENTATION_DIRECTORY_MAX_LENGTH,
                field_name="presentation_section_directory",
            )
            filenames = tuple(
                item.presentation_filename
                for item in section.items
                if item.presentation_filename is not None
            )
            for filename in filenames:
                require_generated_component(
                    filename,
                    maximum=PRESENTATION_FILENAME_MAX_LENGTH,
                    field_name="presentation_item_filename",
                )
            require_unique_presentation_components(filenames)
            for item in section.items:
                if item.entry_plan_id in seen_entry_plan_ids:
                    raise PortfolioPresentationPackageError(
                        "portfolio_presentation_package.preparation_invalid",
                        "Prepared presentation repeats an Entry Plan identity.",
                        stage="custody",
                    )
                seen_entry_plan_ids.add(item.entry_plan_id)
    except VitrinePathPolicyError as error:
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.preparation_invalid",
            "Prepared presentation root components contain a portable collision.",
            stage="custody",
        ) from error


def create_student_portfolio_file_package(
    root: str | Path,
    preparation: StudentPortfolioPresentationPreparation,
    *,
    presentation_artifact_id: str,
) -> StudentPortfolioFilePackageResult:
    """Create one bounded, create-only digital student Portfolio package.

    Slice 3 includes deterministic offline HTML but still does not persist
    PortfolioPresentationArtifact because the canonical record also requires the
    later printable-PDF output.
    """

    _validate_preparation(preparation)
    try:
        artifact_id = require_identifier(
            presentation_artifact_id, "presentation_artifact_id"
        )
    except VitrineModelValidationError as error:
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.invalid_request",
            "Portfolio presentation artifact identity is invalid.",
            stage="request",
        ) from error

    verification = _verify_exact_export(root, preparation)
    verified_paths = set(verification.verified_file_paths)
    try:
        export_root = snapshot_export_path_from_relative(
            root,
            preparation.technical_export_relative_path,
        )
        relative_root = presentation_artifact_custody_relative_path(artifact_id)
        final_root = safe_vitrine_descendant(root, relative_root)
        namespace_root = safe_vitrine_descendant(
            root, PORTFOLIO_PRESENTATION_CUSTODY_NAMESPACE
        )
    except (
        SnapshotCustodyError,
        PortfolioPresentationPreparationError,
        VitrineStorageValidationError,
    ) as error:
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.preparation_invalid",
            "Presentation custody or exact technical Export custody is invalid.",
            stage="custody",
        ) from error

    _validate_root_components(preparation)

    try:
        namespace_root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.write_failed",
            "Presentation custody namespace could not be created.",
            stage="custody",
        ) from error
    if final_root.exists():
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.custody_conflict",
            "Presentation custody already exists; create-only output will not overwrite it.",
            stage="custody",
        )
    try:
        final_root.mkdir(parents=False, exist_ok=False)
    except FileExistsError as error:
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.custody_conflict",
            "Presentation custody already exists; create-only output will not overwrite it.",
            stage="custody",
        ) from error
    except OSError as error:
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.write_failed",
            "Presentation custody could not be created.",
            stage="custody",
        ) from error

    copied: list[_CopiedFile] = []
    copied_by_entry_plan: dict[str, _CopiedFile] = {}
    text_payloads_by_entry_plan: dict[str, bytes] = {}
    try:
        for section in preparation.sections:
            section_root = final_root / section.presentation_directory_name
            section_root.mkdir(parents=False, exist_ok=False)
            for item in section.items:
                if not item.export_file_available:
                    continue
                if (
                    item.technical_relative_path is None
                    or item.presentation_filename is None
                    or item.output_sha256 is None
                    or item.byte_size is None
                ):
                    raise PortfolioPresentationPackageError(
                        "portfolio_presentation_package.preparation_invalid",
                        "Byte-bearing presentation item lacks exact copy metadata.",
                        stage="copy",
                    )
                if item.technical_relative_path not in verified_paths:
                    raise PortfolioPresentationPackageError(
                        "portfolio_presentation_package.source_mismatch",
                        "Prepared source path is absent from the verified technical Export.",
                        stage="copy",
                    )
                payload = _read_verified_export_file(
                    export_root, item.technical_relative_path
                )
                actual_digest = _sha256(payload)
                if actual_digest != item.output_sha256 or len(payload) != item.byte_size:
                    raise PortfolioPresentationPackageError(
                        "portfolio_presentation_package.source_mismatch",
                        "Technical Export bytes differ from the exact frozen "
                        "Snapshot materialization.",
                        stage="copy",
                    )
                target = section_root / item.presentation_filename
                with target.open("xb") as stream:
                    stream.write(payload)
                relative_file = (
                    f"{section.presentation_directory_name}/{item.presentation_filename}"
                )
                copied_file = _CopiedFile(
                    relative_path=relative_file,
                    byte_size=len(payload),
                    sha256=actual_digest,
                )
                copied.append(copied_file)
                copied_by_entry_plan[item.entry_plan_id] = copied_file
                if (
                    item.media_type in _INLINE_TEXT_MEDIA_TYPES
                    and "reflection" in {item.content_class, item.semantic_role}
                ):
                    text_payloads_by_entry_plan[item.entry_plan_id] = payload

        try:
            html_render = render_student_portfolio_html(
                preparation,
                text_payloads_by_entry_plan=text_payloads_by_entry_plan,
            )
        except PortfolioPresentationHtmlError as error:
            raise PortfolioPresentationPackageError(
                "portfolio_presentation_package.render_failed",
                "Student Portfolio HTML could not be rendered from the exact preparation.",
                stage="html",
            ) from error

        html_path = final_root / html_render.filename
        with html_path.open("xb") as stream:
            stream.write(html_render.payload)
        html_file = _CopiedFile(
            relative_path=html_render.filename,
            byte_size=html_render.byte_size,
            sha256=html_render.sha256,
        )

        package_files = (*copied, html_file)
        inventory_value = _package_inventory_value(tuple(package_files))
        inventory_digest = _sha256(_canonical_json_bytes(inventory_value))
        manifest_value = _manifest_value(
            preparation,
            presentation_artifact_id=artifact_id,
            copied_by_entry_plan=copied_by_entry_plan,
            html_render=html_render,
            package_inventory_sha256=inventory_digest,
            package_file_count=len(package_files),
        )
        manifest_payload = _canonical_json_bytes(manifest_value)
        manifest_path = final_root / PRESENTATION_MANIFEST_FILENAME
        with manifest_path.open("xb") as stream:
            stream.write(manifest_payload)
    except PortfolioPresentationPackageError:
        _rollback_partial(final_root)
        raise
    except (OSError, ValueError, TypeError) as error:
        _rollback_partial(final_root)
        raise PortfolioPresentationPackageError(
            "portfolio_presentation_package.write_failed",
            "Student Portfolio file package could not be written safely.",
            stage="write",
        ) from error

    return StudentPortfolioFilePackageResult(
        presentation_artifact_id=artifact_id,
        relative_path=relative_root,
        manifest_relative_path=f"{relative_root}/{PRESENTATION_MANIFEST_FILENAME}",
        manifest_sha256=_sha256(manifest_payload),
        html_relative_path=f"{relative_root}/{html_render.filename}",
        html_sha256=html_render.sha256,
        package_inventory_sha256=inventory_digest,
        copied_file_paths=tuple(
            item.relative_path
            for item in sorted(copied, key=lambda item: item.relative_path)
        ),
        reference_only_count=preparation.reference_only_count,
        omitted_count=preparation.omitted_count,
        preparation_fingerprint=preparation.preparation_fingerprint,
    )


__all__ = [
    "PORTFOLIO_PRESENTATION_PACKAGE_ERROR_CODES",
    "PRESENTATION_MANIFEST_FILENAME",
    "STUDENT_PORTFOLIO_FILE_PACKAGE_CONTRACT_VERSION",
    "PortfolioPresentationPackageError",
    "StudentPortfolioFilePackageResult",
    "create_student_portfolio_file_package",
]
