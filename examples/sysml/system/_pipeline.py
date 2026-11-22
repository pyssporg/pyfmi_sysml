"""Shared generate/build/package step for the multi-unit system example.

Both scripts export one FMU per ``:> FmuInterop`` unit and never merge several
units into one IR.  Keeping the packaging block here means ``build_one.py`` and
``build_all.py`` cannot drift in how they call ``package_fmu`` on the
``psysml2`` FMI layer.
"""

from __future__ import annotations

import importlib
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pyfmi_interop import build_model, package_fmu
from pyfmi_interop.core import BuildConfig
from pyfmi_interop.packaging import platform_binary_dir
from pyfmi_interop.core import load_adapter_model, wire_model_from_adapter_json
from pyfmi_sysml import ParsedModel, generate_adapter, model_from_architecture

#: Retry window for a parallel update that has not exposed ``fmu_units`` yet.
_UNIT_RETRIES = 20
_UNIT_RETRY_DELAY_S = 0.25


def fmu_unit_names(architecture: Any) -> list[str]:
    """Every exportable ``:> FmuModel`` leaf, sorted by name.

    The enumeration is owned by ``pyfmi_interfaces.core.fmu_units``.  A parallel
    change may still be landing while this example runs, so a missing symbol is
    retried briefly instead of failing on the first import.
    """

    module = importlib.import_module("pyfmi_interfaces.core")
    for attempt in range(_UNIT_RETRIES):
        unit_function = getattr(module, "fmu_units", None)
        if unit_function is not None:
            return [definition.name for definition in unit_function(architecture)]
        if attempt + 1 < _UNIT_RETRIES:
            time.sleep(_UNIT_RETRY_DELAY_S)
            module = importlib.reload(module)
    raise RuntimeError(
        "pyfmi_interfaces.core.fmu_units is not available; update pyfmi_interfaces to "
        "a revision that enumerates FmuInterop leaves"
    )


def build_unit(
    architecture: Any,
    unit: str,
    out_dir: str | Path,
    *,
    serialization: str = "protobuf",
    includes: Iterable[str | Path] = (),
) -> tuple[Any, Path, Path]:
    """Generate, build and package one unit under ``out_dir``.

    The model is the unit's own interface (``composition=unit``), never the
    container that composes it.  Returns ``(model, model_dir, fmu_path)``.
    """

    root = Path(out_dir)
    model_dir = root / "model"
    build_dir = root / "build"

    model = model_from_architecture(
        architecture,
        composition=unit,
        name=unit,
        realtime=False,
    )
    from pyfmi_interfaces.core import to_reduction

    parsed = ParsedModel(
        spec=model,
        reduction=to_reduction(architecture, composition=unit),
        unit=unit,
    )
    generate_adapter(
        parsed,
        model_dir,
        BuildConfig(serialization=serialization),
    )
    library = build_model(model_dir, build_dir=build_dir)
    fmu_path = package_psysml2(model_dir, library, root / f"{unit}.fmu")
    return model, model_dir, fmu_path


def package_psysml2(model_dir: str | Path, library: str | Path, fmu_path: str | Path) -> Path:
    """Package a ``psysml2`` adapter tree exactly as the adapter example does."""

    directory = Path(model_dir)
    payload = load_adapter_model(directory)
    effective = wire_model_from_adapter_json(payload)
    platform = platform_binary_dir()
    extra = {
        f"binaries/{platform}/wire.json": (directory / "wire.json").read_bytes()
    }
    proto = directory / f"{effective.name}.proto"
    if proto.is_file():
        extra[f"binaries/{platform}/{proto.name}"] = proto.read_bytes()
    return package_fmu(
        directory,
        library,
        fmu_path,
        model=effective,
        model_description=(
            directory / effective.interface / "modelDescription.xml"
        ).read_text(encoding="utf-8"),
        model_json=(directory / "model.json").read_bytes(),
        model_name=payload["model_name"],
        extra_entries=extra,
        include_schema=False,
    )
