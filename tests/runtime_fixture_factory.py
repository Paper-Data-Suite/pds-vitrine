from __future__ import annotations

from datetime import datetime, timezone

from pds_core.routing_models import ModuleRecordRef, ModuleWorkRef

from vitrine.models import (
    AcademicWorkRegistrationSnapshot,
    ActorAttribution,
    AudienceContext,
    CandidateAvailabilityObservation,
    CandidateEvaluation,
    CandidateSourceEndpoint,
    ClassQualifiedStudentRef,
    CorePublicationSourceReference,
    DigestReference,
    PlacementPresentation,
    Portfolio,
    PortfolioCandidate,
    PortfolioPlacement,
    PortfolioProfileBinding,
    PortfolioProfileFamily,
    PortfolioProfileRevision,
    PortfolioSelection,
    PortfolioSubject,
    PortfolioSubjectClassLink,
    PortfolioSubjectRelationshipAssertion,
    ProducerSourceReference,
    ProfileApplicability,
    ProfileAudienceRule,
    ProfileSectionDefinition,
    SectionArrangementRevision,
    SnapshotEdition,
    SnapshotEditionRef,
    SnapshotEntry,
    SnapshotManifest,
    SnapshotMaterializationRecord,
    SnapshotOmission,
    SnapshotSeal,
    SourceArtifactReference,
    SourcePrivacyMetadata,
    VitrineRecordGraph,
    WorkingPortfolioCompositionRevision,
)

NOW = datetime(2026, 8, 6, 20, 0, tzinfo=timezone.utc)
TEACHER = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_001",
    owning_system="vitrine",
    display_label_snapshot="Synthetic Teacher",
    role_snapshot="teacher",
)
D1 = DigestReference(value="1" * 64)
D2 = DigestReference(value="2" * 64)
D3 = DigestReference(value="3" * 64)
D4 = DigestReference(value="4" * 64)
D5 = DigestReference(value="5" * 64)
D6 = DigestReference(value="6" * 64)


def registration(work_id: str, title: str) -> AcademicWorkRegistrationSnapshot:
    return AcademicWorkRegistrationSnapshot(
        registration_revision=1,
        producer_contract_version="quillan_academic_work_v1",
        title_snapshot=title,
        work_kind="assignment",
        academic_intent="formative",
        lifecycle="closed",
        source_records=(
            ModuleRecordRef(
                module_id="quillan",
                record_kind="assignment",
                record_id=work_id,
                contract_version="assignment_v2",
            ),
        ),
    )


def publication(
    *, module_id: str, class_id: str, work_id: str, publication_id: str,
    record_set_revision: int, manifest_digest: str, manifest_contract: str,
    producer_contract: str, title: str, capabilities: tuple[str, ...],
) -> CorePublicationSourceReference:
    reg = AcademicWorkRegistrationSnapshot(
        registration_revision=1,
        producer_contract_version=producer_contract,
        title_snapshot=title,
        work_kind="assignment" if module_id != "concord" else "activity",
        academic_intent="formative",
        lifecycle="closed",
        source_records=(
            ModuleRecordRef(
                module_id=module_id,
                record_kind="assignment" if module_id != "concord" else "activity",
                record_id=work_id,
                contract_version=None,
            ),
        ),
    )
    return CorePublicationSourceReference(
        core_publication_schema_version="1",
        publication_id=publication_id,
        work=ModuleWorkRef(module_id=module_id, class_id=class_id, work_id=work_id),
        source_record=None,
        publication_kind="academic_result_set",
        capabilities=capabilities,
        record_set_id="academic_results",
        record_set_revision=record_set_revision,
        manifest_contract_version=manifest_contract,
        manifest_path=f"classes/{class_id}/modules/{module_id}/work/{work_id}/exports/manifests/academic_results/{record_set_revision}.json",
        manifest_digest_algorithm="sha256",
        manifest_digest=manifest_digest,
        published_at=NOW,
        academic_work_registration_revision=1,
        registration_snapshot=reg,
        supersedes_publication_id=None,
        observed_series_state="current_selectable",
        observed_withdrawal_state="not_withdrawn",
        verified_at=NOW,
    )


