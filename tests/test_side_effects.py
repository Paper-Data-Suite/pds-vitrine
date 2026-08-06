from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_imports_and_static_commands_create_no_files(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["PDS_WORKSPACE_ROOT"] = str(tmp_path / "workspace")
    commands = (
        [sys.executable, "-c", "import vitrine, vitrine.cli, vitrine.menu"],
        [sys.executable, "-m", "vitrine", "--help"],
        [sys.executable, "-m", "vitrine", "--version"],
    )
    for command in commands:
        subprocess.run(
            command,
            cwd=tmp_path,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
    assert list(tmp_path.iterdir()) == []
