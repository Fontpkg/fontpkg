from matplotlib import font_manager, rcParams
from matplotlib.font_manager import FontProperties

from fontpkg._registry import family
from fontpkg._resolve import normalize_style, normalize_weight


def use(
    name: str,
    weight: int | str = 400,
    style: str = "normal",
    set_default: bool = False,
) -> FontProperties:
    fam = family(name)
    for f in fam.files:
        font_manager.fontManager.addfont(str(f.path))
    if set_default:
        rcParams["font.family"] = fam.name
    return FontProperties(
        family=fam.name,
        weight=normalize_weight(weight),
        style=normalize_style(style),
    )
