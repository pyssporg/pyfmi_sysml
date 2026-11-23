# modelica

Generate a Modelica package from SysML, then fill the equation the generator
leaves to the implementer.

## Run

From the workspace root, in the workspace venv:

```bash
python repos/pyfmi_sysml/examples/modelica/build_model.py
```

Everything lands under the gitignored `build/examples/modelica/`:

| Path | What |
| --- | --- |
| `GeneratedInterfaces/package.mo` | the package root |
| `GeneratedInterfaces/package.order` | the package file order |
| `GeneratedInterfaces/GeneratedInterfaces.mo` | the root package contents |
| `GeneratedInterfaces/Interfaces.mo` | the shared connector set |
| `GeneratedInterfaces/Scale_Interface.mo` | the generated `partial model` seam |
| `GeneratedInterfaces/Scale.mo` | the completed implementer model |

Expected output:

```text
build/examples/modelica/GeneratedInterfaces/GeneratedInterfaces.mo
build/examples/modelica/GeneratedInterfaces/Interfaces.mo
build/examples/modelica/GeneratedInterfaces/Scale.mo
build/examples/modelica/GeneratedInterfaces/Scale_Interface.mo
build/examples/modelica/GeneratedInterfaces/package.mo
build/examples/modelica/GeneratedInterfaces/package.order
```

## Setup

The workspace venv from the top-level `README.md`; no native tool is needed:
the artifact is the Modelica text.

## What the definition encodes

`minimal.sysml` declares one interface parameter, one input, and one output.
`generate_modelica` writes a complete connector set and a `partial model` per
component, with an empty `equation` section in `Scale.mo` — that is the seam.
The example ships the completed model and copies it over the generated stub:

```modelica
model Scale
  extends Scale_Interface;
equation
  y.value = gain * u.value;
end Scale;
```

The seam it extends:

```modelica
partial model Scale_Interface
  parameter Real gain = 2;
  input GeneratedInterfaces.Signal u;
  output GeneratedInterfaces.Signal y;
end Scale_Interface;
```

Without the equation, `buildModel` reports *Too few equations,
under-determined system*. The parameter, input, and output roles, and the
shared vocabulary, are owned by `pyssp_sysml_definitions/docs/roles.md`.
