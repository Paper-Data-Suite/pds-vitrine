"""Presentation-independent Snapshot planning orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol

from vitrine.models import (
    ActorAttribution,
    SnapshotEntryPlan,
    SnapshotExportPlan,
)
from vitrine.models.conversion import dataclass_from_dict
from vitrine.snapshot_custody import SNAPSHOT_DIGEST_POLICY_ID, SNAPSHOT_PATH_POLICY_ID
from vitrine.snapshot_services import (
    SNAPSHOT_BUILDER_CONTRACT_ID,
    SNAPSHOT_BUILDER_CONTRACT_VERSION,
    SnapshotMutationResult,
    plan_snapshot_build,
)


class SnapshotPlanningError(ValueError):
    def __init__(self, code: str, message: str, *, stage: str = "planning") -> None:
        self.code = code
        self.stage = stage
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class SnapshotPlanSpecification:
    entry_plans: tuple[SnapshotEntryPlan, ...]
    export_plans: tuple[SnapshotExportPlan, ...]
    acknowledged_obligation_codes: tuple[str, ...] = ()
    predecessor_plan_id: str | None = None
    builder_contract_id: str = SNAPSHOT_BUILDER_CONTRACT_ID
    builder_contract_version: str = SNAPSHOT_BUILDER_CONTRACT_VERSION
    path_policy_id: str = SNAPSHOT_PATH_POLICY_ID
    digest_policy_id: str = SNAPSHOT_DIGEST_POLICY_ID


@dataclass(frozen=True, slots=True)
class SnapshotPlanningRequest:
    snapshot_build_request_id: str
    planned_by: ActorAttribution
    expected_state_revision: int


class SnapshotPlanningProvider(Protocol):
    def propose(
        self, workspace_root: str | Path, request: SnapshotPlanningRequest
    ) -> SnapshotPlanSpecification: ...


class UnconfiguredSnapshotPlanningProvider:
    def propose(
        self, workspace_root: str | Path, request: SnapshotPlanningRequest
    ) -> SnapshotPlanSpecification:
        raise SnapshotPlanningError(
            "snapshot_planning_unconfigured",
            "Snapshot planning provider is not configured.",
        )


def snapshot_plan_specification_from_dict(
    value: Mapping[str, object],
) -> SnapshotPlanSpecification:
    allowed = {
        "entry_plans",
        "export_plans",
        "acknowledged_obligation_codes",
        "predecessor_plan_id",
        "builder_contract_id",
        "builder_contract_version",
        "path_policy_id",
        "digest_policy_id",
    }
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise SnapshotPlanningError(
            "snapshot_plan_specification_invalid",
            f"Plan specification contains unknown key(s): {', '.join(unknown)}.",
        )
    entries_value = value.get("entry_plans")
    exports_value = value.get("export_plans")
    if not isinstance(entries_value, list) or not isinstance(exports_value, list):
        raise SnapshotPlanningError(
            "snapshot_plan_specification_invalid",
            "Plan specification requires entry_plans and export_plans arrays.",
        )
    try:
        entries = tuple(
            dataclass_from_dict(SnapshotEntryPlan, item, label="entry_plans[]")
            for item in entries_value
            if isinstance(item, Mapping)
        )
        exports = tuple(
            dataclass_from_dict(SnapshotExportPlan, item, label="export_plans[]")
            for item in exports_value
            if isinstance(item, Mapping)
        )
        if len(entries) != len(entries_value) or len(exports) != len(exports_value):
            raise ValueError("plan arrays must contain objects")
        acknowledged = value.get("acknowledged_obligation_codes", [])
        if not isinstance(acknowledged, list) or not all(
            isinstance(item, str) for item in acknowledged
        ):
            raise ValueError(
                "acknowledged_obligation_codes must be an array of strings"
            )
        optional_strings: dict[str, str | None] = {}
        for name in (
            "predecessor_plan_id",
            "builder_contract_id",
            "builder_contract_version",
            "path_policy_id",
            "digest_policy_id",
        ):
            item = value.get(name)
            if item is not None and not isinstance(item, str):
                raise ValueError(f"{name} must be a string or null")
            optional_strings[name] = item
    except (TypeError, ValueError) as exc:
        raise SnapshotPlanningError(
            "snapshot_plan_specification_invalid", f"Invalid plan specification: {exc}"
        ) from exc
    defaults = SnapshotPlanSpecification(entries, exports)
    return SnapshotPlanSpecification(
        entry_plans=entries,
        export_plans=exports,
        acknowledged_obligation_codes=tuple(acknowledged),
        predecessor_plan_id=optional_strings["predecessor_plan_id"],
        builder_contract_id=optional_strings["builder_contract_id"]
        or defaults.builder_contract_id,
        builder_contract_version=optional_strings["builder_contract_version"]
        or defaults.builder_contract_version,
        path_policy_id=optional_strings["path_policy_id"] or defaults.path_policy_id,
        digest_policy_id=optional_strings["digest_policy_id"]
        or defaults.digest_policy_id,
    )


def prepare_snapshot_build(
    workspace_root: str | Path,
    request: SnapshotPlanningRequest,
    *,
    provider: SnapshotPlanningProvider,
    specification: SnapshotPlanSpecification | None = None,
) -> SnapshotMutationResult:
    """Obtain an exact proposal, then delegate all validation/persistence."""
    proposal = specification or provider.propose(workspace_root, request)
    return plan_snapshot_build(
        workspace_root,
        snapshot_build_request_id=request.snapshot_build_request_id,
        entry_plans=proposal.entry_plans,
        export_plans=proposal.export_plans,
        planned_by=request.planned_by,
        expected_state_revision=request.expected_state_revision,
        acknowledged_obligation_codes=proposal.acknowledged_obligation_codes,
        predecessor_plan_id=proposal.predecessor_plan_id,
        builder_contract_id=proposal.builder_contract_id,
        builder_contract_version=proposal.builder_contract_version,
        path_policy_id=proposal.path_policy_id,
        digest_policy_id=proposal.digest_policy_id,
    )


__all__ = [
    "SnapshotPlanSpecification",
    "SnapshotPlanningError",
    "SnapshotPlanningProvider",
    "SnapshotPlanningRequest",
    "UnconfiguredSnapshotPlanningProvider",
    "prepare_snapshot_build",
    "snapshot_plan_specification_from_dict",
]
