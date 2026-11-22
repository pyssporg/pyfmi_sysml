"""Component tests for the generated Modelica interface package."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import GOLDEN_ROOT, fixture_path
from golden_utils import assert_golden_text
from pyfmi_sysml import generate_modelica

pytestmark = pytest.mark.component

SUBJECTS = ("bus", "controller", "generator", "minimal", "sensor")

#: The exported component of each fixture; the package carries one generated
#: ``<Name>_Interface`` and one implementer-owned ``<Name>`` per component.
COMPONENTS = {
    "bus": "Bus",
    "controller": "Controller",
    "generator": "Generator",
    "minimal": "Scale",
    "sensor": "Tank",
}


def _files(subject: str) -> list[str]:
    """Every file the generator writes for one fixture, by name."""
    component = COMPONENTS[subject]
    return [
        "GeneratedInterfaces.mo",
        "Interfaces.mo",
        "package.mo",
        "package.order",
        f"{component}_Interface.mo",
        f"{component}.mo",
    ]

#: The draft this generator replaces hard-coded these names; none may survive.
FORBIDDEN = ("AircraftCommon", "Aircraft", "FlightGearBridge")

GOLDEN = GOLDEN_ROOT / "modelica"

OMC = Path("/usr/bin/omc")

#: Member lines each fixture must produce, per connector. Connectors are types,
#: so they carry no direction; direction lives on the partial model's instances.
CONNECTORS = {
    "bus": {
        "Actuation": ["Real channel_a;", "Real channel_b;", "Real channel_c;"],
        # ``in``, ``out``, and ``inout`` usages cannot agree on a direction.
        "Orientation": ["Real roll;", "Real pitch;", "Real yaw;"],
        "Position": ["Real x;", "Real y;", "Real z;"],
        "StatusPacket": ["Real speed;", "Integer health;"],
    },
    "controller": {
        "Command": ["Real manual;", "Real auto;", "Integer mode;"],
        "Status": ["Integer code;"],
        "Throttle": ["Real demand;", "Boolean enabled;"],
    },
    "generator": {"RealSignal": ["Real value;"]},
    "minimal": {"Signal": ["Real value;"]},
    "sensor": {
        "LevelState": [
            "Real remaining;",
            "Real fraction;",
            "Boolean empty;",
        ],
        "Rate": ["Real rate;"],
    },
}

#: Connector instance lines each fixture's partial model must produce. Direction
#: belongs here: one definition can serve an input and an output component.
INSTANCES = {
    "bus": [
        "input GeneratedInterfaces.Actuation actuation;",
        "input GeneratedInterfaces.Orientation orientation_in;",
        "input GeneratedInterfaces.Position position_in;",
        # An ``inout`` usage stays undirected.
        "GeneratedInterfaces.Orientation shared;",
        "output GeneratedInterfaces.Orientation orientation_out;",
        "output GeneratedInterfaces.Position position_out;",
        "output GeneratedInterfaces.StatusPacket status;",
    ],
    "controller": [
        "input GeneratedInterfaces.Command command;",
        "output GeneratedInterfaces.Throttle throttle;",
        "output GeneratedInterfaces.Status status;",
    ],
    "generator": ["output GeneratedInterfaces.RealSignal y;"],
    "minimal": [
        "input GeneratedInterfaces.Signal u;",
        "output GeneratedInterfaces.Signal y;",
    ],
    "sensor": [
        "input GeneratedInterfaces.Rate supply;",
        "output GeneratedInterfaces.LevelState level;",
    ],
}


def _connectors(path: Path) -> dict[str, list[str]]:
    """Connector name to its member lines, in file order."""
    connectors: dict[str, list[str]] = {}
    current: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if current is None and line.startswith("connector ") and "=" not in line:
            current = line.removeprefix("connector ")
            connectors[current] = []
        elif current is not None and line == f"end {current};":
            current = None
        elif current is not None and line:
            connectors[current].append(line)
    return connectors


def _texts(root: Path) -> dict[str, str]:
    """Every generated file under ``root``, keyed by relative posix path."""
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _generate(subject: str, output_dir: Path, **kwargs: object) -> list[Path]:
    return generate_modelica(
        fixture_path(subject, f"{subject}.sysml"), output_dir, **kwargs
    )


@pytest.mark.parametrize("subject", SUBJECTS)
def test_files_match_the_golden(subject: str, tmp_path: Path) -> None:
    """The committed package is the artifact under test."""
    paths = _generate(subject, tmp_path)

    assert sorted(path.name for path in paths) == sorted(_files(subject))
    assert {path.parent.name for path in paths} == {"GeneratedInterfaces"}
    produced = _texts(tmp_path)
    for name, text in produced.items():
        assert_golden_text(GOLDEN / subject / name, text)
    golden = sorted(
        name
        for name in _texts(GOLDEN / subject)
        if name.startswith("GeneratedInterfaces/")
    )
    assert sorted(produced) == golden


@pytest.mark.parametrize("subject", SUBJECTS)
def test_generation_is_deterministic(subject: str, tmp_path: Path) -> None:
    """Two runs produce identical bytes; nothing reads a clock or a hash seed."""
    first = _generate(subject, tmp_path / "one")
    second = _generate(subject, tmp_path / "two")
    assert [path.relative_to(tmp_path / "one") for path in first] == [
        path.relative_to(tmp_path / "two") for path in second
    ]
    assert _texts(tmp_path / "one") == _texts(tmp_path / "two")


@pytest.mark.parametrize("subject", SUBJECTS)
def test_no_domain_specific_name_is_emitted(subject: str, tmp_path: Path) -> None:
    """The draft's hard-coded package and model names are gone."""
    _generate(subject, tmp_path / "default")
    _generate(
        subject,
        tmp_path / "custom",
        package="Models",
        within="Enclosing",
    )
    for root in (tmp_path / "default", tmp_path / "custom"):
        for name, text in _texts(root).items():
            for forbidden in FORBIDDEN:
                assert forbidden not in text, f"{forbidden} leaked into {name}"


