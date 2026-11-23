"""Build a loadable FMU from the minimal model, end to end.

The library generates sources; this script plays the implementer:

1. :func:`pyfmi_sysml.generate_model_description` writes the FMI XML.
2. :func:`pyfmi_sysml.generate_c_runtime` writes the C++17 runtime and the
   model hook stub.
3. ``Minimal_Scale_model.cpp`` from this directory replaces the stub.
4. ``g++`` compiles the runtime and the model into ``Scale.so``.
5. ``pyssp_standard.FMU`` packs the archive.

Everything is written under ``--out`` (default ``build/examples/c-runtime/``),
which is gitignored when run from the workspace root. The generation time is
pinned so the XML is reproducible.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from pyssp_sysml_definitions import core_definitions
from pyfmi_sysml import (
    generate_c_runtime,
    generate_model_description,
    to_reduction,
)

EXAMPLE_DIR = Path(__file__).resolve().parent
DEFAULT_SYSML = EXAMPLE_DIR / "minimal.sysml"
DEFAULT_OUT = Path("build") / "examples" / "c-runtime"

GENERATION_TIME = datetime(2000, 1, 1, tzinfo=timezone.utc)
PREFIX = "Minimal"
COMPONENT = "Scale"
RUNTIME = f"{PREFIX}_{COMPONENT}_fmi.cpp"
MODEL = f"{PREFIX}_{COMPONENT}_model.cpp"
BINARY = f"{COMPONENT}.so"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"output directory (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args(argv)

    reduction = to_reduction(DEFAULT_SYSML, includes=[core_definitions()])
    [description] = generate_model_description(
        reduction, args.out, generation_time=GENERATION_TIME
    )
    generate_c_runtime(reduction, args.out)

    shutil.copyfile(EXAMPLE_DIR / MODEL, args.out / MODEL)
    _compile(args.out)
    fmu = _package(args.out, description)
    print(fmu)
    return 0


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


if __name__ == "__main__":
    raise SystemExit(main())
