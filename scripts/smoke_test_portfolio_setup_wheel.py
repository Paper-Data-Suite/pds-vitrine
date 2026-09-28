"""Smoke Issue #65 setup from isolated installed Core/Vitrine wheels."""

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
            "Portfolio setup installed command failed "
            f"with exit code {result.returncode}:\n{detail}"
        )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix="vitrine-portfolio-setup-wheel-smoke-"
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

from pds_core.class_metadata import (
    ClassMetadata,
    class_metadata_path,
    write_class_metadata,
)
from pds_core.classes import write_class_roster
from pds_core.rosters import Roster, StudentRecord
from pds_core.workspace import ensure_workspace_root

from vitrine.models import (
    ActorAttribution,
    ClassQualifiedStudentRef,
    PortfolioProfileFamily,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    ProfileApplicability,
    ProfileRevisionRef,
    ProfileSectionDefinition,
)
from vitrine.portfolio_services import list_portfolios
from vitrine.portfolio_setup import (
    CreatePortfolioForStudentRequest,
    create_portfolio_for_student,
    plan_create_portfolio_for_student,
    resolve_portfolio_setup_subject,
)
from vitrine.profile_services import (
    activate_profile_revision,
    create_profile_family,
    create_profile_revision,
    get_portfolio_profile_binding,
    observe_profile_state_revision,
)
from vitrine.storage import load_current_records, load_current_state
from vitrine.subject_services import (
    IdentityDecisionContext,
    observe_state_revision,
    show_subject,
)

NOW = datetime(2026, 9, 6, 20, 0, tzinfo=timezone.utc)
actor = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="wheel_teacher",
    owning_system="local",
    role_snapshot="teacher",
)
identity = IdentityDecisionContext(
    actor=actor,
    authority_source="wheel_fixture",
    basis_type="direct_teacher_knowledge",
    basis_summary="Teacher confirmed exact cross-class identity.",
)
cwd_before = Path.cwd().resolve()
workspace = ensure_workspace_root(Path("workspace"), create=True)


def write_class(class_id: str, period: str) -> None:
    metadata = ClassMetadata(
        class_id=class_id,
        school_year="2026-2027",
        created_at=NOW,
        updated_at=NOW,
        module_details={},
    )
    write_class_metadata(class_metadata_path(workspace, class_id), metadata)
    write_class_roster(
        workspace,
        Roster(
            class_id=class_id,
            students=(
                StudentRecord(
                    class_id=class_id,
                    student_id="00107",
                    last_name="Doe",
                    first_name="Jane",
                    period=period,
                    extra_fields={"preferred_name": "Jay"},
                ),
            ),
            columns=(
                "class_id",
                "student_id",
                "last_name",
                "first_name",
                "period",
                "preferred_name",
            ),
        ),
    )


write_class("english10_p2", "2")
write_class("csp_p1", "1")

profile_reference = ProfileRevisionRef(
    portfolio_profile_id="profile_wheel_setup",
    profile_revision=1,
)
blocked = plan_create_portfolio_for_student(
    workspace,
    CreatePortfolioForStudentRequest(
        student_reference=ClassQualifiedStudentRef(
            school_year="2026-2027",
            class_id="english10_p2",
            student_id="00107",
        ),
        purpose_kind="improvement",
        profile_revision=profile_reference,
        subject_action="create_new",
        identity_context=identity,
    ),
)
assert "profile_revision_not_found" in blocked.blocking_codes
assert not blocked.ready
assert observe_state_revision(workspace) is None

