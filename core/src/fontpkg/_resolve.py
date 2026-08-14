import re

from fontpkg._models import Family, FontFile
from fontpkg.errors import StyleNotAvailable, WeightNotAvailable

WEIGHT_ALIASES = {
    "thin": 100,
    "hairline": 100,
    "extralight": 200,
    "ultralight": 200,
    "light": 300,
    "normal": 400,
    "regular": 400,
    "medium": 500,
    "semibold": 600,
    "demibold": 600,
    "bold": 700,
    "extrabold": 800,
    "ultrabold": 800,
    "black": 900,
    "heavy": 900,
}


def slugify(name: str) -> str:
    return re.sub(r"[\s_]+", "-", name.strip().lower())


def normalize_weight(weight: int | str) -> int:
    if isinstance(weight, str):
        key = weight.strip().lower().replace("-", "").replace(" ", "")
        if key not in WEIGHT_ALIASES:
            raise WeightNotAvailable(f"unknown weight name {weight!r}")
        return WEIGHT_ALIASES[key]
    if not 1 <= weight <= 1000:
        raise WeightNotAvailable(f"weight must be in 1-1000, got {weight}")
    return int(weight)


def normalize_style(style: str) -> str:
    s = style.strip().lower()
    if s in ("italic", "oblique"):
        return "italic"
    return "normal"


def select_file(fam: Family, weight: int, style: str, nearest: bool = False) -> FontFile:
    styled = [f for f in fam.files if f.style == style]
    if not styled:
        raise StyleNotAvailable(
            f"style {style!r} is not available for {fam.name!r}; available: {fam.styles}"
        )
    for f in styled:
        if f.variable and f.wght_min is not None and f.wght_max is not None:
            if f.wght_min <= weight <= f.wght_max:
                return f
    exact = [f for f in styled if f.weight == weight]
    if exact:
        return exact[0]
    if nearest:
        static = [f for f in styled if f.weight is not None]
        if static:
            return min(static, key=lambda f: (abs(f.weight - weight), f.weight))
        variable = [f for f in styled if f.variable and f.wght_min is not None]
        if variable:
            return variable[0]
    available = fam.weights or [
        f"{f.wght_min}-{f.wght_max}" for f in styled if f.variable and f.wght_min is not None
    ]
    raise WeightNotAvailable(
        f"weight {weight} is not available for {fam.name!r} ({style}); "
        f"available: {available} (pass nearest=True to pick the closest)"
    )
