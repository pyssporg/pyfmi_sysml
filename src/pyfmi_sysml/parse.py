"""Ingestion of a SysML v2 architecture into the public model specification.

The SysML dialect itself is owned by :mod:`pycps_sysml2`; the FMI variable
reduction is owned by :mod:`pyfmi_interfaces.core`.  This module only maps that
reduction onto :mod:`pyfmi_interop.core`, so parsing is never re-implemented
here.  ``pycps_sysml2`` and ``pyfmi_interfaces`` are runtime dependencies;
importing this module works without them, and calling :func:`parse` or the
compatibility helpers raises a :class:`RuntimeError` when they are missing.

A SysML source is parsed exactly once.  :func:`parse` returns a
:class:`ParsedModel` holding both the projected specification and the
parser-free ``pyfmi_interfaces.core.Reduction``;
:func:`pyfmi_sysml.generate_adapter` consumes that handle and never
reloads the source.

This module extracts plain attribute values from the reduction.  The spelling,
precedence, period heuristic, default step, type and causality maps, string
capacity, identifier rule and signal projection belong to
:mod:`pyfmi_interop.core.attributes`; no timing or FMI mapping rule is duplicated
here.  The system, component and port scopes are handed over as plain mappings,
and interop decides their precedence.

Timing and transport metadata are ordinary typed attributes.  On a port
definition the attribute must be typed by a dialect container marker (for
example an ``attribute def`` specializing ``ParameterSet``) so the FMI
reduction skips it instead of turning it into a signal field.  On a part
definition any resolved ``attribute def`` is enough; a flat untyped attribute
is rejected by the parameter dialect.

Transport attributes are not interpreted: the repository carries bytes, not
protocol bindings, so ``transport``, ``channel``, and ``transport_endpoint``
remain author metadata only.

String signals get ``DEFAULT_STRING_CAPACITY`` bytes so the runtime owns their
storage and never allocates inside the step loop.  ``pyfmi_interfaces.Variable``
carries neither a unit nor an explicit "absent" marker for the initial value,
so a signal without a ``unit`` attribute gets ``unit=None`` and ``initial`` is
exactly the variable's ``start``: the authored typed default for a parameter or
output, and the upstream neutral start for an input.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pyfmi_interop.core import (
    DEFAULT_STEP_SIZE_S,
    DEFAULT_STRING_CAPACITY,
    ModelSpec,
    data_type_from_name,
    direction_from_causality,
    ir,
    model_name,
    period_seconds_from_attributes,
    rate_hz_from_attributes,
    sanitize_identifier,
    select_component,
    signal_from_values,
    step_size_for_scopes,
    step_size_from_attributes,
    unit_from_attributes,
)
from pyfmi_interop.core.ir import deterministic_guid
from pyfmi_sysml.definitions import load_with_interop

if TYPE_CHECKING:
    from pyfmi_interfaces.core import Reduction

__all__ = [
    "DEFAULT_STEP_SIZE_S",
    "DEFAULT_STRING_CAPACITY",
    "ParsedModel",
    "load_architecture",
    "load_model",
    "model_from_architecture",
    "model_from_sysml",
    "parse",
]

_SYSML_EXTRA = 'the pyfmi_sysml dependencies: pip install "pyfmi-sysml"'


@dataclass(frozen=True)
class ParsedModel:
    """One SysML parse: the projected specification and the parser-free reduction."""

    spec: ModelSpec
    reduction: "Reduction"
    unit: str  # selected exported component name


def parse(
    source: str | Path,
    *,
    includes: Iterable[str | Path] = (),
    component: str | None = None,
    composition: str | None = None,
    name: str | None = None,
    step_size_s: float | None = None,
    realtime: bool = True,
) -> ParsedModel:
    """Parse ``source`` once and return the specification plus its reduction."""

    architecture = load_architecture(source, includes=includes)
    _, to_reduction = _require_sysml()
    reduction = to_reduction(architecture, composition=composition)
    unit = select_component(reduction, component)
    spec = _project_spec(
        reduction,
        [unit],
        name=name,
        step_size_s=step_size_s,
        realtime=realtime,
    )
    return ParsedModel(
        spec=spec,
        reduction=reduction,
        unit=unit.name,
    )


def load_architecture(
    source: str | Path,
    *,
    includes: Iterable[str | Path] = (),
) -> Any:
    """Load a SysML v2 file or directory into an ``Architecture``.

    ``includes`` are extra package roots (files or directories) merged into the
    load, so a model can import a library that defines its FMU base or the
    exported leaf itself.  The bundled ``PyfmiInterop`` library is added to the
    roots only when the architecture imports it, exactly as in
    :func:`load_model`.  Call this once to export several units from the same
    parse, passing each name to :func:`model_from_architecture` as
    ``composition=``.
    """

    pycps_sysml2, _ = _require_sysml()
    return load_with_interop(source, pycps_sysml2.load, includes=includes)


def load_model(
    source: str | Path,
    **kwargs: Any,
) -> ModelSpec:
    """Parse ``source`` and return its public specification."""

    return parse(source, **kwargs).spec


def model_from_sysml(
    source: str | Path,
    **kwargs: Any,
) -> ModelSpec:
    """Alias for :func:`load_model`: parse a SysML source to a ``ModelSpec``."""

    return load_model(source, **kwargs)


def model_from_architecture(
    architecture: Any,
    *,
    name: str | None = None,
    step_size_s: float | None = None,
    realtime: bool = True,
    composition: str | None = None,
) -> ModelSpec:
    """Reduce an already loaded architecture onto the public specification.

    ``composition`` selects the part definition whose components are exported;
    without it the reduction picks the single ``:> FmuModel`` leaf, or asks for
    a name when several leaves exist.  The architecture is reduced once and the
    projected specification reads only the parser-free reduction.  The model
    name defaults to the architecture's package name, sanitized to a C
    identifier.  Passing ``name`` keeps it verbatim so an invalid name is
    rejected by :class:`~pyfmi_interop.ir.ModelDefinition` instead of being
    silently rewritten.
    """

    _, to_reduction = _require_sysml()
    reduction = to_reduction(architecture, composition=composition)
    return _project_spec(
        reduction,
        list(reduction.components),
        name=name,
        step_size_s=step_size_s,
        realtime=realtime,
    )


# -- lazy dependencies -----------------------------------------------------


def _require_sysml():
    try:
        import pycps_sysml2
    except ImportError as error:
        raise RuntimeError(f"SysML ingestion requires {_SYSML_EXTRA}") from error
    from pyfmi_sysml.reduction import to_reduction

    return pycps_sysml2, to_reduction


# -- reduction lookups -----------------------------------------------------


def _model_name(reduction: Any, name: str | None) -> str:
    return model_name(reduction.package, reduction.root, name)


def _port_attributes(component: Any) -> dict[str, Mapping[str, object]]:
    return {
        group.name: _attributes(group.attributes) for group in component.ports
    }


def _attributes(pairs: Any | None) -> Mapping[str, object]:
    if pairs is None:
        return {}
    if isinstance(pairs, Mapping):
        return pairs
    return dict(pairs)


def _variable_attributes(
    variable: Any,
    component_attributes: Mapping[str, object],
    port_attributes: Mapping[str, Mapping[str, object]],
) -> Mapping[str, object]:
    for port_name, attributes in port_attributes.items():
        if variable.name == port_name or variable.name.startswith(f"{port_name}."):
            return {**component_attributes, **attributes}
    return component_attributes


# -- attribute normalization ----------------------------------------------


def _attribute_value(attributes: Mapping[str, object], name: str) -> object | None:
    """Raw value of ``name``; list-valued attributes keep their first element."""

    raw = attributes.get(name)
    if raw is None:
        return None
    value = getattr(raw, "value", raw)
    if isinstance(value, tuple):
        return value[0] if value else None
    return value


def _plain_attributes(attributes: Mapping[str, object]) -> dict[str, object]:
    """Extract plain values; attribute semantics belong to ``pyfmi_interop``."""

    return {name: _attribute_value(attributes, name) for name in attributes}


def _period_seconds_from_attributes(attributes: Mapping[str, object]) -> float | None:
    return period_seconds_from_attributes(_plain_attributes(attributes))


def _step_size_from_attributes(
    attributes: Mapping[str, object], explicit: float | None
) -> float:
    return step_size_from_attributes(_plain_attributes(attributes), explicit)


def _model_step_size(
    reduction: Any,
    components: list[Any],
    explicit: float | None,
) -> float:
    """Extract the scopes; ``pyfmi_interop`` owns their precedence."""

    system = _plain_attributes(_attributes(reduction.attributes))
    component_scopes = [
        _plain_attributes(_attributes(component.attributes))
        for component in components
    ]
    port_scopes = [
        _plain_attributes(attributes)
        for component in components
        for attributes in _port_attributes(component).values()
    ]
    return step_size_for_scopes(
        system, component_scopes, port_scopes, explicit=explicit
    )


def _rate_hz_from_attributes(attributes: Mapping[str, object]) -> float | None:
    return rate_hz_from_attributes(_plain_attributes(attributes))


# -- variable mapping ------------------------------------------------------


def _data_type(type_name: str) -> ir.DataType:
    return data_type_from_name(type_name)


def _direction(causality: str) -> ir.Direction:
    return direction_from_causality(causality)


def _signal_from_variable(
    variable: Any,
    *,
    rate_hz: float | None,
    unit: str | None,
) -> ir.Signal:
    return signal_from_values(
        name=variable.name,
        type_name=variable.type_name,
        causality=variable.causality,
        value_reference=variable.value_reference,
        start=variable.start,
        rate_hz=rate_hz,
        unit=unit,
    )


def _identifier(text: str) -> str:
    return sanitize_identifier(text)


def _project_spec(
    reduction: Any,
    selected: list[Any],
    *,
    name: str | None,
    step_size_s: float | None,
    realtime: bool,
) -> ModelSpec:
    """Project the selected components onto one public specification."""

    model_name = _model_name(reduction, name)
    step_size = _model_step_size(reduction, selected, step_size_s)

    signals: list[ir.Signal] = []
    for component in selected:
        component_attributes = _attributes(component.attributes)
        port_attributes = _port_attributes(component)

        for variable in component.variables:
            attributes = _variable_attributes(
                variable, component_attributes, port_attributes
            )
            rate_hz = _rate_hz_from_attributes(attributes)
            signals.append(
                _signal_from_variable(
                    variable,
                    rate_hz=rate_hz,
                    unit=unit_from_attributes(_plain_attributes(attributes)),
                )
            )

    # The payload message is named after the part definition whose interface
    # the model carries.  A container that combines several exported components
    # has no single part definition, so the message falls back to the model name.
    interface = selected[0].name if len(selected) == 1 else None
    return ModelSpec(
        name=model_name,
        guid=deterministic_guid(model_name),
        step_size_s=step_size,
        realtime=realtime,
        signals=ir.assign_value_references(signals),
        interface=interface,
    )
