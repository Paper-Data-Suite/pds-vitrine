from __future__ import annotations

from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest

import vitrine.compatibility_cli as compatibility_cli
from vitrine.cli import main
from vitrine.compatibility_diagnostics import (
    CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION,
    CrossProducerCompatibilityDiagnostic,
    ProducerIntegrationReadiness,
)
from vitrine.workflow_context import default_workflow_dependencies

PUB = "pub_00000000000000000000000000000000"
PRIVATE = "PRIVATE-STUDENT-CONTENT-DO-NOT-PRINT"


def _diagnostic(
    *,
    outcome: str = "ready",
    code: str = "compatibility.publication_ready",
    stage: str = "publication_compatibility",
    producer: str | None = "scoreform",
    publication_id: str | None = PUB,
    safe_fields: tuple[tuple[str, str], ...] = (),
) -> CrossProducerCompatibilityDiagnostic:
    return CrossProducerCompatibilityDiagnostic(
        diagnostic_contract_version=(
            CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION
        ),
        scope="publication_compatibility",
        outcome=outcome,
        code=code,
        stage=stage,
        producer_module_id=producer,
        publication_id=publication_id,
        adapter_id=None,
        reason_codes=("compatibility.publication_ready",),
        safe_fields=safe_fields,
        summary="Safe compatibility summary.",
        next_action="Safe bounded next action.",
    )


def _readiness(producer: str, status: str) -> ProducerIntegrationReadiness:
    checks = tuple(
        CrossProducerCompatibilityDiagnostic(
            diagnostic_contract_version=(
                CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION
            ),
            scope="producer_readiness",
            outcome=(
                "not_applicable"
                if stage == "artifact_api" and producer == "scoreform"
                else status
            ),
            code=(
                "compatibility.artifact_api_not_applicable"
                if stage == "artifact_api" and producer == "scoreform"
                else "compatibility.producer_ready"
            ),
            stage=stage,
            producer_module_id=producer,
            publication_id=None,
            adapter_id=None,
            reason_codes=(
                "compatibility.artifact_api_not_applicable"
                if stage == "artifact_api" and producer == "scoreform"
                else "compatibility.producer_ready",
            ),
            safe_fields=(),
            summary="Safe readiness summary.",
            next_action="Safe readiness action.",
        )
        for stage in (
            "adapter_registry",
            "core_profile",
            "reader_distribution",
            "reader_api",
            "artifact_api",
        )
    )
    return ProducerIntegrationReadiness(
        producer_module_id=producer,
        overall=CrossProducerCompatibilityDiagnostic(
            diagnostic_contract_version=(
                CROSS_PRODUCER_COMPATIBILITY_DIAGNOSTIC_CONTRACT_VERSION
            ),
            scope="producer_readiness",
            outcome=status,
            code=(
                "compatibility.producer_ready"
                if status == "ready"
                else "compatibility.producer_not_ready"
            ),
            stage="producer_readiness",
            producer_module_id=producer,
            publication_id=None,
            adapter_id=None,
            reason_codes=(
                "compatibility.producer_ready"
                if status == "ready"
                else "compatibility.producer_not_ready",
            ),
            safe_fields=(),
            summary="Safe readiness summary.",
            next_action="Safe readiness action.",
        ),
        checks=checks,
    )


def test_compatibility_producers_is_deterministic_and_observational(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        compatibility_cli,
        "diagnose_installed_producer_readiness",
        lambda **_: (
            _readiness("scoreform", "unavailable"),
            _readiness("quillan", "ready"),
            _readiness("concord", "ready"),
        ),
    )
    out = StringIO()
    err = StringIO()
    assert main(["compatibility", "producers"], output=out, error=err) == 0
    rows = out.getvalue().splitlines()
    assert rows[1].startswith("concord\t")
    assert rows[2].startswith("quillan\t")
    assert rows[3].startswith("scoreform\t")
    assert "not_applicable" in rows[3]
    assert err.getvalue() == ""


def test_contract_diagnostic_needs_no_workspace() -> None:
    out = StringIO()
    err = StringIO()
    code = main(
        [
            "compatibility",
            "contract",
            "--producer",
            "quillan",
            "--core-publication-schema-version",
            "1",
            "--publication-kind",
            "academic_result_set",
            "--manifest-contract-version",
            "quillan_academic_result_manifest_v1",
            "--producer-contract-version",
            "quillan_academic_work_v1",
            "--capability",
            "standards_ratings",
        ],
        output=out,
        error=err,
    )
    assert code == 0
    rendered = out.getvalue()
    assert "Status: supported" in rendered
    assert "Producer: quillan" in rendered
    assert "Technical:" in rendered
    assert err.getvalue() == ""