@pytest.mark.parametrize("subject", SUBJECTS)
def test_within_is_configurable(subject: str, tmp_path: Path) -> None:
    """``within`` reaches the root clause and nests every subpackage."""
    _generate(subject, tmp_path / "default")
    default = _texts(tmp_path / "default")
    assert default["GeneratedInterfaces/package.mo"].splitlines()[0] == "within ;"
    assert default["GeneratedInterfaces/Interfaces.mo"].splitlines()[0] == (
        "within GeneratedInterfaces;"
    )
    assert default["GeneratedInterfaces/GeneratedInterfaces.mo"].splitlines()[0] == (
        "within GeneratedInterfaces;"
    )

    _generate(subject, tmp_path / "named", within="Models.Sub")
    named = _texts(tmp_path / "named")
    assert named["GeneratedInterfaces/package.mo"].splitlines()[0] == (
        "within Models.Sub;"
    )
    assert named["GeneratedInterfaces/Interfaces.mo"].splitlines()[0] == (
        "within Models.Sub.GeneratedInterfaces;"
    )
    assert named[
        "GeneratedInterfaces/GeneratedInterfaces.mo"
    ].splitlines()[0] == "within Models.Sub.GeneratedInterfaces;"
    for name, text in named.items():
        if not name.endswith(".mo"):
            continue
        assert text.splitlines()[0] != default[name].splitlines()[0], name


@pytest.mark.parametrize("subject", SUBJECTS)
def test_package_name_is_configurable(subject: str, tmp_path: Path) -> None:
    """The root package name is an argument, not a constant."""
    paths = _generate(subject, tmp_path, package="Anything")

    assert [path.parent for path in paths] == [tmp_path / "Anything"] * len(paths)
    package = (tmp_path / "Anything" / "package.mo").read_text(encoding="utf-8")
    assert "package Anything" in package
    assert "end Anything;" in package
    for name in ("Interfaces.mo", "GeneratedInterfaces.mo"):
        text = (tmp_path / "Anything" / name).read_text(encoding="utf-8")
        assert text.splitlines()[0] == "within Anything;"