def endpoint(
    *, subject_id: str, link_id: str, module_id: str, class_id: str,
    work_id: str, publication_id: str, source_id: str, artifact_id: str,
    artifact_kind: str, representation_kind: str, locator: str, digest: DigestReference,
    relationship_kinds: tuple[str, ...] = ("submission_subject",),
    rights_review_required: bool = False,
) -> CandidateSourceEndpoint:
    pub = publication(
        module_id=module_id,
        class_id=class_id,
        work_id=work_id,
        publication_id=publication_id,
        record_set_revision=1,
        manifest_digest=digest.value,
        manifest_contract=(
            "concord_academic_result_manifest_v1"
            if module_id == "concord"
            else "quillan_academic_result_manifest_v1"
        ),
        producer_contract=(
            "concord_academic_work_v1"
            if module_id == "concord"
            else "quillan_academic_work_v1"
        ),
        title="Synthetic source",
        capabilities=("artifact_references",),
    )
    assertions = tuple(
        PortfolioSubjectRelationshipAssertion(
            assertion_id=f"assert_{artifact_id}_{index}",
            portfolio_subject_id=subject_id,
            subject_link_id=link_id,
            source_subject_kind="producer_subject",
            source_subject_id=f"source_subject_{index}",
            relationship_kind=kind,
            relationship_authority="producer_contract",
            supporting_source_reference=source_id,
            verified_at=NOW,
            verified_by=TEACHER,
        )
        for index, kind in enumerate(relationship_kinds, start=1)
    )
    return CandidateSourceEndpoint(
        core_publication=pub,
        producer_source=ProducerSourceReference(
            producer_module_id=module_id,
            producer_contract_version=pub.registration_snapshot.producer_contract_version,
            source_record_kind="submission" if module_id == "quillan" else "artifact_instance",
            source_record_id=source_id,
            source_record_contract_version="1",
            native_revision=1,
            native_lifecycle="complete",
            native_disposition=None,
            lineage_reference=None,
            reader_contract_version="1",
            projection_contract_version="vitrine_projection_v1",
        ),
        source_artifact=SourceArtifactReference(
            artifact_id=artifact_id,
            artifact_kind=artifact_kind,
            representation_kind=representation_kind,
            media_type="text/plain",
            source_locator=locator,
            native_revision=1,
            source_digest=digest,
            byte_size=128,
            language="en",
            accessibility_relationship=None,
        ),
        subject_relationship_assertions=assertions,
        source_privacy=SourcePrivacyMetadata(
            classification="student_record",
            subject_scope="single_subject",
            metadata_visibility="authorized_vitrine",
            collaborator_information_present=module_id == "concord",
            third_party_information_present=module_id == "concord",
            rights_review_required=rights_review_required,
            redaction_review_required=False,
            multi_subject_review_required=module_id == "concord",
            minimum_necessary_projection_required=True,
            policy_reference="synthetic_policy_v1",
        ),
    )


