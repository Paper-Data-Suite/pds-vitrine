"""Exact JSON-native conversion for Vitrine runtime records."""

from __future__ import annotations

import types
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from typing import Any, TypeAlias, Union, cast, get_args, get_origin, get_type_hints

from pds_core.routing_models import (
    ModuleRecordRef,
    ModuleWorkRef,
    module_record_ref_from_dict,
    module_record_ref_to_dict,
    module_work_ref_from_dict,
    module_work_ref_to_dict,
)

from vitrine.record_registry import RECORD_DESCRIPTORS

from .audiences import AudienceContext
from .candidates import CandidateEvaluation, PortfolioCandidate
from .curation import (
    PortfolioPlacement,
    PortfolioSelection,
    SectionArrangementRevision,
    WorkingPortfolioCompositionRevision,
)
from .errors import VitrineSerializationError
from .identity import (
    Portfolio,
    PortfolioSubject,
    PortfolioSubjectClassLink,
    PortfolioSubjectDisplaySnapshot,
    PortfolioSubjectIdentityDecision,
    PortfolioSubjectIdentityTransition,
)
from .profiles import (
    PortfolioProfileBinding,
    PortfolioProfileFamily,
    PortfolioProfileRevision,
)
from .snapshots import (
    SnapshotEdition,
    SnapshotEntry,
    SnapshotManifest,
    SnapshotMaterializationRecord,
    SnapshotOmission,
    SnapshotSeal,
)

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

VitrineRecord: TypeAlias = (
    Portfolio
    | PortfolioSubject
    | PortfolioSubjectClassLink
    | PortfolioSubjectDisplaySnapshot
    | PortfolioSubjectIdentityDecision
    | PortfolioSubjectIdentityTransition
    | PortfolioProfileFamily
    | PortfolioProfileRevision
    | PortfolioProfileBinding
    | CandidateEvaluation
    | PortfolioCandidate
    | PortfolioSelection
    | PortfolioPlacement
    | SectionArrangementRevision
    | WorkingPortfolioCompositionRevision
    | AudienceContext
    | SnapshotMaterializationRecord
    | SnapshotEntry
    | SnapshotOmission
    | SnapshotManifest
    | SnapshotSeal
    | SnapshotEdition
)

RECORD_TYPE_REGISTRY: dict[str, type[Any]] = {
    descriptor.record_type: descriptor.model_type for descriptor in RECORD_DESCRIPTORS
}
RECORD_TYPES: tuple[type[Any], ...] = tuple(RECORD_TYPE_REGISTRY.values())



def _datetime_to_text(value: datetime) -> str:
    from .common import canonical_datetime_text

    return canonical_datetime_text(value)


