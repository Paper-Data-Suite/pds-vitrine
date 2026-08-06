from __future__ import annotations

import importlib.metadata
import tomllib
from pathlib import Path

from vitrine import __version__
from vitrine.constants import VITRINE_MODULE_ID


def test_package_identity_and_dependency_metadata() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert project["name"] == "pds-vitrine"
    assert project["requires-python"] == ">=3.11"
    assert project["dependencies"] == ["pds-core>=0.6,<0.7"]
    assert project["scripts"] == {"vitrine": "vitrine.cli:main"}
    assert __version__ == "0.2.0.dev0"
    assert importlib.metadata.version("pds-vitrine") == __version__
    assert VITRINE_MODULE_ID == "vitrine"


def test_no_core_or_producer_entry_points_are_declared() -> None:
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "paper_data_suite.modules" not in text
    assert "paper_data_suite.publication_producers" not in text
    for dependency in ("scoreform", "quillan", "concord", "portia", "meridian"):
        assert dependency not in text.casefold()
