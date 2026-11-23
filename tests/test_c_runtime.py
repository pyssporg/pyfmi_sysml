"""Golden, compile, link, and policy gates for the generated FMI runtime.

The runtime is only credible if it compiles, links, and behaves through the FMI
API. The golden bytes pin the generated shape; the harness compiles the same
files against two model implementations and checks the phase, type, causality,
and step semantics from the outside.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from pycps_sysml2 import load

from conftest import GOLDEN_ROOT, fixture_path, update_goldens
from golden_utils import assert_golden_text
from pyfmi_interfaces.c.headers import (
    common_header_name,
    component_header_name,
    header_stem,
)
from pyfmi_interfaces.c.runtime import (
    hooks_header_name,
    model_source_name,
    runtime_source_name,
)
from pyfmi_interfaces.core import fmi2_headers
from pyfmi_interfaces.core.identity import component_guid
from pyfmi_sysml import (
    components,
    export_identity,
    generate_c_headers,
    generate_c_runtime,
    resolve_system,
)
from pyfmi_sysml.cli import main

pytestmark = pytest.mark.component

SUBJECTS = ("controller", "minimal")
GOLDEN = GOLDEN_ROOT / "c-runtime"
HARNESS = Path(__file__).parent / "c_runtime_harness.cpp"

#: A temporary architecture with a writable Boolean and String, so the smoke
#: test can round-trip every FMI primitive without widening the fixture set.
TYPED_ARCHITECTURE = """package Typed {
  private import ScalarValues::*;
  private import PysspCore::*;

  port def TypedParameters :> ParameterInterface {
    attribute gain : Real = 1.5;
    attribute label : String = "start";
  }

  port def TypedInput {
    attribute flag : Boolean;
    attribute count : Integer;
    attribute note : String;
  }

  port def TypedOutput {
    attribute flag : Boolean;
    attribute count : Integer;
    attribute note : String;
  }

  part def TypedModel {
    in port parameters : TypedParameters;
    in port input : TypedInput;
    out port output : TypedOutput;
  }

  part def TypedRoot {
    part model : TypedModel;
  }
}
"""

_TYPE_CODES = {"Real": 0, "Integer": 1, "Boolean": 2, "String": 3}


def _source(subject: str) -> Path:
    return fixture_path(subject, f"{subject}.sysml")


def _identity(source: Path):
    architecture = load(source)
    system = resolve_system(architecture)
    direct = export_identity(architecture, system).direct
    return architecture, system, direct, components(architecture)


def _stems(source: Path):
    architecture, system, direct, exported = _identity(source)
    package = architecture.package_name
    return package, [
        header_stem(package, item.name, direct=direct) for item in exported
    ]


def _write_meta(directory: Path, component, guid: str) -> None:
    """Describe one component for the generic C++ harness."""
    types = ", ".join(
        str(_TYPE_CODES[variable.type_name]) for variable in component.variables
    )
    writable = ", ".join(
        "true" if variable.writable else "false"
        for variable in component.variables
    )
    parameter = ", ".join(
        "true" if variable.causality == "parameter" else "false"
        for variable in component.variables
    )
    directory.joinpath("vr_meta.h").write_text(
        "\n".join(
            [
                "#ifndef PYFMI_C_RUNTIME_VR_META_H",
                "#define PYFMI_C_RUNTIME_VR_META_H",
                "",
                '#include "fmi2/fmi2Functions.h"',
                "",
                f"#define VR_COUNT {component.vr_count}",
                f'#define VR_GUID "{guid}"',
                f"static const int k_vr_type[VR_COUNT] = {{{types}}};",
                f"static const bool k_vr_writable[VR_COUNT] = {{{writable}}};",
                f"static const bool k_vr_parameter[VR_COUNT] = {{{parameter}}};",
                "",
                "#endif  /* PYFMI_C_RUNTIME_VR_META_H */",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _ok_model(stem: str) -> str:
    """A model implementation whose hooks accept the runtime's calls."""
    return "\n".join(
        [
            f'#include "{hooks_header_name(stem)}"',
            "",
            f"fmi2Status {stem}_model_initialize({stem}_Instance* instance) {{",
            "  (void)instance;",
            "  return fmi2OK;",
            "}",
            "",
            f"fmi2Status {stem}_model_do_step(",
            f"    {stem}_Instance* instance, fmi2Real current_communication_point,",
            "    fmi2Real communication_step_size) {",
            "  (void)instance;",
            "  (void)current_communication_point;",
            "  (void)communication_step_size;",
            "  return fmi2OK;",
            "}",
            "",
            f"fmi2Status {stem}_model_terminate({stem}_Instance* instance) {{",
            "  (void)instance;",
            "  return fmi2OK;",
            "}",
            "",
            f"fmi2Status {stem}_model_reset({stem}_Instance* instance) {{",
            "  (void)instance;",
            "  return fmi2OK;",
            "}",
            "",
            f"fmi2Status {stem}_model_free({stem}_Instance* instance) {{",
            "  (void)instance;",
            "  return fmi2OK;",
            "}",
            "",
        ]
    )


