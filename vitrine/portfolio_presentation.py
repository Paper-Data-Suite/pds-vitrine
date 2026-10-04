"""Read-only preparation for a derived student-facing Portfolio presentation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, TypeVar

from vitrine.models import (
    AudienceContext,
    Portfolio,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioProfileBinding,
    PortfolioProfileRevision,
    PortfolioSubject,
    SnapshotBuildAttemptResult,
    SnapshotBuildPlan,
    SnapshotEdition,
    SnapshotEditionBuildProvenance,
    SnapshotEntry,
    SnapshotExportArtifact,
    SnapshotMaterializationProvenance,
    SnapshotMaterializationRecord,
    SnapshotOmission,
    SnapshotSeal,
    WorkingPortfolioCompositionRevision,
)
from vitrine.models.common import require_identifier, require_positive_int
from vitrine.models.errors import VitrineModelValidationError
from vitrine.models.identity import ProfileRevisionRef, SnapshotEditionRef
from vitrine.path_policy import (
    VitrinePathPolicyError,
    build_bounded_custody_token,
    build_bounded_presentation_directory_name,
    build_bounded_presentation_filename,
    require_unique_presentation_components,
)
from vitrine.snapshot_distribution import (
    SnapshotDistributionError,
    verify_snapshot_export,
)
from vitrine.storage import (
    VitrineStorageError,
    VitrineStorageNotFoundError,
    load_current_records_with_state,
)

STUDENT_PORTFOLIO_PRESENTATION_CONTRACT_VERSION: Final[str] = (
    "vitrine_student_portfolio_presentation_v1"
)
STUDENT_PORTFOLIO_PRESENTATION_CLASS: Final[str] = "student_portfolio"
PORTFOLIO_PRESENTATION_CUSTODY_NAMESPACE: Final[str] = "presentations-bounded-v1"
_PORTFOLIO_PRESENTATION_CUSTODY_DOMAIN: Final[str] = "portfolio-presentation-artifact"
_ITEM_FILENAME_DOMAIN: Final[str] = "student-portfolio-item"
_SECTION_DIRECTORY_DOMAIN: Final[str] = "student-portfolio-section"

_MEDIA_EXTENSION_BY_TYPE: Final[dict[str, str]] = {
    "application/json": ".json",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/tiff": ".tiff",
    "text/markdown": ".md",
    "text/plain": ".txt",
}
PORTFOLIO_PRESENTATION_PREPARATION_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "portfolio_presentation.invalid_request",
        "portfolio_presentation.verification_failed",
        "portfolio_presentation.context_not_found",
        "portfolio_presentation.context_inconsistent",
        "portfolio_presentation.inventory_inconsistent",
        "portfolio_presentation.naming_failed",
        "portfolio_presentation.unsupported_media",
        "portfolio_presentation.unsupported_presentation_class",
        "portfolio_presentation.portfolio_index_prohibited",
    }
)


class PortfolioPresentationPreparationError(RuntimeError):
    def __init__(self, code: str, message: str, *, stage: str) -> None:
        if code not in PORTFOLIO_PRESENTATION_PREPARATION_ERROR_CODES:
            raise ValueError(f"unsupported Portfolio presentation error code: {code}")
        super().__init__(message)
        self.code = code
        self.stage = stage


@dataclass(frozen=True, slots=True)
class StudentPortfolioPresentationItem:
    entry_plan_id: str
    plan_position: int
    section_id: str
    ordinal: int
    semantic_role: str
    content_class: str
    materialization_kind: str
    disposition: str
    display_title: str
    display_caption: str | None
    source_credit: str | None
    presentation_note: str | None
    candidate_id: str | None
    selection_id: str | None
    placement_id: str | None
    snapshot_entry_id: str | None
    materialization_id: str | None
    omission_id: str | None
    technical_relative_path: str | None
    media_type: str | None
    byte_size: int | None
    output_sha256: str | None
    export_file_available: bool
    presentation_filename: str | None


@dataclass(frozen=True, slots=True)
class StudentPortfolioPresentationSection:
    section_id: str
    label: str
    purpose: str
    order: int
    obligation: str
    presentation_directory_name: str
    items: tuple[StudentPortfolioPresentationItem, ...]


@dataclass(frozen=True, slots=True)
class StudentPortfolioPresentationPreparation:
    contract_version: str
    observed_state_revision: int
    snapshot_edition: SnapshotEditionRef
    snapshot_export_artifact_id: str
    snapshot_manifest_sha256: str
    snapshot_logical_inventory_sha256: str
    portfolio_id: str
    portfolio_subject_id: str
    profile_binding_id: str
    profile_revision: ProfileRevisionRef
    composition_revision: int
    audience_context_id: str
    presentation_class: str
    audience_presentation_class: str
    student_display_name: str | None
    portfolio_title: str
    profile_label: str
    purpose: str
    technical_export_relative_path: str
    technical_export_inventory_sha256: str
    custody_namespace: str
    sections: tuple[StudentPortfolioPresentationSection, ...]
    file_item_count: int
    reference_only_count: int
    omitted_count: int
    preparation_fingerprint: str


T = TypeVar("T")


def presentation_artifact_custody_relative_path(presentation_artifact_id: str) -> str:
    """Return the bounded prospective custody root for one artifact identity."""

    try:
        exact_id = require_identifier(
            presentation_artifact_id, "presentation_artifact_id"
        )
        token = build_bounded_custody_token(
            domain=_PORTFOLIO_PRESENTATION_CUSTODY_DOMAIN,
            semantic_identity={"presentation_artifact_id": exact_id},
        )
    except (VitrineModelValidationError, VitrinePathPolicyError) as error:
        raise PortfolioPresentationPreparationError(
            "portfolio_presentation.invalid_request",
            "Portfolio presentation artifact identity is invalid.",
            stage="custody",
        ) from error
    return f"{PORTFOLIO_PRESENTATION_CUSTODY_NAMESPACE}/{token}"


def _one(
    values: tuple[object, ...],
    cls: type[T],
    predicate: Callable[[T], bool],
    *,
    label: str,
) -> T:
    matches: tuple[T, ...] = tuple(
        item for item in values if isinstance(item, cls) and predicate(item)
    )
    if len(matches) != 1:
        raise PortfolioPresentationPreparationError(
            "portfolio_presentation.context_not_found",
            f"{label} must resolve to exactly one canonical record.",
            stage="resolution",
        )
    return matches[0]


def _optional_one(
    values: tuple[object, ...],
    cls: type[T],
    predicate: Callable[[T], bool],
    *,
    label: str,
) -> T | None:
    matches: tuple[T, ...] = tuple(
        item for item in values if isinstance(item, cls) and predicate(item)
    )
    if len(matches) > 1:
        raise PortfolioPresentationPreparationError(
            "portfolio_presentation.context_inconsistent",
            f"{label} resolves to more than one canonical record.",
            stage="resolution",
        )
    return None if not matches else matches[0]


def _extension(media_type: str) -> str:
    known = _MEDIA_EXTENSION_BY_TYPE.get(media_type.casefold())
    if known is None:
        raise PortfolioPresentationPreparationError(
            "portfolio_presentation.unsupported_media",
            "The exact frozen media type has no controlled student-facing extension.",
            stage="media",
        )
    return known


def _friendly_key(value: str) -> str:
    text = value.replace("_", " ").replace("-", " ").strip()
    return " ".join(part.capitalize() for part in text.split()) or "Portfolio Item"


def _fingerprint_value(
    *,
    edition: SnapshotEdition,
    seal: SnapshotSeal,
    artifact: SnapshotExportArtifact,
    audience: AudienceContext,
    profile: PortfolioProfileRevision,
    composition: WorkingPortfolioCompositionRevision,
    sections: tuple[StudentPortfolioPresentationSection, ...],
) -> str:
    value = {
        "contract_version": STUDENT_PORTFOLIO_PRESENTATION_CONTRACT_VERSION,
        "presentation_class": STUDENT_PORTFOLIO_PRESENTATION_CLASS,
        "snapshot_edition": {
            "snapshot_series_id": edition.snapshot_series_id,
            "edition_number": edition.edition_number,
        },
        "snapshot_export_artifact_id": artifact.snapshot_export_artifact_id,
        "snapshot_manifest_digest": seal.manifest_digest.value,
        "snapshot_logical_inventory_digest": seal.logical_inventory_digest.value,
        "directory_inventory_digest": artifact.directory_inventory_digest.value,
        "portfolio_id": edition.portfolio_id,
        "portfolio_subject_id": edition.portfolio_subject_id,
        "profile_binding_id": edition.profile_binding_id,
        "profile_revision": {
            "portfolio_profile_id": edition.profile_revision.portfolio_profile_id,
            "profile_revision": edition.profile_revision.profile_revision,
        },
        "composition_revision": composition.composition_revision,
        "audience_context_id": audience.audience_context_id,
        "profile_label": profile.label,
        "sections": [asdict(section) for section in sections],
    }
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _context_mismatch(message: str) -> PortfolioPresentationPreparationError:
    return PortfolioPresentationPreparationError(
        "portfolio_presentation.context_inconsistent",
        message,
        stage="resolution",
    )


def _inventory_mismatch(message: str) -> PortfolioPresentationPreparationError:
    return PortfolioPresentationPreparationError(
        "portfolio_presentation.inventory_inconsistent",
        message,
        stage="inventory",
    )


def prepare_student_portfolio_presentation(
    root: str | Path,
    *,
    snapshot_series_id: str,
    edition_number: int,
    snapshot_export_artifact_id: str,
) -> StudentPortfolioPresentationPreparation:
    """Prepare one exact student-facing presentation without producer access or writes."""

    try:
        series_id = require_identifier(snapshot_series_id, "snapshot_series_id")
        edition_no = require_positive_int(edition_number, "edition_number")
        export_id = require_identifier(
            snapshot_export_artifact_id, "snapshot_export_artifact_id"
        )
    except VitrineModelValidationError as error:
        raise PortfolioPresentationPreparationError(
            "portfolio_presentation.invalid_request",
            "Portfolio presentation request is invalid.",
            stage="request",
        ) from error

    try:
        export_verification = verify_snapshot_export(
            root,
            snapshot_export_artifact_id=export_id,
        )
    except SnapshotDistributionError as error:
        raise PortfolioPresentationPreparationError(
            "portfolio_presentation.verification_failed",
            "The exact technical Snapshot Export failed producer-independent verification.",
            stage="verification",
        ) from error
    if (
        export_verification.snapshot_series_id != series_id
        or export_verification.edition_number != edition_no
    ):
        raise PortfolioPresentationPreparationError(
            "portfolio_presentation.verification_failed",
            "The verified technical Export does not belong to the requested Snapshot Edition.",
            stage="verification",
        )

    try:
        current, records = load_current_records_with_state(root)
    except (VitrineStorageNotFoundError, VitrineStorageError) as error:
        raise PortfolioPresentationPreparationError(
            "portfolio_presentation.context_not_found",
            "Vitrine canonical state is unavailable for Portfolio presentation preparation.",
            stage="load",
        ) from error
    values = tuple(records)

    edition = _one(
        values,
        SnapshotEdition,
        lambda item: item.snapshot_series_id == series_id
        and item.edition_number == edition_no,
        label="Snapshot Edition",
    )
    seal_id = edition.seal_id

    def matches_seal(item: SnapshotSeal) -> bool:
        return item.seal_id == seal_id

    seal = _one(
        values,
        SnapshotSeal,
        matches_seal,
        label="Snapshot Seal",
    )
    if (
        seal.snapshot_edition != edition.reference
        or seal.manifest_id != edition.manifest_id
    ):
        raise _context_mismatch("Snapshot Seal does not match the sealed Edition.")
    artifact = _one(
        values,
        SnapshotExportArtifact,
        lambda item: item.snapshot_export_artifact_id == export_id,
        label="Snapshot Export Artifact",
    )
    if artifact.snapshot_edition != edition.reference:
        raise _context_mismatch("Snapshot Export Artifact belongs to another Edition.")

    portfolio = _one(
        values,
        Portfolio,
        lambda item: item.portfolio_id == edition.portfolio_id,
        label="Portfolio",
    )
    subject = _one(
        values,
        PortfolioSubject,
        lambda item: item.portfolio_subject_id == edition.portfolio_subject_id,
        label="Portfolio Subject",
    )
    binding = _one(
        values,
        PortfolioProfileBinding,
        lambda item: item.profile_binding_id == edition.profile_binding_id,
        label="Portfolio Profile Binding",
    )
    profile = _one(
        values,
        PortfolioProfileRevision,
        lambda item: item.reference == edition.profile_revision,
        label="Portfolio Profile Revision",
    )
    audience = _one(
        values,
        AudienceContext,
        lambda item: item.audience_context_id == edition.audience_context_id,
        label="Audience Context",
    )
    composition = _one(
        values,
        WorkingPortfolioCompositionRevision,
        lambda item: item.portfolio_id == edition.portfolio_id
        and item.composition_revision == edition.composition_revision,
        label="Working Portfolio Composition",
    )
    provenance = _one(
        values,
        SnapshotEditionBuildProvenance,
        lambda item: item.snapshot_edition == edition.reference,
        label="Snapshot Edition build provenance",
    )
    plan = _one(
        values,
        SnapshotBuildPlan,
        lambda item: item.snapshot_build_plan_id == provenance.snapshot_build_plan_id,
        label="Snapshot Build Plan",
    )
    result = _one(
        values,
        SnapshotBuildAttemptResult,
        lambda item: item.snapshot_build_attempt_result_id
        == provenance.snapshot_build_attempt_result_id,
        label="Snapshot Build Attempt Result",
    )

    if portfolio.portfolio_subject_id != edition.portfolio_subject_id:
        raise _context_mismatch("Portfolio Subject does not match the sealed Edition.")
    if (
        binding.portfolio_id != edition.portfolio_id
        or binding.profile_revision != edition.profile_revision
    ):
        raise _context_mismatch("Profile Binding does not match the sealed Edition.")
    if (
        audience.portfolio_id != edition.portfolio_id
        or audience.portfolio_subject_id != edition.portfolio_subject_id
        or audience.profile_binding_id != edition.profile_binding_id
        or audience.profile_revision != edition.profile_revision
    ):
        raise _context_mismatch("Audience Context does not match the sealed Edition.")
    matching_audience_rules = tuple(
        item
        for item in profile.audience_rules
        if item.audience_rule_id == audience.audience_rule_id
    )
    if len(matching_audience_rules) != 1:
        raise _context_mismatch(
            "Audience Context does not resolve to one exact frozen Profile Audience Rule."
        )
    audience_rule = matching_audience_rules[0]
    if (
        audience.audience_class != audience_rule.audience_class
        or audience.purpose != audience_rule.purpose
        or audience.allowed_content_classes != audience_rule.allowed_content_classes
        or audience.prohibited_content_classes
        != audience_rule.prohibited_content_classes
        or audience.required_review_classes != audience_rule.required_review_classes
        or audience.presentation_class != audience_rule.presentation_class
        or audience.retention_policy_reference
        != audience_rule.retention_policy_reference
    ):
        raise _context_mismatch(
            "Audience Context policy differs from its exact frozen Profile Audience Rule."
        )
    if audience_rule.presentation_class != STUDENT_PORTFOLIO_PRESENTATION_CLASS:
        raise PortfolioPresentationPreparationError(
            "portfolio_presentation.unsupported_presentation_class",
            "The exact Audience Rule does not permit the student Portfolio renderer.",
            stage="audience",
        )
    if (
        "portfolio_index" not in audience_rule.allowed_content_classes
        or "portfolio_index" in audience_rule.prohibited_content_classes
    ):
        raise PortfolioPresentationPreparationError(
            "portfolio_presentation.portfolio_index_prohibited",
            "The exact Audience Rule does not permit the Portfolio index layer.",
            stage="audience",
        )
    if (
        composition.portfolio_subject_id != edition.portfolio_subject_id
        or composition.profile_binding_id != edition.profile_binding_id
        or composition.profile_revision != edition.profile_revision
    ):
        raise _context_mismatch("Working Composition does not match the sealed Edition.")
    if (
        plan.snapshot_series_id != edition.snapshot_series_id
        or plan.portfolio_id != edition.portfolio_id
        or plan.portfolio_subject_id != edition.portfolio_subject_id
        or plan.profile_binding_id != edition.profile_binding_id
        or plan.profile_revision != edition.profile_revision
        or plan.composition_revision != edition.composition_revision
        or plan.audience_context_id != edition.audience_context_id
        or result.sealed_snapshot_edition != edition.reference
    ):
        raise _context_mismatch(
            "Snapshot build history does not reproduce the sealed Edition context."
        )

    outcomes = {item.entry_plan_id: item for item in result.entry_outcomes}
    if set(outcomes) != {item.entry_plan_id for item in plan.entry_plans}:
        raise _inventory_mismatch(
            "Snapshot Attempt Result does not cover the complete frozen Entry Plan inventory."
        )

    entry_records = tuple(
        item
        for item in values
        if isinstance(item, SnapshotEntry) and item.snapshot_edition == edition.reference
    )
    materializations = tuple(
        item
        for item in values
        if isinstance(item, SnapshotMaterializationRecord)
        and item.snapshot_edition == edition.reference
    )
    materialization_provenance = tuple(
        item
        for item in values
        if isinstance(item, SnapshotMaterializationProvenance)
        and item.snapshot_edition == edition.reference
    )
    omissions = tuple(
        item
        for item in values
        if isinstance(item, SnapshotOmission) and item.snapshot_edition == edition.reference
    )
    export_entry_ids = set(artifact.included_entry_ids)
    composition_placement_ids = set(composition.placement_ids)

    prepared_by_section: dict[str, list[StudentPortfolioPresentationItem]] = {
        section.section_id: [] for section in profile.sections
    }

    for entry_plan in plan.entry_plans:
        if entry_plan.section_id not in prepared_by_section:
            raise _inventory_mismatch(
                "Snapshot Entry Plan references a section outside the exact Profile Revision."
            )
        outcome = outcomes[entry_plan.entry_plan_id]
        placement: PortfolioPlacement | None = None
        if entry_plan.placement_id is not None:
            if entry_plan.placement_id not in composition_placement_ids:
                raise _inventory_mismatch(
                    "Snapshot Entry Plan Placement is not frozen by the exact Working Composition."
                )
            placement_id = entry_plan.placement_id

            def matches_placement(item: PortfolioPlacement) -> bool:
                return item.placement_id == placement_id

            placement = _one(
                values,
                PortfolioPlacement,
                matches_placement,
                label="Portfolio Placement",
            )
            if placement.section_id != entry_plan.section_id:
                raise _inventory_mismatch(
                    "Snapshot Entry Plan and Placement section identities disagree."
                )

        candidate = None
        if entry_plan.candidate_id is not None:
            candidate_id = entry_plan.candidate_id

            def matches_candidate(item: PortfolioCandidate) -> bool:
                return item.candidate_id == candidate_id

            candidate = _optional_one(
                values,
                PortfolioCandidate,
                matches_candidate,
                label="Portfolio Candidate",
            )

        presentation = None if placement is None else placement.presentation
        snapshot_entry: SnapshotEntry | None = None
        materialization: SnapshotMaterializationRecord | None = None
        omission: SnapshotOmission | None = None
        presentation_filename: str | None = None
        export_file_available = False

        if outcome.disposition in {"included", "reference_only"}:
            entry_plan_id = entry_plan.entry_plan_id

            def matches_materialization_provenance(
                item: SnapshotMaterializationProvenance,
            ) -> bool:
                return item.entry_plan_id == entry_plan_id

            provenance_record = _one(
                materialization_provenance,
                SnapshotMaterializationProvenance,
                matches_materialization_provenance,
                label="Snapshot materialization provenance",
            )
            materialization_id = provenance_record.materialization_id

            def matches_materialization(
                item: SnapshotMaterializationRecord,
            ) -> bool:
                return item.materialization_id == materialization_id

            materialization = _one(
                materializations,
                SnapshotMaterializationRecord,
                matches_materialization,
                label="Snapshot materialization",
            )
            if materialization.materialization_kind != entry_plan.materialization_kind:
                raise _inventory_mismatch(
                    "Snapshot materialization kind differs from the frozen Entry Plan."
                )

        if outcome.disposition == "included":
            if (
                materialization is None
                or outcome.materialization_id != materialization.materialization_id
            ):
                raise _inventory_mismatch(
                    "Included Snapshot outcome does not resolve its exact materialization."
                )
            included_materialization_id = materialization.materialization_id

            def matches_snapshot_entry(item: SnapshotEntry) -> bool:
                return item.materialization_id == included_materialization_id

            snapshot_entry = _one(
                entry_records,
                SnapshotEntry,
                matches_snapshot_entry,
                label="Snapshot Entry",
            )
            if (
                snapshot_entry.section_id != entry_plan.section_id
                or snapshot_entry.ordinal != entry_plan.ordinal
                or snapshot_entry.source_placement_id != entry_plan.placement_id
            ):
                raise _inventory_mismatch(
                    "Snapshot Entry differs from its frozen Entry Plan presentation position."
                )
            export_file_available = snapshot_entry.snapshot_entry_id in export_entry_ids
        elif outcome.disposition == "reference_only":
            if (
                materialization is None
                or materialization.materialization_kind != "reference_only"
            ):
                raise _inventory_mismatch(
                    "Reference-only Snapshot outcome lacks exact reference-only "
                    "materialization provenance."
                )
        elif outcome.disposition == "omitted_permitted":
            if outcome.omission_id is None:
                raise _inventory_mismatch(
                    "Permitted omission does not identify its Omission record."
                )
            omission_id = outcome.omission_id

            def matches_omission(item: SnapshotOmission) -> bool:
                return item.snapshot_omission_id == omission_id

            omission = _one(
                omissions,
                SnapshotOmission,
                matches_omission,
                label="Snapshot Omission",
            )
        else:
            raise _inventory_mismatch(
                "A sealed Portfolio presentation cannot contain failed_blocking Entry outcomes."
            )

        display_title = (
            None if snapshot_entry is None else snapshot_entry.display_title
        )
        if display_title is None and presentation is not None:
            display_title = presentation.display_title
        if display_title is None and candidate is not None:
            display_title = candidate.display_snapshot
        if display_title is None:
            display_title = _friendly_key(
                entry_plan.semantic_role or entry_plan.content_class
            )

        display_caption = (
            None if presentation is None else presentation.display_caption
        )
        source_credit = None if presentation is None else presentation.source_credit
        presentation_note = (
            None if presentation is None else presentation.presentation_note
        )
        if outcome.disposition == "reference_only" and presentation_note is None:
            presentation_note = (
                "This item is part of the portfolio record, but this edition does not "
                "include a portable file for it."
            )
        elif outcome.disposition == "omitted_permitted" and presentation_note is None:
            presentation_note = (
                "This item was intentionally not included in this edition under its "
                "audience rules."
            )
        elif (
            outcome.disposition == "included"
            and not export_file_available
            and presentation_note is None
        ):
            presentation_note = (
                "This item is sealed in the Snapshot but is not included in the verified "
                "technical export."
            )

        if snapshot_entry is not None and export_file_available:
            try:
                presentation_filename = build_bounded_presentation_filename(
                    display_title,
                    semantic_domain=_ITEM_FILENAME_DOMAIN,
                    semantic_identity={
                        "snapshot_series_id": edition.snapshot_series_id,
                        "edition_number": edition.edition_number,
                        "entry_plan_id": entry_plan.entry_plan_id,
                        "snapshot_entry_id": snapshot_entry.snapshot_entry_id,
                    },
                    extension=_extension(snapshot_entry.media_type),
                )
            except VitrinePathPolicyError as error:
                raise PortfolioPresentationPreparationError(
                    "portfolio_presentation.naming_failed",
                    "A student-facing Portfolio filename could not be bounded safely.",
                    stage="naming",
                ) from error

        prepared_by_section[entry_plan.section_id].append(
            StudentPortfolioPresentationItem(
                entry_plan_id=entry_plan.entry_plan_id,
                plan_position=entry_plan.plan_position,
                section_id=entry_plan.section_id,
                ordinal=entry_plan.ordinal,
                semantic_role=entry_plan.semantic_role,
                content_class=entry_plan.content_class,
                materialization_kind=entry_plan.materialization_kind,
                disposition=outcome.disposition,
                display_title=display_title,
                display_caption=display_caption,
                source_credit=source_credit,
                presentation_note=presentation_note,
                candidate_id=entry_plan.candidate_id,
                selection_id=entry_plan.selection_id,
                placement_id=entry_plan.placement_id,
                snapshot_entry_id=(
                    None if snapshot_entry is None else snapshot_entry.snapshot_entry_id
                ),
                materialization_id=(
                    None if materialization is None else materialization.materialization_id
                ),
                omission_id=None if omission is None else omission.snapshot_omission_id,
                technical_relative_path=(
                    None if snapshot_entry is None else snapshot_entry.relative_path
                ),
                media_type=None if snapshot_entry is None else snapshot_entry.media_type,
                byte_size=(
                    None if materialization is None else materialization.byte_size
                ),
                output_sha256=(
                    None
                    if materialization is None or materialization.output_digest is None
                    else materialization.output_digest.value
                ),
                export_file_available=export_file_available,
                presentation_filename=presentation_filename,
            )
        )

    sections: list[StudentPortfolioPresentationSection] = []
    section_directories: list[str] = []
    for section in profile.sections:
        items = tuple(
            sorted(
                prepared_by_section[section.section_id],
                key=lambda item: (item.ordinal, item.plan_position),
            )
        )
        filenames = tuple(
            item.presentation_filename
            for item in items
            if item.presentation_filename is not None
        )
        try:
            require_unique_presentation_components(filenames)
            directory_name = build_bounded_presentation_directory_name(
                section.label,
                semantic_domain=_SECTION_DIRECTORY_DOMAIN,
                semantic_identity={
                    "portfolio_profile_id": profile.portfolio_profile_id,
                    "profile_revision": profile.profile_revision,
                    "section_id": section.section_id,
                },
                ordinal=section.order,
            )
        except VitrinePathPolicyError as error:
            raise PortfolioPresentationPreparationError(
                "portfolio_presentation.naming_failed",
                "Student-facing Portfolio section naming failed the bounded path policy.",
                stage="naming",
            ) from error
        section_directories.append(directory_name)
        sections.append(
            StudentPortfolioPresentationSection(
                section_id=section.section_id,
                label=section.label,
                purpose=section.purpose,
                order=section.order,
                obligation=section.obligation,
                presentation_directory_name=directory_name,
                items=items,
            )
        )
    try:
        require_unique_presentation_components(tuple(section_directories))
    except VitrinePathPolicyError as error:
        raise PortfolioPresentationPreparationError(
            "portfolio_presentation.naming_failed",
            "Student-facing Portfolio section directories collide portably.",
            stage="naming",
        ) from error

    section_tuple = tuple(sections)
    all_items = tuple(item for section in section_tuple for item in section.items)
    portfolio_title = portfolio.title_snapshot or profile.label
    fingerprint = _fingerprint_value(
        edition=edition,
        seal=seal,
        artifact=artifact,
        audience=audience,
        profile=profile,
        composition=composition,
        sections=section_tuple,
    )
    return StudentPortfolioPresentationPreparation(
        contract_version=STUDENT_PORTFOLIO_PRESENTATION_CONTRACT_VERSION,
        observed_state_revision=current.state_revision,
        snapshot_edition=edition.reference,
        snapshot_export_artifact_id=artifact.snapshot_export_artifact_id,
        snapshot_manifest_sha256=seal.manifest_digest.value,
        snapshot_logical_inventory_sha256=seal.logical_inventory_digest.value,
        portfolio_id=edition.portfolio_id,
        portfolio_subject_id=edition.portfolio_subject_id,
        profile_binding_id=edition.profile_binding_id,
        profile_revision=edition.profile_revision,
        composition_revision=edition.composition_revision,
        audience_context_id=edition.audience_context_id,
        presentation_class=STUDENT_PORTFOLIO_PRESENTATION_CLASS,
        audience_presentation_class=audience.presentation_class,
        student_display_name=subject.display_name_snapshot,
        portfolio_title=portfolio_title,
        profile_label=profile.label,
        purpose=audience.purpose,
        technical_export_relative_path=artifact.relative_path,
        technical_export_inventory_sha256=artifact.directory_inventory_digest.value,
        custody_namespace=PORTFOLIO_PRESENTATION_CUSTODY_NAMESPACE,
        sections=section_tuple,
        file_item_count=sum(1 for item in all_items if item.export_file_available),
        reference_only_count=sum(
            1 for item in all_items if item.disposition == "reference_only"
        ),
        omitted_count=sum(
            1 for item in all_items if item.disposition == "omitted_permitted"
        ),
        preparation_fingerprint=fingerprint,
    )


__all__ = [
    "PORTFOLIO_PRESENTATION_CUSTODY_NAMESPACE",
    "PORTFOLIO_PRESENTATION_PREPARATION_ERROR_CODES",
    "STUDENT_PORTFOLIO_PRESENTATION_CLASS",
    "STUDENT_PORTFOLIO_PRESENTATION_CONTRACT_VERSION",
    "PortfolioPresentationPreparationError",
    "StudentPortfolioPresentationItem",
    "StudentPortfolioPresentationPreparation",
    "StudentPortfolioPresentationSection",
    "prepare_student_portfolio_presentation",
    "presentation_artifact_custody_relative_path",
]
