"""Re-export the installable shared SysML vocabulary.

The reusable ``PyfmiInterop`` vocabulary ships with
:mod:`pyssp_sysml_definitions`, so a model author can install the definitions
without this package. This module exposes the same names from the composition
layer's public surface.
"""

from __future__ import annotations

from pyssp_sysml_definitions import interop_definitions, load_with_interop

__all__ = ["interop_definitions", "load_with_interop"]
