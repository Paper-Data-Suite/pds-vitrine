"""Producer-independent verification for immutable student Portfolio presentations."""

from __future__ import annotations

import hashlib
import json
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from vitrine.models import PortfolioPresentationArtifact
from vitrine.models.errors import VitrineSerializationError
from vitrine.models.serialization import strict_json_loads
from vitrine.path_policy import (
    PRESENTATION_DIRECTORY_MAX_LENGTH,
    PRESENTATION_FILENAME_MAX_LENGTH,
    VitrinePathPolicyError,
    require_generated_component,
    require_unique_presentation_components,
)
from vitrine.portfolio_presentation import (
    STUDENT_PORTFOLIO_PRESENTATION_CLASS,
    PortfolioPresentationPreparationError,
    StudentPortfolioPresentationPreparation,
    prepare_student_portfolio_presentation,
    presentation_artifact_custody_relative_path,
)
from vitrine.portfolio_presentation_contract import (
    STUDENT_PORTFOLIO_PRESENTATION_RENDERER_CONTRACT_VERSION,
    STUDENT_PORTFOLIO_PRESENTATION_RENDERER_ID,
    STUDENT_PORTFOLIO_PRESENTATION_RENDERER_VERSION,
    student_portfolio_renderer_configuration_sha256,
)
from vitrine.portfolio_presentation_html import (
    STUDENT_PORTFOLIO_HTML_CONTRACT_VERSION,
    STUDENT_PORTFOLIO_HTML_FILENAME,
    STUDENT_PORTFOLIO_HTML_RENDERER_CONFIGURATION_SHA256,
    STUDENT_PORTFOLIO_HTML_RENDERER_ID,
    STUDENT_PORTFOLIO_HTML_RENDERER_VERSION,
)
from vitrine.portfolio_presentation_package import (
    PRESENTATION_MANIFEST_FILENAME,
    STUDENT_PORTFOLIO_FILE_INVENTORY_CONTRACT_VERSION,
    STUDENT_PORTFOLIO_FILE_PACKAGE_CONTRACT_VERSION,
)
from vitrine.portfolio_presentation_pdf import (
    PDF_PRINT_DISPOSITIONS,
    STUDENT_PORTFOLIO_PDF_CONTRACT_VERSION,
    STUDENT_PORTFOLIO_PDF_RENDERER_ID,
    STUDENT_PORTFOLIO_PDF_RENDERER_VERSION,
)
from vitrine.snapshot_distribution import (
    SnapshotDistributionError,
    verify_snapshot_edition,
    verify_snapshot_export,
)
from vitrine.storage import (
    VitrineStorageError,
    VitrineStorageNotFoundError,
    load_current_records_with_state,
)
from vitrine.storage.errors import VitrineStorageValidationError
from vitrine.storage.paths import safe_vitrine_descendant

PORTFOLIO_PRESENTATION_VERIFICATION_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "portfolio_presentation_verification.invalid_request",
        "portfolio_presentation_verification.canonical_not_found",
        "portfolio_presentation_verification.canonical_inconsistent",
        "portfolio_presentation_verification.snapshot_verification_failed",
        "portfolio_presentation_verification.custody_invalid",
        "portfolio_presentation_verification.manifest_invalid",
        "portfolio_presentation_verification.inventory_mismatch",
        "portfolio_presentation_verification.file_mismatch",
        "portfolio_presentation_verification.unexpected_file",
        "portfolio_presentation_verification.source_mismatch",
        "portfolio_presentation_verification.naming_invalid",
    }
)


