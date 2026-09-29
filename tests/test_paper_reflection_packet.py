from __future__ import annotations

from pathlib import Path

from scripts.curation_fixture_support import (
    ACTOR,
    REFLECTION_REQUIREMENT_ID,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.models import CurationTargetRef
from vitrine.paper_reflection_packet import (
    issue_paper_reflection_packet,
    render_issued_paper_reflection_packet,
)
from vitrine.paper_reflection_pdf import exact_curated_target_lines
from vitrine.teacher_presentation import build_teacher_portfolio_overview


def test_issue_packet_persists_routes_and_renders_pdf(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    overview = build_teacher_portfolio_overview(
        setup.workspace,
        setup.portfolio_id,
    )
    assert len(overview.subject_links) == 1
    link = overview.subject_links[0]

    packet = issue_paper_reflection_packet(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="growth_compare",
        prompt_version="1",
        prompt_snapshot=(
            "Compare the selected Portfolio evidence. What do you notice?"
        ),
        subject_link_id=link.subject_link_id,
        issued_by=ACTOR,
        target_scope="portfolio",
        target_references=(
            CurationTargetRef(
                target_kind="portfolio",
                target_id=setup.portfolio_id,
            ),
        ),
        page_count=2,
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        student_display_name=link.display_name,
        clock=fixed_clock,
        id_factory=setup.ids,
    )

    assert packet.pdf_path.is_file()
    assert packet.pdf_path.read_bytes().startswith(b"%PDF")
    assert len(packet.issuance.response_page_ids) == 2
    assert len(packet.registration_paths) == 2
    assert len(packet.created_registration_paths) == 2
    assert packet.reused_registration_paths == ()
    assert all(path.is_file() for path in packet.registration_paths)

    replay = render_issued_paper_reflection_packet(
        setup.workspace,
        issuance_id=packet.issuance.issuance_id,
        expected_state_revision=packet.state_revision,
        student_display_name=link.display_name,
    )

    assert replay.issuance == packet.issuance
    assert replay.pdf_path == packet.pdf_path
    assert replay.registration_paths == packet.registration_paths
    assert replay.created_registration_paths == ()
    assert replay.reused_registration_paths == packet.registration_paths
    assert replay.pdf_path.read_bytes().startswith(b"%PDF")

def test_exact_curated_target_lines_preserve_frozen_target_identity() -> None:
    targets = (
        CurationTargetRef(
            target_kind="portfolio",
            target_id="portfolio_alpha",
        ),
        CurationTargetRef(
            target_kind="portfolio",
            target_id="portfolio_beta",
        ),
    )

    assert exact_curated_target_lines(targets) == (
        "Exact curated targets (2):",
        "Target 1: portfolio:portfolio_alpha",
        "Target 2: portfolio:portfolio_beta",
    )
