"""Build a loadable FMU from the minimal model, end to end.

The library generates sources; this script plays the implementer:

1. :func:`pyfmi_sysml.generate_model_description` writes the FMI XML.
2. :func:`pyfmi_sysml.generate_c_runtime` writes the C++17 runtime and the
   model hook stub.
3. ``Minimal_Scale_model.cpp`` from this directory replaces the stub.
4. ``g++`` compiles the runtime and the model into ``Scale.so``.
5. ``pyssp_standard.FMU`` packs the archive; ``fmpy`` loads it, sets
   ``gain=2`` and ``u=3``, steps, and reads ``y == 6``.

Everything is written under ``--out`` (default ``build/examples/c-runtime/``),
which is gitignored. The generation time is pinned so the XML is reproducible.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from pyfmi_sysml import generate_c_runtime, generate_model_description

EXAMPLE_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXAMPLE_DIR.parents[1]
DEFAULT_SYSML = EXAMPLE_DIR / "minimal.sysml"
DEFAULT_OUT = REPO_ROOT / "build" / "examples" / "c-runtime"

GENERATION_TIME = datetime(2000, 1, 1, tzinfo=timezone.utc)
PREFIX = "Minimal"
COMPONENT = "Scale"
RUNTIME = f"{PREFIX}_{COMPONENT}_fmi.cpp"
MODEL = f"{PREFIX}_{COMPONENT}_model.cpp"
BINARY = f"{COMPONENT}.so"
STEP = 0.1


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse(argv)
    output_dir = Path(args.out)
    source = Path(args.sysml)

    [description] = generate_model_description(
        source, output_dir, generation_time=GENERATION_TIME
    )
    generate_c_runtime(source, output_dir)

    shutil.copyfile(EXAMPLE_DIR / MODEL, output_dir / MODEL)
    print(f"wrote {output_dir / MODEL}")

    _compile(output_dir)
    fmu = _package(output_dir, description)
    result = _step(fmu)

    print(f"\narchive: {fmu}")
    print(f"y = gain * u = 2 * 3 = {result}")
    return 0


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sysml", default=str(DEFAULT_SYSML), help="SysML source")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="output directory")
    return parser.parse_args(argv)


def _compile(output_dir: Path) -> None:
    """Compile the runtime and the model into the model-identifier binary."""
    gxx = shutil.which("g++")
    if gxx is None:
        raise SystemExit("g++ is required: install a C++17 compiler")
    command = [
        gxx,
        "-std=c++17",
        "-shared",
        "-fPIC",
        "-I",
        str(output_dir),
        "-I",
        str(output_dir / "fmi2"),
        str(output_dir / RUNTIME),
        str(output_dir / MODEL),
        "-o",
        str(output_dir / BINARY),
    ]
    print("$ " + " ".join(command))
    built = subprocess.run(command, capture_output=True, text=True)
    if built.returncode != 0:
        raise SystemExit(f"compile failed:\n{built.stdout}{built.stderr}")


def _package(output_dir: Path, description: Path) -> Path:
    """Pack the XML and the shared object; the binary stem is the identifier."""
    from pyssp_standard import FMU

    fmu = output_dir / f"{COMPONENT}.fmu"
    FMU.package(
        fmu,
        model_description=description,
        binaries={"linux64": output_dir / BINARY},
        fmi_version="2.0",
    )
    return fmu


def _step(fmu: Path) -> float:
    """Load the archive in fmpy, drive one step, and return ``y``."""
    try:
        import fmpy
        from fmpy.fmi2 import FMU2Slave
    except ModuleNotFoundError:
        raise SystemExit("fmpy is required to load the example: pip install fmpy")

    description = fmpy.read_model_description(str(fmu))
    unzip_dir = fmu.parent / "unpacked"
    shutil.rmtree(unzip_dir, ignore_errors=True)
    fmpy.extract(str(fmu), str(unzip_dir))

    by_name = {variable.name: variable.valueReference
               for variable in description.modelVariables}
    slave = FMU2Slave(
        guid=description.guid,
        modelIdentifier=description.coSimulation.modelIdentifier,
        unzipDirectory=str(unzip_dir),
        instanceName="scale",
    )
    slave.instantiate()
    slave.setupExperiment(startTime=0.0)
    slave.setReal([by_name["gain"]], [2.0])
    slave.enterInitializationMode()
    slave.exitInitializationMode()
    slave.setReal([by_name["u"]], [3.0])
    slave.doStep(currentCommunicationPoint=0.0, communicationStepSize=STEP)
    y = slave.getReal([by_name["y"]])[0]
    slave.terminate()
    slave.freeInstance()

    if y != 6.0:
        raise SystemExit(f"unexpected output: y = {y}, expected 6.0")
    return y


if __name__ == "__main__":
    raise SystemExit(main())
