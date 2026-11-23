# pyfmi_sysml

SysML ingestion for the FMI interface generators. Contributors read `AGENTS.md`.

`pyfmi_sysml` loads a SysML v2 architecture through
[`pycps_sysml2`](https://github.com/pyssporg/pycps_sysml2), reduces it once to
the parser-free `Reduction` defined by `pyfmi_interfaces`, and calls that
package's emitters. It also owns the interop adapter flow: `parse` extracts
attribute values from the reduction and maps them to a `ModelSpec`, and
`generate_adapter` emits the adapter tree through interop's public writer.
`load_with_interop` and the `PyfmiInterop` include policy live here, not in the
vocabulary package. The FMI interface model and its emitters live in
`pyfmi_interfaces`; the SysML-free generator, runtime, and packager live in
`pyfmi_interop`; this package is the composition layer that owns the SysML
reader and the source-taking command line. FMI packaging (`pyfmi package`) stays
in `pyfmi_interfaces`.

## Install

`pyfmi_sysml` requires Python 3.11 or newer and depends on `pycps-sysml2`,
`pyfmi-interfaces`, `pyfmi-interop`, and `pyssp-sysml-definitions`.

```bash
python3 -m venv venv
./venv/bin/pip install -e ".[dev]"
```

## CLI

`pyfmi-sysml` has four source-taking commands:

- `model-description` — write `modelDescription.xml` per component
- `c-headers` — write the C interface headers
- `c-runtime` — write the C headers and the C++17 FMI runtime
- `modelica` — write the Modelica interface package

Each accepts a `.sysml` file or a directory of them, `--composition`,
`-o/--output` (default `build/`), and the per-artifact flags it had before the
ownership move (`--component`, `--prefix`, `--omit`, `--package`, `--within`,
`--generation-time`, `--base-index`).

```text
usage: pyfmi-sysml [-h] COMMAND ...
```

## Library

```python
from pyfmi_sysml import to_reduction

reduction = to_reduction("model.sysml")
```

The same public reduction names are available: `to_reduction`, `components`,
`component`, `component_interface`, `fmu_units`, `resolve_system`,
`export_identity`, `direction_causality`, and `architecture`. The four
source-taking wrappers mirror the emitter names and accept a source, an
architecture, or an existing `Reduction`.

The interop adapter path parses once and never reloads the source:

```python
from pyfmi_sysml import generate_adapter, parse

parsed = parse("model.sysml")
target = generate_adapter(parsed, "build/adapter")
```

Also exported: `load_model`, `load_architecture`, `model_from_architecture`,
`model_from_sysml`, `ParsedModel`, `adapter_from_reduction`,
`interop_definitions`, `load_with_interop`, `DEFAULT_STEP_SIZE_S`, and
`DEFAULT_STRING_CAPACITY`.
