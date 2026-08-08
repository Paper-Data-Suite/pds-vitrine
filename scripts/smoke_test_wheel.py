"""Install Core and Vitrine wheels in isolation and smoke the current baseline."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        input=input_text,
        text=True,
        capture_output=True,
        check=True,
    )


def _venv_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _console_path(python: Path) -> Path:
    code = "import json,sysconfig; print(json.dumps(sysconfig.get_path('scripts')))"
    result = subprocess.run(
        [str(python), "-c", code],
        text=True,
        capture_output=True,
        check=True,
    )
    scripts = Path(json.loads(result.stdout))
    return scripts / ("vitrine.exe" if os.name == "nt" else "vitrine")


def _model_smoke_code() -> str:
    return """
from datetime import datetime, timezone
from vitrine.models import (
    ActorAttribution,
    Portfolio,
    PortfolioSubject,
    VitrineRecordGraph,
    graph_from_json_bytes,
    graph_to_canonical_json_bytes,
    validate_record_graph,
)
actor = ActorAttribution(
    actor_kind='authorized_adult',
    actor_id='teacher_1',
    owning_system='vitrine',
)
subject = PortfolioSubject(
    portfolio_subject_id='subject_1',
    created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    created_by=actor,
)
portfolio = Portfolio(
    portfolio_id='portfolio_1',
    portfolio_subject_id=subject.portfolio_subject_id,
    created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    created_by=actor,
)
graph = VitrineRecordGraph(
    portfolios=(portfolio,),
    portfolio_subjects=(subject,),
)
validate_record_graph(graph)
content = graph_to_canonical_json_bytes(graph)
loaded = graph_from_json_bytes(content)
validate_record_graph(loaded)
assert graph_to_canonical_json_bytes(loaded) == content
"""


def _storage_smoke_code() -> str:
    return r"""
from datetime import datetime, timezone
from pathlib import Path
import sys

from vitrine.models import (
    ActorAttribution,
    Portfolio,
    PortfolioProfileFamily,
    PortfolioSubject,
)
from vitrine.storage import (
    catalog_path,
    commit_record_batch,
    load_current_record_graph,
    query_catalog_records,
    rebuild_catalog,
)

workspace = Path(sys.argv[1])
actor = ActorAttribution(
    actor_kind='authorized_adult',
    actor_id='teacher_1',
    owning_system='vitrine',
)
now = datetime(2026, 1, 1, tzinfo=timezone.utc)
subject = PortfolioSubject(
    portfolio_subject_id='subject_1',
    created_at=now,
    created_by=actor,
)
portfolio = Portfolio(
    portfolio_id='portfolio_1',
    portfolio_subject_id=subject.portfolio_subject_id,
    created_at=now,
    created_by=actor,
)
first = commit_record_batch(
    workspace,
    (subject, portfolio),
    expected_state_revision=None,
)
assert first.state_revision == 1
family = PortfolioProfileFamily(
    profile_family_id='family_1',
    label='Synthetic Family',
    purpose_kind='improvement',
    created_at=now,
    created_by=actor,
)
second = commit_record_batch(
    workspace,
    (family,),
    expected_state_revision=1,
)
assert second.state_revision == 2
loaded = load_current_record_graph(workspace)
assert loaded.state_revision == 2
rebuilt = rebuild_catalog(workspace)
assert rebuilt.is_file()
assert len(query_catalog_records(workspace, state='current')) == 3
catalog_path(workspace).unlink()
assert load_current_record_graph(workspace).state_revision == 2
"""



def _subject_smoke_code() -> str:
    return r"""
from datetime import datetime, timezone
from pathlib import Path
import sys

from pds_core.class_metadata import ClassMetadata, class_metadata_path, write_class_metadata
from pds_core.classes import write_class_roster
from pds_core.rosters import Roster, StudentRecord
from vitrine.models import ActorAttribution, ClassQualifiedStudentRef
from vitrine.subject_services import (
    IdentityDecisionContext,
    correct_subject_link,
    create_portfolio_subject,
    link_portfolio_subject,
    show_subject,
)

