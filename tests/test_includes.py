"""Contract: include roots reach every public source-taking entry point.

``parse``/``load_architecture`` always accepted ``includes=``; this module pins
that ``architecture``, ``to_reduction``, the four generator wrappers, and the
CLI now thread the same roots, load a path source exactly once, and refuse to
replay includes on an already loaded architecture or reduction.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest
from conftest import fixture_path
from pyssp_sysml_definitions import core_definitions

from pyfmi_sysml import (
    architecture,
    fmu_units,
    generate_c_headers,
    generate_c_runtime,
    generate_model_description,
    generate_modelica,
    to_reduction,
)
from pyfmi_sysml.cli import _includes, main

pytestmark = pytest.mark.unit

WRAPPERS = (
    pytest.param(generate_model_description, id="model-description"),
    pytest.param(generate_c_headers, id="c-headers"),
    pytest.param(generate_c_runtime, id="c-runtime"),
    pytest.param(generate_modelica, id="modelica"),
)

_LIBRARY = """package ChainLibrary {
  private import ScalarValues::*;
  private import PysspCore::*;

  port def Signal {
    attribute value : Real;
  }

  port def Params :> ParameterInterface {
    attribute gain : Real = 1.5;
  }

  part def FmuInterop :> FmuModel {
  }

  part def Leaf :> FmuInterop {
    in port parameters : Params;
    in port command : Signal;
    out port status : Signal;
  }
}
"""

_APP = """package ChainApp {
  private import ChainLibrary::*;
}
"""


def _write_chain(tmp_path: Path) -> tuple[Path, Path]:
    """An app whose exported leaf only exists in the include-root library."""
    library = tmp_path / "chain_library.sysml"
    library.write_text(_LIBRARY, encoding="utf-8")
    app = tmp_path / "chain_app.sysml"
    app.write_text(_APP, encoding="utf-8")
    return app, library


@pytest.mark.parametrize("wrapper", WRAPPERS)
def test_wrappers_forward_includes_to_the_load(tmp_path: Path, wrapper) -> None:
    """Drift caught: a wrapper drops ``includes`` before reducing the source."""
    app, library = _write_chain(tmp_path)
    out = tmp_path / "out"

    written = wrapper(app, out, includes=[library, core_definitions()])

    assert written
    assert all(Path(path).is_file() for path in written)
    assert any("Leaf" in path.as_posix() for path in out.rglob("*"))


@pytest.mark.parametrize("wrapper", WRAPPERS)
def test_wrappers_fail_when_a_required_include_is_omitted(
    tmp_path: Path, wrapper
) -> None:
    """Drift caught: an include silently invented or ignored."""
    app, _ = _write_chain(tmp_path)

    with pytest.raises(ValueError, match="composition root"):
        wrapper(app, tmp_path / "out")


def test_model_description_resolves_pysspcore_markers(tmp_path: Path) -> None:
    """The included core turns ``:> ParameterInterface`` into FMI parameters."""
    app, library = _write_chain(tmp_path)

    [description] = generate_model_description(
        app,
        tmp_path / "out",
        includes=[library, core_definitions()],
    )

    document = Path(description).read_text(encoding="utf-8")
    assert 'modelName="Leaf"' in document
    assert 'name="gain"' in document


def test_architecture_accepts_includes_and_refuses_a_reload(tmp_path: Path) -> None:
    app, library = _write_chain(tmp_path)

    loaded = architecture(app, includes=[library, core_definitions()])

    assert [definition.name for definition in fmu_units(loaded)] == ["Leaf"]
    with pytest.raises(ValueError, match="already loaded"):
        architecture(loaded, includes=[core_definitions()])


def test_to_reduction_accepts_includes_and_refuses_a_replay(tmp_path: Path) -> None:
    app, library = _write_chain(tmp_path)

    reduction = to_reduction(app, includes=[library, core_definitions()])

    assert [component.name for component in reduction.components] == ["Leaf"]
    with pytest.raises(ValueError, match="already fixes composition"):
        to_reduction(reduction, includes=[core_definitions()])


def test_a_path_source_is_loaded_once(tmp_path: Path, monkeypatch) -> None:
    """Drift caught: a wrapper resolving the same path twice."""
    import pycps_sysml

    app, library = _write_chain(tmp_path)
    calls = {"count": 0}
    real_load = pycps_sysml.load

    def counted(*args, **kwargs):
        calls["count"] += 1
        return real_load(*args, **kwargs)

    monkeypatch.setattr(pycps_sysml, "load", counted)

    generate_c_headers(
        app, tmp_path / "out", includes=[library, core_definitions()]
    )

    assert calls["count"] == 1


def test_cli_include_is_repeatable(tmp_path: Path) -> None:
    app, library = _write_chain(tmp_path)
    out = tmp_path / "build"

    assert (
        main(
            [
                "model-description",
                str(app),
                "-o",
                str(out),
                "--include",
                str(library),
                "--include",
                str(core_definitions()),
            ]
        )
        == 0
    )

    document = (out / "Leaf" / "modelDescription.xml").read_text(encoding="utf-8")
    assert 'modelName="Leaf"' in document


def test_cli_core_definitions_is_include_sugar(tmp_path: Path) -> None:
    out = tmp_path / "build"
    source = fixture_path("minimal", "minimal.sysml")

    assert (
        main(["model-description", str(source), "-o", str(out), "--core-definitions"])
        == 0
    )

    assert (out / "Scale" / "modelDescription.xml").is_file()


def test_cli_sugar_appends_after_explicit_includes(tmp_path: Path) -> None:
    """The documented precedence: repeated ``--include`` roots, then the sugar."""
    app, library = _write_chain(tmp_path)
    out = tmp_path / "build"

    assert (
        main(
            [
                "model-description",
                str(app),
                "-o",
                str(out),
                "--include",
                str(library),
                "--core-definitions",
            ]
        )
        == 0
    )

    args = argparse.Namespace(
        includes=[Path("first"), Path("second")], core_definitions=True
    )
    assert _includes(args) == [Path("first"), Path("second"), core_definitions()]


def test_cli_fails_when_a_required_include_is_omitted(
    tmp_path: Path, capsys
) -> None:
    app, _ = _write_chain(tmp_path)

    assert (
        main(["model-description", str(app), "-o", str(tmp_path / "build")]) == 1
    )
    assert capsys.readouterr().err


@pytest.mark.parametrize(
    "command", ["model-description", "c-headers", "c-runtime", "modelica"]
)
def test_every_source_command_exposes_the_include_flags(command, capsys) -> None:
    with pytest.raises(SystemExit) as raised:
        main([command, "--help"])

    assert raised.value.code == 0
    text = capsys.readouterr().out
    assert "--include" in text
    assert "--core-definitions" in text
