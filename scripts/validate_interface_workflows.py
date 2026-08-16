#!/usr/bin/env python3
"""Execute one synthetic workflow through public interface/orchestration seams."""

# ruff: noqa: E402
from __future__ import annotations

import io
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.improvement_portfolio_fixture_support import (
    PORTFOLIO_ID,
    SUBJECT_ID,
    TEACHER,
    ImprovementPortfolioFixture,
    build_improvement_portfolio_fixture,
)
from scripts.validate_improvement_portfolio import _entry_plans
from scripts.validate_snapshot_workflows import (
    EXPORT_CONFIGURATION_BYTES,
    _digest,
    _FixtureAuthorityGate,
    _provider_registry,
    _ReflectionFixtureRenderer,
)
from vitrine.cli import main as cli_main
from vitrine.menu import run_menu
from vitrine.models import (
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotExportPlan,
    SnapshotSeries,
)
from vitrine.snapshot_materialization import SnapshotRendererRegistry
from vitrine.snapshot_planning import (
    SnapshotPlanningRequest,
    SnapshotPlanSpecification,
    prepare_snapshot_build,
)
from vitrine.storage import load_current_records, load_current_state
from vitrine.workflow_context import (
    VitrineWorkflowDependencies,
    default_workflow_dependencies,
)


class _FixturePlanningProvider:
    def __init__(self, fixture: ImprovementPortfolioFixture) -> None:
        self.fixture = fixture

    def propose(
        self, workspace_root: str | Path, request: SnapshotPlanningRequest
    ) -> SnapshotPlanSpecification:
        entries = _entry_plans(self.fixture)
        export = SnapshotExportPlan(
            export_plan_id="export-plan-interface-directory",
            export_format="directory_package",
            export_contract_version="1",
            included_entry_plan_ids=tuple(item.entry_plan_id for item in entries),
            excluded_entry_plan_ids=(),
            configuration_digest=_digest(EXPORT_CONFIGURATION_BYTES),
        )
        return SnapshotPlanSpecification(
            entries,
            (export,),
            self.fixture.inventory.unresolved_obligation_codes,
        )


def _run(arguments: list[str], dependencies: VitrineWorkflowDependencies) -> str:
    output, error = io.StringIO(), io.StringIO()
    if cli_main(arguments, output=output, error=error, dependencies=dependencies) != 0:
        raise RuntimeError(f"interface command failed: {error.getvalue().strip()}")
    return output.getvalue()


def validate() -> None:
    with tempfile.TemporaryDirectory(prefix="vitrine-interface-workflow-") as raw:
        fixture = build_improvement_portfolio_fixture(Path(raw))
        if not isinstance(fixture, ImprovementPortfolioFixture):
            raise RuntimeError("development fixture did not build")
        workspace = str(fixture.workspace)
        dependencies = replace(
            default_workflow_dependencies(),
            snapshot_planning_provider=_FixturePlanningProvider(fixture),
            snapshot_build_authority_gate=_FixtureAuthorityGate(),
            snapshot_renderers=SnapshotRendererRegistry(
                (_ReflectionFixtureRenderer(reflection=fixture.reflection),)
            ),
            development_fixture_mode=True,
        )
        created = _run(
            [
                "portfolio",
                "create",
                "--subject-id",
                SUBJECT_ID,
                "--title",
                "Interface acceptance Portfolio",
                "--actor-id",
                TEACHER.actor_id,
                "--workspace-root",
                workspace,
            ],
            dependencies,
        )
        if "Created Portfolio:" not in created:
            raise RuntimeError("Portfolio create interface did not execute")
        for arguments in (
            ["portfolio", "show", PORTFOLIO_ID, "--workspace-root", workspace],
            [
                "candidate",
                "show",
                fixture.candidates[0].candidate_id,
                "--workspace-root",
                workspace,
            ],
            [
                "arrangement",
                "show",
                PORTFOLIO_ID,
                "--section-id",
                "baseline",
                "--workspace-root",
                workspace,
            ],
            ["composition", "show", PORTFOLIO_ID, "--workspace-root", workspace],
            [
                "audience",
                "show",
                fixture.audience.audience_context_id,
                "--workspace-root",
                workspace,
            ],
        ):
            _run(arguments, dependencies)

        _run(
            [
                "snapshot",
                "series",
                "create",
                PORTFOLIO_ID,
                "--audience-context-id",
                fixture.audience.audience_context_id,
                "--purpose",
                "interface_acceptance",
                "--actor-id",
                TEACHER.actor_id,
                "--workspace-root",
                workspace,
            ],
            dependencies,
        )
        series = next(
            item
            for item in load_current_records(fixture.workspace)
            if isinstance(item, SnapshotSeries)
            and item.snapshot_purpose == "interface_acceptance"
        )
        _run(
            [
                "snapshot",
                "request",
                series.snapshot_series_id,
                "--composition-revision",
                str(fixture.composition.composition_revision),
                "--actor-id",
                TEACHER.actor_id,
                "--workspace-root",
                workspace,
            ],
            dependencies,
        )
        request = next(
            item
            for item in load_current_records(fixture.workspace)
            if isinstance(item, SnapshotBuildRequest)
            and item.snapshot_series_id == series.snapshot_series_id
        )
        planned = prepare_snapshot_build(
            fixture.workspace,
            SnapshotPlanningRequest(
                request.snapshot_build_request_id,
                TEACHER,
                load_current_state(fixture.workspace).state_revision,
            ),
            provider=dependencies.snapshot_planning_provider,
        )
        plan = next(
            item for item in planned.records if isinstance(item, SnapshotBuildPlan)
        )
        dependencies = replace(
            dependencies,
            snapshot_source_providers=_provider_registry(
                plan.entry_plans, fixture.source_root
            ),
        )
        built = _run(
            [
                "snapshot",
                "build",
                plan.snapshot_build_plan_id,
                "--actor-id",
                TEACHER.actor_id,
                "--workspace-root",
                workspace,
            ],
            dependencies,
        )
        if "Sealed Edition:" not in built:
            raise RuntimeError("Snapshot build did not seal an Edition")
        verified = _run(
            [
                "snapshot",
                "verify",
                series.snapshot_series_id,
                "--edition",
                "1",
                "--workspace-root",
                workspace,
            ],
            dependencies,
        )
        if "Edition verification: verified" not in verified:
            raise RuntimeError("exact Edition verification did not execute")

        menu_output = io.StringIO()
        if (
            run_menu(
                input_fn=lambda _prompt: "Q", output=menu_output, clear_fn=lambda: None
            )
            != 0
            or "Portfolios" not in menu_output.getvalue()
        ):
            raise RuntimeError(
                "teacher menu did not unwind from its Portfolio-centered screen"
            )
        ordinary = default_workflow_dependencies()
        if ordinary.adapter_registry.adapters or ordinary.producer_registry.profiles:
            raise RuntimeError("ordinary runtime silently enabled development fixtures")


def main() -> int:
    validate()
    print("PASS interface workflow validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
