"""Write one ``modelDescription.xml`` per exported leaf part.

The input is this directory's own ``thermal_plant.sysml``: a container root
with two leaf parts, ``Sensor`` and ``Valve``. The shared vocabulary is passed
as an include root, and the generation time is pinned so the output is
reproducible.

Output lands under ``--out`` (default ``build/examples/model-description/``),
which is gitignored when run from the workspace root.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from pyssp_sysml_definitions import core_definitions
from pyfmi_sysml import generate_model_description

EXAMPLE_DIR = Path(__file__).resolve().parent
DEFAULT_SYSML = EXAMPLE_DIR / "thermal_plant.sysml"
DEFAULT_OUT = Path("build") / "examples" / "model-description"

GENERATION_TIME = datetime(2000, 1, 1, tzinfo=timezone.utc)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"output directory (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args(argv)

    written = generate_model_description(
        DEFAULT_SYSML,
        args.out,
        generation_time=GENERATION_TIME,
        includes=[core_definitions()],
    )
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
