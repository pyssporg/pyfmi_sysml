"""SysML ingestion and interop composition for the FMI interface generators.

This composition package owns the only SysML reader: :func:`to_reduction`
loads through ``pycps_sysml2`` once and produces the parser-free ``Reduction``
that every ``pyfmi_interfaces`` emitter consumes. The source-taking generator
wrappers, the interop adapter flow (``parse`` once, then ``generate_adapter``),
and the ``pyfmi-sysml`` command line live here; FMI packaging stays in
``pyfmi_interfaces``, and the SysML-free generator, runtime, and packager stay
in ``pyfmi_interop``.
"""

from pyfmi_interop.core import adapter_from_reduction
from pyfmi_sysml.definitions import interop_definitions, load_with_interop
from pyfmi_sysml.generate import (
    generate_c_headers,
    generate_c_runtime,
    generate_model_description,
    generate_modelica,
)
from pyfmi_sysml.generate_adapter import generate_adapter
from pyfmi_sysml.parse import (
    DEFAULT_STEP_SIZE_S,
    DEFAULT_STRING_CAPACITY,
    ParsedModel,
    load_architecture,
    load_model,
    model_from_architecture,
    model_from_sysml,
    parse,
)
from pyfmi_sysml.reduction import (
    architecture,
    component,
    component_interface,
    components,
    direction_causality,
    export_identity,
    fmu_units,
    resolve_system,
    to_reduction,
)

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "DEFAULT_STEP_SIZE_S",
    "DEFAULT_STRING_CAPACITY",
    "ParsedModel",
    "adapter_from_reduction",
    "architecture",
    "component",
    "component_interface",
    "components",
    "direction_causality",
    "export_identity",
    "fmu_units",
    "generate_adapter",
    "generate_c_headers",
    "generate_c_runtime",
    "generate_model_description",
    "generate_modelica",
    "interop_definitions",
    "load_architecture",
    "load_model",
    "load_with_interop",
    "model_from_architecture",
    "model_from_sysml",
    "parse",
    "resolve_system",
    "to_reduction",
]
