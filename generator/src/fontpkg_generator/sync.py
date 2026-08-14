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
    catalog_path: Path | None = None,
) -> SyncReport:
    state = load_state(state_path)
    catalog = load_state(catalog_path) if catalog_path else {}
    report = SyncReport()
    for name in families:
        key = gh.google_dirname(name)
        try:
            _sync_one(name, key, state, catalog, out_dir, wheel_builder, report)
        except (gh.FamilyNotFound, UnsupportedLicense, FileNotFoundError, ValueError) as err:
            report.failed.append((key, str(err)))
    save_state(state_path, state)
    if catalog_path:
        save_state(catalog_path, catalog)
    return report


def catalog_entry(meta: dict) -> dict:
    files = meta.get("files", [])
    weights = sorted({f["weight"] for f in files if f.get("weight") is not None})
    wght = next((a for a in meta.get("axes", []) if a.get("tag") == "wght"), None)
    if wght:
        weight_range = [int(wght["min"]), int(wght["max"])]
    elif weights:
        weight_range = [weights[0], weights[-1]]
    else:
        weight_range = None
    return {
        "family": meta["family"],
        "slug": meta["slug"],
        "package": f"fontpkg-{meta['slug']}",
        "version": str(meta["version"]),
        "license": meta["license"],
        "category": meta.get("category", []),
        "styles": sorted({f.get("style", "normal") for f in files}),
        "variable": any(f.get("variable") for f in files),
        "weights": weights,
        "weight_range": weight_range,
    }


def _sync_one(
    name: str,
    key: str,
    state: dict,
    catalog: dict,
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
    meta = _built_metadata(pkg_root)
    version = str(meta["version"])
    if wheel_builder is not None:
        wheel_builder(pkg_root)
    state[key] = {
        "path": fetched.repo_path,
        "commit": fetched.commit,
        "version": version,
        "package": pkg_root.name,
    }
    catalog[meta["slug"]] = catalog_entry(meta)
    report.built.append((key, version))


def _built_metadata(pkg_root: Path) -> dict:
    module_dir = next((pkg_root / "src").iterdir())
    return json.loads((module_dir / "metadata.json").read_text(encoding="utf-8"))
