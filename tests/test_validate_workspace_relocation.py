from __future__ import annotations

from pathlib import Path

from scripts.validate_workspace_relocation import validate_workspace_relocation


def test_opaque_workspace_copy_preserves_vitrine_state_and_recovery(
    tmp_path: Path,
) -> None:
    validate_workspace_relocation(tmp_path)
