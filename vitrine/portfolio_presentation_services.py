"""Canonical build/reuse/recovery services for student Portfolio presentations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from vitrine.models import (
    ActorAttribution,
    DigestReference,
    PortfolioPresentationArtifact,
)
from vitrine.models.common import require_aware_datetime
from vitrine.models.errors import VitrineModelValidationError
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
    student_portfolio_presentation_artifact_id,
    student_portfolio_renderer_configuration_sha256,
)
from vitrine.portfolio_presentation_package import (
    PortfolioPresentationPackageError,
    clear_student_portfolio_file_package_staging,
    create_student_portfolio_file_package,
)
from vitrine.portfolio_presentation_pdf import (
    PortfolioPresentationPdfError,
    student_portfolio_pdf_renderer_configuration_sha256,
)
from vitrine.portfolio_presentation_verification import (
    PortfolioPresentationVerificationError,
    StudentPortfolioPackageVerification,
    verify_portfolio_presentation,
    verify_student_portfolio_file_package,
)
from vitrine.storage import (
    VitrineStorageError,
    VitrineStoragePartialSuccessError,
    commit_record_batch,
    load_current_records_with_state,
)
from vitrine.storage.errors import VitrineStorageValidationError
from vitrine.storage.paths import safe_vitrine_descendant

Clock = Callable[[], datetime]

STUDENT_PORTFOLIO_PRESENTATION_BUILD_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "portfolio_presentation_build.invalid_request",
        "portfolio_presentation_build.preparation_failed",
        "portfolio_presentation_build.renderer_unavailable",
        "portfolio_presentation_build.package_failed",
        "portfolio_presentation_build.existing_package_invalid",
        "portfolio_presentation_build.canonical_commit_failed",
        "portfolio_presentation_build.verification_failed",
    }
)


class PortfolioPresentationBuildError(RuntimeError):
    """Stable presentation build/recovery failure with exact next action metadata."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        stage: str,
        underlying_code: str | None = None,
        underlying_stage: str | None = None,
        presentation_artifact_id: str | None = None,
        next_safe_action: str | None = None,
    ) -> None:
        if code not in STUDENT_PORTFOLIO_PRESENTATION_BUILD_ERROR_CODES:
            raise ValueError(f"unsupported Portfolio presentation build code: {code}")
        self.code = code
        self.stage = stage
        self.underlying_code = underlying_code
        self.underlying_stage = underlying_stage
        self.presentation_artifact_id = presentation_artifact_id
        self.next_safe_action = next_safe_action
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class PortfolioPresentationBuildResult:
    state_revision: int
    presentation_artifact_id: str
    disposition: str
    relative_path: str
    html_relative_path: str
    printable_pdf_relative_path: str
    presentation_manifest_sha256: str
    package_inventory_sha256: str
    verified_file_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.state_revision <= 0:
            raise ValueError("presentation result state_revision must be positive")
        if self.disposition not in {"created", "existing", "recovered"}:
            raise ValueError("unsupported presentation build disposition")


def _clock() -> datetime:
    return datetime.now(timezone.utc)


def _now(clock: Clock) -> datetime:
    try:
        return require_aware_datetime(clock(), "clock").astimezone(timezone.utc)
    except VitrineModelValidationError as error:
        raise PortfolioPresentationBuildError(
            "portfolio_presentation_build.invalid_request",
            "Presentation build clock must return an aware datetime.",
            stage="clock",
        ) from error


def _load_state(root: str | Path) -> tuple[int, tuple[object, ...]]:
    try:
        current, records = load_current_records_with_state(root)
    except VitrineStorageError as error:
        raise PortfolioPresentationBuildError(
            "portfolio_presentation_build.canonical_commit_failed",
            "Canonical Vitrine state is unavailable for presentation publication.",
            stage="canonical",
            next_safe_action="inspect_canonical_storage_then_resume_presentation",
        ) from error
    return current.state_revision, tuple(records)


