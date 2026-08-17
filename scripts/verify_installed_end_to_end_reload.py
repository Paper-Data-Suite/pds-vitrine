"""Reload and verify installed Vitrine historical state in a fresh interpreter."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from vitrine.models import (
    PortfolioProfileBinding,
    SnapshotBuildAttempt,
    SnapshotBuildAttemptResult,
    SnapshotBuildPlan,
    SnapshotBuildRequest,
    SnapshotCurrentPointerRevision,
    SnapshotEdition,
    SnapshotExportArtifact,
    SnapshotSeal,
    SnapshotSeries,
    WorkingPortfolioCompositionRevision,
)
from vitrine.models.serialization import record_to_canonical_json_bytes
from vitrine.snapshot_distribution import (
    verify_snapshot_edition,
    verify_snapshot_export,
)
from vitrine.storage import load_current_records, load_current_state
from vitrine.workflow_views import show_snapshot_series


class HistoricalReloadError(RuntimeError):
    """Bounded failure from the fresh-process historical reload acceptance."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HistoricalReloadError(message)


def _installed_origin(name: str) -> Path:
    module = import_module(name)
    raw = getattr(module, "__file__", None)
    _require(isinstance(raw, str) and bool(raw), f"{name} has no installed origin")
    assert isinstance(raw, str)
    path = Path(raw).resolve()
    lowered = {part.casefold() for part in path.parts}
    _require(
        path.is_relative_to(Path(sys.prefix).resolve()) and "site-packages" in lowered,
        f"{name} did not reload from site-packages",
    )
    return path


def _load_expectations(path: Path) -> dict[str, object]:
    try:
        raw = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HistoricalReloadError("historical expectation file is unreadable") from error
    _require(isinstance(raw, dict), "historical expectations must be one object")
    assert isinstance(raw, dict)
    expected_keys = {
        "workspace_state_revision",
        "record_inventory",
        "record_inventory_sha256",
        "snapshots",
        "pointer_probe",
    }
    _require(set(raw) == expected_keys, "historical expectation schema is not exact")
    return cast(dict[str, object], raw)


