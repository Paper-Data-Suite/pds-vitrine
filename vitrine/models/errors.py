"""Errors for Vitrine's pure runtime model layer."""

from __future__ import annotations

from dataclasses import dataclass


class VitrineModelError(ValueError):
    """Base error for immutable Vitrine runtime models."""


class VitrineModelValidationError(VitrineModelError):
    """Raised when a model or value object is structurally invalid."""


class VitrineSerializationError(VitrineModelError):
    """Raised when exact mapping or JSON conversion fails."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidationIssue:
    """One deterministic privacy-safe cross-record validation issue."""

    code: str
    message: str
    record_type: str | None = None
    record_id: str | None = None
    field_path: tuple[str | int, ...] = ()
    related_references: tuple[object, ...] = ()


class VitrineRecordGraphError(VitrineModelError):
    """Raised when one or more graph relationships are invalid."""

    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        self.issues = tuple(issues)
        super().__init__(f"Vitrine record graph contains {len(self.issues)} issue(s).")


class VitrineIdentityStateError(VitrineModelError):
    """Raised when Portfolio Subject identity history is inconsistent."""

    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        self.issues = tuple(issues)
        super().__init__(
            f"Vitrine identity state contains {len(self.issues)} issue(s)."
        )
