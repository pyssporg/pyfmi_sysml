"""Generate, build and package one interop unit from a multi-unit architecture.

This is the single-unit mode: the architecture is loaded once, one
``:> FmuInterop`` leaf is selected with ``composition=``, and its own model is
carried through the ``psysml2`` FMI layer into one FMU.  Nothing from the other
units is merged into its interface.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from _pipeline import build_unit, fmu_unit_names

from pyfmi_sysml import load_architecture

EXAMPLE_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXAMPLE_DIR.parents[2]
DEFAULT_SYSML = EXAMPLE_DIR / "bench.sysml"
DEFAULT_OUT_ROOT = REPO_ROOT / "build" / "examples" / "sysml" / "system" / "one"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate, build and package one FmuInterop unit.",
    )
    parser.add_argument(
        "--unit",
        default=None,
        help="Part definition to package (default: the only unit).",
    )
    parser.add_argument("--sysml", type=Path, default=DEFAULT_SYSML)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=f"Output directory (default: {DEFAULT_OUT_ROOT}/<serialization>).",
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

    architecture = load_architecture(args.sysml)
    units = fmu_unit_names(architecture)

    unit = args.unit
    if unit is None:
        if len(units) != 1:
            available = ", ".join(units) or "none"
            parser.error(
                f"{args.sysml} has {len(units)} interop units ({available}); "
                "pass --unit NAME"
            )
        unit = units[0]
    elif unit not in units:
        available = ", ".join(units) or "none"
        parser.error(f"no interop unit {unit!r}; choose from: {available}")

    out_dir = args.out or DEFAULT_OUT_ROOT / args.serialization
    model, model_dir, fmu_path = build_unit(
        architecture,
        unit,
        out_dir,
        serialization=args.serialization,
    )

    print(f"unit: {unit}")
    print(f"signals: {len(model.signals)}")
    print(f"model sources: {model_dir}")
    print(f"fmu: {fmu_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
