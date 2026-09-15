"""Producer-independent sealed Snapshot verifier for issue #71 Slice 4B."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

from vitrine.models import SnapshotEdition, SnapshotExportArtifact, SnapshotSeal
from vitrine.snapshot_distribution import (
    verify_snapshot_edition,
    verify_snapshot_export,
)
from vitrine.storage import load_current_state, load_state_records

VERIFIER_REQUEST_CONTRACT = "vitrine_issue71_sealed_verifier_request_v1"
_EXPECTED_KEYS = frozenset(
    {
        "contract_version",
        "snapshot_series_id",
        "edition_number",
        "snapshot_export_artifact_id",
        "edition_manifest_sha256",
        "edition_logical_inventory_sha256",
        "export_directory_inventory_sha256",
        "historical_state_revision",
        "current_state_revision",
    }
)


def _load_request(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or frozenset(value) != _EXPECTED_KEYS:
        raise RuntimeError("sealed verifier request shape is invalid")
    if value.get("contract_version") != VERIFIER_REQUEST_CONTRACT:
        raise RuntimeError("sealed verifier request contract is unsupported")
    for key in (
        "snapshot_series_id",
        "snapshot_export_artifact_id",
        "edition_manifest_sha256",
        "edition_logical_inventory_sha256",
        "export_directory_inventory_sha256",
    ):
        if not isinstance(value.get(key), str) or not value[key]:
            raise RuntimeError("sealed verifier request text field is invalid")
    for key in ("edition_number", "historical_state_revision", "current_state_revision"):
        item = value.get(key)
        if isinstance(item, bool) or not isinstance(item, int) or item < 1:
            raise RuntimeError("sealed verifier request integer field is invalid")
    for key in (
        "edition_manifest_sha256",
        "edition_logical_inventory_sha256",
        "export_directory_inventory_sha256",
    ):
        digest = value[key]
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise RuntimeError("sealed verifier request digest is invalid")
    return value


def _assert_producer_isolation() -> None:
    for distribution in ("scoreform", "quillan", "pds-concord"):
        try:
            metadata.version(distribution)
        except metadata.PackageNotFoundError:
            pass
        else:
            raise RuntimeError("producer distribution entered isolated verifier")
    for module in ("scoreform", "quillan", "concord"):
        if module in sys.modules or importlib.util.find_spec(module) is not None:
            raise RuntimeError("producer module entered isolated verifier")


def _historical_identity(workspace: Path, request: dict[str, Any]) -> None:
    historical_revision = int(request["historical_state_revision"])
    current_revision = int(request["current_state_revision"])
    current = load_current_state(workspace)
    if current.state_revision != current_revision or current_revision <= historical_revision:
        raise RuntimeError("sealed verifier historical/current revision relation drifted")
    records = load_state_records(workspace, historical_revision)
    editions = tuple(
        item
        for item in records
        if isinstance(item, SnapshotEdition)
        and item.snapshot_series_id == request["snapshot_series_id"]
        and item.edition_number == request["edition_number"]
    )
    exports = tuple(
        item
        for item in records
        if isinstance(item, SnapshotExportArtifact)
        and item.snapshot_export_artifact_id
        == request["snapshot_export_artifact_id"]
    )
    if len(editions) != 1 or len(exports) != 1:
        raise RuntimeError("sealed verifier historical identity is incomplete")
    seals = tuple(
        item
        for item in records
        if isinstance(item, SnapshotSeal) and item.seal_id == editions[0].seal_id
    )
    if len(seals) != 1:
        raise RuntimeError("sealed verifier historical Seal is incomplete")
    if (
        seals[0].manifest_digest.value != request["edition_manifest_sha256"]
        or seals[0].logical_inventory_digest.value
        != request["edition_logical_inventory_sha256"]
        or exports[0].directory_inventory_digest.value
        != request["export_directory_inventory_sha256"]
    ):
        raise RuntimeError("sealed verifier historical digest identity drifted")


def verify(workspace: Path, request_path: Path) -> dict[str, object]:
    workspace = workspace.resolve(strict=True)
    request = _load_request(request_path.resolve(strict=True))
    _assert_producer_isolation()
    _historical_identity(workspace, request)
    edition = verify_snapshot_edition(
        workspace,
        snapshot_series_id=str(request["snapshot_series_id"]),
        edition_number=int(request["edition_number"]),
    )
    export = verify_snapshot_export(
        workspace,
        snapshot_export_artifact_id=str(request["snapshot_export_artifact_id"]),
    )
    if (
        edition.manifest_digest.value != request["edition_manifest_sha256"]
        or edition.logical_inventory_digest.value
        != request["edition_logical_inventory_sha256"]
        or export.directory_inventory_digest.value
        != request["export_directory_inventory_sha256"]
    ):
        raise RuntimeError("isolated sealed verification digest drifted")
    return {
        "mode": "sealed_verifier",
        "producer_distributions_installed": False,
        "producer_modules_imported": False,
        "historical_reload_verified": True,
        "edition_verified": True,
        "export_verified": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = verify(args.workspace, args.request)
    except Exception as error:
        print(
            json.dumps(
                {
                    "mode": "sealed_verifier",
                    "status": "failed",
                    "error_type": type(error).__name__,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
