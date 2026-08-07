"""Stable error types for Vitrine canonical storage and derived catalogs."""

from __future__ import annotations

from vitrine.models.errors import ValidationIssue


class VitrineStorageError(Exception):
    """Base class for canonical Vitrine persistence failures."""


class VitrineStorageValidationError(VitrineStorageError, ValueError):
    """Raised for invalid persistence inputs."""


class VitrineStorageNotFoundError(VitrineStorageError):
    """Raised when an exact canonical object does not exist."""


class VitrineStorageReadError(VitrineStorageError):
    """Raised when canonical bytes cannot be read or decoded."""


class VitrineStorageWriteError(VitrineStorageError):
    """Raised when canonical bytes cannot be written safely."""


class VitrineStorageConflictError(VitrineStorageError):
    """Raised for expected-state or exclusive-write conflicts."""


class VitrineStorageIntegrityError(VitrineStorageError):
    """Raised when canonical history cannot be proven internally consistent."""


class VitrineStorageGraphIntegrityError(VitrineStorageIntegrityError):
    """Raised when persisted records reconstruct to an invalid runtime graph."""

    def __init__(self, message: str, *, issues: tuple[ValidationIssue, ...]) -> None:
        super().__init__(message)
        self.issues = issues


class VitrineStoragePartialSuccessError(VitrineStorageError):
    """Raised when durable effects occurred but the operation did not finish cleanly."""

    def __init__(
        self,
        message: str,
        *,
        durable_paths: tuple[str, ...],
        pointer_published: bool,
        state_revision: int | None,
        state_sha256: str | None,
    ) -> None:
        super().__init__(message)
        self.durable_paths = durable_paths
        self.pointer_published = pointer_published
        self.state_revision = state_revision
        self.state_sha256 = state_sha256


class VitrineCatalogError(VitrineStorageError):
    """Base class for nonauthoritative derived-catalog failures."""


class VitrineCatalogNotFoundError(VitrineCatalogError):
    pass


class VitrineCatalogCompatibilityError(VitrineCatalogError):
    pass


class VitrineCatalogSourceError(VitrineCatalogError):
    pass


class VitrineCatalogIntegrityError(VitrineCatalogError):
    pass


class VitrineCatalogConflictError(VitrineCatalogError):
    pass


class VitrineCatalogBuildError(VitrineCatalogError):
    pass
