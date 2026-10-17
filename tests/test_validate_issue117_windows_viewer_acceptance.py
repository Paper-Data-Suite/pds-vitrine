"""#117 Slice 6: shell dispatch never implies human viewer accessibility."""

from __future__ import annotations

from copy import deepcopy

from scripts.validate_issue117_windows_viewer_acceptance import (
    CONTRACT,
    KINDS,
    report_findings,
)


def _report() -> dict[str, object]:
    targets = []
    for kind in KINDS:
        canonical = "C:\\synthetic\\" + "deep\\" * 48 + kind + ".pdf"
        targets.append(
            {
                "kind": kind,
                "canonical_path": canonical,
                "canonical_path_length": len(canonical),
                "canonical_sha256": "a" * 64 if kind in {"student_html", "printable_pdf"} else None,
                "shell_handoff": "returned",
                "handoff_content_matches": True,
                "handoff_path": canonical,
                "handoff_path_length": len(canonical),
                "viewer_accessibility": "pending",
            }
        )
    return {
        "contract": CONTRACT,
        "platform": "win32",
        "core_version": "0.6.5",
        "vitrine_version": "0.4.0",
        "synthetic_only": True,
        "canonical_verified": True,
        "targets": targets,
    }


def test_shell_return_without_real_viewer_confirmation_is_never_pass() -> None:
    record = _report()
    assert not report_findings(record, require_attested=False)
    assert report_findings(record, require_attested=True)


def test_four_human_confirmations_required() -> None:
    record = _report()
    for target in record["targets"]:
        target["viewer_accessibility"] = "confirmed"
    record["attestation_method"] = "interactive_human"
    assert not report_findings(record, require_attested=True)


def test_missing_handoff_cannot_be_manually_overridden() -> None:
    record = _report()
    for target in record["targets"]:
        target["viewer_accessibility"] = "confirmed"
    record["targets"][1]["shell_handoff"] = "failed"
    record["attestation_method"] = "interactive_human"
    assert report_findings(record, require_attested=True)


def test_non_windows_and_short_path_fail_closed() -> None:
    record = _report()
    record["platform"] = "linux"
    record["targets"][0]["canonical_path"] = "C:\\short\\portfolio.html"
    record["targets"][0]["canonical_path_length"] = len(
        record["targets"][0]["canonical_path"]
    )
    errors = "\n".join(report_findings(record, require_attested=False))
    assert "Windows" in errors and "260" in errors


def test_wrong_target_set_cannot_be_accepted() -> None:
    record = _report()
    record["targets"] = record["targets"][:3]
    assert report_findings(record, require_attested=False)


def test_digest_and_length_mismatches_are_detected() -> None:
    record = _report()
    record["targets"][0]["canonical_sha256"] = "bad"
    record["targets"][1]["handoff_path_length"] = -1
    assert len(report_findings(record, require_attested=False)) >= 2


def test_authorization_verification_flag_is_required() -> None:
    record = deepcopy(_report())
    record["canonical_verified"] = False
    assert report_findings(record, require_attested=False)


def test_new_core066_report_is_separate_from_historical_core065() -> None:
    record = _report()
    record["core_version"] = "0.6.6"
    for target in record["targets"]:
        target["viewer_accessibility"] = "confirmed"
    record["attestation_method"] = "interactive_human"
    assert report_findings(record, require_attested=True)
    assert report_findings(
        record, require_attested=True, expected_core_version="0.6.6"
    ) == ()


def test_shell_return_cannot_pass_core066_without_viewer_attestation() -> None:
    record = _report()
    record["core_version"] = "0.6.6"
    assert report_findings(
        record, require_attested=True, expected_core_version="0.6.6"
    )