class PortfolioPresentationVerificationError(RuntimeError):
    """Stable fail-closed verification error for student Portfolio presentation."""

    def __init__(self, code: str, message: str, *, stage: str) -> None:
        if code not in PORTFOLIO_PRESENTATION_VERIFICATION_ERROR_CODES:
            raise ValueError(f"unsupported Portfolio verification code: {code}")
        self.code = code
        self.stage = stage
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class StudentPortfolioPackageVerification:
    presentation_artifact_id: str
    relative_path: str
    presentation_manifest_relative_path: str
    presentation_manifest_sha256: str
    html_relative_path: str
    html_sha256: str
    printable_pdf_relative_path: str
    printable_pdf_sha256: str
    package_inventory_sha256: str
    pdf_renderer_configuration_sha256: str
    renderer_configuration_sha256: str
    verified_file_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PortfolioPresentationVerification:
    presentation_artifact_id: str
    snapshot_series_id: str
    edition_number: int
    snapshot_export_artifact_id: str
    relative_path: str
    presentation_manifest_sha256: str
    html_sha256: str
    printable_pdf_sha256: str
    package_inventory_sha256: str
    verified_file_paths: tuple[str, ...]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.manifest_invalid",
            f"Presentation manifest {label} must be an object.",
            stage="manifest",
        )
    return cast(Mapping[str, object], value)


def _require_exact_keys(
    value: Mapping[str, object],
    expected: set[str],
    label: str,
) -> None:
    if set(value) != expected:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.manifest_invalid",
            f"Presentation manifest {label} contains missing or unexpected fields.",
            stage="manifest",
        )


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.manifest_invalid",
            f"Presentation manifest {label} must be nonempty text.",
            stage="manifest",
        )
    return value


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.manifest_invalid",
            f"Presentation manifest {label} must be a positive integer.",
            stage="manifest",
        )
    return value


def _nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.manifest_invalid",
            f"Presentation manifest {label} must be a nonnegative integer.",
            stage="manifest",
        )
    return value


def _digest(value: object, label: str) -> str:
    text = _string(value, label)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.manifest_invalid",
            f"Presentation manifest {label} must be a lowercase SHA-256 digest.",
            stage="manifest",
        )
    return text


def _safe_relative_file(value: object, label: str) -> str:
    text = _string(value, label)
    if "\\" in text or ":" in text:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.naming_invalid",
            f"Presentation {label} is not a portable relative path.",
            stage="naming",
        )
    parts = text.split("/")
    if len(parts) not in {1, 2} or any(part in {"", ".", ".."} for part in parts):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.naming_invalid",
            f"Presentation {label} is not a bounded package-relative file path.",
            stage="naming",
        )
    try:
        if len(parts) == 2:
            require_generated_component(
                parts[0],
                maximum=PRESENTATION_DIRECTORY_MAX_LENGTH,
                field_name=f"{label}_directory",
            )
        require_generated_component(
            parts[-1],
            maximum=PRESENTATION_FILENAME_MAX_LENGTH,
            field_name=f"{label}_filename",
        )
    except VitrinePathPolicyError as error:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.naming_invalid",
            f"Presentation {label} violates bounded component policy.",
            stage="naming",
        ) from error
    return text


def _read_file(root: Path, relative_path: str) -> bytes:
    current = root
    parts = relative_path.split("/")
    for component in parts[:-1]:
        current = current / component
        if not current.exists() or not current.is_dir() or not _is_plain(current):
            raise PortfolioPresentationVerificationError(
                "portfolio_presentation_verification.file_mismatch",
                "Presentation package contains an unsafe directory path.",
                stage="files",
            )
    target = current / parts[-1]
    if not target.exists() or not target.is_file() or not _is_plain(target):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.file_mismatch",
            "Presentation package file is missing or unsafe.",
            stage="files",
        )
    try:
        return target.read_bytes()
    except OSError as error:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.file_mismatch",
            "Presentation package file could not be read safely.",
            stage="files",
        ) from error


