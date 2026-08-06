#!/usr/bin/env python3
"""Validate Vitrine's representative synthetic Portfolio corpus."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

VERSION = "1"
CORPUS = "pds-vitrine.representative-portfolio-corpus"
PORTFOLIO = "pds-vitrine.representative-portfolio"
MANIFEST = "pds-vitrine.synthetic-snapshot-manifest"
NEGATIVES = "pds-vitrine.representative-portfolio-negative-cases"


class FixtureError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def fail(code: str, detail: str) -> NoReturn:
    raise FixtureError(code, detail)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail("file.missing", path.as_posix())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail("json.invalid", f"{path.as_posix()}: {exc}")
    if not isinstance(value, dict):
        fail("json.object_required", path.as_posix())
    return value


def check_contract(data: dict[str, Any], expected: str, path: Path) -> None:
    if data.get("fixture_contract") != expected:
        fail("contract.invalid", path.as_posix())
    if data.get("fixture_version") != VERSION:
        fail("contract.unsupported_version", path.as_posix())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reject_link(path: Path) -> None:
    is_junction = getattr(path, "is_junction", None)
    if path.is_symlink() or (callable(is_junction) and is_junction()):
        fail("path.link_prohibited", path.as_posix())


def safe_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        fail("path.unsafe", repr(value))
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        fail("path.unsafe", value)
    if path.parts and ":" in path.parts[0]:
        fail("path.unsafe", value)
    return path


def collect_ids(data: dict[str, Any], path: Path) -> set[str]:
    records = data.get("records")
    if not isinstance(records, list):
        fail("records.invalid", path.as_posix())
    ids: set[str] = set()
    for item in records:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            fail("records.invalid", path.as_posix())
        if item["id"] in ids:
            fail("records.duplicate_id", item["id"])
        ids.add(item["id"])
    return ids


def check_refs(records: list[dict[str, Any]], allowed: set[str]) -> None:
    for item in records:
        refs = item.get("refs", [])
        if not isinstance(refs, list) or not all(isinstance(ref, str) for ref in refs):
            fail("records.invalid_refs", str(item.get("id")))
        for ref in refs:
            if ref not in allowed:
                fail("records.dangling_reference", f"{item['id']} -> {ref}")


def inventory_digest(entries: list[dict[str, Any]]) -> str:
    text = "".join(
        f"{entry['sequence']}|{entry['relative_path']}|{entry['sha256']}|{entry['size']}\n"
        for entry in entries
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def trigger_negative(case: dict[str, Any]) -> None:
    code = case.get("expected_error")
    p = case.get("payload")
    if not isinstance(code, str) or not isinstance(p, dict):
        fail("negative.invalid_case", str(case.get("case_id")))
    tests = {
        "identity.name_only_match": p.get("match_basis") == "name_only",
        "source.catalog_without_canonical_verification": p.get("catalog_only") is True,
        "source.unsupported_producer_contract": p.get("producer_contract_supported") is False,
        "integrity.digest_mismatch": p.get("declared_sha256") != p.get("actual_sha256"),
        "curation.silent_source_replacement": p.get("selected_source_id") != p.get("snapshot_source_id") and not p.get("replacement_record"),
        "concord.group_membership_as_authorship": p.get("authorship_basis") == "group_membership",
        "concord.group_score_as_individual_score": p.get("score_target") == "group" and p.get("claimed_target") == "individual",
        "quillan.private_material_in_audience_package": p.get("audience") == "parent_guardian_facing" and "private_notes" in p.get("fields", []),
        "scoreform.secure_material_exposed": "answer_key" in p.get("fields", []),
        "portia.suppressed_existence_leak": "PORTIA-RESTRICTED-MARKER" in p.get("audience_text", ""),
        "snapshot.internal_manifest_distributed": "internal_snapshot_manifest" in p.get("audience_entries", []),
        "snapshot.audience_content_changed_without_new_edition": p.get("edition_before") == p.get("edition_after") and p.get("digest_before") != p.get("digest_after"),
        "regulated.checklist_satisfied_without_evidence": p.get("finding") == "satisfied" and not p.get("evidence_refs"),
        "regulated.attestation_as_approval": p.get("approval_basis") == "attestation_only",
        "regulated.resubmission_overwrites_predecessor": p.get("correction") is True and p.get("predecessor_preserved") is False,
        "authorization.indeterminate_treated_as_allowed": p.get("decision") == "indeterminate" and p.get("action_executed") is True,
        "snapshot.duplicate_entry_path": len(p.get("paths", [])) != len(set(p.get("paths", []))),
        "snapshot.manifest_order_mismatch": p.get("sequences") != sorted(p.get("sequences", [])),
        "snapshot.issued_edition_silently_refreshed": p.get("issued") is True and p.get("source_digest_before") != p.get("source_digest_after") and p.get("edition_changed") is False,
    }
    if code == "path.unsafe":
        safe_path(str(p.get("path", "")))
        fail("negative.did_not_fail", str(case.get("case_id")))
    if tests.get(code):
        fail(code, str(case.get("case_id")))
    fail("negative.did_not_fail", str(case.get("case_id")))


def validate() -> tuple[int, int, int, int]:
    repo = Path(__file__).resolve().parents[1]
    root = repo / "fixtures" / "representative-portfolios"
    corpus_path = root / "corpus.json"
    for path in root.rglob("*"):
        reject_link(path)
    corpus = load_json(corpus_path)
    check_contract(corpus, CORPUS, corpus_path)
    if corpus.get("not_runtime_contract") is not True:
        fail("contract.runtime_claim", corpus_path.as_posix())

    shared_ids: set[str] = set()
    shared_files = corpus.get("shared_record_files")
    if not isinstance(shared_files, list):
        fail("corpus.invalid_shared_files", corpus_path.as_posix())
    for value in shared_files:
        path = root / safe_path(value)
        data = load_json(path)
        ids = collect_ids(data, path)
        if shared_ids & ids:
            fail("records.duplicate_shared_id", sorted(shared_ids & ids)[0])
        shared_ids |= ids

    artifact_path = root / safe_path(corpus["artifact_index"])
    artifact_index = load_json(artifact_path)
    check_contract(artifact_index, "pds-vitrine.synthetic-artifact-index", artifact_path)
    artifacts = artifact_index.get("artifacts")
    if not isinstance(artifacts, list):
        fail("artifacts.invalid", artifact_path.as_posix())
    artifact_ids: set[str] = set()
    for item in artifacts:
        source_id = item.get("source_id")
        if not isinstance(source_id, str) or source_id in artifact_ids:
            fail("artifacts.duplicate_or_invalid_id", str(source_id))
        artifact_ids.add(source_id)
        path = root / safe_path(item["path"])
        if not path.is_file():
            fail("file.missing", path.as_posix())
        if digest(path) != item.get("sha256"):
            fail("integrity.digest_mismatch", source_id)
        if path.stat().st_size != item.get("size"):
            fail("integrity.size_mismatch", source_id)
    shared_ids |= artifact_ids

    forbidden = corpus.get("forbidden_audience_markers")
    if not isinstance(forbidden, list) or not all(isinstance(x, str) for x in forbidden):
        fail("corpus.invalid_forbidden_markers", corpus_path.as_posix())

    global_ids: set[str] = set()
    portfolio_count = entry_count = 0
    byte_count = len(artifacts)
    for index in corpus.get("portfolios", []):
        fixture_path = root / safe_path(index["fixture"])
        expected_path = root / safe_path(index["expected"])
        walkthrough = root / safe_path(index["walkthrough"])
        if not walkthrough.is_file():
            fail("file.missing", walkthrough.as_posix())
        fixture = load_json(fixture_path)
        check_contract(fixture, PORTFOLIO, fixture_path)
        if fixture.get("portfolio_id") != index.get("portfolio_id"):
            fail("portfolio.id_mismatch", fixture_path.as_posix())
        records = fixture.get("records")
        if not isinstance(records, list):
            fail("records.invalid", fixture_path.as_posix())
        local_ids = collect_ids(fixture, fixture_path)
        if global_ids & local_ids:
            fail("records.duplicate_corpus_id", sorted(global_ids & local_ids)[0])
        global_ids |= local_ids
        check_refs(records, shared_ids | local_ids)

        for source_id in fixture.get("source_artifacts", []):
            if source_id not in artifact_ids:
                fail("artifacts.unknown_source", source_id)
        exclusions = fixture.get("exclusions", [])
        if not isinstance(exclusions, list):
            fail("portfolio.invalid_exclusions", fixture_path.as_posix())
        for exclusion in exclusions:
            if exclusion.get("source_id") not in artifact_ids:
                fail("artifacts.unknown_exclusion", str(exclusion.get("source_id")))
            if exclusion.get("reason_code") == "suppressed_no_existence_disclosure" and exclusion.get("audience_visible_notice") is not False:
                fail("portia.suppressed_existence_leak", fixture_path.as_posix())

        snapshot = fixture.get("snapshot")
        if not isinstance(snapshot, dict):
            fail("snapshot.invalid", fixture_path.as_posix())
        manifest_path = root / safe_path(snapshot["manifest_path"])
        manifest = load_json(manifest_path)
        check_contract(manifest, MANIFEST, manifest_path)
        if digest(manifest_path) != snapshot.get("manifest_sha256"):
            fail("snapshot.manifest_digest_mismatch", fixture_path.as_posix())
        for left, right, code in [
            (manifest.get("snapshot_edition_id"), snapshot.get("edition_id"), "snapshot.edition_mismatch"),
            (manifest.get("composition_revision_id"), snapshot.get("composition_revision_id"), "snapshot.composition_mismatch"),
            (manifest.get("audience_context_id"), snapshot.get("audience_context_id"), "snapshot.audience_mismatch"),
        ]:
            if left != right:
                fail(code, fixture_path.as_posix())
        omissions = manifest.get("omissions", [])
        if not isinstance(omissions, list):
            fail("snapshot.omissions_invalid", manifest_path.as_posix())
        omission_ids: set[str] = set()
        for omission in omissions:
            omission_id = omission.get("omission_id")
            if not isinstance(omission_id, str) or omission_id in omission_ids:
                fail("snapshot.omissions_invalid", manifest_path.as_posix())
            omission_ids.add(omission_id)
            if omission.get("reason_code") == "restricted_source_unverified" and omission.get("audience_visible") is not False:
                fail("snapshot.restricted_omission_visible", omission_id)
        entries = manifest.get("entries")
        if not isinstance(entries, list) or not entries:
            fail("snapshot.entries_invalid", manifest_path.as_posix())
        sequences = [entry.get("sequence") for entry in entries]
        if sequences != list(range(1, len(entries) + 1)):
            fail("snapshot.manifest_order_mismatch", manifest_path.as_posix())
        entry_ids = [entry.get("entry_id") for entry in entries]
        paths = [entry.get("relative_path") for entry in entries]
        if len(entry_ids) != len(set(entry_ids)):
            fail("snapshot.duplicate_entry_id", manifest_path.as_posix())
        if len(paths) != len(set(paths)):
            fail("snapshot.duplicate_entry_path", manifest_path.as_posix())
        if inventory_digest(entries) != snapshot.get("logical_inventory_sha256"):
            fail("snapshot.logical_inventory_digest_mismatch", fixture_path.as_posix())

        export_root = root / safe_path(snapshot["export_root"])
        declared: set[str] = set()
        for entry in entries:
            relative = safe_path(entry["relative_path"])
            declared.add(relative.as_posix())
            output = export_root / relative
            if not output.is_file():
                fail("file.missing", output.as_posix())
            if output.stat().st_size != entry.get("size"):
                fail("integrity.size_mismatch", entry["entry_id"])
            if digest(output) != entry.get("sha256"):
                fail("integrity.digest_mismatch", entry["entry_id"])
            if entry.get("materialization_kind") == "exact_byte_copy":
                source = root / safe_path(entry.get("source_path", ""))
                if not source.is_file() or source.read_bytes() != output.read_bytes():
                    fail("snapshot.exact_copy_mismatch", entry["entry_id"])
            content = output.read_bytes()
            for marker in forbidden:
                if marker in relative.as_posix() or marker.encode("utf-8") in content:
                    fail("audience.forbidden_marker", f"{index['portfolio_id']}:{marker}")
        actual = {p.relative_to(export_root).as_posix() for p in export_root.rglob("*") if p.is_file()}
        if actual != declared:
            fail("snapshot.undeclared_audience_file", index["portfolio_id"])
        if manifest_path.is_relative_to(export_root):
            fail("snapshot.internal_manifest_distributed", index["portfolio_id"])

        expected = load_json(expected_path)
        if expected.get("expected_result") != "pass":
            fail("expected.invalid_result", expected_path.as_posix())
        if expected.get("included_entry_ids") != entry_ids:
            fail("expected.entry_mismatch", expected_path.as_posix())
        if expected.get("excluded_source_ids") != [x["source_id"] for x in exclusions]:
            fail("expected.exclusion_mismatch", expected_path.as_posix())

        for item in fixture.get("external_artifacts", []):
            path = root / safe_path(item["path"])
            if not path.is_file() or digest(path) != item.get("sha256") or path.stat().st_size != item.get("size"):
                fail("external.artifact_mismatch", item.get("path", "unknown"))
            byte_count += 1

        portfolio_count += 1
        entry_count += len(entries)
        byte_count += len(entries)

    negative_path = root / safe_path(corpus["negative_cases"])
    negative_data = load_json(negative_path)
    check_contract(negative_data, NEGATIVES, negative_path)
    cases = negative_data.get("cases")
    if not isinstance(cases, list) or not cases:
        fail("negative.invalid_cases", negative_path.as_posix())
    seen: set[str] = set()
    for case in cases:
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or case_id in seen:
            fail("negative.duplicate_case_id", str(case_id))
        seen.add(case_id)
        try:
            trigger_negative(case)
        except FixtureError as exc:
            if exc.code != case.get("expected_error"):
                fail("negative.wrong_error", f"{case_id}: {exc.code}")
        else:
            fail("negative.did_not_fail", case_id)

    return portfolio_count, len(cases), entry_count, byte_count


def main() -> int:
    try:
        portfolios, negatives, entries, byte_files = validate()
    except FixtureError as exc:
        print(f"FAIL {exc.code}: {exc.detail}", file=sys.stderr)
        return 1
    print(
        f"PASS representative Portfolio corpus: {portfolios} portfolios, "
        f"{entries} Snapshot Entries, {negatives} negative cases, "
        f"{byte_files} verified byte files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
