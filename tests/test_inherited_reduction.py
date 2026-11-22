"""Inherited members reach the FMI boundary, not only the declared ones.

The reduction reads the effective member view, so a derived part definition
exposes the ports and attributes it inherits from its supertypes. The variable
order stays ancestor-first: inherited members keep their declared position and
a derived member that overrides a name keeps the inherited slot.
"""

from __future__ import annotations

from pathlib import Path

import pycps_sysml2
import pytest
from pycps_sysml2 import effective_members

from pyfmi_sysml import components

pytestmark = pytest.mark.unit

INHERITED_MODEL = """package Inherited {
  attribute def Tag;

  port def ParameterInterface;

  port def BaseParameters :> ParameterInterface {
    attribute alpha : Real = 1.0;
  }

  port def DerivedParameters :> BaseParameters, ParameterInterface {
    attribute beta : Integer = 2;
  }

  port def Signal {
    attribute value : Real;
  }

  port def RichSignal :> Signal {
    attribute extra : Integer;
  }

  part def Base {
    attribute base_tag : Tag;
    in port parameters : BaseParameters;
    in port u : Signal;
  }

  part def Derived :> Base {
    attribute own_tag : Tag;
    in port parameters : DerivedParameters;
    out port y : RichSignal;
  }

  part def Root {
    part d : Derived;
  }
}
"""


def _write_model(directory: Path, text: str) -> Path:
    path = directory / "model.sysml"
    path.write_text(text, encoding="utf-8")
    return path


def test_derived_part_exposes_inherited_and_own_members(tmp_path: Path) -> None:
    """The derived component carries the inherited port before its own port."""
    architecture = pycps_sysml2.load(_write_model(tmp_path, INHERITED_MODEL))

    [component] = components(architecture)

    assert component.name == "Derived"
    assert [(variable.name, variable.causality) for variable in component.variables] == [
        ("alpha", "parameter"),
        ("beta", "parameter"),
        ("u", "input"),
        ("y.value", "output"),
        ("y.extra", "output"),
    ]


def test_inherited_members_keep_ancestor_first_order(tmp_path: Path) -> None:
    """Attributes and ports list the supertype members first, then the own ones."""
    architecture = pycps_sysml2.load(_write_model(tmp_path, INHERITED_MODEL))

    view = effective_members(architecture, architecture.get_part_def("Derived"))

    assert list(view.attributes) == ["base_tag", "own_tag"]
    assert list(view.ports) == ["parameters", "u", "y"]


def test_derived_port_definition_expands_inherited_attributes(
    tmp_path: Path,
) -> None:
    """``RichSignal :> Signal`` emits ``value`` then ``extra`` for one port."""
    architecture = pycps_sysml2.load(_write_model(tmp_path, INHERITED_MODEL))

    [component] = components(architecture)

    [rich] = [port for port in component.ports if port.name == "y"]
    assert [field.name for field in rich.fields] == ["value", "extra"]
