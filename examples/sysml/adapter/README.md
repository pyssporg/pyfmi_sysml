# Adapter FMU from SysML (Python API)

This example authors a SysML v2 part definition and runs the whole pipeline in
Python — load, generate, build, package — with no CLI and no IR JSON.

## What the SysML says

`actuator_link.sysml` defines one package with two port definitions and one
part definition, and imports the shared `PyfmiInterop` library with
`private import PyfmiInterop::*;`. `from pyfmi_sysml import
interop_definitions` returns the same library path for tooling, and the loader
adds it to the load roots only when that import is present.

Its ports are:

| Port | Direction on the part | Fields |
| --- | --- | --- |
| `Command` | `in` | `setpoint : Real`, `mode : Integer`, `enable : Boolean`, `gains : Real[3]` |
| `Feedback` | `out` | `position : Real`, `status : Integer`, `healthy : Boolean`, `samples : Real[2]` |
| `InteropDeployment` | parameter interface (inherited) | `transport`, `bind_address`, `peer_address` |

`part def ActuatorLink :> FmuInterop` owns `in port command : Command;` and
`out port feedback : Feedback;`. The shared base supplies `interop_meta` and
`in port parameters : InteropDeployment;`, whose defaults are the loopback
bench configuration (`transport = "loopback"`,
`bind_address = "127.0.0.1:5000"`, empty peer). `ActuatorLink` is the only
`:> FmuModel` leaf, so it is the export unit itself: the FMI `modelName` is
the bare `ActuatorLink`, not `Root.ActuatorLink`, and the GUID uses the
direct-FMU scope without a composition level. The same rule exports a library
leaf under its bare name when the library is supplied as an include root.

The example no longer keeps a `Root`/`BenchDefaults` composition: binding a
`ParameterSet` to the deployment port did not change the exported FMI
defaults (the authored `InteropDeployment` values still won), so it was dead
configuration rather than a demonstration.

A port field with fixed multiplicity is not an FMI array — FMI 2.0 has no array
variable — so it becomes one scalar variable per element. `command.gains[0..2]`
becomes `command_gains_0` through `command_gains_2` on the wire and three
separate `ScalarVariable` entries in `modelDescription.xml`.

## Three classes of value

| Class | Examples | Where it lives | On the wire? |
| --- | --- | --- | --- |
| Build-time attribute | serialization backend, derived role (`step_size_s` belongs to the realtime model, not the adapter) | authored/generated into the build; changing it requires a rebuild | no |
| Deployment parameter | `transport`, `bind_address`, `peer_address` (`queue_depth` and `deadline_s` are documented keys the runtime does not consume) | FMI `causality="parameter"`, `variability="fixed"` with an authored `start` | never |
| Derived | value reference, field number, wire direction, model id | computed from the interface by the generators | yes (model id is in the envelope header) |

Parameters are initialization-only configuration, not wire fields: they are
writable before `fmi2EnterInitializationMode`, fixed afterwards, and omitted
from the payload schema, the packed layout, and the `model_id` digest; the
`psysml2` descriptor records them in a separate `parameters` list rather than
in `signals`. Runtime behaviour belongs in `in` ports (FMI
`causality="input"`), not parameters. The remaining INPUT/OUTPUT fields keep
the value references they were assigned, and each wire field number stays equal
to its value reference.

`resources/transport.json` lists `queue_depth` and `deadline_s` among the
recognised keys, but the C++ runtime does not consume them; only `transport`,
`bind_address`, and `peer_address` select the transport.

## Wire direction is the inverse of FMI causality

The FMI XML describes what the model exposes; the wire describes what the
endpoint sends.

| FMI causality | Adapter role | Wire direction |
| --- | --- | --- |
| `input` | publish | `out` |
| `output` | consume | `in` |
| `parameter` | configuration | never published |

Because `ActuatorLink` has both inputs and outputs, the derived role is
`adapter`: the six `command.*` fields are published (`out`) and the five
`feedback.*` fields are consumed (`in`).

