import importlib.resources
import json
from importlib.metadata import entry_points
from pathlib import Path

from fontpkg._models import Family, FontFile, family_from_metadata
from fontpkg._resolve import slugify
from fontpkg.errors import FamilyNotInstalled

_cache: dict[str, Family] | None = None

ENTRY_POINT_GROUP = "fontpkg.family"
LEGACY_GROUP = "fonts_ttf"


def _load_native() -> dict[str, Family]:
    fams: dict[str, Family] = {}
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        module = ep.load()
        root = importlib.resources.files(module)
        meta = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
        fam = family_from_metadata(meta, root)
        fams[fam.slug] = fam
    return fams


def _load_legacy() -> dict[str, Family]:
    fams: dict[str, Family] = {}
    for ep in entry_points(group=LEGACY_GROUP):
        try:
            value = ep.load()
        except Exception:
            continue
        if not isinstance(value, (str, Path)):
            continue
        slug = slugify(ep.name)
        fams[slug] = Family(
            name=ep.name,
            slug=slug,
            version="0",
            license="unknown",
            files=(FontFile(path=Path(value), style="normal", weight=400, variable=False),),
        )
    return fams


def families(refresh: bool = False) -> dict[str, Family]:
    global _cache
    if _cache is None or refresh:
        fams = _load_legacy()
        fams.update(_load_native())
        _cache = fams
    return dict(_cache)


def family(name: str) -> Family:
    slug = slugify(name)
    fams = families()
    if slug not in fams:
        raise FamilyNotInstalled(slug)
    return fams[slug]


def refresh() -> dict[str, Family]:
    return families(refresh=True)
