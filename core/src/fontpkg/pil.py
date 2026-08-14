from typing import Any

from PIL import ImageFont

from fontpkg._registry import family
from fontpkg._resolve import normalize_style, normalize_weight, select_file


def truetype(
    name: str,
    size: float,
    weight: int | str = 400,
    style: str = "normal",
    nearest: bool = False,
    **kwargs: Any,
) -> ImageFont.FreeTypeFont:
    fam = family(name)
    w = normalize_weight(weight)
    chosen = select_file(fam, w, normalize_style(style), nearest)
    font = ImageFont.truetype(str(chosen.path), size, **kwargs)
    if chosen.variable:
        _set_weight_axis(font, w)
    return font


def _set_weight_axis(font: ImageFont.FreeTypeFont, weight: int) -> None:
    axes = font.get_variation_axes()
    values: list[float] = []
    for axis in axes:
        name = axis["name"]
        if isinstance(name, bytes):
            name = name.decode("ascii", "replace")
        if name.strip().lower() in ("weight", "wght"):
            values.append(float(weight))
        else:
            values.append(float(axis["default"]))
    font.set_variation_by_axes(values)
