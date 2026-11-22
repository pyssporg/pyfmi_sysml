# modelica

Generate a Modelica package, then fill the equation the generator deliberately
leaves out.

`generate_modelica` writes a package with a complete connector set and a
`partial model` for each component. The implementer model `Scale.mo` is created
once with an empty `equation` section and never rewritten — that is the seam.
This example ships the completed model:

```modelica
model Scale
  extends Scale_Interface;
equation
  y.value = gain * u.value;
end Scale;
```

From the repository root:

```bash
python examples/modelica/build_model.py
```

The script generates into `build/examples/modelica/GeneratedInterfaces/`,
replaces `Scale.mo` with the completed model, and — when `omc` is on `PATH` —
runs `checkModel` on the package and `buildModel` on `Scale`.

Expected output (paths trimmed):

```text
.../build/examples/modelica/GeneratedInterfaces/GeneratedInterfaces.mo
.../build/examples/modelica/GeneratedInterfaces/Interfaces.mo
.../build/examples/modelica/GeneratedInterfaces/Scale.mo
.../build/examples/modelica/GeneratedInterfaces/Scale_Interface.mo
.../build/examples/modelica/GeneratedInterfaces/package.mo
.../build/examples/modelica/GeneratedInterfaces/package.order
wrote .../build/examples/modelica/GeneratedInterfaces/Scale.mo
OpenModelica checked and built GeneratedInterfaces.Scale
```

The generated seam, for reference:

```modelica
partial model Scale_Interface
  parameter Real gain = 2;
  input GeneratedInterfaces.Signal u;
  output GeneratedInterfaces.Signal y;
end Scale_Interface;
```

Without the equation, `buildModel` fails with *Too few equations,
under-determined system*. `omc` is optional: the script skips the check and
still writes the package when it is absent.

The manual equivalent:

```bash
pyfmi modelica examples/modelica/minimal.sysml -o build/examples/modelica
cp examples/modelica/Scale.mo build/examples/modelica/GeneratedInterfaces/
omc build/examples/modelica/build.mos
```
