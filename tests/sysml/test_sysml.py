"""SysML ingestion: attribute normalization and architecture-to-IR mapping."""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from pyssp_sysml_definitions import core_definitions

from pyfmi_interop import ir

sysml = importlib.import_module("pyfmi_sysml.parse")

pytestmark = [pytest.mark.unit, pytest.mark.sysml]


class _Attribute:
    """Minimal stand-in for :class:`pycps_sysml2.Attribute`."""

    def __init__(self, value: object) -> None:
        self.value = value


def test_step_size_attributes_and_explicit_override() -> None:
    assert sysml._step_size_from_attributes({}, None) == sysml.DEFAULT_STEP_SIZE_S
    assert sysml._step_size_from_attributes({"step_size": _Attribute(0.01)}, None) == 0.01
    assert sysml._step_size_from_attributes({"step_size_s": 0.02}, None) == 0.02
    assert sysml._step_size_from_attributes({"period_s": 0.005}, None) == 0.005
    assert sysml._step_size_from_attributes({"rate_hz": 2000}, None) == 0.0005
    assert sysml._step_size_from_attributes({"rate": 1000}, None) == 0.001
    assert sysml._step_size_from_attributes({"step_size": 0.1}, 0.02) == 0.02


def test_period_key_is_seconds_at_or_below_one_and_hz_above_one() -> None:
    assert sysml._period_seconds_from_attributes({"period": 0.5}) == 0.5
    assert sysml._period_seconds_from_attributes({"period": 1.0}) == 1.0
    assert sysml._period_seconds_from_attributes({"period": 10.0}) == 0.1


def test_rate_attributes_cover_seconds_and_hertz_forms() -> None:
    assert sysml._rate_hz_from_attributes({}) is None
    assert sysml._rate_hz_from_attributes({"rate_hz": 10}) == 10.0
    assert sysml._rate_hz_from_attributes({"rate": 25}) == 25.0
    assert sysml._rate_hz_from_attributes({"period_s": 0.1}) == 10.0
    assert sysml._rate_hz_from_attributes({"period": 100}) == 100.0
    assert sysml._rate_hz_from_attributes({"step_size": 0.2}) == 5.0


@pytest.mark.parametrize("value", [0, -1, "not-a-number", True])
def test_invalid_timing_values_are_rejected(value: object) -> None:
    with pytest.raises(ValueError):
        sysml._step_size_from_attributes({"step_size": value}, None)


def test_data_type_and_direction_mapping() -> None:
    assert sysml._data_type("Real") is ir.DataType.REAL
    assert sysml._data_type("integer") is ir.DataType.INTEGER
    assert sysml._data_type("Boolean") is ir.DataType.BOOLEAN
    assert sysml._data_type("String") is ir.DataType.STRING
    with pytest.raises(ValueError, match="unsupported FMI data type"):
        sysml._data_type("Complex")

    assert sysml._direction("input") is ir.Direction.INPUT
    assert sysml._direction("output") is ir.Direction.OUTPUT
    assert sysml._direction("parameter") is ir.Direction.PARAMETER
    with pytest.raises(ValueError, match="unsupported FMI causality"):
        sysml._direction("inout")


def test_string_signals_get_capacity_and_initial_value() -> None:
    real = SimpleNamespace(
        name="r", type_name="Real", causality="input", value_reference=7, start=1.5
    )
    string = SimpleNamespace(
        name="s", type_name="String", causality="output", value_reference=8, start="ok"
    )

    real_signal = sysml._signal_from_variable(real, rate_hz=None, unit="V")
    string_signal = sysml._signal_from_variable(string, rate_hz=10.0, unit=None)

    assert real_signal.capacity == 0
    assert real_signal.initial == 1.5
    assert real_signal.unit == "V"
    assert string_signal.data_type is ir.DataType.STRING
    assert string_signal.capacity == sysml.DEFAULT_STRING_CAPACITY
    assert string_signal.initial == "ok"
    assert string_signal.rate_hz == 10.0


