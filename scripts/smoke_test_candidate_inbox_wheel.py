"""Smoke issue #64 Candidate inbox from isolated installed Core/Vitrine wheels."""

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
            "Candidate inbox installed command failed "
            f"with exit code {result.returncode}:\n{detail}"
        )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix="vitrine-candidate-inbox-wheel-smoke-"
    ) as temporary:
        root = Path(temporary)
        environment = root / "venv"
        work = root / "work"
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

        code = r"""
import importlib.util
from datetime import datetime, timezone
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

from vitrine.candidate_inbox import (
    CandidateInboxQuery,
    get_candidate_inbox_detail,
    list_candidate_inbox,
)
from vitrine.candidate_services import CANDIDATE_EVALUATOR_CONTRACT_VERSION
from vitrine.candidate_state import project_candidate_state
from vitrine.models import (
    AcademicWorkRegistrationSnapshot,
    ActorAttribution,
    CandidateCurrentEvaluationPointerRevision,
    CandidateEvaluation,
    CandidateSourceEndpoint,
    CorePublicationSourceReference,
    Portfolio,
    PortfolioCandidate,
    PortfolioProfileBinding,
    PortfolioProfileFamily,
    PortfolioProfileLifecycleEvent,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    PortfolioSubject,
    ProducerSourceReference,
    ProfileApplicability,
    ProfileSectionDefinition,
    SourcePrivacyMetadata,
)
from vitrine.storage import commit_record_batch, load_current_state

NOW = datetime(2026, 9, 5, 20, 0, tzinfo=timezone.utc)
actor = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="wheel_teacher",
    owning_system="vitrine",
    role_snapshot="teacher",
)
workspace = ensure_workspace_root(Path("workspace"), create=True)

work_ref = ModuleWorkRef("wheel_fixture", "class_1", "work_1")
work_root = module_work_dir(workspace, work_ref)
work_root.mkdir(parents=True, exist_ok=True)
registration = register_academic_work(
    workspace,
    AcademicWorkRegistrationRequest(
        work=work_ref,
        producer_contract_version="wheel_fixture_academic_work_v1",
        title="Synthetic wheel work",
        work_kind="assignment",
        academic_intent="formative",
        lifecycle="active",
        source_records=(),
    ),
).registration
manifest = (
    work_root
    / "exports"
    / "manifests"
    / "wheel_results"
    / "1.json"
)
manifest.parent.mkdir(parents=True, exist_ok=True)
manifest.write_text("{}", encoding="utf-8")
publication = publish_manifest_revision(
    workspace,
    PublicationManifestRequest(
        work=work_ref,
        source_record=None,
        publication_kind="academic_result_set",
        capabilities=("points",),
        record_set_id="wheel_results",
        record_set_revision=1,
        manifest_contract_version="wheel_fixture_manifest_v1",
        manifest_path=manifest.relative_to(workspace).as_posix(),
        academic_work_registration_revision=registration.registration_revision,
    ),
).publication

subject = PortfolioSubject(
    portfolio_subject_id="subject_wheel",
    created_at=NOW,
    created_by=actor,
    display_name_snapshot="Synthetic Wheel Student",
)
portfolio = Portfolio(
    portfolio_id="portfolio_wheel",
    portfolio_subject_id=subject.portfolio_subject_id,
    created_at=NOW,
    created_by=actor,
    title_snapshot="Wheel Candidate Inbox",
)
family = PortfolioProfileFamily(
    profile_family_id="family_wheel",
    label="Wheel Profiles",
    purpose_kind="improvement",
    created_at=NOW,
    created_by=actor,
)
revision = PortfolioProfileRevision(
    portfolio_profile_id="profile_wheel",
    profile_revision=1,
    profile_family_id=family.profile_family_id,
    predecessor_revision=None,
    label="Wheel Profile",
    purpose_kind="improvement",
    applicability=ProfileApplicability(),
    sections=(
        ProfileSectionDefinition(
            section_id="evidence",
            label="Evidence",
            purpose="Synthetic installed-wheel evidence.",
            order=1,
            obligation="optional",
            minimum_placements=0,
            maximum_placements=None,
            allowed_candidate_kinds=("assessment_summary",),
            required_relationship_kinds=(),
            reflection_requirement="none",
        ),
    ),
    audience_rules=(),
    created_at=NOW,
    created_by=actor,
    source_authority_references=("wheel_fixture",),
)
requirement = PortfolioProfileRequirement(
    portfolio_profile_id=revision.portfolio_profile_id,
    profile_revision=revision.profile_revision,
    requirement_id="evidence_rule",
    requirement_kind="section",
    obligation="optional",
    title="Synthetic evidence Candidate rule",
    statement="Synthetic evidence may be considered for this Profile section.",
    scope_kind="section",
    satisfaction_class="candidate_eligibility",
    authority_references=("wheel_fixture",),
    scope_reference="evidence",
)
lifecycle = PortfolioProfileLifecycleEvent(
    profile_lifecycle_event_id="profile_event_wheel",
    profile_revision=revision.reference,
    event_kind="activated",
    event_at=NOW,
    effective_at=NOW,
    actor=actor,
    reason="Activate wheel fixture Profile.",
    authority_reference="wheel_fixture",
)
binding = PortfolioProfileBinding(
    profile_binding_id="binding_wheel_a",
    portfolio_id=portfolio.portfolio_id,
    profile_revision=revision.reference,
    bound_at=NOW,
    bound_by=actor,
    binding_reason="Synthetic installed-wheel binding.",
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
    academic_work_registration_revision=(
        publication.academic_work_registration_revision
    ),
    registration_snapshot=registration_snapshot,
    supersedes_publication_id=publication.supersedes_publication_id,
    observed_series_state="current_selectable",
    observed_withdrawal_state="not_withdrawn",
    verified_at=NOW,
)
privacy = SourcePrivacyMetadata(
    classification="student_record",
    subject_scope="individual",
    metadata_visibility="portfolio_review",
    collaborator_information_present=False,
    third_party_information_present=False,
    rights_review_required=False,
    redaction_review_required=False,
    multi_subject_review_required=False,
    minimum_necessary_projection_required=True,
    policy_reference="wheel_fixture",
)


def endpoint(source_id: str) -> CandidateSourceEndpoint:
    return CandidateSourceEndpoint(
        core_publication=core_reference,
        producer_source=ProducerSourceReference(
            producer_module_id="wheel_fixture",
            producer_contract_version="wheel_fixture_academic_work_v1",
            source_record_kind="assessment_attempt",
            source_record_id=source_id,
            source_record_contract_version=None,
            native_revision=1,
            native_lifecycle="submitted",
            native_disposition=None,
            lineage_reference=None,
            reader_contract_version="wheel_reader_v1",
            projection_contract_version="wheel_projection_v1",
        ),
        source_artifact=None,
        subject_relationship_assertions=(),
        source_privacy=privacy,
    )


positive = CandidateEvaluation(
    candidate_evaluation_id="evaluation_positive",
    portfolio_id=portfolio.portfolio_id,
    portfolio_subject_id=subject.portfolio_subject_id,
    profile_binding_id=binding.profile_binding_id,
    profile_revision=revision.reference,
    requesting_actor=actor,
    purpose="improvement",
    source_endpoint=endpoint("source_positive"),
    availability_observations=(),
    matched_profile_rule_ids=("evidence_rule",),
    eligible_section_ids=("evidence",),
    outcome="eligible",
    reason_codes=(),
    evaluated_at=NOW,
    evaluator_contract_version=CANDIDATE_EVALUATOR_CONTRACT_VERSION,
)
candidate = PortfolioCandidate(
    candidate_id="candidate_positive",
    portfolio_id=portfolio.portfolio_id,
    portfolio_subject_id=subject.portfolio_subject_id,
    profile_binding_id=binding.profile_binding_id,
    profile_revision=revision.reference,
    candidate_evaluation_id=positive.candidate_evaluation_id,
    source_endpoint=positive.source_endpoint,
    eligible_profile_rule_ids=("evidence_rule",),
    eligible_section_ids=("evidence",),
    condition_state="ready_for_consideration",
    display_snapshot="Synthetic positive source",
    created_at=NOW,
    created_by=actor,
)
pointer = CandidateCurrentEvaluationPointerRevision(
    candidate_id=candidate.candidate_id,
    pointer_revision=1,
    current_candidate_evaluation_id=positive.candidate_evaluation_id,
    updated_at=NOW,
    updated_by=actor,
    reason="candidate_created",
)
negative = CandidateEvaluation(
    candidate_evaluation_id="evaluation_negative",
    portfolio_id=portfolio.portfolio_id,
    portfolio_subject_id=subject.portfolio_subject_id,
    profile_binding_id=binding.profile_binding_id,
    profile_revision=revision.reference,
    requesting_actor=actor,
    purpose="improvement",
    source_endpoint=endpoint("source_negative"),
    availability_observations=(),
    matched_profile_rule_ids=(),
    eligible_section_ids=(),
    outcome="ineligible",
    reason_codes=("candidate:profile_ineligible",),
    evaluated_at=NOW,
    evaluator_contract_version=CANDIDATE_EVALUATOR_CONTRACT_VERSION,
)
unresolved = CandidateEvaluation(
    candidate_evaluation_id="evaluation_unresolved",
    portfolio_id=portfolio.portfolio_id,
    portfolio_subject_id=subject.portfolio_subject_id,
    profile_binding_id=binding.profile_binding_id,
    profile_revision=revision.reference,
    requesting_actor=actor,
    purpose="improvement",
    source_endpoint=endpoint("source_unresolved"),
    availability_observations=(),
    matched_profile_rule_ids=(),
    eligible_section_ids=(),
    outcome="unresolved",
    reason_codes=("candidate:subject_unresolved",),
    evaluated_at=NOW,
    evaluator_contract_version=CANDIDATE_EVALUATOR_CONTRACT_VERSION,
)
suppressed = CandidateEvaluation(
    candidate_evaluation_id="evaluation_suppressed",
    portfolio_id=portfolio.portfolio_id,
    portfolio_subject_id=subject.portfolio_subject_id,
    profile_binding_id=binding.profile_binding_id,
    profile_revision=revision.reference,
    requesting_actor=actor,
    purpose="improvement",
    source_endpoint=endpoint("source_suppressed"),
    availability_observations=(),
    matched_profile_rule_ids=(),
    eligible_section_ids=(),
    outcome="suppressed",
    reason_codes=("candidate:suppressed",),
    evaluated_at=NOW,
    evaluator_contract_version=CANDIDATE_EVALUATOR_CONTRACT_VERSION,
)

commit_record_batch(
    workspace,
    (
        subject,
        portfolio,
        family,
        revision,
        requirement,
        lifecycle,
        binding,
        positive,
        candidate,
        pointer,
        negative,
        unresolved,
        suppressed,
    ),
    expected_state_revision=None,
)
before = load_current_state(workspace).state_revision

state = project_candidate_state((positive, candidate, pointer, negative, unresolved, suppressed))
resolution = state.resolve_current_evaluation(candidate.candidate_id)
assert resolution.mode == "explicit"
assert resolution.evaluation == positive

listing = list_candidate_inbox(workspace)
assert listing.matched_count == 3
assert {item.evaluation_outcome for item in listing.items} == {
    "eligible",
    "ineligible",
    "unresolved",
}
assert "evaluation_suppressed" not in repr(listing)
positive_item = next(item for item in listing.items if item.candidate_id is not None)
detail = get_candidate_inbox_detail(workspace, positive_item.entry_id)
assert detail.evaluation == positive
assert detail.pointer_history == (pointer,)
assert load_current_state(workspace).state_revision == before

binding_b = PortfolioProfileBinding(
    profile_binding_id="binding_wheel_b",
    portfolio_id=portfolio.portfolio_id,
    profile_revision=revision.reference,
    bound_at=NOW,
    bound_by=actor,
    binding_reason="Synthetic Profile rebinding.",
    predecessor_binding_id=binding.profile_binding_id,
)
commit_record_batch(
    workspace,
    (binding_b,),
    expected_state_revision=before,
)
before_stale_read = load_current_state(workspace).state_revision
stale = list_candidate_inbox(workspace, CandidateInboxQuery(stale_only=True))
assert stale.matched_count == 3
assert all(
    "candidate_inbox.profile_binding_changed" in item.stale_reason_codes
    for item in stale.items
)
assert load_current_state(workspace).state_revision == before_stale_read

for name in ("scoreform", "quillan", "concord", "meridian"):
    assert importlib.util.find_spec(name) is None
"""
        _run([str(python), "-c", code], cwd=work, env=env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS isolated Candidate inbox wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Candidate inbox wheel smoke test failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
