"""MONO-THEME-02 — epic matrix: S0–S5 cross-slice contract guardrails."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

EPIC_TEST_FILES = (
    "tests/test_mono_theme_02_visual_contract.py",
    "tests/test_mono_theme_02_s1_sidebar_polish.py",
    "tests/test_mono_theme_02_s2_topbar_refinement.py",
    "tests/test_mono_theme_02_s3_dashboard_refinement.py",
    "tests/test_mono_theme_02_s4_table_refinement.py",
    "tests/test_mono_theme_02_s5_mobile_parity.py",
)

EPIC_DOCS = (
    "docs/MONO_THEME_02_VISUAL_CONTRACT.md",
    "docs/MONO_THEME_02_IMPLEMENTATION_AUDIT.md",
)

EPIC_TAGS = (
    "mono-theme-02-s0-visual-contract",
    "mono-theme-02-s1-sidebar-refinement",
    "mono-theme-02-s2-topbar-refinement",
    "mono-theme-02-s3-dashboard-refinement",
    "mono-theme-02-s4-table-refinement",
    "mono-theme-02-s5-mobile-parity",
)

SLICE_MARKERS = (
    "MONO-THEME-02-S0",
    "MONO-THEME-02-S1",
    "MONO-THEME-02-S2",
    "MONO-THEME-02-S3",
    "MONO-THEME-02-S4",
    "MONO-THEME-02-S5",
)


@pytest.mark.parametrize("rel_path", EPIC_TEST_FILES)
def test_epic_test_files_exist(rel_path):
    assert (ROOT / rel_path).is_file()


@pytest.mark.parametrize("rel_path", EPIC_DOCS)
def test_epic_docs_exist(rel_path):
    p = ROOT / rel_path
    assert p.is_file() and p.stat().st_size > 0


@pytest.mark.parametrize("tag", EPIC_TAGS)
def test_epic_git_tags_exist(tag):
    import subprocess

    out = subprocess.run(
        ["git", "rev-parse", tag],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0, f"Missing git tag: {tag}"


@pytest.mark.parametrize("marker", SLICE_MARKERS)
def test_theme_css_carries_slice_markers(marker):
    css = (ROOT / "ui" / "theme.css").read_text(encoding="utf-8")
    if marker in ("MONO-THEME-02-S0",):
        pytest.skip("S0 is audit-only")
    assert marker in css, f"theme.css missing {marker}"


def test_widgets_carries_s3_s4_s5_markers():
    css = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    for marker in ("MONO-THEME-02-S3", "MONO-THEME-02-S4", "MONO-THEME-02-S5"):
        assert marker in css, f"widgets.css missing {marker}"


def test_mobile_shell_carries_s5_marker():
    css = (ROOT / "ui" / "mobile_shell.css").read_text(encoding="utf-8")
    assert "MONO-THEME-02-S5" in css


def test_contract_doc_marks_epic_complete():
    text = (ROOT / "docs" / "MONO_THEME_02_VISUAL_CONTRACT.md").read_text(encoding="utf-8").lower()
    assert "mono-theme-02-s5" in text
    assert "complete" in text.split("mono-theme-02-s5")[1][:200]


def test_audit_doc_marks_all_slices_committed():
    text = (ROOT / "docs" / "MONO_THEME_02_IMPLEMENTATION_AUDIT.md").read_text(encoding="utf-8")
    for label in ("S0", "S1", "S2", "S3", "S4", "S5"):
        assert f"**{label}**" in text
        assert "Committed" in text.split(f"**{label}**")[1][:120]


def test_roadmap_marks_mono_theme_02_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "MONO-THEME-02" in roadmap
    section = roadmap.split("## MONO-THEME-02", 1)[1].split("## ", 1)[0]
    assert "Complete" in section
    assert "mono-theme-02-s5" in section.lower() or "S5" in section
