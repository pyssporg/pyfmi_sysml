"""Source-taking generator wrappers: reduce once, then call the emitter.

The emitters in :mod:`pyfmi_interfaces` accept a parser-free
:class:`~pyfmi_interfaces.core.model.Reduction` only. These wrappers are the
composition seam: they resolve a SysML source, an already loaded architecture,
or an existing ``Reduction`` through :func:`pyfmi_sysml.reduction.to_reduction`
and forward the result to the matching emitter.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING

from pyfmi_interfaces import (
    generate_c_headers as _generate_c_headers,
    generate_c_runtime as _generate_c_runtime,
    generate_model_description as _generate_model_description,
    generate_modelica as _generate_modelica,
)
from pyfmi_interfaces.modelica.package import DEFAULT_PACKAGE
from pyfmi_sysml.reduction import to_reduction

if TYPE_CHECKING:
    from pycps_sysml2 import Architecture

    from pyfmi_interfaces import Reduction


def generate_model_description(
    source: Reduction | Architecture | str | PathLike[str],
    output_dir: Path | str,
    *,
    composition: str | None = None,
    component: str | None = None,
    generation_time: datetime | None = None,
    base_index: int = 0,
) -> list[Path]:
    """Write ``modelDescription.xml`` per component from a SysML source."""
    return _generate_model_description(
        to_reduction(source, composition=composition, base_index=base_index),
        output_dir,
        component=component,
        generation_time=generation_time,
    )


def generate_c_headers(
    source: Reduction | Architecture | str | PathLike[str],
    output_dir: Path | str,
    *,
    composition: str | None = None,
    component: str | None = None,
    prefix: str | None = None,
    base_index: int = 0,
) -> list[Path]:
    """Write the C interface headers from a SysML source."""
    return _generate_c_headers(
        to_reduction(source, composition=composition, base_index=base_index),
        output_dir,
        component=component,
        prefix=prefix,
    )


def generate_c_runtime(
    source: Reduction | Architecture | str | PathLike[str],
    output_dir: Path | str,
    *,
    composition: str | None = None,
    component: str | None = None,
    prefix: str | None = None,
    base_index: int = 0,
    omit: Sequence[str] | str = (),
) -> list[Path]:
    """Write the C headers and the C++17 FMI runtime from a SysML source."""
    return _generate_c_runtime(
        to_reduction(source, composition=composition, base_index=base_index),
        output_dir,
        component=component,
        prefix=prefix,
        omit=omit,
    )


def generate_modelica(
    source: Reduction | Architecture | str | PathLike[str],
    output_dir: str | Path,
    *,
    composition: str | None = None,
    package: str = DEFAULT_PACKAGE,
    within: str | None = None,
) -> list[Path]:
    """Write the Modelica interface package from a SysML source."""
    return _generate_modelica(
        to_reduction(source, composition=composition),
        output_dir,
        package=package,
        within=within,
    )
