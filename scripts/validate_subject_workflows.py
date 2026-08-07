"""Exercise Portfolio Subject identity workflows in a disposable Core workspace."""

from __future__ import annotations

import hashlib
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pds_core.class_metadata import (
    ClassMetadata,
    class_metadata_path,
    write_class_metadata,
)
from pds_core.classes import write_class_roster
from pds_core.rosters import Roster, StudentRecord
from pds_core.workspace import ensure_workspace_root

from vitrine.models import ActorAttribution, ClassQualifiedStudentRef
from vitrine.storage import catalog_path, load_current_records, rebuild_catalog
from vitrine.subject_services import (
    IdentityDecisionContext,
    correct_subject_link,
    create_portfolio_subject,
    link_portfolio_subject,
    list_subjects,
    merge_portfolio_subjects,
    resolve_roster_student,
    show_subject,
    split_portfolio_subject,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIGESTS = {
    "improvement-foundational-records-v1.json": (
        "608f96fa10e5b7a20cf42dd4582a2b77cb1dede99da74491c8e7faf8f7635de8"
    ),
    "showcase-foundational-records-v1.json": (
        "ac72e824bb97c5e550b65f1dbdcb489abd3bd11d9b8f84cb0f83a6fc0c8b0360"
    ),
}
NOW = datetime(2026, 8, 7, 15, 0, tzinfo=timezone.utc)


class Ids:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def __call__(self, prefix: str) -> str:
        value = self._counts.get(prefix, 0) + 1
        self._counts[prefix] = value
        return f"{prefix}_{value}"


def _clock() -> datetime:
    return NOW


def _context(reason: str) -> IdentityDecisionContext:
    return IdentityDecisionContext(
        actor=ActorAttribution(
            actor_kind="authorized_adult",
            actor_id="teacher_1",
            owning_system="local",
            role_snapshot="teacher",
        ),
        authority_source="local_teacher_workflow",
        basis_type="direct_teacher_knowledge",
        basis_summary=reason,
    )


def _student(
    class_id: str,
    student_id: str,
    first_name: str,
    last_name: str,
    period: str,
) -> StudentRecord:
    return StudentRecord(
        class_id=class_id,
        student_id=student_id,
        first_name=first_name,
        last_name=last_name,
        period=period,
        extra_fields={},
    )


def _write_class(
    workspace: Path,
    class_id: str,
    students: tuple[StudentRecord, ...],
) -> None:
    metadata = ClassMetadata(
        class_id=class_id,
        school_year="2026-2027",
        created_at=NOW,
        updated_at=NOW,
        module_details={},
    )
    write_class_metadata(class_metadata_path(workspace, class_id), metadata)
    write_class_roster(
        workspace,
        Roster(
            class_id=class_id,
            students=students,
            columns=("class_id", "student_id", "last_name", "first_name", "period"),
        ),
    )


def _ref(class_id: str, student_id: str = "00107") -> ClassQualifiedStudentRef:
    return ClassQualifiedStudentRef(
        school_year="2026-2027",
        class_id=class_id,
        student_id=student_id,
    )


def _verify_fixture_digests() -> None:
    fixture_dir = ROOT / "tests" / "fixtures" / "runtime-models"
    for name, expected in FIXTURE_DIGESTS.items():
        actual = hashlib.sha256((fixture_dir / name).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"foundational fixture digest changed: {name}")


def validate() -> None:
    _verify_fixture_digests()
    with tempfile.TemporaryDirectory(prefix="vitrine-subject-validation-") as temporary:
        workspace = ensure_workspace_root(Path(temporary) / "workspace", create=True)
        _write_class(
            workspace,
            "english10_p2",
            (_student("english10_p2", "00107", "Jane", "Doe", "2"),),
        )
        _write_class(
            workspace,
            "csp_p1",
            (
                _student("csp_p1", "00107", "Jane", "Doe", "1"),
                _student("csp_p1", "00999", "Jane", "Doe", "1"),
            ),
        )
        _write_class(
            workspace,
            "math_p3",
            (_student("math_p3", "00107", "Different", "Person", "3"),),
        )
        _write_class(
            workspace,
            "history_p4",
            (_student("history_p4", "00777", "Jane", "Doe", "4"),),
        )
        old_metadata = ClassMetadata(
            class_id="old_english9_p3",
            school_year="2025-2026",
            created_at=NOW,
            updated_at=NOW,
            module_details={},
        )
        write_class_metadata(
            class_metadata_path(workspace, "old_english9_p3"), old_metadata
        )
        write_class_roster(
            workspace,
            Roster(
                class_id="old_english9_p3",
                students=(
                    _student("old_english9_p3", "00107", "Jane", "Doe", "3"),
                ),
                columns=("class_id", "student_id", "last_name", "first_name", "period"),
            ),
        )

        ids = Ids()
        first = create_portfolio_subject(
            workspace,
            _ref("english10_p2"),
            context=_context("Initial exact roster confirmation."),
            expected_state_revision=None,
            clock=_clock,
            id_factory=ids,
        )
        linked = link_portfolio_subject(
            workspace,
            first.subject_ids[0],
            _ref("csp_p1"),
            context=_context("Teacher confirmed cross-class continuity."),
            expected_state_revision=first.commit.state_revision,
            clock=_clock,
            id_factory=ids,
        )

        cross_year = link_portfolio_subject(
            workspace,
            first.subject_ids[0],
            ClassQualifiedStudentRef(
                school_year="2025-2026",
                class_id="old_english9_p3",
                student_id="00107",
            ),
            context=_context("Teacher confirmed longitudinal continuity."),
            expected_state_revision=linked.commit.state_revision,
            clock=_clock,
            id_factory=ids,
        )

        same_name = create_portfolio_subject(
            workspace,
            _ref("csp_p1", "00999"),
            context=_context("Same name is a different student."),
            expected_state_revision=cross_year.commit.state_revision,
            clock=_clock,
            id_factory=ids,
        )
        repeated_id = create_portfolio_subject(
            workspace,
            _ref("math_p3"),
            context=_context("Repeated local ID is a different student."),
            expected_state_revision=same_name.commit.state_revision,
            clock=_clock,
            id_factory=ids,
        )
        if len(list_subjects(workspace)) != 3:
            raise RuntimeError("name or repeated local ID was matched automatically")

        detail = show_subject(workspace, first.subject_ids[0])
        csp_link = next(
            item for item in detail.current_links if item.reference.class_id == "csp_p1"
        )
        corrected = correct_subject_link(
            workspace,
            csp_link.subject_link_id,
            _ref("history_p4", "00777"),
            context=_context("Corrected the previously confirmed class reference."),
            expected_state_revision=repeated_id.commit.state_revision,
            clock=_clock,
            id_factory=ids,
        )
        corrected_detail = show_subject(workspace, first.subject_ids[0])
        if not any(item.status == "superseded" for item in corrected_detail.historical_links):
            raise RuntimeError("link correction did not preserve predecessor history")

        merged = merge_portfolio_subjects(
            workspace,
            (first.subject_ids[0], repeated_id.subject_ids[0]),
            context=_context("Teacher explicitly confirmed these Subjects are one person."),
            expected_state_revision=corrected.commit.state_revision,
            clock=_clock,
            id_factory=ids,
        )
        merged_detail = show_subject(workspace, merged.subject_ids[0])
        if len(merged_detail.current_links) < 2:
            raise RuntimeError("merge did not preserve successor roster associations")
        groups = (
            (merged_detail.current_links[0].subject_link_id,),
            tuple(item.subject_link_id for item in merged_detail.current_links[1:]),
        )
        split = split_portfolio_subject(
            workspace,
            merged.subject_ids[0],
            groups,
            context=_context("Teacher explicitly separated the merged identity."),
            expected_state_revision=merged.commit.state_revision,
            clock=_clock,
            id_factory=ids,
        )
        if len(split.subject_ids) != 2:
            raise RuntimeError("split did not create two successor Subjects")

        # Remove the source for a superseded historical link. Historical identity remains.
        (workspace / "classes" / "csp_p1" / "roster.csv").unlink()
        historical = show_subject(workspace, first.subject_ids[0]).historical_links
        if not any(
            item.reference.class_id == "csp_p1"
            and item.current_resolution == "historical_reference_only"
            for item in historical
        ):
            raise RuntimeError("historical link depended on current Core roster availability")

        if resolve_roster_student(workspace, _ref("english10_p2")).status != "resolvable":
            raise RuntimeError("exact Core roster resolution failed")
        before = load_current_records(workspace)
        rebuild_catalog(workspace)
        catalog_path(workspace).unlink()
        after = load_current_records(workspace)
        if after != before:
            raise RuntimeError("canonical Subject reads depended on derived catalog state")


def main() -> int:
    try:
        validate()
        print("PASS Portfolio Subject workflow validation")
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Portfolio Subject workflow validation failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
