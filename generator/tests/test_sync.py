import json
import shutil
from pathlib import Path

import pytest

import fontpkg_generator.gh as gh
from fontpkg_generator.gh import FetchResult
from fontpkg_generator.sync import load_state, publish_pending, sync_families


@pytest.fixture
def fake_upstream(static_family_dir: Path, monkeypatch):
    calls = {"fetch": 0, "probe": 0, "commit": 0}
    upstream = {"commit": "sha-1"}

    def fake_repo_path(name: str) -> str:
        calls["probe"] += 1
        return "ofl/testface"

    def fake_latest_commit(repo_path: str) -> str:
        calls["commit"] += 1
        return upstream["commit"]

    def fake_fetch(name: str, dest: Path) -> FetchResult:
        calls["fetch"] += 1
        target = dest / "testface"
        shutil.copytree(static_family_dir, target)
        return FetchResult(family_dir=target, repo_path="ofl/testface", commit=upstream["commit"])

    monkeypatch.setattr(gh, "family_repo_path", fake_repo_path)
    monkeypatch.setattr(gh, "latest_commit", fake_latest_commit)
    monkeypatch.setattr(gh, "fetch_family", fake_fetch)
    return calls, upstream


def test_first_sync_builds_and_records_state(fake_upstream, tmp_path: Path) -> None:
    calls, _ = fake_upstream
    state_path = tmp_path / "state.json"
    catalog_path = tmp_path / "catalog.json"
    report = sync_families(["testface"], state_path, tmp_path / "out", catalog_path=catalog_path)
    assert report.built == [("testface", "2.137")]
    assert report.unchanged == [] and report.failed == []
    state = load_state(state_path)
    assert state["testface"]["commit"] == "sha-1"
    assert state["testface"]["version"] == "2.137"
    assert state["testface"]["package"] == "fontpkg-testface"
    assert calls["fetch"] == 1
    entry = load_state(catalog_path)["testface"]
    assert entry["package"] == "fontpkg-testface"
    assert entry["styles"] == ["italic", "normal"]
    assert entry["variable"] is False
    assert entry["weights"] == [400]
    assert entry["weight_range"] == [400, 400]
    assert entry["category"] == ["SANS_SERIF"]


def test_unchanged_family_is_skipped(fake_upstream, tmp_path: Path) -> None:
    calls, _ = fake_upstream
    state_path = tmp_path / "state.json"
    sync_families(["testface"], state_path, tmp_path / "out")
    report = sync_families(["testface"], state_path, tmp_path / "out")
    assert report.unchanged == ["testface"]
    assert report.built == []
    assert calls["fetch"] == 1
    assert calls["probe"] == 1


def test_changed_commit_triggers_rebuild(fake_upstream, tmp_path: Path) -> None:
    calls, upstream = fake_upstream
    state_path = tmp_path / "state.json"
    sync_families(["testface"], state_path, tmp_path / "out")
    upstream["commit"] = "sha-2"
    report = sync_families(["testface"], state_path, tmp_path / "out")
    assert report.built == [("testface", "2.137")]
    assert load_state(state_path)["testface"]["commit"] == "sha-2"
    assert calls["fetch"] == 2


def test_failure_is_reported_and_state_preserved(fake_upstream, tmp_path: Path, monkeypatch) -> None:
    _, _ = fake_upstream
    state_path = tmp_path / "state.json"
    sync_families(["testface"], state_path, tmp_path / "out")

    def boom(name: str) -> str:
        raise gh.FamilyNotFound("nope")

    monkeypatch.setattr(gh, "family_repo_path", boom)
    report = sync_families(["missingface"], state_path, tmp_path / "out")
    assert report.failed == [("missingface", "nope")]
    state = load_state(state_path)
    assert "testface" in state and "missingface" not in state


def test_rate_limit_style_error_is_recorded_and_sync_continues(
    fake_upstream, tmp_path: Path, monkeypatch
) -> None:
    import urllib.error

    real_fetch = gh.fetch_family

    def flaky_fetch(name: str, dest: Path):
        if name == "otherface":
            raise urllib.error.URLError("rate limited")
        return real_fetch(name, dest)

    monkeypatch.setattr(gh, "fetch_family", flaky_fetch)
    state_path = tmp_path / "state.json"

    report = sync_families(["testface", "otherface", "thirdface"], state_path, tmp_path / "out")

    assert report.failed == [("otherface", "<urlopen error rate limited>")]
    state = load_state(state_path)
    assert set(state) == {"testface", "thirdface"}


