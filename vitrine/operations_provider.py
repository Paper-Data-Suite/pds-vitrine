"""Core v1 adapters for Vitrine readiness and teacher attention."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from pds_core.module_operations import (
    ModuleAttentionReport,
    ModuleAttentionSummary,
    ModuleOperationsNotice,
    ModuleOperationsRequest,
    ModuleOwnerActionRef,
    ModuleReadinessReport,
    validate_module_attention_report,
    validate_module_operations_request,
    validate_module_readiness_report,
)
from pds_core.workspace import WorkspaceRootError, inspect_workspace_root

from vitrine.attention import (
    VitrineAttentionNotice,
    VitrineAttentionReport,
    VitrineAttentionSummary,
    evaluate_vitrine_attention,
)
from vitrine.constants import VITRINE_MODULE_ID
from vitrine.storage import audit_canonical_storage, vitrine_root

VITRINE_READINESS_WORKSPACE_REQUIRED: Final[str] = (
    "vitrine_readiness_workspace_required"
)
VITRINE_READINESS_WORKSPACE_UNAVAILABLE: Final[str] = (
    "vitrine_readiness_workspace_unavailable"
)
VITRINE_READINESS_WORKSPACE_NOT_WRITABLE: Final[str] = (
    "vitrine_readiness_workspace_not_writable"
)
VITRINE_READINESS_STORAGE_BLOCKED: Final[str] = "vitrine_readiness_storage_blocked"
VITRINE_READINESS_UNAVAILABLE: Final[str] = "vitrine_readiness_unavailable"
VITRINE_ATTENTION_WORKSPACE_REQUIRED: Final[str] = (
    "vitrine_attention_workspace_required"
)
VITRINE_ATTENTION_CLASS_SCOPE_UNSUPPORTED: Final[str] = (
    "vitrine_attention_class_scope_unsupported"
)


def _validate_readiness(
    report: ModuleReadinessReport,
) -> ModuleReadinessReport:
    return validate_module_readiness_report(
        report,
        expected_module_id=VITRINE_MODULE_ID,
    )


def _validate_attention(
    report: ModuleAttentionReport,
) -> ModuleAttentionReport:
    return validate_module_attention_report(
        report,
        expected_module_id=VITRINE_MODULE_ID,
    )


def _readiness_unavailable(code: str, summary: str) -> ModuleReadinessReport:
    return _validate_readiness(
        ModuleReadinessReport(
            evaluation="unavailable",
            ready=None,
            notices=(ModuleOperationsNotice(code=code, summary=summary),),
        )
    )


def _readiness_blocked(code: str, summary: str) -> ModuleReadinessReport:
    return _validate_readiness(
        ModuleReadinessReport(
            evaluation="evaluated",
            ready=False,
            notices=(ModuleOperationsNotice(code=code, summary=summary),),
        )
    )


def _readiness_ready() -> ModuleReadinessReport:
    return _validate_readiness(
        ModuleReadinessReport(
            evaluation="evaluated",
            ready=True,
            notices=(),
        )
    )


def evaluate_vitrine_readiness(
    request: ModuleOperationsRequest,
    /,
) -> ModuleReadinessReport:
    """Evaluate workspace-level Vitrine operational readiness without mutation."""
    if not isinstance(request, ModuleOperationsRequest):
        raise TypeError("request must be a ModuleOperationsRequest.")
    validate_module_operations_request(request)

    if request.workspace_root is None:
        return _readiness_unavailable(
            VITRINE_READINESS_WORKSPACE_REQUIRED,
            "Vitrine readiness requires an explicit workspace.",
        )

    try:
        workspace = inspect_workspace_root(request.workspace_root)
    except WorkspaceRootError:
        return _readiness_unavailable(
            VITRINE_READINESS_WORKSPACE_UNAVAILABLE,
            "The requested workspace cannot be inspected safely for Vitrine readiness.",
        )

    if not workspace.exists or not workspace.is_dir:
        return _readiness_unavailable(
            VITRINE_READINESS_WORKSPACE_UNAVAILABLE,
            "The requested workspace is not an existing directory.",
        )
    if not workspace.is_writable:
        return _readiness_blocked(
            VITRINE_READINESS_WORKSPACE_NOT_WRITABLE,
            "Vitrine cannot operate normally because the requested workspace is not writable.",
        )

    try:
        namespace = vitrine_root(workspace.root)
        namespace.lstat()
    except FileNotFoundError:
        # A valid workspace in which Vitrine has never created canonical state is
        # ready to begin. Readiness is not a Portfolio-presence check.
        return _readiness_ready()
    except (OSError, WorkspaceRootError):
        return _readiness_unavailable(
            VITRINE_READINESS_UNAVAILABLE,
            "Vitrine readiness could not inspect its workspace namespace safely.",
        )

    try:
        issues = audit_canonical_storage(workspace.root)
    except (OSError, WorkspaceRootError):
        return _readiness_unavailable(
            VITRINE_READINESS_UNAVAILABLE,
            "Vitrine readiness could not inspect canonical state safely.",
        )

    if issues:
        return _readiness_blocked(
            VITRINE_READINESS_STORAGE_BLOCKED,
            "Vitrine canonical state requires owner review before normal operation.",
        )
    return _readiness_ready()


def _attention_unavailable(code: str, summary: str) -> ModuleAttentionReport:
    return _validate_attention(
        ModuleAttentionReport(
            evaluation="unavailable",
            summaries=(),
            notices=(ModuleOperationsNotice(code=code, summary=summary),),
        )
    )


def _map_notice(notice: VitrineAttentionNotice) -> ModuleOperationsNotice:
    return ModuleOperationsNotice(code=notice.code, summary=notice.summary)


def _map_summary(summary: VitrineAttentionSummary) -> ModuleAttentionSummary:
    action = summary.next_action
    return ModuleAttentionSummary(
        code=summary.code,
        label=summary.label,
        count=summary.count,
        class_id=None,
        work_ref=None,
        action=(
            None
            if action is None
            else ModuleOwnerActionRef(
                module_id=VITRINE_MODULE_ID,
                action_id=action.action_id,
            )
        ),
    )


def project_vitrine_attention_to_core(
    report: VitrineAttentionReport,
    /,
) -> ModuleAttentionReport:
    """Purely map one validated native attention report into Core v1."""
    if not isinstance(report, VitrineAttentionReport):
        raise TypeError("report must be a VitrineAttentionReport.")

    notices = tuple(_map_notice(item) for item in report.notices)
    if report.evaluation == "unavailable":
        return _validate_attention(
            ModuleAttentionReport(
                evaluation="unavailable",
                summaries=(),
                notices=notices,
            )
        )

    return _validate_attention(
        ModuleAttentionReport(
            evaluation="evaluated",
            summaries=tuple(_map_summary(item) for item in report.summaries),
            notices=notices,
        )
    )


def evaluate_vitrine_attention_for_core(
    request: ModuleOperationsRequest,
    /,
) -> ModuleAttentionReport:
    """Evaluate Vitrine attention under the deliberately bounded Core v1 scope."""
    if not isinstance(request, ModuleOperationsRequest):
        raise TypeError("request must be a ModuleOperationsRequest.")
    validate_module_operations_request(request)

    if request.class_id is not None:
        return _attention_unavailable(
            VITRINE_ATTENTION_CLASS_SCOPE_UNSUPPORTED,
            (
                "Vitrine Portfolio attention may span classes and cannot be safely "
                "reduced to the requested class; use unfiltered Vitrine attention."
            ),
        )
    if request.workspace_root is None:
        return _attention_unavailable(
            VITRINE_ATTENTION_WORKSPACE_REQUIRED,
            "Vitrine attention requires an explicit workspace.",
        )

    native = evaluate_vitrine_attention(Path(request.workspace_root))
    return project_vitrine_attention_to_core(native)


__all__ = [
    "VITRINE_ATTENTION_CLASS_SCOPE_UNSUPPORTED",
    "VITRINE_ATTENTION_WORKSPACE_REQUIRED",
    "VITRINE_READINESS_STORAGE_BLOCKED",
    "VITRINE_READINESS_UNAVAILABLE",
    "VITRINE_READINESS_WORKSPACE_NOT_WRITABLE",
    "VITRINE_READINESS_WORKSPACE_REQUIRED",
    "VITRINE_READINESS_WORKSPACE_UNAVAILABLE",
    "evaluate_vitrine_attention_for_core",
    "evaluate_vitrine_readiness",
    "project_vitrine_attention_to_core",
]