workspace = Path(sys.argv[1])
now = datetime(2026, 1, 1, tzinfo=timezone.utc)
actor = ActorAttribution(
    actor_kind='authorized_adult',
    actor_id='teacher_1',
    owning_system='local',
    role_snapshot='teacher',
)
context = IdentityDecisionContext(
    actor=actor,
    authority_source='local_teacher_workflow',
    basis_type='direct_teacher_knowledge',
    basis_summary='Synthetic installed-wheel confirmation.',
)

def write_class(class_id, student_id, first, last, period):
    metadata = ClassMetadata(
        class_id=class_id,
        school_year='2026-2027',
        created_at=now,
        updated_at=now,
        module_details={},
    )
    write_class_metadata(class_metadata_path(workspace, class_id), metadata)
    write_class_roster(
        workspace,
        Roster(
            class_id=class_id,
            students=(StudentRecord(
                class_id=class_id,
                student_id=student_id,
                last_name=last,
                first_name=first,
                period=period,
                extra_fields={},
            ),),
            columns=('class_id','student_id','last_name','first_name','period'),
        ),
    )

write_class('english10_p2', '00107', 'Jane', 'Doe', '2')
write_class('csp_p1', '00107', 'Jane', 'Doe', '1')
write_class('history_p4', '00777', 'Jane', 'Doe', '4')

first = create_portfolio_subject(
    workspace,
    ClassQualifiedStudentRef(
        school_year='2026-2027', class_id='english10_p2', student_id='00107'
    ),
    context=context,
    expected_state_revision=2,
)
linked = link_portfolio_subject(
    workspace,
    first.subject_ids[0],
    ClassQualifiedStudentRef(
        school_year='2026-2027', class_id='csp_p1', student_id='00107'
    ),
    context=context,
    expected_state_revision=first.commit.state_revision,
)
detail = show_subject(workspace, first.subject_ids[0])
assert {item.reference.class_id for item in detail.current_links} == {'english10_p2','csp_p1'}
csp_link = next(item for item in detail.current_links if item.reference.class_id == 'csp_p1')
corrected = correct_subject_link(
    workspace,
    csp_link.subject_link_id,
    ClassQualifiedStudentRef(
        school_year='2026-2027', class_id='history_p4', student_id='00777'
    ),
    context=context,
    expected_state_revision=linked.commit.state_revision,
)
assert corrected.commit.state_revision == linked.commit.state_revision + 1
final = show_subject(workspace, first.subject_ids[0])
assert any(item.reference.class_id == 'csp_p1' for item in final.historical_links)
assert any(item.reference.class_id == 'history_p4' for item in final.current_links)
"""


def _profile_smoke_code() -> str:
    return r"""
from datetime import datetime, timezone
from pathlib import Path
import sys

from vitrine.models import (
    ActorAttribution,
    PortfolioProfileFamily,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    ProfileApplicability,
    ProfileAudienceRule,
    ProfileRevisionRef,
    ProfileSectionDefinition,
)
from vitrine.profile_services import (
    ProfileBindingContext,
    activate_profile_revision,
    bind_portfolio_profile,
    create_profile_family,
    create_profile_revision,
    get_portfolio_profile_binding,
    migrate_portfolio_profile,
    observe_profile_state_revision,
)

workspace = Path(sys.argv[1])
now = datetime(2026, 1, 1, tzinfo=timezone.utc)
actor = ActorAttribution(
    actor_kind='authorized_adult', actor_id='teacher_profile', owning_system='local', role_snapshot='teacher'
)
family = PortfolioProfileFamily(
    profile_family_id='family_smoke_growth',
    label='Smoke Growth',
    purpose_kind='improvement',
    created_at=now,
    created_by=actor,
)
expected = observe_profile_state_revision(workspace)
created = create_profile_family(workspace, family, expected_state_revision=expected)
expected = created.commit.state_revision if created.commit is not None else expected

