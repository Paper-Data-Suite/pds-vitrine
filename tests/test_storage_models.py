from __future__ import annotations

import pytest

from tests.runtime_fixture_factory import make_improvement_graph
from vitrine.storage import (
    VitrineCurrentState,
    VitrineRecordRevisionRef,
    VitrineStateRevision,
    VitrineStorageRecordKey,
    VitrineStorageValidationError,
    key_for_record,
)


def test_record_keys_preserve_composite_domain_identity() -> None:
    graph = make_improvement_graph()
    profile = graph.profile_revisions[0]
    composition = graph.compositions[0]
    edition = graph.snapshot_editions[0]

    assert key_for_record(profile) == VitrineStorageRecordKey(
        "portfolio_profile_revision",
        (profile.portfolio_profile_id, str(profile.profile_revision)),
    )
    assert key_for_record(composition).identity_segments == (
        composition.portfolio_id,
        str(composition.composition_revision),
    )
    assert key_for_record(edition).identity_segments == (
        edition.snapshot_series_id,
        str(edition.edition_number),
    )


def test_integer_identity_segments_are_canonical_decimal_text() -> None:
    with pytest.raises(VitrineStorageValidationError):
        VitrineStorageRecordKey("snapshot_edition", ("series_x", "01"))
    with pytest.raises(VitrineStorageValidationError):
        VitrineStorageRecordKey("snapshot_edition", ("series_x", "0"))


def test_state_revision_requires_deterministic_unique_references() -> None:
    key_a = VitrineStorageRecordKey("portfolio", ("portfolio_a",))
    key_b = VitrineStorageRecordKey("portfolio_subject", ("subject_a",))
    ref_a = VitrineRecordRevisionRef(key_a, 1, "1" * 64)
    ref_b = VitrineRecordRevisionRef(key_b, 1, "2" * 64)

    with pytest.raises(VitrineStorageValidationError):
        VitrineStateRevision(1, None, None, (ref_b, ref_a))
    with pytest.raises(VitrineStorageValidationError):
        VitrineStateRevision(1, None, None, (ref_a, ref_a))


def test_revision_numbers_reject_boolean_values() -> None:
    with pytest.raises(VitrineStorageValidationError):
        VitrineCurrentState(True, "1" * 64)  # type: ignore[arg-type]
