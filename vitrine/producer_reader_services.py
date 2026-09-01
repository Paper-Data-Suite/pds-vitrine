"""Shared source-read authorization services for installed producer reading.

Issue #58 starts by extracting the authorization contract from Candidate services.
This module performs no producer discovery, producer import, manifest access,
projection, persistence, or network access.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module, metadata
from pathlib import Path
from typing import Final, Protocol, cast

from pds_core.publication_records import PublicationRecord
from pds_core.publication_storage import (
    PublicationManifestError,
    PublicationManifestIntegrityError,
    PublicationManifestNotFoundError,
    verify_publication_manifest,
)

from vitrine.models.common import (
    lower_key_tuple,
    require_controlled_key,
    require_identifier,
    require_text,
)
from vitrine.models.errors import VitrineModelValidationError
from vitrine.producer_adapters import (
    ProducerManifestReader,
    ProducerReaderDescriptor,
    ProducerReaderError,
)
from vitrine.released_producer_contracts import (
    RELEASED_PRODUCER_CONTRACT_BY_MODULE,
    RELEASED_PRODUCER_CONTRACTS,
    ReleasedProducerContractAudit,
)

PRODUCER_READER_SERVICE_CONTRACT_VERSION: Final[str] = (
    "vitrine_producer_reader_service_v1"
)
INSTALLED_PRODUCER_READER_CONTRACT_VERSION: Final[str] = (
    "vitrine_installed_producer_reader_v1"
)
SOURCE_READ_AUTHORIZATION_OUTCOMES: Final[frozenset[str]] = frozenset(
    {"allowed", "denied", "unresolved"}
)
PRODUCER_READER_SERVICE_FAILURE_CODES: Final[frozenset[str]] = frozenset(
    {
        "source_read.invalid_request",
        "source_read.authorization_denied",
        "source_read.authorization_unresolved",
        "source_read.manifest_missing",
        "source_read.manifest_integrity_failed",
    }
)


class ProducerReaderServiceError(RuntimeError):
    """Stable privacy-safe source-read or producer-reader service failure."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        stage: str,
        diagnostic_fields: tuple[tuple[str, str], ...] = (),
    ) -> None:
        if code not in PRODUCER_READER_SERVICE_FAILURE_CODES:
            raise ValueError(f"unsupported producer-reader service code: {code}")
        if not isinstance(stage, str) or not stage:
            raise ValueError("stage must be nonempty.")
        self.code = code
        self.stage = stage
        self.diagnostic_fields = tuple(sorted(diagnostic_fields))
        super().__init__(message)


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceReadAuthorizationRequest:
    portfolio_id: str
    portfolio_subject_id: str
    publication_id: str
    operation: str
    purpose: str

    def __post_init__(self) -> None:
        try:
            for name in ("portfolio_id", "portfolio_subject_id", "publication_id"):
                object.__setattr__(
                    self,
                    name,
                    require_identifier(getattr(self, name), name),
                )
            object.__setattr__(
                self,
                "operation",
                require_controlled_key(self.operation, "operation"),
            )
            object.__setattr__(
                self,
                "purpose",
                require_text(self.purpose, "purpose", maximum=500),
            )
        except VitrineModelValidationError as error:
            raise ProducerReaderServiceError(
                "source_read.invalid_request",
                "Source-read authorization request is invalid.",
                stage="authorization_request",
            ) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceReadAuthorizationDecision:
    outcome: str
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.outcome not in SOURCE_READ_AUTHORIZATION_OUTCOMES:
            raise ProducerReaderServiceError(
                "source_read.invalid_request",
                "Source-read authorization outcome is invalid.",
                stage="authorization",
            )
        try:
            object.__setattr__(
                self,
                "reason_codes",
                lower_key_tuple(self.reason_codes, "reason_codes"),
            )
        except VitrineModelValidationError as error:
            raise ProducerReaderServiceError(
                "source_read.invalid_request",
                "Source-read authorization reason codes are invalid.",
                stage="authorization",
            ) from error


class SourceReadAuthorizationGate(Protocol):
    def authorize(
        self,
        request: SourceReadAuthorizationRequest,
    ) -> SourceReadAuthorizationDecision: ...


