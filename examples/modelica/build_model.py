"""Generate the Modelica package and complete the implementer model.

:func:`pyfmi_sysml.generate_modelica` writes a package whose ``Scale.mo``
contains no equations, which is deliberate: the equation is the implementer's
job, just like the C hooks. This script drops in the checked-in ``Scale.mo``
(``y.value = gain * u.value``) and prints the package paths.

Output lands under ``--out`` (default ``build/examples/modelica/``), which is
gitignored when run from the workspace root.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Sequence

from pyssp_sysml_definitions import core_definitions
from pyfmi_sysml import generate_modelica, load_architecture

EXAMPLE_DIR = Path(__file__).resolve().parent
DEFAULT_SYSML = EXAMPLE_DIR / "minimal.sysml"
DEFAULT_OUT = Path("build") / "examples" / "modelica"

PACKAGE = "GeneratedInterfaces"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"output directory (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args(argv)

    architecture = load_architecture(DEFAULT_SYSML, includes=[core_definitions()])
    written = generate_modelica(architecture, args.out)
    model = args.out / PACKAGE / "Scale.mo"
    shutil.copyfile(EXAMPLE_DIR / "Scale.mo", model)
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