## Generated FMU layout

For the default `ActuatorLink` identifier on Linux the archive contains:

```text
modelDescription.xml                     FMI 2.0 variables, causalities, value references
binaries/linux64/ActuatorLink.so         generated adapter shared library
binaries/linux64/ActuatorLink.proto      payload schema (protobuf only)
binaries/linux64/wire.json               field table, format, role, wire directions
resources/model.json                     resolved IR (role, serialization, signals)
resources/runtime.json                   fingerprint, binary path, format id
resources/transport.json                 parameter keys, schemes, env fallback
```

`packed` ships the same layout minus the `.proto`; `wire.json` alone describes
its deterministic little-endian payload. The generated source tree (including
`wire.json` and, for protobuf, the `.proto`) is also written to the model
directory before the build.

## Override a deployment parameter

The parameter variables are ordinary FMI variables with
`causality="parameter"` and `variability="fixed"`. Read their value references
from `modelDescription.xml` (or `resources/model.json`) and write them with the
matching setter *before* `fmi2EnterInitializationMode`:

```c
/* transport, bind_address and peer_address are String parameters. */
fmi2SetString(component, transport_vr, 1, (const fmi2String[]){"udp"});
fmi2SetString(component, bind_vr, 1, (const fmi2String[]){"127.0.0.1:5000"});
fmi2SetString(component, peer_vr, 1, (const fmi2String[]){"127.0.0.1:5001"});

fmi2EnterInitializationMode(component);   /* the transport is opened here */
fmi2ExitInitializationMode(component);
```

The runtime composes `<transport>://<bind_address>`, appends
`?peer=<peer_address>` when the peer is non-empty, and treats
`transport=loopback` or an empty `bind_address` as `loopback`. Parameter names
are matched case-insensitively without the port prefix. An unknown `transport`
value makes `fmi2EnterInitializationMode` return `fmi2Error` and log the key and
the accepted values (`loopback`, `udp`, `tcp`). Writing a parameter after
initialization is rejected with `fmi2Error`; writes in the instantiated state are
legal.

Because the transport is created per instance from parameter members, two
instances of the same FMU in one process can bind different addresses. The
process-global `PYFMI_INTEROP_TRANSPORT` / `PYFMI_INTEROP_TRANSPORT_ENDPOINT`
variables remain only as a fallback for a model that declares no parameter
interface at all.

## Run it

From the repository root, with the native runtime built and the package
installed:

```bash
python examples/sysml/adapter/generate_adapter_fmu.py --serialization protobuf
python examples/sysml/adapter/generate_adapter_fmu.py --serialization packed
```

Both write under `build/examples/sysml/adapter/<serialization>/` (gitignored):

```text
build/examples/sysml/adapter/<serialization>/model/       generated C++ and schema
build/examples/sysml/adapter/<serialization>/build/       CMake build tree
build/examples/sysml/adapter/<serialization>/ActuatorLink.fmu
```

Use `--out DIR` to choose another root, and `--sysml`, `--name`,
`--step-size`, or `--role` to override the inputs. The default `--name` is
`ActuatorLinkAdapter`; on the `psysml2` layer it becomes `model_name` in
`resources/runtime.json`, while the FMI identifier and the file stems above come
from the exported component (`ActuatorLink`). `--fmi-layer interop` instead
keeps the repository's own FMI facade and names the FMU, binary, and proto
after `--name`. The script prints the derived role, payload message and format
id, the field table, transport URI examples, and the final `.fmu` path.

## Pointing an external peer at it

Configure this FMU through its parameters as shown above. Give the peer the
address it should bind or send to according to its own role. A UDP peer that
consumes the adapter's published `command` fields binds a socket and receives
frames; the frame carries the payload whose schema is
`binaries/linux64/ActuatorLink.proto` inside the `.fmu` for `protobuf`.
Extract that file and compile it into the peer. For `packed` there is no
`.proto`: the peer reads `binaries/linux64/wire.json` and reproduces the packed
layout in value-reference order.
