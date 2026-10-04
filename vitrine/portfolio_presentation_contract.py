"""Composite renderer identity for one student Portfolio presentation."""

from __future__ import annotations

import hashlib
import json
from typing import Final

from vitrine.portfolio_presentation import (
    STUDENT_PORTFOLIO_PRESENTATION_CONTRACT_VERSION,
)
from vitrine.portfolio_presentation_html import (
    STUDENT_PORTFOLIO_HTML_CONTRACT_VERSION,
    STUDENT_PORTFOLIO_HTML_RENDERER_CONFIGURATION_SHA256,
    STUDENT_PORTFOLIO_HTML_RENDERER_ID,
    STUDENT_PORTFOLIO_HTML_RENDERER_VERSION,
)
from vitrine.portfolio_presentation_package import (
    STUDENT_PORTFOLIO_FILE_INVENTORY_CONTRACT_VERSION,
    STUDENT_PORTFOLIO_FILE_PACKAGE_CONTRACT_VERSION,
)
from vitrine.portfolio_presentation_pdf import (
    STUDENT_PORTFOLIO_PDF_CONTRACT_VERSION,
    STUDENT_PORTFOLIO_PDF_RENDERER_ID,
    STUDENT_PORTFOLIO_PDF_RENDERER_VERSION,
)

STUDENT_PORTFOLIO_PRESENTATION_RENDERER_ID: Final[str] = (
    "vitrine_student_portfolio_renderer"
)
STUDENT_PORTFOLIO_PRESENTATION_RENDERER_VERSION: Final[str] = "1"
STUDENT_PORTFOLIO_PRESENTATION_RENDERER_CONTRACT_VERSION: Final[str] = (
    "vitrine_student_portfolio_renderer_v1"
)
_PRESENTATION_IDENTITY_DOMAIN: Final[str] = (
    "vitrine_student_portfolio_presentation_identity_v1"
)


def _require_sha256(value: str, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest.")
    return value


def student_portfolio_renderer_configuration_sha256(
    *,
    pdf_renderer_configuration_sha256: str,
) -> str:
    """Bind the exact HTML/PDF/file-package renderer configuration."""

    pdf_configuration = _require_sha256(
        pdf_renderer_configuration_sha256,
        "pdf_renderer_configuration_sha256",
    )
    value = {
        "presentation_contract_version": (
            STUDENT_PORTFOLIO_PRESENTATION_CONTRACT_VERSION
        ),
        "file_package_contract_version": (
            STUDENT_PORTFOLIO_FILE_PACKAGE_CONTRACT_VERSION
        ),
        "file_inventory_contract_version": (
            STUDENT_PORTFOLIO_FILE_INVENTORY_CONTRACT_VERSION
        ),
        "html": {
            "renderer_id": STUDENT_PORTFOLIO_HTML_RENDERER_ID,
            "renderer_version": STUDENT_PORTFOLIO_HTML_RENDERER_VERSION,
            "renderer_contract_version": STUDENT_PORTFOLIO_HTML_CONTRACT_VERSION,
            "renderer_configuration_sha256": (
                STUDENT_PORTFOLIO_HTML_RENDERER_CONFIGURATION_SHA256
            ),
        },
        "printable_pdf": {
            "renderer_id": STUDENT_PORTFOLIO_PDF_RENDERER_ID,
            "renderer_version": STUDENT_PORTFOLIO_PDF_RENDERER_VERSION,
            "renderer_contract_version": STUDENT_PORTFOLIO_PDF_CONTRACT_VERSION,
            "renderer_configuration_sha256": pdf_configuration,
        },
    }
    payload = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def student_portfolio_presentation_artifact_id(
    *,
    preparation_fingerprint: str,
    renderer_configuration_sha256: str,
) -> str:
    """Return the stable semantic identity for one exact presentation build."""

    preparation = _require_sha256(
        preparation_fingerprint,
        "preparation_fingerprint",
    )
    configuration = _require_sha256(
        renderer_configuration_sha256,
        "renderer_configuration_sha256",
    )
    payload = json.dumps(
        {
            "domain": _PRESENTATION_IDENTITY_DOMAIN,
            "presentation_contract_version": (
                STUDENT_PORTFOLIO_PRESENTATION_CONTRACT_VERSION
            ),
            "preparation_fingerprint": preparation,
            "renderer_configuration_sha256": configuration,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return f"presentation_{hashlib.sha256(payload).hexdigest()}"


__all__ = [
    "STUDENT_PORTFOLIO_PRESENTATION_RENDERER_CONTRACT_VERSION",
    "STUDENT_PORTFOLIO_PRESENTATION_RENDERER_ID",
    "STUDENT_PORTFOLIO_PRESENTATION_RENDERER_VERSION",
    "student_portfolio_presentation_artifact_id",
    "student_portfolio_renderer_configuration_sha256",
]
