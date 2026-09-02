"""Pure live Concord Score projection for Vitrine.

Issue #61 consumes only the already validated public Concord Academic Result
Manifest returned by the installed reader. Slice 2 preserves Concord Activity,
Criterion, Scale, Score, Evidence Link, Moderation, privacy, and Artifact-reference
semantics. It performs no manifest parsing, workspace access, Artifact I/O, Score
selection, Grade/proficiency inference, or Candidate policy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from importlib import import_module
from typing import Final, Protocol, TypeAlias, cast

from vitrine.models.sources import (
    ProducerSourceReference,
    SourceArtifactReference,
    SourcePrivacyMetadata,
)
from vitrine.producer_adapters import (
    ProducerManifestReader,
    ProducerProjectionAdapterDeclaration,
    ProducerProjectionBatch,
    ProducerProjectionError,
    ProjectedProducerRelationship,
    ProjectedProducerSource,
    ProjectionDisplaySnapshot,
    ProjectionField,
)
from vitrine.producer_reader_services import (
    INSTALLED_PRODUCER_READER_CONTRACT_VERSION,
    build_audited_installed_producer_reader,
)
from vitrine.released_producer_contracts import (
    CONCORD_LIVE_SUPPORT_KEY,
    RELEASED_PRODUCER_CONTRACT_BY_MODULE,
)

CONCORD_LIVE_ADAPTER_ID: Final[str] = "vitrine_concord_live_adapter"
CONCORD_LIVE_ADAPTER_CONTRACT_VERSION: Final[str] = (
    "vitrine_concord_live_adapter_v1"
)
CONCORD_LIVE_PROJECTION_CONTRACT_VERSION: Final[str] = (
    "vitrine_candidate_projection_v1"
)
CONCORD_LIVE_DIAGNOSTIC_CONTRACT_VERSION: Final[str] = (
    "vitrine_adapter_diagnostic_v1"
)
CONCORD_SCORE_PROJECTION_KIND: Final[str] = "concord:score_summary"
CONCORD_SCORE_MEDIA_TYPE: Final[str] = (
    "application/vnd.pds.vitrine.concord-score-summary+json"
)
CONCORD_EVIDENCE_LINK_PROJECTION_KIND: Final[str] = "concord:evidence_link_summary"
CONCORD_EVIDENCE_LINK_MEDIA_TYPE: Final[str] = (
    "application/vnd.pds.vitrine.concord-evidence-link-summary+json"
)
CONCORD_ARTIFACT_PROJECTION_KIND: Final[str] = "concord:artifact_evidence"
CONCORD_ARTIFACT_REPRESENTATION_KIND: Final[str] = "concord:returned_artifact_pdf"
CONCORD_ARTIFACT_MEDIA_TYPE: Final[str] = "application/pdf"
CONCORD_PRIVACY_POLICY_REFERENCE: Final[str] = (
    "vitrine_live_concord_minimum_necessary_v1"
)

_CONCORD_AUDIT = RELEASED_PRODUCER_CONTRACT_BY_MODULE["concord"]
_CONCORD_READER_DESCRIPTOR = build_audited_installed_producer_reader(
    "concord"
).descriptor

CONCORD_LIVE_ADAPTER_DECLARATION: Final[ProducerProjectionAdapterDeclaration] = (
    ProducerProjectionAdapterDeclaration(
        adapter_id=CONCORD_LIVE_ADAPTER_ID,
        adapter_contract_version=CONCORD_LIVE_ADAPTER_CONTRACT_VERSION,
        candidate_projection_contract_version=CONCORD_LIVE_PROJECTION_CONTRACT_VERSION,
        support_key=CONCORD_LIVE_SUPPORT_KEY,
        public_reader_id=_CONCORD_READER_DESCRIPTOR.public_reader_id,
        reader_contract_version=INSTALLED_PRODUCER_READER_CONTRACT_VERSION,
        reader_package_identity=_CONCORD_AUDIT.distribution_name,
        supported_source_families=("collaborative_work", "score_summary"),
        supported_representation_families=("collaborative_work", "result_summary"),
        diagnostic_contract_version=CONCORD_LIVE_DIAGNOSTIC_CONTRACT_VERSION,
        integration_kind="live",
    )
)

JsonScalar: TypeAlias = str | int | float | bool


class _RecordSet(Protocol):
    record_set_id: str
    revision: int


class _ModuleWork(Protocol):
    module_id: str
    class_id: str
    work_id: str


class _ModuleRecord(Protocol):
    module_id: str
    record_kind: str
    record_id: str
    contract_version: str | None


class _Actor(Protocol):
    actor_kind: str
    actor_id: str
    owning_system: str


class _ManifestProjection(Protocol):
    source_snapshot_revision: int
    projection_digest_algorithm: str
    projection_digest: str
    generated_by: _Actor
    revision_reason: str


class _ActivityContext(Protocol):
    activity_id: str
    class_id: str
    title: str
    scoring_orientation: str
    standards_profile_id: str | None
    focus_standard_ids: tuple[str, ...]
    criterion_set_ids: tuple[str, ...]


class _CriterionSet(Protocol):
    criterion_set_id: str
    lineage_id: str
    revision: int
    criterion_set_kind: str
    scope: str
    criterion_ids: tuple[str, ...]
    status: str
    supersedes_criterion_set_id: str | None
    standards_profile_id: str | None


class _Criterion(Protocol):
    criterion_id: str
    criterion_set_id: str
    key: str
    label: str
    definition: str
    criterion_kind: str
    supported_target_kinds: tuple[str, ...]
    status: str
    standard_id: str | None
    alignment_standard_ids: tuple[str, ...]
    default_scoring_scale_id: str | None


class _ScaleLevel(Protocol):
    value: JsonScalar
    label: str
    meaning: str
    position: int | None
    description: str | None


class _ScoringScale(Protocol):
    scoring_scale_id: str
    lineage_id: str
    name: str
    revision: int
    scale_type: str
    levels: tuple[_ScaleLevel, ...]
    status: str
    supersedes_scoring_scale_id: str | None


class _TargetReference(Protocol):
    target_kind: str
    target_id: str
    owning_system: str
    contract_version: str | None


class _SubjectReference(Protocol):
    subject_kind: str
    subject_id: str
    owning_system: str
    contract_version: str | None


class _CorePublicationReference(Protocol):
    publication_id: str
    publication_schema_version: str | None


class _EvidenceLocator(Protocol):
    page_number: int | None
    source_page_index: int | None
    section_label: str | None
    row_label: str | None
    column_label: str | None
    participant_label: str | None
    session_id: str | None


class _EvidenceReference(Protocol):
    evidence_kind: str
    owning_system: str
    record_id: str
    contract_version: str | None
    source_publication_reference: _CorePublicationReference | None
    immutable_source_version: str | None
    locator: _EvidenceLocator | None
    subject_context: tuple[_SubjectReference, ...]
    moderation_requirement: str | None


class _ScoreEvidenceLink(Protocol):
    score_evidence_link_id: str
    score_record_id: str
    evidence_reference: _EvidenceReference
    evidence_locator: _EvidenceLocator | None
    subject_context: tuple[_SubjectReference, ...]
    relevance_description: str
    significance: str | None
    moderation_record_id: str | None
    status: str
    supersedes_score_evidence_link_id: str | None


class _Moderation(Protocol):
    moderation_record_id: str
    target_evidence_reference: _EvidenceReference
    target_subject_references: tuple[_SubjectReference, ...]
    status: str
    permitted_use: str
    qualification: str | None
    supersedes_moderation_record_id: str | None
    current_state: str


class _StatusReason(Protocol):
    reason_code: str
    recorded_by: _Actor
    recorded_at: datetime
    related_record: _ModuleRecord | None


class _Score(Protocol):
    score_record_id: str
    activity_id: str
    session_id: str | None
    target_reference: _TargetReference
    criterion_id: str
    score_kind: str
    standard_id: str | None
    scoring_scale_id: str
    disposition: str
    value: JsonScalar | None
    basis: str
    scorer: _Actor
    scored_at: datetime
    moderation_complete: bool
    status_reason: _StatusReason | None
    supersedes_score_record_id: str | None
    current_state: str


class _StandardsResult(Protocol):
    score_record_id: str
    standard_id: str


class _Privacy(Protocol):
    classification: str
    audience_references: tuple[_SubjectReference, ...]
    policy_reference: _ModuleRecord | None
    inherited_from: _ModuleRecord | None


class _AcademicResultManifest(Protocol):
    record_type: str
    contract_version: str
    producer_module_id: str
    generated_at: datetime
    record_set: _RecordSet
    work: _ModuleWork
    source_activity: _ModuleRecord
    projection: _ManifestProjection
    activity_context: _ActivityContext
    criterion_sets: tuple[_CriterionSet, ...]
    criteria: tuple[_Criterion, ...]
    scoring_scales: tuple[_ScoringScale, ...]
    scores: tuple[_Score, ...]
    score_evidence_links: tuple[_ScoreEvidenceLink, ...]
    moderation_records: tuple[_Moderation, ...]
    standards_result_projection: tuple[_StandardsResult, ...]
    privacy: _Privacy


def _projection_error(code: str, stage: str, message: str) -> ProducerProjectionError:
    return ProducerProjectionError(
        code,
        stage,
        message,
        adapter_id=CONCORD_LIVE_ADAPTER_ID,
        producer_module_id="concord",
        publication_kind=CONCORD_LIVE_SUPPORT_KEY.publication_kind,
        manifest_contract_version=CONCORD_LIVE_SUPPORT_KEY.manifest_contract_version,
    )


def _canonical_timestamp(value: datetime) -> str:
    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _native_scalar_type(value: JsonScalar | None) -> str:
    if value is None:
        return "absent"
    if type(value) is bool:
        return "bool"
    if type(value) is int:
        return "int"
    if type(value) is float:
        return "float"
    if type(value) is str:
        return "string"
    raise TypeError("Concord native Score/Scale value has an unsupported scalar type.")



def _reference_text(reference: _ModuleRecord | None) -> str | None:
    if reference is None:
        return None
    return ":".join(
        (
            reference.module_id,
            reference.record_kind,
            reference.record_id,
            reference.contract_version or "<none>",
        )
    )


def _subject_fields(
    prefix: str,
    subjects: tuple[_SubjectReference, ...],
) -> tuple[ProjectionField, ...]:
    return (
        ProjectionField(
            key=f"{prefix}_kinds",
            value=tuple(subject.subject_kind for subject in subjects),
        ),
        ProjectionField(
            key=f"{prefix}_ids",
            value=tuple(subject.subject_id for subject in subjects),
        ),
        ProjectionField(
            key=f"{prefix}_owning_systems",
            value=tuple(subject.owning_system for subject in subjects),
        ),
        ProjectionField(
            key=f"{prefix}_contract_versions",
            value=tuple(subject.contract_version for subject in subjects),
        ),
    )


def _privacy_fields(manifest: _AcademicResultManifest) -> tuple[ProjectionField, ...]:
    privacy = manifest.privacy
    return (
        ProjectionField(
            key="producer_privacy_classification",
            value=privacy.classification,
        ),
        ProjectionField(
            key="producer_privacy_policy_reference",
            value=_reference_text(privacy.policy_reference),
        ),
        ProjectionField(
            key="producer_privacy_inherited_from",
            value=_reference_text(privacy.inherited_from),
        ),
    ) + _subject_fields("producer_privacy_audience", privacy.audience_references)


def _locator_fields(
    prefix: str,
    locator: _EvidenceLocator | None,
) -> tuple[ProjectionField, ...]:
    return (
        ProjectionField(
            key=f"{prefix}_page_number",
            value=locator.page_number if locator is not None else None,
        ),
        ProjectionField(
            key=f"{prefix}_source_page_index",
            value=locator.source_page_index if locator is not None else None,
        ),
        ProjectionField(
            key=f"{prefix}_section_label",
            value=locator.section_label if locator is not None else None,
        ),
        ProjectionField(
            key=f"{prefix}_row_label",
            value=locator.row_label if locator is not None else None,
        ),
        ProjectionField(
            key=f"{prefix}_column_label",
            value=locator.column_label if locator is not None else None,
        ),
        ProjectionField(
            key=f"{prefix}_participant_label",
            value=locator.participant_label if locator is not None else None,
        ),
        ProjectionField(
            key=f"{prefix}_session_id",
            value=locator.session_id if locator is not None else None,
        ),
    )


def _evidence_reference_fields(
    evidence: _EvidenceReference,
) -> tuple[ProjectionField, ...]:
    publication = evidence.source_publication_reference
    return (
        ProjectionField(key="evidence_kind", value=evidence.evidence_kind),
        ProjectionField(
            key="evidence_owning_system", value=evidence.owning_system
        ),
        ProjectionField(key="evidence_record_id", value=evidence.record_id),
        ProjectionField(
            key="evidence_contract_version", value=evidence.contract_version
        ),
        ProjectionField(
            key="evidence_source_publication_id",
            value=(
                publication.publication_id if publication is not None else None
            ),
        ),
        ProjectionField(
            key="evidence_source_publication_schema_version",
            value=(
                publication.publication_schema_version
                if publication is not None
                else None
            ),
        ),
        ProjectionField(
            key="evidence_immutable_source_version",
            value=evidence.immutable_source_version,
        ),
        ProjectionField(
            key="evidence_moderation_requirement",
            value=evidence.moderation_requirement,
        ),
    ) + _locator_fields(
        "evidence_reference_locator", evidence.locator
    ) + _subject_fields("evidence_reference_subject", evidence.subject_context)


def _moderation_fields(
    moderation: _Moderation | None,
) -> tuple[ProjectionField, ...]:
    if moderation is None:
        empty: tuple[_SubjectReference, ...] = ()
        return (
            ProjectionField(key="moderation_record_id", value=None),
            ProjectionField(key="moderation_status", value=None),
            ProjectionField(key="moderation_permitted_use", value=None),
            ProjectionField(key="moderation_qualification", value=None),
            ProjectionField(
                key="moderation_supersedes_record_id", value=None
            ),
            ProjectionField(key="moderation_current_state", value=None),
            ProjectionField(
                key="moderation_target_evidence_kind", value=None
            ),
            ProjectionField(
                key="moderation_target_evidence_owning_system", value=None
            ),
            ProjectionField(
                key="moderation_target_evidence_record_id", value=None
            ),
            ProjectionField(
                key="moderation_target_evidence_contract_version", value=None
            ),
            ProjectionField(
                key="moderation_target_evidence_immutable_source_version",
                value=None,
            ),
            ProjectionField(
                key="moderation_target_evidence_source_publication_id",
                value=None,
            ),
        ) + _subject_fields("moderation_target_subject", empty)

    target = moderation.target_evidence_reference
    return (
        ProjectionField(
            key="moderation_record_id", value=moderation.moderation_record_id
        ),
        ProjectionField(key="moderation_status", value=moderation.status),
        ProjectionField(
            key="moderation_permitted_use", value=moderation.permitted_use
        ),
        ProjectionField(
            key="moderation_qualification", value=moderation.qualification
        ),
        ProjectionField(
            key="moderation_supersedes_record_id",
            value=moderation.supersedes_moderation_record_id,
        ),
        ProjectionField(
            key="moderation_current_state", value=moderation.current_state
        ),
        ProjectionField(
            key="moderation_target_evidence_kind",
            value=target.evidence_kind,
        ),
        ProjectionField(
            key="moderation_target_evidence_owning_system",
            value=target.owning_system,
        ),
        ProjectionField(
            key="moderation_target_evidence_record_id",
            value=target.record_id,
        ),
        ProjectionField(
            key="moderation_target_evidence_contract_version",
            value=target.contract_version,
        ),
        ProjectionField(
            key="moderation_target_evidence_immutable_source_version",
            value=target.immutable_source_version,
        ),
        ProjectionField(
            key="moderation_target_evidence_source_publication_id",
            value=(
                target.source_publication_reference.publication_id
                if target.source_publication_reference is not None
                else None
            ),
        ),
    ) + _subject_fields(
        "moderation_target_subject", moderation.target_subject_references
    )


def _links_for_score(
    links: tuple[_ScoreEvidenceLink, ...],
    score_record_id: str,
) -> tuple[_ScoreEvidenceLink, ...]:
    return tuple(link for link in links if link.score_record_id == score_record_id)


def _score_link_fields(
    links: tuple[_ScoreEvidenceLink, ...],
) -> tuple[ProjectionField, ...]:
    return (
        ProjectionField(
            key="score_evidence_link_ids",
            value=tuple(link.score_evidence_link_id for link in links),
        ),
        ProjectionField(
            key="score_evidence_link_statuses",
            value=tuple(link.status for link in links),
        ),
        ProjectionField(
            key="score_evidence_link_significance",
            value=tuple(link.significance for link in links),
        ),
        ProjectionField(
            key="score_evidence_kinds",
            value=tuple(link.evidence_reference.evidence_kind for link in links),
        ),
        ProjectionField(
            key="score_evidence_owning_systems",
            value=tuple(
                link.evidence_reference.owning_system for link in links
            ),
        ),
        ProjectionField(
            key="score_evidence_record_ids",
            value=tuple(link.evidence_reference.record_id for link in links),
        ),
        ProjectionField(
            key="score_evidence_moderation_record_ids",
            value=tuple(link.moderation_record_id for link in links),
        ),
    )


def _evidence_link_privacy(
    manifest: _AcademicResultManifest,
    link: _ScoreEvidenceLink,
) -> SourcePrivacyMetadata:
    evidence = link.evidence_reference
    artifact = (
        evidence.owning_system == "concord"
        and evidence.evidence_kind in {"artifact_instance", "artifact_page"}
    )
    subjects = link.subject_context or evidence.subject_context
    single_student = (
        not artifact
        and len(subjects) == 1
        and subjects[0].subject_kind == "core_student"
    )
    privacy = manifest.privacy
    collaborative = (
        privacy.classification in {"group_and_teacher", "classroom_shared"}
        or len(privacy.audience_references) > 1
        or any(
            subject.subject_kind != "core_student"
            for subject in privacy.audience_references
        )
    )
    multi_subject = artifact or not single_student or collaborative
    return SourcePrivacyMetadata(
        classification=manifest.privacy.classification,
        subject_scope="single_subject" if single_student else "multi_subject",
        metadata_visibility="internal",
        collaborator_information_present=artifact or multi_subject,
        third_party_information_present=evidence.owning_system != "concord",
        rights_review_required=False,
        redaction_review_required=artifact or multi_subject,
        multi_subject_review_required=artifact or multi_subject,
        minimum_necessary_projection_required=True,
        policy_reference=CONCORD_PRIVACY_POLICY_REFERENCE,
    )


def _artifact_capable(link: _ScoreEvidenceLink) -> bool:
    evidence = link.evidence_reference
    return (
        evidence.owning_system == "concord"
        and evidence.evidence_kind in {"artifact_instance", "artifact_page"}
    )


def _score_relationships(score: _Score) -> tuple[ProjectedProducerRelationship, ...]:
    target = score.target_reference
    if target.target_kind == "core_student":
        return (
            ProjectedProducerRelationship(
                source_subject_kind="core_student",
                source_subject_id=target.target_id,
                relationship_kind="individual_score_target",
                relationship_authority="concord",
                supporting_source_reference=score.score_record_id,
            ),
        )
    if target.target_kind == "concord_group":
        return (
            ProjectedProducerRelationship(
                source_subject_kind="concord_group",
                source_subject_id=target.target_id,
                relationship_kind="group_score_target",
                relationship_authority="concord",
                supporting_source_reference=score.score_record_id,
            ),
        )
    return ()


def _score_privacy(
    manifest: _AcademicResultManifest, score: _Score
) -> SourcePrivacyMetadata:
    privacy = manifest.privacy
    collaborative = (
        privacy.classification in {"group_and_teacher", "classroom_shared"}
        or len(privacy.audience_references) > 1
        or any(
            subject.subject_kind != "core_student"
            for subject in privacy.audience_references
        )
    )
    multi_subject = (
        score.target_reference.target_kind != "core_student" or collaborative
    )
    return SourcePrivacyMetadata(
        classification=privacy.classification,
        subject_scope="multi_subject" if multi_subject else "single_subject",
        metadata_visibility="internal",
        collaborator_information_present=multi_subject,
        third_party_information_present=False,
        rights_review_required=False,
        redaction_review_required=multi_subject,
        multi_subject_review_required=multi_subject,
        minimum_necessary_projection_required=True,
        policy_reference=CONCORD_PRIVACY_POLICY_REFERENCE,
    )


def _related_record_fields(reason: _StatusReason | None) -> tuple[ProjectionField, ...]:
    if reason is None or reason.related_record is None:
        return (
            ProjectionField(key="status_reason_related_module_id", value=None),
            ProjectionField(key="status_reason_related_record_kind", value=None),
            ProjectionField(key="status_reason_related_record_id", value=None),
            ProjectionField(key="status_reason_related_contract_version", value=None),
        )
    related = reason.related_record
    return (
        ProjectionField(
            key="status_reason_related_module_id", value=related.module_id
        ),
        ProjectionField(
            key="status_reason_related_record_kind", value=related.record_kind
        ),
        ProjectionField(
            key="status_reason_related_record_id", value=related.record_id
        ),
        ProjectionField(
            key="status_reason_related_contract_version",
            value=related.contract_version,
        ),
    )


def _score_fields(
    *,
    manifest: _AcademicResultManifest,
    score: _Score,
    criterion_set: _CriterionSet,
    criterion: _Criterion,
    scale: _ScoringScale,
    standards_result: _StandardsResult | None,
    score_links: tuple[_ScoreEvidenceLink, ...],
) -> tuple[ProjectionField, ...]:
    reason = score.status_reason
    level_values = tuple(level.value for level in scale.levels)
    level_types = tuple(_native_scalar_type(level.value) for level in scale.levels)
    level_labels = tuple(level.label for level in scale.levels)
    level_meanings = tuple(level.meaning for level in scale.levels)
    level_positions = tuple(level.position for level in scale.levels)
    level_descriptions = tuple(level.description for level in scale.levels)
    fields = (
        ProjectionField(key="manifest_record_type", value=manifest.record_type),
        ProjectionField(
            key="manifest_contract_version", value=manifest.contract_version
        ),
        ProjectionField(key="producer_module_id", value=manifest.producer_module_id),
        ProjectionField(key="record_set_id", value=manifest.record_set.record_set_id),
        ProjectionField(key="record_set_revision", value=manifest.record_set.revision),
        ProjectionField(
            key="manifest_generated_at",
            value=_canonical_timestamp(manifest.generated_at),
        ),
        ProjectionField(key="work_class_id", value=manifest.work.class_id),
        ProjectionField(key="work_id", value=manifest.work.work_id),
        ProjectionField(
            key="source_activity_record_kind",
            value=manifest.source_activity.record_kind,
        ),
        ProjectionField(
            key="source_activity_record_id", value=manifest.source_activity.record_id
        ),
        ProjectionField(
            key="source_activity_contract_version",
            value=manifest.source_activity.contract_version,
        ),
        ProjectionField(
            key="source_snapshot_revision",
            value=manifest.projection.source_snapshot_revision,
        ),
        ProjectionField(
            key="projection_digest_algorithm",
            value=manifest.projection.projection_digest_algorithm,
        ),
        ProjectionField(
            key="projection_digest", value=manifest.projection.projection_digest
        ),
        ProjectionField(
            key="projection_generated_by_kind",
            value=manifest.projection.generated_by.actor_kind,
        ),
        ProjectionField(
            key="projection_generated_by_id",
            value=manifest.projection.generated_by.actor_id,
        ),
        ProjectionField(
            key="projection_generated_by_system",
            value=manifest.projection.generated_by.owning_system,
        ),
        ProjectionField(
            key="projection_revision_reason",
            value=manifest.projection.revision_reason,
        ),
        ProjectionField(
            key="activity_id", value=manifest.activity_context.activity_id
        ),
        ProjectionField(
            key="activity_title", value=manifest.activity_context.title
        ),
        ProjectionField(
            key="activity_scoring_orientation",
            value=manifest.activity_context.scoring_orientation,
        ),
        ProjectionField(
            key="activity_standards_profile_id",
            value=manifest.activity_context.standards_profile_id,
        ),
        ProjectionField(
            key="activity_focus_standard_ids",
            value=manifest.activity_context.focus_standard_ids,
        ),
        ProjectionField(
            key="activity_criterion_set_ids",
            value=manifest.activity_context.criterion_set_ids,
        ),
        ProjectionField(
            key="criterion_set_id", value=criterion_set.criterion_set_id
        ),
        ProjectionField(
            key="criterion_set_lineage_id", value=criterion_set.lineage_id
        ),
        ProjectionField(
            key="criterion_set_revision", value=criterion_set.revision
        ),
        ProjectionField(
            key="criterion_set_kind", value=criterion_set.criterion_set_kind
        ),
        ProjectionField(key="criterion_set_scope", value=criterion_set.scope),
        ProjectionField(
            key="criterion_set_criterion_ids", value=criterion_set.criterion_ids
        ),
        ProjectionField(key="criterion_set_status", value=criterion_set.status),
        ProjectionField(
            key="criterion_set_supersedes_id",
            value=criterion_set.supersedes_criterion_set_id,
        ),
        ProjectionField(
            key="criterion_set_standards_profile_id",
            value=criterion_set.standards_profile_id,
        ),
        ProjectionField(key="criterion_id", value=criterion.criterion_id),
        ProjectionField(key="criterion_key", value=criterion.key),
        ProjectionField(key="criterion_label", value=criterion.label),
        ProjectionField(key="criterion_definition", value=criterion.definition),
        ProjectionField(key="criterion_kind", value=criterion.criterion_kind),
        ProjectionField(
            key="criterion_supported_target_kinds",
            value=criterion.supported_target_kinds,
        ),
        ProjectionField(key="criterion_status", value=criterion.status),
        ProjectionField(key="criterion_standard_id", value=criterion.standard_id),
        ProjectionField(
            key="criterion_alignment_standard_ids",
            value=criterion.alignment_standard_ids,
        ),
        ProjectionField(
            key="criterion_default_scoring_scale_id",
            value=criterion.default_scoring_scale_id,
        ),
        ProjectionField(key="scoring_scale_id", value=scale.scoring_scale_id),
        ProjectionField(key="scoring_scale_lineage_id", value=scale.lineage_id),
        ProjectionField(key="scoring_scale_name", value=scale.name),
        ProjectionField(key="scoring_scale_revision", value=scale.revision),
        ProjectionField(key="scoring_scale_type", value=scale.scale_type),
        ProjectionField(key="scoring_scale_status", value=scale.status),
        ProjectionField(
            key="scoring_scale_supersedes_id",
            value=scale.supersedes_scoring_scale_id,
        ),
        ProjectionField(key="scale_level_values", value=level_values),
        ProjectionField(key="scale_level_value_types", value=level_types),
        ProjectionField(key="scale_level_labels", value=level_labels),
        ProjectionField(key="scale_level_meanings", value=level_meanings),
        ProjectionField(key="scale_level_positions", value=level_positions),
        ProjectionField(key="scale_level_descriptions", value=level_descriptions),
        ProjectionField(key="score_record_id", value=score.score_record_id),
        ProjectionField(key="score_activity_id", value=score.activity_id),
        ProjectionField(key="score_session_id", value=score.session_id),
        ProjectionField(
            key="score_target_kind", value=score.target_reference.target_kind
        ),
        ProjectionField(
            key="score_target_id", value=score.target_reference.target_id
        ),
        ProjectionField(
            key="score_target_owning_system",
            value=score.target_reference.owning_system,
        ),
        ProjectionField(
            key="score_target_contract_version",
            value=score.target_reference.contract_version,
        ),
        ProjectionField(key="score_kind", value=score.score_kind),
        ProjectionField(key="score_standard_id", value=score.standard_id),
        ProjectionField(
            key="score_scoring_scale_id", value=score.scoring_scale_id
        ),
        ProjectionField(key="score_disposition", value=score.disposition),
        ProjectionField(key="score_native_value", value=score.value),
        ProjectionField(
            key="score_native_value_type", value=_native_scalar_type(score.value)
        ),
        ProjectionField(key="score_basis", value=score.basis),
        ProjectionField(key="score_scorer_kind", value=score.scorer.actor_kind),
        ProjectionField(key="score_scorer_id", value=score.scorer.actor_id),
        ProjectionField(
            key="score_scorer_owning_system", value=score.scorer.owning_system
        ),
        ProjectionField(
            key="score_scored_at", value=_canonical_timestamp(score.scored_at)
        ),
        ProjectionField(
            key="score_moderation_complete", value=score.moderation_complete
        ),
        ProjectionField(
            key="score_supersedes_score_record_id",
            value=score.supersedes_score_record_id,
        ),
        ProjectionField(key="score_current_state", value=score.current_state),
        ProjectionField(
            key="status_reason_code",
            value=reason.reason_code if reason is not None else None,
        ),
        ProjectionField(
            key="status_reason_recorded_by_kind",
            value=reason.recorded_by.actor_kind if reason is not None else None,
        ),
        ProjectionField(
            key="status_reason_recorded_by_id",
            value=reason.recorded_by.actor_id if reason is not None else None,
        ),
        ProjectionField(
            key="status_reason_recorded_by_system",
            value=reason.recorded_by.owning_system if reason is not None else None,
        ),
        ProjectionField(
            key="status_reason_recorded_at",
            value=(
                _canonical_timestamp(reason.recorded_at)
                if reason is not None
                else None
            ),
        ),
        ProjectionField(
            key="standards_result_standard_id",
            value=(
                standards_result.standard_id
                if standards_result is not None
                else None
            ),
        ),
    )
    return (
        fields
        + _related_record_fields(reason)
        + _score_link_fields(score_links)
        + _privacy_fields(manifest)
    )


def _project_score(
    *,
    manifest: _AcademicResultManifest,
    score: _Score,
    criterion_set: _CriterionSet,
    criterion: _Criterion,
    scale: _ScoringScale,
    standards_result: _StandardsResult | None,
    score_links: tuple[_ScoreEvidenceLink, ...],
) -> ProjectedProducerSource:
    return ProjectedProducerSource(
        projection_kind=CONCORD_SCORE_PROJECTION_KIND,
        producer_source=ProducerSourceReference(
            producer_module_id="concord",
            producer_contract_version="concord_academic_work_v1",
            source_record_kind="score_record",
            source_record_id=score.score_record_id,
            source_record_contract_version=None,
            native_revision=None,
            native_lifecycle=score.current_state,
            native_disposition=score.disposition,
            lineage_reference=score.activity_id,
            reader_contract_version=(
                CONCORD_LIVE_ADAPTER_DECLARATION.reader_contract_version
            ),
            projection_contract_version=(
                CONCORD_LIVE_ADAPTER_DECLARATION.candidate_projection_contract_version
            ),
        ),
        source_artifact=SourceArtifactReference(
            artifact_id=f"{score.score_record_id}_summary",
            artifact_kind="assessment_summary",
            representation_kind=CONCORD_SCORE_PROJECTION_KIND,
            media_type=CONCORD_SCORE_MEDIA_TYPE,
            source_locator=None,
            native_revision=None,
            source_digest=None,
            byte_size=None,
            language=None,
            accessibility_relationship=None,
        ),
        source_relationships=_score_relationships(score),
        source_privacy=_score_privacy(manifest, score),
        display_snapshot=ProjectionDisplaySnapshot(
            title="Concord Score evidence",
            summary=(
                "One exact Concord Score revision with native Criterion and "
                "Scale context."
            ),
            fields=_score_fields(
                manifest=manifest,
                score=score,
                criterion_set=criterion_set,
                criterion=criterion,
                scale=scale,
                standards_result=standards_result,
                score_links=score_links,
            ),
        ),
    )



def _evidence_link_fields(
    *,
    manifest: _AcademicResultManifest,
    link: _ScoreEvidenceLink,
    moderation: _Moderation | None,
) -> tuple[ProjectionField, ...]:
    evidence = link.evidence_reference
    return (
        ProjectionField(
            key="manifest_record_type", value=manifest.record_type
        ),
        ProjectionField(
            key="manifest_contract_version", value=manifest.contract_version
        ),
        ProjectionField(
            key="producer_module_id", value=manifest.producer_module_id
        ),
        ProjectionField(
            key="record_set_id", value=manifest.record_set.record_set_id
        ),
        ProjectionField(
            key="record_set_revision", value=manifest.record_set.revision
        ),
        ProjectionField(
            key="manifest_generated_at",
            value=_canonical_timestamp(manifest.generated_at),
        ),
        ProjectionField(key="work_class_id", value=manifest.work.class_id),
        ProjectionField(key="work_id", value=manifest.work.work_id),
        ProjectionField(
            key="source_snapshot_revision",
            value=manifest.projection.source_snapshot_revision,
        ),
        ProjectionField(
            key="score_evidence_link_id",
            value=link.score_evidence_link_id,
        ),
        ProjectionField(
            key="score_evidence_parent_score_record_id",
            value=link.score_record_id,
        ),
        ProjectionField(
            key="score_evidence_relevance_description",
            value=link.relevance_description,
        ),
        ProjectionField(
            key="score_evidence_significance", value=link.significance
        ),
        ProjectionField(
            key="score_evidence_moderation_record_id",
            value=link.moderation_record_id,
        ),
        ProjectionField(key="score_evidence_status", value=link.status),
        ProjectionField(
            key="score_evidence_supersedes_link_id",
            value=link.supersedes_score_evidence_link_id,
        ),
        ProjectionField(
            key="artifact_resolution_capable",
            value=_artifact_capable(link),
        ),
        ProjectionField(
            key="artifact_resolution_representation",
            value=(
                CONCORD_ARTIFACT_REPRESENTATION_KIND
                if _artifact_capable(link)
                else None
            ),
        ),
        ProjectionField(
            key="artifact_resolution_source_snapshot_revision",
            value=(
                manifest.projection.source_snapshot_revision
                if _artifact_capable(link)
                else None
            ),
        ),
        ProjectionField(
            key="artifact_resolution_evidence_record_id",
            value=evidence.record_id if _artifact_capable(link) else None,
        ),
    ) + _evidence_reference_fields(
        evidence
    ) + _locator_fields(
        "score_evidence_locator", link.evidence_locator
    ) + _subject_fields(
        "score_evidence_subject", link.subject_context
    ) + _moderation_fields(
        moderation
    ) + _privacy_fields(manifest)


def _project_evidence_link(
    *,
    manifest: _AcademicResultManifest,
    link: _ScoreEvidenceLink,
    score: _Score,
    moderation: _Moderation | None,
) -> ProjectedProducerSource:
    evidence = link.evidence_reference
    artifact_capable = _artifact_capable(link)
    if artifact_capable:
        projection_kind = CONCORD_ARTIFACT_PROJECTION_KIND
        artifact_id = evidence.record_id
        artifact_kind = "collaborative_artifact"
        representation_kind = CONCORD_ARTIFACT_REPRESENTATION_KIND
        media_type = CONCORD_ARTIFACT_MEDIA_TYPE
        title = "Concord Artifact evidence"
        summary = (
            "One exact Concord-owned Artifact Score Evidence Link, represented "
            "without Artifact bytes or a native source locator."
        )
    else:
        projection_kind = CONCORD_EVIDENCE_LINK_PROJECTION_KIND
        artifact_id = f"{link.score_evidence_link_id}_summary"
        artifact_kind = "assessment_summary"
        representation_kind = CONCORD_EVIDENCE_LINK_PROJECTION_KIND
        media_type = CONCORD_EVIDENCE_LINK_MEDIA_TYPE
        title = "Concord evidence link"
        summary = (
            "One exact Concord Score Evidence Link preserved as metadata only."
        )

    return ProjectedProducerSource(
        projection_kind=projection_kind,
        producer_source=ProducerSourceReference(
            producer_module_id="concord",
            producer_contract_version="concord_academic_work_v1",
            source_record_kind="score_evidence_link",
            source_record_id=link.score_evidence_link_id,
            source_record_contract_version=None,
            native_revision=None,
            native_lifecycle=link.status,
            native_disposition=link.significance or evidence.evidence_kind,
            lineage_reference=link.score_record_id,
            reader_contract_version=(
                CONCORD_LIVE_ADAPTER_DECLARATION.reader_contract_version
            ),
            projection_contract_version=(
                CONCORD_LIVE_ADAPTER_DECLARATION.candidate_projection_contract_version
            ),
        ),
        source_artifact=SourceArtifactReference(
            artifact_id=artifact_id,
            artifact_kind=artifact_kind,
            representation_kind=representation_kind,
            media_type=media_type,
            source_locator=None,
            native_revision=manifest.projection.source_snapshot_revision,
            source_digest=None,
            byte_size=None,
            language=None,
            accessibility_relationship=None,
        ),
        source_relationships=_score_relationships(score),
        source_privacy=_evidence_link_privacy(manifest, link),
        display_snapshot=ProjectionDisplaySnapshot(
            title=title,
            summary=summary,
            fields=_evidence_link_fields(
                manifest=manifest,
                link=link,
                moderation=moderation,
            ),
        ),
    )


class ConcordLiveProjectionAdapter:
    """Project every Concord Score and Evidence Link revision independently."""

    def __init__(self) -> None:
        self._reader: ProducerManifestReader = build_audited_installed_producer_reader(
            "concord"
        )

    @property
    def declaration(self) -> ProducerProjectionAdapterDeclaration:
        return CONCORD_LIVE_ADAPTER_DECLARATION

    @property
    def reader(self) -> ProducerManifestReader:
        return self._reader

    def project(self, public_model: object) -> ProducerProjectionBatch:
        """Project one validated public Concord manifest without selecting evidence."""

        try:
            contract = import_module("concord.academic_result_manifest")
            manifest_type = getattr(contract, "AcademicResultManifest")
        except Exception as error:
            raise _projection_error(
                "projection.failed",
                "projection_contract",
                "Live Concord projection contract could not be resolved.",
            ) from error
        if not isinstance(manifest_type, type):
            raise _projection_error(
                "projection.failed",
                "projection_contract",
                "Live Concord projection contract has an incompatible type surface.",
            )
        if not isinstance(public_model, manifest_type):
            raise _projection_error(
                "projection.invalid_input",
                "projection",
                "Live Concord adapter requires the validated public Concord model.",
            )

        manifest = cast(_AcademicResultManifest, public_model)
        try:
            criteria = {item.criterion_id: item for item in manifest.criteria}
            criterion_sets = {
                item.criterion_set_id: item for item in manifest.criterion_sets
            }
            scales = {
                item.scoring_scale_id: item for item in manifest.scoring_scales
            }
            standards_results = {
                item.score_record_id: item
                for item in manifest.standards_result_projection
            }
            moderation_by_id = {
                item.moderation_record_id: item
                for item in manifest.moderation_records
            }
            scores_by_id = {
                item.score_record_id: item
                for item in manifest.scores
            }

            sources: list[ProjectedProducerSource] = []
            for score in manifest.scores:
                criterion = criteria[score.criterion_id]
                criterion_set = criterion_sets[criterion.criterion_set_id]
                scale = scales[score.scoring_scale_id]
                score_links = _links_for_score(
                    manifest.score_evidence_links, score.score_record_id
                )
                sources.append(
                    _project_score(
                        manifest=manifest,
                        score=score,
                        criterion_set=criterion_set,
                        criterion=criterion,
                        scale=scale,
                        standards_result=standards_results.get(score.score_record_id),
                        score_links=score_links,
                    )
                )

            for link in manifest.score_evidence_links:
                moderation = (
                    moderation_by_id[link.moderation_record_id]
                    if link.moderation_record_id is not None
                    else None
                )
                sources.append(
                    _project_evidence_link(
                        manifest=manifest,
                        link=link,
                        score=scores_by_id[link.score_record_id],
                        moderation=moderation,
                    )
                )

            return ProducerProjectionBatch(
                adapter_id=self.declaration.adapter_id,
                adapter_contract_version=self.declaration.adapter_contract_version,
                reader_id=self.declaration.public_reader_id,
                reader_contract_version=self.declaration.reader_contract_version,
                candidate_projection_contract_version=(
                    self.declaration.candidate_projection_contract_version
                ),
                support_key=self.declaration.support_key,
                projected_sources=tuple(sources),
                diagnostic_codes=(),
            )
        except ProducerProjectionError:
            raise
        except Exception as error:
            raise _projection_error(
                "projection.failed",
                "projection",
                "Live Concord projection failed.",
            ) from error


def build_concord_live_adapter() -> ConcordLiveProjectionAdapter:
    """Build the live Concord adapter without importing or discovering Concord."""

    return ConcordLiveProjectionAdapter()


__all__ = [
    "CONCORD_ARTIFACT_MEDIA_TYPE",
    "CONCORD_ARTIFACT_PROJECTION_KIND",
    "CONCORD_ARTIFACT_REPRESENTATION_KIND",
    "CONCORD_EVIDENCE_LINK_MEDIA_TYPE",
    "CONCORD_EVIDENCE_LINK_PROJECTION_KIND",
    "CONCORD_LIVE_ADAPTER_CONTRACT_VERSION",
    "CONCORD_LIVE_ADAPTER_DECLARATION",
    "CONCORD_LIVE_ADAPTER_ID",
    "CONCORD_LIVE_DIAGNOSTIC_CONTRACT_VERSION",
    "CONCORD_LIVE_PROJECTION_CONTRACT_VERSION",
    "CONCORD_PRIVACY_POLICY_REFERENCE",
    "CONCORD_SCORE_MEDIA_TYPE",
    "CONCORD_SCORE_PROJECTION_KIND",
    "ConcordLiveProjectionAdapter",
    "build_concord_live_adapter",
]
