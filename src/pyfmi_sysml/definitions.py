"""Re-export the installable vocabulary and the composition's export selection.

The reusable ``PyfmiInterop`` vocabulary ships with
:mod:`pyssp_sysml_definitions`, so a model author can install the definitions
without this package.  This module exposes the same vocabulary from the
composition layer's public surface and owns the one policy that decides when
the interop root joins a load: the vocabulary is an include root, and the
``PyfmiInterop`` package is added only when the architecture imports it.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pyssp_sysml_definitions import interop_definitions

__all__ = ["interop_definitions", "load_with_interop"]


def load_with_interop(
    source: Any, load: Any, includes: Iterable[str | Path] = ()
) -> Any:
    """Load ``source`` plus caller roots, adding the library only when imported.

    ``includes`` are extra package roots the caller supplies (a library a model
    imports); they are passed to every load call so the first parse resolves
    those imports.  The bundled vocabulary is an include root, not a definition
    every model inherits.  ``pyfmi_interfaces`` selects an export unit by
    ``:> FmuModel``, so including the library in an architecture that never
    imports it would expose ``FmuInterop`` as a candidate and change that
    model's composition.  The model declares ``PyfmiInterop`` in its imports
    only when it wants the shared types, so the include is conditional on that
    declaration; an imported package root can make that declaration visible
    too, so the check runs after the caller's roots are loaded.

    ``load`` is injected by the caller, so this package keeps no parser
    dependency.
    """

    roots = tuple(includes)
    architecture = load(source, *roots)
    if "PyfmiInterop" not in getattr(architecture, "imports", {}):
        return architecture
    return load(source, *roots, interop_definitions())
