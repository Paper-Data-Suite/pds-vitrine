"""Pure projection and validation for Candidate Evaluation current-state history."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from vitrine.models.candidates import (
    CandidateCurrentEvaluationPointerRevision,
    CandidateEvaluation,
    PortfolioCandidate,
)
from vitrine.models.conversion import VitrineRecord
from vitrine.models.errors import ValidationIssue


def _issue(
    code: str,
    message: str,
    record_type: str | None = None,
    record_id: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message=message,
        record_type=record_type,
        record_id=record_id,
    )


def _cycle_representatives(
    predecessors: dict[str, str | None],
) -> tuple[str, ...]:
    representatives: set[str] = set()
    for start in sorted(predecessors):
        path: list[str] = []
        positions: dict[str, int] = {}
        current: str | None = start
        while current is not None and current in predecessors:
            if current in positions:
                representatives.add(min(path[positions[current] :]))
                break
            positions[current] = len(path)
            path.append(current)
            current = predecessors[current]
    return tuple(sorted(representatives))


def _evaluation_series_key(
    value: CandidateEvaluation,
) -> tuple[object, ...]:
    """Return fields that define one exact reevaluable Candidate meaning."""

    return (
        value.portfolio_id,
        value.portfolio_subject_id,
        value.profile_binding_id,
        value.profile_revision,
        value.purpose,
        value.source_endpoint,
    )


@dataclass(frozen=True, slots=True)
class CandidateCurrentEvaluationResolution:
    candidate_id: str
    evaluation: CandidateEvaluation | None
    pointer: CandidateCurrentEvaluationPointerRevision | None
    mode: str
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class CandidateState:
    evaluations: tuple[CandidateEvaluation, ...]
    candidates: tuple[PortfolioCandidate, ...]
    current_evaluation_pointers: tuple[
        CandidateCurrentEvaluationPointerRevision, ...
    ]

    def pointer_heads(
        self,
        candidate_id: str,
    ) -> tuple[CandidateCurrentEvaluationPointerRevision, ...]:
        values = tuple(
            item
            for item in self.current_evaluation_pointers
            if item.candidate_id == candidate_id
        )
        predecessor_keys = {
            (item.candidate_id, item.predecessor_pointer_revision)
            for item in values
            if item.predecessor_pointer_revision is not None
        }
        return tuple(
            sorted(
                (
                    item
                    for item in values
                    if (item.candidate_id, item.pointer_revision)
                    not in predecessor_keys
                ),
                key=lambda item: item.pointer_revision,
            )
        )

    def evaluation_successors(
        self,
        candidate_evaluation_id: str,
    ) -> tuple[CandidateEvaluation, ...]:
        return tuple(
            sorted(
                (
                    item
                    for item in self.evaluations
                    if item.predecessor_evaluation_id
                    == candidate_evaluation_id
                ),
                key=lambda item: item.candidate_evaluation_id,
            )
        )

    def resolve_current_evaluation(
        self,
        candidate_id: str,
    ) -> CandidateCurrentEvaluationResolution:
        candidate_matches = tuple(
            item
            for item in self.candidates
            if item.candidate_id == candidate_id
        )
        if len(candidate_matches) != 1:
            return CandidateCurrentEvaluationResolution(
                candidate_id=candidate_id,
                evaluation=None,
                pointer=None,
                mode="unresolved",
                reason_code=(
                    "candidate.current_candidate_missing"
                    if not candidate_matches
                    else "candidate.current_candidate_conflict"
                ),
            )
        candidate = candidate_matches[0]
        pointer_values = tuple(
            item
            for item in self.current_evaluation_pointers
            if item.candidate_id == candidate_id
        )
        if pointer_values:
            heads = self.pointer_heads(candidate_id)
            if len(heads) != 1:
                return CandidateCurrentEvaluationResolution(
                    candidate_id=candidate_id,
                    evaluation=None,
                    pointer=None,
                    mode="unresolved",
                    reason_code="candidate.current_pointer_conflict",
                )
            pointer = heads[0]
            evaluation_matches = tuple(
                item
                for item in self.evaluations
                if item.candidate_evaluation_id
                == pointer.current_candidate_evaluation_id
            )
            if len(evaluation_matches) != 1:
                return CandidateCurrentEvaluationResolution(
                    candidate_id=candidate_id,
                    evaluation=None,
                    pointer=pointer,
                    mode="unresolved",
                    reason_code=(
                        "candidate.current_pointer_evaluation_missing"
                    ),
                )
            return CandidateCurrentEvaluationResolution(
                candidate_id=candidate_id,
                evaluation=evaluation_matches[0],
                pointer=pointer,
                mode="explicit",
            )

        creation_matches = tuple(
            item
            for item in self.evaluations
            if item.candidate_evaluation_id
            == candidate.candidate_evaluation_id
        )
        if len(creation_matches) != 1:
            return CandidateCurrentEvaluationResolution(
                candidate_id=candidate_id,
                evaluation=None,
                pointer=None,
                mode="unresolved",
                reason_code=(
                    "candidate.legacy_creation_evaluation_missing"
                ),
            )
        creation = creation_matches[0]
        if self.evaluation_successors(
            creation.candidate_evaluation_id
        ):
            return CandidateCurrentEvaluationResolution(
                candidate_id=candidate_id,
                evaluation=None,
                pointer=None,
                mode="unresolved",
                reason_code=(
                    "candidate.legacy_current_evaluation_ambiguous"
                ),
            )
        return CandidateCurrentEvaluationResolution(
            candidate_id=candidate_id,
            evaluation=creation,
            pointer=None,
            mode="legacy",
        )


def project_candidate_state(
    records: Iterable[VitrineRecord],
) -> CandidateState:
    values = tuple(records)
    return CandidateState(
        evaluations=tuple(
            item
            for item in values
            if isinstance(item, CandidateEvaluation)
        ),
        candidates=tuple(
            item
            for item in values
            if isinstance(item, PortfolioCandidate)
        ),
        current_evaluation_pointers=tuple(
            item
            for item in values
            if isinstance(
                item,
                CandidateCurrentEvaluationPointerRevision,
            )
        ),
    )


def collect_candidate_state_issues(
    state: CandidateState,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []

    evaluations: dict[str, CandidateEvaluation] = {}
    for evaluation in state.evaluations:
        if evaluation.candidate_evaluation_id in evaluations:
            issues.append(
                _issue(
                    "candidate.evaluation_duplicate",
                    "Candidate Evaluation identity is duplicated.",
                    evaluation.record_type,
                    evaluation.candidate_evaluation_id,
                )
            )
        else:
            evaluations[
                evaluation.candidate_evaluation_id
            ] = evaluation

    candidates: dict[str, PortfolioCandidate] = {}
    for candidate in state.candidates:
        if candidate.candidate_id in candidates:
            issues.append(
                _issue(
                    "candidate.duplicate",
                    "Candidate identity is duplicated.",
                    candidate.record_type,
                    candidate.candidate_id,
                )
            )
        else:
            candidates[candidate.candidate_id] = candidate

    evaluation_successors: dict[str, list[str]] = defaultdict(list)
    evaluation_predecessors: dict[str, str | None] = {}
    for evaluation in state.evaluations:
        evaluation_predecessors[
            evaluation.candidate_evaluation_id
        ] = evaluation.predecessor_evaluation_id
        if evaluation.predecessor_evaluation_id is None:
            continue
        predecessor = evaluations.get(
            evaluation.predecessor_evaluation_id
        )
        if predecessor is None:
            issues.append(
                _issue(
                    "candidate.evaluation_predecessor_missing",
                    "Candidate Evaluation predecessor does not exist.",
                    evaluation.record_type,
                    evaluation.candidate_evaluation_id,
                )
            )
            continue
        if (
            _evaluation_series_key(predecessor)
            != _evaluation_series_key(evaluation)
        ):
            issues.append(
                _issue(
                    "candidate.evaluation_predecessor_context_mismatch",
                    (
                        "Candidate Evaluation predecessor belongs to "
                        "another exact source/context series."
                    ),
                    evaluation.record_type,
                    evaluation.candidate_evaluation_id,
                )
            )
        evaluation_successors[
            evaluation.predecessor_evaluation_id
        ].append(evaluation.candidate_evaluation_id)

    for predecessor_id, successor_ids in sorted(
        evaluation_successors.items()
    ):
        if len(successor_ids) > 1:
            issues.append(
                _issue(
                    "candidate.evaluation_branch",
                    (
                        "Candidate Evaluation predecessor has more "
                        "than one successor."
                    ),
                    "candidate_evaluation",
                    predecessor_id,
                )
            )
    for representative in _cycle_representatives(
        evaluation_predecessors
    ):
        issues.append(
            _issue(
                "candidate.evaluation_cycle",
                (
                    "Candidate Evaluation predecessor history "
                    "contains a cycle."
                ),
                "candidate_evaluation",
                representative,
            )
        )

    for candidate in state.candidates:
        creation = evaluations.get(candidate.candidate_evaluation_id)
        if (
            creation is not None
            and creation.predecessor_evaluation_id is not None
        ):
            issues.append(
                _issue(
                    "candidate.creation_evaluation_not_root",
                    (
                        "Candidate creation Evaluation must be the "
                        "root of its Evaluation series."
                    ),
                    candidate.record_type,
                    candidate.candidate_id,
                )
            )

    pointer_by_key: dict[
        tuple[str, int],
        CandidateCurrentEvaluationPointerRevision,
    ] = {}
    pointer_groups: dict[
        str,
        list[CandidateCurrentEvaluationPointerRevision],
    ] = defaultdict(list)

    for pointer in state.current_evaluation_pointers:
        key = (pointer.candidate_id, pointer.pointer_revision)
        if key in pointer_by_key:
            issues.append(
                _issue(
                    "candidate.pointer_duplicate",
                    (
                        "Candidate Current Evaluation Pointer "
                        "identity is duplicated."
                    ),
                    pointer.record_type,
                    (
                        f"{pointer.candidate_id}:"
                        f"{pointer.pointer_revision}"
                    ),
                )
            )
        else:
            pointer_by_key[key] = pointer
        pointer_groups[pointer.candidate_id].append(pointer)

        pointer_candidate = candidates.get(pointer.candidate_id)
        pointer_evaluation = evaluations.get(
            pointer.current_candidate_evaluation_id
        )
        if pointer_candidate is None:
            issues.append(
                _issue(
                    "candidate.pointer_candidate_missing",
                    (
                        "Candidate Current Evaluation Pointer "
                        "references a missing Candidate."
                    ),
                    pointer.record_type,
                    (
                        f"{pointer.candidate_id}:"
                        f"{pointer.pointer_revision}"
                    ),
                )
            )
            continue

        creation_evaluation = evaluations.get(
            pointer_candidate.candidate_evaluation_id
        )
        if pointer_evaluation is None:
            issues.append(
                _issue(
                    "candidate.pointer_evaluation_missing",
                    (
                        "Candidate Current Evaluation Pointer "
                        "references a missing Evaluation."
                    ),
                    pointer.record_type,
                    (
                        f"{pointer.candidate_id}:"
                        f"{pointer.pointer_revision}"
                    ),
                )
            )
        elif creation_evaluation is not None:
            if (
                _evaluation_series_key(pointer_evaluation)
                != _evaluation_series_key(creation_evaluation)
            ):
                issues.append(
                    _issue(
                        "candidate.pointer_evaluation_context_mismatch",
                        (
                            "Candidate Current Evaluation Pointer "
                            "references another exact source/context "
                            "series."
                        ),
                        pointer.record_type,
                        (
                            f"{pointer.candidate_id}:"
                            f"{pointer.pointer_revision}"
                        ),
                    )
                )
            if (
                pointer_evaluation.source_endpoint
                != pointer_candidate.source_endpoint
            ):
                issues.append(
                    _issue(
                        "candidate.pointer_source_endpoint_mismatch",
                        (
                            "Candidate Current Evaluation Pointer "
                            "references an Evaluation for another "
                            "source endpoint."
                        ),
                        pointer.record_type,
                        (
                            f"{pointer.candidate_id}:"
                            f"{pointer.pointer_revision}"
                        ),
                    )
                )

        if (
            pointer.pointer_revision == 1
            and pointer.current_candidate_evaluation_id
            != pointer_candidate.candidate_evaluation_id
        ):
            issues.append(
                _issue(
                    "candidate.pointer_initial_evaluation_mismatch",
                    (
                        "Initial Candidate Current Evaluation Pointer "
                        "must reference the Candidate creation "
                        "Evaluation."
                    ),
                    pointer.record_type,
                    (
                        f"{pointer.candidate_id}:"
                        f"{pointer.pointer_revision}"
                    ),
                )
            )

    pointer_successors: dict[
        tuple[str, int],
        list[tuple[str, int]],
    ] = defaultdict(list)

    for candidate_id, pointer_records in sorted(
        pointer_groups.items()
    ):
        for pointer in pointer_records:
            if pointer.predecessor_pointer_revision is None:
                continue
            current_key = (
                candidate_id,
                pointer.pointer_revision,
            )
            predecessor_key = (
                candidate_id,
                pointer.predecessor_pointer_revision,
            )
            predecessor_pointer = pointer_by_key.get(predecessor_key)
            if predecessor_pointer is None:
                issues.append(
                    _issue(
                        "candidate.pointer_predecessor_missing",
                        (
                            "Candidate Current Evaluation Pointer "
                            "predecessor revision does not exist."
                        ),
                        pointer.record_type,
                        (
                            f"{pointer.candidate_id}:"
                            f"{pointer.pointer_revision}"
                        ),
                    )
                )
                continue

            pointer_successors[predecessor_key].append(
                current_key
            )
            if (
                pointer.previous_candidate_evaluation_id
                != predecessor_pointer.current_candidate_evaluation_id
            ):
                issues.append(
                    _issue(
                        "candidate.pointer_previous_evaluation_mismatch",
                        (
                            "Candidate Current Evaluation Pointer "
                            "does not preserve the predecessor "
                            "pointer's Evaluation."
                        ),
                        pointer.record_type,
                        (
                            f"{pointer.candidate_id}:"
                            f"{pointer.pointer_revision}"
                        ),
                    )
                )

            current_evaluation = evaluations.get(
                pointer.current_candidate_evaluation_id
            )
            if (
                current_evaluation is not None
                and current_evaluation.predecessor_evaluation_id
                != predecessor_pointer.current_candidate_evaluation_id
            ):
                issues.append(
                    _issue(
                        "candidate.pointer_evaluation_predecessor_mismatch",
                        (
                            "Candidate Current Evaluation Pointer "
                            "transition does not follow explicit "
                            "Evaluation lineage."
                        ),
                        pointer.record_type,
                        (
                            f"{pointer.candidate_id}:"
                            f"{pointer.pointer_revision}"
                        ),
                    )
                )

        heads = state.pointer_heads(candidate_id)
        if len(heads) > 1:
            issues.append(
                _issue(
                    "candidate.pointer_head_conflict",
                    (
                        "Candidate has more than one Current "
                        "Evaluation Pointer head."
                    ),
                    (
                        "candidate_current_evaluation_"
                        "pointer_revision"
                    ),
                    candidate_id,
                )
            )

    for predecessor_key, successor_keys in sorted(
        pointer_successors.items()
    ):
        if len(successor_keys) > 1:
            issues.append(
                _issue(
                    "candidate.pointer_branch",
                    (
                        "Candidate Current Evaluation Pointer "
                        "revision has more than one successor."
                    ),
                    (
                        "candidate_current_evaluation_"
                        "pointer_revision"
                    ),
                    (
                        f"{predecessor_key[0]}:"
                        f"{predecessor_key[1]}"
                    ),
                )
            )

    return tuple(issues)


__all__ = [
    "CandidateCurrentEvaluationResolution",
    "CandidateState",
    "collect_candidate_state_issues",
    "project_candidate_state",
]
