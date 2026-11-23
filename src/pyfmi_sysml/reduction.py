"""Reduction of a SysML architecture onto the FMI interface it must expose.

Every generator in ``pyfmi_interfaces`` consumes the parser-free result of this
module, so that the modelDescription, the C headers, and the Modelica connectors
cannot disagree about *which* variables exist. The reduction follows the
``pyssp_sysml2`` v0.3.0 FMI policy:

- parameters come from the parameter dialect only (``in port parameters ...``),
  never from flat part attributes, and keep their interface defaults;
- a parameter list is expanded into one scalar per element, named
  ``<name>[<index>]``; the index base is configurable through ``base_index``
  (0 by default, 1 targets OMC-built Modelica FMUs, which declare arrays
  one-based);
- a port whose only member is a non-array ``value`` is named after the port
  alone (``y``), matching the SSP connector; every other port field is named
  ``<port>.<field>`` and expanded the same way;
- value references restart at 0 for every component, parameters first, then
  ports in declaration order and fields in declaration order.

FMI 2.0 has no array variable and no bidirectional scalar, so an ``inout`` or
undirected port becomes an input and the Modelica connector keeps the
direction out of the signal declaration.
"""

from __future__ import annotations

from collections.abc import Iterable
from functools import cache
from os import PathLike
from typing import TYPE_CHECKING

from pyfmi_interfaces.core.model import (
    Component,
    Experiment,
    ExportIdentity,
    Field,
    PortGroup,
    Reduction,
    Variable,
)
from pyfmi_interfaces.core.spelling import DISCRETE_TYPES, INPUT_START

if TYPE_CHECKING:
    from pycps_sysml2 import (
        Architecture,
        Attribute,
        PartDefinition,
        PortDefinition,
    )


@cache
def _container_kinds() -> frozenset[object]:
    """Attribute kinds that are typed containers, never FMI signal fields.

    The enum lives in the dialect, so it is read on first use rather than at
    import time: a generator that only consumes a :class:`Reduction` never
    imports ``pycps_sysml2``.
    """
    from pycps_sysml2.parameters import AttributeKind

    return frozenset(
        {
            AttributeKind.FMU_METADATA,
            AttributeKind.SSP_METADATA,
            AttributeKind.SOURCED_METADATA,  # family metadata: no FMI slot
            AttributeKind.PARAMETER_SET,
            AttributeKind.EXPERIMENT,
        }
    )


def architecture(
    source: Architecture | str | PathLike[str],
    *,
    includes: Iterable[str | PathLike[str]] = (),
) -> Architecture:
    """An already loaded architecture, or the one at ``source``.

    ``includes`` are extra package roots (files or directories) merged into the
    load, so a model can import a library that defines its FMU base or the
    exported leaf itself.  They apply only when ``source`` must be loaded: an
    already loaded architecture is returned unchanged and a non-empty
    ``includes`` is refused rather than silently dropped.  The bundled
    ``PysspCore`` and ``PyfmiInterop`` libraries join the roots only when the
    architecture imports them, the same policy as
    :func:`pyfmi_sysml.load_architecture`.
    """
    from pycps_sysml2 import Architecture, load

    from pyfmi_sysml.definitions import load_with_definitions

    roots = tuple(includes)
    if isinstance(source, Architecture):
        if roots:
            raise ValueError(
                "includes apply only when loading a source; the given "
                "architecture is already loaded"
            )
        return source
    return load_with_definitions(source, load, includes=roots)


def _start_text(type_name: str, value: object | None) -> str | None:
    """The formatted ``start`` text, or ``None`` when no default was authored."""
    if value is None:
        return None
    from pycps_sysml2.core import format_value

    return format_value(type_name, value)


def direction_causality(direction: str | None) -> str:
    """FMI causality for a SysML port direction.

    FMI 2.0 CoSimulation has no bidirectional scalar variable, so ``inout`` and
    an undirected port are exposed as inputs.
    """
    return "output" if direction == "out" else "input"


def _fixed_count(multiplicity: str | None, value: object) -> int | None:
    """Declared element count for a field, or ``None`` for a scalar."""
    if multiplicity:
        text = multiplicity
        if ".." in text:
            lower, upper = text.split("..", 1)
            if lower != upper:
                raise ValueError(
                    f"Variable multiplicity '[{text}]' is not a fixed length; "
                    "FMI 2.0 needs one scalar per element"
                )
            text = lower
        try:
            return int(text)
        except ValueError:
            raise ValueError(
                f"Unsupported multiplicity '[{multiplicity}]'"
            ) from None
    if isinstance(value, tuple):
        return len(value)
    return None


def _field_dtype(attribute: Attribute) -> str:
    from pycps_sysml2.core import map_fmi_type

    return map_fmi_type(attribute.primitive_type_str())


