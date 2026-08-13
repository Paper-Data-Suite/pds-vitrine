"""Deterministic Snapshot sealing serialization and digest primitives."""

from __future__ import annotations

import hashlib
import json
from typing import Final

from vitrine.models import DigestReference
from vitrine.models.conversion import JsonValue

SNAPSHOT_INTERNAL_MANIFEST_CONTRACT_VERSION: Final[str] = (
    "vitrine_snapshot_internal_manifest_v1"
)
SNAPSHOT_LOGICAL_INVENTORY_CONTRACT_VERSION: Final[str] = (
    "vitrine_snapshot_logical_inventory_v1"
)


def canonical_snapshot_json_bytes(value: dict[str, JsonValue]) -> bytes:
    """Serialize one Snapshot-owned object as canonical UTF-8 JSON plus LF."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def snapshot_digest(payload: bytes) -> DigestReference:
    """Return the v0.2 SHA-256 DigestReference for exact bytes."""

    if not isinstance(payload, bytes):
        raise TypeError("Snapshot digest payload must be bytes.")
    return DigestReference(value=hashlib.sha256(payload).hexdigest())


def snapshot_manifest_digest(manifest: dict[str, JsonValue]) -> DigestReference:
    """Digest the canonical internal manifest; the manifest contains no self-digest."""

    return snapshot_digest(canonical_snapshot_json_bytes(manifest))


def snapshot_logical_inventory_digest(
    inventory: dict[str, JsonValue],
) -> DigestReference:
    """Digest the canonical logical inventory independently of manifest bytes."""

    return snapshot_digest(canonical_snapshot_json_bytes(inventory))


__all__ = [
    "SNAPSHOT_INTERNAL_MANIFEST_CONTRACT_VERSION",
    "SNAPSHOT_LOGICAL_INVENTORY_CONTRACT_VERSION",
    "canonical_snapshot_json_bytes",
    "snapshot_digest",
    "snapshot_logical_inventory_digest",
    "snapshot_manifest_digest",
]
