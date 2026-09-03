from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_quillan_adapter_validator_passes_without_nested_pytest() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_quillan_adapter.py",
            "--skip-focused-tests",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "PASS live Quillan adapter validation" in result.stdout
