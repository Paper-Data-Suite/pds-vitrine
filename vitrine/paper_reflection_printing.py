"""Print-contract planning and Core route persistence for paper Reflections."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from pds_core.route_registrations import (
    RouteRegistrationPersistenceError,
    load_route_registration,
    write_route_registration,
)
from pds_core.routes import route_registration_path
from pds_core.workspace import WorkspaceRootError, resolve_workspace_root

from vitrine.models import ReflectionPromptIssuance, ReflectionResponsePage
from vitrine.paper_reflection_routes import (
    ReflectionResponsePageRoute,
    build_reflection_response_route_set,
)
from vitrine.storage import VitrineStorageError, load_current_records_with_state


class PaperReflectionPrintError(RuntimeError):
    """Base error for paper-Reflection print planning and route persistence."""


class PaperReflectionPrintContextError(PaperReflectionPrintError):
    """Raised when canonical issuance/page context is unavailable or contradictory."""


class PaperReflectionPrintRouteError(PaperReflectionPrintError):
    """Raised when Core route registrations cannot be safely prepared."""


class PaperReflectionPrintRoutePersistenceError(PaperReflectionPrintRouteError):
    """Raised when route persistence fails after complete preflight."""

    def __init__(
        self,
        message: str,
        *,
        created_paths: tuple[Path, ...] = (),
        verified_paths: tuple[Path, ...] = (),
        current_path: Path | None = None,
    ) -> None:
        super().__init__(message)
        self.created_paths = created_paths
        self.verified_paths = verified_paths
        self.current_path = current_path


@dataclass(frozen=True, slots=True)
class ReflectionPrintPlan:
    """Exact immutable inputs required by a later paper renderer."""

    workspace_root: Path
    state_revision: int
    issuance: ReflectionPromptIssuance
    pages: tuple[ReflectionResponsePage, ...]
    routes: tuple[ReflectionResponsePageRoute, ...]

    def __post_init__(self) -> None:
        validate_reflection_print_plan(self)


@dataclass(frozen=True, slots=True)
class PersistedReflectionPrintRoutes:
    """Verified Core registration result for one exact print plan."""

    plan: ReflectionPrintPlan
    registration_paths: tuple[Path, ...]
    created_paths: tuple[Path, ...]
    reused_paths: tuple[Path, ...]

    def __post_init__(self) -> None:
        validate_reflection_print_plan(self.plan)
        expected = tuple(
            route_registration_path(self.plan.workspace_root, route.locator)
            for route in self.plan.routes
        )
        if self.registration_paths != expected:
            raise PaperReflectionPrintRoutePersistenceError(
                "registration_paths do not match the plan's canonical routes."
            )
        if len(set(self.registration_paths)) != len(self.registration_paths):
            raise PaperReflectionPrintRoutePersistenceError(
                "registration_paths must be unique."
            )
        if set(self.created_paths) & set(self.reused_paths):
            raise PaperReflectionPrintRoutePersistenceError(
                "created_paths and reused_paths must be disjoint."
            )
        if set(self.created_paths) | set(self.reused_paths) != set(
            self.registration_paths
        ):
            raise PaperReflectionPrintRoutePersistenceError(
                "created/reused paths must account for every registration."
            )


@dataclass(frozen=True, slots=True)
class _RouteDestination:
    route: ReflectionResponsePageRoute
    path: Path
    exists_exactly: bool


def prepare_reflection_print_plan(
    workspace_root: str | Path,
    *,
    issuance_id: str,
    expected_state_revision: int,
) -> ReflectionPrintPlan:
    """Load one exact durable issuance/page set and build its print route plan."""

    root = _workspace_root(workspace_root)
    if (
        isinstance(expected_state_revision, bool)
        or not isinstance(expected_state_revision, int)
        or expected_state_revision < 1
    ):
        raise PaperReflectionPrintContextError(
            "expected_state_revision must be a positive non-Boolean integer."
        )
    if not isinstance(issuance_id, str) or not issuance_id.strip():
        raise PaperReflectionPrintContextError(
            "issuance_id must be a nonempty string."
        )

    try:
        current, records = load_current_records_with_state(root)
    except VitrineStorageError as error:
        raise PaperReflectionPrintContextError(
            "Canonical Vitrine state is unavailable for Reflection printing."
        ) from error
    if current.state_revision != expected_state_revision:
        raise PaperReflectionPrintContextError(
            "Vitrine state changed before Reflection print planning."
        )

    issuances = tuple(
        item
        for item in records
        if isinstance(item, ReflectionPromptIssuance)
        and item.issuance_id == issuance_id
    )
    if len(issuances) != 1:
        raise PaperReflectionPrintContextError(
            "Exact Reflection prompt issuance is missing or ambiguous."
        )
    issuance = issuances[0]

    related_pages = tuple(
        item
        for item in records
        if isinstance(item, ReflectionResponsePage)
        and item.issuance_id == issuance.issuance_id
    )
    pages_by_id = {item.response_page_id: item for item in related_pages}
    if len(pages_by_id) != len(related_pages):
        raise PaperReflectionPrintContextError(
            "Reflection issuance contains duplicate response-page identities."
        )
    if set(pages_by_id) != set(issuance.response_page_ids):
        raise PaperReflectionPrintContextError(
            "Durable Reflection response pages do not exactly match the issuance."
        )
    pages = tuple(pages_by_id[page_id] for page_id in issuance.response_page_ids)

    try:
        routes = build_reflection_response_route_set(issuance, pages)
    except ValueError as error:
        raise PaperReflectionPrintContextError(
            "Durable Reflection issuance/page context cannot form exact Core routes."
        ) from error

    plan = ReflectionPrintPlan(
        workspace_root=root,
        state_revision=current.state_revision,
        issuance=issuance,
        pages=pages,
        routes=routes,
    )
    preflight_reflection_print_route_registrations(plan)
    return plan


def validate_reflection_print_plan(value: object) -> ReflectionPrintPlan:
    """Revalidate a print plan without writing route registrations."""

    if not isinstance(value, ReflectionPrintPlan):
        raise PaperReflectionPrintContextError(
            "value must be a ReflectionPrintPlan."
        )
    root = _workspace_root(value.workspace_root)
    if value.workspace_root != root:
        raise PaperReflectionPrintContextError(
            "Print plan workspace_root must be canonical."
        )
    if (
        isinstance(value.state_revision, bool)
        or not isinstance(value.state_revision, int)
        or value.state_revision < 1
    ):
        raise PaperReflectionPrintContextError(
            "Print plan state_revision must be positive."
        )
    if not isinstance(value.issuance, ReflectionPromptIssuance):
        raise PaperReflectionPrintContextError(
            "Print plan issuance is invalid."
        )
    if not isinstance(value.pages, tuple) or not value.pages:
        raise PaperReflectionPrintContextError(
            "Print plan pages must be a nonempty tuple."
        )
    if not all(isinstance(page, ReflectionResponsePage) for page in value.pages):
        raise PaperReflectionPrintContextError(
            "Print plan pages contain an invalid record."
        )
    if tuple(page.response_page_id for page in value.pages) != (
        value.issuance.response_page_ids
    ):
        raise PaperReflectionPrintContextError(
            "Print plan pages do not preserve issuance page order."
        )
    try:
        expected_routes = build_reflection_response_route_set(
            value.issuance,
            value.pages,
        )
    except ValueError as error:
        raise PaperReflectionPrintContextError(
            "Print plan issuance/pages cannot form exact Core routes."
        ) from error
    if value.routes != expected_routes:
        raise PaperReflectionPrintContextError(
            "Print plan routes contradict immutable issuance/page records."
        )
    return value


def preflight_reflection_print_route_registrations(
    plan: ReflectionPrintPlan,
) -> tuple[Path, ...]:
    """Verify the full Core route set before any route-registration write."""

    destinations = _route_destinations(validate_reflection_print_plan(plan))
    return tuple(item.path for item in destinations)


def persist_reflection_print_route_registrations(
    plan: ReflectionPrintPlan,
) -> PersistedReflectionPrintRoutes:
    """Persist missing Core registrations after full-set preflight.

    Existing routes are reused only when they exactly equal the immutable plan.
    Core writes registrations individually, so a later write failure reports
    every registration already durably created or verified.
    """

    validated = validate_reflection_print_plan(plan)
    current = prepare_reflection_print_plan(
        validated.workspace_root,
        issuance_id=validated.issuance.issuance_id,
        expected_state_revision=validated.state_revision,
    )
    if current != validated:
        raise PaperReflectionPrintRoutePersistenceError(
            "Canonical Reflection print context changed since planning."
        )

    destinations = _route_destinations(validated)
    created: list[Path] = []
    reused: list[Path] = [
        item.path for item in destinations if item.exists_exactly
    ]
    verified: list[Path] = list(reused)

    for item in destinations:
        if item.exists_exactly:
            continue
        try:
            written = write_route_registration(
                validated.workspace_root,
                item.route.registration,
            )
            if written != item.path:
                raise PaperReflectionPrintRoutePersistenceError(
                    "Core wrote a Reflection route to a noncanonical path.",
                    created_paths=tuple(created),
                    verified_paths=tuple(verified),
                    current_path=written,
                )
            loaded = load_route_registration(
                validated.workspace_root,
                item.route.locator,
            )
            if loaded != item.route.registration:
                raise PaperReflectionPrintRoutePersistenceError(
                    "Reloaded Reflection route contradicts the immutable plan.",
                    created_paths=tuple((*created, item.path)),
                    verified_paths=tuple(verified),
                    current_path=item.path,
                )
        except PaperReflectionPrintRoutePersistenceError:
            raise
        except RouteRegistrationPersistenceError as error:
            if _registration_matches(
                validated.workspace_root,
                item.route,
            ):
                reused.append(item.path)
                verified.append(item.path)
                continue
            raise PaperReflectionPrintRoutePersistenceError(
                "Could not persist the complete Reflection route set.",
                created_paths=tuple(created),
                verified_paths=tuple(verified),
                current_path=item.path if os.path.lexists(item.path) else None,
            ) from error
        created.append(item.path)
        verified.append(item.path)

    for item in destinations:
        try:
            loaded = load_route_registration(
                validated.workspace_root,
                item.route.locator,
            )
        except RouteRegistrationPersistenceError as error:
            raise PaperReflectionPrintRoutePersistenceError(
                "Persisted Reflection route set could not be completely reloaded.",
                created_paths=tuple(created),
                verified_paths=tuple(verified),
                current_path=item.path if os.path.lexists(item.path) else None,
            ) from error
        if loaded != item.route.registration:
            raise PaperReflectionPrintRoutePersistenceError(
                "Persisted Reflection route set failed exact final verification.",
                created_paths=tuple(created),
                verified_paths=tuple(verified),
                current_path=item.path,
            )

    return PersistedReflectionPrintRoutes(
        plan=validated,
        registration_paths=tuple(item.path for item in destinations),
        created_paths=tuple(created),
        reused_paths=tuple(
            item.path
            for item in destinations
            if item.path not in set(created)
        ),
    )


def _route_destinations(
    plan: ReflectionPrintPlan,
) -> tuple[_RouteDestination, ...]:
    result: list[_RouteDestination] = []
    seen: set[Path] = set()
    for route in plan.routes:
        path = route_registration_path(plan.workspace_root, route.locator)
        if path in seen:
            raise PaperReflectionPrintRouteError(
                "Reflection route destinations must be unique."
            )
        seen.add(path)
        if os.path.lexists(path):
            try:
                loaded = load_route_registration(
                    plan.workspace_root,
                    route.locator,
                )
            except RouteRegistrationPersistenceError as error:
                raise PaperReflectionPrintRouteError(
                    f"Existing Core route registration is unreadable: {path}"
                ) from error
            if loaded != route.registration:
                raise PaperReflectionPrintRouteError(
                    f"Existing Core route registration contradicts the plan: {path}"
                )
            result.append(_RouteDestination(route, path, True))
        else:
            result.append(_RouteDestination(route, path, False))
    return tuple(result)


def _registration_matches(
    root: Path,
    route: ReflectionResponsePageRoute,
) -> bool:
    try:
        return load_route_registration(root, route.locator) == route.registration
    except RouteRegistrationPersistenceError:
        return False


def _workspace_root(value: str | Path) -> Path:
    try:
        root = resolve_workspace_root(value)
    except (WorkspaceRootError, TypeError, ValueError, OSError) as error:
        raise PaperReflectionPrintContextError(
            "workspace_root is invalid."
        ) from error
    if not root.is_absolute():
        raise PaperReflectionPrintContextError(
            "workspace_root must resolve to an absolute path."
        )
    return root


__all__ = [
    "PaperReflectionPrintContextError",
    "PaperReflectionPrintError",
    "PaperReflectionPrintRouteError",
    "PaperReflectionPrintRoutePersistenceError",
    "PersistedReflectionPrintRoutes",
    "ReflectionPrintPlan",
    "persist_reflection_print_route_registrations",
    "preflight_reflection_print_route_registrations",
    "prepare_reflection_print_plan",
    "validate_reflection_print_plan",
]