family = PortfolioProfileFamily(
    profile_family_id="family_wheel_setup",
    label="Wheel Setup Profiles",
    purpose_kind="improvement",
    created_at=NOW,
    created_by=actor,
)
revision = PortfolioProfileRevision(
    portfolio_profile_id=profile_reference.portfolio_profile_id,
    profile_revision=profile_reference.profile_revision,
    profile_family_id=family.profile_family_id,
    predecessor_revision=None,
    label="Wheel Setup Improvement",
    purpose_kind="improvement",
    applicability=ProfileApplicability(school_years=("2026-2027",)),
    sections=(
        ProfileSectionDefinition(
            section_id="evidence",
            label="Evidence",
            purpose="Synthetic setup evidence section.",
            order=1,
            obligation="required",
            minimum_placements=1,
            maximum_placements=None,
            allowed_candidate_kinds=("student_work",),
            required_relationship_kinds=("artifact_author",),
            reflection_requirement="optional",
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
    requirement_id="evidence_required",
    requirement_kind="section",
    obligation="required",
    title="Evidence required",
    statement="Include evidence.",
    scope_kind="section",
    scope_reference="evidence",
    satisfaction_class="section_cardinality",
    authority_references=("wheel_fixture",),
)
create_profile_family(
    workspace,
    family,
    expected_state_revision=observe_profile_state_revision(workspace),
)
create_profile_revision(
    workspace,
    revision,
    (requirement,),
    expected_state_revision=observe_profile_state_revision(workspace),
)
activate_profile_revision(
    workspace,
    revision.reference,
    actor=actor,
    reason="Explicitly activate installed-wheel fixture Profile.",
    authority_reference="wheel_fixture",
    expected_state_revision=observe_profile_state_revision(workspace),
)

ref_a = ClassQualifiedStudentRef(
    school_year="2026-2027",
    class_id="english10_p2",
    student_id="00107",
)
plan_a = plan_create_portfolio_for_student(
    workspace,
    CreatePortfolioForStudentRequest(
        student_reference=ref_a,
        purpose_kind="improvement",
        profile_revision=revision.reference,
        subject_action="create_new",
        identity_context=identity,
        title_snapshot="Wheel Improvement A",
    ),
)
assert plan_a.ready
before_a = load_current_state(workspace).state_revision
result_a = create_portfolio_for_student(workspace, plan_a, actor=actor)
assert result_a.state_revision == before_a + 1

ref_b = ClassQualifiedStudentRef(
    school_year="2026-2027",
    class_id="csp_p1",
    student_id="00107",
)
resolution_b = resolve_portfolio_setup_subject(workspace, ref_b)
assert resolution_b.subject_status == "unlinked"
auto_plan = plan_create_portfolio_for_student(
    workspace,
    CreatePortfolioForStudentRequest(
        student_reference=ref_b,
        purpose_kind="improvement",
        profile_revision=revision.reference,
    ),
)
assert "subject_choice_required" in auto_plan.blocking_codes
assert not auto_plan.ready

plan_b = plan_create_portfolio_for_student(
    workspace,
    CreatePortfolioForStudentRequest(
        student_reference=ref_b,
        purpose_kind="improvement",
        profile_revision=revision.reference,
        subject_action="link_existing",
        existing_subject_id=result_a.portfolio_subject_id,
        identity_context=identity,
        title_snapshot="Wheel Improvement B",
    ),
)
assert plan_b.ready
before_b = load_current_state(workspace).state_revision
result_b = create_portfolio_for_student(workspace, plan_b, actor=actor)
assert result_b.state_revision == before_b + 1

subject = show_subject(workspace, result_a.portfolio_subject_id)
assert {link.reference.class_id for link in subject.current_links} == {
    "english10_p2",
    "csp_p1",
}
portfolios = list_portfolios(workspace)
assert {item.portfolio_id for item in portfolios} == {
    result_a.portfolio_id,
    result_b.portfolio_id,
}
for portfolio_id in (result_a.portfolio_id, result_b.portfolio_id):
    binding = get_portfolio_profile_binding(workspace, portfolio_id)
    assert binding is not None
    assert binding.profile_revision == revision.reference

assert load_current_state(workspace).state_revision == result_b.state_revision
record_types = {item.record_type for item in load_current_records(workspace)}
assert not any("candidate" in value for value in record_types)
assert not any("selection" in value for value in record_types)
assert not any("placement" in value for value in record_types)
assert Path.cwd().resolve() == cwd_before

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
        print("PASS isolated Create Portfolio for Student wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(
            f"Create Portfolio for Student wheel smoke test failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
