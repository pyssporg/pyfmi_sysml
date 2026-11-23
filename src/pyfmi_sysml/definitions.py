"""Re-export the installable vocabulary and the composition's export selection.

The shared ``PysspCore`` and ``PyfmiInterop`` vocabularies ship with
:mod:`pyssp_sysml_definitions`, so a model author can install the definitions
without this package.  This module exposes the same vocabulary from the
composition layer's public surface and owns the one policy that decides when a
shared root joins a load: each vocabulary is an include root, and a package is
added only when the architecture imports it.  ``PysspCore`` is supplied when a
model imports ``PysspCore`` and ``PyfmiInterop`` when it imports
``PyfmiInterop``; a model that imports neither is loaded with the caller's
roots alone.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from pyssp_sysml_definitions import core_definitions, interop_definitions

__all__ = [
    "interop_definitions",
    "load_with_definitions",
    "load_with_interop",
]

#: Imported package name and the bundled vocabulary root it needs, core first.
_DEFINITION_ROOTS: tuple[tuple[str, Callable[[], Path]], ...] = (
    ("PysspCore", core_definitions),
    ("PyfmiInterop", interop_definitions),
)


def load_with_definitions(
    source: Any, load: Any, includes: Iterable[str | Path] = ()
) -> Any:
    """Load ``source`` plus caller roots, adding a vocabulary only when imported.

    ``includes`` are extra package roots the caller supplies (a library a model
    imports); they are passed to every load call so the first parse resolves
    those imports.  The bundled vocabularies are include roots, not definitions
    every model inherits.  ``pyfmi_interfaces`` selects an export unit by
    ``:> FmuModel``, so including a library in an architecture that never
    imports it would expose its definitions as candidates and change that
    model's composition.  The model declares ``PysspCore`` and ``PyfmiInterop``
    in its imports only when it wants the shared types, so each include is
    conditional on that declaration; an imported package root can make such a
    declaration visible too, so the check runs after the caller's roots are
    loaded.

    A vocabulary already supplied through ``includes`` is not added a second
    time: the loader merges roots and rejects a definition that comes from two
    included roots.  When nothing is missing the first load is returned, so a
    caller that passes the roots explicitly still loads the source once.

    ``load`` is injected by the caller, so this package keeps no parser
    dependency.
    """

    roots = tuple(includes)
    architecture = load(source, *roots)
    imported = getattr(architecture, "imports", {})
    present = {Path(root).resolve() for root in roots}
    missing = tuple(
        path
        for package, factory in _DEFINITION_ROOTS
        if package in imported
        for path in (factory(),)
        if path.resolve() not in present
    )
    if not missing:
        return architecture
    return load(source, *roots, *missing)


#: Kept as the stable public name.  It now supplies ``PysspCore`` as well as
#: ``PyfmiInterop``; :func:`load_with_definitions` is the name that says so.
load_with_interop = load_with_definitions
