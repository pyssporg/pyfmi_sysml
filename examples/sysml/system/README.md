# system

Package one interop unit, or every unit, from a single SysML architecture.

## Run

From the workspace root, in the workspace venv:

```bash
python repos/pyfmi_sysml/examples/sysml/system/build_all.py
```

Everything lands under the gitignored
`build/examples/sysml/system/all/<serialization>/`, one directory per unit:

| Path | What |
| --- | --- |
| `<unit>/model/` | generated sources, `wire.json`, `model.json` |
| `<unit>/build/` | the CMake build tree and shared library |
| `<unit>/<unit>.fmu` | the packaged FMU |

Expected output:

```text
build/examples/sysml/system/all/protobuf/ActuatorLink/ActuatorLink.fmu
build/examples/sysml/system/all/protobuf/Controller/Controller.fmu
build/examples/sysml/system/all/protobuf/SensorLink/SensorLink.fmu
```

One unit only:

```bash
python repos/pyfmi_sysml/examples/sysml/system/build_one.py
```

That packages the first unit by name; pass `--unit SensorLink` to choose
another. It writes under `build/examples/sysml/system/one/<serialization>/` and
prints the model directory and the FMU:

```text
build/examples/sysml/system/one/protobuf/model
build/examples/sysml/system/one/protobuf/ActuatorLink.fmu
```

Both scripts accept `--out` and `--serialization` (`protobuf` or `packed`).

## Setup

The workspace venv from the top-level `README.md`, plus `cmake`, `ninja`, `g++`,
and `protoc` on `PATH` for the native build.

## What the definition encodes

`bench.sysml` declares three independent interop units — `ActuatorLink`,
`SensorLink`, and `Controller` — plus an unmarked `part def System` that
composes them. Each unit inherits the shared `FmuInterop` base and its
`InteropDeployment` parameter port.

One part definition is one model: the units are never merged into a single IR,
and the container is never packaged as an FMU. `build_all.py` lists the
`:> FmuInterop` leaves with `fmu_units()` and runs the same
generate/build/package step for each; `build_one.py` loads the architecture once
and selects one unit with `model_from_architecture(architecture,
composition=unit, ...)`.

The role contract is stated once in `pyssp_sysml_definitions/docs/roles.md`;
this is only the landing. The inherited `InteropDeployment` port gives each
unit FMI parameters (`transport`, `bind_address`, `peer_address`). They are
initialization-only: the master binds them before `fmi2EnterInitializationMode`,
they are never wire fields, and changing them does not require a rebuild. The
unit's `in` ports become FMI inputs and wire `out` fields; its `out` ports
become FMI outputs and wire `in` fields.

## Composition

`System` composes `actuator`, `sensor`, and `controller` as parts, but it is not
marked `:> FmuModel`, so it only groups the three units. Each part is exported
on its own; composition decides the architecture, not the artifact count.

Both scripts use the Python API directly; the `pyfmi-interop` CLI has no
`composition=`/`component=` option and does not iterate over several units.
