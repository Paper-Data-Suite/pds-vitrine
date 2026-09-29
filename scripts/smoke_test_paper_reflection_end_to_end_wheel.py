"""Installed end-to-end acceptance for Issue #99 paper-native Reflection."""

from __future__ import annotations

import argparse
import os
import shutil
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
            "paper Reflection end-to-end installed command failed "
            f"with exit code {result.returncode}:\n{detail}"
        )
    return result.stdout


def _copy_fixture_harness(destination: Path) -> None:
    scripts = destination / "scripts"
    scripts.mkdir(parents=True)
    for name in ("candidate_fixture_support.py", "curation_fixture_support.py"):
        source = ROOT / "scripts" / name
        if not source.is_file():
            raise RuntimeError(f"missing installed-acceptance fixture helper: {source}")
        shutil.copyfile(source, scripts / name)

    fixture_source = ROOT / "fixtures" / "producer-adapters"
    if not fixture_source.is_dir():
        raise RuntimeError(
            "missing producer-adapter fixtures for installed acceptance"
        )
    shutil.copytree(
        fixture_source,
        destination / "fixtures" / "producer-adapters",
    )


def smoke(vitrine_wheel: Path, core_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix="vitrine-paper-reflection-e2e-wheel-"
    ) as temporary:
        root = Path(temporary)
        environment = root / "venv"
        harness = root / "harness"
        harness.mkdir()
        _copy_fixture_harness(harness)

        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        _run(
            [str(python), "-m", "pip", "install", str(core_wheel.resolve())],
            cwd=harness,
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
            cwd=harness,
            env=env,
        )

        code = r"""
import base64
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory

from pds_core.module_dispatch import RouteDispatchRequest, dispatch_route
from pds_core.module_profiles import build_module_registry
from pds_core.scan_retention import retain_source_scan

from scripts.candidate_fixture_support import STUDENT_ID
from scripts.curation_fixture_support import (
    ACTOR,
    REFLECTION_REQUIREMENT_ID,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.current_portfolio_reflection import (
    current_portfolio_reflection_bytes,
    current_portfolio_reflection_input_references,
    current_portfolio_reflection_supported,
)
from vitrine.models import (
    CurationTargetRef,
    PortfolioPlacement,
    PortfolioReflection,
    ReflectionAuthorshipConfirmation,
    ReflectionPaperFinalization,
    ReflectionPromptIssuance,
    ReflectionResponsePage,
    ReflectionReturnedPaperEvidence,
)
from vitrine.paper_reflection_authorship import (
    confirm_returned_paper_authorship,
    finalize_confirmed_paper_reflection,
)
from vitrine.paper_reflection_materialization import (
    read_paper_reflection_materialization_bytes,
    resolve_paper_reflection_materialization,
)
from vitrine.paper_reflection_printing import (
    persist_reflection_print_route_registrations,
    prepare_reflection_print_plan,
)
from vitrine.paper_reflection_services import prepare_reflection_issuance
from vitrine.paper_reflection_workflow import (
    build_paper_reflection_workflow_view,
)
from vitrine.storage import load_current_records_with_state, load_current_state
from vitrine.teacher_presentation import build_teacher_portfolio_overview

for sibling in ("scoreform", "quillan", "concord", "portia", "meridian"):
    assert importlib.util.find_spec(sibling) is None, sibling

# A valid 1x1 PNG. Image interpretation is not needed by Vitrine; exact retained
# bytes and provenance are what the paper Reflection contract materializes.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

with TemporaryDirectory(prefix="paper-reflection-case-", dir=".") as case:
    case_root = Path(case).resolve(strict=True)
    setup = build_curation_fixture_workspace(case_root)
    overview = build_teacher_portfolio_overview(
        setup.workspace,
        setup.portfolio_id,
    )
    assert len(overview.subject_links) == 1
    subject_link = overview.subject_links[0]
    assert subject_link.student_id == STUDENT_ID

    before_state, before_records = load_current_records_with_state(setup.workspace)
    before_placements = tuple(
        item for item in before_records if isinstance(item, PortfolioPlacement)
    )
    assert before_placements == ()

    targets = (
        CurationTargetRef(
            target_kind="portfolio",
            target_id=setup.portfolio_id,
        ),
    )
    prompt_id = "installed_growth_compare"
    prompt_version = "1"
    prompt_snapshot = (
        "Compare the curated Portfolio evidence. What do you notice?"
    )

    issued = prepare_reflection_issuance(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        prompt_snapshot=prompt_snapshot,
        target_scope="portfolio",
        target_references=targets,
        issued_by=ACTOR,
        page_count=1,
        expected_state_revision=before_state.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        subject_link_id=subject_link.subject_link_id,
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    issuance = next(
        item
        for item in issued.records
        if isinstance(item, ReflectionPromptIssuance)
    )
    page = next(
        item
        for item in issued.records
        if isinstance(item, ReflectionResponsePage)
    )
    assert issuance.prompt_id == prompt_id
    assert issuance.prompt_version == prompt_version
    assert issuance.prompt_snapshot == prompt_snapshot
    assert issuance.target_references == targets
    assert issuance.subject_link_id == subject_link.subject_link_id
    assert issuance.student_reference.student_id == STUDENT_ID
    assert issuance.response_page_ids == (page.response_page_id,)

    plan = prepare_reflection_print_plan(
        setup.workspace,
        issuance_id=issuance.issuance_id,
        expected_state_revision=issued.state_revision,
    )
    persisted = persist_reflection_print_route_registrations(plan)
    assert len(plan.routes) == 1
    assert len(persisted.registration_paths) == 1
    assert persisted.registration_paths[0].is_file()
    assert plan.routes[0].payload_text.startswith("PDS2|m=vitrine|")

    incoming = Path(case) / "student-reflection.png"
    incoming.write_bytes(PNG)
    retained = retain_source_scan(
        setup.workspace,
        incoming,
        intake_timestamp=fixed_clock(),
    )
    assert retained.retained_source_path.read_bytes() == PNG

    registry = build_module_registry(discover_installed=True)
    assert registry.module_ids() == ("vitrine",)
    success = dispatch_route(
        setup.workspace,
        registry,
        RouteDispatchRequest(
            plan.routes[0].locator,
            retained,
            1,
        ),
    )
    evidence = success.module_result
    assert isinstance(evidence, ReflectionReturnedPaperEvidence)
    assert evidence.issuance_id == issuance.issuance_id
    assert evidence.response_page_id == page.response_page_id
    assert evidence.route_id == page.route_id
    assert evidence.source_scan_id == retained.source_scan_id
    assert evidence.source_sha256 == retained.source_sha256
    assert evidence.retained_source_relative_path == retained.retained_source_relative_path

    state_after_dispatch = load_current_state(setup.workspace)
    confirmed = confirm_returned_paper_authorship(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        issuance_id=issuance.issuance_id,
        returned_paper_evidence_ids=(evidence.returned_paper_evidence_id,),
        confirmed_by=ACTOR,
        expected_state_revision=state_after_dispatch.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    confirmation = next(
        item
        for item in confirmed.records
        if isinstance(item, ReflectionAuthorshipConfirmation)
    )
    assert confirmation.subject_link_id == issuance.subject_link_id
    assert confirmation.student_reference == issuance.student_reference
    assert confirmation.returned_paper_evidence_ids == (
        evidence.returned_paper_evidence_id,
    )
    assert confirmation.confirmed_by == ACTOR

    finalized = finalize_confirmed_paper_reflection(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        authorship_confirmation_id=confirmation.authorship_confirmation_id,
        recorded_by=ACTOR,
        expected_state_revision=confirmed.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    reflection = next(
        item for item in finalized.records if isinstance(item, PortfolioReflection)
    )
    finalization = next(
        item
        for item in finalized.records
        if isinstance(item, ReflectionPaperFinalization)
    )

    assert reflection.author.actor_kind == "core_student"
    assert reflection.author.actor_id == STUDENT_ID
    assert reflection.author.owning_system == "core"
    assert reflection.reflection_requirement_id == REFLECTION_REQUIREMENT_ID
    assert reflection.prompt_id == prompt_id
    assert reflection.prompt_version == prompt_version
    assert reflection.prompt_snapshot == prompt_snapshot
    assert reflection.target_scope == "portfolio"
    assert reflection.target_references == targets
    assert reflection.content_mode == "external_reference"
    assert reflection.content_format == "vitrine:returned_paper_evidence"

    assert finalization.authorship_confirmation_id == confirmation.authorship_confirmation_id
    assert finalization.returned_paper_evidence_ids == (
        evidence.returned_paper_evidence_id,
    )
    assert finalization.student_author == reflection.author
    assert finalization.recorded_by == ACTOR

    final_state, final_records = load_current_records_with_state(setup.workspace)
    placements = tuple(
        item for item in final_records if isinstance(item, PortfolioPlacement)
    )
    assert placements == before_placements

    exact_reflections = tuple(
        item
        for item in final_records
        if isinstance(item, PortfolioReflection)
        and item.reflection_id == reflection.reflection_id
        and item.reflection_revision == reflection.reflection_revision
    )
    assert exact_reflections == (reflection,)

    materialization = resolve_paper_reflection_materialization(
        final_records,
        reflection,
    )
    assert materialization is not None
    assert materialization.paper_finalization_id == finalization.paper_finalization_id
    assert materialization.returned_paper_evidence_id == evidence.returned_paper_evidence_id
    assert materialization.source_sha256 == retained.source_sha256
    assert materialization.media_type == "image/png"
    assert read_paper_reflection_materialization_bytes(
        setup.workspace,
        materialization,
    ) == PNG

    assert current_portfolio_reflection_supported(
        reflection,
        records=final_records,
    )
    assert current_portfolio_reflection_bytes(
        reflection,
        workspace_root=setup.workspace,
        records=final_records,
    ) == PNG
    input_types = tuple(
        item.record_type
        for item in current_portfolio_reflection_input_references(
            reflection,
            records=final_records,
        )
    )
    assert input_types == (
        "portfolio_reflection",
        "reflection_paper_finalization",
        "reflection_returned_paper_evidence",
    )

    workflow = build_paper_reflection_workflow_view(
        setup.workspace,
        setup.portfolio_id,
    )
    requirement = next(
        item
        for item in workflow.requirements
        if item.requirement_id == REFLECTION_REQUIREMENT_ID
    )
    assert requirement.status == "recorded"
    assert requirement.reflection_id == reflection.reflection_id
    assert requirement.paper_finalization_id == finalization.paper_finalization_id
    assert final_state.state_revision == workflow.observed_state_revision

for sibling in ("scoreform", "quillan", "concord", "portia", "meridian"):
    assert importlib.util.find_spec(sibling) is None, sibling
"""
        _run([str(python), "-c", code], cwd=harness, env=env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vitrine_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        smoke(args.vitrine_wheel, args.core_wheel)
        print("PASS installed paper Reflection end-to-end wheel acceptance")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(
            f"Paper Reflection end-to-end wheel acceptance failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
