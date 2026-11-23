# pyfmi_sysml

SysML ingestion for the FMI interface generators. Contributors read
[`AGENTS.md`](AGENTS.md).

`pyfmi_sysml` loads a SysML v2 architecture through
[`pycps_sysml2`](https://github.com/pyssporg/pycps_sysml2), reduces it once to
the parser-free `Reduction` defined by `pyfmi_interfaces`, and calls that
package's emitters. It also owns the interop adapter flow: `parse` extracts
attribute values from the reduction and maps them to a `ModelSpec`, and
`generate_adapter` emits the adapter tree through interop's public writer.
`load_with_interop` and the `PyfmiInterop` include policy live here, not in the
vocabulary package. The FMI interface model, its emitters, and `pyfmi package`
live in `pyfmi_interfaces`; `pyfmi_interop` owns the protobuf `ModelSpec` and the
adapter model on one versioned wire, and takes only its FMI facade from
`pyfmi_interfaces`. This package is the composition layer that owns the SysML
reader and the source-taking command line.

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
`--include PATH` (repeatable package root, appended in flag order), and
`-o/--output` (default `build/`). `--core-definitions` is sugar for one root:
it appends `pyssp_sysml_definitions.core_definitions()` after every `--include`.
Per command: `model-description` adds
`--component`, `--generation-time`, and `--base-index`; `c-headers` adds
`--component`, `--prefix`, and `--base-index`; `c-runtime` adds those plus
`--omit`; `modelica` adds `--package` and `--within`.

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
architecture, or an existing `Reduction`; a path source also accepts
`includes=[...]` package roots, which `architecture` and `to_reduction` take
too.

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

## Examples

Runnable walkthroughs live in [`examples/`](examples/README.md): one FMI XML
document per leaf, the Modelica package, a C++17 runtime compiled to a loadable
FMU, and the interop adapter. Each directory has its own README and writes only
under `build/`. Start with:

```bash
python examples/model-description/build.py
```

## Development

Install the dev extra as above, then:

```bash
./venv/bin/python -m pytest                    # everything
./venv/bin/python -m pytest -m "not slow"      # the default subset
./venv/bin/ruff check src tests
```

`pyproject.toml` carries the explicit ruff selection. Contributor rules, cross-
repository boundaries, and the one-parse contract are in
[`AGENTS.md`](AGENTS.md).
