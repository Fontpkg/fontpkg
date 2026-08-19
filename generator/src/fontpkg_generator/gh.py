import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_URL = "https://github.com/google/fonts"
LICENSE_DIRS = ("ofl", "apache", "ufl")
KEEP_NAMES = {"METADATA.pb", "OFL.txt", "LICENSE.txt", "UFL.txt"}
KEEP_SUFFIXES = (".ttf", ".otf")

# A shallow local clone, reused across calls in a process and across runs on the
# same machine. Cloning once and reading files from disk replaces thousands of
# individual, deliberately-paced GitHub API/download requests (the previous
# approach) with a single bulk git operation — faster, and immune to the
# per-request abuse-detection limits that a large families.txt would otherwise
# trip regardless of how politely those requests were spaced out.
CLONE_DIR = Path(
    os.environ.get("FONTPKG_GFONTS_CLONE", str(Path.home() / ".cache" / "fontpkg" / "google-fonts"))
)

_clone_ready = False


class FamilyNotFound(Exception):
    pass


@dataclass(frozen=True)
class FetchResult:
    family_dir: Path
    repo_path: str
    commit: str


def google_dirname(name_or_slug: str) -> str:
    return name_or_slug.lower().replace("-", "").replace(" ", "").replace("_", "")


def _ensure_clone() -> Path:
    global _clone_ready
    if _clone_ready:
        return CLONE_DIR
    if (CLONE_DIR / ".git").is_dir():
        subprocess.run(
            ["git", "-C", str(CLONE_DIR), "fetch", "--depth", "1", "origin", "HEAD"], check=True
        )
        subprocess.run(["git", "-C", str(CLONE_DIR), "reset", "--hard", "FETCH_HEAD"], check=True)
    else:
        CLONE_DIR.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", f"{REPO_URL}.git", str(CLONE_DIR)], check=True
        )
    _clone_ready = True
    return CLONE_DIR


def family_repo_path(name_or_slug: str) -> str:
    root = _ensure_clone()
    dirname = google_dirname(name_or_slug)
    for lic_dir in LICENSE_DIRS:
        if (root / lic_dir / dirname).is_dir():
            return f"{lic_dir}/{dirname}"
    raise FamilyNotFound(
        f"family directory {dirname!r} not found under {'/'.join(LICENSE_DIRS)} in google/fonts"
    )


def latest_commit(repo_path: str) -> str:
    root = _ensure_clone()
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"HEAD:{repo_path}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def fetch_family(name_or_slug: str, dest: Path) -> FetchResult:
    root = _ensure_clone()
    dirname = google_dirname(name_or_slug)
    repo_path = family_repo_path(name_or_slug)
    src_dir = root / repo_path
    family_dir = dest / dirname
    family_dir.mkdir(parents=True, exist_ok=True)
    for item in sorted(src_dir.iterdir()):
        if not item.is_file():
            continue
        if item.name not in KEEP_NAMES and item.suffix.lower() not in KEEP_SUFFIXES:
            continue
        shutil.copy2(item, family_dir / item.name)
    commit = latest_commit(repo_path)
    return FetchResult(family_dir=family_dir, repo_path=repo_path, commit=commit)
