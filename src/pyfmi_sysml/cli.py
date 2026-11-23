"""The ``pyfmi-sysml`` command line: one source-taking command per artifact.

Each command resolves its SysML source to a ``Reduction`` with
:func:`pyfmi_sysml.reduction.to_reduction` and calls the matching
``pyfmi_interfaces`` emitter. Packaging (``pyfmi package``) is not here; it
stays in ``pyfmi_interfaces``.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from pyfmi_interfaces.core.cli import Command, run
from pyfmi_interfaces.core.identity import GENERATION_TIME_FORMAT
from pyfmi_interfaces.modelica.package import DEFAULT_PACKAGE
from pyfmi_sysml.generate import (
    generate_c_headers,
    generate_c_runtime,
    generate_model_description,
    generate_modelica,
)
from pyssp_sysml_definitions import core_definitions

#: Where the generators write when no ``-o/--output`` is given.
DEFAULT_OUTPUT = "build"


def _parse_generation_time(text: str) -> datetime:
    """The FMI ``dateTime`` forms accepted on the command line, as UTC."""
    value = text.strip()
    if value.endswith("Z"):
        try:
            moment = datetime.strptime(value, GENERATION_TIME_FORMAT)
        except ValueError:
            pass
        else:
            return moment.replace(tzinfo=timezone.utc)

    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid generation time {text!r}; use "
            "YYYY-MM-DDTHH:MM:SSZ or an ISO 8601 form with an offset"
        ) from None
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise argparse.ArgumentTypeError(
            f"generation time {text!r} must carry a timezone, for example "
            "2026-01-01T00:00:00Z"
        )
    return moment.astimezone(timezone.utc)


def _add_source(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "source",
        metavar="SOURCE",
        help="A .sysml file or a directory containing them.",
    )


def _add_output(parser: argparse.ArgumentParser, help_text: str) -> None:
    parser.add_argument(
        "-o",
        "--output",
        metavar="OUT",
        default=DEFAULT_OUTPUT,
        help=help_text,
    )


def _add_composition(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--composition",
        metavar="NAME",
        help="Composition part definition to export (default: the single root).",
    )


def _add_base_index(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--base-index",
        metavar="N",
        type=int,
        default=0,
        help=(
            "First emitted array index (default: 0; 1 targets OMC-built "
            "Modelica FMUs, which declare arrays one-based)."
        ),
    )


def _add_generation_time(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--generation-time",
        metavar="ISO8601",
        type=_parse_generation_time,
        help=(
            "Fixed generationDateAndTime, for example 2026-01-01T00:00:00Z "
            "(default: 2000-01-01T00:00:00Z, the fixed epoch)."
        ),
    )


def _add_includes(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--include",
        dest="includes",
        metavar="PATH",
        type=Path,
        action="append",
        default=[],
        help=(
            "Extra SysML package root (file or directory) to merge into the "
            "load; repeatable."
        ),
    )
    parser.add_argument(
        "--core-definitions",
        action="store_true",
        help=(
            "Append pyssp_sysml_definitions.core_definitions() after every "
            "--include root, so a model can import PysspCore."
        ),
    )


def _includes(args: argparse.Namespace) -> list[Path]:
    """The include roots in resolution order: repeated flags, then the sugar."""
    roots = list(args.includes)
    if args.core_definitions:
        roots.append(core_definitions())
    return roots


def _configure_model_description(parser: argparse.ArgumentParser) -> None:
    _add_source(parser)
    _add_output(parser, "Output directory (default: build).")
    _add_composition(parser)
    _add_base_index(parser)
    _add_includes(parser)
    parser.add_argument(
        "--component",
        metavar="NAME",
        help="Restrict the output to one exported component.",
    )
    _add_generation_time(parser)


_PREFIX_HELP = "Header prefix and C type prefix (default: the package name)."
_COMPONENT_HELP = "Restrict the output to one exported component."


def _configure_headers(parser: argparse.ArgumentParser) -> None:
    _add_source(parser)
    _add_output(parser, "Output directory (default: build).")
    _add_composition(parser)
    _add_base_index(parser)
    _add_includes(parser)
    parser.add_argument("--component", metavar="NAME", help=_COMPONENT_HELP)
    parser.add_argument("--prefix", metavar="NAME", help=_PREFIX_HELP)


def _configure_runtime(parser: argparse.ArgumentParser) -> None:
    _configure_headers(parser)
    parser.add_argument(
        "--omit",
        metavar="NAME[,NAME...]",
        action="append",
        default=[],
        help=(
            "Skip the definition of an FMI function and leave a marker; "
            "repeatable and comma-separated."
        ),
    )


def _configure_modelica(parser: argparse.ArgumentParser) -> None:
    _add_source(parser)
    _add_output(parser, "Output directory (default: build).")
    _add_composition(parser)
    _add_includes(parser)
    parser.add_argument(
        "--package",
        metavar="NAME",
        default=DEFAULT_PACKAGE,
        help=f"Root Modelica package name (default: {DEFAULT_PACKAGE}).",
    )
    parser.add_argument(
        "--within",
        metavar="NAME",
        help="Enclosing Modelica scope for the root package.",
    )


def _run_model_description(args: argparse.Namespace) -> int:
    written = generate_model_description(
        args.source,
        args.output,
        composition=args.composition,
        component=args.component,
        generation_time=args.generation_time,
        base_index=args.base_index,
        includes=_includes(args),
    )
    _print_paths(written)
    return 0


def _run_headers(args: argparse.Namespace) -> int:
    written = generate_c_headers(
        args.source,
        args.output,
        composition=args.composition,
        component=args.component,
        prefix=args.prefix,
        base_index=args.base_index,
        includes=_includes(args),
    )
    _print_paths(written)
    return 0


def _run_runtime(args: argparse.Namespace) -> int:
    written = generate_c_runtime(
        args.source,
        args.output,
        composition=args.composition,
        component=args.component,
        prefix=args.prefix,
        base_index=args.base_index,
        omit=args.omit,
        includes=_includes(args),
    )
    _print_paths(written)
    return 0


def _run_modelica(args: argparse.Namespace) -> int:
    written = generate_modelica(
        args.source,
        args.output,
        package=args.package,
        within=args.within,
        composition=args.composition,
        includes=_includes(args),
    )
    _print_paths(written)
    return 0


def _print_paths(written: list) -> None:
    for path in written:
        print(path)


#: Every subcommand, in ``--help`` order.
COMMANDS: tuple[Command, ...] = (
    Command(
        name="model-description",
        help="Write modelDescription.xml per component.",
        description=(
            "Write modelDescription.xml per component to an output directory."
        ),
        configure=_configure_model_description,
        handler=_run_model_description,
    ),
    Command(
        name="c-headers",
        help="Write C interface headers.",
        description="Write the C interface headers to an output directory.",
        configure=_configure_headers,
        handler=_run_headers,
    ),
    Command(
        name="c-runtime",
        help="Write the C headers and a C++17 FMI runtime.",
        description=(
            "Write the C interface headers, a C++17 FMI 2.0 CoSimulation "
            "runtime, and a user-owned model file to an output directory."
        ),
        configure=_configure_runtime,
        handler=_run_runtime,
    ),
    Command(
        name="modelica",
        help="Write a Modelica interface package.",
        description=(
            "Write the Modelica interface package to an output directory."
        ),
        configure=_configure_modelica,
        handler=_run_modelica,
    ),
)

PROG = "pyfmi-sysml"


def main(argv: Sequence[str] | None = None) -> int:
    """Run one ``pyfmi-sysml`` command and return its process exit code."""
    return run(COMMANDS, argv, prog=PROG)


if __name__ == "__main__":
    raise SystemExit(main())
