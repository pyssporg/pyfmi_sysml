# Examples

Runnable walkthroughs for `pyfmi_interfaces`. Each directory is **fully
standalone**: it carries its own SysML input, its scripts, and its README, and
shares no code or model with its neighbours. Copy one out of the tree and it
still describes the whole step.

Every example writes only under `build/` (or the `--out` you pass), which is
gitignored. No generated source, compiled binary, or `.fmu` is committed. The
one exception is `model-description/reference/`: the pinned clock makes that
output deterministic, so it is checked in for diffing.

| Example | Own input | Shows | Needs |
| --- | --- | --- | --- |
| [`model-description/`](model-description/) | `thermal_plant.sysml` | one FMI XML document per leaf, from a script and the CLI | `pyfmi` |
| [`modelica/`](modelica/) | `minimal.sysml` | Modelica package and the implementer seam | `omc` (optional) |
| [`c-runtime/`](c-runtime/) | `minimal.sysml` | C++17 runtime, five hooks, compile, pack, load | `g++`, `fmpy` |

## Prerequisites

Install the package with its dev extra (see the top-level `README.md`):

```bash
python3 -m venv venv
./venv/bin/pip install -e ".[dev]"
```

Run the commands from the repository root. If the `pyfmi` console script is not
on `PATH`, use `python -m pyfmi_interfaces.cli` instead.

## Run each example

```bash
# One modelDescription.xml per leaf part
python examples/model-description/build.py

# Modelica package plus the completed implementer model
python examples/modelica/build_model.py

# Sources to a loadable FMU, then step it in fmpy
python examples/c-runtime/build_fmu.py
```

Each directory's `README.md` has the expected file tree, the flags that matter,
the CLI equivalent of its script, and the manual command sequence.

## What is not here

The package never compiles generated code. The `g++` and `omc` steps in the
`c-runtime` and `modelica` examples are the implementer's build steps; the
library's job ends when it has written the sources.