def authorize_source_read(
    gate: SourceReadAuthorizationGate,
    request: SourceReadAuthorizationRequest,
) -> SourceReadAuthorizationDecision:
    """Require one explicit allowed source-read decision and otherwise fail closed."""

    if not isinstance(request, SourceReadAuthorizationRequest):
        raise ProducerReaderServiceError(
            "source_read.invalid_request",
            "Source-read authorization request is invalid.",
            stage="authorization_request",
        )
    try:
        decision = gate.authorize(request)
    except Exception as error:
        raise ProducerReaderServiceError(
            "source_read.authorization_unresolved",
            "Source-read authorization could not be established.",
            stage="source_authorization",
        ) from error
    if not isinstance(decision, SourceReadAuthorizationDecision):
        raise ProducerReaderServiceError(
            "source_read.authorization_unresolved",
            "Source-read authorization gate returned an invalid decision.",
            stage="source_authorization",
        )
    if decision.outcome == "denied":
        raise ProducerReaderServiceError(
            "source_read.authorization_denied",
            "Source-read authorization was denied.",
            stage="source_authorization",
        )
    if decision.outcome != "allowed":
        raise ProducerReaderServiceError(
            "source_read.authorization_unresolved",
            "Source-read authorization is unresolved.",
            stage="source_authorization",
        )
    return decision





@dataclass(frozen=True, slots=True, kw_only=True)
class AuthorizedProducerManifestReadResult:
    """Transient result of one authorized verified producer-manifest read."""

    authorization: SourceReadAuthorizationDecision
    reader_descriptor: ProducerReaderDescriptor
    manifest_bytes: bytes
    public_model: object

    def __post_init__(self) -> None:
        if not isinstance(self.authorization, SourceReadAuthorizationDecision):
            raise ValueError("authorization must be SourceReadAuthorizationDecision.")
        if not isinstance(self.reader_descriptor, ProducerReaderDescriptor):
            raise ValueError("reader_descriptor must be ProducerReaderDescriptor.")
        if type(self.manifest_bytes) is not bytes:
            raise ValueError("manifest_bytes must be immutable bytes.")


def read_verified_publication_manifest_bytes(
    workspace_root: str | Path,
    publication: PublicationRecord,
) -> bytes:
    """Verify Core containment/digest and return the exact immutable reader bytes."""

    if not isinstance(publication, PublicationRecord):
        raise ProducerReaderServiceError(
            "source_read.manifest_integrity_failed",
            "Canonical Publication manifest metadata is invalid.",
            stage="manifest_integrity",
        )

    lexical_root = Path(workspace_root).absolute()
    lexical_path = lexical_root.joinpath(*publication.manifest_path.split("/"))
    current = lexical_path
    try:
        while current != lexical_root:
            if current.is_symlink():
                raise ProducerReaderServiceError(
                    "source_read.manifest_integrity_failed",
                    "Canonical Publication manifest path traverses a symlink.",
                    stage="manifest_integrity",
                )
            current = current.parent
    except OSError as error:
        raise ProducerReaderServiceError(
            "source_read.manifest_integrity_failed",
            "Canonical Publication manifest path could not be inspected safely.",
            stage="manifest_integrity",
        ) from error

    try:
        path = verify_publication_manifest(workspace_root, publication)
    except PublicationManifestNotFoundError as error:
        raise ProducerReaderServiceError(
            "source_read.manifest_missing",
            "Canonical Publication manifest is unavailable.",
            stage="manifest_integrity",
        ) from error
    except (PublicationManifestIntegrityError, PublicationManifestError) as error:
        raise ProducerReaderServiceError(
            "source_read.manifest_integrity_failed",
            "Canonical Publication manifest failed integrity verification.",
            stage="manifest_integrity",
        ) from error

    try:
        data = path.read_bytes()
    except OSError as error:
        raise ProducerReaderServiceError(
            "source_read.manifest_missing",
            "Verified Publication manifest could not be read.",
            stage="manifest_integrity",
        ) from error

    actual = hashlib.sha256(data).hexdigest()
    if not hmac.compare_digest(actual, publication.manifest_digest):
        raise ProducerReaderServiceError(
            "source_read.manifest_integrity_failed",
            "Publication manifest changed before producer reading.",
            stage="manifest_integrity",
        )
    return data


def read_authorized_producer_manifest(
    workspace_root: str | Path,
    *,
    publication: PublicationRecord,
    authorization_gate: SourceReadAuthorizationGate,
    authorization_request: SourceReadAuthorizationRequest,
    reader: ProducerManifestReader,
) -> AuthorizedProducerManifestReadResult:
    """Authorize, verify exact bytes, and invoke one producer public reader."""

    authorization = authorize_source_read(
        authorization_gate,
        authorization_request,
    )
    manifest_bytes = read_verified_publication_manifest_bytes(
        workspace_root,
        publication,
    )
    public_model = reader.read(manifest_bytes)
    return AuthorizedProducerManifestReadResult(
        authorization=authorization,
        reader_descriptor=reader.descriptor,
        manifest_bytes=manifest_bytes,
        public_model=public_model,
    )


