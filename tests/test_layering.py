"""Layering: only ``pyfmi_sysml`` may import the SysML parser.

``pyfmi_interfaces`` is parser-free: it consumes a ``Reduction`` and nothing
else. This test locates the installed ``pyfmi_interfaces`` source and asserts
that no module in it imports ``pycps_sysml2``, while this package does import
it (the reduction bridge).
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.static

PARSER = "pycps_sysml2"

PACKAGE_SRC = Path(__file__).resolve().parents[1] / "src" / "pyfmi_sysml"


def _interfaces_src() -> Path:
    spec = importlib.util.find_spec("pyfmi_interfaces")
    assert spec is not None and spec.origin is not None, "pyfmi_interfaces missing"
    return Path(spec.origin).resolve().parent


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def _parser_importers(root: Path) -> list[str]:
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if any(name.split(".")[0] == PARSER for name in _imports(path)):
            offenders.append(path.as_posix())
    return offenders


def test_interfaces_source_imports_no_sysml_parser():
    """Drift caught: an emitter reaching back for the dialect."""
    offenders = _parser_importers(_interfaces_src())
    assert not offenders, (
        f"{PARSER} must be imported only by pyfmi_sysml: {offenders}"
    )


def test_pyfmi_sysml_is_the_parser_importer():
    """The reduction bridge is the one module that reads the dialect."""
    importers = _parser_importers(PACKAGE_SRC)
    assert importers, f"pyfmi_sysml must import {PARSER} through its reduction"
    assert any(path.endswith("reduction.py") for path in importers), importers
