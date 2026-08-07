"""Strict canonical JSON for Vitrine records and graphs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import fields
from typing import Never, cast

from .audiences import AudienceContext
from .candidates import CandidateEvaluation, PortfolioCandidate
from .conversion import JsonValue, VitrineRecord, record_from_dict, record_to_dict
from .curation import (
    PortfolioPlacement,
    PortfolioSelection,
    SectionArrangementRevision,
    WorkingPortfolioCompositionRevision,
)
from .errors import VitrineSerializationError
from .graph import GRAPH_COLLECTION_TYPES, VitrineRecordGraph
from .identity import Portfolio, PortfolioSubject, PortfolioSubjectClassLink
from .profiles import (
    PortfolioProfileBinding,
    PortfolioProfileFamily,
    PortfolioProfileRevision,
)
from .snapshots import (
    SnapshotEdition,
    SnapshotEntry,
    SnapshotManifest,
    SnapshotMaterializationRecord,
    SnapshotOmission,
    SnapshotSeal,
)


def _reject_constant(value: str) -> Never:
    raise VitrineSerializationError(f"nonfinite JSON number {value!r} is prohibited.")


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise VitrineSerializationError(f"duplicate JSON key {key!r}.")
        result[key] = value
    return result


def strict_json_loads(data: bytes) -> object:
    if not isinstance(data, bytes):
        raise VitrineSerializationError("JSON input must be immutable bytes.")
    if data.startswith(b"\xef\xbb\xbf"):
        raise VitrineSerializationError("UTF-8 BOM is prohibited.")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise VitrineSerializationError("JSON bytes must be valid UTF-8.") from error
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except VitrineSerializationError:
        raise
    except json.JSONDecodeError as error:
        raise VitrineSerializationError(f"invalid JSON: {error.msg}.") from error


def _canonical_bytes(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise VitrineSerializationError(f"could not serialize canonical JSON: {error}") from error


def record_to_canonical_json_bytes(record: VitrineRecord) -> bytes:
    return _canonical_bytes(record_to_dict(record))


def record_from_json_bytes(data: bytes) -> VitrineRecord:
    value = strict_json_loads(data)
    if not isinstance(value, Mapping):
        raise VitrineSerializationError("record JSON must contain an object.")
    return record_from_dict(cast(Mapping[str, object], value))


def graph_to_dict(graph: VitrineRecordGraph) -> dict[str, JsonValue]:
    if not isinstance(graph, VitrineRecordGraph):
        raise VitrineSerializationError("graph must be a VitrineRecordGraph.")
    return {
        graph_field.name: [
            record_to_dict(item)
            for item in getattr(graph, graph_field.name)
        ]
        for graph_field in fields(graph)
    }


def graph_from_dict(data: Mapping[str, object]) -> VitrineRecordGraph:
    if not isinstance(data, Mapping):
        raise VitrineSerializationError("graph must be an object.")
    expected = set(GRAPH_COLLECTION_TYPES)
    actual = set(data)
    unknown = sorted(actual - expected)
    if unknown:
        raise VitrineSerializationError(
            f"graph contains unknown key(s): {', '.join(unknown)}."
        )
    missing = sorted(expected - actual)
    if missing:
        raise VitrineSerializationError(
            f"graph is missing required key(s): {', '.join(missing)}."
        )

    collections: dict[str, tuple[VitrineRecord, ...]] = {}
    for field_name, expected_type in GRAPH_COLLECTION_TYPES.items():
        raw = data[field_name]
        if not isinstance(raw, list):
            raise VitrineSerializationError(
                f"graph.{field_name} must be an array."
            )
        records: list[VitrineRecord] = []
        for index, item in enumerate(raw):
            if not isinstance(item, Mapping):
                raise VitrineSerializationError(
                    f"graph.{field_name}[{index}] must be an object."
                )
            record = record_from_dict(cast(Mapping[str, object], item))
            if type(record) is not expected_type:
                raise VitrineSerializationError(
                    f"graph.{field_name}[{index}] must contain "
                    f"{expected_type.__name__} records."
                )
            records.append(record)
        collections[field_name] = tuple(records)

    return VitrineRecordGraph(
        portfolios=cast(tuple[Portfolio, ...], collections["portfolios"]),
        portfolio_subjects=cast(
            tuple[PortfolioSubject, ...], collections["portfolio_subjects"]
        ),
        subject_links=cast(
            tuple[PortfolioSubjectClassLink, ...], collections["subject_links"]
        ),
        profile_families=cast(
            tuple[PortfolioProfileFamily, ...], collections["profile_families"]
        ),
        profile_revisions=cast(
            tuple[PortfolioProfileRevision, ...], collections["profile_revisions"]
        ),
        profile_bindings=cast(
            tuple[PortfolioProfileBinding, ...], collections["profile_bindings"]
        ),
        candidate_evaluations=cast(
            tuple[CandidateEvaluation, ...],
            collections["candidate_evaluations"],
        ),
        candidates=cast(
            tuple[PortfolioCandidate, ...], collections["candidates"]
        ),
        selections=cast(
            tuple[PortfolioSelection, ...], collections["selections"]
        ),
        placements=cast(
            tuple[PortfolioPlacement, ...], collections["placements"]
        ),
        arrangements=cast(
            tuple[SectionArrangementRevision, ...], collections["arrangements"]
        ),
        compositions=cast(
            tuple[WorkingPortfolioCompositionRevision, ...],
            collections["compositions"],
        ),
        audience_contexts=cast(
            tuple[AudienceContext, ...], collections["audience_contexts"]
        ),
        materializations=cast(
            tuple[SnapshotMaterializationRecord, ...],
            collections["materializations"],
        ),
        snapshot_entries=cast(
            tuple[SnapshotEntry, ...], collections["snapshot_entries"]
        ),
        snapshot_omissions=cast(
            tuple[SnapshotOmission, ...], collections["snapshot_omissions"]
        ),
        snapshot_manifests=cast(
            tuple[SnapshotManifest, ...], collections["snapshot_manifests"]
        ),
        snapshot_seals=cast(
            tuple[SnapshotSeal, ...], collections["snapshot_seals"]
        ),
        snapshot_editions=cast(
            tuple[SnapshotEdition, ...], collections["snapshot_editions"]
        ),
    )


def graph_to_canonical_json_bytes(graph: VitrineRecordGraph) -> bytes:
    return _canonical_bytes(graph_to_dict(graph))


def graph_from_json_bytes(data: bytes) -> VitrineRecordGraph:
    value = strict_json_loads(data)
    if not isinstance(value, Mapping):
        raise VitrineSerializationError("graph JSON must contain an object.")
    return graph_from_dict(cast(Mapping[str, object], value))


__all__ = [
    "graph_from_dict",
    "graph_from_json_bytes",
    "graph_to_canonical_json_bytes",
    "graph_to_dict",
    "record_from_json_bytes",
    "record_to_canonical_json_bytes",
    "strict_json_loads",
]
