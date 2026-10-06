"""Installed-wheel acceptance for Issue #101 student Portfolio presentation."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
            "Issue #101 installed command failed "
            f"with exit code {result.returncode}:\n{detail}"
        )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "verify_core_wheel.py"),
            str(core_wheel.resolve()),
        ],
        cwd=ROOT,
        env=os.environ.copy(),
    )

    with tempfile.TemporaryDirectory(prefix="vitrine-issue101-wheel-") as temporary:
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
        requirement = f"pds-vitrine[paper] @ {vitrine_wheel.resolve().as_uri()}"
        _run(
            [str(python), "-m", "pip", "install", requirement],
            cwd=work,
            env=env,
        )
        _run([str(python), "-m", "pip", "check"], cwd=work, env=env)

        code = r'''\
import importlib.metadata
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

from pds_core.workspace import ensure_workspace_root

from vitrine.curation_services import (
    CurationAuthorityDecision,
    CurationAuthorityRequest,
)
from vitrine.current_portfolio_build import prepare_current_portfolio_build
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
from vitrine.portfolio_presentation_services import build_student_portfolio_presentation
from vitrine.portfolio_presentation_verification import verify_portfolio_presentation
from vitrine.snapshot_materialization import (
    SnapshotBuildAuthorityDecision,
    SnapshotBuildAuthorityRequest,
)
from vitrine.storage import commit_record_batch, load_current_state
from vitrine.storage.paths import safe_vitrine_descendant
from vitrine.workflow_views import show_snapshot_series
from vitrine.working_composition import (
    freeze_prepared_working_composition,
    prepare_working_composition,
)

NOW = datetime(2026, 10, 4, 20, 0, tzinfo=timezone.utc)
TEACHER = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="issue101_wheel_teacher",
    owning_system="local",
    role_snapshot="teacher",
)
STUDENT = ActorAttribution(
    actor_kind="external_actor",
    actor_id="issue101_wheel_student",
    owning_system="local",
    role_snapshot="student",
)
REFLECTION_TEXT = "This exact reflection belongs in my student Portfolio."


class CurationGate:
    def authorize(self, request: CurationAuthorityRequest) -> CurationAuthorityDecision:
        assert request.operation == "compose_portfolio"
        return CurationAuthorityDecision(
            outcome="allowed",
            authority_reference="issue101_wheel_curation",
            reason_codes=("issue101_wheel",),
        )


class SnapshotGate:
    def authorize(
        self, request: SnapshotBuildAuthorityRequest
    ) -> SnapshotBuildAuthorityDecision:
        return SnapshotBuildAuthorityDecision(
            outcome="allowed",
            authority_reference="issue101_wheel_snapshot",
            reason_codes=("issue101_wheel",),
        )


assert importlib.metadata.version("pds-core") == "0.6.4"
assert importlib.metadata.version("pds-vitrine") == "0.3.0"
for name in ("scoreform", "quillan", "concord", "portia", "meridian"):
    assert importlib.util.find_spec(name) is None, name

workspace = ensure_workspace_root(Path(sys.argv[1]), create=True)
subject = PortfolioSubject(
    portfolio_subject_id="subject_issue101_wheel",
    created_at=NOW,
    created_by=TEACHER,
    display_name_snapshot="Synthetic Student",
)
portfolio = Portfolio(
    portfolio_id="portfolio_issue101_wheel",
    portfolio_subject_id=subject.portfolio_subject_id,
    created_at=NOW,
    created_by=TEACHER,
    title_snapshot="Student Portfolio Wheel Acceptance",
)
family = PortfolioProfileFamily(
    profile_family_id="family_issue101_wheel",
    label="Issue 101 Wheel Profiles",
    purpose_kind="improvement",
    created_at=NOW,
    created_by=TEACHER,
)
section = ProfileSectionDefinition(
    section_id="reflection",
    label="Reflection",
    purpose="One exact student Reflection.",
    order=1,
    obligation="required",
    minimum_placements=0,
    maximum_placements=0,
    allowed_candidate_kinds=("student_work",),
    required_relationship_kinds=(),
    reflection_requirement="required",
)
profile = PortfolioProfileRevision(
    portfolio_profile_id="profile_issue101_wheel",
    profile_revision=1,
    profile_family_id=family.profile_family_id,
    predecessor_revision=None,
    label="Student Portfolio Wheel Profile",
    purpose_kind="improvement",
    applicability=ProfileApplicability(school_years=("2026-2027",)),
    sections=(section,),
    audience_rules=(
        ProfileAudienceRule(
            audience_rule_id="student_review",
            audience_class="student",
            purpose="Review this exact synthetic student Portfolio.",
            allowed_content_classes=("portfolio_index", "reflection"),
            prohibited_content_classes=("private_teacher_note",),
            required_review_classes=(),
            presentation_class="student_portfolio",
        ),
    ),
    created_at=NOW,
    created_by=TEACHER,
    source_authority_references=("issue101_wheel_policy",),
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
    authority_references=("issue101_wheel_policy",),
)
lifecycle = PortfolioProfileLifecycleEvent(
    profile_lifecycle_event_id="profile_event_issue101_wheel",
    profile_revision=profile.reference,
    event_kind="activated",
    event_at=NOW,
    effective_at=NOW,
    actor=TEACHER,
    reason="Activate Issue #101 wheel Profile.",
    authority_reference="issue101_wheel_policy",
)
binding = PortfolioProfileBinding(
    profile_binding_id="binding_issue101_wheel",
    portfolio_id=portfolio.portfolio_id,
    profile_revision=profile.reference,
    bound_at=NOW,
    bound_by=TEACHER,
    binding_reason="Issue #101 wheel binding.",
)
reflection = PortfolioReflection(
    reflection_id="reflection_issue101_wheel",
    reflection_revision=1,
    portfolio_id=portfolio.portfolio_id,
    portfolio_subject_id=subject.portfolio_subject_id,
    profile_binding_id=binding.profile_binding_id,
    profile_revision=profile.reference,
    reflection_requirement_id=requirement.requirement_id,
    prompt_id="issue101_wheel_prompt",
    prompt_version="1",
    prompt_snapshot="Explain what this exact Portfolio evidence means.",
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
frozen = freeze_prepared_working_composition(
    workspace,
    working,
    created_by=TEACHER,
    authority_gate=CurationGate(),
)
assert frozen.disposition == "created"

preparation = prepare_current_portfolio_build(
    workspace,
    portfolio.portfolio_id,
    audience_rule_id="student_review",
)
assert preparation.ready_for_plan_execution
result = execute_prepared_current_portfolio_build(
    workspace,
    preparation,
    actor=TEACHER,
    authority_gate=SnapshotGate(),
)
assert result.attempt_terminal_outcome == "sealed"
assert result.presentation_disposition == "created"
assert result.presentation_verified
assert result.presentation_artifact_id is not None
assert result.presentation_html_relative_path is not None
assert result.presentation_pdf_relative_path is not None
assert result.current_pointer_advanced is False

html_path = safe_vitrine_descendant(
    workspace, result.presentation_html_relative_path
)
pdf_path = safe_vitrine_descendant(
    workspace, result.presentation_pdf_relative_path
)
html = html_path.read_text(encoding="utf-8")
assert "Student Portfolio Wheel Acceptance" in html
assert "Synthetic Student" in html
assert "Reflection" in html
assert REFLECTION_TEXT in html
assert "http://" not in html and "https://" not in html
assert pdf_path.read_bytes().startswith(b"%PDF-")

verified = verify_portfolio_presentation(
    workspace,
    presentation_artifact_id=result.presentation_artifact_id,
)
assert verified.presentation_artifact_id == result.presentation_artifact_id
assert verified.edition_number == result.edition_number

before_repeat = load_current_state(workspace).state_revision
repeat = build_student_portfolio_presentation(
    workspace,
    snapshot_series_id=result.snapshot_series_id,
    edition_number=result.edition_number,
    snapshot_export_artifact_id=result.snapshot_export_artifact_id,
    generated_by=TEACHER,
)
assert repeat.disposition == "existing"
assert repeat.presentation_artifact_id == result.presentation_artifact_id
assert load_current_state(workspace).state_revision == before_repeat

series = show_snapshot_series(workspace, result.snapshot_series_id)
assert series.current_edition is None
'''
        _run([str(python), "-c", code, str(workspace)], cwd=work, env=env)
        if list(work.iterdir()):
            raise RuntimeError(
                "Issue #101 installed-wheel acceptance left working-directory residue"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS Issue #101 Core 0.6.4 installed-wheel presentation acceptance")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Issue #101 installed-wheel smoke failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