def _existing_artifact(
    records: tuple[object, ...],
    presentation_artifact_id: str,
) -> PortfolioPresentationArtifact | None:
    matches = tuple(
        item
        for item in records
        if isinstance(item, PortfolioPresentationArtifact)
        and item.presentation_artifact_id == presentation_artifact_id
    )
    if len(matches) > 1:
        raise PortfolioPresentationBuildError(
            "portfolio_presentation_build.canonical_commit_failed",
            "Presentation Artifact identity is ambiguous in canonical state.",
            stage="canonical",
            presentation_artifact_id=presentation_artifact_id,
            next_safe_action="inspect_canonical_storage",
        )
    return None if not matches else matches[0]


def _predecessor_id(
    records: tuple[object, ...],
    preparation: StudentPortfolioPresentationPreparation,
    presentation_artifact_id: str,
) -> str | None:
    matches = tuple(
        item
        for item in records
        if isinstance(item, PortfolioPresentationArtifact)
        and item.presentation_artifact_id != presentation_artifact_id
        and item.snapshot_edition == preparation.snapshot_edition
        and item.presentation_class == STUDENT_PORTFOLIO_PRESENTATION_CLASS
    )
    if not matches:
        return None
    ordered = sorted(
        matches,
        key=lambda item: (item.generated_at, item.presentation_artifact_id),
    )
    return ordered[-1].presentation_artifact_id


def _result(
    state_revision: int,
    artifact: PortfolioPresentationArtifact,
    package: StudentPortfolioPackageVerification,
    *,
    disposition: str,
) -> PortfolioPresentationBuildResult:
    return PortfolioPresentationBuildResult(
        state_revision=state_revision,
        presentation_artifact_id=artifact.presentation_artifact_id,
        disposition=disposition,
        relative_path=artifact.relative_path,
        html_relative_path=artifact.html_relative_path,
        printable_pdf_relative_path=artifact.printable_pdf_relative_path,
        presentation_manifest_sha256=package.presentation_manifest_sha256,
        package_inventory_sha256=package.package_inventory_sha256,
        verified_file_paths=package.verified_file_paths,
    )


