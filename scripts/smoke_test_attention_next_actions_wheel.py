"""Smoke issue #69 attention from isolated Core and Vitrine wheels."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def _venv_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "(no child output)"
        raise RuntimeError(
            "attention installed command failed "
            f"with exit code {result.returncode}:\n{detail}"
        )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="vitrine-attention-wheel-smoke-") as temporary:
        root = Path(temporary)
        environment = root / "venv"
        work = root / "work"
        workspace = root / "workspace"
        work.mkdir()
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        _run(
            [str(python), "-m", "pip", "install", str(core_wheel.resolve())],
            cwd=work,
            env=env,
        )
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                str(vitrine_wheel.resolve()),
            ],
            cwd=work,
            env=env,
        )
        _run([str(python), "-m", "pip", "check"], cwd=work, env=env)

        code = r'''\
import importlib.metadata
import importlib.util
import sys
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

from pds_core.registry_services import (
    AcademicWorkRegistrationRequest,
    PublicationManifestRequest,
    publish_manifest_revision,
    register_academic_work,
)
from pds_core.routes import module_work_dir
from pds_core.routing_models import ModuleWorkRef
from pds_core.workspace import ensure_workspace_root

from vitrine import cli
from vitrine.attention import (
    VITRINE_ATTENTION_CONTRACT_VERSION,
    VitrineAttentionQuery,
    evaluate_vitrine_attention,
)
from vitrine.attention_menu import run_attention_menu
from vitrine.candidate_services import CANDIDATE_EVALUATOR_CONTRACT_VERSION
from vitrine.curation_services import (
    CurationAuthorityDecision,
    CurationAuthorityRequest,
    place_selection,
    select_candidate_directly,
)
from vitrine.current_portfolio_build import prepare_current_portfolio_build
from vitrine.current_portfolio_execution import (
    execute_prepared_current_portfolio_build,
    execute_prepared_current_portfolio_plan,
)
from vitrine.models import (
    AcademicWorkRegistrationSnapshot,
    ActorAttribution,
    CandidateCurrentEvaluationPointerRevision,
    CandidateEvaluation,
    CandidateSourceEndpoint,
    CorePublicationSourceReference,
    CurationTargetRef,
    Portfolio,
    PortfolioCandidate,
    PortfolioProfileBinding,
    PortfolioProfileFamily,
    PortfolioProfileLifecycleEvent,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    PortfolioReflection,
    PortfolioSelection,
    PortfolioSubject,
    ProducerSourceReference,
    ProfileApplicability,
    ProfileAudienceRule,
    ProfileSectionDefinition,
    SourceArtifactReference,
    SourcePrivacyMetadata,
)
from vitrine.snapshot_distribution import abandon_snapshot_build_attempt_after_recovery
from vitrine.snapshot_materialization import (
    SnapshotBuildAuthorityDecision,
    SnapshotBuildAuthorityRequest,
    SnapshotRendererRegistry,
    SnapshotSourceProviderRegistry,
)
from vitrine.snapshot_services import (
    SnapshotWorkflowError,
    execute_snapshot_build_attempt,
    start_snapshot_build_attempt,
)
from vitrine.storage import commit_record_batch, load_current_state
from vitrine.working_composition import (
    freeze_prepared_working_composition,
    prepare_working_composition,
)

NOW = datetime(2026, 9, 9, 18, 0, tzinfo=timezone.utc)
TEACHER = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="attention_wheel_teacher",
    owning_system="local",
    role_snapshot="teacher",
)
STUDENT = ActorAttribution(
    actor_kind="external_actor",
    actor_id="attention_wheel_student",
    owning_system="local",
    role_snapshot="student",
)


class CurationGate:
    def authorize(self, request: CurationAuthorityRequest) -> CurationAuthorityDecision:
        return CurationAuthorityDecision(
            outcome="allowed",
            authority_reference="attention_wheel_curation_authority",
            reason_codes=("wheel_smoke",),
        )


class SnapshotGate:
    def __init__(self, outcome="allowed"):
        self.outcome = outcome

    def authorize(
        self, request: SnapshotBuildAuthorityRequest
    ) -> SnapshotBuildAuthorityDecision:
        return SnapshotBuildAuthorityDecision(
            outcome=self.outcome,
            authority_reference=(
                "attention_wheel_snapshot_authority"
                if self.outcome == "allowed"
                else None
            ),
            reason_codes=("wheel_smoke",),
        )


def get_summary(report, code):
    values = tuple(item for item in report.summaries if item.code == code)
    assert len(values) <= 1
    return values[0] if values else None


assert importlib.metadata.version("pds-core") == "0.6.3"
workspace = ensure_workspace_root(Path(sys.argv[1]), create=True)

work_ref = ModuleWorkRef("scoreform", "class_attention", "work_attention")
work_root = module_work_dir(workspace, work_ref)
work_root.mkdir(parents=True, exist_ok=True)
registration = register_academic_work(
    workspace,
    AcademicWorkRegistrationRequest(
        work=work_ref,
        producer_contract_version="scoreform_academic_work_v1",
        title="Synthetic attention work",
        work_kind="assignment",
        academic_intent="formative",
        lifecycle="active",
        source_records=(),
    ),
).registration
manifest = work_root / "exports" / "manifests" / "attention_results" / "1.json"
manifest.parent.mkdir(parents=True, exist_ok=True)
manifest.write_text("{}", encoding="utf-8")
publication = publish_manifest_revision(
    workspace,
    PublicationManifestRequest(
        work=work_ref,
        source_record=None,
        publication_kind="academic_result_set",
        capabilities=("multiple_attempts", "points", "question_evidence"),
        record_set_id="attention_results",
        record_set_revision=1,
        manifest_contract_version="scoreform_academic_result_manifest_v1",
        manifest_path=manifest.relative_to(workspace).as_posix(),
        academic_work_registration_revision=registration.registration_revision,
    ),
).publication

subject = PortfolioSubject(
    portfolio_subject_id="subject_attention_wheel",
    created_at=NOW,
    created_by=TEACHER,
    display_name_snapshot="Synthetic Attention Student",
)
portfolio = Portfolio(
    portfolio_id="portfolio_attention_wheel",
    portfolio_subject_id=subject.portfolio_subject_id,
    created_at=NOW,
    created_by=TEACHER,
    title_snapshot="Attention Wheel Smoke",
)
family = PortfolioProfileFamily(
    profile_family_id="family_attention_wheel",
    label="Attention Wheel Profiles",
    purpose_kind="improvement",
    created_at=NOW,
    created_by=TEACHER,
)
evidence_section = ProfileSectionDefinition(
    section_id="evidence",
    label="Evidence",
    purpose="Synthetic ScoreForm assessment evidence.",
    order=1,
    obligation="optional",
    minimum_placements=0,
    maximum_placements=1,
    allowed_candidate_kinds=("assessment_summary",),
    required_relationship_kinds=(),
    reflection_requirement="none",
)
reflection_section = ProfileSectionDefinition(
    section_id="reflection",
    label="Reflection",
    purpose="One exact student Reflection.",
    order=2,
    obligation="required",
    minimum_placements=0,
    maximum_placements=0,
    allowed_candidate_kinds=("student_work",),
    required_relationship_kinds=(),
    reflection_requirement="required",
)
profile = PortfolioProfileRevision(
    portfolio_profile_id="profile_attention_wheel",
    profile_revision=1,
    profile_family_id=family.profile_family_id,
    predecessor_revision=None,
    label="Attention Wheel Profile",
    purpose_kind="improvement",
    applicability=ProfileApplicability(school_years=("2026-2027",)),
    sections=(evidence_section, reflection_section),
    audience_rules=(
        ProfileAudienceRule(
            audience_rule_id="student_review",
            audience_class="student",
            purpose="Review this exact synthetic portfolio package.",
            allowed_content_classes=("reflection",),
            prohibited_content_classes=("assessment_summary",),
            required_review_classes=(),
            presentation_class="student_portfolio",
        ),
    ),
    created_at=NOW,
    created_by=TEACHER,
    source_authority_references=("attention_wheel_policy",),
)
evidence_requirement = PortfolioProfileRequirement(
    portfolio_profile_id=profile.portfolio_profile_id,
    profile_revision=profile.profile_revision,
    requirement_id="evidence_candidate",
    requirement_kind="section",
    obligation="optional",
    title="Assessment evidence",
    statement="Assessment evidence may be considered.",
    scope_kind="section",
    satisfaction_class="candidate_eligibility",
    scope_reference=evidence_section.section_id,
    authority_references=("attention_wheel_policy",),
)
reflection_requirement = PortfolioProfileRequirement(
    portfolio_profile_id=profile.portfolio_profile_id,
    profile_revision=profile.profile_revision,
    requirement_id="reflection_required",
    requirement_kind="reflection",
    obligation="required",
    title="Reflection required",
    statement="One exact section Reflection is required.",
    scope_kind="section",
    satisfaction_class="reflection_presence",
    scope_reference=reflection_section.section_id,
    authority_references=("attention_wheel_policy",),
)
lifecycle = PortfolioProfileLifecycleEvent(
    profile_lifecycle_event_id="profile_event_attention_wheel",
    profile_revision=profile.reference,
    event_kind="activated",
    event_at=NOW,
    effective_at=NOW,
    actor=TEACHER,
    reason="Activate synthetic attention Profile.",
    authority_reference="attention_wheel_policy",
)
binding = PortfolioProfileBinding(
    profile_binding_id="binding_attention_wheel",
    portfolio_id=portfolio.portfolio_id,
    profile_revision=profile.reference,
    bound_at=NOW,
    bound_by=TEACHER,
    binding_reason="Synthetic attention binding.",
)
registration_snapshot = AcademicWorkRegistrationSnapshot(
    registration_revision=registration.registration_revision,
    producer_contract_version=registration.producer_contract_version,
    title_snapshot=registration.title,
    work_kind=registration.work_kind,
    academic_intent=registration.academic_intent,
    lifecycle=registration.lifecycle,
    source_records=registration.source_records,
)
core_reference = CorePublicationSourceReference(
    core_publication_schema_version=publication.schema_version,
    publication_id=publication.publication_id,
    work=publication.work,
    source_record=publication.source_record,
    publication_kind=publication.publication_kind,
    capabilities=publication.capabilities,
    record_set_id=publication.record_set_id,
    record_set_revision=publication.record_set_revision,
    manifest_contract_version=publication.manifest_contract_version,
    manifest_path=publication.manifest_path,
    manifest_digest_algorithm=publication.manifest_digest_algorithm,
    manifest_digest=publication.manifest_digest,
    published_at=publication.published_at,
    academic_work_registration_revision=publication.academic_work_registration_revision,
    registration_snapshot=registration_snapshot,
    supersedes_publication_id=publication.supersedes_publication_id,
    observed_series_state="current_selectable",
    observed_withdrawal_state="not_withdrawn",
    verified_at=NOW,
)
privacy = SourcePrivacyMetadata(
    classification="student_record",
    subject_scope="single_subject",
    metadata_visibility="internal",
    collaborator_information_present=False,
    third_party_information_present=False,
    rights_review_required=False,
    redaction_review_required=False,
    multi_subject_review_required=False,
    minimum_necessary_projection_required=True,
    policy_reference="attention_wheel_policy",
)
artifact = SourceArtifactReference(
    artifact_id="scoreform_attempt_summary",
    artifact_kind="assessment_summary",
    representation_kind="scoreform:attempt_summary",
    media_type="application/vnd.pds.vitrine.scoreform-attempt-summary+json",
    source_locator=None,
    native_revision=1,
    source_digest=None,
    byte_size=None,
    language=None,
    accessibility_relationship=None,
)
endpoint = CandidateSourceEndpoint(
    core_publication=core_reference,
    producer_source=ProducerSourceReference(
        producer_module_id="scoreform",
        producer_contract_version="scoreform_academic_work_v1",
        source_record_kind="academic_result_attempt",
        source_record_id="scoreform_attempt_attention_1",
        source_record_contract_version=None,
        native_revision=1,
        native_lifecycle="recorded",
        native_disposition="attempt",
        lineage_reference="scoreform_work_attention",
        reader_contract_version="vitrine_installed_producer_reader_v1",
        projection_contract_version="vitrine_candidate_projection_v1",
    ),
    source_artifact=artifact,
    subject_relationship_assertions=(),
    source_privacy=privacy,
)
evaluation = CandidateEvaluation(
    candidate_evaluation_id="evaluation_attention_wheel",
    portfolio_id=portfolio.portfolio_id,
    portfolio_subject_id=subject.portfolio_subject_id,
    profile_binding_id=binding.profile_binding_id,
    profile_revision=profile.reference,
    requesting_actor=TEACHER,
    purpose="improvement",
    source_endpoint=endpoint,
    availability_observations=(),
    matched_profile_rule_ids=(evidence_requirement.requirement_id,),
    eligible_section_ids=(evidence_section.section_id,),
    outcome="eligible",
    reason_codes=(),
    evaluated_at=NOW,
    evaluator_contract_version=CANDIDATE_EVALUATOR_CONTRACT_VERSION,
)
candidate = PortfolioCandidate(
    candidate_id="candidate_attention_wheel",
    portfolio_id=portfolio.portfolio_id,
    portfolio_subject_id=subject.portfolio_subject_id,
    profile_binding_id=binding.profile_binding_id,
    profile_revision=profile.reference,
    candidate_evaluation_id=evaluation.candidate_evaluation_id,
    source_endpoint=endpoint,
    eligible_profile_rule_ids=(evidence_requirement.requirement_id,),
    eligible_section_ids=(evidence_section.section_id,),
    condition_state="ready_for_consideration",
    display_snapshot="Synthetic ScoreForm assessment summary",
    created_at=NOW,
    created_by=TEACHER,
)
pointer = CandidateCurrentEvaluationPointerRevision(
    candidate_id=candidate.candidate_id,
    pointer_revision=1,
    current_candidate_evaluation_id=evaluation.candidate_evaluation_id,
    updated_at=NOW,
    updated_by=TEACHER,
    reason="candidate_created",
)
reflection = PortfolioReflection(
    reflection_id="reflection_attention_wheel",
    reflection_revision=1,
    portfolio_id=portfolio.portfolio_id,
    portfolio_subject_id=subject.portfolio_subject_id,
    profile_binding_id=binding.profile_binding_id,
    profile_revision=profile.reference,
    reflection_requirement_id=reflection_requirement.requirement_id,
    prompt_id="attention_wheel_prompt",
    prompt_version="1",
    prompt_snapshot="Explain what this portfolio evidence means.",
    author=STUDENT,
    target_scope="section",
    target_references=(
        CurationTargetRef(
            target_kind="section",
            target_id=reflection_section.section_id,
        ),
    ),
    content_mode="inline_text",
    language="en",
    content_format="plain_text",
    content="This exact portfolio evidence shows one documented learning step.",
    created_at=NOW,
)

commit_record_batch(
    workspace,
    (
        subject,
        portfolio,
        family,
        profile,
        evidence_requirement,
        reflection_requirement,
        lifecycle,
        binding,
        evaluation,
        candidate,
        pointer,
        reflection,
    ),
    expected_state_revision=None,
)

initial_revision = load_current_state(workspace).state_revision
initial_attention = evaluate_vitrine_attention(
    workspace,
    VitrineAttentionQuery(portfolio_id=portfolio.portfolio_id),
)
assert initial_attention.contract_version == "vitrine_attention_next_actions_v1"
assert VITRINE_ATTENTION_CONTRACT_VERSION == "vitrine_attention_next_actions_v1"
assert get_summary(initial_attention, "vitrine_candidate_review_pending").count == 1
assert get_summary(
    initial_attention, "vitrine_working_composition_refresh_needed"
).count == 1
assert load_current_state(workspace).state_revision == initial_revision

selected = select_candidate_directly(
    workspace,
    portfolio_id=portfolio.portfolio_id,
    candidate_id=candidate.candidate_id,
    selected_by=TEACHER,
    proposed_section_ids=(evidence_section.section_id,),
    expected_state_revision=load_current_state(workspace).state_revision,
    authority_gate=CurationGate(),
)
selection = next(
    item for item in selected.records if isinstance(item, PortfolioSelection)
)
unplaced = evaluate_vitrine_attention(
    workspace,
    VitrineAttentionQuery(portfolio_id=portfolio.portfolio_id),
)
assert get_summary(unplaced, "vitrine_selection_unplaced").count == 1

placed = place_selection(
    workspace,
    portfolio_id=portfolio.portfolio_id,
    selection_id=selection.selection_id,
    section_id=evidence_section.section_id,
    placed_by=TEACHER,
    expected_state_revision=load_current_state(workspace).state_revision,
    expected_arrangement_pointer_revision=None,
    authority_gate=CurationGate(),
)
assert placed.records

working = prepare_working_composition(workspace, portfolio.portfolio_id)
assert working.disposition == "create_initial"
frozen = freeze_prepared_working_composition(
    workspace,
    working,
    created_by=TEACHER,
    authority_gate=CurationGate(),
)
assert frozen.disposition == "created"

prepared = prepare_current_portfolio_build(
    workspace,
    portfolio.portfolio_id,
    audience_rule_id="student_review",
)
assert prepared.working_composition_disposition == "reuse_exact_current"
assert prepared.ready_for_plan_execution
assert any(
    item.permitted_omission_reason == "audience_prohibited"
    for item in prepared.planned_items
)
assert len(prepared.generated_reflections) == 1
plan_execution = execute_prepared_current_portfolio_plan(
    workspace,
    prepared,
    actor=TEACHER,
)
attempt_1 = start_snapshot_build_attempt(
    workspace,
    snapshot_build_plan_id=plan_execution.snapshot_build_plan_id,
    started_by=TEACHER,
    expected_state_revision=load_current_state(workspace).state_revision,
)
recovery_attention = evaluate_vitrine_attention(
    workspace,
    VitrineAttentionQuery(portfolio_id=portfolio.portfolio_id),
)
assert get_summary(
    recovery_attention, "vitrine_snapshot_recovery_required"
).count == 1

abandon_snapshot_build_attempt_after_recovery(
    workspace,
    snapshot_build_attempt_id=attempt_1.attempt.snapshot_build_attempt_id,
    expected_state_revision=load_current_state(workspace).state_revision,
    recovered_by=TEACHER,
    authority_reference="attention_wheel_recovery_authority",
    reason="Synthetic wheel smoke abandons the intentionally incomplete Attempt.",
)
attempt_2 = start_snapshot_build_attempt(
    workspace,
    snapshot_build_plan_id=plan_execution.snapshot_build_plan_id,
    started_by=TEACHER,
    expected_state_revision=load_current_state(workspace).state_revision,
)
try:
    execute_snapshot_build_attempt(
        workspace,
        snapshot_build_attempt_id=attempt_2.attempt.snapshot_build_attempt_id,
        expected_state_revision=load_current_state(workspace).state_revision,
        authority_gate=SnapshotGate("denied"),
        source_providers=SnapshotSourceProviderRegistry(),
        renderers=SnapshotRendererRegistry(),
    )
except SnapshotWorkflowError as error:
    assert error.code == "snapshot.authority_denied"
else:
    raise AssertionError("denied Snapshot authority did not fail the Attempt")

failed_attention = evaluate_vitrine_attention(
    workspace,
    VitrineAttentionQuery(portfolio_id=portfolio.portfolio_id),
)
assert get_summary(failed_attention, "vitrine_snapshot_build_failed").count == 1

reprepared = prepare_current_portfolio_build(
    workspace,
    portfolio.portfolio_id,
    audience_rule_id="student_review",
)
result = execute_prepared_current_portfolio_build(
    workspace,
    reprepared,
    actor=TEACHER,
    authority_gate=SnapshotGate(),
)
assert result.attempt_terminal_outcome == "sealed"
assert result.current_pointer_advanced is False
post_build_revision = load_current_state(workspace).state_revision
sealed_attention = evaluate_vitrine_attention(
    workspace,
    VitrineAttentionQuery(portfolio_id=portfolio.portfolio_id),
)
omission = get_summary(sealed_attention, "vitrine_omission_audience_prohibited")
assert omission is not None and omission.count == 1
assert get_summary(sealed_attention, "vitrine_snapshot_build_failed") is None
assert get_summary(sealed_attention, "vitrine_export_pending_after_seal") is None
assert get_summary(sealed_attention, "vitrine_export_verification_problem") is None
assert load_current_state(workspace).state_revision == post_build_revision

export_files = tuple(path for path in result.export_path.rglob("*") if path.is_file())
assert len(export_files) == 1
export_files[0].write_bytes(export_files[0].read_bytes() + b"tamper")
verification_attention = evaluate_vitrine_attention(
    workspace,
    VitrineAttentionQuery(portfolio_id=portfolio.portfolio_id),
)
verification_problem = get_summary(
    verification_attention, "vitrine_export_verification_problem"
)
assert verification_problem is not None and verification_problem.count == 1
assert load_current_state(workspace).state_revision == post_build_revision

output = StringIO()
status = cli.main(
    [
        "attention",
        "list",
        "--portfolio-id",
        portfolio.portfolio_id,
        "--workspace-root",
        str(workspace),
    ],
    output=output,
)
assert status == 0
assert "vitrine_export_verification_problem" in output.getvalue()
assert "action=verify_snapshot_export" in output.getvalue()
assert load_current_state(workspace).state_revision == post_build_revision

menu_output = StringIO()
run_attention_menu(
    output=menu_output,
    clear_fn=lambda: None,
    workspace_root=workspace,
    portfolio_id=portfolio.portfolio_id,
)
assert "Attention / Next Actions" in menu_output.getvalue()
assert "Action ID: verify_snapshot_export" in menu_output.getvalue()
assert load_current_state(workspace).state_revision == post_build_revision

parser = cli.build_parser()
parsed = parser.parse_args(["attention", "list", "--portfolio-id", portfolio.portfolio_id])
assert parsed.command == "attention"
assert parsed.attention_command == "list"

for name in (
    "scoreform",
    "quillan",
    "concord",
    "portia",
    "meridian",
    "paper_data_suite",
):
    assert importlib.util.find_spec(name) is None
'''
        _run([str(python), "-c", code, str(workspace)], cwd=work, env=env)
        if list(work.iterdir()):
            raise RuntimeError("attention wheel smoke left working-directory residue")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS isolated Vitrine attention wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Vitrine attention wheel smoke test failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
