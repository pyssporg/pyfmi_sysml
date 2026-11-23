# c-runtime

Generate the C++17 FMI runtime, implement the five model hooks, compile, and
pack a loadable FMU.

## Run

From the workspace root, in the workspace venv:

```bash
python repos/pyfmi_sysml/examples/c-runtime/build_fmu.py
```

Everything lands under the gitignored `build/examples/c-runtime/`:

| Path | What |
| --- | --- |
| `Scale/modelDescription.xml` | the FMI XML, with a pinned generation time |
| `Minimal_Scale_fmi.cpp` | the generated FMI 2.0 runtime |
| `Minimal_Scale_hooks.h` | the hook seam the model implements |
| `Minimal_Scale_model.cpp` | the example's model, copied over the failing stub |
| `Scale.so` | the compiled shared library |
| `Scale.fmu` | the packed archive |

Expected output:

```text
build/examples/c-runtime/Scale.fmu
```

## Setup

The workspace venv from the top-level `README.md`, plus a C++17 compiler
(`g++`) on `PATH`.

## What the definition encodes

`minimal.sysml` declares one interface parameter (`gain`, default `2`), one
input (`u`), and one output (`y`). The library writes the sources and never
invokes a compiler; the compile and pack steps here are the implementer's job.

The model implements five hooks:

```c
fmi2Status Minimal_Scale_model_initialize(Minimal_Scale_Instance* instance);
fmi2Status Minimal_Scale_model_do_step(
    Minimal_Scale_Instance* instance, fmi2Real current_communication_point,
    fmi2Real communication_step_size);
fmi2Status Minimal_Scale_model_terminate(Minimal_Scale_Instance* instance);
fmi2Status Minimal_Scale_model_reset(Minimal_Scale_Instance* instance);
fmi2Status Minimal_Scale_model_free(Minimal_Scale_Instance* instance);
```

`Minimal_Scale_model.cpp` implements them as `y = gain * u`. The generated
stub's `do_step` returns `fmi2Error` on purpose: an unimplemented model must
fail loudly rather than pretend to step. The binary stem must equal the model
identifier (`Scale`); the archive name is free because packaging takes the
output path. The parameter/input/output roles are owned by
`pyssp_sysml_definitions/docs/roles.md`.
