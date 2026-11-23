"""Generate, build and package the ActuatorLink adapter FMU from SysML.

The pipeline is the public Python API, in four calls:

1. :func:`pyfmi_sysml.parse` parses the SysML interface once and projects it
   onto :class:`pyfmi_interop.ModelSpec`.
2. :func:`pyfmi_sysml.generate_adapter` emits the ``psysml2`` C++ adapter
   source tree.
3. :func:`pyfmi_interop.build_model` configures and builds it with CMake.
4. :func:`pyfmi_interop.package_fmu` writes the deterministic FMI 2.0 archive.

Everything is written under ``--out`` (default
``build/examples/sysml/adapter/<serialization>/``), which is gitignored when
run from the workspace root.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyfmi_interop import build_model, package_fmu
from pyfmi_interop.core import (
    BuildConfig,
    load_adapter_model,
    wire_model_from_adapter_json,
)
from pyfmi_interop.packaging import platform_binary_dir
from pyfmi_sysml import generate_adapter, parse
from pyssp_sysml_definitions import core_definitions

EXAMPLE_DIR = Path(__file__).resolve().parent
DEFAULT_SYSML = EXAMPLE_DIR / "actuator_link.sysml"
DEFAULT_NAME = "ActuatorLinkAdapter"
DEFAULT_OUT = Path("build") / "examples" / "sysml" / "adapter"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"output root (default: {DEFAULT_OUT}/<serialization>)",
    )
    parser.add_argument(
        "--serialization",
        choices=("protobuf", "packed"),
        default="protobuf",
        help="Payload serialization backend (default: protobuf).",
    )
    args = parser.parse_args(argv)

    out_root = args.out / args.serialization
    model_dir = out_root / "model"
    build_dir = out_root / "build"

    # 1. SysML interface -> specification, parsed exactly once.  An adapter has
    #    no step of its own; the master owns the cadence.
    parsed = parse(
        DEFAULT_SYSML,
        includes=[core_definitions()],
        name=DEFAULT_NAME,
        realtime=False,
    )

    # 2. Specification -> C++ adapter sources, wire schema and model.json.
    generate_adapter(
        parsed,
        model_dir,
        BuildConfig(serialization=args.serialization),
    )

    # 3. C++ sources -> shared library (links runtime and transport archives).
    library = build_model(model_dir, build_dir=build_dir)

    payload = load_adapter_model(model_dir)
    effective = wire_model_from_adapter_json(payload)
    platform = platform_binary_dir()
    extra = {f"binaries/{platform}/wire.json": (model_dir / "wire.json").read_bytes()}
    proto = model_dir / f"{effective.name}.proto"
    if proto.is_file():
        extra[f"binaries/{platform}/{proto.name}"] = proto.read_bytes()

    # 4. Library and descriptor -> deterministic FMI 2.0 archive.
    fmu_path = out_root / f"{_fmu_name(model_dir)}.fmu"
    package_fmu(
        model_dir,
        library,
        fmu_path,
        model=effective,
        model_description=(
            model_dir / effective.interface / "modelDescription.xml"
        ).read_text(encoding="utf-8"),
        model_json=(model_dir / "model.json").read_bytes(),
        model_name=payload["model_name"],
        extra_entries=extra,
        include_schema=False,
    )
    print(fmu_path)
    return 0


def _fmu_name(model_dir: Path) -> str:
    payload = json.loads((model_dir / "model.json").read_text(encoding="utf-8"))
    return str(payload["name"])


if __name__ == "__main__":
    raise SystemExit(main())