def revision(number, predecessor=None, feedback=False):
    sections = [
        ProfileSectionDefinition(
            section_id='baseline', label='Baseline', purpose='Starting evidence.', order=1,
            obligation='required', minimum_placements=1, maximum_placements=1,
            allowed_candidate_kinds=('student_work',), required_relationship_kinds=('artifact_author',),
            reflection_requirement='none',
        ),
        ProfileSectionDefinition(
            section_id='current', label='Current', purpose='Later evidence.', order=2,
            obligation='required', minimum_placements=1, maximum_placements=1,
            allowed_candidate_kinds=('student_work',), required_relationship_kinds=('artifact_author',),
            reflection_requirement='required',
        ),
    ]
    if feedback:
        sections.append(ProfileSectionDefinition(
            section_id='feedback_context', label='Feedback Context', purpose='Feedback context.', order=3,
            obligation='required', minimum_placements=1, maximum_placements=1,
            allowed_candidate_kinds=('feedback',), required_relationship_kinds=(), reflection_requirement='none',
        ))
    return PortfolioProfileRevision(
        portfolio_profile_id='profile_smoke_growth', profile_revision=number,
        profile_family_id=family.profile_family_id, predecessor_revision=predecessor,
        label=f'Smoke Growth r{number}', purpose_kind='improvement',
        applicability=ProfileApplicability(), sections=tuple(sections),
        audience_rules=(ProfileAudienceRule(
            audience_rule_id='student_view', audience_class='student', purpose='Student view.',
            allowed_content_classes=('student_work','feedback','reflection'),
            prohibited_content_classes=('private_teacher_note',), required_review_classes=('privacy_review',),
            presentation_class='student_portfolio',
        ),),
        created_at=now, created_by=actor,
    )

def requirements(number, feedback=False):
    values = [
        PortfolioProfileRequirement(
            portfolio_profile_id='profile_smoke_growth', profile_revision=number,
            requirement_id='baseline_required', requirement_kind='section', obligation='required',
            title='Baseline', statement='Include one baseline item.', scope_kind='section',
            scope_reference='baseline', satisfaction_class='section_cardinality',
        ),
        PortfolioProfileRequirement(
            portfolio_profile_id='profile_smoke_growth', profile_revision=number,
            requirement_id='current_required', requirement_kind='section', obligation='required',
            title='Current', statement='Include one current item.', scope_kind='section',
            scope_reference='current', satisfaction_class='section_cardinality',
        ),
    ]
    if feedback:
        values.append(PortfolioProfileRequirement(
            portfolio_profile_id='profile_smoke_growth', profile_revision=number,
            requirement_id='feedback_required', requirement_kind='section', obligation='required',
            title='Feedback', statement='Include feedback context.', scope_kind='section',
            scope_reference='feedback_context', satisfaction_class='section_cardinality',
        ))
    return tuple(values)

