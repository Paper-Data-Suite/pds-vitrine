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
    assert project["dependencies"] == ["pds-core>=0.6.3,<0.7"]
    assert project["scripts"] == {"vitrine": "vitrine.cli:main"}
    assert __version__ == "0.2.0"
    assert importlib.metadata.version("pds-vitrine") == __version__
    assert VITRINE_MODULE_ID == "vitrine"


def test_only_core_module_operations_entry_point_is_declared() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]

    assert project["entry-points"] == {
        "paper_data_suite.module_operations": {
            "vitrine": "vitrine.pds_operations:get_module_operations_profile"
        }
    }
    assert project["scripts"] == {"vitrine": "vitrine.cli:main"}

    dependency_sets = (
        tuple(project["dependencies"]),
        *(
            tuple(requirements)
            for requirements in project.get("optional-dependencies", {}).values()
        ),
    )
    forbidden = ("scoreform", "quillan", "concord", "portia", "meridian")
    for dependencies in dependency_sets:
        for requirement in dependencies:
            normalized = requirement.casefold().replace("_", "-")
            assert not any(name in normalized for name in forbidden)
