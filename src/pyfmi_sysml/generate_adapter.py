"""Artifact generation from an already parsed SysML model.

Generation never reloads the SysML source: every fact comes from the
:class:`~pyfmi_sysml.parse.ParsedModel` handle returned by
:func:`pyfmi_sysml.parse`.
"""

from __future__ import annotations

from pathlib import Path

from pyfmi_interop.core import (
    BuildConfig,
    adapter_from_reduction,
    write_adapter_tree,
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
    return write_adapter_tree(
        adapter,
        parsed.reduction,
        out_dir,
        prefix=options.prefix,
    )
