"""Contract: a load supplies a vocabulary root only when the model imports it.

The composition policy makes ``PysspCore`` and ``PyfmiInterop`` include roots,
not definitions every model inherits.  The public source-taking entry points
add each root when the architecture imports it, so a model that imports a
vocabulary never passes its root by hand, and a model that imports neither
keeps the export unit it selected before.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyfmi_sysml import fmu_units, load_architecture, parse, to_reduction

pytestmark = pytest.mark.sysml

_CORE_ONLY = """package CoreOnly {
  private import PysspCore::*;

  port def Signal {
    attribute value : Real;
  }

  part def Leaf :> FmuModel {
    out port y : Signal;
  }
}
"""

_INTEROP_ONLY = """package InteropOnly {
  private import PyfmiInterop::*;

  port def Signal {
    attribute value : Real;
  }

  part def Leaf :> FmuInterop {
    out port y : Signal;
  }
}
"""

_BOTH = """package Both {
  private import PysspCore::*;
  private import PyfmiInterop::*;

  port def Signal {
    attribute value : Real;
  }

  part def Leaf :> FmuInterop {
    out port y : Signal;
  }
}
"""

_NEITHER = """package Plain {
  port def Signal {
    attribute value : Real;
  }

  part def Leaf {
    out port y : Signal;
  }

  part def System {
    part leaf : Leaf;
  }
}
"""


def _write(tmp_path: Path, text: str) -> Path:
    source = tmp_path / "model.sysml"
    source.write_text(text, encoding="utf-8")
    return source


@pytest.mark.unit
def test_pysspcore_root_is_supplied_when_imported(tmp_path: Path) -> None:
    """``:> FmuModel`` resolves with no root passed by the caller."""
    source = _write(tmp_path, _CORE_ONLY)

    parsed = parse(source)
    architecture = load_architecture(source)

    assert parsed.unit == "Leaf"
    assert [definition.name for definition in fmu_units(architecture)] == ["Leaf"]


@pytest.mark.unit
def test_pyfmiinterop_root_is_supplied_when_imported(tmp_path: Path) -> None:
    source = _write(tmp_path, _INTEROP_ONLY)

    architecture = load_architecture(source)

    assert "PyfmiInterop::FmuInterop" in architecture.part_definitions
    assert [definition.name for definition in fmu_units(architecture)] == ["Leaf"]


@pytest.mark.unit
def test_both_roots_are_supplied_when_both_are_imported(tmp_path: Path) -> None:
    source = _write(tmp_path, _BOTH)

    parsed = parse(source)
    architecture = load_architecture(source)

    assert parsed.unit == "Leaf"
    assert "PysspCore::FmuModel" in architecture.part_definitions
    assert "PyfmiInterop::FmuInterop" in architecture.part_definitions


@pytest.mark.unit
def test_an_import_free_model_keeps_the_export_unit(tmp_path: Path) -> None:
    """Neither root joins, so the selected unit is the direct parse's."""
    pycps = pytest.importorskip("pycps_sysml")
    source = _write(tmp_path, _NEITHER)

    before = to_reduction(pycps.load(source))
    architecture = load_architecture(source)
    after = to_reduction(source)

    assert architecture.imports == {}
    assert "PysspCore::FmuModel" not in architecture.part_definitions
    assert "PyfmiInterop::FmuInterop" not in architecture.part_definitions
    assert [component.name for component in after.components] == [
        component.name for component in before.components
    ]
    assert after.identity == before.identity
    assert after.root == before.root
