"""Smoke issue #67 guided Working Composition from installed Core/Vitrine wheels."""

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
            "guided Working Composition installed command failed "
            f"with exit code {result.returncode}:\n{detail}"
        )
    return result.stdout


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix="vitrine-working-composition-wheel-smoke-"
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

        code = r"""
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

from pds_core.workspace import ensure_workspace_root

from vitrine import cli
from vitrine.curation_services import (
    CurationAuthorityDecision,
    CurationAuthorityRequest,
)
from vitrine.models import (
    ActorAttribution,
    Portfolio,
    PortfolioProfileBinding,
    PortfolioProfileFamily,
    PortfolioProfileLifecycleEvent,
    PortfolioProfileRequirement,
    PortfolioProfileRevision,
    PortfolioSubject,
    ProfileApplicability,
    ProfileAudienceRule,
    ProfileSectionDefinition,
)
from vitrine.storage import commit_record_batch, load_current_state
from vitrine.working_composition import (
    WORKING_COMPOSITION_CONTRACT_VERSION,
    freeze_prepared_working_composition,
    prepare_working_composition,
)

NOW = datetime(2026, 9, 7, 22, 0, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="wheel_smoke_teacher",
    owning_system="local",
    role_snapshot="teacher",
)


class Gate:
    def __init__(self):
        self.requests = []

    def authorize(self, request: CurationAuthorityRequest) -> CurationAuthorityDecision:
        self.requests.append(request)
        return CurationAuthorityDecision(
            outcome="allowed",
            authority_reference="wheel_smoke_authority",
            reason_codes=("wheel_smoke",),
        )


workspace = ensure_workspace_root(Path(sys.argv[1]), create=True)
subject = PortfolioSubject(
    portfolio_subject_id="subject_wheel_smoke",
    created_at=NOW,
    created_by=ACTOR,
    display_name_snapshot="Synthetic Wheel Student",
)
portfolio = Portfolio(
    portfolio_id="portfolio_wheel_smoke",
    portfolio_subject_id=subject.portfolio_subject_id,
    created_at=NOW,
    created_by=ACTOR,
    title_snapshot="Working Composition Wheel Smoke",
)
family = PortfolioProfileFamily(
    profile_family_id="family_wheel_smoke",
    label="Wheel Smoke Profiles",
    purpose_kind="improvement",
    created_at=NOW,
    created_by=ACTOR,
)
sections = (
    ProfileSectionDefinition(
        section_id="required_evidence",
        label="Required Evidence",
        purpose="One required evidence Placement.",
        order=1,
        obligation="required",
        minimum_placements=1,
        maximum_placements=2,
        allowed_candidate_kinds=("student_work",),
        required_relationship_kinds=(),
        reflection_requirement="none",
    ),
    ProfileSectionDefinition(
        section_id="optional_context",
        label="Optional Context",
        purpose="Optional context follows required evidence.",
        order=2,
        obligation="optional",
        minimum_placements=0,
        maximum_placements=2,
        allowed_candidate_kinds=("student_work",),
        required_relationship_kinds=(),
        reflection_requirement="none",
    ),
)
profile = PortfolioProfileRevision(
    portfolio_profile_id="profile_wheel_smoke",
    profile_revision=1,
    profile_family_id=family.profile_family_id,
    predecessor_revision=None,
    label="Working Composition Wheel Smoke",
    purpose_kind="improvement",
    applicability=ProfileApplicability(school_years=("2026-2027",)),
    sections=sections,
    audience_rules=(
        ProfileAudienceRule(
            audience_rule_id="student_internal",
            audience_class="student",
            purpose="Student-facing future Snapshot constraint.",
            allowed_content_classes=("student_work",),
            prohibited_content_classes=("private_teacher_note",),
            required_review_classes=("privacy_review",),
            presentation_class="student_portfolio",
        ),
    ),
    created_at=NOW,
    created_by=ACTOR,
    source_authority_references=("wheel_smoke_policy",),
)
requirement = PortfolioProfileRequirement(
    portfolio_profile_id=profile.portfolio_profile_id,
    profile_revision=profile.profile_revision,
    requirement_id="required_evidence_cardinality",
    requirement_kind="section",
    obligation="required",
    title="Required evidence",
    statement="Synthetic machine-readable cardinality requirement.",
    scope_kind="section",
    satisfaction_class="placement_cardinality",
    scope_reference="required_evidence",
    authority_references=("wheel_smoke_policy",),
)
lifecycle = PortfolioProfileLifecycleEvent(
    profile_lifecycle_event_id="profile_event_wheel_smoke",
    profile_revision=profile.reference,
    event_kind="activated",
    event_at=NOW,
    effective_at=NOW,
    actor=ACTOR,
    reason="Activate synthetic wheel-smoke Profile.",
    authority_reference="wheel_smoke_policy",
)
binding = PortfolioProfileBinding(
    profile_binding_id="binding_wheel_smoke",
    portfolio_id=portfolio.portfolio_id,
    profile_revision=profile.reference,
    bound_at=NOW,
    bound_by=ACTOR,
    binding_reason="Synthetic wheel-smoke binding.",
)

commit_record_batch(
    workspace,
    (subject, portfolio, family, profile, requirement, lifecycle, binding),
    expected_state_revision=None,
)

before = load_current_state(workspace).state_revision
preparation = prepare_working_composition(workspace, portfolio.portfolio_id)
assert WORKING_COMPOSITION_CONTRACT_VERSION == "vitrine_guided_working_composition_v1"
assert load_current_state(workspace).state_revision == before
assert preparation.observed_state_revision == before
assert preparation.observed_composition_pointer_revision is None
assert preparation.disposition == "create_initial"
assert preparation.payload.coherence_state == "coherent_with_unresolved_obligations"
assert "section_minimum_missing" in preparation.payload.unresolved_obligation_codes
assert tuple(item.section_id for item in preparation.sections) == (
    "required_evidence",
    "optional_context",
)
required_summary = next(
    item
    for item in preparation.requirements
    if item.requirement_id == "required_evidence_cardinality"
)
assert required_summary.status == "unresolved_missing"
assert preparation.audience_rules[0].audience_rule_id == "student_internal"
assert preparation.audience_rules[0].prohibited_content_classes == (
    "private_teacher_note",
)
assert len(preparation.preparation_fingerprint) == 64

gate = Gate()
created = freeze_prepared_working_composition(
    workspace,
    preparation,
    created_by=ACTOR,
    authority_gate=gate,
)
assert created.disposition == "created"
assert len(gate.requests) == 1
assert gate.requests[0].operation == "compose_portfolio"
after_create = load_current_state(workspace).state_revision
assert after_create > before

replay = prepare_working_composition(workspace, portfolio.portfolio_id)
assert replay.current_composition_revision == 1
assert replay.predicted_composition_revision == 1
assert replay.disposition == "reuse_exact_current"
before_replay = load_current_state(workspace).state_revision
reused = freeze_prepared_working_composition(
    workspace,
    replay,
    created_by=ACTOR,
    authority_gate=gate,
)
assert reused.disposition == "existing"
assert load_current_state(workspace).state_revision == before_replay

parser = cli.build_parser()
assert (
    parser.parse_args(
        ["composition", "prepare", portfolio.portfolio_id]
    ).composition_command
    == "prepare"
)
parsed_freeze = parser.parse_args(
    [
        "composition",
        "freeze",
        portfolio.portfolio_id,
        "--preparation-fingerprint",
        replay.preparation_fingerprint,
        "--expected-state-revision",
        str(replay.observed_state_revision),
        "--expected-composition-pointer-revision",
        "1",
        "--actor-id",
        ACTOR.actor_id,
    ]
)
assert parsed_freeze.composition_command == "freeze"
assert parsed_freeze.expected_composition_pointer_revision == "1"

for name in ("scoreform", "quillan", "concord", "portia", "meridian"):
    assert importlib.util.find_spec(name) is None
"""
        _run([str(python), "-c", code, str(workspace)], cwd=work, env=env)
        if list(work.iterdir()):
            raise RuntimeError(
                "guided Working Composition wheel smoke left current-directory residue"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS isolated guided Working Composition wheel smoke test")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(
            f"Guided Working Composition wheel smoke test failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
