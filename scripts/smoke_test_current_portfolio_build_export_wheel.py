"""Smoke issue #68 Build/Export from isolated Core and Vitrine wheels."""

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
            "Current Portfolio Build/Export installed command failed "
            f"with exit code {result.returncode}:\n{detail}"
        )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix="vitrine-current-portfolio-wheel-smoke-"
    ) as temporary:
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
import importlib.util
import sys
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

from pds_core.workspace import ensure_workspace_root

from vitrine import cli
from vitrine.curation_services import (
    CurationAuthorityDecision,
    CurationAuthorityRequest,
)
from vitrine.current_portfolio_build import (
    CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION,
    prepare_current_portfolio_build,
)
from vitrine.current_portfolio_execution import execute_prepared_current_portfolio_build
from vitrine.models import (
    ActorAttribution,
    CurationTargetRef,
    Portfolio,
    PortfolioProfileBinding,
    PortfolioProfileFamily,
    PortfolioProfileLifecycleEvent,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    PortfolioReflection,
    PortfolioSubject,
    ProfileApplicability,
    ProfileAudienceRule,
    ProfileSectionDefinition,
)
from vitrine.snapshot_materialization import (
    SnapshotBuildAuthorityDecision,
    SnapshotBuildAuthorityRequest,
)
from vitrine.storage import commit_record_batch, load_current_state
from vitrine.workflow_views import show_snapshot_series
from vitrine.working_composition import (
    freeze_prepared_working_composition,
    prepare_working_composition,
)

NOW = datetime(2026, 9, 9, 1, 0, tzinfo=timezone.utc)
TEACHER = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="wheel_smoke_teacher",
    owning_system="local",
    role_snapshot="teacher",
)
STUDENT = ActorAttribution(
    actor_kind="external_actor",
    actor_id="wheel_smoke_student",
    owning_system="local",
    role_snapshot="student",
)
REFLECTION_TEXT = "I can explain what this exact portfolio evidence means."


class CurationGate:
    def authorize(self, request: CurationAuthorityRequest) -> CurationAuthorityDecision:
        assert request.operation == "compose_portfolio"
        return CurationAuthorityDecision(
            outcome="allowed",
            authority_reference="wheel_smoke_curation_authority",
            reason_codes=("wheel_smoke",),
        )


class SnapshotGate:
    def __init__(self):
        self.requests = []

    def authorize(
        self, request: SnapshotBuildAuthorityRequest
    ) -> SnapshotBuildAuthorityDecision:
        self.requests.append(request)
        return SnapshotBuildAuthorityDecision(
            outcome="allowed",
            authority_reference="wheel_smoke_snapshot_authority",
            reason_codes=("wheel_smoke",),
        )


workspace = ensure_workspace_root(Path(sys.argv[1]), create=True)
subject = PortfolioSubject(
    portfolio_subject_id="subject_current_portfolio_smoke",
    created_at=NOW,
    created_by=TEACHER,
    display_name_snapshot="Synthetic Wheel Student",
)
portfolio = Portfolio(
    portfolio_id="portfolio_current_portfolio_smoke",
    portfolio_subject_id=subject.portfolio_subject_id,
    created_at=NOW,
    created_by=TEACHER,
    title_snapshot="Current Portfolio Wheel Smoke",
)
family = PortfolioProfileFamily(
    profile_family_id="family_current_portfolio_smoke",
    label="Current Portfolio Smoke Profiles",
    purpose_kind="showcase",
    created_at=NOW,
    created_by=TEACHER,
)
section = ProfileSectionDefinition(
    section_id="reflection",
    label="Reflection",
    purpose="One exact student Reflection; no producer Artifact is required.",
    order=1,
    obligation="required",
    minimum_placements=0,
    maximum_placements=0,
    allowed_candidate_kinds=("student_work",),
    required_relationship_kinds=(),
    reflection_requirement="required",
)
profile = PortfolioProfileRevision(
    portfolio_profile_id="profile_current_portfolio_smoke",
    profile_revision=1,
    profile_family_id=family.profile_family_id,
    predecessor_revision=None,
    label="Current Portfolio Wheel Smoke",
    purpose_kind="showcase",
    applicability=ProfileApplicability(school_years=("2026-2027",)),
    sections=(section,),
    audience_rules=(
        ProfileAudienceRule(
            audience_rule_id="student_review",
            audience_class="student",
            purpose="Review this exact synthetic portfolio package.",
            allowed_content_classes=("reflection",),
            prohibited_content_classes=("private_teacher_note",),
            required_review_classes=(),
            presentation_class="student_portfolio",
        ),
    ),
    created_at=NOW,
    created_by=TEACHER,
    source_authority_references=("wheel_smoke_policy",),
)
requirement = PortfolioProfileRequirement(
    portfolio_profile_id=profile.portfolio_profile_id,
    profile_revision=profile.profile_revision,
    requirement_id="reflection_required",
    requirement_kind="reflection",
    obligation="required",
    title="Reflection required",
    statement="One exact section Reflection is required.",
    scope_kind="section",
    satisfaction_class="reflection_presence",
    scope_reference=section.section_id,
    authority_references=("wheel_smoke_policy",),
)
lifecycle = PortfolioProfileLifecycleEvent(
    profile_lifecycle_event_id="profile_event_current_portfolio_smoke",
    profile_revision=profile.reference,
    event_kind="activated",
    event_at=NOW,
    effective_at=NOW,
    actor=TEACHER,
    reason="Activate synthetic wheel-smoke Profile.",
    authority_reference="wheel_smoke_policy",
)
binding = PortfolioProfileBinding(
    profile_binding_id="binding_current_portfolio_smoke",
    portfolio_id=portfolio.portfolio_id,
    profile_revision=profile.reference,
    bound_at=NOW,
    bound_by=TEACHER,
    binding_reason="Synthetic wheel-smoke binding.",
)
reflection = PortfolioReflection(
    reflection_id="reflection_current_portfolio_smoke",
    reflection_revision=1,
    portfolio_id=portfolio.portfolio_id,
    portfolio_subject_id=subject.portfolio_subject_id,
    profile_binding_id=binding.profile_binding_id,
    profile_revision=profile.reference,
    reflection_requirement_id=requirement.requirement_id,
    prompt_id="wheel_smoke_prompt",
    prompt_version="1",
    prompt_snapshot="Explain what this exact portfolio evidence means.",
    author=STUDENT,
    target_scope="section",
    target_references=(
        CurationTargetRef(target_kind="section", target_id=section.section_id),
    ),
    content_mode="inline_text",
    language="en",
    content_format="plain_text",
    content=REFLECTION_TEXT,
    created_at=NOW,
)

