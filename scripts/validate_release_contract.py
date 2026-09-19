"""Validate the pds-vitrine v0.3.0 release identity and scope boundary."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

from vitrine.candidate_services import SourceReadAuthorizationRequest
from vitrine.curation_services import CurationAuthorityRequest
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.models import ActorAttribution
from vitrine.models.profiles import PROFILE_PURPOSE_KINDS
from vitrine.producer_adapters import (
    ProducerAdapterError,
    ProducerAdapterSupportRequest,
    ProducerAdapterUnsupportedError,
    build_adapter_registry,
)
from vitrine.snapshot_materialization import SnapshotBuildAuthorityRequest
from vitrine.snapshot_planning import UnconfiguredSnapshotPlanningProvider
from vitrine.workflow_context import default_workflow_dependencies

EXPECTED_VERSION = "0.3.0"
EXPECTED_CORE_REQUIREMENT = "pds-core>=0.6.3,<0.7"
CURRENT_DEVELOPMENT_CORE_REQUIREMENT = "pds-core>=0.6.3,<0.7"
EXPECTED_CORE_WHEEL = "pds_core-0.6.3-py3-none-any.whl"
EXPECTED_CORE_SHA256 = (
    "98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5"
)
EXPECTED_CONSOLE_SCRIPT = {"vitrine": "vitrine.cli:main"}
EXPECTED_OPERATIONS_ENTRY_POINTS = {
    "paper_data_suite.module_operations": {
        "vitrine": "vitrine.pds_operations:get_module_operations_profile"
    }
}
EXPECTED_FIXTURE_PRODUCER_IDS = (
    "vitrine_concord_fixture",
    "vitrine_quillan_fixture",
    "vitrine_scoreform_fixture",
)
EXPECTED_FIXTURE_ADAPTER_IDS = (
    "vitrine_concord_fixture_adapter",
    "vitrine_quillan_fixture_adapter",
    "vitrine_scoreform_fixture_adapter",
)
EXPECTED_PURPOSE_KINDS = frozenset(
    {"improvement", "showcase", "parent_guardian_conference", "regulated"}
)
FORBIDDEN_ENTRY_POINT_GROUPS = (
    "paper_data_suite.modules",
    "paper_data_suite.publication_producers",
)
FORBIDDEN_RUNTIME_DEPENDENCIES = (
    "scoreform",
    "quillan",
    "concord",
    "portia",
    "meridian",
)


def _version_from_source(root: Path) -> str | None:
    text = (root / "vitrine/_version.py").read_text(encoding="utf-8")
    match = re.fullmatch(
        r'"""Authoritative Vitrine package version\."""\n\n'
        r'__version__ = "([^"]+)"\n',
        text,
    )
    return None if match is None else match.group(1)


def _actor() -> ActorAttribution:
    return ActorAttribution(
        actor_kind="authorized_adult",
        actor_id="release_contract_auditor",
        owning_system="vitrine",
        role_snapshot="release_audit",
    )


def _live_support_requests() -> dict[str, ProducerAdapterSupportRequest]:
    return {
        "scoreform": ProducerAdapterSupportRequest(
            producer_module_id="scoreform",
            core_publication_schema_version="1",
            publication_kind="academic_result_set",
            manifest_contract_version="scoreform_academic_result_manifest_v1",
            producer_contract_version="scoreform_academic_work_v1",
            source_record_kind=None,
            source_record_contract_version=None,
            capabilities=("points", "question_evidence", "multiple_attempts"),
        ),
        "quillan": ProducerAdapterSupportRequest(
            producer_module_id="quillan",
            core_publication_schema_version="1",
            publication_kind="academic_result_set",
            manifest_contract_version="quillan_academic_result_manifest_v1",
            producer_contract_version="quillan_academic_work_v1",
            source_record_kind=None,
            source_record_contract_version=None,
            capabilities=("standards_ratings",),
        ),
        "concord": ProducerAdapterSupportRequest(
            producer_module_id="concord",
            core_publication_schema_version="1",
            publication_kind="academic_result_set",
            manifest_contract_version="concord_academic_result_manifest_v1",
            producer_contract_version="concord_academic_work_v1",
            source_record_kind="activity",
            source_record_contract_version="concord_activity_v1",
            capabilities=(
                "criterion_scores",
                "moderated_scores",
                "standards_ratings",
            ),
        ),
    }


def _runtime_boundary_findings() -> list[str]:
    findings: list[str] = []
    defaults = default_workflow_dependencies()

    if defaults.producer_registry.profiles != ():
        findings.append("default workflow producer registry is not empty")
    if defaults.adapter_registry.adapters != ():
        findings.append("default workflow adapter registry is not empty")
    if defaults.development_fixture_mode is not False:
        findings.append("default workflow dependencies enable fixture mode")
    if defaults.snapshot_source_providers._providers != ():
        findings.append("default Snapshot source-provider registry is not empty")
    if defaults.snapshot_renderers._renderers != ():
        findings.append("default Snapshot renderer registry is not empty")
    if not isinstance(
        defaults.snapshot_planning_provider, UnconfiguredSnapshotPlanningProvider
    ):
        findings.append("default Snapshot planning provider is configured")

    actor = _actor()
    source_decision = defaults.source_read_authorization_gate.authorize(
        SourceReadAuthorizationRequest(
            portfolio_id="portfolio_release_contract",
            portfolio_subject_id="subject_release_contract",
            publication_id="publication_release_contract",
            operation="candidate_source_read",
            purpose="Release-contract fail-closed probe.",
        )
    )
    if (
        source_decision.outcome != "unresolved"
        or source_decision.reason_codes != ("integration_unconfigured",)
    ):
        findings.append("default source-read authority is not fail-closed")

    curation_decision = defaults.curation_authority_gate.authorize(
        CurationAuthorityRequest(
            operation="propose_selection",
            portfolio_id="portfolio_release_contract",
            portfolio_subject_id="subject_release_contract",
            profile_binding_id="binding_release_contract",
            profile_revision_id="profile_release_contract",
            profile_revision_number=1,
            actor=actor,
        )
    )
    if (
        curation_decision.outcome != "unresolved"
        or curation_decision.reason_codes != ("integration_unconfigured",)
    ):
        findings.append("default curation authority is not fail-closed")

    snapshot_decision = defaults.snapshot_build_authority_gate.authorize(
        SnapshotBuildAuthorityRequest(
            operation="build_snapshot",
            snapshot_series_id="series_release_contract",
            snapshot_build_request_id="request_release_contract",
            snapshot_build_plan_id="plan_release_contract",
            snapshot_build_attempt_id="attempt_release_contract",
            portfolio_id="portfolio_release_contract",
            portfolio_subject_id="subject_release_contract",
            profile_binding_id="binding_release_contract",
            actor=actor,
        )
    )
    if (
        snapshot_decision.outcome != "unresolved"
        or snapshot_decision.reason_codes != ("integration_unconfigured",)
    ):
        findings.append("default Snapshot-build authority is not fail-closed")

    ordinary_registry = build_adapter_registry()
    ordinary_adapter_ids = tuple(
        item.declaration.adapter_id for item in ordinary_registry.adapters
    )
    if ordinary_adapter_ids != (
        "vitrine_concord_live_adapter",
        "vitrine_quillan_live_adapter",
        "vitrine_scoreform_live_adapter",
    ):
        findings.append(
            f"ordinary adapter registry drifted: {ordinary_adapter_ids!r}"
        )

    fixture_profiles = build_development_fixture_producer_registry()
    fixture_profile_ids = tuple(item.module_id for item in fixture_profiles.profiles)
    if fixture_profile_ids != EXPECTED_FIXTURE_PRODUCER_IDS:
        findings.append(
            f"fixture producer identities drifted: {fixture_profile_ids!r}"
        )

    fixture_adapters = build_development_fixture_adapter_registry()
    fixture_adapter_ids = tuple(
        item.declaration.adapter_id for item in fixture_adapters.adapters
    )
    if fixture_adapter_ids != EXPECTED_FIXTURE_ADAPTER_IDS:
        findings.append(f"fixture adapter identities drifted: {fixture_adapter_ids!r}")
    if any(
        item.declaration.integration_kind != "development_fixture"
        or item.reader.descriptor.integration_kind != "development_fixture"
        for item in fixture_adapters.adapters
    ):
        findings.append("fixture adapters/readers are not development_fixture only")

    try:
        build_adapter_registry(adapters=fixture_adapters.adapters)
    except ProducerAdapterError as error:
        if error.code != "adapter.fixture_not_enabled":
            findings.append(
                "ordinary adapter registry rejected fixtures with unexpected code: "
                f"{error.code}"
            )
    else:
        findings.append("ordinary adapter registry accepted development fixtures")

    for producer, request in _live_support_requests().items():
        try:
            fixture_adapters.select_adapter(request)
        except ProducerAdapterUnsupportedError as error:
            if error.code != "adapter.unsupported_contract":
                findings.append(
                    f"{producer} live-like request failed with unexpected code: "
                    f"{error.code}"
                )
        else:
            findings.append(
                f"{producer} live-like contract matched a development fixture adapter"
            )

    if PROFILE_PURPOSE_KINDS != EXPECTED_PURPOSE_KINDS:
        findings.append(
            f"Profile purpose-kind vocabulary drifted: {sorted(PROFILE_PURPOSE_KINDS)!r}"
        )

    return findings


def validate(root: Path) -> tuple[str, ...]:
    findings: list[str] = []

    source_version = _version_from_source(root)
    if source_version != EXPECTED_VERSION:
        findings.append(f"unexpected authoritative version: {source_version!r}")

    pyproject_path = root / "pyproject.toml"
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    pyproject = tomllib.loads(pyproject_text)
    project = pyproject.get("project")
    if not isinstance(project, dict):
        findings.append("pyproject project table is missing")
    else:
        if project.get("name") != "pds-vitrine":
            findings.append(f"unexpected distribution name: {project.get('name')!r}")
        if project.get("requires-python") != ">=3.11":
            findings.append(
                f"unexpected Python requirement: {project.get('requires-python')!r}"
            )
        if project.get("dependencies") != [CURRENT_DEVELOPMENT_CORE_REQUIREMENT]:
            findings.append(
                f"unexpected runtime dependencies: {project.get('dependencies')!r}"
            )
        if project.get("scripts") != EXPECTED_CONSOLE_SCRIPT:
            findings.append(f"unexpected console scripts: {project.get('scripts')!r}")
        if project.get("entry-points") != EXPECTED_OPERATIONS_ENTRY_POINTS:
            findings.append(
                f"unexpected Core operations entry points: {project.get('entry-points')!r}"
            )

    for group in FORBIDDEN_ENTRY_POINT_GROUPS:
        if group in pyproject_text:
            findings.append(f"forbidden entry-point group declared: {group}")

    dependencies = project.get("dependencies", []) if isinstance(project, dict) else []
    dependency_text = "\n".join(str(item) for item in dependencies).casefold()
    for name in FORBIDDEN_RUNTIME_DEPENDENCIES:
        if name in dependency_text:
            findings.append(f"forbidden sibling runtime dependency: {name}")

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased_marker = "## Unreleased"
    release_marker = "## 0.3.0 - 2026-09-17"
    historical_release_marker = "## 0.2.0 - 2026-08-17"
    if unreleased_marker not in changelog:
        findings.append("CHANGELOG Unreleased section is missing")
    if release_marker not in changelog:
        findings.append("CHANGELOG v0.3.0 release section is missing")
    elif changelog.index(unreleased_marker) > changelog.index(release_marker):
        findings.append("CHANGELOG Unreleased section must precede v0.3.0")
    if historical_release_marker not in changelog:
        findings.append("historical CHANGELOG v0.2.0 section is missing")

    release_notes = (root / "RELEASE_NOTES_v0.3.0.md").read_text(encoding="utf-8")
    required_release_note_markers = (
        "pds-vitrine v0.3.0",
        EXPECTED_CORE_REQUIREMENT,
        EXPECTED_CORE_WHEEL,
        EXPECTED_CORE_SHA256,
        "ScoreForm 0.11.0",
        "Quillan 0.10.0",
        "Concord 0.3.0",
        "paper_data_suite.module_operations",
        "Candidate eligibility != Selection authority",
        "local Export != external delivery",
    )
    for marker in required_release_note_markers:
        if marker not in release_notes:
            findings.append(f"release notes missing required marker: {marker}")

    compatibility = (root / "docs/v0.3.0-release-compatibility.md").read_text(
        encoding="utf-8"
    )
    for marker in (
        "- **Release source version:** `0.3.0`",
        EXPECTED_CORE_REQUIREMENT,
        EXPECTED_CORE_WHEEL,
        EXPECTED_CORE_SHA256,
        "ScoreForm 0.11.0",
        "Quillan 0.10.0",
        "Concord 0.3.0",
        "paper_data_suite.module_operations",
        "Improvement Portfolio",
        "Showcase Portfolio",
        "local directory_package Export != delivery",
    ):
        if marker not in compatibility:
            findings.append(f"release compatibility document missing marker: {marker}")

    release_audit = (root / "docs/v0.3.0-release-audit.md").read_text(
        encoding="utf-8"
    )
    for marker in (
        "# Vitrine v0.3.0 Release Audit",
        "**Audit phase:** released",
        "`released_verified`",
        "**Final release verdict:** `RELEASED — VERIFIED`",
        "27d28933c645cea1d57b5504362e8798eacee8fe",
        "9c6081f07a4e72098e1c8c7e0897f8ab87cb6710",
        "547527b083fcb0b302f1870906ab4434462f4f74",
        "69d2d1ea8a90b5d25c813da3c852232a0e0a9e7094e2b4d217f22662022596b8",
        "e93ee5d9e8d706c29923b3ee8e38b37574873d5f2dd87e3dcd9e67e4713389b9",
        "cb62552f07cee5540b25d8d9392106f915ddbdfcbf7d9b9ae7fa57ef1f2b54e5",
        "https://github.com/Paper-Data-Suite/pds-vitrine/releases/tag/v0.3.0",
        "ADR 0001",
        "ADR 0009",
        "#57",
        "#72",
        "**RELEASED — VERIFIED**",
    ):
        if marker not in release_audit:
            findings.append(f"release audit document missing marker: {marker}")

    release_checklist = (root / "docs/release_checklist.md").read_text(
        encoding="utf-8"
    )
    for marker in (
        "Vitrine v0.3.0 Release Checklist",
        "post-merge exact-main qualification",
        "fresh-download post-release verification",
        "pds_vitrine-0.3.0-py3-none-any.whl",
        "PASS issue #71 full live installed cross-producer acceptance",
    ):
        if marker not in release_checklist:
            findings.append(f"release checklist missing marker: {marker}")

    readme = (root / "README.md").read_text(encoding="utf-8")
    if "paper_data_suite.module_operations" not in readme:
        findings.append("README does not describe the Core module-operations provider")
    if "no `paper_data_suite.module_operations` entry point yet" in readme:
        findings.append("README still claims the operations entry point is unavailable")

    security = (root / "Security.md").read_text(encoding="utf-8")
    for marker in (
        "ScoreForm 0.11.0",
        "source-read authorization != producer Artifact authorization",
        "local Export != external delivery",
    ):
        if marker not in security:
            findings.append(f"Security.md missing v0.3 boundary marker: {marker}")

    docs_index = (root / "docs/README.md").read_text(encoding="utf-8")
    for marker in (
        "v0.3.0 release audit",
        "v0.3.0-release-audit.md",
        "issue #71",
    ):
        if marker not in docs_index:
            findings.append(f"docs/README.md missing v0.3 marker: {marker}")

    manifest = (root / "MANIFEST.in").read_text(encoding="utf-8")
    for marker in ("RELEASE_NOTES_v0.2.0.md", "RELEASE_NOTES_v0.3.0.md"):
        if marker not in manifest:
            findings.append(f"MANIFEST.in missing release note: {marker}")

    package_checker = (root / "scripts/check_package.py").read_text(encoding="utf-8")
    if 'metadata.get("Version") != "0.3.0"' not in package_checker:
        findings.append("package checker does not require distribution version 0.3.0")

    public_import_test = (root / "tests/test_imports.py").read_text(encoding="utf-8")
    if 'package.__version__ == "0.3.0"' not in public_import_test:
        findings.append("public import test does not require package version 0.3.0")
    if 'package.__version__ == "0.2.0"' in public_import_test:
        findings.append("public import test retains stale package version 0.2.0")

    operations_smoke = (
        root / "scripts/smoke_test_operations_wheel.py"
    ).read_text(encoding="utf-8")
    if 'if "0.3.0" not in version_output:' not in operations_smoke:
        findings.append(
            "operations wheel smoke does not target Vitrine release version 0.3.0"
        )
    if (
        'importlib.metadata.version("pds-vitrine") == "0.3.0"'
        not in operations_smoke
    ):
        findings.append(
            "operations wheel smoke metadata check does not target Vitrine 0.3.0"
        )
    if '"0.2.0"' in operations_smoke:
        findings.append(
            "operations wheel smoke retains stale Vitrine version 0.2.0"
        )

    repository_validator = (root / "scripts/validate_repository.py").read_text(
        encoding="utf-8"
    )
    release_command = '("release contract", ("scripts/validate_release_contract.py",))'
    if release_command not in repository_validator:
        findings.append(
            "repository validator does not invoke the release contract gate"
        )

    findings.extend(_runtime_boundary_findings())
    return tuple(findings)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    findings = validate(root)
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("PASS v0.3.0 release contract validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
