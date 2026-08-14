from pathlib import Path

from fontpkg._models import Axis, Family, FontFile, family_from_metadata
from fontpkg._registry import families, family, refresh
from fontpkg._resolve import normalize_style, normalize_weight, select_file, slugify
from fontpkg.errors import (
    FamilyNotInstalled,
    FontpkgError,
    StyleNotAvailable,
    WeightNotAvailable,
)

__version__ = "0.2.0"

__all__ = [
    "Axis",
    "Family",
    "FamilyNotInstalled",
    "FontFile",
    "FontpkgError",
    "StyleNotAvailable",
    "WeightNotAvailable",
    "families",
    "family",
    "family_from_metadata",
    "normalize_style",
    "normalize_weight",
    "path",
    "refresh",
    "select_file",
    "slugify",
]


def path(
    name: str,
    weight: int | str = 400,
    style: str = "normal",
    nearest: bool = False,
) -> Path:
    fam = family(name)
    chosen = select_file(fam, normalize_weight(weight), normalize_style(style), nearest)
    return chosen.path
