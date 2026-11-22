# model-description

Turn a SysML v2 architecture into FMI 2.0 XML: one document per exported leaf
part. No compiler, no packaging.

The input is this directory's own `thermal_plant.sysml`: a container root with
two leaf parts, `Sensor` and `Valve`. From the repository root:

```bash
python examples/model-description/build.py
```

The script pins the generation time, writes one document per leaf, and prints
every written path. The CLI equivalent:

```bash
pyfmi model-description examples/model-description/thermal_plant.sysml \
  -o build/examples/model-description
```

Either way, two documents are written:

```text
build/examples/model-description/Sensor/modelDescription.xml
build/examples/model-description/Valve/modelDescription.xml
```

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

`reference/` holds the checked-in output for both leaves. The generation time is
pinned, so it is byte-identical to a fresh run; diff your output against it:

```bash
diff -r examples/model-description/reference build/examples/model-description
```

Useful flags (the script and the CLI take the same ones):

- `--component Valve` writes only that leaf.
- `--generation-time 2000-01-01T00:00:00Z` pins the clock. The default is the
  epoch, so an unpinned run is already reproducible; a naive timestamp is
  refused.
- `--base-index 1` shifts array suffixes, for OMC-built Modelica FMUs.

Validate the documents with the same oracle the test suite uses:

```bash
python -c "import fmpy, glob; [fmpy.read_model_description(p) for p in glob.glob('build/examples/model-description/*/modelDescription.xml')]"
```