def _expected_sections(
    preparation: StudentPortfolioPresentationPreparation,
) -> list[dict[str, object]]:
    sections: list[dict[str, object]] = []
    for section in preparation.sections:
        items: list[dict[str, object]] = []
        for item in section.items:
            path = (
                None
                if not item.export_file_available
                else f"{section.presentation_directory_name}/{item.presentation_filename}"
            )
            items.append(
                {
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
                    "presentation_relative_path": path,
                    "byte_size": item.byte_size if path is not None else None,
                    "sha256": item.output_sha256 if path is not None else None,
                }
            )
        sections.append(
            {
                "section_id": section.section_id,
                "label": section.label,
                "purpose": section.purpose,
                "order": section.order,
                "obligation": section.obligation,
                "presentation_directory_name": section.presentation_directory_name,
                "items": items,
            }
        )
    return sections


def _verify_prepared_name_inventory(
    preparation: StudentPortfolioPresentationPreparation,
) -> None:
    try:
        require_unique_presentation_components(
            (
                PRESENTATION_MANIFEST_FILENAME,
                STUDENT_PORTFOLIO_HTML_FILENAME,
                *(
                    section.presentation_directory_name
                    for section in preparation.sections
                ),
            )
        )
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
    except VitrinePathPolicyError as error:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.naming_invalid",
            "Frozen presentation names violate bounded sibling-collision policy.",
            stage="naming",
        ) from error


def _verify_snapshot_bindings(
    root: str | Path,
    preparation: StudentPortfolioPresentationPreparation,
) -> None:
    try:
        edition = verify_snapshot_edition(
            root,
            snapshot_series_id=preparation.snapshot_edition.snapshot_series_id,
            edition_number=preparation.snapshot_edition.edition_number,
        )
        export = verify_snapshot_export(
            root,
            snapshot_export_artifact_id=preparation.snapshot_export_artifact_id,
        )
    except SnapshotDistributionError as error:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.snapshot_verification_failed",
            "Referenced immutable Snapshot custody no longer verifies.",
            stage="snapshot",
        ) from error
    if (
        edition.manifest_digest.value != preparation.snapshot_manifest_sha256
        or edition.logical_inventory_digest.value
        != preparation.snapshot_logical_inventory_sha256
        or export.snapshot_series_id
        != preparation.snapshot_edition.snapshot_series_id
        or export.edition_number != preparation.snapshot_edition.edition_number
        or export.directory_inventory_digest.value
        != preparation.technical_export_inventory_sha256
    ):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.snapshot_verification_failed",
            "Presentation bindings differ from verified Snapshot/Export history.",
            stage="snapshot",
        )


