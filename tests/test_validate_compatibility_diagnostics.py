from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_compatibility_diagnostics.py"


def _load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "validate_compatibility_diagnostics",
        SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_issue62_repository_validator_passes() -> None:
    module = _load_validator()
    module.validate(ROOT)
