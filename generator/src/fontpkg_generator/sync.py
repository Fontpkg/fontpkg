import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from fontpkg_generator import gh
from fontpkg_generator.build import SourceInfo, UnsupportedLicense, build_package


@dataclass
class SyncReport:
    built: list[tuple[str, str]] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)


def load_state(path: Path) -> dict:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sync_families(
    families: list[str],
    state_path: Path,
    out_dir: Path,
    wheel_builder: Callable[[Path], None] | None = None,
) -> SyncReport:
    state = load_state(state_path)
    report = SyncReport()
    for name in families:
        key = gh.google_dirname(name)
        try:
            _sync_one(name, key, state, out_dir, wheel_builder, report)
        except (gh.FamilyNotFound, UnsupportedLicense, FileNotFoundError, ValueError) as err:
            report.failed.append((key, str(err)))
    save_state(state_path, state)
    return report


def _sync_one(
    name: str,
    key: str,
    state: dict,
    out_dir: Path,
    wheel_builder: Callable[[Path], None] | None,
    report: SyncReport,
) -> None:
    entry = state.get(key)
    repo_path = entry["path"] if entry else gh.family_repo_path(name)
    latest = gh.latest_commit(repo_path)
    if entry and entry.get("commit") == latest:
        report.unchanged.append(key)
        return
    with tempfile.TemporaryDirectory(prefix="fontpkg-sync-") as tmp:
        fetched = gh.fetch_family(name, Path(tmp))
        source = SourceInfo(repo=gh.REPO_URL, path=fetched.repo_path, commit=fetched.commit)
        pkg_root = build_package(fetched.family_dir, out_dir, source=source)
    version = _built_version(pkg_root)
    if wheel_builder is not None:
        wheel_builder(pkg_root)
    state[key] = {
        "path": fetched.repo_path,
        "commit": fetched.commit,
        "version": version,
        "package": pkg_root.name,
    }
    report.built.append((key, version))


def _built_version(pkg_root: Path) -> str:
    module_dir = next((pkg_root / "src").iterdir())
    meta = json.loads((module_dir / "metadata.json").read_text(encoding="utf-8"))
    return str(meta["version"])