def test_the_package_order_lists_both_subpackages_and_every_component(
    tmp_path: Path,
) -> None:
    """Modelica loads classes only when the order file names them."""
    _generate("minimal", tmp_path)
    order = (tmp_path / "GeneratedInterfaces" / "package.order").read_text(
        encoding="utf-8"
    )
    assert order == (
        "Interfaces\nGeneratedInterfaces\nScale_Interface\nScale\n"
    )


def test_interfaces_aliases_all_four_primitives(tmp_path: Path) -> None:
    """Every FMI primitive has an input and an output connector alias."""
    _generate("minimal", tmp_path)
    text = (tmp_path / "GeneratedInterfaces" / "Interfaces.mo").read_text(
        encoding="utf-8"
    )
    assert text.splitlines() == [
        "within GeneratedInterfaces;",
        "package Interfaces",
        "  connector RealInput = input Real;",
        "  connector RealOutput = output Real;",
        "  connector IntegerInput = input Integer;",
        "  connector IntegerOutput = output Integer;",
        "  connector BooleanInput = input Boolean;",
        "  connector BooleanOutput = output Boolean;",
        "  connector StringInput = input String;",
        "  connector StringOutput = output String;",
        "end Interfaces;",
    ]


@pytest.mark.parametrize("subject", SUBJECTS)
def test_connectors_are_undirected_types(subject: str, tmp_path: Path) -> None:
    """A connector is reused by inputs and outputs, so it declares no direction."""
    _generate(subject, tmp_path)
    connectors = _connectors(
        tmp_path / "GeneratedInterfaces" / "GeneratedInterfaces.mo"
    )
    assert connectors == CONNECTORS[subject]


@pytest.mark.parametrize("subject", SUBJECTS)
def test_partial_model_instances_carry_the_port_direction(
    subject: str, tmp_path: Path
) -> None:
    """Direction on the instance is what an FMU export reads."""
    _generate(subject, tmp_path)
    component = COMPONENTS[subject]
    text = (
        tmp_path / "GeneratedInterfaces" / f"{component}_Interface.mo"
    ).read_text(encoding="utf-8")
    instances = [
        line.strip()
        for line in text.splitlines()
        if line.startswith("  ") and "GeneratedInterfaces." in line
    ]
    assert instances == INSTANCES[subject]


def test_a_parameter_keeps_its_authored_value_and_an_unbound_one_stays_open(
    tmp_path: Path,
) -> None:
    """The partial model carries the reduction's starts, never a guessed one."""
    architecture = tmp_path / "probe.sysml"
    architecture.write_text(
        """package Probe {
  private import ScalarValues::*;
  private import PysspCore::*;

  port def ParameterInterface;
  attribute def ParameterSet;

  port def Signal {
    attribute value : Real;
  }

  port def Parameters :> ParameterInterface {
    attribute gain : Real = 1.5;
    attribute offset : Real;
  }

  part def Device {
    in port parameters : Parameters;
    in port u : Signal;
    out port y : Signal;
  }

  part def Root {
    part device : Device;
  }
}
""",
        encoding="utf-8",
    )

    generate_modelica(architecture, tmp_path / "out")
    text = (
        tmp_path / "out" / "GeneratedInterfaces" / "Device_Interface.mo"
    ).read_text(encoding="utf-8")

    assert "  parameter Real gain = 1.5;" in text
    assert "  parameter Real offset;" in text
    assert "  input GeneratedInterfaces.Signal u;" in text