def value_to_json(value: object) -> JsonValue:
    """Convert one supported immutable model value into JSON-native data."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        import math

        if not math.isfinite(value):
            raise VitrineSerializationError("nonfinite numbers are not serializable.")
        return value
    if isinstance(value, datetime):
        return _datetime_to_text(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, ModuleWorkRef):
        return cast(dict[str, JsonValue], module_work_ref_to_dict(value))
    if isinstance(value, ModuleRecordRef):
        return cast(dict[str, JsonValue], module_record_ref_to_dict(value))
    if isinstance(value, tuple):
        return [value_to_json(item) for item in value]
    if is_dataclass(value):
        return {
            item.name: value_to_json(getattr(value, item.name))
            for item in fields(value)
        }
    raise VitrineSerializationError(
        f"unsupported serialization value type: {type(value).__name__}."
    )


def record_to_dict(record: VitrineRecord) -> dict[str, JsonValue]:
    """Convert a supported top-level record to its exact mapping."""
    if type(record) not in RECORD_TYPES:
        raise VitrineSerializationError(
            f"unsupported Vitrine record type: {type(record).__name__}."
        )
    value = value_to_json(record)
    if not isinstance(value, dict):
        raise AssertionError("record conversion did not produce an object")
    return value


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise VitrineSerializationError(f"{label} must be an object.")
    if any(not isinstance(key, str) for key in value):
        raise VitrineSerializationError(f"{label} keys must be strings.")
    return cast(Mapping[str, object], value)


def _from_typed_value(value: object, expected: object, field_name: str) -> object:
    origin = get_origin(expected)
    args = get_args(expected)

    if origin is tuple:
        if not isinstance(value, list):
            raise VitrineSerializationError(f"{field_name} must be an array.")
        if len(args) != 2 or args[1] is not Ellipsis:
            raise VitrineSerializationError(
                f"{field_name} uses an unsupported tuple annotation."
            )
        return tuple(
            _from_typed_value(item, args[0], f"{field_name}[]") for item in value
        )

    if origin in (Union, types.UnionType):
        if value is None and type(None) in args:
            return None
        failures: list[Exception] = []
        for option in args:
            if option is type(None):
                continue
            try:
                return _from_typed_value(value, option, field_name)
            except (VitrineSerializationError, ValueError, TypeError) as error:
                failures.append(error)
        raise VitrineSerializationError(
            f"{field_name} does not match any permitted type."
        ) from (failures[-1] if failures else None)

    if expected is Any:
        raise VitrineSerializationError(
            f"{field_name} uses unsupported unconstrained Any."
        )
    if expected is str:
        if not isinstance(value, str):
            raise VitrineSerializationError(f"{field_name} must be a string.")
        return value
    if expected is bool:
        if not isinstance(value, bool):
            raise VitrineSerializationError(f"{field_name} must be a Boolean.")
        return value
    if expected is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise VitrineSerializationError(
                f"{field_name} must be a non-Boolean integer."
            )
        return value
    if expected is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise VitrineSerializationError(f"{field_name} must be numeric.")
        return float(value)
    if expected is datetime:
        if not isinstance(value, str):
            raise VitrineSerializationError(
                f"{field_name} must be an ISO datetime string."
            )
        try:
            return datetime.fromisoformat(value)
        except ValueError as error:
            raise VitrineSerializationError(
                f"{field_name} must be a valid ISO datetime string."
            ) from error
    if expected is date:
        if not isinstance(value, str):
            raise VitrineSerializationError(
                f"{field_name} must be an ISO date string."
            )
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise VitrineSerializationError(
                f"{field_name} must be a valid ISO date string."
            ) from error
    if expected is ModuleWorkRef:
        return module_work_ref_from_dict(_require_mapping(value, field_name))
    if expected is ModuleRecordRef:
        return module_record_ref_from_dict(_require_mapping(value, field_name))

    if isinstance(expected, type) and is_dataclass(expected):
        mapping = _require_mapping(value, field_name)
        return _dataclass_from_mapping(expected, mapping, field_name)

    raise VitrineSerializationError(
        f"{field_name} uses unsupported annotation {expected!r}."
    )


def _dataclass_from_mapping(
    cls: type[Any], data: Mapping[str, object], label: str
) -> object:
    expected_fields = {item.name for item in fields(cls)}
    actual_fields = set(data)
    unknown = sorted(actual_fields - expected_fields)
    if unknown:
        raise VitrineSerializationError(
            f"{label} contains unknown key(s): {', '.join(unknown)}."
        )
    missing = sorted(expected_fields - actual_fields)
    if missing:
        raise VitrineSerializationError(
            f"{label} is missing required key(s): {', '.join(missing)}."
        )
    hints = get_type_hints(cls)
    kwargs = {
        name: _from_typed_value(data[name], hints[name], f"{label}.{name}")
        for name in expected_fields
    }
    try:
        return cls(**kwargs)
    except (TypeError, ValueError) as error:
        raise VitrineSerializationError(f"invalid {label}: {error}") from error


def record_from_dict(data: Mapping[str, object]) -> VitrineRecord:
    """Build one supported top-level record from an exact mapping."""
    mapping = _require_mapping(data, "Vitrine record")
    record_type = mapping.get("record_type")
    if not isinstance(record_type, str):
        raise VitrineSerializationError("record_type must be a string.")
    cls = RECORD_TYPE_REGISTRY.get(record_type)
    if cls is None:
        raise VitrineSerializationError(
            f"unsupported Vitrine record_type {record_type!r}."
        )
    return cast(VitrineRecord, _dataclass_from_mapping(cls, mapping, record_type))


__all__ = [
    "JsonScalar",
    "JsonValue",
    "RECORD_TYPE_REGISTRY",
    "RECORD_TYPES",
    "VitrineRecord",
    "record_from_dict",
    "record_to_dict",
    "value_to_json",
]
