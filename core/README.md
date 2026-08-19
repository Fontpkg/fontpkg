# fontpkg

Fonts as ordinary Python project dependencies. Inspired by [Fontsource](https://fontsource.org).

**[Browse the fonts at fontpkg.org →](https://fontpkg.org/)**

```bash
uv add fontpkg fontpkg-inter
```

```python
import fontpkg

font_path = fontpkg.path("inter")                 # Path to 400/normal
fontpkg.path("Inter", weight=700, style="italic") # names are case/space-insensitive
fontpkg.path("Inter", weight=650, nearest=True)

fam = fontpkg.family("Inter")    # .weights, .styles, .axes, .is_variable, .license
fontpkg.families()               # everything installed in the environment
```

Find installable families with `fontpkg search <query>` (matches family, slug, or
category; the only CLI command that touches the network) or `fontpkg list` for what
is already installed.

Integrations (extras `fontpkg[pil]`, `fontpkg[matplotlib]`):

```python
from fontpkg.pil import truetype
img_font = truetype("Roboto", size=24, weight=500)   # sets VF weight axis for you

from fontpkg.mpl import use
prop = use("Roboto", set_default=True)
```

Font packages are generated from [google/fonts](https://github.com/google/fonts)
(OFL/Apache-licensed families only) — see the repository root for the generator.
