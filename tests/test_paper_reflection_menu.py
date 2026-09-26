from __future__ import annotations

import io
from pathlib import Path

from scripts.curation_fixture_support import build_curation_fixture_workspace
from vitrine.paper_reflection_menu import run_paper_reflection_menu
from vitrine.workflow_context import default_workflow_dependencies


def _inputs(values: list[str]):
    iterator = iter(values)
    return lambda _prompt: next(iterator)


def test_portfolio_reflection_menu_leads_with_paper_status(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    output = io.StringIO()

    run_paper_reflection_menu(
        portfolio_id=setup.portfolio_id,
        input_fn=_inputs(["B"]),
        output=output,
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        workspace_root=setup.workspace,
    )

    rendered = output.getvalue()
    assert "Student Reflection" in rendered
    assert "Growth comparison reflection" in rendered
    assert "Status: Prompt not issued" in rendered
    assert "Paper is the primary Reflection workflow." in rendered
    assert "Typed/manual Reflection remains a fallback" in rendered
