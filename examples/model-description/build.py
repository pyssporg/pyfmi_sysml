"""Write one ``modelDescription.xml`` per exported leaf part.

The input is this directory's own ``thermal_plant.sysml``: a container root
with two leaf parts, ``Sensor`` and ``Valve``. The generation time is pinned so
the XML is reproducible; pass ``--component`` to export a single leaf.

Output lands under ``--out`` (default ``build/examples/model-description/``),
which is gitignored.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from pyfmi_sysml import generate_model_description

EXAMPLE_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXAMPLE_DIR.parents[1]
DEFAULT_SYSML = EXAMPLE_DIR / "thermal_plant.sysml"
DEFAULT_OUT = REPO_ROOT / "build" / "examples" / "model-description"

GENERATION_TIME = datetime(2000, 1, 1, tzinfo=timezone.utc)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse(argv)
    written = generate_model_description(
        Path(args.sysml),
        Path(args.out),
        component=args.component,
        generation_time=GENERATION_TIME,
    )
    for path in written:
        print(path)
    return 0


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sysml", default=str(DEFAULT_SYSML), help="SysML source")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="output directory")
    parser.add_argument(
        "--component", default=None, help="export only this leaf part"
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