first = create_profile_revision(workspace, revision(1), requirements(1), expected_state_revision=expected)
expected = first.commit.state_revision
active = activate_profile_revision(
    workspace, ProfileRevisionRef(portfolio_profile_id='profile_smoke_growth', profile_revision=1),
    actor=actor, reason='Smoke activate.', authority_reference='smoke_policy', expected_state_revision=expected,
)
expected = active.commit.state_revision
bound = bind_portfolio_profile(
    workspace, 'portfolio_1', ProfileRevisionRef(portfolio_profile_id='profile_smoke_growth', profile_revision=1),
    actor=actor, binding_reason='Smoke bind.', context=ProfileBindingContext(), expected_state_revision=expected,
)
expected = bound.commit.state_revision
second = create_profile_revision(workspace, revision(2, predecessor=1, feedback=True), requirements(2, feedback=True), expected_state_revision=expected)
expected = second.commit.state_revision
binding = get_portfolio_profile_binding(workspace, 'portfolio_1')
assert binding is not None and binding.profile_revision.profile_revision == 1
active2 = activate_profile_revision(
    workspace, ProfileRevisionRef(portfolio_profile_id='profile_smoke_growth', profile_revision=2),
    actor=actor, reason='Smoke activate successor.', authority_reference='smoke_policy', expected_state_revision=expected,
)
expected = active2.commit.state_revision
analysis, migrated = migrate_portfolio_profile(
    workspace, 'portfolio_1', ProfileRevisionRef(portfolio_profile_id='profile_smoke_growth', profile_revision=2),
    actor=actor, migration_reason='Smoke migration.', authority_reference='smoke_policy',
    context=ProfileBindingContext(), expected_state_revision=expected,
)
assert not analysis.blocked
assert migrated.commit is not None
binding = get_portfolio_profile_binding(workspace, 'portfolio_1')
assert binding is not None and binding.profile_revision.profile_revision == 2
assert binding.predecessor_binding_id is not None
"""

def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    source_before = {
        path: path.stat().st_mtime_ns
        for path in repository.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    with tempfile.TemporaryDirectory(prefix="vitrine-wheel-smoke-") as temporary:
        root = Path(temporary)
        environment = root / "venv"
        work = root / "work"
        work.mkdir()
        workspace = root / "workspace"
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PDS_WORKSPACE_ROOT"] = str(root / "environment-workspace")
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
        package_path = _run(
            [
                str(python),
                "-c",
                "import json,vitrine; print(json.dumps(vitrine.__path__[0]))",
            ],
            cwd=work,
            env=env,
        )
        installed = Path(json.loads(package_path.stdout))
        if not installed.is_dir():
            raise RuntimeError("installed package path is missing")
        installed_before = {
            path.relative_to(installed): path.read_bytes()
            for path in installed.rglob("*")
            if path.is_file()
        }
        console = _console_path(python)
        _run([str(console), "--version"], cwd=work, env=env)
        _run([str(console), "--help"], cwd=work, env=env)
        _run([str(console), "subject", "--help"], cwd=work, env=env)
        _run([str(console), "profile", "--help"], cwd=work, env=env)
        _run([str(python), "-m", "vitrine", "--version"], cwd=work, env=env)
        _run([str(python), "-m", "vitrine", "--help"], cwd=work, env=env)
        _run([str(python), "-c", _model_smoke_code()], cwd=work, env=env)
        _run([str(console), "menu"], cwd=work, env=env, input_text="Q\n")
        _run(
            [
                str(console),
                "workspace",
                "show",
                "--workspace-root",
                str(workspace),
            ],
            cwd=work,
            env=env,
        )
        if workspace.exists():
            raise RuntimeError("workspace show created the workspace")
        _run(
            [
                str(console),
                "workspace",
                "validate",
                "--workspace-root",
                str(workspace),
            ],
            cwd=work,
            env=env,
        )
        if not (workspace / ".pds" / "workspace.json").is_file():
            raise RuntimeError("workspace validate did not create Core metadata")
        _run(
            [
                str(console),
                "workspace",
                "show",
                "--workspace-root",
                str(workspace),
            ],
            cwd=work,
            env=env,
        )
        _run(
            [str(python), "-c", _storage_smoke_code(), str(workspace)],
            cwd=work,
            env=env,
        )
        _run(
            [str(python), "-c", _subject_smoke_code(), str(workspace)],
            cwd=work,
            env=env,
        )
        _run(
            [str(python), "-c", _profile_smoke_code(), str(workspace)],
            cwd=work,
            env=env,
        )
        _run(
            [
                str(console),
                "subject",
                "list",
                "--workspace-root",
                str(workspace),
            ],
            cwd=work,
            env=env,
        )
        installed_after = {
            path.relative_to(installed): path.read_bytes()
            for path in installed.rglob("*")
            if path.is_file()
        }
        if installed_before != installed_after:
            raise RuntimeError("Vitrine commands modified the installed package")
        residue = [path for path in work.iterdir()]
        if residue:
            raise RuntimeError(f"smoke current directory contains residue: {residue}")
    source_after = {
        path: path.stat().st_mtime_ns
        for path in repository.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    if source_before != source_after:
        raise RuntimeError("installed-wheel smoke test modified the source checkout")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS isolated installed-wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Wheel smoke test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