def make_improvement_graph() -> VitrineRecordGraph:
    subject = PortfolioSubject(
        portfolio_subject_id="subject_improvement",
        created_at=NOW,
        created_by=TEACHER,
        display_name_snapshot="Synthetic Student A",
    )
    link = PortfolioSubjectClassLink(
        subject_link_id="link_improvement",
        portfolio_subject_id=subject.portfolio_subject_id,
        student_reference=ClassQualifiedStudentRef(
            class_id="english10_p2", student_id="student_0042", school_year="2026-2027"
        ),
        confirmed_at=NOW,
        confirmed_by=TEACHER,
        confirmation_basis="teacher_confirmed",
        authority_reference="synthetic_roster_review",
    )
    portfolio = Portfolio(
        portfolio_id="portfolio_improvement",
        portfolio_subject_id=subject.portfolio_subject_id,
        created_at=NOW,
        created_by=TEACHER,
        title_snapshot="Growth in literary analysis",
    )
    family = PortfolioProfileFamily(
        profile_family_id="family_improvement",
        label="Improvement Portfolio",
        purpose_kind="improvement",
        created_at=NOW,
        created_by=TEACHER,
    )
    profile = PortfolioProfileRevision(
        portfolio_profile_id="profile_improvement",
        profile_revision=1,
        profile_family_id=family.profile_family_id,
        predecessor_revision=None,
        label="Improvement Profile v1",
        purpose_kind="improvement",
        applicability=ProfileApplicability(
            school_years=("2026-2027",), content_areas=("ela",)
        ),
        sections=(
            ProfileSectionDefinition(
                section_id="baseline",
                label="Baseline",
                purpose="Establish an initial performance point.",
                order=1,
                obligation="required",
                minimum_placements=1,
                maximum_placements=1,
                allowed_candidate_kinds=("original_student_work",),
                required_relationship_kinds=("submission_subject",),
                reflection_requirement="none",
            ),
            ProfileSectionDefinition(
                section_id="later_work",
                label="Later Work",
                purpose="Show later performance on comparable work.",
                order=2,
                obligation="required",
                minimum_placements=1,
                maximum_placements=1,
                allowed_candidate_kinds=("original_student_work",),
                required_relationship_kinds=("submission_subject",),
                reflection_requirement="none",
            ),
            ProfileSectionDefinition(
                section_id="reflection",
                label="Reflection",
                purpose="Explain the demonstrated change.",
                order=3,
                obligation="required",
                minimum_placements=0,
                maximum_placements=1,
                allowed_candidate_kinds=("local:student_reflection",),
                required_relationship_kinds=(),
                reflection_requirement="required",
            ),
        ),
        audience_rules=(
            ProfileAudienceRule(
                audience_rule_id="student_view",
                audience_class="student",
                purpose="Student review of improvement evidence.",
                allowed_content_classes=("student_work", "feedback", "reflection"),
                prohibited_content_classes=("private_teacher_note",),
                required_review_classes=("privacy_review",),
                presentation_class="student_portfolio",
            ),
        ),
        created_at=NOW,
        created_by=TEACHER,
        source_authority_references=("local_profile_authority",),
        known_limitations=("Synthetic instructional profile only.",),
    )
    binding = PortfolioProfileBinding(
        profile_binding_id="binding_improvement",
        portfolio_id=portfolio.portfolio_id,
        profile_revision=profile.reference,
        bound_at=NOW,
        bound_by=TEACHER,
    )
    baseline_endpoint = endpoint(
        subject_id=subject.portfolio_subject_id,
        link_id=link.subject_link_id,
        module_id="quillan",
        class_id="english10_p2",
        work_id="baseline_argument",
        publication_id="publication_baseline",
        source_id="submission_baseline",
        artifact_id="artifact_baseline",
        artifact_kind="original_student_work",
        representation_kind="student_submission",
        locator="artifacts/baseline-argument.txt",
        digest=D1,
    )
    later_endpoint = endpoint(
        subject_id=subject.portfolio_subject_id,
        link_id=link.subject_link_id,
        module_id="quillan",
        class_id="english10_p2",
        work_id="revised_argument",
        publication_id="publication_later",
        source_id="submission_later",
        artifact_id="artifact_later",
        artifact_kind="original_student_work",
        representation_kind="student_submission",
        locator="artifacts/revised-argument.txt",
        digest=D2,
    )
    observations = (
        CandidateAvailabilityObservation(
            dimension="canonical_publication", outcome="available", checked_at=NOW
        ),
        CandidateAvailabilityObservation(
            dimension="subject_relationship", outcome="confirmed", checked_at=NOW
        ),
        CandidateAvailabilityObservation(
            dimension="profile_eligibility", outcome="eligible", checked_at=NOW
        ),
    )
    evaluation_baseline = CandidateEvaluation(
        candidate_evaluation_id="evaluation_baseline",
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=subject.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile.reference,
        requesting_actor=TEACHER,
        purpose="Evaluate baseline work.",
        source_endpoint=baseline_endpoint,
        availability_observations=observations,
        matched_profile_rule_ids=("baseline_rule",),
        eligible_section_ids=("baseline",),
        outcome="eligible",
        reason_codes=(),
        evaluated_at=NOW,
        evaluator_contract_version="candidate_evaluator_v1",
    )
    evaluation_later = CandidateEvaluation(
        candidate_evaluation_id="evaluation_later",
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=subject.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile.reference,
        requesting_actor=TEACHER,
        purpose="Evaluate later work.",
        source_endpoint=later_endpoint,
        availability_observations=observations,
        matched_profile_rule_ids=("later_rule",),
        eligible_section_ids=("later_work",),
        outcome="eligible",
        reason_codes=(),
        evaluated_at=NOW,
        evaluator_contract_version="candidate_evaluator_v1",
    )
    candidate_baseline = PortfolioCandidate(
        candidate_id="candidate_baseline",
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=subject.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile.reference,
        candidate_evaluation_id=evaluation_baseline.candidate_evaluation_id,
        source_endpoint=baseline_endpoint,
        eligible_profile_rule_ids=("baseline_rule",),
        eligible_section_ids=("baseline",),
        condition_state="ready_for_consideration",
        display_snapshot="Baseline argument",
        created_at=NOW,
        created_by=TEACHER,
    )
    candidate_later = PortfolioCandidate(
        candidate_id="candidate_later",
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=subject.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile.reference,
        candidate_evaluation_id=evaluation_later.candidate_evaluation_id,
        source_endpoint=later_endpoint,
        eligible_profile_rule_ids=("later_rule",),
        eligible_section_ids=("later_work",),
        condition_state="ready_for_consideration",
        display_snapshot="Revised argument",
        created_at=NOW,
        created_by=TEACHER,
    )
    selection_baseline = PortfolioSelection(
        selection_id="selection_baseline",
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=subject.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile.reference,
        candidate_id=candidate_baseline.candidate_id,
        candidate_evaluation_id=evaluation_baseline.candidate_evaluation_id,
        selected_at=NOW,
        selected_by=TEACHER,
    )
    selection_later = PortfolioSelection(
        selection_id="selection_later",
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=subject.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile.reference,
        candidate_id=candidate_later.candidate_id,
        candidate_evaluation_id=evaluation_later.candidate_evaluation_id,
        selected_at=NOW,
        selected_by=TEACHER,
    )
    placement_baseline = PortfolioPlacement(
        placement_id="placement_baseline",
        portfolio_id=portfolio.portfolio_id,
        profile_binding_id=binding.profile_binding_id,
        selection_id=selection_baseline.selection_id,
        section_id="baseline",
        presentation=PlacementPresentation(display_title="Baseline"),
        placed_at=NOW,
        placed_by=TEACHER,
    )
    placement_later = PortfolioPlacement(
        placement_id="placement_later",
        portfolio_id=portfolio.portfolio_id,
        profile_binding_id=binding.profile_binding_id,
        selection_id=selection_later.selection_id,
        section_id="later_work",
        presentation=PlacementPresentation(display_title="Later Work"),
        placed_at=NOW,
        placed_by=TEACHER,
    )
    arrangement_baseline = SectionArrangementRevision(
        arrangement_id="arrangement_baseline",
        portfolio_id=portfolio.portfolio_id,
        profile_binding_id=binding.profile_binding_id,
        section_id="baseline",
        arrangement_revision=1,
        placement_ids=(placement_baseline.placement_id,),
        created_at=NOW,
        created_by=TEACHER,
    )
    arrangement_later = SectionArrangementRevision(
        arrangement_id="arrangement_later",
        portfolio_id=portfolio.portfolio_id,
        profile_binding_id=binding.profile_binding_id,
        section_id="later_work",
        arrangement_revision=1,
        placement_ids=(placement_later.placement_id,),
        created_at=NOW,
        created_by=TEACHER,
    )
    composition = WorkingPortfolioCompositionRevision(
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=subject.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile.reference,
        composition_revision=1,
        selection_ids=(selection_baseline.selection_id, selection_later.selection_id),
        placement_ids=(placement_baseline.placement_id, placement_later.placement_id),
        arrangement_ids=(arrangement_baseline.arrangement_id, arrangement_later.arrangement_id),
        created_at=NOW,
        created_by=TEACHER,
    )
    rule = profile.audience_rules[0]
    audience = AudienceContext(
        audience_context_id="audience_improvement",
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=subject.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile.reference,
        audience_rule_id=rule.audience_rule_id,
        audience_class=rule.audience_class,
        purpose=rule.purpose,
        subject_scope="portfolio_subject",
        allowed_content_classes=rule.allowed_content_classes,
        prohibited_content_classes=rule.prohibited_content_classes,
        required_review_classes=rule.required_review_classes,
        presentation_class=rule.presentation_class,
        retention_policy_reference=rule.retention_policy_reference,
        created_at=NOW,
        created_by=TEACHER,
    )
    edition_ref = SnapshotEditionRef(snapshot_series_id="snapshot_improvement", edition_number=1)
    mat_baseline = SnapshotMaterializationRecord(
        materialization_id="materialization_baseline",
        snapshot_edition=edition_ref,
        materialization_kind="copied_source",
        candidate_id=candidate_baseline.candidate_id,
        selection_id=selection_baseline.selection_id,
        placement_id=placement_baseline.placement_id,
        source_artifact=baseline_endpoint.source_artifact,
        source_digest=D1,
        output_digest=D1,
        byte_size=128,
        materialized_at=NOW,
        materialized_by=TEACHER,
    )
    mat_later = SnapshotMaterializationRecord(
        materialization_id="materialization_later",
        snapshot_edition=edition_ref,
        materialization_kind="copied_source",
        candidate_id=candidate_later.candidate_id,
        selection_id=selection_later.selection_id,
        placement_id=placement_later.placement_id,
        source_artifact=later_endpoint.source_artifact,
        source_digest=D2,
        output_digest=D2,
        byte_size=128,
        materialized_at=NOW,
        materialized_by=TEACHER,
    )
    mat_reflection = SnapshotMaterializationRecord(
        materialization_id="materialization_reflection",
        snapshot_edition=edition_ref,
        materialization_kind="generated_vitrine",
        candidate_id=None,
        selection_id=None,
        placement_id=None,
        source_artifact=None,
        source_digest=None,
        output_digest=D3,
        byte_size=96,
        materialized_at=NOW,
        materialized_by=TEACHER,
    )
    entries = (
        SnapshotEntry(
            snapshot_entry_id="entry_baseline",
            snapshot_edition=edition_ref,
            materialization_id=mat_baseline.materialization_id,
            section_id="baseline",
            ordinal=1,
            relative_path="export/01-baseline.txt",
            media_type="text/plain",
            content_class="student_work",
            display_title="Baseline Argument",
            source_placement_id=placement_baseline.placement_id,
        ),
        SnapshotEntry(
            snapshot_entry_id="entry_later",
            snapshot_edition=edition_ref,
            materialization_id=mat_later.materialization_id,
            section_id="later_work",
            ordinal=1,
            relative_path="export/02-later-work.txt",
            media_type="text/plain",
            content_class="student_work",
            display_title="Revised Argument",
            source_placement_id=placement_later.placement_id,
        ),
        SnapshotEntry(
            snapshot_entry_id="entry_reflection",
            snapshot_edition=edition_ref,
            materialization_id=mat_reflection.materialization_id,
            section_id="reflection",
            ordinal=1,
            relative_path="export/03-reflection.md",
            media_type="text/markdown",
            content_class="reflection",
            display_title="Student Reflection",
            source_placement_id=None,
        ),
    )
    manifest = SnapshotManifest(
        manifest_id="manifest_improvement",
        manifest_contract_version="vitrine_snapshot_manifest_v1",
        snapshot_edition=edition_ref,
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=subject.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile.reference,
        composition_revision=composition.composition_revision,
        audience_context_id=audience.audience_context_id,
        entry_ids=tuple(item.snapshot_entry_id for item in entries),
        omission_ids=(),
        created_at=NOW,
        created_by=TEACHER,
    )
    seal = SnapshotSeal(
        seal_id="seal_improvement",
        snapshot_edition=edition_ref,
        manifest_id=manifest.manifest_id,
        manifest_digest=D4,
        logical_inventory_digest=D5,
        sealed_at=NOW,
        sealed_by=TEACHER,
    )
    edition = SnapshotEdition(
        snapshot_series_id=edition_ref.snapshot_series_id,
        edition_number=edition_ref.edition_number,
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=subject.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile.reference,
        composition_revision=composition.composition_revision,
        audience_context_id=audience.audience_context_id,
        manifest_id=manifest.manifest_id,
        seal_id=seal.seal_id,
        created_at=NOW,
        created_by=TEACHER,
    )
    return VitrineRecordGraph(
        portfolios=(portfolio,),
        portfolio_subjects=(subject,),
        subject_links=(link,),
        profile_families=(family,),
        profile_revisions=(profile,),
        profile_bindings=(binding,),
        candidate_evaluations=(evaluation_baseline, evaluation_later),
        candidates=(candidate_baseline, candidate_later),
        selections=(selection_baseline, selection_later),
        placements=(placement_baseline, placement_later),
        arrangements=(arrangement_baseline, arrangement_later),
        compositions=(composition,),
        audience_contexts=(audience,),
        materializations=(mat_baseline, mat_later, mat_reflection),
        snapshot_entries=entries,
        snapshot_omissions=(),
        snapshot_manifests=(manifest,),
        snapshot_seals=(seal,),
        snapshot_editions=(edition,),
    )


