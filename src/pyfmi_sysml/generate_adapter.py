"""Artifact generation from an already parsed SysML model.

Generation never reloads the SysML source: every fact comes from the
:class:`~pyfmi_sysml.parse.ParsedModel` handle returned by
:func:`pyfmi_sysml.parse`.
"""

from __future__ import annotations

from pathlib import Path

from pyfmi_interop.core import BuildConfig
from pyfmi_interop.core.serialization.protobuf import render_proto
from pyfmi_interop.core.adapter import (
    _require_fmi_layer,
    _strip_default_experiment,
    _write,
    adapter_from_reduction,
    adapter_model_json,
    render_adapter_cmake,
    render_adapter_hooks,
    render_adapter_wire_json,
)
from pyfmi_sysml.parse import ParsedModel

__all__ = ["generate_adapter"]


def generate_adapter(
    parsed: ParsedModel,
    out_dir: str | Path,
    config: BuildConfig | None = None,
) -> Path:
    """Write the adapter source tree from an already parsed model.

    The source is never reloaded: every fact comes from ``parsed.reduction``
    and ``parsed.spec``.  ``config`` supplies the serialization backend, role
    and adapter prefix.
    """

    if not isinstance(parsed, ParsedModel):
        raise TypeError(
            "generate_adapter expects a ParsedModel, got "
            f"{type(parsed).__name__}; call parse() first"
        )
    options = config or BuildConfig()
    model = parsed.spec.to_model(options)
    adapter = adapter_from_reduction(
        parsed.reduction,
        model,
        component=parsed.unit,
        serialization=options.serialization,
        role=options.role,
        prefix=options.prefix,
    )

    helpers = _require_fmi_layer()
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)

    helpers["generate_c_runtime"](
        parsed.reduction,
        target,
        component=adapter.identifier,
        prefix=options.prefix,
    )
    helpers["generate_model_description"](
        parsed.reduction,
        target,
        component=adapter.identifier,
        generation_time=None,
    )
    # An adapter has no step to declare.  pyfmi_interfaces emits DefaultExperiment
    # when the composition authors start/stop control attributes; strip it so
    # the adapter document never advertises a fixed step.
    _strip_default_experiment(
        target / adapter.identifier / "modelDescription.xml"
    )

    _write(
        target / f"{adapter.stem}_model.cpp",
        render_adapter_hooks(adapter),
    )
    _write(target / "CMakeLists.txt", render_adapter_cmake(adapter))
    _write(target / "wire.json", render_adapter_wire_json(adapter))
    (target / "model.json").write_bytes(adapter_model_json(adapter))
    if adapter.serialization == "protobuf":
        _write(target / f"{adapter.wire_model.name}.proto", render_proto(adapter.wire_model))
    return target
