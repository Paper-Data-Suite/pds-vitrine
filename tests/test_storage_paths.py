from __future__ import annotations

from pathlib import Path

import pytest

from vitrine.storage import (
    VitrineStorageRecordKey,
    VitrineStorageValidationError,
    record_revision_path,
    safe_vitrine_descendant,
    state_revision_path,
    vitrine_root,
)


def test_workspace_scoped_paths_are_deterministic(tmp_path: Path) -> None:
    key = VitrineStorageRecordKey(
        "portfolio_profile_revision", ("profile_alpha", "2")
    )
    assert vitrine_root(tmp_path) == tmp_path.resolve() / "vitrine"
    assert record_revision_path(tmp_path, key, 1) == (
        tmp_path.resolve()
        / "vitrine"
        / "state"
        / "records"
        / "portfolio_profile_revision"
        / "profile_alpha"
        / "2"
        / "revisions"
        / "1.json"
    )
    assert state_revision_path(tmp_path, 3).name == "3.json"
    assert not (tmp_path / "vitrine").exists()


@pytest.mark.parametrize(
    "relative",
    ("../escape", "state/../escape", "/absolute", "C:/escape", "state//x"),
)
def test_safe_vitrine_descendant_rejects_unsafe_paths(
    tmp_path: Path, relative: str
) -> None:
    with pytest.raises(VitrineStorageValidationError):
        safe_vitrine_descendant(tmp_path, relative)
