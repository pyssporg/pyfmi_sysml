# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-11-24

### Added

- Absorb the SysML ingestion and interop adapter flow from `pyfmi_interop`:
  `parse`, `load_model`, `load_architecture`, `model_from_architecture`,
  `model_from_sysml`, `ParsedModel`, `generate_adapter`,
  `adapter_from_reduction`, and the parser-free `Reduction` hand-off now live
  here.
- Re-export the `PyfmiInterop` vocabulary (`interop_definitions`,
  `load_with_interop`) from `pyssp_sysml_definitions`.
- Move the SysML examples and the interop sysml test suite into this package.

### Changed

- Generate the adapter from the interop core (`pyfmi_interop.core.adapter`);
  this package owns ingestion, not the wire plane.
- `generate_adapter` now uses interop's public `write_adapter_tree`; the private
  adapter imports (`_select_component`, `_require_fmi_layer`, `_write`,
  `_strip_default_experiment`) are gone.
- Attribute semantics moved to `pyfmi_interop.core.attributes`; `parse` only
  extracts plain values, and `DEFAULT_STEP_SIZE_S` / `DEFAULT_STRING_CAPACITY`
  are re-exported from interop.
- `load_with_interop` moved here from `pyssp_sysml_definitions`; the vocabulary
  package now ships paths only.
- Depend on `pyfmi-interop` at runtime; `pyfmi_interop` is now SysML-free.

## [0.1.0] - 2026-11-22

### Added

- Add `pyfmi_sysml`, the SysML composition layer: `to_reduction` loads through
  `pycps_sysml2` once and returns the parser-free `Reduction` that every
  `pyfmi_interfaces` emitter consumes.
- Move the reduction module wholesale from `pyfmi_interfaces`, keeping
  `to_reduction`, `components`, `component`, `component_interface`, `fmu_units`,
  `resolve_system`, `export_identity`, `direction_causality`, and
  `architecture`.
- Add the `pyfmi-sysml` console script with the four source-taking commands
  `model-description`, `c-headers`, `c-runtime`, and `modelica`, preserving
  their flags and output semantics.
- Add source-taking generator wrappers and the source-driven test suite,
  fixtures, goldens, Simulink prototype, iterative walkthrough, and examples.
