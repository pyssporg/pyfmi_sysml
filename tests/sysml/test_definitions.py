"""The bundled ``PyfmiInterop`` SysML library and its packaging."""

from __future__ import annotations

import pytest

from conftest import fixture_path
from pyfmi_sysml import interop_definitions

pytestmark = pytest.mark.sysml


@pytest.mark.unit
def test_interop_definitions_is_a_bundled_file():
    path = interop_definitions()

    assert path.name == "interop.sysml"
    assert path.parent.name == "pyssp_sysml_definitions"
    assert path.is_file()


@pytest.mark.unit
def test_interop_definitions_declares_the_shared_vocabulary():
    pycps = pytest.importorskip("pycps_sysml2")
    # The interop vocabulary imports PysspCore privately, so the core root has
    # to resolve `SourcedMetadata` for the inherited-member view.
    architecture = pycps.load(interop_definitions(), pycps.core_definitions())

    assert architecture.package_name == "PyfmiInterop"

    metadata = next(
        definition
        for definition in architecture.attribute_definitions.values()
        if definition.name == "InteropMetadata"
    )
    # A family container: it reaches SourcedMetadata and inherits `source`
    # instead of declaring it again.
    assert "SourcedMetadata" in metadata.specializes
    assert "FmuMetadata" not in metadata.specializes
    assert set(pycps.effective_members(architecture, metadata).attributes) == {
        "source",
        "serialization",
        "version",
    }
    assert set(metadata.attributes) == {"serialization", "version"}
    assert "source" not in metadata.attributes

    deployment = next(
        definition
        for definition in architecture.port_definitions.values()
        if definition.name == "InteropDeployment"
    )
    assert "ParameterInterface" in deployment.specializes
    assert set(pycps.effective_members(architecture, deployment).attributes) == {
        "transport",
        "bind_address",
        "peer_address",
    }

    model = next(
        definition
        for definition in architecture.part_definitions.values()
        if definition.name == "FmuInterop"
    )
    assert "FmuModel" in model.specializes
    assert "interop_meta" in model.attributes
    parameters = model.ports["parameters"]
    assert parameters.direction == "in"
    assert parameters.type_name == "InteropDeployment"
    # fmu_meta stays inherited from FmuModel, not redeclared locally.
    assert "fmu_meta" not in model.attributes
    assert "fmu_meta" in pycps.effective_members(architecture, model).attributes



class _Architecture:
    """The only part of a loaded architecture ``load_with_interop`` reads."""

    def __init__(self, imports: dict[str, object]) -> None:
        self.imports = imports


@pytest.mark.unit
def test_load_with_interop_skips_the_library_without_an_import() -> None:
    from pyfmi_sysml import load_with_interop

    calls: list[tuple[object, tuple[object, ...]]] = []

    def load(source, *roots):
        calls.append((source, roots))
        return _Architecture({})

    result = load_with_interop("model.sysml", load, includes=["lib"])

    assert result.imports == {}
    assert calls == [("model.sysml", ("lib",))]


@pytest.mark.unit
def test_load_with_interop_adds_the_library_when_imported() -> None:
    from pyfmi_sysml import load_with_interop

    calls: list[tuple[object, tuple[object, ...]]] = []

    def load(source, *roots):
        calls.append((source, roots))
        return _Architecture({"PyfmiInterop": object()})

    load_with_interop("model.sysml", load)

    assert calls == [
        ("model.sysml", ()),
        ("model.sysml", (interop_definitions(),)),
    ]


@pytest.mark.unit
def test_an_include_root_can_make_the_import_visible() -> None:
    from pyfmi_sysml import load_with_interop

    calls: list[tuple[object, tuple[object, ...]]] = []

    def load(source, *roots):
        calls.append((source, roots))
        imports = {"PyfmiInterop": object()} if "lib" in roots else {}
        return _Architecture(imports)

    load_with_interop("model.sysml", load, includes=["lib"])

    assert calls == [
        ("model.sysml", ("lib",)),
        ("model.sysml", ("lib", interop_definitions())),
    ]


FIXTURE_SUBJECTS = (
    "applied",
    "bus",
    "controller",
    "generator",
    "minimal",
    "packages",
    "sensor",
)


@pytest.mark.unit
@pytest.mark.parametrize("subject", FIXTURE_SUBJECTS)
def test_fixtures_include_the_shipped_core_instead_of_redeclaring_it(
    subject: str,
) -> None:
    """One copy of the vocabulary: every fixture imports the package roots."""
    pycps = pytest.importorskip("pycps_sysml2")

    includes = (
        [fixture_path("packages", "support")] if subject == "packages" else []
    )
    architecture = pycps.load(
        fixture_path(subject, f"{subject}.sysml"),
        *includes,
        pycps.core_definitions(),
    )

    assert "ParameterInterface" not in architecture.port_definitions
    assert "ParameterSet" not in architecture.attribute_definitions
    assert "FmuModel" not in architecture.part_definitions
    assert "FmuMetadata" not in architecture.attribute_definitions
