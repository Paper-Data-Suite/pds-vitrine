"""Validate the frozen pds-vitrine v0.2.0 release identity and scope boundary."""

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

EXPECTED_VERSION = "0.2.0"
EXPECTED_CORE_REQUIREMENT = "pds-core>=0.6,<0.7"
EXPECTED_CORE_WHEEL = "pds_core-0.6.0-py3-none-any.whl"
EXPECTED_CORE_SHA256 = (
    "be28c061b38463ef59ebc328ed1aa443767fe7f2c626babb769c2d8e5932f308"
)
EXPECTED_CONSOLE_SCRIPT = {"vitrine": "vitrine.cli:main"}
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
    if ordinary_registry.adapters != ():
        findings.append("ordinary adapter registry contains implicit adapters")

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
        if project.get("dependencies") != [EXPECTED_CORE_REQUIREMENT]:
            findings.append(
                f"unexpected runtime dependencies: {project.get('dependencies')!r}"
            )
        if project.get("scripts") != EXPECTED_CONSOLE_SCRIPT:
            findings.append(f"unexpected console scripts: {project.get('scripts')!r}")

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
    release_marker = "## 0.2.0 - 2026-08-17"
    if unreleased_marker not in changelog:
        findings.append("CHANGELOG Unreleased section is missing")
    if release_marker not in changelog:
        findings.append("CHANGELOG v0.2.0 release section is missing")
    elif changelog.index(unreleased_marker) > changelog.index(release_marker):
        findings.append("CHANGELOG Unreleased section must precede v0.2.0")

    release_notes = (root / "RELEASE_NOTES_v0.2.0.md").read_text(encoding="utf-8")
    required_release_note_markers = (
        "pds-vitrine v0.2.0",
        EXPECTED_CORE_REQUIREMENT,
        EXPECTED_CORE_WHEEL,
        EXPECTED_CORE_SHA256,
        "vitrine_scoreform_fixture",
        "vitrine_quillan_fixture",
        "vitrine_concord_fixture",
        "not live producer integrations",
        "Improvement and Showcase",
    )
    for marker in required_release_note_markers:
        if marker not in release_notes:
            findings.append(f"release notes missing required marker: {marker}")

    compatibility = (root / "docs/v0.2.0-release-compatibility.md").read_text(
        encoding="utf-8"
    )
    for marker in (
        "- **Release source version:** `0.2.0`",
        EXPECTED_CORE_REQUIREMENT,
        EXPECTED_CORE_WHEEL,
        EXPECTED_CORE_SHA256,
        "Improvement Portfolio",
        "Showcase Portfolio",
        "Parent/Guardian Conference Portfolio",
        "Regulated Portfolio",
    ):
        if marker not in compatibility:
            findings.append(f"release compatibility document missing marker: {marker}")

    package_checker = (root / "scripts/check_package.py").read_text(encoding="utf-8")
    if 'metadata.get("Version") != "0.2.0"' not in package_checker:
        findings.append("package checker does not require distribution version 0.2.0")

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
    print("PASS v0.2.0 release contract validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
