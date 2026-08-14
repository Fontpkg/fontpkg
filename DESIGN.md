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

**Update detection.** A `state.json` manifest in this repo maps `slug →
{upstream_commit, published_version}`. The weekly run diffs each family's latest
upstream commit against the manifest (via the GitHub compare/commits API), rebuilds and
publishes only the deltas, then commits the updated manifest. Families newly entering
the allowlist are "in upstream, not in state" → built; families that disappear or
change license are flagged for human review, never auto-yanked. Consumers need no
mechanism of their own: font updates arrive through normal dependency tooling
(`uv lock --upgrade`, Dependabot/Renovate) as reviewable version bumps.

**Publishing phases.** (1) MVP 10 families, manual; (2) top ~200 by popularity;
(3) full allowlist once the pipeline has run unattended reliably. Fonts download at
*install* time only — the bytes are in the wheel, cached by uv/pip; import and
resolution are offline.

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

## 8. Implementation decisions (2026-08-14, initial build)

Recorded while implementing the MVP; deviations from or refinements of the sections above.

- **Layout:** uv workspace monorepo — `core/` (the `fontpkg` runtime) + `generator/`
  (`fontpkg-gen` CLI). `just sync / test / build <families>`.
- **Python ≥3.10** (not 3.9): `importlib.metadata.entry_points(group=...)` and modern
  union hints; 3.9 is EOL anyway.
- **metadata.json schema v1:** `{schema, family, slug, version, license, copyright, axes:
  [{tag,min,max}], files: [{path, style, weight|null, variable}], source: {repo, path,
  commit}}`. Variable files carry `weight: null`; their wght range comes from the
  family-level `wght` axis.
- **Licenses in v1: OFL-1.1 and Apache-2.0 only.** UFL dropped for now — its SPDX id is
  unclear and PEP 639 backends validate license expressions, so Ubuntu's family is
  excluded until resolved (only affects a handful of families).
- **Fetching:** GitHub contents API (no multi-GB clone), unauthenticated with UA header,
  top-level `.ttf/.otf` + license + `METADATA.pb` only; `static/` subdirs skipped
  (`[static]` extras deferred). Provenance commit from the commits API. Unauthenticated
  rate limit is 60 req/hr — fine for a handful of families; CI at scale needs a token.
- **Versioning:** `head.fontRevision` formatted `%.3f` → package version; PEP 440
  normalizes leading zeros (Roboto `3.015` becomes wheel version `3.15`) while
  `metadata.json` preserves the exact font version. Theoretical collision (3.015 vs 3.15)
  accepted for MVP; revisit with a post-release scheme if it ever bites.
- **Resolution details:** nearest-match tie-break prefers the lighter weight; VF wins over
  static when both cover the requested weight; `nearest=True` clamps into a VF's range
  when the weight falls outside it.
- **Legacy compat:** pimoroni's `fonts_ttf` entry points are read best-effort (path-valued
  entries become single-file 400/normal families); native `fontpkg.family` entries win on
  slug collision.
- **Zip-installed wheels not supported:** `path()` materializes `Path(str(traversable))`;
  real-world installs are unpacked. Documented limitation rather than an `as_file`
  ExitStack held for the process lifetime.
- **matplotlib helper** registers all family files and returns `FontProperties`;
  matplotlib cannot set VF axes, so non-400 weights of VF-only families need the future
  `[static]` extra there (PIL helper handles VF axes properly).
- **`fontpkg.system` deferred** to v2 (design §3.1 tier 2).
- **CLI added to core:** `fontpkg list` / `fontpkg path <family> [--weight] [--style]
  [--nearest]` (console script + `python -m fontpkg`). Roadmap's `fontpkg search`
  (querying the not-yet-installed catalog) remains future work.
- **Batch validation:** all 10 MVP families generated and verified in a clean venv
  (Roboto, Inter, Open Sans, Lato, Source Sans 3, JetBrains Mono, Fira Code, Noto Sans,
  Merriweather, Playfair Display). Lato exercises the static-only path (18 files);
  Fira Code (no italic) and Playfair Display (min weight 400) exercise the error paths.
- **CI:** GitHub Actions test matrix (3.10/3.12/3.13) + a manual `workflow_dispatch`
  generate workflow that uploads wheels as artifacts. PyPI trusted publishing deferred
  until the names are registered.
- **Delta pipeline implemented (Phase 2):** `fontpkg-gen sync` + `state.json` (keyed by
  google/fonts dirname → `{path, commit, version, package}`) + `families.txt` as the
  tracked-family list. Weekly scheduled workflow (`generate.yml`, Mondays 06:17 UTC)
  syncs deltas, uploads wheels, optionally publishes, and commits the updated manifest.
  GitHub API calls are authenticated via `GITHUB_TOKEN` when present (5,000 req/hr vs 60).
- **Publishing wiring:** `release.yml` publishes core `fontpkg` on `v*` tags via trusted
  publishing. Family-package publishing in `generate.yml` is gated behind a
  `workflow_dispatch` `publish` input (or repo variable `AUTO_PUBLISH=true` for scheduled
  runs) because **each new `fontpkg-<slug>` name needs a pending trusted publisher added
  on PyPI first** — PyPI has no bulk API for this, so the MVP names are a one-time manual
  step (or a first local `uv publish` with a token per package).
- **Discoverability (Phase 3 started):** `catalog.json` at the repo root is the
  machine-readable index of installable families (family, slug, package, version,
  license, category, styles, variable/weights), updated by the same sync that builds
  packages and committed by CI alongside `state.json`. The core CLI's `fontpkg search
  <query>` fetches it from GitHub raw (override with `--catalog-url` or
  `FONTPKG_CATALOG_URL`; accepts a local path) and marks installed families — the only
  CLI command that touches the network; the library API stays offline. The catalog is
  the intended data source for a future docs site with rendered specimens.
- **Tests:** no network anywhere; fixture fonts are built in-memory with fontTools
  `FontBuilder`; generator↔core schema compatibility is covered by a roundtrip test.
  Live verification (fetch → build → wheel → clean-venv install → resolve → PIL render)
  was run manually for Roboto + Inter and passed.
