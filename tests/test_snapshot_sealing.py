from __future__ import annotations

from vitrine.models import DigestReference
from vitrine.models.conversion import JsonValue
from vitrine.snapshot_sealing import (
    canonical_snapshot_json_bytes,
    snapshot_digest,
    snapshot_logical_inventory_digest,
    snapshot_manifest_digest,
)


def test_snapshot_sealing_json_and_digest_layers_are_deterministic_and_distinct() -> None:
    manifest: dict[str, JsonValue] = {
        "contract_version": "vitrine_snapshot_internal_manifest_v1",
        "snapshot_edition": {"snapshot_series_id": "series_alpha", "edition_number": 1},
        "entries": [
            {
                "entry_plan_id": "entry_alpha",
                "relative_path": "work/sample.txt",
                "output_digest": {"algorithm": "sha256", "value": "1" * 64},
            }
        ],
    }
    reordered: dict[str, JsonValue] = {
        "entries": manifest["entries"],
        "snapshot_edition": manifest["snapshot_edition"],
        "contract_version": manifest["contract_version"],
    }
    inventory: dict[str, JsonValue] = {
        "contract_version": "vitrine_snapshot_logical_inventory_v1",
        "entries": manifest["entries"],
    }

    first = canonical_snapshot_json_bytes(manifest)
    second = canonical_snapshot_json_bytes(reordered)
    assert first == second
    assert first.endswith(b"\n")
    assert snapshot_manifest_digest(manifest) == snapshot_digest(first)
    assert snapshot_logical_inventory_digest(inventory) != snapshot_manifest_digest(
        manifest
    )
    assert isinstance(snapshot_digest(b"exact bytes"), DigestReference)
