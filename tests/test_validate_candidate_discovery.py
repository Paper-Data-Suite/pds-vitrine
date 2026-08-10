from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_candidate_discovery_validator_passes() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/validate_candidate_discovery.py"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "PASS Candidate discovery validation" in result.stdout