def test_contract_diagnostic_explains_source_presence_without_fallback() -> None:
    out = StringIO()
    err = StringIO()
    code = main(
        [
            "compatibility",
            "contract",
            "--producer",
            "quillan",
            "--core-publication-schema-version",
            "1",
            "--publication-kind",
            "academic_result_set",
            "--manifest-contract-version",
            "quillan_academic_result_manifest_v1",
            "--producer-contract-version",
            "quillan_academic_work_v1",
            "--source-record-kind",
            "assignment",
            "--source-record-contract-version",
            "2",
            "--capability",
            "standards_ratings",
        ],
        output=out,
        error=err,
    )
    assert code == 1
    rendered = out.getvalue()
    assert "adapter.unsupported_contract" in rendered
    assert "actual_source_record_kind: assignment" in rendered
    assert "expected_source_record_kind: <absent>" in rendered
    assert "nearest" not in rendered.lower()
    assert err.getvalue() == ""


def test_publication_metadata_command_does_not_request_read_probe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    report = SimpleNamespace(
        overall=_diagnostic(),
        checks=(_diagnostic(stage="canonical_publication"),),
        ready=True,
    )
    monkeypatch.setattr(
        compatibility_cli,
        "show_workspace",
        lambda _root: SimpleNamespace(root=tmp_path),
    )
    monkeypatch.setattr(
        compatibility_cli,
        "diagnose_publication_compatibility",
        lambda *_args, **_kwargs: calls.append("metadata") or report,
    )
    monkeypatch.setattr(
        compatibility_cli,
        "diagnose_publication_read_probe",
        lambda *_args, **_kwargs: calls.append("read") or report,
    )
    out = StringIO()
    err = StringIO()
    assert (
        main(
            ["compatibility", "publication", PUB, "--workspace-root", str(tmp_path)],
            output=out,
            error=err,
        )
        == 0
    )
    assert calls == ["metadata"]
    assert "canonical_publication\tready" in out.getvalue()


def test_verify_read_requires_explicit_portfolio_context() -> None:
    out = StringIO()
    err = StringIO()
    assert main(
        ["compatibility", "publication", PUB, "--verify-read"],
        output=out,
        error=err,
    ) == 1
    assert "--portfolio-id" in err.getvalue()
    assert "--portfolio-subject-id" in err.getvalue()
    assert "--purpose" in err.getvalue()


def test_verify_read_uses_injected_source_authorization_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dependencies = default_workflow_dependencies()
    captured: dict[str, object] = {}
    check = _diagnostic(
        outcome="denied",
        code="source_read.authorization_denied",
        stage="source_authorization",
        safe_fields=(("protected_source_inspected", "no"),),
    )
    check = CrossProducerCompatibilityDiagnostic(
        diagnostic_contract_version=check.diagnostic_contract_version,
        scope="source_read",
        outcome=check.outcome,
        code=check.code,
        stage=check.stage,
        producer_module_id=check.producer_module_id,
        publication_id=check.publication_id,
        adapter_id=None,
        reason_codes=("compatibility.source_read_denied",),
        safe_fields=check.safe_fields,
        summary=check.summary,
        next_action=check.next_action,
    )
    report = SimpleNamespace(
        overall=check,
        checks=(check,),
        ready=False,
        projected_source_count=None,
    )

    monkeypatch.setattr(
        compatibility_cli,
        "show_workspace",
        lambda _root: SimpleNamespace(root=tmp_path),
    )

    def fake_probe(*_args: object, **kwargs: object) -> object:
        captured.update(kwargs)
        return report

    monkeypatch.setattr(
        compatibility_cli,
        "diagnose_publication_read_probe",
        fake_probe,
    )
    out = StringIO()
    err = StringIO()
    code = main(
        [
            "compatibility",
            "publication",
            PUB,
            "--verify-read",
            "--portfolio-id",
            "portfolio_alpha",
            "--portfolio-subject-id",
            "subject_alpha",
            "--purpose",
            "diagnose_source",
        ],
        output=out,
        error=err,
        dependencies=dependencies,
    )
    assert code == 1
    assert captured["authorization_gate"] is dependencies.source_read_authorization_gate
    assert "Protected source inspected: no" in out.getvalue()
    assert PRIVATE not in out.getvalue()
    assert PRIVATE not in err.getvalue()


def test_arbitrary_service_exception_text_never_reaches_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(**_kwargs: object) -> object:
        raise RuntimeError(PRIVATE)

    monkeypatch.setattr(
        compatibility_cli,
        "diagnose_installed_producer_readiness",
        fail,
    )
    out = StringIO()
    err = StringIO()
    assert main(["compatibility", "producers"], output=out, error=err) == 1
    assert PRIVATE not in out.getvalue()
    assert PRIVATE not in err.getvalue()
    assert "Compatibility diagnostics could not be completed safely." in err.getvalue()