def test_model_name_sanitization() -> None:
    assert sysml._identifier("Demo") == "Demo"
    assert sysml._identifier("Demo.Package") == "Demo_Package"
    assert sysml._identifier("1Demo") == "_1Demo"
    assert sysml._identifier("") == "model"


def _architecture() -> object:
    pycps = pytest.importorskip("pycps_sysml2")
    try:
        import pyfmi_interfaces  # noqa: F401
    except Exception as error:  # noqa: BLE001 - broken optional dependency
        pytest.skip(f"pyfmi_interfaces is not importable: {error}")

    # A typed container marker keeps author metadata out of the FMI variable
    # set, the 0.3.0 replacement for the retired ``pyssp_*`` names.
    metadata = pycps.AttributeDefinition(
        name="TelemetryMetadata", specializes=("ParameterSet",)
    )
    telemetry = pycps.PortDefinition(
        name="Telemetry",
        attributes={
            "value": pycps.Attribute(name="value", type_name="Real"),
            "label": pycps.Attribute(name="label", type_name="String"),
            "unit": pycps.Attribute(
                name="unit", type_name="TelemetryMetadata", value="V"
            ),
            "rate": pycps.Attribute(
                name="rate", type_name="TelemetryMetadata", value=10.0
            ),
            "step_size_s": pycps.Attribute(
                name="step_size_s", type_name="TelemetryMetadata", value=0.01
            ),
            "transport": pycps.Attribute(
                name="transport",
                type_name="TelemetryMetadata",
                value="loopback",
            ),
            "channel": pycps.Attribute(
                name="channel",
                type_name="TelemetryMetadata",
                value="telemetry",
            ),
            "transport_endpoint": pycps.Attribute(
                name="transport_endpoint",
                type_name="TelemetryMetadata",
                value="udp://239.0.0.1:5000",
            ),
        },
    )
    plant = pycps.PartDefinition(
        name="Plant",
        ports={"out": pycps.PortUsage(name="out", direction="out", type_name="Telemetry")},
    )
    root = pycps.PartDefinition(
        name="Demo",
        parts={"plant": pycps.PartUsage(name="plant", type_name="Plant")},
    )

    architecture = pycps.Architecture(package_name="Demo")
    architecture.add_part_def(root)
    architecture.add_part_def(plant)
    architecture.add_port_def(telemetry)
    architecture.add_attribute_def(metadata)
    return architecture


def test_model_from_architecture_maps_signals_rates_and_units() -> None:
    model = sysml.model_from_architecture(_architecture())

    assert model.name == "Demo"
    assert model.interface == "Plant"
    assert model.guid == ir.deterministic_guid("Demo")
    assert model.step_size_s == pytest.approx(0.01)
    assert [signal.name for signal in model.signals] == ["out.label", "out.value"]
    assert [signal.value_reference for signal in model.signals] == [1, 2]

    label, value = model.signals
    assert label.data_type is ir.DataType.STRING
    assert label.capacity == sysml.DEFAULT_STRING_CAPACITY
    assert value.data_type is ir.DataType.REAL
    assert value.capacity == 0
    assert value.direction is ir.Direction.OUTPUT
    assert value.rate_hz == pytest.approx(10.0)
    assert value.unit == "V"


def test_model_from_architecture_honours_explicit_step_size_and_name() -> None:
    model = sysml.model_from_architecture(
        _architecture(), name="Renamed", step_size_s=0.02, realtime=False
    )

    assert model.name == "Renamed"
    assert model.step_size_s == pytest.approx(0.02)
    assert model.realtime is False