@pytest.mark.parametrize("subject", SUBJECTS)
def test_runtime_matches_golden(subject: str, tmp_path: Path) -> None:
    written = generate_c_runtime(_source(subject), tmp_path)
    package, stems = _stems(_source(subject))
    exported = components(load(_source(subject)))

    assert written[0].name == common_header_name(package)
    [stem] = stems
    expected = [
        runtime_source_name(stem),
        hooks_header_name(stem),
        model_source_name(stem),
    ]
    assert [path.name for path in written[2:5]] == expected
    assert (tmp_path / component_header_name(
        package, exported[0].name
    )).is_file()

    for name in expected:
        assert_golden_text(
            GOLDEN / subject / name,
            (tmp_path / name).read_text(encoding="utf-8"),
        )

    if not update_goldens():
        committed = sorted(
            path.name
            for path in (GOLDEN / subject).glob("*")
            if path.name != "case.md"
        )
        assert committed == sorted(expected)


@pytest.mark.parametrize("subject", SUBJECTS)
def test_fmi2_copies_are_the_packaged_headers(
    subject: str, tmp_path: Path
) -> None:
    generate_c_runtime(_source(subject), tmp_path)

    for header in fmi2_headers():
        copy = tmp_path / "fmi2" / header.name
        assert copy.read_bytes() == header.read_bytes()


