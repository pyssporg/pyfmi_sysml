"""Contract: a ``Reduction`` is a complete, parser-free generator input.

This is the seam that lets parsing and generation be used separately: the
dialect is read once by ``to_reduction``, and every generator then produces the
same bytes from the reduction as from the architecture path, without importing
``pycps_sysml2`` again.
"""

from __future__ import annotations

import builtins
from pathlib import Path

import pytest

from conftest import GENERATION_TIME, fixture_path
from pyfmi_interfaces import (
    generate_c_headers,
    generate_c_runtime,
    generate_model_description,
    generate_modelica,
)
import pyfmi_sysml
from pyfmi_sysml import to_reduction

pytestmark = pytest.mark.contract

SOURCE = fixture_path("controller", "controller.sysml")


def _tree(root: Path) -> dict[str, bytes]:
    """Every generated file under ``root``, keyed by its relative path."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_generators_produce_the_same_bytes_from_a_reduction(tmp_path: Path) -> None:
    """Drift caught: a generator still reads the architecture, not the reduction."""
    reduction = to_reduction(SOURCE)
    runs = (
        (
            lambda root: pyfmi_sysml.generate_c_headers(SOURCE, root / "out"),
            lambda root: generate_c_headers(reduction, root / "out"),
        ),
        (
            lambda root: pyfmi_sysml.generate_c_runtime(SOURCE, root / "out"),
            lambda root: generate_c_runtime(reduction, root / "out"),
        ),
        (
            lambda root: pyfmi_sysml.generate_model_description(
                SOURCE, root / "out", generation_time=GENERATION_TIME
            ),
            lambda root: generate_model_description(
                reduction,
                root / "out",
                generation_time=GENERATION_TIME,
            ),
        ),
        (
            lambda root: pyfmi_sysml.generate_modelica(SOURCE, root / "out"),
            lambda root: generate_modelica(reduction, root / "out"),
        ),
    )

    for from_path, from_reduction in runs:
        expected = tmp_path / "path"
        actual = tmp_path / "reduction"
        from_path(expected)
        from_reduction(actual)
        assert _tree(actual) == _tree(expected)


def test_generators_do_not_import_the_dialect_for_a_reduction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drift caught: a parser import added to a generator's reduction path."""
    reduction = to_reduction(SOURCE)
    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name.split(".")[0] == "pycps_sysml2":
            raise AssertionError(f"generator imported the dialect: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)

    generate_c_headers(reduction, tmp_path / "c")
    generate_c_runtime(reduction, tmp_path / "c")
    generate_model_description(
        reduction, tmp_path / "md", generation_time=GENERATION_TIME
    )
    generate_modelica(reduction, tmp_path / "mo")


def test_a_reduction_refuses_to_be_re_resolved() -> None:
    """Drift caught: overriding arguments of an already resolved export unit."""
    reduction = to_reduction(SOURCE)

    with pytest.raises(ValueError, match="already fixes composition"):
        to_reduction(reduction, composition="ControllerComposition")
    with pytest.raises(ValueError, match="already fixes composition"):
        to_reduction(reduction, base_index=1)


ATTR_MODEL = """package Reduced {
  private import ScalarValues::*;
  private import PysspCore::*;

  port def ParameterInterface;
  attribute def ParameterSet;
  attribute def Tag;

  port def Parameters :> ParameterInterface {
    attribute gain : Real = 2.5;
    attribute label : String = "nominal";
  }

  port def Command {
    attribute manual : Real = 1.25;
    attribute mode : Integer = 2;
    attribute enabled : Boolean = true;
  }

  part def Controller {
    attribute tags : Tag[2] = ("a", "b");
    attribute tag : Tag;
    in port parameters : Parameters;
    in port command : Command;
  }

  part def Root {
    part controller : Controller;
  }
}
"""


def test_reduction_keeps_typed_starts(tmp_path: Path) -> None:
    """Drift caught: a generator must format ``start``, losing the typed value."""
    source = tmp_path / "reduced.sysml"
    source.write_text(ATTR_MODEL, encoding="utf-8")

    reduction = to_reduction(source)

    [component] = reduction.components
    starts = {
        variable.name: (variable.start, variable.start_text)
        for variable in component.variables
    }
    assert starts["gain"] == (2.5, "2.5")
    assert starts["label"] == ("nominal", "nominal")
    assert starts["command.manual"] == (0.0, "0")
    assert starts["command.mode"] == (0, "0")
    assert starts["command.enabled"] == (False, "false")


def test_reduction_keeps_authored_attributes(tmp_path: Path) -> None:
    """Drift caught: a consumer re-resolves the architecture for attributes."""
    source = tmp_path / "reduced.sysml"
    source.write_text(ATTR_MODEL, encoding="utf-8")

    reduction = to_reduction(source)

    [component] = reduction.components
    assert component.attributes == (("tags", ("a", "b")), ("tag", None))
    [command] = component.ports
    assert command.attributes == (
        ("manual", 1.25),
        ("mode", 2),
        ("enabled", True),
    )


def test_reduction_names_the_composition_root_and_package(tmp_path: Path) -> None:
    """Drift caught: the consumer re-selects the system to name the artifact."""
    source = tmp_path / "reduced.sysml"
    source.write_text(ATTR_MODEL, encoding="utf-8")

    reduction = to_reduction(source)

    assert reduction.root == "Root"
    assert reduction.package == "Reduced"
    assert reduction.identity.system == "Root"


ROOT_ATTR_MODEL = """package RootAttrs {
  private import ScalarValues::*;
  private import PysspCore::*;

  attribute def Timing;

  port def Command {
    attribute manual : Real = 1.25;
  }

  part def Controller {
    in port command : Command;
  }

  part def Root {
    attribute rate_hz : Timing = 50.0;
    attribute period_s : Timing = 0.02;
    part controller : Controller;
  }
}
"""


def test_reduction_keeps_composition_root_attributes(tmp_path: Path) -> None:
    """Drift caught: the consumer reads root attributes from the architecture."""
    source = tmp_path / "root.sysml"
    source.write_text(ROOT_ATTR_MODEL, encoding="utf-8")

    reduction = to_reduction(source)

    assert reduction.root == "Root"
    assert reduction.attributes == (("rate_hz", 50.0), ("period_s", 0.02))