def make_showcase_graph() -> VitrineRecordGraph:
    subject = PortfolioSubject(
        portfolio_subject_id="subject_showcase",
        created_at=NOW,
        created_by=TEACHER,
        display_name_snapshot="Synthetic Student B",
    )
    link = PortfolioSubjectClassLink(
        subject_link_id="link_showcase",
        portfolio_subject_id=subject.portfolio_subject_id,
        student_reference=ClassQualifiedStudentRef(
            class_id="science10_p4", student_id="student_0042", school_year="2026-2027"
        ),
        confirmed_at=NOW,
        confirmed_by=TEACHER,
        confirmation_basis="teacher_confirmed",
    )
    portfolio = Portfolio(
        portfolio_id="portfolio_showcase",
        portfolio_subject_id=subject.portfolio_subject_id,
        created_at=NOW,
        created_by=TEACHER,
        title_snapshot="Student Showcase",
    )
    family = PortfolioProfileFamily(
        profile_family_id="family_showcase",
        label="Showcase Portfolio",
        purpose_kind="showcase",
        created_at=NOW,
        created_by=TEACHER,
    )
    profile = PortfolioProfileRevision(
        portfolio_profile_id="profile_showcase",
        profile_revision=1,
        profile_family_id=family.profile_family_id,
        predecessor_revision=None,
        label="Showcase Profile v1",
        purpose_kind="showcase",
        applicability=ProfileApplicability(school_years=("2026-2027",)),
        sections=(
            ProfileSectionDefinition(
                section_id="featured_work",
                label="Featured Work",
                purpose="Present polished individual work.",
                order=1,
                obligation="required",
                minimum_placements=1,
                maximum_placements=3,
                allowed_candidate_kinds=("original_student_work",),
                required_relationship_kinds=("submission_subject",),
                reflection_requirement="optional",
            ),
            ProfileSectionDefinition(
                section_id="collaboration",
                label="Collaboration",
                purpose="Present audience-safe collaborative evidence.",
                order=2,
                obligation="optional",
                minimum_placements=0,
                maximum_placements=2,
                allowed_candidate_kinds=("audience_safe_attribution",),
                required_relationship_kinds=("documented_contributor",),
                reflection_requirement="optional",
            ),
        ),
        audience_rules=(
            ProfileAudienceRule(
                audience_rule_id="public_showcase",
                audience_class="public",
                purpose="Public showcase of reviewed work.",
                allowed_content_classes=("student_work", "audience_safe_attribution"),
                prohibited_content_classes=("private_teacher_note", "raw_collaborator_data"),
                required_review_classes=("rights_review", "privacy_review"),
                presentation_class="public_showcase",
            ),
        ),
        created_at=NOW,
        created_by=TEACHER,
    )
    binding = PortfolioProfileBinding(
        profile_binding_id="binding_showcase",
        portfolio_id=portfolio.portfolio_id,
        profile_revision=profile.reference,
        bound_at=NOW,
        bound_by=TEACHER,
    )
    individual = endpoint(
        subject_id=subject.portfolio_subject_id,
        link_id=link.subject_link_id,
        module_id="quillan",
        class_id="science10_p4",
        work_id="polished_analysis",
        publication_id="publication_polished",
        source_id="submission_polished",
        artifact_id="artifact_polished",
        artifact_kind="original_student_work",
        representation_kind="student_submission",
        locator="artifacts/polished-analysis.txt",
        digest=D1,
    )
    relationships = (
        "group_member",
        "artifact_author",
        "artifact_subject",
        "documented_contributor",
        "recorder",
        "represented_group",
        "individual_score_target",
        "group_score_target",
    )
    collaborative_raw = endpoint(
        subject_id=subject.portfolio_subject_id,
        link_id=link.subject_link_id,
        module_id="concord",
        class_id="science10_p4",
        work_id="water_quality_activity",
        publication_id="publication_collaboration",
        source_id="artifact_group_raw",
        artifact_id="artifact_group_raw",
        artifact_kind="collaborative_artifact",
        representation_kind="original_group_artifact",
        locator="artifacts/group-artifact.txt",
        digest=D2,
        relationship_kinds=relationships,
        rights_review_required=True,
    )
    collaborative_safe = endpoint(
        subject_id=subject.portfolio_subject_id,
        link_id=link.subject_link_id,
        module_id="concord",
        class_id="science10_p4",
        work_id="water_quality_activity",
        publication_id="publication_collaboration_safe",
        source_id="artifact_group_safe",
        artifact_id="artifact_group_safe",
        artifact_kind="audience_safe_attribution",
        representation_kind="audience_safe_projection",
        locator="artifacts/audience-safe-attribution.txt",
        digest=D3,
        relationship_kinds=relationships,
        rights_review_required=False,
    )
    observations = (
        CandidateAvailabilityObservation(
            dimension="canonical_publication", outcome="available", checked_at=NOW
        ),
        CandidateAvailabilityObservation(
            dimension="subject_relationship", outcome="confirmed", checked_at=NOW
        ),
        CandidateAvailabilityObservation(
            dimension="profile_eligibility", outcome="eligible", checked_at=NOW
        ),
    )
    endpoints = (individual, collaborative_raw, collaborative_safe)
    eval_ids = ("evaluation_polished", "evaluation_group_raw", "evaluation_group_safe")
    candidate_ids = ("candidate_polished", "candidate_group_raw", "candidate_group_safe")
    sections = ("featured_work", "collaboration", "collaboration")
    kinds = (
        "ready_for_consideration",
        "rights_review_required",
        "ready_for_consideration",
    )
    evaluations = tuple(
        CandidateEvaluation(
            candidate_evaluation_id=eval_id,
            portfolio_id=portfolio.portfolio_id,
            portfolio_subject_id=subject.portfolio_subject_id,
            profile_binding_id=binding.profile_binding_id,
            profile_revision=profile.reference,
            requesting_actor=TEACHER,
            purpose="Evaluate showcase source.",
            source_endpoint=endpoint_value,
            availability_observations=observations,
            matched_profile_rule_ids=(f"rule_{section}",),
            eligible_section_ids=(section,),
            outcome="conditionally_eligible" if condition != "ready_for_consideration" else "eligible",
            reason_codes=("rights_review_required",) if condition != "ready_for_consideration" else (),
            evaluated_at=NOW,
            evaluator_contract_version="candidate_evaluator_v1",
        )
        for eval_id, endpoint_value, section, condition in zip(eval_ids, endpoints, sections, kinds)
    )
    candidates = tuple(
        PortfolioCandidate(
            candidate_id=candidate_id,
            portfolio_id=portfolio.portfolio_id,
            portfolio_subject_id=subject.portfolio_subject_id,
            profile_binding_id=binding.profile_binding_id,
            profile_revision=profile.reference,
            candidate_evaluation_id=evaluation.candidate_evaluation_id,
            source_endpoint=endpoint_value,
            eligible_profile_rule_ids=(f"rule_{section}",),
            eligible_section_ids=(section,),
            condition_state=condition,
            display_snapshot=candidate_id.replace("_", " ").title(),
            created_at=NOW,
            created_by=TEACHER,
        )
        for candidate_id, evaluation, endpoint_value, section, condition in zip(
            candidate_ids, evaluations, endpoints, sections, kinds
        )
    )
    selection_individual = PortfolioSelection(
        selection_id="selection_polished",
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=subject.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile.reference,
        candidate_id=candidates[0].candidate_id,
        candidate_evaluation_id=evaluations[0].candidate_evaluation_id,
        selected_at=NOW,
        selected_by=TEACHER,
    )
    selection_safe = PortfolioSelection(
        selection_id="selection_group_safe",
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=subject.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile.reference,
        candidate_id=candidates[2].candidate_id,
        candidate_evaluation_id=evaluations[2].candidate_evaluation_id,
        selected_at=NOW,
        selected_by=TEACHER,
    )
    placement_individual = PortfolioPlacement(
        placement_id="placement_polished",
        portfolio_id=portfolio.portfolio_id,
        profile_binding_id=binding.profile_binding_id,
        selection_id=selection_individual.selection_id,
        section_id="featured_work",
        presentation=PlacementPresentation(display_title="Polished Analysis"),
        placed_at=NOW,
        placed_by=TEACHER,
    )
    placement_safe = PortfolioPlacement(
        placement_id="placement_group_safe",
        portfolio_id=portfolio.portfolio_id,
        profile_binding_id=binding.profile_binding_id,
        selection_id=selection_safe.selection_id,
        section_id="collaboration",
        presentation=PlacementPresentation(display_title="Collaborative Recommendation"),
        placed_at=NOW,
        placed_by=TEACHER,
    )
    arrangements = (
        SectionArrangementRevision(
            arrangement_id="arrangement_featured",
            portfolio_id=portfolio.portfolio_id,
            profile_binding_id=binding.profile_binding_id,
            section_id="featured_work",
            arrangement_revision=1,
            placement_ids=(placement_individual.placement_id,),
            created_at=NOW,
            created_by=TEACHER,
        ),
        SectionArrangementRevision(
            arrangement_id="arrangement_collaboration",
            portfolio_id=portfolio.portfolio_id,
            profile_binding_id=binding.profile_binding_id,
            section_id="collaboration",
            arrangement_revision=1,
            placement_ids=(placement_safe.placement_id,),
            created_at=NOW,
            created_by=TEACHER,
        ),
    )
    composition = WorkingPortfolioCompositionRevision(
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=subject.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile.reference,
        composition_revision=1,
        selection_ids=(selection_individual.selection_id, selection_safe.selection_id),
        placement_ids=(placement_individual.placement_id, placement_safe.placement_id),
        arrangement_ids=tuple(item.arrangement_id for item in arrangements),
        created_at=NOW,
        created_by=TEACHER,
    )
    rule = profile.audience_rules[0]
    audience = AudienceContext(
        audience_context_id="audience_showcase",
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=subject.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile.reference,
        audience_rule_id=rule.audience_rule_id,
        audience_class=rule.audience_class,
        purpose=rule.purpose,
        subject_scope="portfolio_subject_and_reviewed_collaborators",
        allowed_content_classes=rule.allowed_content_classes,
        prohibited_content_classes=rule.prohibited_content_classes,
        required_review_classes=rule.required_review_classes,
        presentation_class=rule.presentation_class,
        retention_policy_reference=rule.retention_policy_reference,
        created_at=NOW,
        created_by=TEACHER,
    )
    edition_ref = SnapshotEditionRef(snapshot_series_id="snapshot_showcase", edition_number=1)
    mats = (
        SnapshotMaterializationRecord(
            materialization_id="materialization_polished",
            snapshot_edition=edition_ref,
            materialization_kind="copied_source",
            candidate_id=candidates[0].candidate_id,
            selection_id=selection_individual.selection_id,
            placement_id=placement_individual.placement_id,
            source_artifact=individual.source_artifact,
            source_digest=D1,
            output_digest=D1,
            byte_size=128,
            materialized_at=NOW,
            materialized_by=TEACHER,
        ),
        SnapshotMaterializationRecord(
            materialization_id="materialization_group_safe",
            snapshot_edition=edition_ref,
            materialization_kind="copied_source",
            candidate_id=candidates[2].candidate_id,
            selection_id=selection_safe.selection_id,
            placement_id=placement_safe.placement_id,
            source_artifact=collaborative_safe.source_artifact,
            source_digest=D3,
            output_digest=D3,
            byte_size=128,
            materialized_at=NOW,
            materialized_by=TEACHER,
        ),
    )
    entries = (
        SnapshotEntry(
            snapshot_entry_id="entry_polished",
            snapshot_edition=edition_ref,
            materialization_id=mats[0].materialization_id,
            section_id="featured_work",
            ordinal=1,
            relative_path="export/01-polished-analysis.txt",
            media_type="text/plain",
            content_class="student_work",
            display_title="Polished Analysis",
            source_placement_id=placement_individual.placement_id,
        ),
        SnapshotEntry(
            snapshot_entry_id="entry_group_safe",
            snapshot_edition=edition_ref,
            materialization_id=mats[1].materialization_id,
            section_id="collaboration",
            ordinal=1,
            relative_path="export/02-audience-safe-attribution.txt",
            media_type="text/plain",
            content_class="audience_safe_attribution",
            display_title="Collaborative Recommendation",
            source_placement_id=placement_safe.placement_id,
        ),
    )
    omission = SnapshotOmission(
        snapshot_omission_id="omission_group_raw",
        snapshot_edition=edition_ref,
        candidate_id=candidates[1].candidate_id,
        selection_id=None,
        placement_id=None,
        reason_code="rights_review_unresolved",
        audience_context_id=audience.audience_context_id,
        recorded_at=NOW,
        recorded_by=TEACHER,
        note="Original collaborative representation omitted from public edition.",
    )
    manifest = SnapshotManifest(
        manifest_id="manifest_showcase",
        manifest_contract_version="vitrine_snapshot_manifest_v1",
        snapshot_edition=edition_ref,
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=subject.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile.reference,
        composition_revision=composition.composition_revision,
        audience_context_id=audience.audience_context_id,
        entry_ids=tuple(item.snapshot_entry_id for item in entries),
        omission_ids=(omission.snapshot_omission_id,),
        created_at=NOW,
        created_by=TEACHER,
    )
    seal = SnapshotSeal(
        seal_id="seal_showcase",
        snapshot_edition=edition_ref,
        manifest_id=manifest.manifest_id,
        manifest_digest=D4,
        logical_inventory_digest=D6,
        sealed_at=NOW,
        sealed_by=TEACHER,
    )
    edition = SnapshotEdition(
        snapshot_series_id=edition_ref.snapshot_series_id,
        edition_number=edition_ref.edition_number,
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=subject.portfolio_subject_id,
        profile_binding_id=binding.profile_binding_id,
        profile_revision=profile.reference,
        composition_revision=composition.composition_revision,
        audience_context_id=audience.audience_context_id,
        manifest_id=manifest.manifest_id,
        seal_id=seal.seal_id,
        created_at=NOW,
        created_by=TEACHER,
    )
    return VitrineRecordGraph(
        portfolios=(portfolio,),
        portfolio_subjects=(subject,),
        subject_links=(link,),
        profile_families=(family,),
        profile_revisions=(profile,),
        profile_bindings=(binding,),
        candidate_evaluations=evaluations,
        candidates=candidates,
        selections=(selection_individual, selection_safe),
        placements=(placement_individual, placement_safe),
        arrangements=arrangements,
        compositions=(composition,),
        audience_contexts=(audience,),
        materializations=mats,
        snapshot_entries=entries,
        snapshot_omissions=(omission,),
        snapshot_manifests=(manifest,),
        snapshot_seals=(seal,),
        snapshot_editions=(edition,),
    )
