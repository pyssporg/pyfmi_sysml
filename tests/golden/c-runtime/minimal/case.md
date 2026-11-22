# Case: c-runtime/minimal

The runtime bytes for the smallest legal component: one parameter, one input,
and one output, all Real.

## Artifacts

- `Minimal_Scale_fmi.cpp`
- `Minimal_Scale_hooks.h`
- `Minimal_Scale_model.cpp`

**Conversion**: SysML v2 architecture -> C interface headers -> C++17 FMI 2.0
CoSimulation runtime plus the user-owned model hook file
**Requirement / fault**: the generator must work with three variables and no
String or Boolean member; a runtime that only compiles when a `std::string` or
`bool` storage exists has no legal floor
**Level**: component; the generated translation unit is the unit under test
**Input**: `tests/fixtures/minimal/minimal.sysml`
**Expected**: the same generic runtime shape as the wider case, one parameter
entry in the value-reference switch, and `Minimal_Scale_VrCount == 3`
**Independent oracle**: `g++ -std=c++17 -fsyntax-only` and the linked harness
`tests/c_runtime_harness.cpp`, which exercises instantiation, GUID rejection,
type-correct access, output write refusal, and the placeholder step failure
**Comparison**: byte-for-byte against the golden text
**Normalization**: none; no clock, path, or environment value enters the bytes
**Volatile fields**: none
**Update policy**: `UPDATE_GOLDENS=1 python -m pytest
tests/test_c_runtime.py`; never under `CI`
**Notes**: the three `fmi2/` copies are compared byte-for-byte against the
bundled headers returned by `pyfmi_interfaces.core.fmi2_headers()`, not against a
golden. The C headers are the existing `tests/golden/c-headers/minimal/`
artifacts.

## What this case proves

That the runtime has a working floor and that its variable-independent plumbing
does not accidentally depend on a type the minimal component lacks.

## Update history

- 2026-11-17 — Initial golden for the C++17 runtime generator.
- 2026-11-17 — Bundled-header wording corrected; removed the stale interpreter
  path from the update policy.
