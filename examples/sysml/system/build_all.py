"""Generate, build and package every interop unit in an architecture.

This is the all-units mode: ``pyfmi_sysml.fmu_units`` lists the
``:> FmuInterop`` leaves, and each one is exported on its own under
``<out>/<unit>/``.  One unit, one model, one FMU; the composing container is
never packaged as a model.

Everything is written under ``--out`` (default
``build/examples/sysml/system/all/<serialization>/``), which is gitignored when
run from the workspace root.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _pipeline import build_unit, fmu_unit_names

from pyfmi_sysml import architecture
from pyssp_sysml_definitions import core_definitions

EXAMPLE_DIR = Path(__file__).resolve().parent
DEFAULT_SYSML = EXAMPLE_DIR / "bench.sysml"
DEFAULT_OUT = Path("build") / "examples" / "sysml" / "system" / "all"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate, build and package every FmuInterop unit.",
    )
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    out_root = args.out / args.serialization

    loaded = architecture(DEFAULT_SYSML, includes=[core_definitions()])
    units = fmu_unit_names(loaded)
    if not units:
        print(
            f"error: no :> FmuInterop units found in {DEFAULT_SYSML}",
            file=sys.stderr,
        )
        return 1

    for unit in units:
        _, _, fmu_path = build_unit(
            loaded,
            unit,
            out_root / unit,
            serialization=args.serialization,
        )
        print(fmu_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
