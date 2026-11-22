"""System gate: fmpy accepts the generated XML and loads the packaged FMU.

The independent oracle here is fmpy, a consumer this package does not own. It
validates ``modelDescription.xml`` against its own FMI 2.0 schema and
instantiates the ``.fmu`` through a third-party FMI 2.0 CoSimulation
implementation, so a document that only this package's validator accepts still
fails. The packaged case compiles a model that copies every input to an output
and checks the FMI calls from the outside.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
from pyssp_standard import FMU

from conftest import GENERATION_TIME, fixture_path
from pyfmi_sysml import generate_c_runtime, generate_model_description

pytestmark = pytest.mark.system

#: Every fixture with a ``model-description`` golden.
SUBJECTS = ("bus", "controller", "generator", "minimal", "sensor")

#: The controller artifact names; the packager requires the binary stem to
#: equal ``CoSimulation/@modelIdentifier``.
PACKAGE = "Controller"
BINARY = f"{PACKAGE}.so"
RUNTIME = f"{PACKAGE}_{PACKAGE}_fmi.cpp"
MODEL = f"{PACKAGE}_{PACKAGE}_model.cpp"
HEADER = f"{PACKAGE}_{PACKAGE}.h"

_GUID_DEFINE = re.compile(
    rf'^#define {PACKAGE.upper()}_{PACKAGE.upper()}_GUID "([^"]+)"$',
    re.MULTILINE,
)

#: The implementer's model: every output mirrors one input. The generated file
#: is written once and then replaced here, exactly as an implementer would.
CONTROLLER_MODEL = """\
#include "Controller_Controller_hooks.h"

fmi2Status Controller_Controller_model_initialize(
    Controller_Controller_Instance* instance) {
  (void)instance;
  return fmi2OK;
}

fmi2Status Controller_Controller_model_do_step(
    Controller_Controller_Instance* instance, fmi2Real current_communication_point,
    fmi2Real communication_step_size) {
  (void)current_communication_point;
  (void)communication_step_size;
  instance->throttle.demand = instance->command.manual;
  instance->throttle.enabled = true;
  instance->status.code = instance->command.mode;
  return fmi2OK;
}

fmi2Status Controller_Controller_model_terminate(
    Controller_Controller_Instance* instance) {
  (void)instance;
  return fmi2OK;
}

fmi2Status Controller_Controller_model_reset(
    Controller_Controller_Instance* instance) {
  (void)instance;
  return fmi2OK;
}

fmi2Status Controller_Controller_model_free(
    Controller_Controller_Instance* instance) {
  (void)instance;
  return fmi2OK;
}
"""


def _source(subject: str) -> Path:
    return fixture_path(subject, f"{subject}.sysml")


def _fmpy():
    """Import fmpy or skip with an explicit reason; never pass silently."""
    try:
        import fmpy
        from fmpy.fmi2 import FMU2Slave
    except ModuleNotFoundError:
        pytest.skip("fmpy is not installed")
    return fmpy, FMU2Slave


def _gxx() -> str:
    gxx = shutil.which("g++")
    if gxx is None:
        pytest.skip("g++ is not installed")
    return gxx


@pytest.mark.parametrize("subject", SUBJECTS)
def test_model_description_passes_the_fmpy_validator(
    subject: str, tmp_path: Path
) -> None:
    """fmpy's schema and semantic validation accept every generated document."""
    fmpy, _ = _fmpy()

    [path] = generate_model_description(
        _source(subject), tmp_path, generation_time=GENERATION_TIME
    )

    # ``read_model_description`` only sniffs the XML form for ``str`` paths; a
    # ``Path`` would be treated as an FMU archive.
    fmpy.read_model_description(str(path))


def test_packaged_fmu_loads_and_steps_in_fmpy(tmp_path: Path) -> None:
    """A compiled controller FMU instantiates, steps, and round-trips values."""
    fmpy, fmu2_slave = _fmpy()
    gxx = _gxx()

    generated = tmp_path / "generated"
    [description] = generate_model_description(
        _source("controller"), generated, generation_time=GENERATION_TIME
    )
    generate_c_runtime(_source("controller"), generated)
    (generated / MODEL).write_text(CONTROLLER_MODEL, encoding="utf-8")

    binary = generated / BINARY
    command = [
        gxx,
        "-std=c++17",
        "-shared",
        "-fPIC",
        "-I",
        str(generated),
        "-I",
        str(generated / "fmi2"),
        str(generated / RUNTIME),
        str(generated / MODEL),
        "-o",
        str(binary),
    ]
    built = subprocess.run(command, capture_output=True, text=True)
    assert built.returncode == 0, (
        f"{' '.join(command)}\n{built.stdout}{built.stderr}"
    )

    fmu_path = FMU.package(
        tmp_path / f"{PACKAGE}.fmu",
        model_description=description,
        binaries={"linux64": binary},
        fmi_version="2.0",
    )

    document = fmpy.read_model_description(str(fmu_path))
    found = _GUID_DEFINE.search((generated / HEADER).read_text(encoding="utf-8"))
    assert found is not None, f"{HEADER} declares no GUID"
    expected_guid = found.group(1)
    assert document.guid == expected_guid
    assert document.coSimulation.modelIdentifier == PACKAGE

    value_references = {
        variable.name: variable.valueReference
        for variable in document.modelVariables
    }

    unpacked = fmpy.extract(str(fmu_path), str(tmp_path / "unpacked"))
    fmu = fmu2_slave(
        guid=document.guid,
        unzipDirectory=unpacked,
        modelIdentifier=document.coSimulation.modelIdentifier,
        instanceName="fmpy-load",
    )
    fmu.instantiate()
    try:
        fmu.setupExperiment(startTime=0.0)
        fmu.enterInitializationMode()
        fmu.exitInitializationMode()
        fmu.setReal([value_references["command.manual"]], [1.5])
        fmu.setInteger([value_references["command.mode"]], [7])
        fmu.doStep(currentCommunicationPoint=0.0, communicationStepSize=0.1)

        assert fmu.getReal([value_references["throttle.demand"]])[0] == 1.5
        assert fmu.getBoolean([value_references["throttle.enabled"]])[0] == 1
        assert fmu.getInteger([value_references["status.code"]])[0] == 7
        fmu.terminate()
    finally:
        fmu.freeInstance()
