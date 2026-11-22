# Iterative development

The generated Modelica package is an interface plus a scaffold, not a model.
This walkthrough shows the loop the generator is built for: define the
interface, write the logic, change the architecture, regenerate, and let the
build point at exactly what the change broke.

Run it with the `pyfmi` console script and OpenModelica on `PATH`:

```bash
./run.sh
```

Override the tools when they are not on `PATH`:

```bash
PYFMI=/path/to/pyfmi OMC=/path/to/omc ./run.sh
```

## What the script does

| Stage | Input | Outcome |
| --- | --- | --- |
| 1 | `v1.sysml` + `logic.mo` | the hand-written `Scaler` model builds |
| 2 | `v2.sysml` (port `raw` renamed to `command`) | regenerate in place; `Scaler.mo` is untouched and the build fails |
| 3 | the same model, one local rename | builds again |
| 4 | `v3.sysml` (output member `clipped` added) | the build fails on the unbalanced member |

Stage 2 is the point. Regenerating rewrites the whole generated half in
`GeneratedInterfaces/`: `package.mo`, `package.order`, `Interfaces.mo`,
`GeneratedInterfaces.mo`, and `Scaler_Interface.mo`. It leaves `Scaler.mo`
byte-identical. The build then names `Scaler.mo` and reports:

```
Error: Variable raw.value not found in scope Scaler.
```

That is the file the implementer owns, named by the port they no longer have.
Stage 4 shows the structural change: adding a member does not break a name, it
breaks the balance, and `buildModel` reports `Too few equations` and names
`limited.clipped`.

Nothing here invokes a compiler through `pyfmi`: `omc` is the oracle, driven
from this script. `tests/test_iterative_example.py` runs the same script as a
`system` and `slow` test, and skips with a reason when `omc` is absent.

## Files

- `v1.sysml`, `v2.sysml`, `v3.sysml` — three revisions of one architecture;
- `logic.mo` — the hand-written model for revision 1, copied over the
  generated scaffold;
- `run.sh` — the walkthrough, self-checking: it exits non-zero if a stage does
  not fail where it should.