commit_record_batch(
    workspace,
    (
        subject,
        portfolio,
        family,
        profile,
        requirement,
        lifecycle,
        binding,
        reflection,
    ),
    expected_state_revision=None,
)

working = prepare_working_composition(workspace, portfolio.portfolio_id)
assert working.disposition == "create_initial"
assert working.payload.unresolved_obligation_codes == ()
frozen = freeze_prepared_working_composition(
    workspace,
    working,
    created_by=TEACHER,
    authority_gate=CurationGate(),
)
assert frozen.disposition == "created"

before_prepare = load_current_state(workspace).state_revision
preparation = prepare_current_portfolio_build(
    workspace,
    portfolio.portfolio_id,
    audience_rule_id="student_review",
)
assert CURRENT_PORTFOLIO_BUILD_CONTRACT_VERSION == (
    "vitrine_build_export_current_portfolio_v1"
)
assert load_current_state(workspace).state_revision == before_prepare
assert preparation.working_composition_disposition == "reuse_exact_current"
assert preparation.unplaced_selection_ids == ()
assert preparation.unresolved_obligation_codes == ()
assert preparation.audience_context.disposition == "create"
assert preparation.snapshot_series.disposition == "create"
assert preparation.planned_items == ()
assert len(preparation.generated_reflections) == 1
generated = preparation.generated_reflections[0]
assert generated.materialization_kind == "generated_vitrine"
assert generated.content_class == "reflection"
assert generated.supported
assert generated.export_file
assert preparation.directory_export.included_entry_plan_ids == (
    generated.entry_plan_id,
)
assert preparation.ready_for_plan_execution

snapshot_gate = SnapshotGate()
result = execute_prepared_current_portfolio_build(
    workspace,
    preparation,
    actor=TEACHER,
    authority_gate=snapshot_gate,
)
assert result.attempt_terminal_outcome == "sealed"
assert result.current_pointer_advanced is False
assert len(snapshot_gate.requests) == 1
assert result.export_path.is_dir()
export_files = tuple(
    path for path in result.export_path.rglob("*") if path.is_file()
)
assert len(export_files) == 1
assert export_files[0].read_bytes() == REFLECTION_TEXT.encode("utf-8")
series = show_snapshot_series(workspace, result.snapshot_series_id)
assert series.current_edition is None
assert any(item.edition_number == result.edition_number for item in series.editions)

before_cli_prepare = load_current_state(workspace).state_revision
output = StringIO()
status = cli.main(
    [
        "portfolio",
        "build-export",
        "prepare",
        portfolio.portfolio_id,
        "--audience-rule-id",
        "student_review",
        "--workspace-root",
        str(workspace),
    ],
    output=output,
)
assert status == 0
assert "Build and Export Current Portfolio" in output.getvalue()
assert load_current_state(workspace).state_revision == before_cli_prepare

parser = cli.build_parser()
parsed = parser.parse_args(
    [
        "portfolio",
        "build-export",
        "execute",
        portfolio.portfolio_id,
        "--audience-rule-id",
        "student_review",
        "--preparation-fingerprint",
        preparation.preparation_fingerprint,
        "--expected-state-revision",
        str(preparation.observed_state_revision),
        "--actor-id",
        TEACHER.actor_id,
    ]
)
assert parsed.portfolio_build_export_command == "execute"

for name in ("scoreform", "quillan", "concord", "portia", "meridian"):
    assert importlib.util.find_spec(name) is None
'''
        _run([str(python), "-c", code, str(workspace)], cwd=work, env=env)
        if list(work.iterdir()):
            raise RuntimeError(
                "Current Portfolio Build/Export wheel smoke left "
                "working-directory residue"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS isolated Current Portfolio Build/Export wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(
            f"Current Portfolio Build/Export wheel smoke test failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
