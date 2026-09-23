"""Transient teacher presentation for Candidate discovery runs.

The projection summarizes one exact CandidateDiscoveryResult without changing
discovery authority or persisting UI state. Exact finding codes, Publication
identities, diagnostics, and commit revision remain technical provenance.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Final

from vitrine.candidate_services import CandidateDiscoveryResult

CANDIDATE_DISCOVERY_PRESENTATION_CONTRACT_VERSION: Final[str] = (
    "vitrine_candidate_discovery_presentation_v1"
)

_MODULE_LABELS: Final[dict[str, str]] = {
    "scoreform": "ScoreForm",
    "vitrine_scoreform_fixture": "ScoreForm",
    "quillan": "Quillan",
    "vitrine_quillan_fixture": "Quillan",
    "concord": "Concord",
    "vitrine_concord_fixture": "Concord",
}
_MODULE_ORDER: Final[tuple[str, ...]] = ("ScoreForm", "Quillan", "Concord")


@dataclass(frozen=True, slots=True)
class CandidateDiscoveryModuleParticipation:
    """Safely recognized producer-family participation in evaluated evidence."""

    label: str
    evidence_items: int


@dataclass(frozen=True, slots=True)
class CandidateDiscoverySummary:
    """Teacher-readable projection over one exact discovery result."""

    contract_version: str
    publications_considered: int
    evidence_items_evaluated: int
    new_candidates: int
    already_known_candidates: int
    ineligible_evidence: int
    unresolved_evidence: int
    source_problem_count: int
    module_participation: tuple[CandidateDiscoveryModuleParticipation, ...]


def build_candidate_discovery_summary(
    result: CandidateDiscoveryResult,
) -> CandidateDiscoverySummary:
    """Build a bounded instructional summary from exact discovery output."""

    if not isinstance(result, CandidateDiscoveryResult):
        raise TypeError("result must be CandidateDiscoveryResult.")

    dispositions = Counter(item.disposition for item in result.evaluation_results)
    outcomes = Counter(item.evaluation.outcome for item in result.evaluation_results)
    modules: Counter[str] = Counter()
    for item in result.evaluation_results:
        module_id = item.projected_source.producer_source.producer_module_id
        label = _MODULE_LABELS.get(module_id)
        if label is not None:
            modules[label] += 1

    participation = tuple(
        CandidateDiscoveryModuleParticipation(
            label=label,
            evidence_items=modules[label],
        )
        for label in _MODULE_ORDER
        if modules[label]
    )
    return CandidateDiscoverySummary(
        contract_version=CANDIDATE_DISCOVERY_PRESENTATION_CONTRACT_VERSION,
        publications_considered=len(result.proposed_publication_ids),
        evidence_items_evaluated=len(result.evaluation_results),
        new_candidates=dispositions["created"],
        already_known_candidates=dispositions["existing"],
        ineligible_evidence=outcomes["ineligible"],
        unresolved_evidence=outcomes["unresolved"],
        source_problem_count=len(result.findings),
        module_participation=participation,
    )


__all__ = [
    "CANDIDATE_DISCOVERY_PRESENTATION_CONTRACT_VERSION",
    "CandidateDiscoveryModuleParticipation",
    "CandidateDiscoverySummary",
    "build_candidate_discovery_summary",
]
