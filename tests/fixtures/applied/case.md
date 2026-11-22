# Case: applied

The container side of the contract: a parameter set applied with `bind` and a
default experiment declared as a typed attribute container.

## Artifacts

- `applied.sysml`

**Conversion**: SysML v2 architecture -> `modelDescription.xml`
**Requirement / fault**: the applied set is compared metadata, not a value
source, so the parameter starts must stay the interface defaults (`1.0`, `2.5`)
and never become the set's (`9.0`, `9.5`); the experiment container must reach
the FMI `DefaultExperiment` element with `startTime`, `stopTime`, and
`stepSize`, and a composition without one must emit no element at all
**Level**: unit; the fixture is parsed input, not a generated artifact
**Input**: synthetic, authored for this repository; it mirrors the applied-set
and experiment shapes the dialect's typed containers exist for, with neutral
names only
**Expected**: package `Applied`, exported component `Scale`, four scalar
variables in value-reference order `0..3` — parameters `gains[0]` (`1.0`) and
`gains[1]` (`2.5`), then input `u` and output `y`;
`DefaultExperiment startTime="0.0" stopTime="10.0" stepSize="0.1"`; the
`tuned` and `defaults` attributes are authoring data and are not variables
**Independent oracle**: `pycps_sysml2.load` parses the file, and the FMI2 XSD
and semantic validator check the document
**Comparison**: assertions on the parsed document; this fixture has no golden
**Normalization**: none; parameters precede ports and the array is expanded in
declaration order
**Volatile fields**: none
**Update policy**: change the fixture and every affected assertion in one
commit; the fixture is read through `conftest.fixture_path`, never by a
working-directory path
**Notes**: the experiment belongs to the composition root that `resolve_system`
selects, not to the exported leaf. A plain `DefaultExperiment` may omit
`stepSize`, and then the FMI attribute is absent.
**Provenance**: synthetic, authored for this repository. It replaces the inline
model literal the tests used before the `pyssp_*` control tags were removed.

## What this case proves

That a typed experiment container is read by its type, that its three fields map
onto the FMI `DefaultExperiment` element, and that applying a parameter set
never changes a parameter start value.

## Update history

- 2026-11-19 — Fixture and record created while migrating off the retired
  `pyssp_default_start_time` / `pyssp_default_stop_time` tags.
