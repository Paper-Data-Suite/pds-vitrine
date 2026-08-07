from pathlib import Path

import pytest

from vitrine.models import (
    VitrineSerializationError,
    graph_from_json_bytes,
    graph_to_canonical_json_bytes,
    strict_json_loads,
    validate_record_graph,
)

FIXTURES = Path(__file__).parent / "fixtures" / "runtime-models"


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.json")))
def test_canonical_fixture_round_trip(path: Path) -> None:
    content = path.read_bytes()
    graph = graph_from_json_bytes(content)
    validate_record_graph(graph)
    assert graph_to_canonical_json_bytes(graph) == content


def test_duplicate_json_keys_are_rejected() -> None:
    with pytest.raises(VitrineSerializationError, match="duplicate JSON key"):
        strict_json_loads(b'{"record_type":"portfolio","record_type":"portfolio"}')


def test_bom_and_nonfinite_values_are_rejected() -> None:
    with pytest.raises(VitrineSerializationError, match="BOM"):
        strict_json_loads(b"\xef\xbb\xbf{}")
    with pytest.raises(VitrineSerializationError, match="nonfinite"):
        strict_json_loads(b'{"value":NaN}')


def test_unknown_graph_key_is_rejected() -> None:
    content = next(FIXTURES.glob("*.json")).read_bytes()
    value = strict_json_loads(content)
    assert isinstance(value, dict)
    value["unknown"] = []
    import json

    with pytest.raises(VitrineSerializationError, match="unknown key"):
        graph_from_json_bytes(json.dumps(value).encode())


def test_graph_collection_rejects_wrong_record_family() -> None:
    import json

    content = next(FIXTURES.glob("*.json")).read_bytes()
    value = strict_json_loads(content)
    assert isinstance(value, dict)
    portfolios = value["portfolios"]
    subjects = value["portfolio_subjects"]
    assert isinstance(portfolios, list)
    assert isinstance(subjects, list)
    subjects.append(portfolios[0])
    with pytest.raises(VitrineSerializationError, match="PortfolioSubject records"):
        graph_from_json_bytes(json.dumps(value).encode())