def _is_signal_port(
    architecture: Architecture, definition: PortDefinition | None
) -> bool:
    """True for a port that carries FMI signal fields, not parameters."""
    if definition is None:
        return False
    from pycps_sysml2.parameters import is_parameter_interface

    return not is_parameter_interface(architecture, definition)


def _is_scalar_port(
    architecture: Architecture, definition: PortDefinition
) -> bool:
    """True for a port that names one FMI variable rather than a group.

    Same predicate as ``pyssp_sysml2``: the loader normalizes a connector
    without a dot to a port with one member named ``value``, and the SSP
    exporter names that connector after the port. An array-valued ``value`` is
    deliberately not scalar: FMI expands it into ``<port>.value[<index>]``
    scalars, which one bare connector cannot carry (the SSP exporter refuses
    that shape instead of flattening it). Inherited members count, so a derived
    port definition that only adds fields is still not scalar.
    """
    from pycps_sysml2 import effective_members

    members = effective_members(architecture, definition).attributes
    if tuple(members) != ("value",):
        return False
    attribute = members["value"]
    return _fixed_count(attribute.multiplicity, attribute.value) is None


def component_interface(
    architecture: Architecture,
    part_def: PartDefinition,
    *,
    base_index: int = 0,
) -> Component:
    """Build the FMI interface of one leaf part definition.

    ``base_index`` shifts the ``[i]`` suffixes of every array member; the
    default 0 keeps the FMI convention, 1 targets OMC-built Modelica FMUs.
    """
    from pycps_sysml2 import effective_members
    from pycps_sysml2.parameters import (
        SSP_POLICY,
        classify_attribute,
        parameter_declarations,
        parameter_items,
    )

    parameters: list[Field] = []
    variables: list[Variable] = []
    counter = 0

    for attribute in parameter_declarations(architecture, part_def):
        type_name = _field_dtype(attribute)
        items = parameter_items(attribute, base_index=base_index)
        count = len(items)
        array = count if count > 1 or attribute.multiplicity else None
        parameters.append(Field(attribute.name, type_name, array, base_index))
        for position, item in enumerate(items):
            counter += 1
            # The FMI name is offset by base_index; the C member is not.
            member = (
                item.name
                if array is None
                else f"{attribute.name}[{position}]"
            )
            start = item.value
            variables.append(
                Variable(
                    name=item.name,
                    type_name=type_name,
                    causality="parameter",
                    variability="fixed",
                    value_reference=counter - 1,
                    index=counter,
                    description=attribute.doc,
                    member=member,
                    start=start,
                    start_text=_start_text(type_name, start),
                )
            )

    ports: list[PortGroup] = []
    for name, usage in effective_members(architecture, part_def).ports.items():
        definition = architecture.resolve_port(usage)
        if definition is None:
            raise ValueError(
                f"Unresolved port definition for {part_def.name}.{name}"
            )
        if not _is_signal_port(architecture, definition):
            continue
        scalar = _is_scalar_port(architecture, definition)
        member_directions: list[str | None] = []
        fields: list[Field] = []
        port_attributes = effective_members(architecture, definition).attributes
        for attribute in port_attributes.values():
            if (
                classify_attribute(architecture, attribute, policy=SSP_POLICY)
                in _container_kinds()
            ):
                continue
            member_direction = usage.effective_member_direction(attribute)
            member_directions.append(member_direction)
            causality = direction_causality(member_direction)
            type_name = _field_dtype(attribute)
            array = _fixed_count(attribute.multiplicity, attribute.value)
            fields.append(Field(attribute.name, type_name, array, base_index))
            for suffix, member in fields[-1].members():
                counter += 1
                start = (
                    INPUT_START[type_name] if causality == "input" else None
                )
                variables.append(
                    Variable(
                        name=(
                            name
                            if scalar
                            else f"{name}.{attribute.name}{suffix}"
                        ),
                        type_name=type_name,
                        causality=causality,
                        variability=(
                            "discrete" if type_name in DISCRETE_TYPES else None
                        ),
                        value_reference=counter - 1,
                        index=counter,
                        description=(
                            attribute.doc or usage.doc or definition.doc
                        ),
                        member=f"{name}.{member}",
                        start=start,
                        start_text=_start_text(type_name, start),
                    )
                )
        if member_directions and all(
            direction == member_directions[0] for direction in member_directions
        ):
            port_direction = member_directions[0]
        else:
            port_direction = usage.direction if not member_directions else None
        ports.append(
            PortGroup(
                name=name,
                definition=definition.name,
                direction=port_direction,
                causality=direction_causality(port_direction),
                fields=tuple(fields),
                doc=usage.doc or definition.doc,
                attributes=tuple(
                    (attribute.name, attribute.value)
                    for attribute in port_attributes.values()
                ),
            )
        )

    return Component(
        name=part_def.name,
        doc=part_def.doc,
        parameters=tuple(parameters),
        ports=tuple(ports),
        variables=tuple(variables),
        attributes=tuple(
            (attribute.name, attribute.value)
            for attribute in part_def.attributes.values()
        ),
    )


