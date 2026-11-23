# Adapter FMU from SysML

Generate, build, and package one interop adapter FMU from a SysML v2 part
definition.

## Run

From the workspace root, in the workspace venv:

```bash
python repos/pyfmi_sysml/examples/sysml/adapter/generate_adapter_fmu.py
```

Everything lands under the gitignored
`build/examples/sysml/adapter/<serialization>/`:

| Path | What |
| --- | --- |
| `model/` | generated C++ sources, `wire.json`, `model.json` |
| `build/` | the CMake build tree and shared library |
| `ActuatorLink.fmu` | the packaged FMI 2.0 archive |

Expected output:

```text
build/examples/sysml/adapter/protobuf/ActuatorLink.fmu
```

`--serialization packed` selects the packed payload instead; both backends
produce the same FMU layout, minus the `.proto` schema.

## Setup

The workspace venv from the top-level `README.md`, plus `cmake`, `ninja`, `g++`,
and `protoc` on `PATH` for the native build.

## What the definition encodes

`actuator_link.sysml` defines one package with two port definitions and one
`part def ActuatorLink :> FmuInterop`. The source imports the shared
`PyfmiInterop::*` library, and the script passes
`pyssp_sysml_definitions.core_definitions()` so the interop vocabulary's own
`:> FmuModel` and `:> ParameterInterface` references resolve against the shared
core.

| Port | Direction on the part | Fields |
| --- | --- | --- |
| `Command` | `in` | `setpoint : Real`, `mode : Integer`, `enable : Boolean`, `gains : Real[3]` |
| `Feedback` | `out` | `position : Real`, `status : Integer`, `healthy : Boolean`, `samples : Real[2]` |
| `InteropDeployment` | parameter interface (inherited) | `transport`, `bind_address`, `peer_address` |

`ActuatorLink` is the only `:> FmuModel` leaf, so the FMI `modelName` is the
bare `ActuatorLink` and the GUID uses the direct-FMU scope. A port field with
fixed multiplicity is not an FMI array — FMI 2.0 has no array variable — so
`command.gains[0..2]` becomes `command_gains_0` through `command_gains_2` on
the wire and three separate `ScalarVariable` entries.

The role contract is stated once in `pyssp_sysml_definitions/docs/roles.md`.
This table says only where each role lands in the adapter's FMI artifact:

| Class | Examples | Where it lives | On the wire? |
| --- | --- | --- | --- |
| Build-time attribute | serialization backend, derived role | authored/generated into the build; changing it requires a rebuild | no |
| Deployment parameter | `transport`, `bind_address`, `peer_address` | FMI `causality="parameter"`, `variability="fixed"` with an authored `start` | never |
| Derived | value reference, field number, wire direction, model id | computed from the interface by the generators | yes (model id is in the envelope header) |

Parameters are writable before `fmi2EnterInitializationMode`, fixed afterwards,
and omitted from the payload schema, the packed layout, and the `model_id`
digest. The runtime composes `<transport>://<bind_address>`, appends
`?peer=<peer_address>` when non-empty, and treats `transport=loopback` or an
empty `bind_address` as loopback. Wire direction is the inverse of FMI
causality: `input` publishes (`out`), `output` consumes (`in`), `parameter` is
never published. Because `ActuatorLink` has both, its derived role is
`adapter`.

The archive carries `modelDescription.xml`, `binaries/<platform>/ActuatorLink.so`
and `wire.json`, `resources/model.json`, `runtime.json` (with the build
fingerprint), and `transport.json`; protobuf adds the `.proto` schema.