def test_sync_aborts_early_after_consecutive_network_failures(
    fake_upstream, tmp_path: Path, monkeypatch
) -> None:
    import urllib.error

    from fontpkg_generator.sync import CONSECUTIVE_FAILURE_LIMIT

    def always_fails(name: str, dest: Path):
        raise urllib.error.URLError("rate limited")

    monkeypatch.setattr(gh, "fetch_family", always_fails)
    state_path = tmp_path / "state.json"
    families = [f"family{i}" for i in range(CONSECUTIVE_FAILURE_LIMIT + 10)]

    report = sync_families(families, state_path, tmp_path / "out")

    assert report.aborted_early is True
    assert len(report.failed) == CONSECUTIVE_FAILURE_LIMIT


def test_a_success_resets_the_consecutive_failure_counter(
    fake_upstream, tmp_path: Path, monkeypatch
) -> None:
    import urllib.error

    from fontpkg_generator.sync import CONSECUTIVE_FAILURE_LIMIT

    real_fetch = gh.fetch_family
    calls = {"n": 0}

    def mostly_fails(name: str, dest: Path):
        calls["n"] += 1
        # Fail just under the limit, succeed once, then fail again — the
        # intervening success must reset the streak so we don't abort early.
        if calls["n"] % CONSECUTIVE_FAILURE_LIMIT == 0:
            return real_fetch(name, dest)
        raise urllib.error.URLError("rate limited")

    monkeypatch.setattr(gh, "fetch_family", mostly_fails)
    state_path = tmp_path / "state.json"
    families = [f"family{i}" for i in range(CONSECUTIVE_FAILURE_LIMIT * 2)]

    report = sync_families(families, state_path, tmp_path / "out")

    assert report.aborted_early is False
    assert len(report.built) == 2


def test_state_saved_even_on_a_genuinely_unexpected_exception(
    fake_upstream, tmp_path: Path, monkeypatch
) -> None:
    real_fetch = gh.fetch_family

    def flaky_fetch(name: str, dest: Path):
        if name == "otherface":
            raise RuntimeError("unexpected bug")
        return real_fetch(name, dest)

    monkeypatch.setattr(gh, "fetch_family", flaky_fetch)
    state_path = tmp_path / "state.json"

    with pytest.raises(RuntimeError):
        sync_families(["testface", "otherface", "thirdface"], state_path, tmp_path / "out")

    # testface was built before the crash — must not be lost, even though the
    # function never reached its normal (pre-fix) single save-at-the-end call.
    assert set(load_state(state_path)) == {"testface"}


def test_wheel_builder_hook_called(fake_upstream, tmp_path: Path) -> None:
    built: list[Path] = []
    sync_families(
        ["testface"], tmp_path / "state.json", tmp_path / "out", wheel_builder=built.append
    )
    assert built == [tmp_path / "out" / "fontpkg-testface"]


def test_new_build_is_marked_unpublished(fake_upstream, tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    sync_families(["testface"], state_path, tmp_path / "out")
    assert load_state(state_path)["testface"]["published"] is False


def test_publish_pending_marks_success_and_skips(fake_upstream, tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    out = tmp_path / "out"
    sync_families(["testface"], state_path, out)
    (out / "fontpkg-testface" / "dist").mkdir()
    (out / "fontpkg-testface" / "dist" / "x.whl").write_bytes(b"")

    report = publish_pending(state_path, out, publisher=lambda p: False, rebuild=False)
    assert report.skipped == ["testface"]
    assert load_state(state_path)["testface"]["published"] is False

    attempts: list[Path] = []

    def publisher(pkg_root: Path) -> bool:
        attempts.append(pkg_root)
        return True

    report = publish_pending(state_path, out, publisher=publisher, rebuild=False)
    assert report.published == ["testface"]
    assert attempts == [out / "fontpkg-testface"]
    assert load_state(state_path)["testface"]["published"] is True

    report = publish_pending(state_path, out, publisher=publisher, rebuild=False)
    assert report.published == [] and report.skipped == []
    assert attempts == [out / "fontpkg-testface"]


def test_publish_pending_respects_priority_order(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "abel": {"package": "fontpkg-abel", "published": False},
                "roboto": {"package": "fontpkg-roboto", "published": False},
                "zeyada": {"package": "fontpkg-zeyada", "published": False},
            }
        ),
        encoding="utf-8",
    )
    attempted: list[str] = []

    def publisher(pkg_root: Path) -> bool:
        attempted.append(pkg_root.name)
        return False

    publish_pending(
        state_path, tmp_path, publisher=publisher, rebuild=False, priority=["roboto", "zeyada"]
    )
    assert attempted == ["fontpkg-roboto", "fontpkg-zeyada", "fontpkg-abel"]


def test_state_json_is_sorted_and_stable(fake_upstream, tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    sync_families(["testface"], state_path, tmp_path / "out")
    text = state_path.read_text(encoding="utf-8")
    assert text == json.dumps(json.loads(text), indent=2, sort_keys=True) + "\n"
