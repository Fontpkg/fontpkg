# fontpkg — Design: a Python fontsource analog

Make fonts expressible as ordinary Python project dependencies (`uv add`, `pip install`),
with correct licensing, discoverable at runtime, and maintained by an automated pipeline —
what [Fontsource](https://fontsource.org) does for npm, for PyPI.

## 1. Prior art (survey, Aug 2026)

| Option | Approach | Status / gap |
|---|---|---|
| [`fonts`](https://pypi.org/project/fonts/) + `font-*` (pimoroni) | Per-font PyPI packages exposing TTFs via `fonts_ttf` entry points; `from fonts.ttf import AmaticSC` | Closest analog. Only ~10 hand-made fonts, effectively dormant, no pipeline, no weight/style model |
| [`pyfonts`](https://github.com/y-sunflower/pyfonts) | Runtime download from Google Fonts / Bunny Fonts, registers with matplotlib | Not a dependency: needs network at plot time, matplotlib-only, nothing pinned in `pyproject.toml` |
| One-off font packages (`ttf-opensans`, `py-open-fonts`, `fontawesome_freefile`, `font-source-sans-pro`) | Vendored font files as package data | Ad-hoc, inconsistent APIs, single fonts, mostly unmaintained |
| Installer CLIs (`googlefonts-installer`, `font-installer`) | Download + install into OS font dirs | Imperative side effects, not per-project, not declarative |
| [Fontist](https://www.fontist.org) (Ruby) | YAML manifest + community formulas, 3000+ fonts, license gating | Best licensing model, but Ruby CLI — not pip-resolvable, not importable |
| DIY vendoring | Ship TTF as package data, `importlib.resources` | The de-facto standard; every project reinvents it and often ignores license obligations |

**Gap:** nothing combines (a) pip/uv-resolvable dependencies, (b) broad coverage with automation, (c) a uniform runtime API, (d) license compliance. That's the project.

## 2. Goals / non-goals

Goals
- `uv add fontpkg-roboto` → font available, pinned, offline, reproducible.
- Uniform lookup: family → file path(s) by weight/style, framework helpers (PIL, matplotlib).
- Every package legally redistributable, with license text shipped and copyright/RFN respected.
- Fully automated generation from upstream (Google Fonts repo) — no hand-curation at scale.

Non-goals
- Installing fonts into the OS (that's Fontist's job; we stay inside site-packages).
- Web formats (woff2 subsets, CSS) — fontsource covers the web; Python consumers want TTF/OTF. (A `[web]` extra with woff2 for Django/static-site use is a possible v2 item, not core.)
- Proprietary fonts (Arial etc.) — never redistributable; out of scope.

## 3. Architecture

Three parts, mirroring fontsource:

### 3.1 Core runtime package: `fontpkg`
Small, zero-dependency (stdlib `importlib.metadata` / `importlib.resources`). Font packages
are dumb data; all resolution logic lives here, so fixes ship without republishing 1,500
font packages.

```python
import fontpkg

fontpkg.path("Roboto")                          # Path to 400/normal (or the variable font)
fontpkg.path("Roboto", weight=700, style="italic")
fontpkg.path("Roboto", weight=650, nearest=True)  # opt-in nearest-match; exact-or-raise default

fam = fontpkg.family("Roboto")                  # Family: .weights, .styles, .axes,
                                                #   .is_variable, .files, .license, .version
fontpkg.families()                              # {slug: Family} for everything pip-installed
```

Resolution semantics:
- Family lookup is by slug (case/space-insensitive: `"Open Sans"` == `"open-sans"`).
- Weights are CSS-numeric (100–900) with named aliases (`"bold"` → 700).
- Exact match by default; missing family raises
  `FamilyNotInstalled("open-sans — add it with: uv add fontpkg-open-sans")` — the error
  message is the install instruction.
- If the family ships a variable font, `path()` returns the VF file for any weight in its
  axis range; the *renderer* sets the axis. Integration helpers do this correctly:

```python
# extras: fontpkg[pil], fontpkg[matplotlib]
from fontpkg.pil import truetype
f = truetype("Roboto", size=24, weight=500)     # handles set_variation_by_axes for VFs

from fontpkg.mpl import use
prop = use("Roboto")                            # registers files with font_manager,
                                                # returns FontProperties
```

Discovery via an entry-point group, so the core needs no registry of its own:

```toml
[project.entry-points."fontpkg.family"]
roboto = "fontpkg_roboto"
```

Core loads entry points, reads each package's `metadata.json`, resolves files with
`importlib.resources.files()` (zip-safe). Also reads pimoroni's `fonts_ttf` group for
backward compatibility.

**Installed vs. system fonts.** Three availability tiers, kept deliberately distinct:
1. **pip-installed** (`fontpkg.families()`) — enumerable, versioned, reproducible. Core
   answers only this; that's the point of the project.
2. **OS-installed** — queryable but machine-dependent. Optional `fontpkg[system]` extra
   (wrapping fontconfig / DirectWrite / CoreText enumeration, e.g. via
   `find-system-fonts-filename`) provides `fontpkg.system.families()` and
   `fontpkg.resolve(name, allow_system=True)` for apps that want graceful fallback.
3. **Absent** — the exception message tells the user which package to add.

### 3.2 Font packages: `fontpkg-<slug>`
One PyPI package per family (`fontpkg-roboto`, `fontpkg-source-sans-3`, …), containing:

```
fontpkg_roboto/
  __init__.py          # FAMILY, PATH constants only
  metadata.json        # family, version, license id, weights, styles, axes, upstream commit
  files/*.ttf          # unmodified upstream binaries
  LICENSE              # verbatim OFL/Apache/UFL text with original copyright notice
```

- **Variable font preferred** when upstream ships one (one small file, all weights);
  static instances behind an extra: `fontpkg-roboto[static]` — needed for renderers
  without VF axis support.
- **Related families are separate packages** (`fontpkg-roboto-condensed`,
  `fontpkg-roboto-slab`), mirroring upstream's family boundaries. No superfamily
  metapackages in v1.
- **Never modify the binaries.** No subsetting/instancing in v1 — OFL Reserved Font Names
  make modified fonts a renaming obligation (the compliance trap fontsource engineered
  around; shipping upstream bytes verbatim sidesteps it entirely).
- Package version = upstream font version, PEP 440-mapped, with `.postN` for packaging fixes.
- Wheel metadata: `License-Expression: OFL-1.1` (or Apache-2.0 / Ubuntu font licence),
  `Classifier: Topic :: Text Processing :: Fonts`.

### 3.3 Generator pipeline (the actual product)
A repo (this one) with CI that:

1. Clones/updates [google/fonts](https://github.com/google/fonts) (~1,800 families).
2. Parses each family's `METADATA.pb` → allowlist by license: **OFL, Apache-2.0, UFL only**.
3. Emits a `pyproject.toml` + package tree per family from a template; copies binaries,
   license, provenance (upstream commit hash) into `metadata.json`.
4. Builds wheels; publishes changed/new families via PyPI Trusted Publishing.
5. Runs on a schedule (weekly) — diff against last published upstream commit, so steady
   state publishes only deltas.

**Data sources.** Primary is the google/fonts repo directly: it is the authoritative
origin for binaries, `METADATA.pb`, axis definitions, and license files — provenance we
can cite. Fontsource's own catalog is mostly Google Fonts plus a small "other" set
(League of Moveable Type, icon sets, direct submissions), normalized into a convenient
JSON API (api.fontsource.org) but serving subsetted woff2 — the wrong artifacts for us,
with second-hand license provenance. Use the fontsource API only as (a) a discovery list
for worthwhile non-Google families, (b) a cross-check on metadata normalization — never
in the build pipeline's critical path. Later sources (Bunny, Fontshare,
league-of-moveable-type) plug in as additional adapters.

## 4. Licensing & compliance rules (hard requirements)

- Redistribute only OFL-1.1, Apache-2.0, UFL-1.0 families (same allowlist logic as Fontist/Google Fonts).
- Ship the full license text + original copyright line inside every wheel (OFL §condition 2 requires the license accompany the fonts).
- OFL "no selling fonts by themselves" clause: satisfied — packages are free; PyPI hosting is fine (same position fontsource/npm take).
- Preserve all name-table records by shipping unmodified files; never claim RFNs.
- `metadata.json` records upstream source URL + commit for provenance/takedown handling.

## 5. Naming

**Decision: `fontpkg`** — core package `fontpkg`, families `fontpkg-<slug>`, entry-point
group `fontpkg.family`. Short, self-describing, and the core name doubles as the family
prefix. Verified unclaimed on PyPI 2026-08-14 (as were `fontdep`, `fontset`, `typeface`,
`fontsource-py`, `pyfontsource`). Register `fontpkg` + a few flagship `fontpkg-*` names
early to prevent squatting.

On `fontsource_py`: credit Fontsource prominently as inspiration (factual credit needs no
permission), but don't take the name — it trades on their goodwill, implies API
compatibility we don't intend, and creates an ongoing obligation to track their design.
Precedent: fontsource itself is a renamed continuation of the earlier `typefaces` npm
project; independent names for ecosystem ports are the norm. Optionally email the
Fontsource maintainers a heads-up — good citizenship, possible future collaboration.

## 6. Risks / open questions

- **PyPI at scale:** ~1,500+ packages and font-sized wheels will need a PyPI org account,
  possibly per-project size-limit requests (default 100 MB/file is fine for almost all;
  Noto CJK will need care or exclusion in v1). Mitigation if PyPI objects to the flood:
  publish the long tail on a self-hosted PEP 503 simple index (`--extra-index-url`),
  keep the top ~200 families on PyPI proper.
- **Icon fonts** (Font Awesome Free, Material Symbols): same machinery works; separate
  adapter, v2.
- **Web consumers** (Django static assets): a `fontpkg.django` staticfiles finder +
  `@font-face` generation would want woff2 — candidate `[web]` extra, v2. Server-side
  renderers (PIL, matplotlib, ReportLab, WeasyPrint, CAD) are the v1 sweet spot; all
  consume TTF/OTF paths directly.

## 7. Roadmap

1. **MVP:** `fontpkg` core + generator producing ~10 popular OFL families
   (Roboto, Inter, Open Sans, Lato, Source Sans 3, JetBrains Mono, Fira Code, Noto Sans,
   Merriweather, Playfair Display); PIL + matplotlib helpers; publish to TestPyPI.
2. **Automation:** scheduled CI over full google/fonts allowlist, trusted publishing, deltas.
3. **Ecosystem:** docs site with searchable family index (fontsource-style), `fontpkg search`
   CLI, bunny/fontshare adapters, static-instance extras, `[system]` fallback module.
