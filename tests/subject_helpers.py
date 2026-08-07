from __future__ import annotations

from dataclasses import dataclass
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

from vitrine.models import ActorAttribution
from vitrine.subject_services import IdentityDecisionContext

FIXED_NOW = datetime(2026, 8, 7, 15, 0, tzinfo=timezone.utc)


@dataclass
class DeterministicIds:
    counters: dict[str, int]

    def __init__(self) -> None:
        self.counters = {}

    def __call__(self, prefix: str) -> str:
        value = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = value
        return f"{prefix}_{value}"


def fixed_clock() -> datetime:
    return FIXED_NOW


def teacher_context(summary: str = "Teacher confirmed identity.") -> IdentityDecisionContext:
    return IdentityDecisionContext(
        actor=ActorAttribution(
            actor_kind="authorized_adult",
            actor_id="teacher_1",
            owning_system="local",
            role_snapshot="teacher",
        ),
        authority_source="local_teacher_workflow",
        basis_type="direct_teacher_knowledge",
        basis_summary=summary,
    )


def _write_class(
    workspace: Path,
    *,
    class_id: str,
    school_year: str,
    students: tuple[StudentRecord, ...],
) -> None:
    metadata = ClassMetadata(
        class_id=class_id,
        school_year=school_year,
        created_at=FIXED_NOW,
        updated_at=FIXED_NOW,
        module_details={},
    )
    write_class_metadata(class_metadata_path(workspace, class_id), metadata)
    roster = Roster(
        class_id=class_id,
        students=students,
        columns=(
            "class_id",
            "student_id",
            "last_name",
            "first_name",
            "period",
            "preferred_name",
        ),
    )
    write_class_roster(workspace, roster)


def make_subject_workspace(tmp_path: Path) -> Path:
    workspace = ensure_workspace_root(tmp_path / "workspace", create=True)
    _write_class(
        workspace,
        class_id="english10_p2",
        school_year="2026-2027",
        students=(
            StudentRecord(
                class_id="english10_p2",
                student_id="00107",
                last_name="Doe",
                first_name="Jane",
                period="2",
                extra_fields={"preferred_name": "Jay"},
            ),
            StudentRecord(
                class_id="english10_p2",
                student_id="00421",
                last_name="Smith",
                first_name="Alex",
                period="2",
                extra_fields={"preferred_name": ""},
            ),
        ),
    )
    _write_class(
        workspace,
        class_id="csp_p1",
        school_year="2026-2027",
        students=(
            StudentRecord(
                class_id="csp_p1",
                student_id="00107",
                last_name="Doe",
                first_name="Jane",
                period="1",
                extra_fields={"preferred_name": "Jay"},
            ),
            StudentRecord(
                class_id="csp_p1",
                student_id="00999",
                last_name="Doe",
                first_name="Jane",
                period="1",
                extra_fields={"preferred_name": ""},
            ),
        ),
    )
    _write_class(
        workspace,
        class_id="math_p3",
        school_year="2026-2027",
        students=(
            StudentRecord(
                class_id="math_p3",
                student_id="00107",
                last_name="Different",
                first_name="Person",
                period="3",
                extra_fields={"preferred_name": ""},
            ),
        ),
    )
    _write_class(
        workspace,
        class_id="old_english9_p3",
        school_year="2025-2026",
        students=(
            StudentRecord(
                class_id="old_english9_p3",
                student_id="00107",
                last_name="Doe",
                first_name="Jane",
                period="3",
                extra_fields={"preferred_name": "Jay"},
            ),
        ),
    )
    return workspace
