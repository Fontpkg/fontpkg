# fontpkg

Fonts as ordinary Python project dependencies — a [Fontsource](https://fontsource.org)
analog for PyPI. `uv add fontpkg-roboto` and the font is pinned, offline, and
resolvable at runtime.

```python
import fontpkg

fontpkg.path("Roboto", weight=700, style="italic")   # -> Path to the .ttf
fontpkg.families()                                    # everything installed
```

There is also a small CLI:

```bash
fontpkg list
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
