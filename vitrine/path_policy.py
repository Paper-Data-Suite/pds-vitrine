"""Shared bounded filesystem-component policy for Vitrine-owned writers.

Issue #111 separates exact semantic identity from filesystem serialization.
This module defines prospective naming primitives only. Slice 1 intentionally
does not change any persisted Vitrine storage or Snapshot layout.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Final

VITRINE_PATH_POLICY_VERSION: Final[str] = "vitrine_path_policy_v1"

CUSTODY_TOKEN_HEX_LENGTH: Final[int] = 24
CUSTODY_TOKEN_PREFIX: Final[str] = "vp1_"
CUSTODY_TOKEN_MAX_LENGTH: Final[int] = (
    len(CUSTODY_TOKEN_PREFIX) + CUSTODY_TOKEN_HEX_LENGTH
)

PRESENTATION_DISAMBIGUATOR_HEX_LENGTH: Final[int] = 16
PRESENTATION_READABLE_STEM_MAX_LENGTH: Final[int] = 64
PRESENTATION_FILENAME_MAX_LENGTH: Final[int] = 96
PRESENTATION_DIRECTORY_MAX_LENGTH: Final[int] = 80
PRESENTATION_EXTENSION_MAX_LENGTH: Final[int] = 10
PRESENTATION_ORDINAL_MAX: Final[int] = 9999

_DOMAIN_RE: Final[re.Pattern[str]] = re.compile(
    r"[a-z][a-z0-9_.:-]{0,63}\Z"
)
_EXTENSION_RE: Final[re.Pattern[str]] = re.compile(r"\.[a-z0-9]{1,9}\Z")
_PORTABLE_COMPONENT_RE: Final[re.Pattern[str]] = re.compile(
    r"[a-z0-9][a-z0-9._-]*\Z"
)
_UNSAFE_SLUG_RUN_RE: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9]+")
_WINDOWS_RESERVED_COMPONENTS: Final[frozenset[str]] = frozenset(
    {
        "aux",
        "con",
        "nul",
        "prn",
        *(f"com{number}" for number in range(1, 10)),
        *(f"lpt{number}" for number in range(1, 10)),
    }
)


class VitrinePathPolicyError(ValueError):
    """A prospective Vitrine-generated filesystem name violates policy."""


def _validated_domain(domain: object) -> str:
    if not isinstance(domain, str) or _DOMAIN_RE.fullmatch(domain) is None:
        raise VitrinePathPolicyError(
            "domain must be a lowercase path-policy domain of at most 64 characters."
        )
    return domain


def _canonical_digest(*, domain: str, semantic_identity: object) -> str:
    validated_domain = _validated_domain(domain)
    try:
        encoded = json.dumps(
            {
                "contract_version": VITRINE_PATH_POLICY_VERSION,
                "domain": validated_domain,
                "semantic_identity": semantic_identity,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise VitrinePathPolicyError(
            "semantic_identity must be canonically JSON-serializable."
        ) from error
    return hashlib.sha256(encoded).hexdigest()


def build_bounded_custody_token(
    *,
    domain: str,
    semantic_identity: object,
) -> str:
    """Return a fixed-size opaque token for a Vitrine-owned custody component."""

    digest = _canonical_digest(
        domain=domain,
        semantic_identity=semantic_identity,
    )
    token = f"{CUSTODY_TOKEN_PREFIX}{digest[:CUSTODY_TOKEN_HEX_LENGTH]}"
    if len(token) != CUSTODY_TOKEN_MAX_LENGTH:
        raise AssertionError("custody token exceeded its fixed writer contract")
    return require_generated_component(
        token,
        maximum=CUSTODY_TOKEN_MAX_LENGTH,
        field_name="custody_token",
    )


def _readable_slug(preferred_label: str) -> str:
    normalized = unicodedata.normalize("NFKD", preferred_label)
    ascii_text = normalized.encode("ascii", errors="ignore").decode("ascii")
    slug = _UNSAFE_SLUG_RUN_RE.sub("-", ascii_text.casefold()).strip("-")
    return slug or "item"


def _validated_extension(extension: object) -> str:
    if not isinstance(extension, str) or _EXTENSION_RE.fullmatch(extension) is None:
        raise VitrinePathPolicyError(
            "extension must be a lowercase dot-prefixed alphanumeric extension "
            "of at most 10 characters."
        )
    if len(extension) > PRESENTATION_EXTENSION_MAX_LENGTH:
        raise VitrinePathPolicyError("extension exceeds the presentation budget.")
    return extension


def build_bounded_presentation_filename(
    preferred_label: str,
    *,
    semantic_domain: str,
    semantic_identity: object,
    extension: str,
) -> str:
    """Build one readable, deterministic, collision-resistant output filename."""

    if not isinstance(preferred_label, str):
        raise VitrinePathPolicyError("preferred_label must be text.")
    label = preferred_label.strip()
    if not label:
        raise VitrinePathPolicyError("preferred_label must be nonempty.")

    suffix = _validated_extension(extension)
    validated_semantic_domain = _validated_domain(semantic_domain)
    digest = _canonical_digest(
        domain="presentation-filename",
        semantic_identity={
            "semantic_domain": validated_semantic_domain,
            "value": semantic_identity,
        },
    )
    disambiguator = digest[:PRESENTATION_DISAMBIGUATOR_HEX_LENGTH]
    readable_budget = min(
        PRESENTATION_READABLE_STEM_MAX_LENGTH,
        PRESENTATION_FILENAME_MAX_LENGTH
        - len(suffix)
        - len("-")
        - PRESENTATION_DISAMBIGUATOR_HEX_LENGTH,
    )
    if readable_budget < 1:
        raise AssertionError("presentation filename budget is internally invalid")

    readable = _readable_slug(label)[:readable_budget].rstrip("-") or "item"
    filename = f"{readable}-{disambiguator}{suffix}"
    return require_generated_component(
        filename,
        maximum=PRESENTATION_FILENAME_MAX_LENGTH,
        field_name="presentation_filename",
    )


def build_bounded_presentation_directory_name(
    preferred_label: str,
    *,
    semantic_domain: str,
    semantic_identity: object,
    ordinal: int | None = None,
) -> str:
    """Build one readable, bounded, deterministic presentation directory name.

    The readable label is presentation-only. Exact identity remains structured
    canonical state and contributes only through a domain-separated digest.
    """

    if not isinstance(preferred_label, str):
        raise VitrinePathPolicyError("preferred_label must be text.")
    label = preferred_label.strip()
    if not label:
        raise VitrinePathPolicyError("preferred_label must be nonempty.")

    if ordinal is not None:
        if (
            isinstance(ordinal, bool)
            or not isinstance(ordinal, int)
            or ordinal < 1
            or ordinal > PRESENTATION_ORDINAL_MAX
        ):
            raise VitrinePathPolicyError(
                "ordinal must be an integer from 1 through "
                f"{PRESENTATION_ORDINAL_MAX}."
            )

    validated_semantic_domain = _validated_domain(semantic_domain)
    digest = _canonical_digest(
        domain="presentation-directory",
        semantic_identity={
            "semantic_domain": validated_semantic_domain,
            "value": semantic_identity,
            "ordinal": ordinal,
        },
    )
    disambiguator = digest[:PRESENTATION_DISAMBIGUATOR_HEX_LENGTH]
    ordinal_prefix = "" if ordinal is None else f"{ordinal:02d}-"
    readable_budget = min(
        PRESENTATION_READABLE_STEM_MAX_LENGTH,
        PRESENTATION_DIRECTORY_MAX_LENGTH
        - len(ordinal_prefix)
        - len("-")
        - PRESENTATION_DISAMBIGUATOR_HEX_LENGTH,
    )
    if readable_budget < 1:
        raise AssertionError("presentation directory budget is internally invalid")

    readable = _readable_slug(label)[:readable_budget].rstrip("-") or "item"
    directory = f"{ordinal_prefix}{readable}-{disambiguator}"
    return require_generated_component(
        directory,
        maximum=PRESENTATION_DIRECTORY_MAX_LENGTH,
        field_name="presentation_directory",
    )


def require_unique_presentation_components(
    components: tuple[str, ...],
) -> tuple[str, ...]:
    """Fail closed on portable case/Unicode collisions in one sibling set."""

    if not isinstance(components, tuple):
        raise VitrinePathPolicyError(
            "presentation component inventory must be a tuple."
        )
    seen: set[str] = set()
    for component in components:
        if not isinstance(component, str) or not component:
            raise VitrinePathPolicyError(
                "presentation component inventory contains invalid text."
            )
        normalized = unicodedata.normalize("NFC", component)
        collision_key = normalized.casefold()
        if collision_key in seen:
            raise VitrinePathPolicyError(
                "presentation component inventory contains a portable collision."
            )
        seen.add(collision_key)
    return components


def require_generated_component(
    value: object,
    *,
    maximum: int,
    field_name: str = "component",
) -> str:
    """Validate one Vitrine-generated portable ASCII filesystem component."""

    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 1:
        raise VitrinePathPolicyError("maximum must be a positive integer.")
    if not isinstance(value, str) or not value:
        raise VitrinePathPolicyError(f"{field_name} must be nonempty text.")
    if value in {".", ".."} or _PORTABLE_COMPONENT_RE.fullmatch(value) is None:
        raise VitrinePathPolicyError(
            f"{field_name} must be one lowercase portable ASCII filesystem component."
        )
    if value.endswith((".", " ")):
        raise VitrinePathPolicyError(
            f"{field_name} must not end with a dot or space."
        )
    windows_basename = value.split(".", 1)[0]
    if windows_basename in _WINDOWS_RESERVED_COMPONENTS:
        raise VitrinePathPolicyError(
            f"{field_name} must not use a reserved Windows device name."
        )
    if len(value.encode("utf-8")) > maximum:
        raise VitrinePathPolicyError(
            f"{field_name} exceeds its {maximum}-byte generated-component budget."
        )
    return value


__all__ = [
    "CUSTODY_TOKEN_HEX_LENGTH",
    "CUSTODY_TOKEN_MAX_LENGTH",
    "CUSTODY_TOKEN_PREFIX",
    "PRESENTATION_DIRECTORY_MAX_LENGTH",
    "PRESENTATION_DISAMBIGUATOR_HEX_LENGTH",
    "PRESENTATION_EXTENSION_MAX_LENGTH",
    "PRESENTATION_FILENAME_MAX_LENGTH",
    "PRESENTATION_ORDINAL_MAX",
    "PRESENTATION_READABLE_STEM_MAX_LENGTH",
    "VITRINE_PATH_POLICY_VERSION",
    "VitrinePathPolicyError",
    "build_bounded_custody_token",
    "build_bounded_presentation_directory_name",
    "build_bounded_presentation_filename",
    "require_generated_component",
    "require_unique_presentation_components",
]
