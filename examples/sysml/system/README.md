# One unit or all units from one architecture

`bench.sysml` declares three independent interop units — `ActuatorLink`,
`SensorLink`, and `Controller` — plus an unmarked `part def System` that
composes them. Each unit inherits the shared `FmuInterop` base and its
`InteropDeployment` parameter port. The container is not an FMU: one part
definition is one model, so the units are never merged into a single IR.

## Mode 1: package one unit

```bash
python examples/sysml/system/build_one.py \
  --unit SensorLink \
  --sysml examples/sysml/system/bench.sysml \
  --out /tmp/system/sensor \
  --serialization packed
```

`--unit` may be omitted when the architecture contains exactly one unit;
otherwise the script fails and lists the names. The architecture is loaded
once, then `model_from_architecture(arch, composition=unit, name=unit,
realtime=False)` selects that unit's interface. The output is:

```text
<out>/model/                  generated C++ sources, wire.json, model.json
<out>/build/                  CMake build tree and shared library
<out>/<unit>.fmu              the packaged FMU
```

## Mode 2: package every unit

```bash
python examples/sysml/system/build_all.py \
  --sysml examples/sysml/system/bench.sysml \
  --out /tmp/system/all \
  --serialization packed
```

`build_all.py` calls `pyfmi_interfaces.core.fmu_units(arch)` for the sorted
`:> FmuInterop` leaves, then runs the same generate/build/package step for
each one. Output is one directory per unit:

```text
<out>/<unit>/model/           generated sources for that unit
<out>/<unit>/build/           CMake build tree for that unit
<out>/<unit>/<unit>.fmu       packaged FMU, one message per unit
```

A missing unit list is an error, not an empty success.

## Parameters versus inputs

The inherited `InteropDeployment` port gives each unit FMI parameters
(`transport`, `bind_address`, `peer_address`). They are initialization-only:
the master binds them before `fmi2EnterInitializationMode`, they are never wire
fields, and changing them does not require a rebuild. Runtime behaviour
belongs in the unit's `in` ports, which become FMI inputs and wire `out`
fields. The `out` ports become FMI outputs and wire `in` fields.

Both scripts use the Python API directly; the `pyfmi-interop` CLI has no
`composition=`/`component=` option. Its `generate` command exports the
single selected unit and does not iterate over several.
