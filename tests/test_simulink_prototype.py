"""The Simulink prototype is evidence only when it actually runs.

The prototype lives under ``tests/simulink`` and is deliberately not a shipped
generator family. This test runs the self-checking walkthrough, including the
drift stage, and skips when MATLAB is not installed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "simulink" / "run.sh"
MATLAB = Path(os.environ.get("MATLAB", "/opt/MATLAB/R2023b/bin/matlab"))


@pytest.mark.slow
def test_simulink_prototype_walkthrough() -> None:
    if not MATLAB.is_file():
        pytest.skip(f"MATLAB not found at {MATLAB}")

    completed = subprocess.run(
        ["bash", str(RUN)],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=ROOT,
        env={**os.environ, "PYTHON": sys.executable},
    )
    tail = (completed.stdout + completed.stderr)[-4000:]
    assert completed.returncode == 0, tail
