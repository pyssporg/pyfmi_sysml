"""The opt-in ``psysml2`` FMI layer: two namespaces, one wire plane.

These tests assert against the emitted tree and the packed ``.fmu``, not an
intermediate string: the FMI interface belongs to ``pyfmi_interfaces`` while the
wire field numbers, ``wire.json``, the schema and the packaging stay here.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

import pytest
from pyssp_sysml_definitions import core_definitions

from pyfmi_interop import Direction, package_fmu
from pyfmi_interop.core import BuildConfig
from pyfmi_interop.packaging import platform_binary_dir
from pyfmi_interop.core import (
    load_adapter_model,
    wire_model_from_adapter_json,
)

pytestmark = [pytest.mark.cpp, pytest.mark.system, pytest.mark.sysml]

_EXAMPLE = (
    Path(__file__).resolve().parents[2] / "examples" / "sysml" / "adapter" / "actuator_link.sysml"
)

_CHAIN_LIBRARY = """\
package ChainLibrary {
  private import ScalarValues::*;
  private import PysspCore::*;

  port def Signal {
    attribute value : Real;
  }

  part def FmuInterop :> FmuModel {
  }

  part def Leaf :> FmuInterop {
    in port command : Signal;
    out port status : Signal;
  }
}
"""

_CHAIN_APP = """\
package ChainApp {
  private import ChainLibrary::*;
}
"""


def _write_chain(tmp_path: Path) -> tuple[Path, Path]:
    library = tmp_path / "chain_library.sysml"
    app = tmp_path / "chain_app.sysml"
    library.write_text(_CHAIN_LIBRARY, encoding="utf-8")
    app.write_text(_CHAIN_APP, encoding="utf-8")
    return app, library


@pytest.fixture(scope="module")
def example():
    pytest.importorskip("pycps_sysml")
    pytest.importorskip("pyfmi_interfaces")
    import pyfmi_sysml as sysml

    return sysml.parse(_EXAMPLE, name="ActuatorLinkAdapter")


def _generate(parsed, out: Path, *, serialization: str = "packed"):
    from pyfmi_sysml import generate_adapter

    return generate_adapter(
        parsed,
        out,
        BuildConfig(serialization=serialization),
    )


def test_example_uses_the_shared_interop_library(example, tmp_path):
    text = _EXAMPLE.read_text(encoding="utf-8")

    assert "private import PyfmiInterop::*;" in text
    assert "part def ActuatorLink :> FmuInterop {" in text
    assert "port def InteropDeployment" not in text
    assert "part def FmuModel" not in text
    assert "BenchDefaults" not in text
    assert "part def Root" not in text

    target = _generate(example, tmp_path)
    payload = load_adapter_model(target)
    assert payload["model_name"] == "ActuatorLink"


def test_inline_model_importing_the_library_generates(tmp_path):
    pytest.importorskip("pycps_sysml")
    pytest.importorskip("pyfmi_interfaces")
    import pyfmi_sysml as sysml

    source = tmp_path / "inline.sysml"
    source.write_text(
        "package InlineInterop {\n"
        "  private import ScalarValues::*;\n"
        "  private import PyfmiInterop::*;\n"
        "\n"
        "  port def Command {\n"
        "    attribute demand : Real;\n"
        "  }\n"
        "\n"
        "  port def Status {\n"
        "    attribute actual : Real;\n"
        "  }\n"
        "\n"
        "  part def Widget :> FmuInterop {\n"
        "    in port command : Command;\n"
        "    out port status : Status;\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    parsed = sysml.parse(source, name="WidgetAdapter", realtime=False)
    target = _generate(parsed, tmp_path / "inline")
    model = parsed.spec
    wire = json.loads((target / "wire.json").read_text(encoding="utf-8"))
    description = (target / "Widget" / "modelDescription.xml").read_text(
        encoding="utf-8"
    )

    assert model.interface == "Widget"
    assert {item["name"] for item in wire["parameters"]} == {
        "transport",
        "bind_address",
        "peer_address",
    }
    assert {item["name"] for item in wire["signals"]} == {
        "command.demand",
        "status.actual",
    }
    assert 'modelName="Widget"' in description


def test_generate_adapter_requires_a_parsed_model(example, tmp_path):
    from pyfmi_sysml import generate_adapter

    with pytest.raises(TypeError, match="ParsedModel"):
        generate_adapter(example.spec, tmp_path)
    with pytest.raises(TypeError, match="ParsedModel"):
        generate_adapter(str(_EXAMPLE), tmp_path)


@pytest.mark.component
def test_library_defined_fmu_loads_and_generates_from_includes(tmp_path):
    pytest.importorskip("pycps_sysml")
    pytest.importorskip("pyfmi_interfaces")
    import pyfmi_sysml as sysml

    app, library = _write_chain(tmp_path)
    parsed = sysml.parse(
        app, includes=[library, core_definitions()], realtime=False
    )
    model = parsed.spec

    assert model.interface == "Leaf"
    assert {item.name: item.direction for item in model.signals} == {
        "command": Direction.INPUT,
        "status": Direction.OUTPUT,
    }

    target = _generate(parsed, tmp_path / "generated")
    document = (target / "Leaf" / "modelDescription.xml").read_text(encoding="utf-8")
    payload = load_adapter_model(target)

    assert 'modelName="Leaf"' in document
    assert payload["model_name"] == "Leaf"
    assert {item["name"] for item in payload["signals"] if item["field"] is not None} == {
        "command",
        "status",
    }


@pytest.mark.component
def test_model_without_includes_is_unchanged(example, tmp_path):
    import pyfmi_sysml as sysml

    plain = _generate(example, tmp_path / "plain")
    parsed_empty = sysml.parse(
        _EXAMPLE, name="ActuatorLinkAdapter", includes=()
    )
    empty = _generate(parsed_empty, tmp_path / "empty")

    plain_files = sorted(
        path.relative_to(plain) for path in plain.rglob("*") if path.is_file()
    )
    empty_files = sorted(
        path.relative_to(empty) for path in empty.rglob("*") if path.is_file()
    )
    assert plain_files == empty_files
    for name in plain_files:
        assert (plain / name).read_bytes() == (empty / name).read_bytes(), str(name)
    document = (plain / "ActuatorLink" / "modelDescription.xml").read_text(
        encoding="utf-8"
    )
    assert 'modelName="ActuatorLink"' in document


def test_tree_carries_both_namespaces_per_signal(example, tmp_path):
    target = _generate(example, tmp_path)
    wire = json.loads((target / "wire.json").read_text(encoding="utf-8"))
    model = load_adapter_model(target)

    assert wire["fmi_layer"] == "psysml2"
    assert {item["name"] for item in wire["parameters"]} == {
        "transport",
        "bind_address",
        "peer_address",
    }
    wire_signals = wire["signals"]
    assert [item["field"] for item in wire_signals] == list(
        range(1, len(wire_signals) + 1)
    )
    # Canonical signal-name order is the wire field order.
    assert [item["name"] for item in wire_signals] == sorted(
        item["name"] for item in wire_signals
    )
    # FMI value references are the 0-based pyfmi_interfaces ones and are not
    # renumbered to the field numbers.
    assert all(isinstance(item["value_reference"], int) for item in wire_signals)
    assert wire_signals[0]["value_reference"] != wire_signals[0]["field"]

    parameters = {item["name"]: item for item in model["signals"] if item["field"] is None}
    assert parameters["transport"]["value_reference"] == 0
    assert "field" in model["signals"][0]


def test_generated_hooks_cover_the_five_seams(example, tmp_path):
    target = _generate(example, tmp_path)
    hooks = next(target.glob("*_model.cpp")).read_text(encoding="utf-8")

    for name in (
        "model_initialize",
        "model_do_step",
        "model_terminate",
        "model_reset",
        "model_free",
    ):
        assert name in hooks
    assert "user_data" in hooks
    assert "user_step" not in hooks
    assert "make_transport" in hooks
    assert "wire::encode_frame" in hooks
    assert "wire::decode_frame" in hooks


def test_parameter_addition_moves_vrs_not_fields_or_model_id(tmp_path):
    pytest.importorskip("pyfmi_interfaces")
    import pyfmi_sysml as sysml

    original = _EXAMPLE.read_text(encoding="utf-8")
    # A derived deployment interface adds a parameter while keeping the shared
    # InteropDeployment fields; the part points its parameters port at it.
    extended = original.replace(
        "  port def Command {",
        "  port def ExtendedDeployment :> InteropDeployment {\n"
        '    attribute protocol : String = "v1";\n'
        "  }\n\n"
        "  port def Command {",
    ).replace(
        "  part def ActuatorLink :> FmuInterop {",
        "  part def ActuatorLink :> FmuInterop {\n"
        "    in port parameters : ExtendedDeployment;",
    )
    assert extended != original

    source_a = tmp_path / "a.sysml"
    source_b = tmp_path / "b.sysml"
    source_a.write_text(original, encoding="utf-8")
    source_b.write_text(extended, encoding="utf-8")
    model_a = sysml.parse(source_a, name="ActuatorLinkAdapter")
    model_b = sysml.parse(source_b, name="ActuatorLinkAdapter")

    out_a = _generate(model_a, tmp_path / "a")
    out_b = _generate(model_b, tmp_path / "b")
    wire_a = json.loads((out_a / "wire.json").read_text(encoding="utf-8"))
    wire_b = json.loads((out_b / "wire.json").read_text(encoding="utf-8"))

    assert wire_a["model_id"] == wire_b["model_id"]
    assert [item["field"] for item in wire_a["signals"]] == [
        item["field"] for item in wire_b["signals"]
    ]
    assert [item["value_reference"] for item in wire_a["signals"]] != [
        item["value_reference"] for item in wire_b["signals"]
    ]
    assert any(
        item["name"].endswith("protocol") for item in wire_b["parameters"]
    )


def test_protobuf_schema_uses_wire_field_numbers(example, tmp_path):
    pytest.importorskip("grpc_tools", reason="protoc is not installed")
    target = _generate(example, tmp_path, serialization="protobuf")
    wire = json.loads((target / "wire.json").read_text(encoding="utf-8"))
    proto = next(target.glob("*.proto")).read_text(encoding="utf-8")
    fields = {
        int(match.group(2)): match.group(1)
        for match in re.finditer(r"^  Value (\w+) = (\d+);$", proto, re.MULTILINE)
    }
    assert set(fields) == {item["field"] for item in wire["signals"]}


def test_generation_is_byte_deterministic(example, tmp_path):
    first = _generate(example, tmp_path / "first")
    second = _generate(example, tmp_path / "second")

    names = sorted(
        path.relative_to(first)
        for path in first.rglob("*")
        if path.is_file()
    )
    assert names
    for name in names:
        assert (first / name).read_bytes() == (second / name).read_bytes(), str(name)


def test_packaged_archive_uses_the_sysml2_model_description(example, tmp_path):
    target = _generate(example, tmp_path)
    library = tmp_path / "libActuatorLink.so"
    library.write_bytes(b"\x7fELF fake adapter")
    payload = load_adapter_model(target)
    model = wire_model_from_adapter_json(payload)
    platform = platform_binary_dir()
    description = (target / "ActuatorLink" / "modelDescription.xml").read_bytes()
    entries = {
        f"binaries/{platform}/wire.json": (target / "wire.json").read_bytes()
    }

    def package(path: Path) -> Path:
        return package_fmu(
            target,
            library,
            path,
            model=model,
            model_description=description,
            model_json=(target / "model.json").read_bytes(),
            model_name=payload["model_name"],
            extra_entries=entries,
            include_schema=False,
        )

    first = package(tmp_path / "first.fmu")
    second = package(tmp_path / "second.fmu")
    assert first.read_bytes() == second.read_bytes()

    with ZipFile(first) as archive:
        names = set(archive.namelist())
        assert "modelDescription.xml" in names
        assert f"binaries/{platform}/wire.json" in names
        assert f"binaries/{platform}/ActuatorLink{_extension()}" in names
        document = archive.read("modelDescription.xml").decode("utf-8")
        descriptor = json.loads(
            archive.read(f"binaries/{platform}/wire.json").decode("utf-8")
        )
    assert 'modelName="ActuatorLink"' in document
    assert 'modelName="Root.ActuatorLink"' not in document
    assert 'modelIdentifier="ActuatorLink"' in document
    guid = re.search(r'guid="([^"]+)"', document).group(1)
    assert guid == _direct_guid("ActuatorLink")
    assert {"value_reference", "field"} <= set(descriptor["signals"][0])


def _generate_variant(tmp_path, name: str, text: str):
    pytest.importorskip("pycps_sysml")
    pytest.importorskip("pyfmi_interfaces")
    import pyfmi_sysml as sysml

    source = tmp_path / f"{name}.sysml"
    source.write_text(text, encoding="utf-8")
    parsed = sysml.parse(source, name="ActuatorLinkAdapter", realtime=False)
    target = _generate(parsed, tmp_path / name)
    return target, json.loads((target / "wire.json").read_text(encoding="utf-8"))


def test_adapter_model_id_ignores_step_size_and_declared_rates(tmp_path):
    original = _EXAMPLE.read_text(encoding="utf-8")
    _, base = _generate_variant(tmp_path, "base", original)

    stepped_text = original.replace(
        "  port def Command {",
        "  attribute def BuildTiming;\n\n"
        "  port def Command {",
    ).replace(
        "  part def ActuatorLink :> FmuInterop {",
        "  part def ActuatorLink :> FmuInterop {\n"
        "    attribute step_size_s : BuildTiming = 0.002;",
    )
    rated_text = original.replace(
        "  port def Command {",
        "  attribute def PortTiming :> ParameterSet;\n\n"
        "  port def Command {\n"
        "    attribute rate : PortTiming = 250.0;",
    )
    assert stepped_text != original and rated_text != original

    _, stepped = _generate_variant(tmp_path, "stepped", stepped_text)
    _, rated = _generate_variant(tmp_path, "rated", rated_text)

    assert stepped["step_size_s"] == 0.002
    assert rated["signals"] != base["signals"]
    assert base["model_id"] == stepped["model_id"] == rated["model_id"]


def test_adapter_document_has_no_default_experiment(tmp_path):
    original = _EXAMPLE.read_text(encoding="utf-8")
    text = original.replace(
        "  part def ActuatorLink :> FmuInterop {",
        "  attribute def AdapterDefaults :> DefaultExperiment {\n"
        "    attribute startTime = 0.0;\n"
        "    attribute stopTime = 1.0;\n"
        "  }\n\n"
        "  part def ActuatorLink :> FmuInterop {\n"
        "    attribute defaults : AdapterDefaults;",
    )
    assert text != original

    target, _ = _generate_variant(tmp_path, "experiment", text)
    document = (target / "ActuatorLink" / "modelDescription.xml").read_text(
        encoding="utf-8"
    )
    assert "DefaultExperiment" not in document


def test_adapter_rejects_a_rate_that_is_not_a_multiple_of_the_slowest(tmp_path):
    original = _EXAMPLE.read_text(encoding="utf-8")
    text = original.replace(
        "  port def Command {",
        "  attribute def PortTiming :> ParameterSet;\n\n"
        "  port def Command {\n"
        "    attribute rate : PortTiming = 250.0;",
    ).replace(
        "  port def Feedback {",
        "  port def Feedback {\n"
        "    attribute rate : PortTiming = 100.0;",
    )
    assert text != original

    with pytest.raises(ValueError, match="integer multiple"):
        _generate_variant(tmp_path, "misaligned", text)


def test_adapter_generates_without_a_step_size(tmp_path):
    pytest.importorskip("pycps_sysml")
    pytest.importorskip("pyfmi_interfaces")
    import pyfmi_sysml as sysml

    parsed = sysml.parse(
        _EXAMPLE, name="ActuatorLinkAdapter", realtime=False
    )
    target = _generate(parsed, tmp_path / "no-step")
    hooks = next(target.glob("*_model.cpp")).read_text(encoding="utf-8")

    assert "kStepSize" not in hooks
    assert (target / "wire.json").is_file()


def _direct_guid(component: str) -> str:
    from pyfmi_interfaces.core.identity import component_guid

    return component_guid("ActuatorLinkExample", component, direct=True)


def _extension() -> str:
    from pyfmi_interop.packaging import platform_library_extension

    return platform_library_extension()


_SYSTEM_EXAMPLE = (
    Path(__file__).resolve().parents[2] / "examples" / "sysml" / "system" / "bench.sysml"
)

_SYSTEM_UNITS = ["ActuatorLink", "Controller", "SensorLink"]


def _system_architecture():
    pytest.importorskip("pycps_sysml")
    pytest.importorskip("pyfmi_interfaces")
    from pyfmi_sysml import load_architecture

    return load_architecture(_SYSTEM_EXAMPLE)


def _generate_unit(architecture, unit: str, out: Path, *, serialization="packed"):
    from pyfmi_sysml import ParsedModel, model_from_architecture, to_reduction

    model = model_from_architecture(
        architecture,
        composition=unit,
        name=unit,
        realtime=False,
    )
    parsed = ParsedModel(
        spec=model,
        reduction=to_reduction(architecture, composition=unit),
        unit=unit,
    )
    target = _generate(parsed, out, serialization=serialization)
    return model, target


def test_fmu_units_lists_the_three_system_units_sorted():
    architecture = _system_architecture()
    from pyfmi_sysml import fmu_units

    assert [definition.name for definition in fmu_units(architecture)] == _SYSTEM_UNITS


def test_load_model_composition_selects_only_that_units_signals():
    pytest.importorskip("pycps_sysml")
    pytest.importorskip("pyfmi_interfaces")
    import pyfmi_sysml as sysml

    model = sysml.load_model(
        _SYSTEM_EXAMPLE,
        composition="Controller",
        name="Controller",
        realtime=False,
    )

    assert model.interface == "Controller"
    assert {
        signal.name
        for signal in model.signals
        if signal.direction is not Direction.PARAMETER
    } == {
        "input.measured",
        "input.reference",
        "input.mode",
        "input.enabled",
        "input.weights[0]",
        "input.weights[1]",
        "input.weights[2]",
        "output.command",
        "output.effort",
        "output.phase",
        "output.active",
        "output.limits[0]",
        "output.limits[1]",
    }


def test_generate_one_unit_names_the_model_after_the_unit(tmp_path):
    architecture = _system_architecture()
    model, target = _generate_unit(architecture, "SensorLink", tmp_path / "one")

    document = (target / "SensorLink" / "modelDescription.xml").read_text(
        encoding="utf-8"
    )
    payload = load_adapter_model(target)

    assert model.name == "SensorLink"
    assert model.interface == "SensorLink"
    assert 'modelName="SensorLink"' in document
    assert payload["model_name"] == "SensorLink"
    assert {
        item["name"] for item in payload["signals"] if item["field"] is not None
    } == {
        "request.sample_rate",
        "request.channel",
        "request.trigger",
        "request.offsets[0]",
        "request.offsets[1]",
        "reading.measurement",
        "reading.count",
        "reading.valid",
        "reading.window[0]",
        "reading.window[1]",
        "reading.window[2]",
        "reading.window[3]",
    }


def test_generate_all_units_writes_one_model_per_unit(tmp_path):
    architecture = _system_architecture()
    destinations = []

    for unit in _SYSTEM_UNITS:
        _, target = _generate_unit(architecture, unit, tmp_path / unit)
        destination = target / unit / "modelDescription.xml"
        assert destination.is_file()
        assert f'modelName="{unit}"' in destination.read_text(encoding="utf-8")
        destinations.append(destination.parent.name)

    assert destinations == _SYSTEM_UNITS
    assert sorted(path.name for path in tmp_path.iterdir()) == _SYSTEM_UNITS


def test_generate_adapter_never_re_resolves_the_export_unit(
    example, tmp_path, monkeypatch
):
    import pyfmi_sysml.reduction as upstream

    def fail(*args, **kwargs):
        raise AssertionError("the adapter re-resolved the export unit")

    monkeypatch.setattr(upstream, "resolve_system", fail)
    monkeypatch.setattr(upstream, "components", fail)

    target = _generate(example, tmp_path / "reduced")
    payload = load_adapter_model(target)

    assert payload["model_name"] == "ActuatorLink"
    assert (target / "ActuatorLink" / "modelDescription.xml").is_file()


def test_authored_parameter_and_neutral_input_starts_survive_the_handoff(tmp_path):
    pytest.importorskip("pycps_sysml")
    pytest.importorskip("pyfmi_interfaces")
    from test_parameters import _FIXTURE

    from pyfmi_sysml import parse
    from pyfmi_interop.core.adapter import adapter_from_reduction

    source = tmp_path / "parameter_exchange.sysml"
    source.write_text(_FIXTURE, encoding="utf-8")
    config = BuildConfig(serialization="packed")

    parsed = parse(
        source,
        includes=[core_definitions()],
        name="ParameterExchange",
    )
    spec = {signal.name: signal for signal in parsed.spec.signals}
    assert spec["transport"].initial == "loopback"
    assert spec["bind_address"].initial == "127.0.0.1:0"
    assert spec["peer_address"].initial == ""
    assert spec["queue_depth"].initial == 8
    assert isinstance(spec["queue_depth"].initial, int)
    assert spec["command.demand"].initial == 0.0
    assert isinstance(spec["command.demand"].initial, float)

    adapter = adapter_from_reduction(
        parsed.reduction,
        parsed.spec.to_model(config),
        component=parsed.unit,
        serialization=config.serialization,
    )
    signals = {signal.name: signal for signal in adapter.signals}
    assert signals["transport"].initial == "loopback"
    assert signals["bind_address"].initial == "127.0.0.1:0"
    assert signals["peer_address"].initial == ""
    assert signals["queue_depth"].initial == 8
    assert isinstance(signals["queue_depth"].initial, int)
    assert signals["command.demand"].initial == 0.0
    assert isinstance(signals["command.demand"].initial, float)

    from pyfmi_sysml import generate_adapter

    target = generate_adapter(parsed, tmp_path / "adapter", config)
    description = next(target.glob("*/modelDescription.xml"))
    starts = {
        variable.attrib["name"]: next(iter(variable)).attrib.get("start")
        for variable in ET.parse(description).getroot().iter("ScalarVariable")
    }
    assert starts["transport"] == "loopback"
    assert starts["bind_address"] == "127.0.0.1:0"
    assert starts["queue_depth"] == "8"
    assert starts["command.demand"] == "0"

