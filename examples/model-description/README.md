# model-description

Build one FMI 2.0 `modelDescription.xml` per exported leaf part from a SysML v2
architecture.

## Run

From the workspace root, in the workspace venv:

```bash
python repos/pyfmi_sysml/examples/model-description/build.py
```

Everything lands under the gitignored `build/examples/model-description/`:

| Path | What |
| --- | --- |
| `Sensor/modelDescription.xml` | the `Sensor` leaf's FMI interface |
| `Valve/modelDescription.xml` | the `Valve` leaf's FMI interface |

Expected output:

```text
build/examples/model-description/Sensor/modelDescription.xml
build/examples/model-description/Valve/modelDescription.xml
```

The script pins the generation time, so a fresh run is byte-identical to the
checked-in `reference/` tree.

## Setup

The workspace venv from the top-level `README.md`. No compiler, no extra
package.

## What the definition encodes

`thermal_plant.sysml` is this directory's input: one container root with two
leaf parts, `Sensor` and `Valve`, plus their port definitions. A leaf part is
one FMI model; the container is not exported. The shared vocabulary is a load
root (`core_definitions()`), and the roles are owned by
`pyssp_sysml_definitions/docs/roles.md`.

Each leaf exports its own set. A port whose only member is a non-array `value`
takes the port name; any other field keeps the qualified spelling:

| model | name | value reference | causality | type |
| --- | --- | --- | --- | --- |
| `Sensor` | `gain` | 0 | parameter | `Real` (start `1.0`) |
| `Sensor` | `offset` | 1 | parameter | `Real` (start `0.0`) |
| `Sensor` | `raw` | 2 | input | `Real` |
| `Sensor` | `measured` | 3 | output | `Real` |
| `Valve` | `limit` | 0 | parameter | `Real` (start `1.0`) |
| `Valve` | `command.open` | 1 | input | `Real` |
| `Valve` | `position` | 2 | output | `Real` |

The deployment parameters (`gain`, `offset`, `limit`) are initialization
configuration, not runtime signals; the inputs and outputs are the FMI
interface.
