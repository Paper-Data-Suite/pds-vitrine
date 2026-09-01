from __future__ import annotations

from pds_core.publication_compatibility import PublicationProducerRegistry

import vitrine.workflow_context as workflow_context


def test_default_workflow_dependencies_do_not_discover_installed_producers(
    monkeypatch,
) -> None:
    calls = 0

    def forbidden_discovery(**_kwargs: object) -> PublicationProducerRegistry:
        nonlocal calls
        calls += 1
        raise AssertionError("default workflow dependencies must not discover producers")

    monkeypatch.setattr(
        workflow_context,
        "build_publication_producer_registry",
        forbidden_discovery,
    )

    dependencies = workflow_context.default_workflow_dependencies()

    assert calls == 0
    assert dependencies.producer_registry.profiles == ()
    assert dependencies.adapter_registry.adapters == ()
    assert dependencies.development_fixture_mode is False


def test_installed_producer_registry_discovery_is_explicit_and_core_owned(
    monkeypatch,
) -> None:
    expected = PublicationProducerRegistry(profiles=())
    calls: list[dict[str, object]] = []

    def recording_discovery(**kwargs: object) -> PublicationProducerRegistry:
        calls.append(dict(kwargs))
        return expected

    monkeypatch.setattr(
        workflow_context,
        "build_publication_producer_registry",
        recording_discovery,
    )

    result = workflow_context.build_installed_producer_registry()

    assert result is expected
    assert calls == [
        {
            "explicit_profiles": (),
            "discover_installed": True,
        }
    ]


def test_installed_producer_discovery_does_not_enable_live_adapters(
    monkeypatch,
) -> None:
    expected = PublicationProducerRegistry(profiles=())

    monkeypatch.setattr(
        workflow_context,
        "build_publication_producer_registry",
        lambda **_kwargs: expected,
    )

    producer_registry = workflow_context.build_installed_producer_registry()
    dependencies = workflow_context.default_workflow_dependencies()

    assert producer_registry is expected
    assert dependencies.adapter_registry.adapters == ()
    assert dependencies.producer_registry.profiles == ()
