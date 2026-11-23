"""Generate, build and package one interop unit from a multi-unit architecture.

This is the single-unit mode: the architecture is loaded once, one
``:> FmuInterop`` leaf is selected with ``composition=``, and its own model is
carried through the ``psysml2`` FMI layer into one FMU.  Nothing from the other
units is merged into its interface.

Everything is written under ``--out`` (default
``build/examples/sysml/system/one/<serialization>/``), which is gitignored when
run from the workspace root.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from _pipeline import build_unit, fmu_unit_names

from pyfmi_sysml import architecture
from pyssp_sysml_definitions import core_definitions

EXAMPLE_DIR = Path(__file__).resolve().parent
DEFAULT_SYSML = EXAMPLE_DIR / "bench.sysml"
DEFAULT_OUT = Path("build") / "examples" / "sysml" / "system" / "one"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate, build and package one FmuInterop unit.",
    )
    parser.add_argument(
        "--unit",
        default=None,
        help="Part definition to package (default: the first unit by name).",
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
    parser = _parser()
    args = parser.parse_args(argv)

    loaded = architecture(DEFAULT_SYSML, includes=[core_definitions()])
    units = fmu_unit_names(loaded)

    unit = args.unit or (units[0] if units else None)
    if unit is None or unit not in units:
        available = ", ".join(units) or "none"
        parser.error(f"no interop unit {unit!r}; choose from: {available}")

    out_dir = args.out / args.serialization
    _, model_dir, fmu_path = build_unit(
        loaded,
        unit,
        out_dir,
        serialization=args.serialization,
    )
    print(model_dir)
    print(fmu_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
