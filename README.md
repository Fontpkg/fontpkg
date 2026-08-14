# fontpkg

[![CI](https://github.com/Fontpkg/fontpkg/actions/workflows/ci.yml/badge.svg)](https://github.com/Fontpkg/fontpkg/actions/workflows/ci.yml)

Fonts as ordinary Python project dependencies — a [Fontsource](https://fontsource.org)
analog for PyPI. **[Browse the fonts →](https://fontpkg.github.io/fontpkg/)**

## Usage

```bash
uv add fontpkg fontpkg-inter
```

```python
import fontpkg

font_path = fontpkg.path("inter")                    # Path to Inter 400/normal
fontpkg.path("Inter", weight=700, style="italic")    # names are case/space-insensitive
fontpkg.families()                                    # everything installed
```

The font is pinned in your lockfile, downloaded at install time (never at runtime),
and works offline forever.

There is also a small CLI:

```bash
fontpkg list                             # installed families
fontpkg search mono                      # installable families (fetches the catalog)
fontpkg path "Open Sans" --weight bold
```

## Repository layout

- [`core/`](core/) — the `fontpkg` runtime: entry-point discovery, weight/style
  resolution, PIL and matplotlib helpers.
- [`generator/`](generator/) — `fontpkg-gen`, which builds `fontpkg-<family>`
  packages from [google/fonts](https://github.com/google/fonts) (OFL-1.1 and
  Apache-2.0 families only; binaries shipped unmodified with license text).
- [`DESIGN.md`](DESIGN.md) — architecture, licensing rules, roadmap, decisions.

## Development

```bash
just sync    # uv sync --all-packages
just test    # pytest for core + generator
just build roboto inter   # generate + wheel real font packages into build/
```