def _verify_existing(
    root: str | Path,
    artifact: PortfolioPresentationArtifact,
    *,
    state_revision: int,
) -> PortfolioPresentationBuildResult:
    try:
        verification = verify_portfolio_presentation(
            root,
            presentation_artifact_id=artifact.presentation_artifact_id,
        )
        preparation = prepare_student_portfolio_presentation(
            root,
            snapshot_series_id=artifact.snapshot_edition.snapshot_series_id,
            edition_number=artifact.snapshot_edition.edition_number,
            snapshot_export_artifact_id=artifact.snapshot_export_artifact_id,
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
    except (PortfolioPresentationVerificationError, PortfolioPresentationPreparationError) as error:
        raise PortfolioPresentationBuildError(
            "portfolio_presentation_build.verification_failed",
            "Existing canonical student Portfolio presentation no longer verifies.",
            stage="verification",
            underlying_code=getattr(error, "code", None),
            underlying_stage=getattr(error, "stage", None),
            presentation_artifact_id=artifact.presentation_artifact_id,
            next_safe_action="inspect_presentation_custody",
        ) from error
    if verification.presentation_artifact_id != artifact.presentation_artifact_id:
        raise PortfolioPresentationBuildError(
            "portfolio_presentation_build.verification_failed",
            "Presentation verification returned a different artifact identity.",
            stage="verification",
            presentation_artifact_id=artifact.presentation_artifact_id,
            next_safe_action="inspect_presentation_custody",
        )
    return _result(state_revision, artifact, package, disposition="existing")


def _package_exists(
    root: str | Path,
    presentation_artifact_id: str,
) -> bool:
    try:
        relative = presentation_artifact_custody_relative_path(
            presentation_artifact_id
        )
        path = safe_vitrine_descendant(root, relative)
    except (PortfolioPresentationPreparationError, VitrineStorageValidationError) as error:
        raise PortfolioPresentationBuildError(
            "portfolio_presentation_build.invalid_request",
            "Presentation custody identity cannot be resolved safely.",
            stage="custody",
            presentation_artifact_id=presentation_artifact_id,
        ) from error
    try:
        return path.exists()
    except OSError as error:
        raise PortfolioPresentationBuildError(
            "portfolio_presentation_build.package_failed",
            "Presentation custody could not be inspected safely.",
            stage="custody",
            presentation_artifact_id=presentation_artifact_id,
            next_safe_action="inspect_presentation_custody",
        ) from error


def _verify_unpublished_package(
    root: str | Path,
    preparation: StudentPortfolioPresentationPreparation,
    *,
    presentation_artifact_id: str,
    renderer_configuration_sha256: str,
) -> StudentPortfolioPackageVerification:
    try:
        package = verify_student_portfolio_file_package(
            root,
            preparation,
            presentation_artifact_id=presentation_artifact_id,
        )
    except PortfolioPresentationVerificationError as error:
        raise PortfolioPresentationBuildError(
            "portfolio_presentation_build.existing_package_invalid",
            "Published presentation custody exists but does not verify exactly.",
            stage="package_verification",
            underlying_code=error.code,
            underlying_stage=error.stage,
            presentation_artifact_id=presentation_artifact_id,
            next_safe_action="inspect_presentation_custody",
        ) from error
    if package.renderer_configuration_sha256 != renderer_configuration_sha256:
        raise PortfolioPresentationBuildError(
            "portfolio_presentation_build.existing_package_invalid",
            "Published presentation renderer configuration differs from this exact build.",
            stage="package_verification",
            presentation_artifact_id=presentation_artifact_id,
            next_safe_action="inspect_presentation_custody",
        )
    return package


def build_student_portfolio_presentation(
    root: str | Path,
    *,
    snapshot_series_id: str,
    edition_number: int,
    snapshot_export_artifact_id: str,
    generated_by: ActorAttribution,
    clock: Clock = _clock,
) -> PortfolioPresentationBuildResult:
    """Create/reuse one exact presentation, persist it canonically, then verify it."""

    if not isinstance(generated_by, ActorAttribution):
        raise PortfolioPresentationBuildError(
            "portfolio_presentation_build.invalid_request",
            "Presentation generation requires exact actor attribution.",
            stage="request",
        )
    try:
        preparation = prepare_student_portfolio_presentation(
            root,
            snapshot_series_id=snapshot_series_id,
            edition_number=edition_number,
            snapshot_export_artifact_id=snapshot_export_artifact_id,
        )
    except PortfolioPresentationPreparationError as error:
        raise PortfolioPresentationBuildError(
            "portfolio_presentation_build.preparation_failed",
            "Exact student Portfolio presentation preparation failed.",
            stage="preparation",
            underlying_code=error.code,
            underlying_stage=error.stage,
            next_safe_action="review_presentation_readiness",
        ) from error
    try:
        pdf_configuration = student_portfolio_pdf_renderer_configuration_sha256()
    except PortfolioPresentationPdfError as error:
        raise PortfolioPresentationBuildError(
            "portfolio_presentation_build.renderer_unavailable",
            "Printable Portfolio renderer is unavailable for this exact presentation.",
            stage="renderer",
            underlying_code=error.code,
            underlying_stage=error.stage,
            next_safe_action="install_vitrine_paper_dependencies",
        ) from error
    renderer_configuration = student_portfolio_renderer_configuration_sha256(
        pdf_renderer_configuration_sha256=pdf_configuration
    )
    artifact_id = student_portfolio_presentation_artifact_id(
        preparation_fingerprint=preparation.preparation_fingerprint,
        renderer_configuration_sha256=renderer_configuration,
    )

    state_revision, records = _load_state(root)
    existing = _existing_artifact(records, artifact_id)
    if existing is not None:
        return _verify_existing(root, existing, state_revision=state_revision)

    recovered_package = _package_exists(root, artifact_id)
    if recovered_package:
        package = _verify_unpublished_package(
            root,
            preparation,
            presentation_artifact_id=artifact_id,
            renderer_configuration_sha256=renderer_configuration,
        )
    else:
        try:
            create_student_portfolio_file_package(
                root,
                preparation,
                presentation_artifact_id=artifact_id,
            )
        except PortfolioPresentationPackageError as error:
            if error.code == "portfolio_presentation_package.custody_conflict":
                package = _verify_unpublished_package(
                    root,
                    preparation,
                    presentation_artifact_id=artifact_id,
                    renderer_configuration_sha256=renderer_configuration,
                )
                recovered_package = True
            else:
                if error.code == "portfolio_presentation_package.staging_conflict":
                    next_action = "inspect_presentation_staging_then_resume"
                elif error.code == "portfolio_presentation_package.durability_uncertain":
                    next_action = "inspect_presentation_custody_then_resume"
                else:
                    next_action = "resume_presentation_existing_edition"
                raise PortfolioPresentationBuildError(
                    "portfolio_presentation_build.package_failed",
                    "Student Portfolio presentation package could not be published.",
                    stage="package",
                    underlying_code=error.code,
                    underlying_stage=error.stage,
                    presentation_artifact_id=artifact_id,
                    next_safe_action=next_action,
                ) from error
        else:
            package = _verify_unpublished_package(
                root,
                preparation,
                presentation_artifact_id=artifact_id,
                renderer_configuration_sha256=renderer_configuration,
            )

    # Re-read canonical state after potentially expensive deterministic rendering.
    state_revision, records = _load_state(root)
    existing = _existing_artifact(records, artifact_id)
    if existing is not None:
        return _verify_existing(root, existing, state_revision=state_revision)

    artifact = PortfolioPresentationArtifact(
        presentation_artifact_id=artifact_id,
        snapshot_edition=preparation.snapshot_edition,
        snapshot_export_artifact_id=preparation.snapshot_export_artifact_id,
        portfolio_id=preparation.portfolio_id,
        portfolio_subject_id=preparation.portfolio_subject_id,
        profile_binding_id=preparation.profile_binding_id,
        profile_revision=preparation.profile_revision,
        audience_context_id=preparation.audience_context_id,
        presentation_class=preparation.presentation_class,
        presentation_contract_version=preparation.contract_version,
        renderer_id=STUDENT_PORTFOLIO_PRESENTATION_RENDERER_ID,
        renderer_version=STUDENT_PORTFOLIO_PRESENTATION_RENDERER_VERSION,
        renderer_contract_version=(
            STUDENT_PORTFOLIO_PRESENTATION_RENDERER_CONTRACT_VERSION
        ),
        renderer_configuration_digest=DigestReference(
            value=renderer_configuration
        ),
        relative_path=package.relative_path,
        presentation_manifest_relative_path=(
            package.presentation_manifest_relative_path
        ),
        presentation_manifest_digest=DigestReference(
            value=package.presentation_manifest_sha256
        ),
        html_relative_path=package.html_relative_path,
        html_digest=DigestReference(value=package.html_sha256),
        printable_pdf_relative_path=package.printable_pdf_relative_path,
        printable_pdf_digest=DigestReference(
            value=package.printable_pdf_sha256
        ),
        package_inventory_digest=DigestReference(
            value=package.package_inventory_sha256
        ),
        generated_at=_now(clock),
        generated_by=generated_by,
        predecessor_presentation_artifact_id=_predecessor_id(
            records,
            preparation,
            artifact_id,
        ),
    )
    try:
        committed = commit_record_batch(
            root,
            (artifact,),
            expected_state_revision=state_revision,
        )
    except VitrineStorageError as error:
        # A concurrent writer may have published the exact same semantic artifact.
        try:
            observed_revision, observed_records = _load_state(root)
            observed = _existing_artifact(observed_records, artifact_id)
        except PortfolioPresentationBuildError:
            observed = None
            observed_revision = state_revision
        if observed is not None:
            return _verify_existing(
                root,
                observed,
                state_revision=observed_revision,
            )
        next_action = (
            "inspect_canonical_storage_then_resume_presentation"
            if isinstance(error, VitrineStoragePartialSuccessError)
            else "resume_presentation_existing_edition"
        )
        raise PortfolioPresentationBuildError(
            "portfolio_presentation_build.canonical_commit_failed",
            "Presentation package is durable, but canonical publication did not complete.",
            stage="canonical",
            presentation_artifact_id=artifact_id,
            next_safe_action=next_action,
        ) from error

    try:
        verification = verify_portfolio_presentation(
            root,
            presentation_artifact_id=artifact_id,
        )
    except PortfolioPresentationVerificationError as error:
        raise PortfolioPresentationBuildError(
            "portfolio_presentation_build.verification_failed",
            "Canonical student Portfolio presentation failed post-publication verification.",
            stage="verification",
            underlying_code=error.code,
            underlying_stage=error.stage,
            presentation_artifact_id=artifact_id,
            next_safe_action="inspect_presentation_custody",
        ) from error
    if verification.presentation_artifact_id != artifact_id:
        raise PortfolioPresentationBuildError(
            "portfolio_presentation_build.verification_failed",
            "Post-publication verification returned a different presentation identity.",
            stage="verification",
            presentation_artifact_id=artifact_id,
            next_safe_action="inspect_presentation_custody",
        )
    disposition = "recovered" if recovered_package else "created"
    return _result(
        committed.state_revision,
        artifact,
        package,
        disposition=disposition,
    )


def resume_student_portfolio_presentation(
    root: str | Path,
    *,
    snapshot_series_id: str,
    edition_number: int,
    snapshot_export_artifact_id: str,
    generated_by: ActorAttribution,
    clock: Clock = _clock,
) -> PortfolioPresentationBuildResult:
    """Resume only the presentation stage from one exact durable Edition/Export."""

    try:
        return build_student_portfolio_presentation(
            root,
            snapshot_series_id=snapshot_series_id,
            edition_number=edition_number,
            snapshot_export_artifact_id=snapshot_export_artifact_id,
            generated_by=generated_by,
            clock=clock,
        )
    except PortfolioPresentationBuildError as error:
        if (
            error.underlying_code
            != "portfolio_presentation_package.staging_conflict"
            or error.presentation_artifact_id is None
        ):
            raise
        try:
            clear_student_portfolio_file_package_staging(
                root,
                presentation_artifact_id=error.presentation_artifact_id,
            )
        except PortfolioPresentationPackageError as cleanup_error:
            raise PortfolioPresentationBuildError(
                "portfolio_presentation_build.package_failed",
                "Exact presentation staging could not be cleared for resume.",
                stage="resume_cleanup",
                underlying_code=cleanup_error.code,
                underlying_stage=cleanup_error.stage,
                presentation_artifact_id=error.presentation_artifact_id,
                next_safe_action="inspect_presentation_staging",
            ) from cleanup_error
        return build_student_portfolio_presentation(
            root,
            snapshot_series_id=snapshot_series_id,
            edition_number=edition_number,
            snapshot_export_artifact_id=snapshot_export_artifact_id,
            generated_by=generated_by,
            clock=clock,
        )


__all__ = [
    "STUDENT_PORTFOLIO_PRESENTATION_BUILD_ERROR_CODES",
    "PortfolioPresentationBuildError",
    "PortfolioPresentationBuildResult",
    "build_student_portfolio_presentation",
    "resume_student_portfolio_presentation",
]
