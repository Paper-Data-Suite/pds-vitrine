from __future__ import annotations

import importlib


def test_public_imports_are_available() -> None:
    package = importlib.import_module("vitrine")
    importlib.import_module("vitrine.cli")
    importlib.import_module("vitrine.menu")
    importlib.import_module("vitrine.workspace")
    assert package.__version__ == "0.2.0.dev0"