def _reader_error(
    audit: ReleasedProducerContractAudit,
    code: str,
    stage: str,
    message: str,
) -> ProducerReaderError:
    return ProducerReaderError(
        code,
        stage,
        message,
        producer_module_id=audit.producer_module_id,
        publication_kind=audit.support_key.publication_kind,
        manifest_contract_version=audit.support_key.manifest_contract_version,
        diagnostic_fields=(
            ("distribution_name", audit.distribution_name),
            (
                "public_reader_id",
                f"vitrine_installed_{audit.producer_module_id}_academic_result_reader",
            ),
        ),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class InstalledProducerManifestReader:
    """Lazy binding to one exact #57-audited producer public manifest reader."""

    audit: ReleasedProducerContractAudit

    def __post_init__(self) -> None:
        authoritative = RELEASED_PRODUCER_CONTRACT_BY_MODULE.get(
            self.audit.producer_module_id
        )
        if authoritative is None or self.audit != authoritative:
            raise _reader_error(
                self.audit,
                "reader.incompatible",
                "reader_binding",
                "Installed producer reader binding is not an audited Vitrine contract.",
            )

    @property
    def descriptor(self) -> ProducerReaderDescriptor:
        return ProducerReaderDescriptor(
            public_reader_id=(
                f"vitrine_installed_{self.audit.producer_module_id}"
                "_academic_result_reader"
            ),
            reader_contract_version=INSTALLED_PRODUCER_READER_CONTRACT_VERSION,
            package_identity=self.audit.distribution_name,
            integration_kind="live",
        )

    def read(self, value: bytes) -> object:
        if type(value) is not bytes:
            raise _reader_error(
                self.audit,
                "reader.validation_failed",
                "reader_input",
                "Installed producer reader input must be immutable bytes.",
            )

        try:
            metadata.version(self.audit.distribution_name)
        except metadata.PackageNotFoundError as error:
            raise _reader_error(
                self.audit,
                "reader.unavailable",
                "reader_distribution",
                "Audited producer reader distribution is not installed.",
            ) from error
        except Exception as error:
            raise _reader_error(
                self.audit,
                "reader.unavailable",
                "reader_distribution",
                "Audited producer reader distribution could not be resolved.",
            ) from error

        try:
            module = import_module(self.audit.public_reader_module)
        except Exception as error:
            raise _reader_error(
                self.audit,
                "reader.incompatible",
                "reader_api",
                "Audited producer public reader module is unavailable.",
            ) from error

        try:
            reader = getattr(module, self.audit.public_reader_symbol)
        except Exception as error:
            raise _reader_error(
                self.audit,
                "reader.incompatible",
                "reader_api",
                "Audited producer public reader symbol is unavailable.",
            ) from error
        if not callable(reader):
            raise _reader_error(
                self.audit,
                "reader.incompatible",
                "reader_api",
                "Audited producer public reader symbol is not callable.",
            )

        callable_reader = cast(Callable[[bytes], object], reader)
        try:
            return callable_reader(value)
        except Exception as error:
            raise _reader_error(
                self.audit,
                "reader.validation_failed",
                "producer_reader",
                "Producer public reader rejected the verified manifest bytes.",
            ) from error


def build_audited_installed_producer_reader(
    producer_module_id: str,
) -> InstalledProducerManifestReader:
    """Build one lazy live reader only for an exact #57-audited producer."""

    audit = (
        RELEASED_PRODUCER_CONTRACT_BY_MODULE.get(producer_module_id)
        if isinstance(producer_module_id, str)
        else None
    )
    if audit is None:
        raise ProducerReaderError(
            "reader.incompatible",
            "reader_binding",
            "No audited installed producer reader binding exists.",
            producer_module_id=(
                producer_module_id if isinstance(producer_module_id, str) else None
            ),
        )
    return InstalledProducerManifestReader(audit=audit)


def build_audited_installed_producer_readers(
) -> tuple[InstalledProducerManifestReader, ...]:
    """Build all audited lazy reader bindings without importing producer packages."""

    return tuple(
        InstalledProducerManifestReader(audit=audit)
        for audit in RELEASED_PRODUCER_CONTRACTS
    )

__all__ = [
    "AuthorizedProducerManifestReadResult",
    "INSTALLED_PRODUCER_READER_CONTRACT_VERSION",
    "PRODUCER_READER_SERVICE_CONTRACT_VERSION",
    "PRODUCER_READER_SERVICE_FAILURE_CODES",
    "InstalledProducerManifestReader",
    "ProducerReaderServiceError",
    "SOURCE_READ_AUTHORIZATION_OUTCOMES",
    "SourceReadAuthorizationDecision",
    "SourceReadAuthorizationGate",
    "SourceReadAuthorizationRequest",
    "authorize_source_read",
    "build_audited_installed_producer_reader",
    "build_audited_installed_producer_readers",
    "read_authorized_producer_manifest",
    "read_verified_publication_manifest_bytes",
]
