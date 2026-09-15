"""Run Vitrine issue #71 installed healthy-path acceptance through Slice 3."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
from collections.abc import Callable
from importlib import metadata
from pathlib import Path
from typing import TypeVar

from live_installed_acceptance_portfolio import (
    build_representative_snapshot,
    curate_representative_portfolio,
)
from live_installed_acceptance_support import (
    DeterministicIds,
    build_concord_publication,
    build_quillan_publication,
    build_scoreform_publication,
    discover_live_candidates,
    install_improvement_portfolio,
    low_density_json,
    prepare_core_identity_sources,
)

from vitrine.current_portfolio_execution import CurrentPortfolioExecutionError

EXPECTED_VERSIONS = {
    "pds-core": "0.6.3",
    "scoreform": "0.11.0",
    "quillan": "0.10.0",
    "pds-concord": "0.3.0",
    "pds-vitrine": "0.2.0",
}

_T = TypeVar("_T")


class ScenarioStageError(RuntimeError):
    """Bounded stage failure that never renders producer-native content."""

    def __init__(
        self,
        stage: str,
        cause_type: str,
        *,
        diagnostic_fields: dict[str, object] | None = None,
    ) -> None:
        super().__init__(stage)
        self.stage = stage
        self.cause_type = cause_type
        self.diagnostic_fields = dict(diagnostic_fields or {})


def _origin(name: str) -> Path:
    module = importlib.import_module(name)
    raw = getattr(module, "__file__", None)
    if not isinstance(raw, str) or not raw:
        raise RuntimeError(f"{name} has no installed origin")
    return Path(raw).resolve()


def _require_installed_isolation(repository: Path) -> None:
    if "PYTHONPATH" in os.environ:
        raise RuntimeError("PYTHONPATH must be absent in the live scenario")
    for distribution, version in EXPECTED_VERSIONS.items():
        if metadata.version(distribution) != version:
            raise RuntimeError(f"installed version mismatch for {distribution}")
    prefix = Path(sys.prefix).resolve()
    for module_name in (
        "pds_core",
        "scoreform",
        "quillan",
        "concord",
        "vitrine",
    ):
        origin = _origin(module_name)
        if (
            not origin.is_relative_to(prefix)
            or "site-packages" not in {part.casefold() for part in origin.parts}
            or origin.is_relative_to(repository)
        ):
            raise RuntimeError(
                f"{module_name} did not import from isolated site-packages"
            )



def _snapshot_validation_issue_code(error: BaseException) -> str | None:
    """Extract only the stable first Snapshot validation-issue token."""

    current: BaseException | None = error
    seen: set[int] = set()
    pattern = re.compile(
        r"^Snapshot transition is invalid \((snapshot\.[a-z0-9_]+)\)\.$"
    )
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if type(current).__name__ == "SnapshotWorkflowError":
            raw = current.args[0] if current.args else None
            if isinstance(raw, str):
                match = pattern.fullmatch(raw)
                if match is not None:
                    return match.group(1)
        current = current.__cause__
    return None

def _stage(label: str, action: Callable[[], _T]) -> _T:
    print(f"Running: {label}", flush=True)
    try:
        result = action()
    except Exception as error:
        diagnostics: dict[str, object] = {}
        if isinstance(error, CurrentPortfolioExecutionError):
            diagnostics = {
                "execution_code": error.code,
                "execution_stage": error.stage,
                "underlying_code": error.underlying_code,
                "underlying_stage": error.underlying_stage,
                "validation_issue_code": _snapshot_validation_issue_code(error),
                "next_safe_action": error.next_safe_action,
                "completed_stages": list(error.completed_stages),
            }
        raise ScenarioStageError(
            label,
            type(error).__name__,
            diagnostic_fields=diagnostics,
        ) from error
    print(f"PASSED: {label}", flush=True)
    return result


def run(
    *,
    workspace: Path,
    repository: Path,
    work_root: Path,
    portfolio_snapshot: bool = False,
) -> dict[str, object]:
    repository = repository.resolve(strict=True)
    workspace = workspace.resolve()
    work_root = work_root.resolve()
    if workspace.exists():
        raise RuntimeError("installed acceptance workspace must begin absent")
    if workspace.is_relative_to(repository) or work_root.is_relative_to(repository):
        raise RuntimeError("installed acceptance roots must remain outside the repository")
    work_root.mkdir(parents=True, exist_ok=True)
    _require_installed_isolation(repository)

    ids = DeterministicIds()
    standards = _stage(
        "Core synthetic class identity sources",
        lambda: prepare_core_identity_sources(workspace),
    )
    scoreform = _stage(
        "ScoreForm native publication",
        lambda: build_scoreform_publication(workspace),
    )
    quillan = _stage(
        "Quillan native publication",
        lambda: build_quillan_publication(
            workspace,
            standards=standards,
            work_root=work_root,
        ),
    )
    concord = _stage(
        "Concord native publication",
        lambda: build_concord_publication(workspace, standards=standards),
    )
    publications = (scoreform, quillan, concord)

    portfolio = _stage(
        "Vitrine Starter Improvement Portfolio and explicit Subject links",
        lambda: install_improvement_portfolio(workspace, ids=ids),
    )
    candidate_summary, gate = _stage(
        "Vitrine live Candidate discovery",
        lambda: discover_live_candidates(
            workspace,
            portfolio=portfolio,
            publications=publications,
            ids=ids,
        ),
    )
    summary: dict[str, object] = {
        "mode": (
            "slice3_curated_snapshot_acceptance"
            if portfolio_snapshot
            else "slice2_live_candidate_acceptance"
        ),
        "producer_publications": sorted(item.module_id for item in publications),
        "explicit_subject_class_links": 3,
        "source_authorization_requests": len(gate.requests),
        "candidate_discovery": candidate_summary,
        "fixture_registry_used": False,
        "full_acceptance_ready": False,
    }
    if not portfolio_snapshot:
        return summary

    curated, curation_gate = _stage(
        "Vitrine explicit representative curation",
        lambda: curate_representative_portfolio(
            workspace,
            portfolio=portfolio,
            ids=ids,
        ),
    )
    built = _stage(
        "Vitrine authorized Snapshot build, seal, verify, and Export",
        lambda: build_representative_snapshot(
            workspace,
            portfolio=portfolio,
            publications=publications,
            curation_gate=curation_gate,
        ),
    )
    summary["curation"] = {
        "selection_count": len(curated.selection_ids),
        "placement_count": len(curated.placement_ids),
        "reflection_count": 1,
        "teacher_review_count": 1,
        "composition_revision": curated.composition_revision,
    }
    summary["snapshot"] = {
        "edition_number": built.edition_number,
        "materializations": built.materialization_counts,
        "copied_artifact_kinds": built.copied_artifact_kinds,
        "curation_authorization_requests": built.curation_authorization_requests,
        "snapshot_source_read_requests": built.snapshot_source_read_requests,
        "quillan_artifact_authorization_requests": (
            built.quillan_artifact_authorization_requests
        ),
        "concord_artifact_authorization_requests": (
            built.concord_artifact_authorization_requests
        ),
        "snapshot_build_authorization_requests": (
            built.snapshot_build_authorization_requests
        ),
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--portfolio-snapshot", action="store_true")
    args = parser.parse_args(argv)
    try:
        summary = run(
            workspace=args.workspace,
            repository=args.repository,
            work_root=args.work_root,
            portfolio_snapshot=args.portfolio_snapshot,
        )
    except ScenarioStageError as error:
        print(
            json.dumps(
                {
                    "mode": (
                        "slice3_curated_snapshot_acceptance"
                        if args.portfolio_snapshot
                        else "slice2_live_candidate_acceptance"
                    ),
                    "status": "failed",
                    "error_stage": error.stage,
                    "error_type": error.cause_type,
                    **error.diagnostic_fields,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    except Exception as error:
        print(
            json.dumps(
                {
                    "mode": (
                        "slice3_curated_snapshot_acceptance"
                        if args.portfolio_snapshot
                        else "slice2_live_candidate_acceptance"
                    ),
                    "status": "failed",
                    "error_stage": "scenario_preflight",
                    "error_type": type(error).__name__,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(low_density_json(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
