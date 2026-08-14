# Conversation Log

## 2026-08-14

**User:** Wanted a pip/uv-installable way to express fonts as Python project dependencies (analog of JS's fontsource). Asked to (1) survey existing pythonic options, (2) design a Python fontsource analog if nothing good exists, respecting licensing/copyright.

**Claude:** Surveyed the landscape:
- pimoroni `fonts` + `font-*` packages — closest analog (entry-point-based per-font PyPI packages) but ~10 fonts, dormant, no automation.
- `pyfonts` — runtime Google Fonts download for matplotlib; not a real dependency.
- One-off vendored packages (`ttf-opensans`, `py-open-fonts`, etc.) — ad-hoc.
- Installer CLIs (`googlefonts-installer`) — imperative, OS-level.
- Fontist (Ruby) — best license model but not pip.
- Conclusion: no maintained, comprehensive, license-correct system exists.

Wrote [DESIGN.md](DESIGN.md): three-part architecture —
1. `fontgrab` core runtime (entry-point discovery, `font("Roboto", weight=700)`, PIL/matplotlib helpers),
2. auto-generated `fontpkg-<slug>` packages (unmodified upstream binaries + license text + metadata.json, variable-font-first, version = upstream version),
3. CI generator pipeline over google/fonts METADATA.pb, allowlisting OFL/Apache-2.0/UFL only, trusted publishing, weekly deltas.

Key compliance decisions: ship unmodified binaries (avoids OFL Reserved Font Name obligations), embed full license text per wheel, provenance in metadata.json.

Open decisions: project/package naming (`fontgrab` vs `pyfontsource`), PyPI scale strategy (org account vs self-hosted extra index for long tail).

---

**User:** Asked about consumer use cases (Django, CAD, matplotlib): what does the consuming API look like — an overarching package with `get_path('roboto')` / `installed_fonts()`? How do consumers learn what's available vs. system fonts? How are families/multiple weights handled? Is fontsource's metadata all from Google Fonts, or worth parsing too? Prefers the name `fontpkg`; asked for other naming ideas and thoughts on `fontsource_py` (would need permission, implies API commitment).

**Claude:** Updated [DESIGN.md](DESIGN.md):
- Confirmed the overarching-core model: `fontpkg.path("Roboto", weight=700, style="italic")`, `fontpkg.family()` / `families()`; font packages are dumb data, all logic in core.
- Resolution semantics: slug-normalized names, CSS-numeric weights + aliases, exact-match default with opt-in `nearest=True`, `FamilyNotInstalled` errors that name the `uv add` command.
- Three availability tiers: pip-installed (core's job, reproducible), OS-installed (optional `fontpkg[system]` extra), absent (actionable error). Variable fonts returned as-is; PIL/matplotlib helpers set axes.
- Related families (Roboto Condensed/Slab) = separate packages mirroring upstream boundaries.
- Data sources: google/fonts repo is authoritative (binaries, METADATA.pb, licenses); fontsource's API is mostly normalized Google Fonts data serving subsetted woff2 — use only for discovery of non-Google families and cross-checks, never in the build critical path.
- Naming decision: `fontpkg` (core + `fontpkg-<slug>` prefix). Verified `fontpkg`, `fontdep`, `fontset`, `typeface`, `fontsource-py`, `pyfontsource` all unclaimed on PyPI (2026-08-14). Recommended against `fontsource_py`: trades on their goodwill + implies API tracking; credit them in README instead, optional heads-up email.

---

## 2026-08-14 (later)

**User:** Asked to implement the plan as `fontpkg`, autonomously (gone for a couple hours), noting decisions in DESIGN.md.

**Claude:** Implemented the MVP on branch `feature/fontpkg` (repo git-initialized first):
- `core/` — `fontpkg` runtime: entry-point discovery (`fontpkg.family` group + legacy `fonts_ttf`), `path()/family()/families()`, weight/style normalization with aliases, exact/nearest/VF resolution, actionable errors, `fontpkg.pil` (sets VF weight axis) and `fontpkg.mpl` helpers.
- `generator/` — `fontpkg-gen` CLI: fetches families from google/fonts via the GitHub contents API, parses METADATA.pb with a small textproto parser, enforces OFL-1.1/Apache-2.0 allowlist, emits per-family packages (unmodified binaries + LICENSE + metadata.json + entry point), optionally builds wheels via `uv build`; `--from-dir` for offline builds.
- 28 tests passing (no network; fixture fonts via fontTools FontBuilder; core↔generator schema roundtrip).
- Live e2e verified: built `fontpkg-roboto` (3.015) and `fontpkg-inter` (4.001) wheels, installed into a clean venv, resolved paths/weights/styles, rendered six Inter VF weights via PIL (demo PNG sent).
- Decisions recorded in DESIGN.md §8 (Python ≥3.10, OFL+Apache only for now — UFL deferred, head.fontRevision versioning + PEP 440 leading-zero caveat, static/ subdirs skipped, zip-install limitation, matplotlib VF limitation).
