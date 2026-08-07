import subprocess
import sys


def test_runtime_fixture_validator_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_runtime_models.py"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "PASS foundational runtime-model fixture validation" in result.stdout
