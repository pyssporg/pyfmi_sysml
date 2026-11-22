# c-runtime

The full pipeline: generate the C++17 runtime, implement the five model hooks,
compile, pack an `.fmu`, and load it.

The library writes sources and never invokes a compiler. Everything below the
hook seam is the implementer's job, which is what this example demonstrates.

From the repository root:

```bash
python examples/c-runtime/build_fmu.py
```

The script:

1. writes `Scale/modelDescription.xml` with a pinned generation time;
2. writes the runtime, headers, hook header, and a stub `Minimal_Scale_model.cpp`;
3. copies the example's `Minimal_Scale_model.cpp` (`y = gain * u`) over the stub;
4. compiles `Minimal_Scale_fmi.cpp` and the model into `Scale.so`;
5. packs `Scale.fmu` with `pyssp_standard.FMU`;
6. loads it in `fmpy`, sets `gain = 2` and `u = 3`, steps, and reads `y`.

Expected tail:

```text
wrote .../build/examples/c-runtime/Minimal_Scale_model.cpp
$ g++ -std=c++17 -shared -fPIC -I ... -I .../fmi2 .../Minimal_Scale_fmi.cpp .../Minimal_Scale_model.cpp -o .../Scale.so

archive: build/examples/c-runtime/Scale.fmu
y = gain * u = 2 * 3 = 6.0
```

The hook seam the model implements:

```c
fmi2Status Minimal_Scale_model_initialize(Minimal_Scale_Instance* instance);
fmi2Status Minimal_Scale_model_do_step(
    Minimal_Scale_Instance* instance, fmi2Real current_communication_point,
    fmi2Real communication_step_size);
fmi2Status Minimal_Scale_model_terminate(Minimal_Scale_Instance* instance);
fmi2Status Minimal_Scale_model_reset(Minimal_Scale_Instance* instance);
fmi2Status Minimal_Scale_model_free(Minimal_Scale_Instance* instance);
```

The generated stub's `do_step` returns `fmi2Error` on purpose: an unimplemented
model must fail loudly rather than pretend to step.

Requirements: a C++17 compiler (`g++`) and `fmpy` (`pip install -e ".[dev]"`).

The manual equivalent:

```bash
pyfmi model-description examples/c-runtime/minimal.sysml -o build/examples/c-runtime
pyfmi c-runtime examples/c-runtime/minimal.sysml -o build/examples/c-runtime
cp examples/c-runtime/Minimal_Scale_model.cpp build/examples/c-runtime/
g++ -std=c++17 -shared -fPIC \
  -I build/examples/c-runtime -I build/examples/c-runtime/fmi2 \
  build/examples/c-runtime/Minimal_Scale_fmi.cpp \
  build/examples/c-runtime/Minimal_Scale_model.cpp \
  -o build/examples/c-runtime/Scale.so
pyfmi package build/examples/c-runtime/Scale.fmu \
  --model-description build/examples/c-runtime/Scale/modelDescription.xml \
  --binary build/examples/c-runtime/Scale.so
```

The binary stem must equal the model identifier (`Scale`), and the archive name
is free — `pyfmi package` takes the output path explicitly.