def export_identity(
    architecture: Architecture, system: PartDefinition
) -> ExportIdentity:
    """The naming rule for the export unit ``resolve_system`` selected."""
    from pycps_sysml2.metadata.roles import is_fmu_model

    return ExportIdentity(system.name, is_fmu_model(architecture, system))


def _fmu_leaves(
    architecture: Architecture, candidates: list[PartDefinition]
) -> list[PartDefinition]:
    """Drop every candidate that another candidate specializes.

    A shared base such as ``FmuInterop :> FmuModel`` makes every model that
    imports it a candidate transitively. Selection belongs to the FMI export
    unit, not to the dialect, so such a base is a role rather than an export
    unit: only candidates no other candidate specializes remain. Ancestry
    follows ``specializes`` through ``resolve_part``; the visited set holds
    package-qualified stored keys, which keeps the walk cycle-safe and two
    packages that reuse a bare name apart.

    A definition an included package owns is still a candidate: a library may
    define the FMU another model packages, and the candidate is selected by
    the same rule.
    """
    keys = {architecture.stored_key(definition) for definition in candidates}
    ancestors: set[str] = set()
    for definition in candidates:
        owned = architecture.stored_key(definition)
        seen: set[str] = set()
        pending = list(definition.specializes)
        while pending:
            base = architecture.resolve_part(pending.pop())
            if base is None:
                continue
            key = architecture.stored_key(base)
            if key in seen:
                continue
            seen.add(key)
            if key in keys and key != owned:
                ancestors.add(key)
            pending.extend(base.specializes)
    return [
        definition
        for definition in candidates
        if architecture.stored_key(definition) not in ancestors
    ]


def _fmu_candidates(architecture: Architecture) -> list[PartDefinition]:
    """Every part definition marked ``:> FmuModel``, the marker excluded."""
    from pycps_sysml2.metadata.helpers import short_name
    from pycps_sysml2.metadata.roles import FMU_MODEL_MARKER, is_fmu_model

    return [
        definition
        for definition in architecture.part_definitions.values()
        if is_fmu_model(architecture, definition)
        and short_name(definition.name) != FMU_MODEL_MARKER
    ]


def fmu_units(architecture: Architecture) -> list[PartDefinition]:
    """Every exportable ``:> FmuModel`` leaf definition, sorted deterministically.

    This is the line-up ``resolve_system`` chooses from when ``composition=``
    is omitted, exposed for a caller that exports each unit in turn: shared role
    bases are dropped, the ``FmuModel`` marker is never included, and several
    siblings are returned instead of refused. Sorting on the bare name first
    and the stored key second keeps equal names in different packages stable.
    Pass each name back as ``components(architecture, composition=...)``.
    """
    return sorted(
        _fmu_leaves(architecture, _fmu_candidates(architecture)),
        key=lambda definition: (
            definition.name,
            architecture.stored_key(definition),
        ),
    )


def resolve_system(
    architecture: Architecture, composition: str | None = None
) -> PartDefinition:
    """The part definition whose components are exported.

    ``composition`` names it explicitly, which may be a base definition.
    Without a name, a part definition marked ``:> FmuModel`` is the export unit
    itself; a candidate that another candidate specializes is a shared role
    base and does not count, and several remaining leaves must name one. When
    none is marked, the single part definition that has parts and is not used
    as a part elsewhere is taken; an architecture with several such roots must
    name one.
    """
    from pycps_sysml2 import effective_members
    from pycps_sysml2.metadata.roles import FMU_MODEL_MARKER

    if composition is not None:
        return architecture.get_part_def(composition)

    fmu_models = _fmu_leaves(architecture, _fmu_candidates(architecture))
    if fmu_models:
        if len(fmu_models) == 1:
            return fmu_models[0]
        names = ", ".join(sorted(definition.name for definition in fmu_models))
        raise ValueError(
            "Cannot pick a composition root; "
            f"{len(fmu_models)} {FMU_MODEL_MARKER} candidates ({names}). "
            "Pass composition=."
        )

    used: set[str] = set()
    for definition in architecture.part_definitions.values():
        for usage in effective_members(architecture, definition).parts.values():
            resolved = architecture.resolve_part(usage)
            if resolved is not None:
                used.add(architecture.stored_key(resolved))
    roots = [
        definition
        for definition in architecture.part_definitions.values()
        if effective_members(architecture, definition).parts
        and architecture.stored_key(definition) not in used
    ]
    if len(roots) != 1:
        names = ", ".join(sorted(definition.name for definition in roots))
        raise ValueError(
            "Cannot pick a composition root; "
            f"{len(roots)} candidates ({names or 'none'}). Pass composition=."
        )
    return roots[0]


