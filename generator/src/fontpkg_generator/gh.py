import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

API = "https://api.github.com/repos/google/fonts"
REPO_URL = "https://github.com/google/fonts"
LICENSE_DIRS = ("ofl", "apache", "ufl")
KEEP_NAMES = {"METADATA.pb", "OFL.txt", "LICENSE.txt", "UFL.txt"}
KEEP_SUFFIXES = (".ttf", ".otf")


class FamilyNotFound(Exception):
    pass


@dataclass(frozen=True)
class FetchResult:
    family_dir: Path
    repo_path: str
    commit: str


def google_dirname(name_or_slug: str) -> str:
    return name_or_slug.lower().replace("-", "").replace(" ", "").replace("_", "")


def fetch_family(name_or_slug: str, dest: Path) -> FetchResult:
    dirname = google_dirname(name_or_slug)
    repo_path, listing = _find_family(dirname)
    family_dir = dest / dirname
    family_dir.mkdir(parents=True, exist_ok=True)
    for item in listing:
        if item.get("type") != "file":
            continue
        name = item["name"]
        if name not in KEEP_NAMES and not name.lower().endswith(KEEP_SUFFIXES):
            continue
        _download(item["download_url"], family_dir / name)
    commit = latest_commit(repo_path)
    return FetchResult(family_dir=family_dir, repo_path=repo_path, commit=commit)


def _find_family(dirname: str) -> tuple[str, list[dict]]:
    for lic_dir in LICENSE_DIRS:
        repo_path = f"{lic_dir}/{dirname}"
        try:
            listing = _get_json(f"{API}/contents/{repo_path}")
        except urllib.error.HTTPError as err:
            if err.code == 404:
                continue
            raise
        return repo_path, listing
    raise FamilyNotFound(
        f"family directory {dirname!r} not found under {'/'.join(LICENSE_DIRS)} in google/fonts"
    )


def latest_commit(repo_path: str) -> str:
    commits = _get_json(f"{API}/commits?path={repo_path}&per_page=1")
    return commits[0]["sha"] if commits else "unknown"


def family_repo_path(name_or_slug: str) -> str:
    repo_path, _ = _find_family(google_dirname(name_or_slug))
    return repo_path


def _request(url: str) -> urllib.request.Request:
    headers = {"User-Agent": "fontpkg-generator/0.1"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def _get_json(url: str) -> dict | list:
    with urllib.request.urlopen(_request(url), timeout=60) as response:
        return json.load(response)


def _download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(_request(url), timeout=120) as response:
        dest.write_bytes(response.read())