def verify_student_portfolio_file_package(
    root: str | Path,
    preparation: StudentPortfolioPresentationPreparation,
    *,
    presentation_artifact_id: str,
    expected_manifest_sha256: str | None = None,
    expected_html_sha256: str | None = None,
    expected_printable_pdf_sha256: str | None = None,
    expected_package_inventory_sha256: str | None = None,
) -> StudentPortfolioPackageVerification:
    """Verify one published package without requiring a canonical Presentation record."""

    if not isinstance(preparation, StudentPortfolioPresentationPreparation):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.invalid_request",
            "Package verification requires exact presentation preparation.",
            stage="request",
        )
    if preparation.presentation_class != STUDENT_PORTFOLIO_PRESENTATION_CLASS:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.invalid_request",
            "Only student_portfolio package verification is supported.",
            stage="request",
        )
    _verify_prepared_name_inventory(preparation)
    _verify_snapshot_bindings(root, preparation)

    try:
        relative_root = presentation_artifact_custody_relative_path(
            presentation_artifact_id
        )
        package_root = safe_vitrine_descendant(root, relative_root)
    except (PortfolioPresentationPreparationError, VitrineStorageValidationError) as error:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.custody_invalid",
            "Presentation custody cannot be resolved safely.",
            stage="custody",
        ) from error
    if not package_root.exists() or not package_root.is_dir() or not _is_plain(package_root):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.custody_invalid",
            "Presentation custody is missing or unsafe.",
            stage="custody",
        )

    manifest_payload = _read_file(package_root, PRESENTATION_MANIFEST_FILENAME)
    manifest_sha = _sha256(manifest_payload)
    if expected_manifest_sha256 is not None and manifest_sha != expected_manifest_sha256:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.manifest_invalid",
            "Presentation manifest digest differs from canonical state.",
            stage="manifest",
        )
    try:
        raw = strict_json_loads(manifest_payload)
    except VitrineSerializationError as error:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.manifest_invalid",
            "Presentation manifest is not strict JSON.",
            stage="manifest",
        ) from error
    manifest = _mapping(raw, "root")
    _require_exact_keys(
        manifest,
        {
            "file_package_contract_version",
            "presentation_contract_version",
            "presentation_artifact_id",
            "presentation_class",
            "portfolio",
            "profile",
            "audience",
            "snapshot",
            "technical_export",
            "package_inventory",
            "sections",
            "generated_outputs",
            "preparation_fingerprint",
        },
        "root",
    )

    expected_top = {
        "file_package_contract_version": STUDENT_PORTFOLIO_FILE_PACKAGE_CONTRACT_VERSION,
        "presentation_contract_version": preparation.contract_version,
        "presentation_artifact_id": presentation_artifact_id,
        "presentation_class": preparation.presentation_class,
        "preparation_fingerprint": preparation.preparation_fingerprint,
    }
    for key, expected in expected_top.items():
        if manifest.get(key) != expected:
            raise PortfolioPresentationVerificationError(
                "portfolio_presentation_verification.manifest_invalid",
                f"Presentation manifest {key} does not match exact preparation.",
                stage="manifest",
            )

    expected_portfolio = {
        "portfolio_id": preparation.portfolio_id,
        "portfolio_subject_id": preparation.portfolio_subject_id,
        "student_display_name": preparation.student_display_name,
        "title": preparation.portfolio_title,
        "profile_label": preparation.profile_label,
    }
    expected_profile = {
        "profile_binding_id": preparation.profile_binding_id,
        "portfolio_profile_id": preparation.profile_revision.portfolio_profile_id,
        "profile_revision": preparation.profile_revision.profile_revision,
        "composition_revision": preparation.composition_revision,
    }
    expected_audience = {
        "audience_context_id": preparation.audience_context_id,
        "audience_presentation_class": preparation.audience_presentation_class,
        "purpose": preparation.purpose,
    }
    expected_snapshot = {
        "snapshot_series_id": preparation.snapshot_edition.snapshot_series_id,
        "edition_number": preparation.snapshot_edition.edition_number,
        "manifest_sha256": preparation.snapshot_manifest_sha256,
        "logical_inventory_sha256": preparation.snapshot_logical_inventory_sha256,
    }
    expected_export = {
        "snapshot_export_artifact_id": preparation.snapshot_export_artifact_id,
        "directory_inventory_sha256": preparation.technical_export_inventory_sha256,
    }
    for key, expected_binding in (
        ("portfolio", expected_portfolio),
        ("profile", expected_profile),
        ("audience", expected_audience),
        ("snapshot", expected_snapshot),
        ("technical_export", expected_export),
    ):
        if manifest.get(key) != expected_binding:
            raise PortfolioPresentationVerificationError(
                "portfolio_presentation_verification.manifest_invalid",
                f"Presentation manifest {key} binding is inconsistent.",
                stage="manifest",
            )

    if manifest.get("sections") != _expected_sections(preparation):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.source_mismatch",
            "Presentation manifest section/item inventory differs from frozen preparation.",
            stage="sources",
        )

    generated = _mapping(manifest.get("generated_outputs"), "generated_outputs")
    _require_exact_keys(
        generated,
        {"html", "printable_pdf"},
        "generated_outputs",
    )
    html = _mapping(generated.get("html"), "generated_outputs.html")
    pdf = _mapping(
        generated.get("printable_pdf"),
        "generated_outputs.printable_pdf",
    )
    _require_exact_keys(
        html,
        {
            "relative_path",
            "byte_size",
            "sha256",
            "renderer_id",
            "renderer_version",
            "renderer_contract_version",
            "renderer_configuration_sha256",
        },
        "generated_outputs.html",
    )
    _require_exact_keys(
        pdf,
        {
            "relative_path",
            "byte_size",
            "sha256",
            "page_count",
            "renderer_id",
            "renderer_version",
            "renderer_contract_version",
            "renderer_configuration_sha256",
            "items",
        },
        "generated_outputs.printable_pdf",
    )

    html_path = _safe_relative_file(html.get("relative_path"), "HTML path")
    if html_path != STUDENT_PORTFOLIO_HTML_FILENAME:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.manifest_invalid",
            "Presentation HTML path differs from the renderer contract.",
            stage="manifest",
        )
    html_sha = _digest(html.get("sha256"), "HTML sha256")
    html_size = _positive_int(html.get("byte_size"), "HTML byte_size")
    if (
        html.get("renderer_id") != STUDENT_PORTFOLIO_HTML_RENDERER_ID
        or html.get("renderer_version") != STUDENT_PORTFOLIO_HTML_RENDERER_VERSION
        or html.get("renderer_contract_version")
        != STUDENT_PORTFOLIO_HTML_CONTRACT_VERSION
        or html.get("renderer_configuration_sha256")
        != STUDENT_PORTFOLIO_HTML_RENDERER_CONFIGURATION_SHA256
    ):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.manifest_invalid",
            "Presentation HTML renderer binding is unsupported or inconsistent.",
            stage="manifest",
        )
    if expected_html_sha256 is not None and html_sha != expected_html_sha256:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.file_mismatch",
            "Presentation HTML digest differs from canonical state.",
            stage="files",
        )

    pdf_path = _safe_relative_file(pdf.get("relative_path"), "printable PDF path")
    pdf_sha = _digest(pdf.get("sha256"), "printable PDF sha256")
    pdf_size = _positive_int(pdf.get("byte_size"), "printable PDF byte_size")
    _positive_int(pdf.get("page_count"), "printable PDF page_count")
    pdf_configuration = _digest(
        pdf.get("renderer_configuration_sha256"),
        "printable PDF renderer configuration",
    )
    if (
        pdf.get("renderer_id") != STUDENT_PORTFOLIO_PDF_RENDERER_ID
        or pdf.get("renderer_version") != STUDENT_PORTFOLIO_PDF_RENDERER_VERSION
        or pdf.get("renderer_contract_version")
        != STUDENT_PORTFOLIO_PDF_CONTRACT_VERSION
    ):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.manifest_invalid",
            "Printable PDF renderer binding is unsupported or inconsistent.",
            stage="manifest",
        )
    if expected_printable_pdf_sha256 is not None and pdf_sha != expected_printable_pdf_sha256:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.file_mismatch",
            "Printable PDF digest differs from canonical state.",
            stage="files",
        )
    try:
        require_unique_presentation_components(
            (
                PRESENTATION_MANIFEST_FILENAME,
                html_path,
                pdf_path,
                *(
                    section.presentation_directory_name
                    for section in preparation.sections
                ),
            )
        )
    except VitrinePathPolicyError as error:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.naming_invalid",
            "Presentation root components contain a portable collision.",
            stage="naming",
        ) from error

    raw_print_items = pdf.get("items")
    if not isinstance(raw_print_items, list):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.manifest_invalid",
            "Printable PDF item dispositions must be an array.",
            stage="manifest",
        )
    expected_entry_ids = [
        item.entry_plan_id
        for section in preparation.sections
        for item in section.items
    ]
    observed_entry_ids: list[str] = []
    for index, value in enumerate(raw_print_items):
        entry = _mapping(value, f"printable_pdf.items[{index}]")
        _require_exact_keys(
            entry,
            {"entry_plan_id", "print_disposition", "page_count"},
            f"printable_pdf.items[{index}]",
        )
        observed_entry_ids.append(
            _string(entry.get("entry_plan_id"), "print entry_plan_id")
        )
        disposition = _string(entry.get("print_disposition"), "print disposition")
        if disposition not in PDF_PRINT_DISPOSITIONS:
            raise PortfolioPresentationVerificationError(
                "portfolio_presentation_verification.manifest_invalid",
                "Printable PDF contains an unsupported item disposition.",
                stage="manifest",
            )
        _nonnegative_int(entry.get("page_count"), "print item page_count")
    if observed_entry_ids != expected_entry_ids:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.source_mismatch",
            "Printable PDF item dispositions do not cover frozen items in exact order.",
            stage="sources",
        )

    file_values: list[dict[str, object]] = []
    expected_paths: list[str] = []
    for section in preparation.sections:
        for item in section.items:
            if not item.export_file_available:
                continue
            if (
                item.presentation_filename is None
                or item.byte_size is None
                or item.output_sha256 is None
            ):
                raise PortfolioPresentationVerificationError(
                    "portfolio_presentation_verification.source_mismatch",
                    "Frozen byte-bearing item is incomplete for verification.",
                    stage="sources",
                )
            relative = _safe_relative_file(
                f"{section.presentation_directory_name}/{item.presentation_filename}",
                "source path",
            )
            expected_paths.append(relative)
            file_values.append(
                {
                    "relative_path": relative,
                    "byte_size": item.byte_size,
                    "sha256": item.output_sha256,
                }
            )
    expected_paths.extend((html_path, pdf_path))
    file_values.extend(
        (
            {
                "relative_path": html_path,
                "byte_size": html_size,
                "sha256": html_sha,
            },
            {
                "relative_path": pdf_path,
                "byte_size": pdf_size,
                "sha256": pdf_sha,
            },
        )
    )
    try:
        require_unique_presentation_components(
            tuple(path.casefold() for path in expected_paths)
        )
    except VitrinePathPolicyError as error:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.naming_invalid",
            "Presentation package contains colliding file paths.",
            stage="naming",
        ) from error

    inventory = _mapping(manifest.get("package_inventory"), "package_inventory")
    _require_exact_keys(
        inventory,
        {"contract_version", "sha256", "file_count"},
        "package_inventory",
    )
    if (
        inventory.get("contract_version")
        != STUDENT_PORTFOLIO_FILE_INVENTORY_CONTRACT_VERSION
    ):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.inventory_mismatch",
            "Presentation inventory contract version is unsupported.",
            stage="inventory",
        )
    inventory_sha = _digest(inventory.get("sha256"), "package inventory sha256")
    if _positive_int(inventory.get("file_count"), "package inventory file_count") != len(file_values):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.inventory_mismatch",
            "Presentation inventory file count is inconsistent.",
            stage="inventory",
        )
    inventory_value = {
        "contract_version": STUDENT_PORTFOLIO_FILE_INVENTORY_CONTRACT_VERSION,
        "files": sorted(file_values, key=lambda item: cast(str, item["relative_path"])),
    }
    calculated_inventory_sha = _sha256(_canonical_json_bytes(inventory_value))
    if inventory_sha != calculated_inventory_sha:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.inventory_mismatch",
            "Presentation package inventory digest is inconsistent.",
            stage="inventory",
        )
    if (
        expected_package_inventory_sha256 is not None
        and inventory_sha != expected_package_inventory_sha256
    ):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.inventory_mismatch",
            "Presentation package inventory differs from canonical state.",
            stage="inventory",
        )

    expected_file_map = {
        cast(str, item["relative_path"]): (
            cast(int, item["byte_size"]),
            cast(str, item["sha256"]),
        )
        for item in file_values
    }
    verified: list[str] = []
    for relative, (expected_size, expected_sha) in sorted(expected_file_map.items()):
        payload = _read_file(package_root, relative)
        if len(payload) != expected_size or _sha256(payload) != expected_sha:
            raise PortfolioPresentationVerificationError(
                "portfolio_presentation_verification.file_mismatch",
                "Presentation package file bytes differ from recorded exact bytes.",
                stage="files",
            )
        verified.append(relative)

    expected_section_dirs = {
        section.presentation_directory_name for section in preparation.sections
    }
    expected_root_files = {
        PRESENTATION_MANIFEST_FILENAME,
        html_path,
        pdf_path,
    }
    actual_files: set[str] = set()
    actual_dirs: set[str] = set()
    try:
        for filesystem_entry in package_root.iterdir():
            if filesystem_entry.is_symlink() or not _is_plain(filesystem_entry):
                raise PortfolioPresentationVerificationError(
                    "portfolio_presentation_verification.unexpected_file",
                    "Presentation custody contains a symlink or reparse point.",
                    stage="files",
                )
            if filesystem_entry.is_file():
                actual_files.add(filesystem_entry.name)
                continue
            if not filesystem_entry.is_dir():
                raise PortfolioPresentationVerificationError(
                    "portfolio_presentation_verification.unexpected_file",
                    "Presentation custody contains an unsupported filesystem entry.",
                    stage="files",
                )
            actual_dirs.add(filesystem_entry.name)
            for child in filesystem_entry.iterdir():
                if child.is_symlink() or not child.is_file() or not _is_plain(child):
                    raise PortfolioPresentationVerificationError(
                        "portfolio_presentation_verification.unexpected_file",
                        "Presentation section contains an unexpected filesystem entry.",
                        stage="files",
                    )
                actual_files.add(f"{filesystem_entry.name}/{child.name}")
    except OSError as error:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.file_mismatch",
            "Presentation custody could not be enumerated safely.",
            stage="files",
        ) from error

    if actual_dirs != expected_section_dirs:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.unexpected_file",
            "Presentation package section directories differ from frozen preparation.",
            stage="files",
        )
    expected_all_files = {*expected_file_map, PRESENTATION_MANIFEST_FILENAME}
    if actual_files != expected_all_files:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.unexpected_file",
            "Presentation package contains missing or unexpected files.",
            stage="files",
        )
    if not expected_root_files.issubset(actual_files):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.unexpected_file",
            "Presentation package is missing required root outputs.",
            stage="files",
        )

    renderer_configuration = student_portfolio_renderer_configuration_sha256(
        pdf_renderer_configuration_sha256=pdf_configuration
    )
    return StudentPortfolioPackageVerification(
        presentation_artifact_id=presentation_artifact_id,
        relative_path=relative_root,
        presentation_manifest_relative_path=(
            f"{relative_root}/{PRESENTATION_MANIFEST_FILENAME}"
        ),
        presentation_manifest_sha256=manifest_sha,
        html_relative_path=f"{relative_root}/{html_path}",
        html_sha256=html_sha,
        printable_pdf_relative_path=f"{relative_root}/{pdf_path}",
        printable_pdf_sha256=pdf_sha,
        package_inventory_sha256=inventory_sha,
        pdf_renderer_configuration_sha256=pdf_configuration,
        renderer_configuration_sha256=renderer_configuration,
        verified_file_paths=tuple(verified),
    )


