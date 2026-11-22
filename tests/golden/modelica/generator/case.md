# Case: `modelica/generator`

A direct FMU model with one output payload: the connector set is built from the
exported component itself, not from a container's leaves.

## Artifacts

Generated from `tests/fixtures/generator/generator.sysml`; every artifact path
is relative to this directory.

| Path | Kind |
| --- | --- |
| `GeneratedInterfaces/package.mo` | root package with the `Modelica` uses annotation |
| `GeneratedInterfaces/package.order` | `Interfaces`, `GeneratedInterfaces`, then per component `Generator_Interface` and `Generator` |
| `GeneratedInterfaces/Interfaces.mo` | eight primitive input/output connector aliases |
| `GeneratedInterfaces/GeneratedInterfaces.mo` | one undirected connector per port definition |
| `GeneratedInterfaces/Generator_Interface.mo` | generated `partial model` — parameters and connector instances |
| `GeneratedInterfaces/Generator.mo` | implementer-owned `model`, created once, never rewritten |

`case.md` is provenance, not a golden.

## What this case proves

- **Conversion:** `generator.sysml` (SysML v2) → the six Modelica package
  files under `GeneratedInterfaces/`.
- **Requirement / fault:** the direct export must contribute its own output
  port to the connector set, and the parameter interface must not leak into it;
  a missing `RealSignal` connector or a parameter connector is a fault.
- **Level:** component.
- **Input:** `tests/fixtures/generator/generator.sysml` (package `Generator`,
  definition `Generator`); synthetic and self-contained.
- **Expected:** the committed files listed under *Artifacts*.
- **Independent oracle:** `omc`, the OpenModelica compiler — `loadFile` on
  `package.mo` plus `checkModel` on both subpackages and on the generated
  `Generator_Interface` partial model (three successful checks); the generator
  and the fixture are this repository, the parser and checker are not.
- **Comparison:** exact bytes against the committed files, plus the `omc` gates
  in `tests/test_modelica.py::test_openmodelica_accepts_the_generated_packages`
  and `tests/test_modelica.py::test_openmodelica_builds_hand_written_logic_against_the_partial`
  (a hand-written model extending the partial must build; the untouched scaffold
  must fail with `Too few equations`).
- **Normalization:** none; the writer is a pure function of the parsed
  architecture and its arguments.
- **Volatile fields:** none.
- **Update policy:** `UPDATE_GOLDENS=1`, read the diff, commit fixture and
  goldens together; refused when `CI` is set.
- **Notes:** `GeneratorParameters :> ParameterInterface` is a parameter port and
  is excluded, leaving only `RealSignal`; the only usage is `out`, so the
  partial model emits an `output ... y` instance and the connector stays
  undirected.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-11-05 | Case added with the direct `FmuModel` fixture | Modelica coverage for the direct export pattern. |
| 2026-11-17 | Modelica seam: generated partial model and implementer-owned model | Iterative model development: interface generated, logic hand-written |
| 2026-11-17 | Case record reviewed | Artifact list and seam description verified against the committed package and `tests/test_modelica.py`. |
| 2026-11-17 | Direction restated on the partial model's instances | Connectors are undirected; the instance carries `input`/`output`. |
