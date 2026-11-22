"""Generate the Modelica package and complete the implementer model.

:func:`pyfmi_sysml.generate_modelica` writes a package whose ``Scale.mo``
contains no equations, which is deliberate: the equation is the implementer's
job, just like the C hooks. This script drops in the checked-in ``Scale.mo``
(``y.value = gain * u.value``) and, when ``omc`` is installed, checks and
builds the package.

Output lands under ``--out`` (default ``build/examples/modelica/``), which is
gitignored.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from pyfmi_sysml import generate_modelica

EXAMPLE_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXAMPLE_DIR.parents[1]
DEFAULT_SYSML = EXAMPLE_DIR / "minimal.sysml"
DEFAULT_OUT = REPO_ROOT / "build" / "examples" / "modelica"

PACKAGE = "GeneratedInterfaces"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse(argv)
    output_dir = Path(args.out)
    source = Path(args.sysml)

    written = generate_modelica(source, output_dir)
    model = output_dir / PACKAGE / "Scale.mo"
    shutil.copyfile(EXAMPLE_DIR / "Scale.mo", model)
    for path in written:
        print(path)
    print(f"wrote {model}")

    omc = shutil.which("omc")
    if omc is None:
        print("\nomc not found: skipping the Modelica check")
        return 0

    return _check_with_omc(Path(omc), output_dir)


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sysml", default=str(DEFAULT_SYSML), help="SysML source")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="output directory")
    return parser.parse_args(argv)


def _check_with_omc(omc: Path, output_dir: Path) -> int:
    """Check the package and build ``Scale``, failing on any OpenModelica error."""
    script = output_dir / "build.mos"
    package = (output_dir / PACKAGE / "package.mo").as_posix()
    script.write_text(
        "\n".join(
            [
                f'loadFile("{package}");',
                f"checkModel({PACKAGE}.{PACKAGE});",
                f"checkModel({PACKAGE}.Scale);",
                f"buildModel({PACKAGE}.Scale, startTime=0, stopTime=1);",
                "getErrorString();",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    built = subprocess.run(
        [str(omc), str(script)], capture_output=True, text=True, cwd=output_dir
    )
    combined = built.stdout + built.stderr
    print(combined)
    if built.returncode != 0 or "Error" in combined:
        raise SystemExit("OpenModelica rejected the package")
    print("OpenModelica checked and built GeneratedInterfaces.Scale")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