def test_the_model_scaffold_is_created_once_and_never_rewritten(
    tmp_path: Path,
) -> None:
    """The implementer's model is the seam; only the generated half is replaced."""
    _generate("minimal", tmp_path)
    root = tmp_path / "GeneratedInterfaces"
    scaffold = root / "Scale.mo"
    sentinel = "within GeneratedInterfaces;\nmodel Scale\n  // mine\nend Scale;\n"
    scaffold.write_text(sentinel, encoding="utf-8")
    (root / "Scale_Interface.mo").write_text("tampered\n", encoding="utf-8")

    written = _generate("minimal", tmp_path)

    assert scaffold.read_text(encoding="utf-8") == sentinel
    assert scaffold not in written
    assert root / "Scale_Interface.mo" in written
    assert (root / "Scale_Interface.mo").read_text(encoding="utf-8").startswith(
        "within GeneratedInterfaces;"
    )
    order = (root / "package.order").read_text(encoding="utf-8")
    assert "Scale_Interface\nScale\n" in order


def test_string_and_array_fields_reach_the_connector(tmp_path: Path) -> None:
    """A String field and a fixed-length array keep their type and shape."""
    architecture = tmp_path / "probe.sysml"
    architecture.write_text(
        """package Probe {
  port def ParameterInterface;

  port def Text {
    attribute label : String;
    attribute samples : Real[3];
  }

  part def Device {
    in port text : Text;
  }

  part def Root {
    part device : Device;
  }
}
""",
        encoding="utf-8",
    )

    generate_modelica(architecture, tmp_path / "out")
    connectors = _connectors(
        tmp_path / "out" / "GeneratedInterfaces" / "GeneratedInterfaces.mo"
    )
    assert connectors == {"Text": ["String label;", "Real samples[3];"]}


@pytest.mark.skipif(
    shutil.which("omc") is None or not OMC.is_file(),
    reason="omc is not installed",
)
@pytest.mark.slow
def test_openmodelica_accepts_the_generated_packages(tmp_path: Path) -> None:
    """The syntactic oracle: the Modelica toolchain parses and checks it.

    ``checkModel`` accepts a ``partial model`` without balance-checking it, so
    this proves the generated half is well formed, not that it is useful.
    """
    for subject in SUBJECTS:
        directory = tmp_path / subject
        _generate(subject, directory)
        package = directory / "GeneratedInterfaces" / "package.mo"
        lines = [
            f'loadFile("{package.as_posix()}");',
            "checkModel(GeneratedInterfaces.GeneratedInterfaces);",
            "checkModel(GeneratedInterfaces.Interfaces);",
            f"checkModel(GeneratedInterfaces.{COMPONENTS[subject]}_Interface);",
            "getErrorString();",
        ]

        combined = _omc(directory, lines)

        assert "Error" not in combined, combined
        assert combined.count("completed successfully") == 3, combined


def _omc(directory: Path, lines: list[str]) -> str:
    """Run one ``omc`` script inside ``directory``; return its combined output."""
    script = directory / "check.mos"
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = subprocess.run(
        [str(OMC), str(script)],
        capture_output=True,
        text=True,
        check=False,
        cwd=directory,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout + result.stderr


@pytest.mark.skipif(
    shutil.which("omc") is None or not OMC.is_file(),
    reason="omc is not installed",
)
@pytest.mark.slow
def test_openmodelica_builds_hand_written_logic_against_the_partial(
    tmp_path: Path,
) -> None:
    """The seam, proven both ways: hollow scaffold fails, filled model builds."""
    build = [
        'loadFile("GeneratedInterfaces/package.mo");',
        "buildModel(GeneratedInterfaces.Scale, startTime=0, stopTime=1);",
        "getErrorString();",
    ]

    empty = tmp_path / "empty"
    _generate("minimal", empty)
    hollow = _omc(empty, build)
    assert "Too few equations, under-determined system" in hollow, hollow

    filled = tmp_path / "filled"
    _generate("minimal", filled)
    (filled / "GeneratedInterfaces" / "Scale.mo").write_text(
        """within GeneratedInterfaces;

model Scale
  extends Scale_Interface;
equation
  y.value = gain*u.value;
end Scale;
""",
        encoding="utf-8",
    )
    built = _omc(filled, build)
    assert "Too few equations" not in built, built
    assert "Error" not in built, built
    assert (filled / "GeneratedInterfaces.Scale").is_file()
