# Examples

Runnable walkthroughs for `pyfmi_sysml`. Each directory carries its own SysML
input and scripts, and no directory imports another.

## Run

From the workspace root, in the workspace venv. Every example writes under the
gitignored `build/examples/` and takes an optional `--out`; the `sysml` examples
also accept `--serialization`, and `build_one.py` accepts `--unit`.

| Example | Builds | Command |
| --- | --- | --- |
| [`model-description/`](model-description/) | one FMI XML document per leaf part | `python repos/pyfmi_sysml/examples/model-description/build.py` |
| [`modelica/`](modelica/) | a Modelica package plus the completed `Scale` model | `python repos/pyfmi_sysml/examples/modelica/build_model.py` |
| [`c-runtime/`](c-runtime/) | a C++17 runtime compiled and packed into an FMU | `python repos/pyfmi_sysml/examples/c-runtime/build_fmu.py` |
| [`sysml/adapter/`](sysml/adapter/) | one interop adapter FMU | `python repos/pyfmi_sysml/examples/sysml/adapter/generate_adapter_fmu.py` |
| [`sysml/system/`](sysml/system/) | every interop unit in one architecture | `python repos/pyfmi_sysml/examples/sysml/system/build_all.py` |

## Setup

One workspace venv from `requirements-experimental.txt` and
`requirements-thirdparty.txt`, with the working trees installed editable (see
the top-level `README.md`). `c-runtime` and both `sysml` examples need `cmake`,
`ninja`, `g++`, and `protoc` on `PATH`.

## Shared vocabulary

The models import the shared role vocabulary (`private import PysspCore::*;`,
or `private import PyfmiInterop::*;` for the interop units) and never redeclare
`ParameterInterface`, `ParameterSet`, `FmuModel`, or the metadata containers.
Each script supplies the vocabulary as an include root through
`pyssp_sysml_definitions.core_definitions()`; the interop library is added when
the model imports it. No `.sysml` vocabulary is copied here.

The roles themselves — build metadata, initialization configuration, runtime
signal — are defined once in `pyssp_sysml_definitions/docs/roles.md`. These
examples state only where each role lands in this repository's FMI and Modelica
artifacts.

The `pyfmi-sysml` CLI has no `--include` option, so the scripts call the public
`pyfmi_sysml` wrappers and pass `core_definitions()` explicitly: the vocabulary
is a real load root, not a name match.

## What the library does not do

The package never compiles generated code. The `g++` and CMake steps in the
`c-runtime` and `sysml` examples are the implementer's build steps; the
library's job ends when it has written the sources.