def _record_inventory(records: tuple[Any, ...]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for record in records:
        record_type = getattr(record, "record_type", None)
        _require(isinstance(record_type, str), "historical record lacks record_type")
        assert isinstance(record_type, str)
        grouped.setdefault(record_type, []).append(
            hashlib.sha256(record_to_canonical_json_bytes(record)).hexdigest()
        )
    return {
        record_type: sorted(digests)
        for record_type, digests in sorted(grouped.items())
    }


def _expect_snapshot_rows(value: object) -> tuple[dict[str, object], ...]:
    _require(isinstance(value, list) and len(value) == 2, "expected two Snapshot rows")
    assert isinstance(value, list)
    required = {
        "snapshot_series_id",
        "build_request_id",
        "build_plan_id",
        "build_plan_fingerprint",
        "build_attempt_id",
        "edition_number",
        "seal_id",
        "manifest_sha256",
        "logical_inventory_sha256",
        "export_artifact_id",
        "export_inventory_sha256",
        "current_pointer_revision",
    }
    rows: list[dict[str, object]] = []
    for raw in value:
        _require(isinstance(raw, dict), "Snapshot expectation row is not an object")
        assert isinstance(raw, dict)
        _require(set(raw) == required, "Snapshot expectation row schema is not exact")
        rows.append(cast(dict[str, object], raw))
    return tuple(rows)


def _expect_pointer_probe(value: object) -> dict[str, object]:
    _require(isinstance(value, dict), "pointer expectation is not an object")
    assert isinstance(value, dict)
    required = {
        "snapshot_series_id",
        "pointed_edition_number",
        "greatest_edition_number",
        "successor_manifest_sha256",
        "successor_logical_inventory_sha256",
    }
    _require(set(value) == required, "pointer expectation schema is not exact")
    series_id = value["snapshot_series_id"]
    pointed = value["pointed_edition_number"]
    greatest = value["greatest_edition_number"]
    _require(
        isinstance(series_id, str)
        and isinstance(pointed, int)
        and not isinstance(pointed, bool)
        and isinstance(greatest, int)
        and not isinstance(greatest, bool)
        and pointed < greatest,
        "pointer expectation identity is invalid",
    )
    for key in ("successor_manifest_sha256", "successor_logical_inventory_sha256"):
        digest = value[key]
        _require(
            isinstance(digest, str)
            and len(digest) == 64
            and all(character in "0123456789abcdef" for character in digest),
            "pointer expectation digest is invalid",
        )
    return cast(dict[str, object], value)


def _one(records: tuple[Any, ...], expected_type: type[Any], predicate: Any, label: str) -> Any:
    matches = tuple(
        item for item in records if isinstance(item, expected_type) and predicate(item)
    )
    _require(len(matches) == 1, f"historical {label} did not resolve exactly")
    return matches[0]


def verify(workspace: Path, expectations_path: Path) -> dict[str, object]:
    resolved_workspace = workspace.resolve(strict=True)
    _installed_origin("vitrine")
    _installed_origin("pds_core")
    _require(
        not (resolved_workspace.parent / "producer-source").exists(),
        "historical reload unexpectedly depends on producer-source availability",
    )
    expectations = _load_expectations(expectations_path.resolve(strict=True))
    expected_revision = expectations["workspace_state_revision"]
    _require(
        isinstance(expected_revision, int) and not isinstance(expected_revision, bool),
        "historical state revision expectation is invalid",
    )
    assert isinstance(expected_revision, int)
    before_revision = load_current_state(resolved_workspace).state_revision
    _require(before_revision == expected_revision, "historical workspace revision changed")

    records = load_current_records(resolved_workspace)
    actual_inventory = _record_inventory(records)
    raw_inventory = expectations["record_inventory"]
    _require(isinstance(raw_inventory, dict), "historical record inventory is invalid")
    assert isinstance(raw_inventory, dict)
    expected_inventory = cast(dict[str, object], raw_inventory)
    _require(actual_inventory == expected_inventory, "historical canonical record inventory changed")
    expected_inventory_sha = expectations["record_inventory_sha256"]
    _require(isinstance(expected_inventory_sha, str), "historical inventory digest is invalid")
    digest = hashlib.sha256(
        json.dumps(
            actual_inventory,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    _require(digest == expected_inventory_sha, "historical record inventory digest changed")

    bindings = tuple(item for item in records if isinstance(item, PortfolioProfileBinding))
    compositions = tuple(
        item for item in records if isinstance(item, WorkingPortfolioCompositionRevision)
    )
    _require(len(compositions) == 2, "historical Composition inventory is not exact")
    for composition in compositions:
        binding = _one(
            bindings,
            PortfolioProfileBinding,
            lambda item: item.profile_binding_id == composition.profile_binding_id,
            "Composition Binding",
        )
        _require(
            binding.profile_revision == composition.profile_revision,
            "historical Composition no longer resolves its own frozen Binding revision",
        )

    snapshots = _expect_snapshot_rows(expectations["snapshots"])
    for expected in snapshots:
        series_id = expected["snapshot_series_id"]
        edition_number = expected["edition_number"]
        _require(
            isinstance(series_id, str)
            and isinstance(edition_number, int)
            and not isinstance(edition_number, bool),
            "historical Snapshot identity is invalid",
        )
        assert isinstance(series_id, str)
        assert isinstance(edition_number, int)
        series = _one(
            records,
            SnapshotSeries,
            lambda item: item.snapshot_series_id == series_id,
            "Snapshot Series",
        )
        request = _one(
            records,
            SnapshotBuildRequest,
            lambda item: item.snapshot_build_request_id == expected["build_request_id"],
            "Snapshot Build Request",
        )
        plan = _one(
            records,
            SnapshotBuildPlan,
            lambda item: item.snapshot_build_plan_id == expected["build_plan_id"],
            "Snapshot Build Plan",
        )
        attempt = _one(
            records,
            SnapshotBuildAttempt,
            lambda item: item.snapshot_build_attempt_id == expected["build_attempt_id"],
            "Snapshot Build Attempt",
        )
        attempt_result = _one(
            records,
            SnapshotBuildAttemptResult,
            lambda item: item.snapshot_build_attempt_id == attempt.snapshot_build_attempt_id,
            "Snapshot Build Attempt Result",
        )
        edition = _one(
            records,
            SnapshotEdition,
            lambda item: item.snapshot_series_id == series_id
            and item.edition_number == edition_number,
            "Snapshot Edition",
        )
        seal = _one(
            records,
            SnapshotSeal,
            lambda item: item.seal_id == expected["seal_id"],
            "Snapshot Seal",
        )
        export = _one(
            records,
            SnapshotExportArtifact,
            lambda item: item.snapshot_export_artifact_id
            == expected["export_artifact_id"],
            "Snapshot Export",
        )
        pointer = _one(
            records,
            SnapshotCurrentPointerRevision,
            lambda item: item.snapshot_series_id == series_id
            and item.pointer_revision == expected["current_pointer_revision"],
            "Snapshot Current Pointer",
        )
        _require(
            request.snapshot_series_id == series.snapshot_series_id
            and plan.snapshot_build_request_id == request.snapshot_build_request_id
            and attempt.snapshot_build_plan_id == plan.snapshot_build_plan_id,
            "historical Snapshot control-plane provenance is disconnected",
        )
        _require(
            attempt_result.terminal_outcome == "sealed"
            and attempt_result.sealed_snapshot_edition == edition.reference,
            "historical Snapshot Attempt Result is not the exact sealed Edition",
        )
        _require(
            seal.snapshot_edition == edition.reference
            and edition.seal_id == seal.seal_id
            and export.snapshot_edition == edition.reference,
            "historical Seal/Edition/Export identities are disconnected",
        )
        _require(
            pointer.snapshot_edition == edition.reference,
            "current Edition did not resolve from the explicit pointer",
        )
        _require(
            plan.plan_fingerprint == expected["build_plan_fingerprint"],
            "historical Snapshot Plan fingerprint changed",
        )
        edition_verification = verify_snapshot_edition(
            resolved_workspace,
            snapshot_series_id=series_id,
            edition_number=edition_number,
            verified_at=datetime(2026, 8, 16, 18, 0, tzinfo=timezone.utc),
        )
        export_verification = verify_snapshot_export(
            resolved_workspace,
            snapshot_export_artifact_id=export.snapshot_export_artifact_id,
            verified_at=datetime(2026, 8, 16, 18, 0, tzinfo=timezone.utc),
        )
        _require(
            edition_verification.manifest_digest.value == expected["manifest_sha256"]
            and edition_verification.logical_inventory_digest.value
            == expected["logical_inventory_sha256"],
            "historical Edition digest verification changed",
        )
        _require(
            export_verification.directory_inventory_digest.value
            == expected["export_inventory_sha256"],
            "historical Export digest verification changed",
        )


    pointer_probe = _expect_pointer_probe(expectations["pointer_probe"])
    pointer_series_id = cast(str, pointer_probe["snapshot_series_id"])
    pointed_edition_number = cast(int, pointer_probe["pointed_edition_number"])
    greatest_edition_number = cast(int, pointer_probe["greatest_edition_number"])
    series_view = show_snapshot_series(resolved_workspace, pointer_series_id)
    _require(
        series_view.current_edition is not None
        and series_view.current_edition.edition_number == pointed_edition_number,
        "historical current Edition does not follow the explicit pointer",
    )
    _require(
        len(series_view.editions) == 2
        and max(item.edition_number for item in series_view.editions)
        == greatest_edition_number
        and pointed_edition_number < greatest_edition_number,
        "historical pointer test does not differ from greatest-Edition inference",
    )
    successor_verification = verify_snapshot_edition(
        resolved_workspace,
        snapshot_series_id=pointer_series_id,
        edition_number=greatest_edition_number,
        verified_at=datetime(2026, 8, 16, 18, 0, tzinfo=timezone.utc),
    )
    _require(
        successor_verification.manifest_digest.value
        == pointer_probe["successor_manifest_sha256"]
        and successor_verification.logical_inventory_digest.value
        == pointer_probe["successor_logical_inventory_sha256"],
        "historical unpromoted successor Edition digest verification changed",
    )

    after_revision = load_current_state(resolved_workspace).state_revision
    _require(after_revision == before_revision, "historical reload performed a repair or write")
    return {
        "record_count": len(records),
        "record_type_count": len(actual_inventory),
        "record_inventory_sha256": digest,
        "composition_count": len(compositions),
        "snapshot_series_count": len(snapshots),
        "current_edition_resolution": "explicit_pointer_precedes_greatest",
        "producer_source_required": False,
        "state_revision_unchanged": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--expectations", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = verify(args.workspace, args.expectations)
    except (HistoricalReloadError, OSError, RuntimeError, ValueError) as error:
        print(f"historical_reload: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
