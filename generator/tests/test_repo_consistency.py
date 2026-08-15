import json
from pathlib import Path

from fontpkg_generator.gh import google_dirname

REPO_ROOT = Path(__file__).parents[2]

RETIRED_FAMILIES: set[str] = set()


def _tracked_dirnames() -> set[str]:
    lines = (REPO_ROOT / "families.txt").read_text(encoding="utf-8").splitlines()
    return {google_dirname(ln.strip()) for ln in lines if ln.strip() and not ln.startswith("#")}


def test_every_published_family_is_still_tracked() -> None:
    state = json.loads((REPO_ROOT / "state.json").read_text(encoding="utf-8"))
    tracked = _tracked_dirnames()
    lost = {
        key
        for key, entry in state.items()
        if entry.get("published") and key not in tracked and key not in RETIRED_FAMILIES
    }
    assert not lost, (
        f"published families missing from families.txt: {sorted(lost)} — "
        "a list regeneration silently dropped tracked families. Re-add them, or if the "
        "removal is deliberate, add them to RETIRED_FAMILIES in this test."
    )


def test_every_state_family_is_tracked_or_retired() -> None:
    state = json.loads((REPO_ROOT / "state.json").read_text(encoding="utf-8"))
    tracked = _tracked_dirnames()
    lost = {k for k in state if k not in tracked and k not in RETIRED_FAMILIES}
    assert not lost, f"state.json families missing from families.txt: {sorted(lost)}"
