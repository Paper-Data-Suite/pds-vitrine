"""Installed Vitrine module-operations profile for Core contract v1."""

from __future__ import annotations

from pds_core.module_operations import (
    MODULE_OPERATIONS_CONTRACT_VERSION,
    ModuleAttentionReport,
    ModuleOperationsProfile,
    ModuleOperationsRequest,
    ModuleReadinessReport,
    validate_module_operations_profile,
)

from vitrine.constants import VITRINE_MODULE_ID


def evaluate_vitrine_readiness(
    request: ModuleOperationsRequest,
    /,
) -> ModuleReadinessReport:
    """Lazily invoke Vitrine's workspace-level readiness adapter."""
    from vitrine.operations_provider import evaluate_vitrine_readiness as _evaluate

    return _evaluate(request)


def evaluate_vitrine_attention_for_core(
    request: ModuleOperationsRequest,
    /,
) -> ModuleAttentionReport:
    """Lazily invoke the Core adapter over Vitrine's native attention service."""
    from vitrine.operations_provider import (
        evaluate_vitrine_attention_for_core as _evaluate,
    )

    return _evaluate(request)


def get_module_operations_profile() -> ModuleOperationsProfile:
    """Return Vitrine's validated Core v1 module-operations profile."""
    return validate_module_operations_profile(
        ModuleOperationsProfile(
            module_id=VITRINE_MODULE_ID,
            supported_core_operations_contract_versions=frozenset(
                {MODULE_OPERATIONS_CONTRACT_VERSION}
            ),
            readiness_provider=evaluate_vitrine_readiness,
            attention_provider=evaluate_vitrine_attention_for_core,
        )
    )


__all__ = [
    "evaluate_vitrine_attention_for_core",
    "evaluate_vitrine_readiness",
    "get_module_operations_profile",
]