def verify_portfolio_presentation(
    root: str | Path,
    *,
    presentation_artifact_id: str,
) -> PortfolioPresentationVerification:
    """Verify one canonical Presentation Artifact and its complete package."""

    try:
        _current, records = load_current_records_with_state(root)
    except (VitrineStorageNotFoundError, VitrineStorageError) as error:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.canonical_not_found",
            "Canonical Vitrine state is unavailable for presentation verification.",
            stage="canonical",
        ) from error
    matches = tuple(
        item
        for item in records
        if isinstance(item, PortfolioPresentationArtifact)
        and item.presentation_artifact_id == presentation_artifact_id
    )
    if len(matches) != 1:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.canonical_not_found",
            "Presentation Artifact must resolve uniquely in canonical state.",
            stage="canonical",
        )
    artifact = matches[0]
    if (
        artifact.presentation_class != STUDENT_PORTFOLIO_PRESENTATION_CLASS
        or artifact.renderer_id != STUDENT_PORTFOLIO_PRESENTATION_RENDERER_ID
        or artifact.renderer_version != STUDENT_PORTFOLIO_PRESENTATION_RENDERER_VERSION
        or artifact.renderer_contract_version
        != STUDENT_PORTFOLIO_PRESENTATION_RENDERER_CONTRACT_VERSION
    ):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.canonical_inconsistent",
            "Canonical Presentation Artifact uses an unsupported renderer contract.",
            stage="canonical",
        )

    try:
        preparation = prepare_student_portfolio_presentation(
            root,
            snapshot_series_id=artifact.snapshot_edition.snapshot_series_id,
            edition_number=artifact.snapshot_edition.edition_number,
            snapshot_export_artifact_id=artifact.snapshot_export_artifact_id,
        )
    except PortfolioPresentationPreparationError as error:
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.canonical_inconsistent",
            "Canonical Presentation Artifact no longer resolves to exact frozen preparation.",
            stage="canonical",
        ) from error
    if (
        artifact.portfolio_id != preparation.portfolio_id
        or artifact.portfolio_subject_id != preparation.portfolio_subject_id
        or artifact.profile_binding_id != preparation.profile_binding_id
        or artifact.profile_revision != preparation.profile_revision
        or artifact.audience_context_id != preparation.audience_context_id
        or artifact.presentation_contract_version != preparation.contract_version
    ):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.canonical_inconsistent",
            "Canonical Presentation Artifact differs from exact frozen preparation.",
            stage="canonical",
        )

    package = verify_student_portfolio_file_package(
        root,
        preparation,
        presentation_artifact_id=artifact.presentation_artifact_id,
        expected_manifest_sha256=artifact.presentation_manifest_digest.value,
        expected_html_sha256=artifact.html_digest.value,
        expected_printable_pdf_sha256=artifact.printable_pdf_digest.value,
        expected_package_inventory_sha256=artifact.package_inventory_digest.value,
    )
    if (
        artifact.relative_path != package.relative_path
        or artifact.presentation_manifest_relative_path
        != package.presentation_manifest_relative_path
        or artifact.html_relative_path != package.html_relative_path
        or artifact.printable_pdf_relative_path
        != package.printable_pdf_relative_path
        or artifact.renderer_configuration_digest.value
        != package.renderer_configuration_sha256
    ):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.canonical_inconsistent",
            "Canonical Presentation Artifact path/configuration bindings are inconsistent.",
            stage="canonical",
        )

    return PortfolioPresentationVerification(
        presentation_artifact_id=artifact.presentation_artifact_id,
        snapshot_series_id=artifact.snapshot_edition.snapshot_series_id,
        edition_number=artifact.snapshot_edition.edition_number,
        snapshot_export_artifact_id=artifact.snapshot_export_artifact_id,
        relative_path=artifact.relative_path,
        presentation_manifest_sha256=package.presentation_manifest_sha256,
        html_sha256=package.html_sha256,
        printable_pdf_sha256=package.printable_pdf_sha256,
        package_inventory_sha256=package.package_inventory_sha256,
        verified_file_paths=package.verified_file_paths,
    )


__all__ = [
    "PORTFOLIO_PRESENTATION_VERIFICATION_ERROR_CODES",
    "PortfolioPresentationVerification",
    "PortfolioPresentationVerificationError",
    "StudentPortfolioPackageVerification",
    "verify_portfolio_presentation",
    "verify_student_portfolio_file_package",
]