def _component_definitions(
    architecture: Architecture, system: PartDefinition
) -> list[PartDefinition]:
    """Unique part definitions reachable from ``system``, in path order.

    The walk reads the effective member view, so a derived composition exports
    the parts it inherits, not only the ones it declares. Stored keys, not bare
    names, keep two packages that declare the same name apart.
    """
    definitions: list[PartDefinition] = []
    seen: set[str] = set()
    from pycps_sysml2 import effective_members

    def walk(
        part_def: PartDefinition,
        prefix: tuple[str, ...],
        ancestors: frozenset[str],
    ) -> None:
        for usage in effective_members(architecture, part_def).parts.values():
            path = prefix + (usage.name,)
            child = architecture.resolve_part(usage)
            if child is None:
                raise ValueError(
                    f"Unresolved part definition for {'.'.join(path)}"
                )
            key = architecture.stored_key(child)
            if key not in seen:
                seen.add(key)
                definitions.append(child)
            if effective_members(architecture, child).parts:
                if key in ancestors:
                    raise ValueError(
                        "Recursive part hierarchy at "
                        f"'{'.'.join(path)}' ({key})"
                    )
                walk(child, path, ancestors | {key})

    walk(system, (), frozenset({architecture.stored_key(system)}))
    return definitions


def _experiment(
    architecture: Architecture, system: PartDefinition
) -> Experiment | None:
    """The composition's experiment container in FMI terms, or ``None``."""
    from pycps_sysml2.metadata.roles import read_experiment

    experiment = read_experiment(architecture, system, required=False)
    if experiment is None:
        return None
    return Experiment(
        start_time=experiment.start_time,
        stop_time=experiment.stop_time,
        tolerance=experiment.tolerance,
        step_size=experiment.step_size,
    )


def to_reduction(
    source: Reduction | Architecture | str | PathLike[str],
    *,
    composition: str | None = None,
    base_index: int = 0,
    includes: Iterable[str | PathLike[str]] = (),
) -> Reduction:
    """Reduce an architecture, or return the ``Reduction`` already given.

    This is the only place that reads the SysML dialect. Every artifact
    generator calls it once and then works on the parser-free result, so a
    caller that already holds a :class:`Reduction` runs the generators without
    ``pycps_sysml2`` being imported.

    ``includes`` are extra package roots merged into the load when ``source`` is
    a path; the root is loaded exactly once.  An already loaded architecture or
    reduction is not re-resolved, so ``includes`` is refused there.

    A ``Reduction`` has already fixed ``composition`` and ``base_index``, and an
    architecture is already loaded with its includes; passing those arguments
    again is refused rather than silently ignored.
    """
    if isinstance(source, Reduction):
        if composition is not None or base_index != 0 or tuple(includes):
            raise ValueError(
                "A Reduction already fixes composition and base_index; "
                "reduce the architecture with those arguments instead"
            )
        return source

    from pycps_sysml2 import effective_members
    from pycps_sysml2.parameters import SSP_POLICY, validate_parameter_dialect

    parsed = architecture(source, includes=includes)
    system = resolve_system(parsed, composition)
    identity = export_identity(parsed, system)
    validate_parameter_dialect(parsed, system, policy=SSP_POLICY)
    if identity.direct:
        definitions = [system]
    else:
        definitions = [
            definition
            for definition in sorted(
                _component_definitions(parsed, system),
                key=lambda candidate: candidate.name,
            )
            if not effective_members(parsed, definition).parts
        ]
    return Reduction(
        components=tuple(
            component_interface(parsed, definition, base_index=base_index)
            for definition in definitions
        ),
        identity=identity,
        package=parsed.package_name,
        experiment=_experiment(parsed, system),
        root=system.name,
        attributes=tuple(
            (attribute.name, attribute.value)
            for attribute in system.attributes.values()
        ),
    )


def components(
    architecture: Architecture,
    *,
    composition: str | None = None,
    base_index: int = 0,
) -> list[Component]:
    """Every exported component, sorted by name.

    A composition that is itself the FMU model exports that definition as its
    single component; a container root exports its leaf descendants. The
    parameter dialect is validated first, so a flat parameter attribute is
    reported instead of silently dropped. ``base_index`` is forwarded to each
    component's interface.
    """
    return list(
        to_reduction(
            architecture, composition=composition, base_index=base_index
        ).components
    )


def component(
    architecture: Architecture,
    name: str,
    *,
    composition: str | None = None,
    base_index: int = 0,
) -> Component:
    """One named exported component."""
    for candidate in components(
        architecture, composition=composition, base_index=base_index
    ):
        if candidate.name == name:
            return candidate
    raise KeyError(f"No exported component named {name!r}")
