# Case: `modelica/controller`

Mixed primitives on both sides: an `Integer` member inside an input `Command`
and a `Boolean` member inside an output `Throttle`.

- **Conversion:** `controller.sysml` (SysML v2) → `GeneratedInterfaces/package.mo`,
  `GeneratedInterfaces/package.order`, `GeneratedInterfaces/Interfaces.mo`,
  `GeneratedInterfaces/GeneratedInterfaces.mo`,
  `GeneratedInterfaces/Controller_Interface.mo`,
  `GeneratedInterfaces/Controller.mo`
- **Requirement / fault:** the connector member type must be the FMI primitive,
  not a stringified SysML type, and direction belongs on the partial model's
  port instance, never on the undirected connector. A generator that emits
  `Real` for every member, or that omits `output` on the `throttle` instance,
  produces a package that still loads — the fault only shows up when a tool
  wires the instance.
- **Level:** component
- **Input:** `tests/fixtures/controller/controller.sysml` (package `Controller`,
  composition `ControllerComposition`); no external source, no licence obligation
- **Expected:** the committed files listed under *Artifacts*
- **Independent oracle:** `omc`, the OpenModelica compiler — `loadFile` on
  `package.mo` plus `checkModel` on both subpackages and on the generated
  `Controller_Interface` partial model (three successful checks). This case was
  verified with `OpenModelica 1.26.1` (`/usr/bin/omc`). The generator is this
  repository; the parser and checker are not.
- **Comparison:** exact bytes against the committed file, plus the `omc` gates in
  `tests/test_modelica.py::test_openmodelica_accepts_the_generated_packages` and
  `tests/test_modelica.py::test_openmodelica_builds_hand_written_logic_against_the_partial`
  (a hand-written model extending the partial must build; the untouched scaffold
  must fail with `Too few equations`)
- **Normalization:** none; the writer is a pure function of the parsed
  architecture and its arguments, with no clock, hash seed, or environment input
- **Volatile fields:** none
- **Update policy:** `UPDATE_GOLDENS=1`, read the diff, commit fixtures and
  goldens together; refused when `CI` is set
- **Notes:** the parameter port (`ControllerParameters`, with a `Real[2]` and a
  `String`) is not a signal port and correctly produces no connector; its values
  appear as `parameter` declarations in `Controller_Interface`. The `omc` gate is
  marked `slow` (about 1 s, one `omc` invocation each); the text
  golden above is the default CI gate.

## Artifacts

Generated from `tests/fixtures/controller/controller.sysml`; every artifact path
is relative to this directory.

| Path | Kind |
| --- | --- |
| `GeneratedInterfaces/package.mo` | root package with the `Modelica` uses annotation |
| `GeneratedInterfaces/package.order` | `Interfaces`, `GeneratedInterfaces`, then per component `Controller_Interface` and `Controller` |
| `GeneratedInterfaces/Interfaces.mo` | eight primitive input/output connector aliases |
| `GeneratedInterfaces/GeneratedInterfaces.mo` | one undirected connector per port definition |
| `GeneratedInterfaces/Controller_Interface.mo` | generated `partial model` — parameters and connector instances |
| `GeneratedInterfaces/Controller.mo` | implementer-owned `model`, created once, never rewritten |

`case.md` is provenance, not a golden.

## What this case proves

If this case is deleted, a regression that flattens every member to `Real`, or
that loses the `input `/`output ` prefix on a single-direction instance, still
passes the minimal and sensor cases only if those happen to carry the same type
mix — they do not: neither has an `output Integer`. This is the case that keeps
the primitive-type mapping and the instance prefix together.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-11-05 | Case added with the generator | U3.4: Modelica interface package |
| 2026-11-17 | Modelica seam: generated partial model and implementer-owned model | Iterative model development: interface generated, logic hand-written |
| 2026-11-17 | Case record reviewed | Artifact list and seam description verified against the committed package and `tests/test_modelica.py`. |
| 2026-11-17 | Direction restated on the partial model's instances | Connectors are undirected; the instance carries `input`/`output`. |
