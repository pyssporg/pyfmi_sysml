"""Acceptance test for the executable example walkthroughs.

An example is documentation an implementer runs, so it is executed here rather
than trusted. Only the OpenModelica build stages make this slow.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.system, pytest.mark.slow]

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tests" / "iterative" / "run.sh"


@pytest.mark.skipif(
    shutil.which("omc") is None, reason="omc is not installed"
)
def test_the_iterative_example_fails_at_the_port_change() -> None:
    """The walkthrough proves the interface moves and the model stays."""
    pyfmi = Path(sys.executable).with_name("pyfmi-sysml")
    assert pyfmi.is_file(), f"the example needs the console script at {pyfmi}"

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYFMI": str(pyfmi)},
        timeout=900,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Scaler.mo" in result.stdout
    assert "raw.value not found in scope" in result.stdout
    assert "limited.clipped" in result.stdout
