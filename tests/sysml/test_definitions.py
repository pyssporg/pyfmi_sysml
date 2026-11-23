"""The bundled ``PyfmiInterop`` SysML library and its packaging."""

from __future__ import annotations

import pytest

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
    architecture = pycps.load(interop_definitions())

    assert architecture.package_name == "PyfmiInterop"

    metadata = next(
        definition
        for definition in architecture.attribute_definitions.values()
        if definition.name == "InteropMetadata"
    )
    assert "FmuMetadata" not in metadata.specializes
    assert set(metadata.attributes) == {"source", "serialization", "version"}

    deployment = next(
        definition
        for definition in architecture.port_definitions.values()
        if definition.name == "InteropDeployment"
    )
    assert "ParameterInterface" in deployment.specializes
    assert set(deployment.attributes) == {
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
    assert "parameters" in model.ports
    # fmu_meta stays inherited from FmuModel, not redeclared locally.
    assert "fmu_meta" not in model.attributes



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
