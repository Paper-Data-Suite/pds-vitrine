"""Installed-wheel acceptance for Issue #102 completed Portfolio navigation."""

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
            "Issue #102 installed command failed "
            f"with exit code {result.returncode}:\n{detail}"
        )
    return result.stdout


def smoke(
    vitrine_wheel: Path,
    core_wheel: Path,
    *,
    viewer_workspace: Path | None = None,
    viewer_report: Path | None = None,
) -> None:
    if (viewer_workspace is None) != (viewer_report is None):
        raise RuntimeError("Viewer workspace and report must be supplied together")
    if viewer_workspace is not None and viewer_report is not None:
        if sys.platform != "win32":
            raise RuntimeError("Actual Windows viewer qualification requires Windows")
        viewer_workspace = viewer_workspace.expanduser().absolute()
        viewer_report = viewer_report.expanduser().absolute()
        if viewer_workspace.exists() or viewer_report.exists():
            raise RuntimeError("Viewer workspace/report must not already exist")
        if viewer_workspace.is_relative_to(ROOT):
            raise RuntimeError("Viewer workspace must not be inside the repository")
        if not viewer_report.parent.is_dir():
            raise RuntimeError("Viewer report parent does not exist")
    _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "verify_core_wheel.py"),
            str(core_wheel.resolve()),
        ],
        cwd=ROOT,
        env=os.environ.copy(),
    )

    with tempfile.TemporaryDirectory(prefix="vitrine-issue102-wheel-") as temporary:
        root = Path(temporary)
        environment = root / "venv"
        work = root / "work"
        workspace = (viewer_workspace if viewer_workspace is not None else root / "deep" / "workspace" / "for" / "completed" / "portfolios")
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

        code = r"""import importlib.metadata
import importlib.util
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

from pds_core.workspace import ensure_workspace_root

from vitrine import portfolio_menu
from vitrine.completed_portfolio import project_completed_portfolio_history
from vitrine.completed_portfolio_actions import (
    CompletedPortfolioActionError,
    verify_completed_portfolio_edition,
)
from vitrine.completed_portfolio_menu import BUILD_UPDATED_EDITION
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
from vitrine.portfolio_output_opening import (
    PortfolioOutputOpenError,
    open_printable_student_portfolio,
    open_student_portfolio_folder,
    open_student_portfolio_html,
    open_technical_export_folder,
)
from vitrine.snapshot_materialization import (
    SnapshotBuildAuthorityDecision,
    SnapshotBuildAuthorityRequest,
)
from vitrine.storage import (
    commit_record_batch,
    load_current_records,
    load_current_state,
)
from vitrine.storage.paths import safe_vitrine_descendant
from vitrine.workflow_context import default_workflow_dependencies
from vitrine.working_composition import (
    freeze_prepared_working_composition,
    prepare_working_composition,
)

NOW = datetime(2026, 10, 6, 20, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 10, 6, 20, 5, tzinfo=timezone.utc)
TEACHER = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="issue102_teacher",
    owning_system="local",
    role_snapshot="teacher",
)
STUDENT = ActorAttribution(
    actor_kind="external_actor",
    actor_id="issue102_student",
    owning_system="local",
    role_snapshot="student",
)


class CurationGate:
    def authorize(self, request: CurationAuthorityRequest) -> CurationAuthorityDecision:
        assert request.operation == "compose_portfolio"
        return CurationAuthorityDecision(
            outcome="allowed",
            authority_reference="issue102_curation",
            reason_codes=("issue102",),
        )


class SnapshotGate:
    def authorize(
        self, request: SnapshotBuildAuthorityRequest
    ) -> SnapshotBuildAuthorityDecision:
        return SnapshotBuildAuthorityDecision(
            outcome="allowed",
            authority_reference="issue102_snapshot",
            reason_codes=("issue102",),
        )


assert importlib.metadata.version("pds-core") == "0.6.6"
assert importlib.metadata.version("pds-vitrine") == "0.4.0"
for name in ("scoreform", "quillan", "concord", "portia", "meridian"):
    assert importlib.util.find_spec(name) is None, name

workspace = ensure_workspace_root(Path(sys.argv[1]), create=True)
subject = PortfolioSubject(
    portfolio_subject_id="subject_issue102",
    created_at=NOW,
    created_by=TEACHER,
    display_name_snapshot="Synthetic Student",
)
portfolio = Portfolio(
    portfolio_id="portfolio_issue102",
    portfolio_subject_id=subject.portfolio_subject_id,
    created_at=NOW,
    created_by=TEACHER,
    title_snapshot="Completed Portfolio Acceptance",
)
family = PortfolioProfileFamily(
    profile_family_id="family_issue102",
    label="Issue 102 Wheel Profiles",
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
    portfolio_profile_id="profile_issue102",
    profile_revision=1,
    profile_family_id=family.profile_family_id,
    predecessor_revision=None,
    label="Completed Portfolio Wheel Profile",
    purpose_kind="improvement",
    applicability=ProfileApplicability(school_years=("2026-2027",)),
    sections=(section,),
    audience_rules=(
        ProfileAudienceRule(
            audience_rule_id="student_review",
            audience_class="student",
            purpose="Student Review",
            allowed_content_classes=("portfolio_index", "reflection"),
            prohibited_content_classes=("private_teacher_note",),
            required_review_classes=(),
            presentation_class="student_portfolio",
        ),
    ),
    created_at=NOW,
    created_by=TEACHER,
    source_authority_references=("issue102_policy",),
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
    authority_references=("issue102_policy",),
)
lifecycle = PortfolioProfileLifecycleEvent(
    profile_lifecycle_event_id="profile_event_issue102",
    profile_revision=profile.reference,
    event_kind="activated",
    event_at=NOW,
    effective_at=NOW,
    actor=TEACHER,
    reason="Activate Issue #102 wheel Profile.",
    authority_reference="issue102_policy",
)
binding = PortfolioProfileBinding(
    profile_binding_id="binding_issue102",
    portfolio_id=portfolio.portfolio_id,
    profile_revision=profile.reference,
    bound_at=NOW,
    bound_by=TEACHER,
    binding_reason="Issue #102 wheel binding.",
)
reflection1 = PortfolioReflection(
    reflection_id="reflection_issue102",
    reflection_revision=1,
    portfolio_id=portfolio.portfolio_id,
    portfolio_subject_id=subject.portfolio_subject_id,
    profile_binding_id=binding.profile_binding_id,
    profile_revision=profile.reference,
    reflection_requirement_id=requirement.requirement_id,
    prompt_id="issue102_prompt",
    prompt_version="1",
    prompt_snapshot="Explain what this Portfolio evidence means.",
    author=STUDENT,
    target_scope="section",
    target_references=(
        CurationTargetRef(target_kind="section", target_id=section.section_id),
    ),
    content_mode="inline_text",
    language="en",
    content_format="plain_text",
    content="First completed Portfolio reflection.",
    created_at=NOW,
)

commit_record_batch(
    workspace,
    (subject, portfolio, family, profile, requirement, lifecycle, binding, reflection1),
    expected_state_revision=None,
)

working1 = prepare_working_composition(workspace, portfolio.portfolio_id)
assert working1.disposition == "create_initial"
freeze_prepared_working_composition(
    workspace,
    working1,
    created_by=TEACHER,
    authority_gate=CurationGate(),
)
preparation1 = prepare_current_portfolio_build(
    workspace,
    portfolio.portfolio_id,
    audience_rule_id="student_review",
)
assert preparation1.ready_for_plan_execution
result1 = execute_prepared_current_portfolio_build(
    workspace,
    preparation1,
    actor=TEACHER,
    authority_gate=SnapshotGate(),
)
assert result1.presentation_verified
assert result1.current_pointer_advanced is False

reflection2 = PortfolioReflection(
    reflection_id=reflection1.reflection_id,
    reflection_revision=2,
    portfolio_id=reflection1.portfolio_id,
    portfolio_subject_id=reflection1.portfolio_subject_id,
    profile_binding_id=reflection1.profile_binding_id,
    profile_revision=reflection1.profile_revision,
    reflection_requirement_id=reflection1.reflection_requirement_id,
    prompt_id=reflection1.prompt_id,
    prompt_version=reflection1.prompt_version,
    prompt_snapshot=reflection1.prompt_snapshot,
    author=reflection1.author,
    target_scope=reflection1.target_scope,
    target_references=reflection1.target_references,
    content_mode=reflection1.content_mode,
    language=reflection1.language,
    content_format=reflection1.content_format,
    content="Second completed Portfolio reflection.",
    created_at=LATER,
    predecessor_reflection_revision=1,
)
commit_record_batch(
    workspace,
    (reflection2,),
    expected_state_revision=load_current_state(workspace).state_revision,
)
working2 = prepare_working_composition(workspace, portfolio.portfolio_id)
assert working2.disposition == "create_successor"
freeze_prepared_working_composition(
    workspace,
    working2,
    created_by=TEACHER,
    authority_gate=CurationGate(),
)
preparation2 = prepare_current_portfolio_build(
    workspace,
    portfolio.portfolio_id,
    audience_rule_id="student_review",
)
assert preparation2.ready_for_plan_execution
result2 = execute_prepared_current_portfolio_build(
    workspace,
    preparation2,
    actor=TEACHER,
    authority_gate=SnapshotGate(),
)
assert result2.presentation_verified
assert result2.current_pointer_advanced is False
assert result2.edition_number > result1.edition_number

history = project_completed_portfolio_history(
    load_current_records(workspace),
    portfolio_id=portfolio.portfolio_id,
)
assert history.completed_edition_count == 2
series = next(item for item in history.series if item.snapshot_series_id == result2.snapshot_series_id)
assert len(series.editions) == 2
assert series.current_edition_number is None
assert series.editions[0].edition_number == result2.edition_number
assert not any(item.is_current for item in series.editions)
selected = series.editions[0]
assert selected.exports
assert selected.presentations

before_read_only = load_current_state(workspace).state_revision
verified = verify_completed_portfolio_edition(
    workspace,
    portfolio_id=portfolio.portfolio_id,
    snapshot_series_id=selected.snapshot_series_id,
    edition_number=selected.edition_number,
)
assert verified.verified_export_count >= 1
assert verified.verified_student_presentation_count >= 1

opened = []
def recorder(path):
    resolved = Path(path).resolve(strict=True)
    opened.append(resolved)
    return resolved

presentation = selected.presentations[0]
export = selected.exports[0]
html = open_student_portfolio_html(
    workspace,
    presentation_artifact_id=presentation.presentation_artifact_id,
    opener=recorder,
)
pdf = open_printable_student_portfolio(
    workspace,
    presentation_artifact_id=presentation.presentation_artifact_id,
    opener=recorder,
)
presentation_root = open_student_portfolio_folder(
    workspace,
    presentation_artifact_id=presentation.presentation_artifact_id,
    opener=recorder,
)
export_root = open_technical_export_folder(
    workspace,
    snapshot_export_artifact_id=export.snapshot_export_artifact_id,
    opener=recorder,
)
assert opened == [html, pdf, presentation_root, export_root]
assert html.is_file() and pdf.is_file()
assert presentation_root.is_dir() and export_root.is_dir()
assert load_current_state(workspace).state_revision == before_read_only

original_html = html.read_bytes()
html.write_bytes(original_html + b"\n")
try:
    verify_completed_portfolio_edition(
        workspace,
        portfolio_id=portfolio.portfolio_id,
        snapshot_series_id=selected.snapshot_series_id,
        edition_number=selected.edition_number,
    )
except CompletedPortfolioActionError as error:
    assert error.code == "completed_portfolio_action.verification_failed"
else:
    raise AssertionError("tampered Presentation unexpectedly verified")

try:
    open_student_portfolio_html(
        workspace,
        presentation_artifact_id=presentation.presentation_artifact_id,
        opener=recorder,
    )
except PortfolioOutputOpenError as error:
    assert error.code == "portfolio_output.verification_failed"
else:
    raise AssertionError("tampered Presentation unexpectedly opened")

html.write_bytes(original_html)
verify_completed_portfolio_edition(
    workspace,
    portfolio_id=portfolio.portfolio_id,
    snapshot_series_id=selected.snapshot_series_id,
    edition_number=selected.edition_number,
)
assert load_current_state(workspace).state_revision == before_read_only

# Real Windows viewer characterization is opt-in; the ordinary installed smoke
# remains headless and cannot claim actual browser/PDF/Explorer accessibility.
if len(sys.argv) > 2 and sys.argv[2] != "-":
    import hashlib
    import json

    if sys.platform != "win32":
        raise RuntimeError("real viewer opening requires Windows")
    targets = (
        ("student_html", html, lambda: open_student_portfolio_html(
            workspace, presentation_artifact_id=presentation.presentation_artifact_id
        )),
        ("printable_pdf", pdf, lambda: open_printable_student_portfolio(
            workspace, presentation_artifact_id=presentation.presentation_artifact_id
        )),
        ("presentation_folder", presentation_root, lambda: open_student_portfolio_folder(
            workspace, presentation_artifact_id=presentation.presentation_artifact_id
        )),
        ("technical_export_folder", export_root, lambda: open_technical_export_folder(
            workspace, snapshot_export_artifact_id=export.snapshot_export_artifact_id
        )),
    )
    # Each type must actually be deep; no shallow-pass substitution.
    if any(len(str(path)) <= 260 for _, path, _ in targets):
        raise RuntimeError("viewer targets must all exceed 260 canonical characters")
    report_targets = []
    for kind, canonical, launch in targets:
        result = {
            "kind": kind,
            "canonical_path": str(canonical),
            "canonical_path_length": len(str(canonical)),
            "canonical_sha256": (hashlib.sha256(canonical.read_bytes()).hexdigest()
                                 if canonical.is_file() else None),
            "shell_handoff": "failed",
            "handoff_path": None,
            "handoff_path_length": None,
            "viewer_accessibility": "pending",
        }
        try:
            returned = launch()
            result["shell_handoff"] = "returned"
            result["handoff_path"] = str(returned)
            result["handoff_path_length"] = len(str(returned))
            # A short handoff may be an alias, not the canonical path. Require
            # equivalent verified bytes/inventory; never assume alias authority.
            returned_path = Path(returned)
            if canonical.is_file():
                result["handoff_content_matches"] = (
                    hashlib.sha256(returned_path.read_bytes()).hexdigest()
                    == result["canonical_sha256"]
                )
            else:
                def inventory(folder):
                    return tuple(sorted(
                        (item.relative_to(folder).as_posix(),
                         hashlib.sha256(item.read_bytes()).hexdigest())
                        for item in folder.rglob("*") if item.is_file()
                    ))
                result["handoff_content_matches"] = (
                    inventory(returned_path) == inventory(canonical)
                )
        except (PortfolioOutputOpenError, OSError, RuntimeError) as error:
            result["shell_error"] = type(error).__name__
        report_targets.append(result)
    report = {
        "contract": "vitrine_issue117_windows_viewer_v1",
        "platform": sys.platform,
        "core_version": importlib.metadata.version("pds-core"),
        "vitrine_version": importlib.metadata.version("pds-vitrine"),
        "workspace": str(workspace),
        "synthetic_only": True,
        "canonical_verified": True,
        "targets": report_targets,
        "attestation_method": "pending",
    }
    Path(sys.argv[2]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

calls = []
portfolio_menu.run_completed_portfolio_menu = (
    lambda **_kwargs: BUILD_UPDATED_EDITION
)
portfolio_menu.run_current_portfolio_build_export_menu = (
    lambda **kwargs: calls.append(kwargs)
)
inputs = iter(("8", "B"))
portfolio_menu._portfolio_context(
    root=workspace,
    portfolio_id=portfolio.portfolio_id,
    input_fn=lambda _prompt: next(inputs),
    output=io.StringIO(),
    clear_fn=lambda: None,
    dependencies=default_workflow_dependencies(),
    actor=TEACHER,
)
assert len(calls) == 1
assert calls[0]["portfolio_id"] == portfolio.portfolio_id
assert "snapshot_series_id" not in calls[0]
assert "edition_number" not in calls[0]

for name in ("scoreform", "quillan", "concord", "portia", "meridian"):
    assert importlib.util.find_spec(name) is None, name
"""
        _run(
            [str(python), "-c", code, str(workspace),
             str(viewer_report) if viewer_report is not None else "-"],
            cwd=work, env=env,
        )
        if viewer_report is not None:
            if not viewer_report.is_file():
                raise RuntimeError("Expected viewer capture report was not produced")
            print(f"CAPTURED real Windows shell-handoff evidence: {viewer_report}")
            print("PENDING manual verification of actual viewer accessibility")
        if list(work.iterdir()):
            raise RuntimeError(
                "Issue #102 installed-wheel acceptance left working-directory residue"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    parser.add_argument("--viewer-workspace", type=Path)
    parser.add_argument("--viewer-report", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(
            args.vitrine_wheel, args.core_wheel,
            viewer_workspace=args.viewer_workspace,
            viewer_report=args.viewer_report,
        )
        print("PASS Issue #117 Core 0.6.6 installed-wheel completed Portfolio acceptance")
        if args.viewer_report is not None:
            print("NOTE shell handoff captured; Windows viewer accessibility remains UNVERIFIED until attested")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Issue #102 installed-wheel smoke failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
