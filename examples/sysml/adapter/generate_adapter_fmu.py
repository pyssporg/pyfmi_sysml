"""Generate an adapter FMU from a SysML v2 part definition, without the CLI.

The pipeline is the public Python API, in four calls:

1. :func:`pyfmi_sysml.parse` parses the SysML interface once and
   projects it onto :class:`pyfmi_interop.ModelSpec`.
2. :func:`pyfmi_interop.generate_model` (interop facade) or
   :func:`pyfmi_sysml.generate_adapter` (``psysml2`` facade) emits the
   C++ adapter source tree.
3. :func:`pyfmi_interop.build_model` configures and builds it with CMake.
4. :func:`pyfmi_interop.package_fmu` writes the deterministic FMI 2.0 archive.

Everything is written under ``--out`` (default ``build/examples/sysml/adapter/``),
which is gitignored.  The script prints the derived role, the payload message
and format, the field table, and example transport URIs so a peer can be
pointed at the same wire schema.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyfmi_interop import (
    build_model,
    generate_model,
    model_from_dict,
    package_fmu,
)
from pyfmi_interop.core import BuildConfig
from pyfmi_interop.packaging import platform_binary_dir
from pyfmi_interop.roles import ROLES
from pyfmi_sysml import generate_adapter, parse

EXAMPLE_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXAMPLE_DIR.parents[2]
DEFAULT_SYSML = EXAMPLE_DIR / "actuator_link.sysml"
DEFAULT_NAME = "ActuatorLinkAdapter"
DEFAULT_OUT_ROOT = REPO_ROOT / "build" / "examples" / "sysml" / "adapter"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate, build and package the ActuatorLink adapter FMU.",
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
    parser.add_argument("--name", default=DEFAULT_NAME, help="FMI model name.")
    parser.add_argument(
        "--step-size",
        type=float,
        default=None,
        dest="step_size",
        help="Base step size in seconds (default: from SysML, else 0.001).",
    )
    parser.add_argument(
        "--role",
        choices=ROLES,
        default=None,
        help="Narrow the role derived from FMI causality.",
    )
    parser.add_argument(
        "--fmi-layer",
        choices=("psysml2", "interop"),
        default="psysml2",
        help=(
            "Who owns the FMI 2.0 interface (default: psysml2, which delegates "
            "it to pyfmi_interfaces)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    out_root = args.out or DEFAULT_OUT_ROOT / args.serialization
    model_dir = out_root / "model"
    build_dir = out_root / "build"

    # 1. SysML interface -> specification, parsed exactly once.  An adapter has
    #    no step of its own; the master owns the cadence.
    parsed = parse(
        args.sysml,
        name=args.name,
        step_size_s=args.step_size,
        realtime=False,
    )
    model = parsed.spec

    # 2. Specification -> C++ adapter sources, wire schema and model.json.
    config = BuildConfig(serialization=args.serialization, role=args.role)
    if args.fmi_layer == "psysml2":
        generate_adapter(parsed, model_dir, config)
    else:
        generate_model(model, model_dir, config)

    # 3. C++ sources -> shared library (links runtime and transport archives).
    library = build_model(model_dir, build_dir=build_dir)

    fmu_path = out_root / f"{_fmu_name(model_dir)}.fmu"
    if args.fmi_layer == "psysml2":
        from pyfmi_interop.core import (
            load_adapter_model,
            wire_model_from_adapter_json,
        )

        payload = load_adapter_model(model_dir)
        effective = wire_model_from_adapter_json(payload)
        platform = platform_binary_dir()
        extra = {
            f"binaries/{platform}/wire.json": (model_dir / "wire.json").read_bytes()
        }
        proto = model_dir / f"{effective.name}.proto"
        if proto.is_file():
            extra[f"binaries/{platform}/{proto.name}"] = proto.read_bytes()
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
    else:
        effective = model_from_dict(
            json.loads((model_dir / "model.json").read_text(encoding="utf-8"))
        )
        package_fmu(model_dir, library, fmu_path, model=effective)

    _print_summary(model_dir, fmu_path)
    return 0


def _fmu_name(model_dir: Path) -> str:
    payload = json.loads((model_dir / "model.json").read_text(encoding="utf-8"))
    return str(payload["name"])


def _print_summary(model_dir: Path, fmu_path: Path) -> None:
    wire = json.loads((model_dir / "wire.json").read_text(encoding="utf-8"))
    model = json.loads((model_dir / "model.json").read_text(encoding="utf-8"))
    print(f"role: {wire['role']}")
    print(
        f"payload: {wire['payload_message']} "
        f"(format={wire['format']}, format_id={wire['format_id']})"
    )
    print(f"step_size_s: {wire.get('step_size_s')}")
    print(f"{'signal':<24} {'vr':>4} {'field':>5} {'causality':<9} wire")
    for signal in wire["signals"]:
        vr = signal.get("value_reference", signal.get("id"))
        field = signal.get("field")
        print(
            f"{signal['name']:<24} {vr:>4} {str(field):>5} "
            f"{signal['direction']:<9} {signal['wire']}"
        )
    parameters = [
        signal for signal in model["signals"] if signal["direction"] == "parameter"
    ]
    if parameters:
        print("deployment parameters (set before fmi2EnterInitializationMode):")
        for signal in parameters:
            print(
                f"  {signal['name']:<20} vr={signal['value_reference']:<3} "
                f"{signal['data_type']:<8} start={signal['initial']!r}"
            )
    print("transport URIs come from the parameters, for example:")
    print("  loopback")
    print("  udp://127.0.0.1:5000?peer=127.0.0.1:5001")
    print("  tcp://127.0.0.1:5001?peer=127.0.0.1:5000")
    print(f"fmu: {fmu_path}")


if __name__ == "__main__":
    raise SystemExit(main())
