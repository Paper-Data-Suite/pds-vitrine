"""Shared validation helpers for Vitrine runtime models."""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Iterable
from datetime import date, datetime, timezone
from pathlib import PurePosixPath
from typing import Final, TypeVar

from pds_core.identifiers import IdentifierValidationError, validate_identifier
from pds_core.school_years import SchoolYearValidationError, validate_school_year

from .errors import VitrineModelValidationError

SCHEMA_VERSION: Final[str] = "1"
SHA256_ALGORITHM: Final[str] = "sha256"
_SHA256_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
_EXTENSION_KEY_RE: Final[re.Pattern[str]] = re.compile(
    r"^[a-z][a-z0-9_-]*:[a-z][a-z0-9_-]*$"
)
_CONTROL_RE: Final[re.Pattern[str]] = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

T = TypeVar("T")


def require_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise VitrineModelValidationError(f"{field_name} must be a string.")
    try:
        return validate_identifier(value, field_name)
    except IdentifierValidationError as error:
        raise VitrineModelValidationError(str(error)) from error


def require_lower_identifier(value: object, field_name: str) -> str:
    result = require_identifier(value, field_name)
    if result != result.lower():
        raise VitrineModelValidationError(f"{field_name} must be lowercase.")
    return result


def require_school_year_value(value: object) -> str:
    try:
        return validate_school_year(value)
    except SchoolYearValidationError as error:
        raise VitrineModelValidationError(str(error)) from error


def require_text(value: object, field_name: str, *, maximum: int = 1000) -> str:
    if not isinstance(value, str):
        raise VitrineModelValidationError(f"{field_name} must be a string.")
    if value == "" or value != value.strip():
        raise VitrineModelValidationError(
            f"{field_name} must be nonempty and have no surrounding whitespace."
        )
    if len(value) > maximum:
        raise VitrineModelValidationError(
            f"{field_name} must be at most {maximum} characters."
        )
    if _CONTROL_RE.search(value):
        raise VitrineModelValidationError(
            f"{field_name} must not contain disallowed control characters."
        )
    return value


def require_optional_text(
    value: object, field_name: str, *, maximum: int = 1000
) -> str | None:
    if value is None:
        return None
    return require_text(value, field_name, maximum=maximum)


def require_enum(
    value: object,
    field_name: str,
    allowed: frozenset[str],
    *,
    allow_extension: bool = False,
) -> str:
    result = require_text(value, field_name, maximum=128)
    if result in allowed:
        return result
    if allow_extension and _EXTENSION_KEY_RE.fullmatch(result):
        return result
    choices = ", ".join(sorted(allowed))
    raise VitrineModelValidationError(
        f"{field_name} must be one of: {choices}."
    )


def require_controlled_key(
    value: object,
    field_name: str,
    *,
    allowed: frozenset[str] | None = None,
    allow_extension: bool = True,
) -> str:
    """Validate one built-in or namespace-qualified controlled key."""
    text = require_text(value, field_name, maximum=128)
    if allowed is not None and text in allowed:
        return text
    if allowed is None and re.fullmatch(r"[a-z][a-z0-9_-]*", text):
        return text
    if allow_extension and _EXTENSION_KEY_RE.fullmatch(text):
        return text
    if allowed is None:
        raise VitrineModelValidationError(
            f"{field_name} must be a lowercase controlled key or "
            "namespace-qualified extension."
        )
    choices = ", ".join(sorted(allowed))
    raise VitrineModelValidationError(
        f"{field_name} must be one of: {choices}; or a namespace-qualified "
        "extension."
    )


def require_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise VitrineModelValidationError(f"{field_name} must be a Boolean.")
    return value


def require_positive_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise VitrineModelValidationError(
            f"{field_name} must be a positive non-Boolean integer."
        )
    return value


def require_nonnegative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise VitrineModelValidationError(
            f"{field_name} must be a nonnegative non-Boolean integer."
        )
    return value


def require_finite_number(value: object, field_name: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VitrineModelValidationError(f"{field_name} must be numeric.")
    if isinstance(value, float) and not math.isfinite(value):
        raise VitrineModelValidationError(f"{field_name} must be finite.")
    return value


def require_aware_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise VitrineModelValidationError(f"{field_name} must be a datetime.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise VitrineModelValidationError(
            f"{field_name} must be timezone-aware."
        )
    return value


def canonical_datetime_text(value: datetime) -> str:
    return require_aware_datetime(value, "datetime").astimezone(timezone.utc).isoformat(
        timespec="microseconds"
    )


def require_date(value: object, field_name: str) -> date:
    if isinstance(value, datetime) or not isinstance(value, date):
        raise VitrineModelValidationError(f"{field_name} must be a date.")
    return value


def tuple_of(
    values: Iterable[object] | tuple[object, ...],
    field_name: str,
    validator: Callable[[object], T],
    *,
    unique: bool = False,
    nonempty: bool = False,
) -> tuple[T, ...]:
    if isinstance(values, (str, bytes)):
        raise VitrineModelValidationError(f"{field_name} must be a collection.")
    try:
        result = tuple(validator(item) for item in values)
    except TypeError as error:
        raise VitrineModelValidationError(
            f"{field_name} must be an iterable collection."
        ) from error
    if nonempty and not result:
        raise VitrineModelValidationError(f"{field_name} must not be empty.")
    if unique and len(set(result)) != len(result):
        raise VitrineModelValidationError(
            f"{field_name} must not contain duplicates."
        )
    return result


def identifier_tuple(
    values: Iterable[str], field_name: str, *, nonempty: bool = False
) -> tuple[str, ...]:
    return tuple_of(
        values,
        field_name,
        lambda item: require_identifier(item, field_name),
        unique=True,
        nonempty=nonempty,
    )


def lower_key_tuple(
    values: Iterable[str],
    field_name: str,
    *,
    allowed: frozenset[str] | None = None,
    allow_extension: bool = True,
    nonempty: bool = False,
) -> tuple[str, ...]:
    def validate(item: object) -> str:
        return require_controlled_key(
            item,
            field_name,
            allowed=allowed,
            allow_extension=allow_extension,
        )

    return tuple_of(
        values,
        field_name,
        validate,
        unique=True,
        nonempty=nonempty,
    )


def text_tuple(
    values: Iterable[str], field_name: str, *, nonempty: bool = False
) -> tuple[str, ...]:
    return tuple_of(
        values,
        field_name,
        lambda item: require_text(item, field_name),
        unique=True,
        nonempty=nonempty,
    )


def require_relative_path(value: object, field_name: str) -> str:
    text = require_text(value, field_name, maximum=2048)
    if "\\" in text or "://" in text or re.match(r"^[A-Za-z]:", text):
        raise VitrineModelValidationError(
            f"{field_name} must be a portable relative POSIX path."
        )
    path = PurePosixPath(text)
    if path.is_absolute() or text.startswith("/"):
        raise VitrineModelValidationError(f"{field_name} must be relative.")
    parts = text.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise VitrineModelValidationError(
            f"{field_name} must not contain empty, '.' or '..' components."
        )
    return text


def require_sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise VitrineModelValidationError(
            f"{field_name} must be a lowercase 64-character SHA-256 value."
        )
    return value


def require_record_envelope(
    schema_version: object,
    record_type: object,
    expected_record_type: str,
) -> None:
    if schema_version != SCHEMA_VERSION:
        raise VitrineModelValidationError("schema_version must be '1'.")
    if record_type != expected_record_type:
        raise VitrineModelValidationError(
            f"record_type must be {expected_record_type!r}."
        )
