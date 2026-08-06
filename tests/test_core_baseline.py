from __future__ import annotations

import importlib
from collections.abc import Mapping

from pds_core.identifiers import validate_identifier
from pds_core.workspace import inspect_workspace_root


def test_core_version_and_public_workspace_identifier_contracts() -> None:
    import pds_core

    assert pds_core.__version__ == "0.6.0"
    assert validate_identifier("vitrine") == "vitrine"
    assert inspect_workspace_root is not None


def test_required_core_public_modules_and_surfaces() -> None:
    required: Mapping[str, tuple[str, ...]] = {
        "pds_core.classes": ("list_class_folders", "load_class_roster"),
        "pds_core.rosters": ("Roster", "student_display_name"),
        "pds_core.academic_work_registrations": ("AcademicWorkRegistration",),
        "pds_core.academic_work_registration_storage": (
            "load_current_academic_work_registration",
        ),
        "pds_core.registry_services": (
            "AcademicWorkRegistrationRequest",
            "get_canonical_publication_record",
        ),
        "pds_core.publication_records": ("PublicationRecord",),
        "pds_core.publication_storage": ("verify_publication_manifest",),
        "pds_core.publication_compatibility": (
            "PublicationProducerProfile",
            "evaluate_publication_compatibility",
        ),
        "pds_core.academic_catalog": ("ACADEMIC_CATALOG_SCHEMA_VERSION",),
    }
    for module_name, attributes in required.items():
        module = importlib.import_module(module_name)
        for attribute in attributes:
            assert hasattr(module, attribute), f"{module_name}.{attribute} is missing"
