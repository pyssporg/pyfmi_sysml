"""Generate, build and package every interop unit in an architecture.

This is the all-units mode: ``pyfmi_interfaces.core.fmu_units`` lists the
``:> FmuInterop`` leaves, and each one is exported on its own under
``<out>/<unit>/``.  One unit, one model, one FMU; the composing container is
never packaged as a model.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _pipeline import build_unit, fmu_unit_names

from pyfmi_sysml import load_architecture

EXAMPLE_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXAMPLE_DIR.parents[2]
DEFAULT_SYSML = EXAMPLE_DIR / "bench.sysml"
DEFAULT_OUT_ROOT = REPO_ROOT / "build" / "examples" / "sysml" / "system" / "all"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate, build and package every FmuInterop unit.",
    )
    parser.add_argument("--sysml", type=Path, default=DEFAULT_SYSML)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=f"Output root (default: {DEFAULT_OUT_ROOT}/<serialization>).",
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

    architecture = load_architecture(args.sysml)
    units = fmu_unit_names(architecture)
    if not units:
        print(
            f"error: no :> FmuInterop units found in {args.sysml}",
            file=sys.stderr,
        )
        return 1

    out_root = args.out or DEFAULT_OUT_ROOT / args.serialization
    results: list[tuple[str, int, Path]] = []
    for unit in units:
        model, _, fmu_path = build_unit(
            architecture,
            unit,
            out_root / unit,
            serialization=args.serialization,
        )
        results.append((unit, len(model.signals), fmu_path))

    print(f"packaged {len(results)} interop units from {args.sysml}:")
    for unit, signal_count, fmu_path in results:
        print(f"  {unit:<16} {signal_count:>3} signals  {fmu_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