@pytest.mark.parametrize("subject", SUBJECTS)
def test_runtime_and_model_compile(subject: str, tmp_path: Path) -> None:
    gxx = shutil.which("g++")
    if gxx is None:
        pytest.skip("g++ is not installed")

    generate_c_runtime(_source(subject), tmp_path)
    _, stems = _stems(_source(subject))
    for stem in stems:
        for name in (runtime_source_name(stem), model_source_name(stem)):
            command = [
                gxx,
                "-std=c++17",
                "-fsyntax-only",
                "-I",
                str(tmp_path),
                str(tmp_path / name),
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            assert result.returncode == 0, (
                f"{' '.join(command)}\n{result.stdout}{result.stderr}"
            )


def _smoke_source(subject: str, tmp_path: Path) -> Path:
    if subject == "types":
        source = tmp_path / "typed.sysml"
        source.write_text(TYPED_ARCHITECTURE, encoding="utf-8")
        return source
    return _source(subject)


@pytest.mark.parametrize("subject", ("controller", "minimal", "types"))
def test_link_and_execute(subject: str, tmp_path: Path) -> None:
    gxx = shutil.which("g++")
    if gxx is None:
        pytest.skip("g++ is not installed")

    source = _smoke_source(subject, tmp_path)
    architecture, system, direct, exported = _identity(source)
    [component] = exported
    stem = header_stem(architecture.package_name, component.name, direct=direct)
    guid = component_guid(system.name, component.name, direct=direct)

    generated = tmp_path / "generated"
    accepted = tmp_path / "accepted"
    generate_c_runtime(source, generated)
    generate_c_runtime(source, accepted)
    (accepted / model_source_name(stem)).write_text(
        _ok_model(stem), encoding="utf-8"
    )
    _write_meta(generated, component, guid)
    _write_meta(accepted, component, guid)

    for name, defines, directory in (
        ("generated", (), generated),
        ("accepted", ("-DHARNESS_MODEL_OK",), accepted),
    ):
        executable = tmp_path / f"harness_{name}"
        command = [
            gxx,
            "-std=c++17",
            *defines,
            "-I",
            str(directory),
            str(directory / runtime_source_name(stem)),
            str(directory / model_source_name(stem)),
            str(HARNESS),
            "-o",
            str(executable),
        ]
        built = subprocess.run(command, capture_output=True, text=True)
        assert built.returncode == 0, (
            f"{' '.join(command)}\n{built.stdout}{built.stderr}"
        )
        run = subprocess.run([str(executable)], capture_output=True, text=True)
        assert run.returncode == 0, f"{name}\n{run.stdout}{run.stderr}"


def test_regeneration_preserves_the_model_and_rewrites_generated(
    tmp_path: Path,
) -> None:
    source = _source("controller")
    output = tmp_path / "output"
    clean = tmp_path / "clean"
    generate_c_runtime(source, output)
    generate_c_runtime(source, clean)

    package, [stem] = _stems(source)
    model = output / model_source_name(stem)
    generated = (
        output / runtime_source_name(stem),
        output / hooks_header_name(stem),
        output / component_header_name(package, "Controller"),
    )

    sentinel = "/* user model edit */\n"
    model.write_text(sentinel, encoding="utf-8")
    for path in generated:
        path.write_text("stale\n", encoding="utf-8")

    generate_c_runtime(source, output)

    assert model.read_text(encoding="utf-8") == sentinel
    for path in generated:
        assert path.read_bytes() == (clean / path.name).read_bytes()

    headers = generate_c_headers(source, tmp_path / "headers")
    for path in headers:
        assert (output / path.name).read_bytes() == path.read_bytes()


def test_two_runs_are_byte_identical(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate_c_runtime(_source("controller"), first)
    generate_c_runtime(_source("controller"), second)

    first_files = {
        path.relative_to(first): path.read_bytes()
        for path in first.rglob("*")
        if path.is_file()
    }
    second_files = {
        path.relative_to(second): path.read_bytes()
        for path in second.rglob("*")
        if path.is_file()
    }

    assert first_files == second_files


def test_omit_skips_definitions_and_names_them_in_the_banner(
    tmp_path: Path,
) -> None:
    generate_c_runtime(
        _source("controller"),
        tmp_path,
        omit=["fmi2SetReal,fmi2GetReal", "fmi2DoStep"],
    )
    _, [stem] = _stems(_source("controller"))
    text = (tmp_path / runtime_source_name(stem)).read_text(encoding="utf-8")

    for name in ("fmi2SetReal", "fmi2GetReal", "fmi2DoStep"):
        assert f"/* omitted via --omit: {name} */" in text
        assert f"{name}(" not in text

    assert text.count("omitted via --omit:") == 3


def test_omit_accepts_a_bare_name(tmp_path: Path) -> None:
    generate_c_runtime(_source("minimal"), tmp_path, omit="fmi2SetReal")
    _, [stem] = _stems(_source("minimal"))
    text = (tmp_path / runtime_source_name(stem)).read_text(encoding="utf-8")

    assert "/* omitted via --omit: fmi2SetReal */" in text
    assert "fmi2SetReal(" not in text


def test_unknown_omit_name_lists_the_valid_names(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as found:
        generate_c_runtime(_source("minimal"), tmp_path, omit=["fmi2Nope"])

    message = str(found.value)
    assert "unknown --omit name(s): fmi2Nope" in message
    assert "fmi2SetReal" in message
    assert "fmi2GetStringStatus" in message


@pytest.mark.system
def test_c_runtime_subcommand_prints_every_path(
    tmp_path: Path, capsys
) -> None:
    output = tmp_path / "runtime"
    source = _source("controller").resolve()

    assert main(["c-runtime", str(source), "-o", str(output)]) == 0

    expected = [
        "Controller_InterfaceCommon.h",
        "Controller_Controller.h",
        "Controller_Controller_fmi.cpp",
        "Controller_Controller_hooks.h",
        "Controller_Controller_model.cpp",
        "fmi2/fmi2FunctionTypes.h",
        "fmi2/fmi2Functions.h",
        "fmi2/fmi2TypesPlatform.h",
    ]
    assert capsys.readouterr().out.splitlines() == [
        str(output / name) for name in expected
    ]
    assert all((output / name).is_file() for name in expected)


@pytest.mark.system
def test_c_runtime_subcommand_accepts_omit_and_reports_unknown(
    tmp_path: Path, capsys
) -> None:
    output = tmp_path / "runtime"
    source = _source("minimal").resolve()

    assert (
        main(
            [
                "c-runtime",
                str(source),
                "-o",
                str(output),
                "--omit",
                "fmi2SetReal,fmi2GetReal",
                "--omit",
                "fmi2DoStep",
            ]
        )
        == 0
    )
    capsys.readouterr()
    text = (output / "Minimal_Scale_fmi.cpp").read_text(encoding="utf-8")
    assert text.count("omitted via --omit:") == 3

    assert (
        main(
            [
                "c-runtime",
                str(source),
                "-o",
                str(tmp_path / "again"),
                "--omit",
                "fmi2Nope",
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "pyfmi-sysml:" in captured.err
    assert "unknown --omit name(s): fmi2Nope" in captured.err
    assert "Traceback" not in captured.err
