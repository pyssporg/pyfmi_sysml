"""Component tests for ``modelDescription.xml`` generation.

The generator is run against the architecture fixtures into a temporary
directory; the tests then read the files back with the independent
``pyssp_standard`` codec and validator. The goldens pin the bytes, the
assertions pin the contract.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pycps_sysml2
import pytest
from pyssp_standard.standard.fmi2.codec import Fmi2ModelDescriptionXmlCodec
from pyssp_standard.standard.fmi2.validation import Fmi2ModelDescriptionValidator

from conftest import GENERATION_TIME, GOLDEN_ROOT, fixture_path
from golden_utils import assert_golden_text
from pyfmi_interfaces.core.identity import component_guid, format_generation_time
from pyfmi_interfaces.model_description.document import (
    model_description_document,
    render_model_description,
)
from pyfmi_sysml import (
    components,
    generate_model_description,
    to_reduction,
)

pytestmark = pytest.mark.component

CODEC = Fmi2ModelDescriptionXmlCodec()

#: Fixture subjects; each has exactly one exported component.
SUBJECTS = ("minimal", "sensor", "controller", "bus", "generator")

#: ``component_guid("ControllerComposition", "Controller")``, computed by the
#: test from ``uuid5(NAMESPACE_URL, "pyssp_sysml2/<composition>/<component>")``.
CONTROLLER_GUID = "{64044cfb-9f40-5998-99f1-6652e4828def}"

CASE_HEADINGS = (
    "# Case:",
    "## Artifacts",
    "## What this case proves",
    "## Update history",
)

CASE_FIELDS = (
    "**Conversion:**",
    "**Requirement / fault:**",
    "**Level:**",
    "**Input:**",
    "**Expected:**",
    "**Independent oracle:**",
    "**Comparison:**",
    "**Normalization:**",
    "**Volatile fields:**",
    "**Update policy:**",
    "**Notes:**",
)

#: Two leaf components, declared out of name order.
PAIR_MODEL = """package Pair {
  port def Signal {
    attribute value : Real;
  }

  part def Zulu {
    in port u : Signal;
    out port y : Signal;
  }

  part def Alpha {
    in port u : Signal;
    out port y : Signal;
  }

  part def PairComposition {
    part zulu : Zulu;
    part alpha : Alpha;
  }
}
"""

#: A typed parameter port: a Boolean and an Integer default besides a Real.
TYPED_MODEL = """package Typed {
  port def ParameterInterface;
  attribute def ParameterSet;

  port def Signal {
    attribute value : Real;
  }

  port def FlagParameters :> ParameterInterface {
    attribute enabled : Boolean = true;
    attribute count : Integer = 3;
  }

  part def Flagged {
    doc /* A component with a typed parameter port. */
    in port parameters : FlagParameters;
    in port u : Signal;
    out port y : Signal;
  }

  part def TypedComposition {
    part flagged : Flagged;
  }
}
"""

#: An experiment container that is a plain ``DefaultExperiment`` without
#: ``stepSize``; the FMI attribute must then be absent.
STEPLESS_MODEL = """package Stepless {
  attribute def Defaults :> DefaultExperiment {
    attribute startTime : Real = 0.0;
    attribute stopTime : Real = 2.0;
  }
  port def Signal { attribute value : Real; }
  part def Plate { in port u : Signal; }
  part def SteplessComposition {
    part plate : Plate;
    attribute defaults : Defaults;
  }
}
"""


#: An experiment container declaring the optional ``tolerance``; the FMI
#: attribute must carry it.
TOLERANT_MODEL = """package Tolerant {
  attribute def Defaults :> DefaultExperiment {
    attribute startTime : Real = 0.0;
    attribute stopTime : Real = 2.0;
    attribute stepSize : Real = 0.1;
    attribute tolerance = 1e-6;
  }
  port def Signal { attribute value : Real; }
  part def Plate { in port u : Signal; }
  part def TolerantComposition {
    part plate : Plate;
    attribute defaults : Defaults;
  }
}
"""


#: A document still writing the retired ``pyssp_*`` vocabulary; it must fail
#: with the dialect's migration error, never be read as a plain attribute.
RETIRED_MODEL = """package Retired {
  port def Signal { attribute value : Real; }
  part def Scale { in port u : Signal; }
  part def RetiredComposition {
    part scale : Scale;
    attribute pyssp_default_start_time : Real = 0.0;
  }
}
"""


#: A port payload with a fixed-length array field, for index-base coverage.
ARRAY_PORT_MODEL = """package ArrayPort {
  port def Signal {
    attribute value : Real[2];
  }

  part def Widget {
    in port u : Signal;
    out port y : Signal;
  }

  part def ArrayPortComposition {
    part widget : Widget;
  }
}
"""


#: A port whose members disagree on direction, plus an unmarked member on an
#: ``inout`` usage. Direction belongs to the member; the usage is only a fallback.
MIXED_MEMBER_MODEL = """package MemberDirections {
  port def MixedSignal {
    in attribute p[3] : Real;
    out attribute m : Real;
  }

  port def UnmarkedSignal {
    attribute n : Real;
  }

  part def Widget {
    inout port sig : MixedSignal;
    inout port fallback : UnmarkedSignal;
  }

  part def MemberDirectionsComposition {
    part widget : Widget;
  }
}
"""


def _write_model(directory: Path, text: str) -> Path:
    path = directory / "model.sysml"
    path.write_text(text, encoding="utf-8")
    return path


def _generate(subject: str, output_dir: Path, **kwargs) -> list[Path]:
    return generate_model_description(
        fixture_path(subject, f"{subject}.sysml"),
        output_dir,
        generation_time=GENERATION_TIME,
        **kwargs,
    )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("subject", SUBJECTS)
def test_every_generated_file_validates(subject: str, tmp_path: Path) -> None:
    """Each written file re-parses and passes the independent validator."""
    written = _generate(subject, tmp_path)

    assert written
    for path in written:
        xml = _read(path)
        Fmi2ModelDescriptionValidator().validate(CODEC.parse(xml), xml)


@pytest.mark.parametrize("subject", ("sensor", "generator"))
def test_same_generation_time_is_byte_identical(
    subject: str, tmp_path: Path
) -> None:
    first = _generate(subject, tmp_path / "first")
    second = _generate(subject, tmp_path / "second")

    assert [path.read_bytes() for path in first] == [
        path.read_bytes() for path in second
    ]


def test_default_generation_time_is_the_fixed_epoch(tmp_path: Path) -> None:
    """No injected clock: a default build is byte-identical across runs."""
    first = generate_model_description(
        fixture_path("sensor", "sensor.sysml"), tmp_path / "first"
    )
    second = generate_model_description(
        fixture_path("sensor", "sensor.sysml"), tmp_path / "second"
    )

    assert [path.read_bytes() for path in first] == [
        path.read_bytes() for path in second
    ]
    assert 'generationDateAndTime="2000-01-01T00:00:00Z"' in _read(first[0])
    assert format_generation_time(None) == "2000-01-01T00:00:00Z"


def test_another_generation_time_changes_only_the_timestamp(
    tmp_path: Path,
) -> None:
    earlier = _read(_generate("sensor", tmp_path / "earlier")[0])
    later = _read(
        generate_model_description(
            fixture_path("sensor", "sensor.sysml"),
            tmp_path / "later",
            generation_time=GENERATION_TIME + timedelta(hours=1),
        )[0]
    )

    assert 'generationDateAndTime="2026-01-01T01:00:00Z"' in later
    assert later.replace("2026-01-01T01:00:00Z", "@") == earlier.replace(
        "2026-01-01T00:00:00Z", "@"
    )


def test_controller_guid_is_pinned(tmp_path: Path) -> None:
    """``guid`` is ``uuid5(NAMESPACE_URL, "pyssp_sysml2/<composition>/<name>")``.

    Computed here from the frozen namespace string, so a namespace, input, or
    formatting change fails instead of silently regenerating every guid.
    """
    expected = (
        "{"
        + str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                "pyssp_sysml2/ControllerComposition/Controller",
            )
        )
        + "}"
    )

    [path] = _generate("controller", tmp_path)

    assert CODEC.parse(_read(path)).guid == expected
    assert component_guid("ControllerComposition", "Controller") == expected
    assert expected == CONTROLLER_GUID


def test_direct_fmu_model_identity_is_the_bare_name(tmp_path: Path) -> None:
    """A marked definition is its own component; no container level is added."""
    expected = (
        "{"
        + str(uuid.uuid5(uuid.NAMESPACE_URL, "pyssp_sysml2/Generator"))
        + "}"
    )

    [path] = _generate("generator", tmp_path)

    document = CODEC.parse(_read(path))

    assert path.parent.name == "Generator"
    assert document.model_name == "Generator"
    assert document.capabilities is not None
    assert document.capabilities.model_identifier == "Generator"
    assert document.guid == expected


def test_controller_variable_summary_is_exact() -> None:
    """Names, value references, causalities, variabilities, starts, and types."""
    architecture = pycps_sysml2.load(
        fixture_path("controller", "controller.sysml")
    )

    document = model_description_document(
        to_reduction(architecture),
        "Controller",
        generation_time=GENERATION_TIME,
    )

    assert [
        (
            variable.name,
            variable.value_reference,
            variable.causality,
            variable.variability,
            variable.start,
            variable.type_name,
        )
        for variable in document.variables
    ] == [
        ("gains[0]", 0, "parameter", "fixed", "1", "Real"),
        ("gains[1]", 1, "parameter", "fixed", "2.5", "Real"),
        ("label", 2, "parameter", "fixed", "nominal", "String"),
        ("command.manual", 3, "input", None, "0", "Real"),
        ("command.auto", 4, "input", None, "0", "Real"),
        ("command.mode", 5, "input", "discrete", "0", "Integer"),
        ("throttle.demand", 6, "output", None, None, "Real"),
        ("throttle.enabled", 7, "output", "discrete", None, "Boolean"),
        ("status.code", 8, "output", "discrete", None, "Integer"),
    ]
    assert [
        unknown.index for unknown in document.model_structure.outputs
    ] == [7, 8, 9]
    assert [
        unknown.index for unknown in document.model_structure.initial_unknowns
    ] == [7, 8, 9]


def test_boolean_start_is_fmi_text(tmp_path: Path) -> None:
    """``Boolean`` starts are ``true``/``false``, never ``str(True)``."""
    [path] = generate_model_description(
        _write_model(tmp_path, TYPED_MODEL),
        tmp_path / "out",
        generation_time=GENERATION_TIME,
    )

    document = CODEC.parse(_read(path))

    assert [(variable.name, variable.start) for variable in document.parameters] == [
        ("enabled", "true"),
        ("count", 3),
    ]
    assert '<Boolean start="true" />' in _read(path)
    assert "True" not in _read(path)


def test_interface_default_wins_over_an_applied_parameter_set(
    tmp_path: Path,
) -> None:
    """The reduction reads parameter defaults from the interface only."""
    [path] = generate_model_description(
        fixture_path("applied", "applied.sysml"),
        tmp_path / "out",
        generation_time=GENERATION_TIME,
    )

    document = CODEC.parse(_read(path))

    assert [(variable.name, variable.start) for variable in document.parameters] == [
        ("gains[0]", 1.0),
        ("gains[1]", 2.5),
    ]


def test_base_index_one_renames_array_variables(tmp_path: Path) -> None:
    """``base_index=1`` shifts ``[0]``/``[1]`` to ``[1]``/``[2]`` in the XML."""
    [path] = generate_model_description(
        fixture_path("controller", "controller.sysml"),
        tmp_path / "out",
        generation_time=GENERATION_TIME,
        base_index=1,
    )

    document = CODEC.parse(_read(path))

    assert [variable.name for variable in document.parameters] == [
        "gains[1]",
        "gains[2]",
        "label",
    ]
    assert "gains[0]" not in _read(path)


def test_base_index_threads_through_port_array_members(tmp_path: Path) -> None:
    """The base reaches port payload fields, not only parameters."""
    architecture = pycps_sysml2.load(_write_model(tmp_path, ARRAY_PORT_MODEL))

    [component] = components(architecture, base_index=1)

    assert [variable.name for variable in component.variables] == [
        "u.value[1]",
        "u.value[2]",
        "y.value[1]",
        "y.value[2]",
    ]


def test_mixed_port_members_carry_their_own_causality(tmp_path: Path) -> None:
    """Member direction wins over the ``inout`` usage; an unmarked member is input."""
    architecture = pycps_sysml2.load(_write_model(tmp_path, MIXED_MEMBER_MODEL))

    [component] = components(architecture, base_index=1)

    assert [
        (variable.name, variable.causality, variable.start_text)
        for variable in component.variables
    ] == [
        ("sig.p[1]", "input", "0"),
        ("sig.p[2]", "input", "0"),
        ("sig.p[3]", "input", "0"),
        ("sig.m", "output", None),
        ("fallback.n", "input", "0"),
    ]
    assert [
        (port.name, port.direction, port.causality) for port in component.ports
    ] == [
        ("sig", None, "input"),
        ("fallback", "inout", "input"),
    ]


def test_default_experiment_comes_from_the_experiment_container(
    tmp_path: Path,
) -> None:
    """The typed container maps its three fields onto the FMI element."""
    [path] = generate_model_description(
        fixture_path("applied", "applied.sysml"),
        tmp_path / "out",
        generation_time=GENERATION_TIME,
    )

    experiment = CODEC.parse(_read(path)).default_experiment

    assert experiment is not None
    assert experiment.start_time == 0.0
    assert experiment.stop_time == 10.0
    assert experiment.step_size == 0.1
    assert (
        '<DefaultExperiment startTime="0.0" stopTime="10.0" stepSize="0.1" />'
        in _read(path)
    )


def test_step_size_is_omitted_when_the_container_declares_none(
    tmp_path: Path,
) -> None:
    """A plain ``DefaultExperiment`` may omit ``stepSize``; so does the XML."""
    [path] = generate_model_description(
        _write_model(tmp_path, STEPLESS_MODEL),
        tmp_path / "out",
        generation_time=GENERATION_TIME,
    )

    text = _read(path)
    experiment = CODEC.parse(text).default_experiment

    assert experiment is not None
    assert experiment.start_time == 0.0
    assert experiment.stop_time == 2.0
    assert experiment.step_size is None
    assert "stepSize" not in text


def test_tolerance_comes_from_the_experiment_container(
    tmp_path: Path,
) -> None:
    """An authored ``tolerance`` is emitted and the file still validates."""
    [path] = generate_model_description(
        _write_model(tmp_path, TOLERANT_MODEL),
        tmp_path / "out",
        generation_time=GENERATION_TIME,
    )

    text = _read(path)
    experiment = CODEC.parse(text).default_experiment
    Fmi2ModelDescriptionValidator().validate(CODEC.parse(text), text)

    assert experiment is not None
    assert experiment.tolerance == 1e-6
    assert experiment.step_size == 0.1
    assert 'tolerance="1e-06"' in text


def test_tolerance_is_omitted_when_the_container_declares_none(
    tmp_path: Path,
) -> None:
    """No authored ``tolerance`` means no attribute, not a default."""
    [path] = generate_model_description(
        fixture_path("applied", "applied.sysml"),
        tmp_path / "out",
        generation_time=GENERATION_TIME,
    )

    text = _read(path)
    experiment = CODEC.parse(text).default_experiment

    assert experiment is not None
    assert experiment.step_size == 0.1
    assert experiment.tolerance is None
    assert "tolerance" not in text


def test_no_default_experiment_without_an_experiment_container(
    tmp_path: Path,
) -> None:
    [path] = _generate("minimal", tmp_path)

    assert CODEC.parse(_read(path)).default_experiment is None


def test_retired_control_tags_are_refused(tmp_path: Path) -> None:
    """The removed ``pyssp_*`` vocabulary fails with the migration hint."""
    with pytest.raises(ValueError, match="no longer supported"):
        generate_model_description(
            _write_model(tmp_path, RETIRED_MODEL),
            tmp_path / "out",
            generation_time=GENERATION_TIME,
        )


def test_naive_generation_time_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        generate_model_description(
            fixture_path("minimal", "minimal.sysml"),
            tmp_path,
            generation_time=datetime(2026, 1, 1),
        )


def test_output_layout_is_sorted_by_component_name(tmp_path: Path) -> None:
    written = generate_model_description(
        _write_model(tmp_path, PAIR_MODEL),
        tmp_path / "out",
        generation_time=GENERATION_TIME,
    )

    assert [
        path.relative_to(tmp_path / "out").as_posix() for path in written
    ] == ["Alpha/modelDescription.xml", "Zulu/modelDescription.xml"]


def test_component_filter_selects_one_and_refuses_an_unknown(tmp_path: Path) -> None:
    written = _generate("controller", tmp_path / "selected", component="Controller")

    assert [
        path.relative_to(tmp_path / "selected").as_posix() for path in written
    ] == ["Controller/modelDescription.xml"]

    with pytest.raises(ValueError, match="No exported component named 'Missing'"):
        _generate("controller", tmp_path / "missing", component="Missing")


def test_document_round_trips_through_the_codec() -> None:
    architecture = pycps_sysml2.load(
        fixture_path("applied", "applied.sysml")
    )
    reduction = to_reduction(architecture)
    component = components(architecture)[0]

    document = model_description_document(
        reduction,
        component,
        generation_time=GENERATION_TIME,
    )
    parsed = CODEC.parse(
        render_model_description(
            reduction,
            component,
            generation_time=GENERATION_TIME,
        )
    )

    assert parsed.fmi_version == document.fmi_version == "2.0"
    assert parsed.model_name == document.model_name
    assert parsed.guid == document.guid
    assert parsed.description == document.description
    assert parsed.generation_tool == document.generation_tool
    assert parsed.generation_date_and_time == document.generation_date_and_time
    assert parsed.variable_naming_convention == document.variable_naming_convention
    assert parsed.interface_type == document.interface_type == "CoSimulation"
    assert parsed.capabilities is not None
    assert parsed.capabilities.model_identifier == "Scale"
    assert [
        (
            variable.name,
            variable.value_reference,
            variable.type_name,
            variable.causality,
            variable.variability,
        )
        for variable in parsed.variables
    ] == [
        ("gains[0]", 0, "Real", "parameter", "fixed"),
        ("gains[1]", 1, "Real", "parameter", "fixed"),
        ("u", 2, "Real", "input", None),
        ("y", 3, "Real", "output", None),
    ]
    assert [variable.start for variable in parsed.parameters] == [1.0, 2.5]
    assert [
        unknown.index for unknown in parsed.model_structure.outputs
    ] == [4]
    assert [
        unknown.index for unknown in parsed.model_structure.initial_unknowns
    ] == [4]
    assert parsed.default_experiment == document.default_experiment


@pytest.mark.parametrize("subject", SUBJECTS)
def test_golden_model_description(subject: str, tmp_path: Path) -> None:
    """Generated bytes equal the committed golden for every fixture."""
    written = _generate(subject, tmp_path)

    assert len(written) == 1
    [path] = written
    assert path.parent.parent == tmp_path

    golden = (
        GOLDEN_ROOT
        / "model-description"
        / subject
        / path.parent.name
        / path.name
    )
    assert_golden_text(golden, _read(path))


@pytest.mark.parametrize("subject", SUBJECTS)
def test_case_record_is_complete(subject: str) -> None:
    """Every subject carries a provenance record with the required fields."""
    text = _read(GOLDEN_ROOT / "model-description" / subject / "case.md")

    for marker in CASE_HEADINGS + CASE_FIELDS:
        assert marker in text, f"{subject}/case.md lacks {marker!r}"


#: One definition used as ``P`` and ``~P``: conjugation flips each directed
#: member's causality, so both ends resolve to the same definition.
CONJUGATED_MODEL = """package ConjugatedPorts {
  port def Feed {
    out attribute p : Real;
    in attribute m : Real;
  }

  part def Source {
    out port feed : Feed;
  }

  part def Sink {
    in port feed : ~Feed;
  }

  part def ConjugatedComposition {
    part source : Source;
    part sink : Sink;
  }
}
"""


def test_conjugated_port_flips_member_causality(tmp_path: Path) -> None:
    """``~P`` flips input/output per member; both ends share one definition."""
    architecture = pycps_sysml2.load(_write_model(tmp_path, CONJUGATED_MODEL))

    by_name = {
        component.name: component
        for component in components(architecture, base_index=1)
    }

    assert [port.definition for port in by_name["Source"].ports] == ["Feed"]
    assert [port.definition for port in by_name["Sink"].ports] == ["Feed"]
    assert [
        (variable.name, variable.causality, variable.start_text)
        for variable in by_name["Source"].variables
    ] == [
        ("feed.p", "output", None),
        ("feed.m", "input", "0"),
    ]
    assert [
        (variable.name, variable.causality, variable.start_text)
        for variable in by_name["Sink"].variables
    ] == [
        ("feed.p", "input", "0"),
        ("feed.m", "output", None),
    ]
