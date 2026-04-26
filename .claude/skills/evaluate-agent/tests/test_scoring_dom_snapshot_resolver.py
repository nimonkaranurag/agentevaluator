"""
Tests for locating the post-submit DOM snapshot under a case directory.
"""

from __future__ import annotations

from pathlib import Path

from evaluate_agent.scoring import (
    ResolvedDOMSnapshot,
    post_submit_dom_snapshot_dir,
    resolve_post_submit_dom_snapshot,
)


def _seed_case_dir(case_dir: Path) -> Path:
    dom_dir = case_dir / "trace" / "dom"
    dom_dir.mkdir(parents=True, exist_ok=True)
    return dom_dir


class TestPostSubmitDomSnapshotDir:
    def test_path_shape(self, tmp_path):
        case_dir = tmp_path / "demo-case"
        result = post_submit_dom_snapshot_dir(case_dir)
        assert result == case_dir / "trace" / "dom"

    def test_does_not_create(self, tmp_path):
        case_dir = tmp_path / "demo-case"
        post_submit_dom_snapshot_dir(case_dir)
        assert not (case_dir / "trace").exists()


class TestResolveReturnsNone:
    def test_no_dom_dir(self, tmp_path):
        assert (
            resolve_post_submit_dom_snapshot(tmp_path)
            is None
        )

    def test_dom_dir_empty(self, tmp_path):
        _seed_case_dir(tmp_path)
        assert (
            resolve_post_submit_dom_snapshot(tmp_path)
            is None
        )

    def test_only_landing_present(self, tmp_path):
        dom_dir = _seed_case_dir(tmp_path)
        (dom_dir / "step-001-landing.html").write_text(
            "<html></html>", encoding="utf-8"
        )
        assert (
            resolve_post_submit_dom_snapshot(tmp_path)
            is None
        )

    def test_only_auto_snapshots_present(self, tmp_path):
        dom_dir = _seed_case_dir(tmp_path)
        (dom_dir / "auto-001-nav.html").write_text(
            "<html></html>", encoding="utf-8"
        )
        (dom_dir / "auto-002-nav.html").write_text(
            "<html></html>", encoding="utf-8"
        )
        assert (
            resolve_post_submit_dom_snapshot(tmp_path)
            is None
        )

    def test_other_explicit_labels_present(self, tmp_path):
        dom_dir = _seed_case_dir(tmp_path)
        (
            dom_dir / "step-002-some_other_label.html"
        ).write_text("<html></html>", encoding="utf-8")
        assert (
            resolve_post_submit_dom_snapshot(tmp_path)
            is None
        )

    def test_path_is_a_file_not_dir(self, tmp_path):
        trace = tmp_path / "trace"
        trace.mkdir()
        (trace / "dom").write_text(
            "this is a file", encoding="utf-8"
        )
        assert (
            resolve_post_submit_dom_snapshot(tmp_path)
            is None
        )


class TestResolveReturnsParsedSnapshot:
    def test_single_after_submit_file(self, tmp_path):
        dom_dir = _seed_case_dir(tmp_path)
        target = dom_dir / "step-002-after_submit.html"
        target.write_text(
            "<html><body><p>hello</p></body></html>",
            encoding="utf-8",
        )
        result = resolve_post_submit_dom_snapshot(tmp_path)
        assert isinstance(result, ResolvedDOMSnapshot)
        assert result.path == target
        assert result.visible_text == "hello"

    def test_multiple_after_submit_picks_highest_step(
        self, tmp_path
    ):
        dom_dir = _seed_case_dir(tmp_path)
        (dom_dir / "step-002-after_submit.html").write_text(
            "<html>early</html>", encoding="utf-8"
        )
        latest = dom_dir / "step-005-after_submit.html"
        latest.write_text(
            "<html><body>latest</body></html>",
            encoding="utf-8",
        )
        (dom_dir / "step-003-after_submit.html").write_text(
            "<html>middle</html>", encoding="utf-8"
        )
        result = resolve_post_submit_dom_snapshot(tmp_path)
        assert result.path == latest
        assert result.visible_text == "latest"

    def test_step_numbers_sorted_numerically(
        self, tmp_path
    ):
        dom_dir = _seed_case_dir(tmp_path)
        (dom_dir / "step-002-after_submit.html").write_text(
            "<html><body>two</body></html>",
            encoding="utf-8",
        )
        latest = dom_dir / "step-010-after_submit.html"
        latest.write_text(
            "<html><body>ten</body></html>",
            encoding="utf-8",
        )
        result = resolve_post_submit_dom_snapshot(tmp_path)
        assert result.path == latest
        assert result.visible_text == "ten"

    def test_ignores_non_explicit_prefixes(self, tmp_path):
        dom_dir = _seed_case_dir(tmp_path)
        (dom_dir / "auto-002-after_submit.html").write_text(
            "<html><body>auto</body></html>",
            encoding="utf-8",
        )
        target = dom_dir / "step-002-after_submit.html"
        target.write_text(
            "<html><body>explicit</body></html>",
            encoding="utf-8",
        )
        result = resolve_post_submit_dom_snapshot(tmp_path)
        assert result.path == target
        assert result.visible_text == "explicit"

    def test_ignores_files_outside_dom_dir(self, tmp_path):
        dom_dir = _seed_case_dir(tmp_path)
        (
            tmp_path / "step-002-after_submit.html"
        ).write_text(
            "<html>misplaced</html>", encoding="utf-8"
        )
        target = dom_dir / "step-002-after_submit.html"
        target.write_text(
            "<html><body>real</body></html>",
            encoding="utf-8",
        )
        result = resolve_post_submit_dom_snapshot(tmp_path)
        assert result.path == target
        assert result.visible_text == "real"


class TestResolvedDOMSnapshotShape:
    def test_frozen(self, tmp_path):
        dom_dir = _seed_case_dir(tmp_path)
        target = dom_dir / "step-002-after_submit.html"
        target.write_text(
            "<html><body>x</body></html>",
            encoding="utf-8",
        )
        snapshot = resolve_post_submit_dom_snapshot(
            tmp_path
        )
        try:
            snapshot.path = target  # type: ignore[misc]
        except Exception:
            return
        raise AssertionError(
            "ResolvedDOMSnapshot is not frozen"
        )