def test_parse_reduces_once_and_loads_the_source_once(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("pycps_sysml2")
    pytest.importorskip("pyfmi_interfaces")
    import pycps_sysml2
    import pyfmi_sysml.reduction as upstream
    from test_parameters import _FIXTURE

    source = tmp_path / "deployment.sysml"
    source.write_text(_FIXTURE, encoding="utf-8")

    loads = []
    real_load = pycps_sysml2.load

    def counting_load(*args, **kwargs):
        loads.append(args)
        return real_load(*args, **kwargs)

    reductions = []
    real_reduction = upstream.to_reduction

    def counting_reduction(*args, **kwargs):
        reductions.append(args)
        return real_reduction(*args, **kwargs)

    monkeypatch.setattr(pycps_sysml2, "load", counting_load)
    monkeypatch.setattr(upstream, "to_reduction", counting_reduction)

    parsed = sysml.parse(source)

    assert parsed.unit == "Exchange"
    assert len(loads) == 1
    assert len(reductions) == 1


def test_parsed_model_carries_the_selected_unit_and_the_upstream_reduction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("pycps_sysml2")
    pytest.importorskip("pyfmi_interfaces")
    import pyfmi_sysml.reduction as upstream
    from pyfmi_interfaces.core import Reduction

    reductions = []
    real_reduction = upstream.to_reduction

    def counting_reduction(*args, **kwargs):
        reductions.append(args)
        return real_reduction(*args, **kwargs)

    monkeypatch.setattr(upstream, "to_reduction", counting_reduction)

    example = (
        Path(__file__).resolve().parents[2]
        / "examples"
        / "sysml"
        / "adapter"
        / "actuator_link.sysml"
    )
    parsed = sysml.parse(example, name="ActuatorLinkAdapter", realtime=False)

    assert len(reductions) == 1
    assert parsed.unit == "ActuatorLink"
    assert isinstance(parsed.reduction, Reduction)
    assert parsed.reduction.root == "ActuatorLink"


def test_single_parse_then_adapter_generation_never_reloads(tmp_path, monkeypatch):
    pytest.importorskip("pycps_sysml2")
    pytest.importorskip("pyfmi_interfaces")
    import pycps_sysml2

    source = tmp_path / "single.sysml"
    source.write_text(
        "package Single {\n"
        "  private import ScalarValues::*;\n"
        "  private import PysspCore::*;\n"
        "  port def Signal { attribute value : Real; }\n"
        "  part def FmuInterop :> FmuModel { }\n"
        "  part def Only :> FmuInterop { out port y : Signal; }\n"
        "}\n",
        encoding="utf-8",
    )

    calls = {"count": 0}
    real_load = pycps_sysml2.load

    def counted(*args, **kwargs):
        calls["count"] += 1
        return real_load(*args, **kwargs)

    monkeypatch.setattr(pycps_sysml2, "load", counted)
    parsed = sysml.parse(
        source, includes=[core_definitions()], name="OnlyModel", realtime=False
    )
    assert calls["count"] == 1

    def failing(*args, **kwargs):
        raise AssertionError("generate_adapter reloaded the SysML source")

    monkeypatch.setattr(pycps_sysml2, "load", failing)
    from pyfmi_sysml import generate_adapter

    target = generate_adapter(parsed, tmp_path / "adapter")

    assert (target / "wire.json").is_file()
    assert (target / "CMakeLists.txt").is_file()
    with pytest.raises(AssertionError, match="reloaded"):
        sysml.parse(source, name="OnlyModel", realtime=False)


def test_includes_merge_a_library_defined_fmu(tmp_path):
    pytest.importorskip("pycps_sysml2")
    pytest.importorskip("pyfmi_interfaces")

    library = tmp_path / "chain_library.sysml"
    library.write_text(
        "package ChainLibrary {\n"
        "  private import ScalarValues::*;\n"
        "  private import PysspCore::*;\n"
        "\n"
        "  port def Signal {\n"
        "    attribute value : Real;\n"
        "  }\n"
        "\n"
        "  part def FmuInterop :> FmuModel {\n"
        "  }\n"
        "\n"
        "  part def Leaf :> FmuInterop {\n"
        "    in port command : Signal;\n"
        "    out port status : Signal;\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    app = tmp_path / "chain_app.sysml"
    app.write_text(
        "package ChainApp {\n"
        "  private import ChainLibrary::*;\n"
        "}\n",
        encoding="utf-8",
    )

    model = sysml.load_model(app, includes=[library, core_definitions()])

    assert model.interface == "Leaf"
    assert {signal.name for signal in model.signals} == {"command", "status"}
