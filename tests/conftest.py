"""Shared test configuration and the fixed clock every golden is built with."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

import pyfmi_interop
import pyfmi_interfaces
from pyfmi_interop import native

#: The checkout that owns the native runtime, resolved through the editable
#: install: ``<repo>/src/pyfmi_interop/__init__.py``.
INTEROP_ROOT = Path(pyfmi_interop.__file__).resolve().parents[2]

_CMAKE = shutil.which("cmake")
_CXX = (
    shutil.which(os.environ.get("CXX", "c++"))
    or shutil.which("g++")
    or shutil.which("clang++")
)

#: The injected clock. Goldens must never depend on the wall clock.
GENERATION_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)

#: The injected clock as the CLI text form.
GENERATION_TIME_TEXT = "2026-01-01T00:00:00Z"

FIXTURE_ROOT = Path(__file__).parent / "fixtures"
GOLDEN_ROOT = Path(__file__).parent / "golden"


def fixture_path(subject: str, name: str) -> Path:
    """Path of one architecture fixture file."""
    return FIXTURE_ROOT / subject / name


@pytest.fixture(name="generation_time")
def generation_time_fixture() -> datetime:
    return GENERATION_TIME


def update_goldens() -> bool:
    """Whether a test may rewrite its golden instead of comparing."""
    if os.environ.get("CI"):
        return False
    return os.environ.get("UPDATE_GOLDENS") == "1"


def skip_reason(posix_message: str = "the end-to-end runner is POSIX-only") -> str | None:
    """Return why a native end-to-end test cannot run, or ``None``."""

    if _CMAKE is None:
        return "cmake is not available"
    if _CXX is None:
        return "a C++ compiler is not available"
    if sys.platform == "win32":
        return posix_message
    if not native.bundled_library_path().is_file() and not native.default_runtime_library_path(
        INTEROP_ROOT
    ).is_file():
        return "the native runtime has not been built"
    if not native.bundled_transport_library_path().is_file() and not any(
        path.is_file() for path in native.transport_search_paths(INTEROP_ROOT)
    ):
        return "the native transport has not been built"
    return None


def free_udp_port() -> int:
    """Bind an ephemeral UDP port, then release it for the runner."""

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def compile_runner(
    directory: Path,
    library: Path,
    source_text: str,
    *,
    stem: str = "runner",
) -> Path:
    """Compile ``source_text`` against a generated model and return the binary."""

    source = directory / f"{stem}.cpp"
    source.write_text(source_text, encoding="utf-8")
    executable = directory / stem
    headers = Path(pyfmi_interfaces.fmi2_headers()[0]).parent
    completed = subprocess.run(
        [
            _CXX or "c++",
            "-std=c++17",
            "-O0",
            str(source),
            str(library),
            "-I",
            str(headers),
            f"-Wl,-rpath,{library.parent}",
            "-pthread",
            "-o",
            str(executable),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return executable
