from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_producer_adapter_validator_passes() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/validate_producer_adapters.py"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "PASS producer adapter validation" in result.stdout
