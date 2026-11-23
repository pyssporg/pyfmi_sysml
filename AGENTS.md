# AGENTS

## Rules

1. **Don't assume. Surface tradeoffs.** If a contract is ambiguous, stop and say
   so rather than picking a behaviour silently.
2. **Minimum code that solves the problem.** Nothing speculative.
3. **Touch only what you must.** Clean up only your own mess.
4. **Define success criteria and verify.**

## Repository Focus

`pyfmi_sysml` is the SysML composition layer for the pyfmi artifact family. It
loads a SysML v2 architecture through `pycps_sysml2`, reduces once to the
parser-free `Reduction`, and calls the emitters in `pyfmi_interfaces`; it also
owns the interop adapter flow — `parse`, `ModelSpec`, and `generate_adapter`
over `pyfmi_interop`'s core.

- Modules: `parse`/reduction (the one parser entry), `load_*` and
  `model_from_*` (architecture and `ModelSpec` hand-offs), `generate_adapter`,
  and `cli` (`pyfmi-sysml`).
- Runtime dependencies: `pycps-sysml2`, `pyfmi-interfaces`, `pyfmi-interop`, and
  `pyssp-sysml-definitions`, all as plain specifiers.
- FMI XML, the wire plane, and the runtime belong to the two lower packages;
  packaging (`pyfmi package`) stays in `pyfmi_interfaces`.
- `README.md` and `CHANGELOG.md` are the public record; current contracts live in
  `docs/breakdown/` where a tree exists.

## Hard constraints

- **One parse.** A source is loaded once; `generate_adapter` consumes the
  resulting `ParsedModel` and never reloads the source or re-resolves the export
  unit.
- **One dialect owner.** SysML v2 is parsed by `pycps_sysml2.load`; never fork a
  parser, copy grammar, or import `sysmlpy` directly.
- **No wire plane, no runtime.** Emit the adapter tree through the public
  `pyfmi_interop.core` writer; do not add framing, transports, or scheduling
  here.
- **No hand-rolled FMI XML.** FMI documents come from
  `pyfmi_interfaces`/`pyssp_standard`, never from a private writer.
- **No model equations.** `user_step` and the model hooks are the implementer's
  place; this layer moves interfaces, not behaviour.
- **Source-taking commands live here.** `model-description`, `c-headers`,
  `c-runtime`, and `modelica` are `pyfmi-sysml`; `pyfmi package` stays in
  `pyfmi_interfaces`.

## Workspace rule

The workspace is this checkout. Sibling repositories — `pycps_sysml2`,
`pyssp_sysml2`, `pyfmi_interfaces`, `pyfmi_interop`,
`pyssp_sysml_definitions`, `pysos_sysml`, and the `pyssp_workflow` consumer —
are read-only unless the task explicitly names one. Never scan outside this
checkout to infer a contract, and never treat an installed copy as more
authoritative than the workspace source.

## Environment

- Python >= 3.11.
- Install: `python3 -m venv venv && . venv/bin/activate && pip install -e ".[dev]"`.
- Tests: `python -m pytest`; the default subset is `python -m pytest -m "not slow"`.
- Lint: `ruff check src tests`.
