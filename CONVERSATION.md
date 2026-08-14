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

**Claude (continued):** Batch-validated all 10 MVP families (Lato static-only, Fira Code no-italic, Playfair min-weight edge cases all behave). Added `fontpkg list` / `fontpkg path` CLI (console script + `python -m fontpkg`) with tests (32 passing total), and GitHub Actions CI (test matrix 3.10/3.12/3.13 + manual generate workflow uploading wheels). PyPI publishing deferred until names are registered.

---

**User:** Asked about usage patterns: do we publish ~1500 Google fonts to PyPI? Are fonts downloaded at first load or venv creation? What system detects new font packages?

**Claude:** Answered and recorded in DESIGN.md §3.3:
- Publishing is phased: 10 MVP families manual → top ~200 by popularity → full ~1,500 allowlist once the pipeline runs unattended (precedent: fontsource's ~1,500 npm packages, typeshed's thousands of types-* packages). Fallback for PyPI pushback: self-hosted PEP 503 index for the long tail.
- Fonts are downloaded at install time only — bytes live in the wheel, cached by uv/pip; import/resolution are fully offline (deliberate inversion of pyfonts' plot-time fetching).
- Update detection: state.json manifest (slug → upstream_commit + published_version); weekly CI diffs upstream commits, rebuilds/publishes deltas, commits manifest; new allowlist families auto-built, disappearing/license-changed families flagged for review. Consumers use normal dependency tooling (uv lock --upgrade, Dependabot). Future `fontpkg search` queries a static catalog index for not-yet-installed fonts.

---

**User:** Asked what they need to do now.

**Claude:** Listed the account-gated steps: (1) push repo to GitHub (gh repo create) and merge feature/fontpkg; (2) register PyPI names — time-sensitive — by publishing fontpkg (and flagship fontpkg-* names) with their credentials, TestPyPI dry run suggested; (3) configure Trusted Publishing for generate.yml; (4) request a PyPI org early; (5) optional courtesy email to Fontsource maintainers. Next build items after that: state.json delta pipeline, publish step in CI, top-200 run.

---

**User:** Asked to merge feature/fontpkg into main.

**Claude:** Merged with --no-ff (merge commit 70625bb, 34 files); test suite re-run on main, 32 passing.

---

**User:** Created the GitHub repo (etjones/fontpkg); asked for a CI badge in the README and to push main.

**Claude:** Added the actions/ci.yml badge to README.md, committed, pushed main (and feature/fontpkg) to origin.

---

**User:** Set up the Fontpkg GitHub organization; asked to transfer etjones/fontpkg to it.

**Claude:** Transferred via the GitHub API (now Fontpkg/fontpkg), updated the local git remote and the README badge/links to the new owner, pushed.

---

**User:** Asked for a good GitHub sidebar topic list.

**Claude:** Applied 16 topics to Fontpkg/fontpkg: fonts, typography, python, pypi, packaging, pip, uv, google-fonts, fontsource, variable-fonts, ttf, opentype, open-fonts, sil-ofl, matplotlib, pillow.

---

**User:** Did a test publish of fontpkg to PyPI, set up trusted publishing for github.com/fontpkg/fontpkg, requested the fontpkg PyPI org. Asked for a better way to contact Fontsource's authors than a GitHub issue. (Project dir renamed to ~/Dropbox/Projects/fontpkg.)

**Claude:** Fontsource org members are ayuhito (Ayu, public email hello@ayuhito.com, ayuhito.com) and jwr1. Recommended a short personal email to Ayu now, plus a GitHub Discussions post (enabled on fontsource/fontsource) as a public announcement once fontpkg is public/published; issue tracker is off-register. Offered to draft the email.

---

**User:** Asked for a draft of the email to Ayu.

**Claude:** Drafted a short heads-up email: leads with credit to Fontsource, describes fontpkg (google/fonts generation, license compliance, runtime API), offers to adjust README credit wording, explicitly no ask, open door to advice/coordination. Advised sending only after the repo is public so the link resolves.

---

**User:** Sent the email to Ayu; repo is public; PyPI test publish + trusted publishing + org request done. Asked Claude to take the next steps.

**Claude:** Built the automation phase:
- `fontpkg-gen sync`: state.json-driven delta detection (per-family upstream commit), rebuilds only changed families, `--families-file` support, wheel-builder hook; GitHub API calls now use GITHUB_TOKEN when set.
- families.txt (the 10 MVP slugs) + seeded state.json via a live sync (all 10 built; second run: all unchanged).
- generate.yml rewritten: weekly cron (Mon 06:17 UTC) + manual dispatch, syncs deltas, uploads wheels, publish step gated on `publish` input or AUTO_PUBLISH repo var, auto-commits state.json.
- release.yml: publishes core fontpkg on v* tags via trusted publishing (tests must pass first).
- 38 tests passing. Remaining user actions: add pending trusted publishers on PyPI for the 10 fontpkg-<slug> names (or first manual token publish), tag v0.1.0 to exercise release.yml, optionally set AUTO_PUBLISH=true.

---

**User:** Put PYPI_TOKEN in .env; asked Claude to publish the first 10 MVP font packages.

**Claude:** Added .env to .gitignore first (it wasn't ignored). Built wheels+sdists for all 10, published with the token via UV_PUBLISH_TOKEN. fontpkg-fira-code and fontpkg-inter landed immediately; PyPI's new-project creation throttle (429) hit on the third, so the remaining 8 are publishing via a background retry loop (idempotent with --check-url, 120s backoff).

---

**User:** Asked about discoverability (fontsource-style search/specimens), requested a CLI query for installable (not just installed) fonts, a README usage update, and further suggestions.

**Claude:** Built the catalog layer:
- catalog.json at repo root: index of installable families (family/slug/package/version/license/category/styles/variable/weights), generated by sync alongside state.json, committed by the weekly workflow; seeded from a fresh sync of the 10 families. build.py now records category+subsets in metadata.json.
- `fontpkg search <query>` in the core CLI: fetches catalog from GitHub raw (--catalog-url / FONTPKG_CATALOG_URL override, local paths supported), matches family/slug/category, marks [installed], prints uv add hints. Only networked CLI command; library API stays offline.
- READMEs updated with normal usage (uv add fontpkg-inter; fontpkg.path("inter")) and CLI examples. 45 tests passing.

---

**User:** Suggested fontpkg-<name> packages depend on fontpkg core, so one `uv add fontpkg-inter` suffices.

**Claude:** Agreed (clean dependency direction, core guarantees schema back-compat) and implemented: generated pyproject now has dependencies = ["fontpkg>=0.1.0"]; added --post N flag to fontpkg-gen build for republishing already-released names as .postN without an upstream bump. 46 tests passing. Republish of the already-published packages queued behind the still-running PyPI throttle retry job.

---

**User:** Asked to start a static specimen site with live-typing demo + filtering; asked whether to serve fonts via fontpkg's own files or Fontsource; open to a separate repo.

**Claude:** Recommended serving fontpkg's own TTFs (the site's promise is "this is exactly what uv add gives you"; browsers render TTF/VF natively; fontsource CDN would demo their subsetted builds) and staying in the same repo. Built:
- `fontpkg-gen site`: generates a static site from catalog.json + built packages — copies font binaries (bracket-free names), emits @font-face rules (truetype-variations with weight ranges for VFs), embeds the catalog as JSON in a vanilla-JS page.
- Page features: live-typing preview (global input + per-card contenteditable), substring family filter, category chips, global weight slider driving VF axes, italic toggle, uv-add copy buttons, lazy font loading via IntersectionObserver (30MB of fonts load only as cards scroll into view), dark/light theme.
- pages.yml: deploys to GitHub Pages on dispatch and after each font sync; enabled Pages (build_type=workflow) via API. 48 tests passing. Verified live in browser: typing, filtering, weight slider all work.

---

**User:** Asked whether 1,500 fonts will break GitHub Pages, and whether to buy fontpkg.org.

**Claude:** Pages math: 1 GB site limit; ~3 MB/family avg → top-200 fits (~600 MB), full 1,500 (~3-4.5 GB) does not. Client side already fine via lazy loading. Recommended buying fontpkg.org now (decouples URLs from hosting; ~$12/yr) and pointing it at Pages; at full scale move font assets to Cloudflare R2 behind fonts.fontpkg.org. Flagged woff2 as OFL format-conversion gray area — deliberate decision later, packages stay unmodified TTF. Recorded as DESIGN.md §9. User actions: buy domain + CNAME to fontpkg.github.io; Claude wires repo side after.

---

**User:** Bought fontpkg.org (Route53 registration in progress); will confirm CNAME later. Said to build assuming the domain works shortly.

**Claude:** fira-code + inter .post1 published (existing projects bypass the new-project throttle) — all live packages now carry the fontpkg dependency; 8 still queued. Pre-wired the domain: canonical/og meta tags + emoji favicon pointing at fontpkg.org in the site template. Added a font-request issue template (license checkbox, google-fonts link) + config linking the specimen site. Added `fontpkg search --category` filter with tests (49 passing). Domain repo-side wiring (Pages custom domain, HTTPS) waits for CNAME confirmation.

---

**User:** Route53 rejected a CNAME at the apex (fontpkg.org) with "RRSet of type CNAME ... not permitted at apex".

**Claude:** Explained CNAMEs are forbidden at zone apex and Route53 ALIAS only targets AWS resources. Prescribed the standard GitHub Pages setup: apex A records to 185.199.108-111.153 (optionally AAAA 2606:50c0:8000-8003::153), and the CNAME on the www subdomain → fontpkg.github.io. Will wire the Pages custom domain + HTTPS + link updates once records are saved.

---

**User:** Asked to expand families.txt toward the top 200 while waiting on DNS.

**Claude:** Generated families.txt from Google Fonts' own metadata endpoint (fonts.google.com/metadata/fonts, no API key): top 200 by popularity rank, excluding CJK-subset families (Noto JP/KR/SC/TC etc. — size, per design), Ubuntu (UFL), and brand fonts (Google Sans slipped the isOpenSource filter; added isBrandFont exclusion). Committed families.txt only; state.json/catalog.json deliberately unchanged so the live site never advertises packages PyPI's throttle hasn't allowed publishing. Full 200-family validation build running in background to scratch; failures will prune the list. Real sync + catalog + site update happen when publishing capacity exists.

---

**User:** Reported SSL_ERROR_BAD_CERT_DOMAIN at www.fontpkg.org (GitHub's *.github.io cert).

**Claude:** Diagnosed as expected mid-setup state: DNS had gone live but the Pages custom domain wasn't set yet, so GitHub served its default cert. Set custom domain fontpkg.org via API; cert issuance (Let's Encrypt) in progress with a background watcher that enables HTTPS enforcement when issued. HTTP already serves the site. Updated README/config links and repo homepage to fontpkg.org; stopped the now-obsolete DNS watcher.
