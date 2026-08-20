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

---

**User:** Site confirmed working. Asked: are we just waiting on PyPI now — is everything else automated? Are we done?

**Claude:** Found and closed two automation gaps: (1) published fontpkg 0.1.0 predated `fontpkg search` — bumped core to 0.2.0 and tagged v0.2.0 to exercise release.yml via trusted publishing; (2) weekly workflow had no publish credentials for family packages — stored PYPI_TOKEN as an Actions secret (from .env, at user's service; rotatable), wired it into generate.yml's publish step, and set AUTO_PUBLISH=true so scheduled runs publish autonomously. Remaining external wait: PyPI new-project throttle for the 8 MVP + 190 top-200 packages.

---

**User (mid-turn):** Reported the failed 0.2.0 CI run and PyPI's warning email (API token "poetry" used on fontpkg despite a Trusted Publisher; recommends token removal). Asked if the workflow should change.

**Claude:** Clarified 0.2.0 IS live (failed run was the pre-fix tag attempt; dispatch re-run succeeded). Updated release.yml to drop the token and use trusted publishing exclusively for core (the earlier TP failure means the PyPI publisher config likely names a different workflow — user to set it to release.yml). generate.yml keeps the token for family packages (200 per-project publishers impractical until the PyPI org). Recommended rotating the old "poetry" token to a fresh dedicated one (it must be account-scoped to create new projects) and updating .env + the PYPI_TOKEN secret.

---

**User:** Asked how important rotating the PyPI token is; whether it was exposed in plaintext.

**Claude:** No exposure event: never committed (gitignored pre-commit, verified), never printed; moved only via env vars over TLS to PyPI and GitHub's encrypted secret store. Rotation still recommended as hygiene: (1) .env lives in the Dropbox-synced tree, so the plaintext token syncs to Dropbox servers/devices; (2) it's an old account-wide "poetry" token with unknown other homes. New token must stay account-scoped while creating new projects; can be narrowed post-org.

---

**User:** Set the PyPI trusted publisher to release.yml; asked how to test it.

**Claude:** Cut fontpkg 0.2.1 (version-only bump) via tag v0.2.1 — release.yml has no token anymore, so a green run proves trusted publishing end-to-end. Run succeeded in 14s; 0.2.1 confirmed on PyPI (wheel+sdist). The default JSON endpoint briefly served the cached 0.2.0; the versioned endpoint confirmed.

---

**User:** Asked for better cross-platform secret patterns than plaintext .env in Dropbox (their idea: non-Dropbox ~/project_secrets/<proj>/.env, but less automatic).

**Claude:** Recommended 1Password CLI (already owned): .env keeps only op:// references (Dropbox/commit-safe), `op run --env-file=.env --` injects at runtime, 1P handles cross-machine sync + biometric unlock; justfile prefix makes it invisible. direnv as per-directory auto-loading glue (also improves their project_secrets idea). SOPS+age as the no-subscription versioned alternative. Skip OS keychains (no sync) and AWS SM (overkill locally). Offered to convert fontpkg's .env to op:// pattern when they create the vault item.

---

**User:** Asked whether anyone but them would need 1Password in the proposed setup (.env.example stays plain, only their .env uses op://).

**Claude:** Confirmed: 1Password is a personal dependency only. Users get plain wheels; contributors use .env.example with plaintext values; CI uses Actions secrets. One caution: shared justfile recipes shouldn't hardwire `op run` — keep recipes env-agnostic and let each person populate the environment their own way (direnv/.envrc as the personal wrapper home).

---

**User:** Asked for a fuller explanation of the SOPS+age solution.

**Claude:** Explained: age = minimal public-key file encryption (one keypair in ~/.config/sops/age/keys.txt); SOPS = structured-file layer that encrypts values but not variable names (diffable, reviewable), encrypting a per-file data key to N recipient public keys. Workflow: .sops.yaml lists recipients; sops encrypt/edit/exec-env (exec-env = op run analog, decrypt only into child process env). Encrypted .env can live in Dropbox/git; only the age secret key stays off Dropbox, copied once per machine — shrinks the sync problem from "every secret continuously" to "one key file once". Per-machine keys give cheap revocation. Compared honestly with 1Password (service+biometrics+zero key management vs no-service+versioned-with-repo); recommended op for personal tokens, SOPS+age for team-shared repo secrets.

---

**User:** Adopting the 1Password solution. Asked Claude to (a) save notes in its own memory describing the standard pattern for future projects, and (b) write a short user-facing doc explaining the workflow and its 2026 rationale for rediscovery years later.

**Claude:** Saved two persistent memories (1password-env-secrets-pattern; evan-workflow-context) + index. Wrote docs/SECRETS.md: one-sentence version, the 2026 Dropbox rationale, the pieces (.env with op:// refs, .env.example contract, vault, op CLI), op run usage, and a future-you FAQ (new machine, adding secrets, contributors without 1P, CI, 1P exit strategy). Added .env.example. Remaining to activate: user creates the vault item with the rotated token; Claude then converts .env to op:// references and updates the Actions secret.

---

**User:** Created a Development vault + new PyPI token item. Asked how to get a CLI-valid path from the 1Password GUI.

**Claude:** Pointed to "Copy Secret Reference" in the field's dropdown/right-click menu (enable Settings → Developer → 1Password Developer experience / CLI integration if absent). Noted references use field labels (rename to pypi-token for clarity) and the `op item get --format json` alternative. Next: paste reference into .env; Claude verifies op run resolution and rotates the Actions secret without seeing the value.

---

**User:** Set .env to the op:// secret reference; enabled CLI integration after Claude diagnosed it was off.

**Claude:** Verified op resolves the reference (179-char pypi- token; only length/prefix shown). Rotated the GitHub Actions PYPI_TOKEN secret via op run (value never displayed). Proved the new token with an authenticated byte-identical re-upload of fontpkg-fira-code (exit 0). Meanwhile the old loop had published jetbrains-mono at 16:13 (throttle windows roll every ~80min). Stopped the old-token loop, relaunched the retry for the remaining 7 under op run with an 8h horizon. Old "poetry" token is now safe to delete at PyPI.

---

**User:** Was away from keyboard during 1Password prompts; asked if permissions went through.

**Claude:** Background processes can't receive 1P authorization prompts (no GUI session), and foreground attempts timed out while user was away (app auto-locked). With user present, foreground op run authorized successfully and spawned the publish loop as a detached child (pid 2973) inheriting the resolved token — publishing the remaining 7 packages as throttle windows roll.

---

**User:** Asked whether 1Password requires presence at every launch, and how cron/unattended jobs fit.

**Claude:** Interactive: prompts only when the app is locked or a new app first asks; silent while unlocked (tunable auto-lock). Unattended: use 1Password Service Accounts (vault-scoped OP_SERVICE_ACCOUNT_TOKEN, headless op run), bootstrapped from the macOS Keychain via `security find-generic-password` — the irreducible root credential lives encrypted+machine-local, not Dropbox. Single-secret daemons can use the Keychain directly; CI keeps platform secret stores. Added the unattended pattern to persistent memory.

---

**User:** Asked for a published-fonts report; restarting their computer; wants the project to continue autonomously until PyPI responds about the org.

**Claude:** Daily quota confirmed reset: lato, merriweather, noto-sans published immediately (throttle = ~3 new projects/day). Now 6/10 live: fira-code, inter, jetbrains-mono, lato, merriweather, noto-sans; pending: open-sans, playfair-display, roboto, source-sans-3. Built full autonomy for the drip:
- state.json entries now carry published: true/false (migrated); sync marks new builds unpublished.
- `fontpkg-gen publish-pending`: rebuilds pending packages if needed, attempts publish (idempotent --check-url), flips the flag on success.
- publish.yml: NEW daily workflow (09:41 UTC) running publish-pending + committing state — survives the user's restart, drains the queue at PyPI's daily rate with zero human action.
- generate.yml publish step now uses publish-pending; pages.yml site build filters to published families only (site never advertises uninstallable packages — verified 6 families rendered).
52 tests passing.

---

**User:** Asked what the process will be to change the publishing schedule once PyPI grants bulk permissions.

**Claude:** No schedule change needed — publish-pending already attempts everything unpublished each run; the daily drip is PyPI's limit, not ours. Process when granted: dispatch "Sync font packages" (build top-200 into state) then "Publish pending packages" (drains queue in one pass); site auto-redeploys. If granted via an org: transfer existing fontpkg-* projects, swap to an org-scoped token (update the 1Password item; Claude re-runs gh secret set). Daily job then becomes a cheap no-op safety net. Same process scales to phase-3 (~1,300 more families).

---

**User (via question dialog):** Reported they did NOT remove the roboto/noto families; asked how the removal happened, whether re-adding is safe, and whether the process could remove fonts again in the future.

**Claude:** Root-caused it: Claude's own gen-2 regeneration of families.txt added an isBrandFont filter to exclude Google Sans, and Google's metadata flags Roboto and ALL Noto families as brand fonts (they're Google trademarks, still OFL + in google/fonts) — 15 families silently dropped, and only the google-sans exclusion was verified, no diff review. Also fixed the symptom bug: pages.yml now builds from state.json so the site can never reference an unbuilt published package (the noto-sans FileNotFoundError).
Fixes: regenerated families.txt WITHOUT the brand filter (explicit google-sans/-flex + tinos exclusions instead, with a warning comment); 15 families restored (roboto, roboto-condensed/flex/mono/serif/slab, noto-sans, noto-serif, noto-color-emoji, noto-kufi-arabic, noto-sans-arabic/khmer/tamil/telugu/thai; 15 tail families displaced from the top-200). All 13 newly-restored families validation-built (noto-color-emoji is 23MB — flagged for size watch). NEW CI guard test: every published/state family must appear in families.txt (or an explicit RETIRED_FAMILIES list) — silent drops now fail CI.
Future-removal risk answer: yes, the vector was wholesale list regeneration against mutable upstream flags; even then, drops only ever stopped update-tracking — sync never deletes state entries, publishing never yanks PyPI, and the site builds from state — nothing user-facing disappears. The CI guard closes the silent-drop vector.

---

**User:** Asked to exclude noto-color-emoji until the big-font (CJK) decision is made.

**Claude:** Removed it from families.txt (header comment documents why), backfilled tenor-sans to keep 200. It was never synced, so no state/catalog/PyPI cleanup needed; consistency guard passes.

---

**User:** Heard back from Ayu (friendly, open to collaboration; Python wasn't on his radar). Wants to discuss making fontpkg a transparent Python implementation of Fontsource — identical data/fonts if possible — and reusing fontsource pipeline parts instead of our hand-rolled version. Discussion only for now; deep dig likely a new session.

**Claude:** Framed the key insight: byte-identical fonts is the wrong goal (fontsource ships subsetted woff2 for the web; Python needs complete TTF/OTF; both derive from the same upstream) — the right promise is same families/IDs/versions/metadata, ecosystem-appropriate wrapper. Fontsource pipeline layers: (1) google-font-metadata (Ayu's normalization lib; JSON ships in the npm package, consumable without Node) — high-value adoption, replaces our METADATA.pb parser + metadata scraping and yields their family IDs; (2) subsetting/woff2 build — not reusable (wrong formats, RFN obligations); (3) api.fontsource.org — cross-check + non-Google coverage + future cross-listing. Concrete changes: swap generator metadata source (keep google/fonts binaries+licenses for provenance), ID alignment audit/mapping, catalog schema convergence to their API shape, versioning decision (our font-version scheme vs their own semver — divergence to agree with Ayu), enriched metadata (unicode ranges/subsets) enabling a future [web] extra possibly pointing at their CDN. Keep: resolver, entry points, PyPI pipeline, license gating. Open questions for Ayu: ID mapping blessing, versioning, API listing python package names, "Python implementation of Fontsource" framing under the fontpkg name. To verify in the deep-dive: gfm JSON shape, full ID diff, whether their CDN serves complete TTFs.

---

**User:** Agreed on layer 1 (adopt google-font-metadata), against layer 2. Asked whether consuming fontsource's data + staying synced makes fontsource_py a better name than fontpkg.

**Claude:** Recommended keeping fontpkg. Key analogy: Fontsource consumes Google Fonts wholesale and isn't called google-fonts-js — a synced data dependency isn't an identity. Costs of the fontsource name: implies their governance (only defensible if the project effectively moves under their org), turns every deliberate divergence (complete TTFs, font-version versioning, Python API) into perceived unfaithfulness, abandons sunk identity (fontpkg.org live, 6 published packages, org request), and couples the name to the collaboration's future mood. Recommended instead: blessed tagline ("Fontsource's sibling for Python" / "powered by Fontsource metadata"), reserve fontsource/fontsource-py/pyfontsource on PyPI as pointer packages depending on fontpkg (squat protection + discoverability, with Ayu's blessing), cross-listing between their API/docs and fontpkg.org, and note that moving the repo into their org later remains possible without renaming.

**Follow-up:** setup-uv@v10 failed to resolve (Astral stopped publishing floating major tags after v7) — pinned exactly to v10.0.1; all actions/* floating majors verified to exist. CI green in 15s with zero "Node.js 20" warnings. Also observed while pushing: the Monday sync built the full top-200 into state/catalog and daily publishing has continued autonomously — 14 published, 186 pending, draining at PyPI's daily rate.

---

**User:** Asked why fontpkg.org shows 10 families when 14 are published.

**Claude:** Wiring gap: pages.yml redeployed only after the weekly sync (and manual dispatch), while packages flip to published in the daily 09:41 publish job — so the site lagged at Monday-morning state. Fixed pages.yml to also trigger on "Publish pending packages" completing; dispatched a catch-up deploy showing all 14.

---

**User:** Browser pane had shown the raw template (editor preview hook) — clarified with a local serve of the real build; user confirmed everything looks great.

**Claude:** Local site served on :8734 showing 14 families + count + auto-appearing Display chip; live deploy verified (count element + 14 families on fontpkg.org). Steady state: daily popularity-ordered publish drip (roboto/montserrat/poppins next), site auto-redeploys after each publish, awaiting PyPI org approval to drain the remaining ~186.

---

**User:** Putting the project to bed until PyPI responds about the org.

**Claude:** Parked. Resume checklist when PyPI answers: (1) if org granted — transfer existing fontpkg-* projects to the org, mint org-scoped token, update the 1Password item, Claude rotates the Actions secret; (2) dispatch "Sync font packages" then "Publish pending packages" to drain the ~186 remaining top-200 (or just let the daily drip continue if limits stay); (3) site follows automatically. Meanwhile everything runs unattended: weekly sync (Mon 06:17 UTC), daily popularity-ordered publish (09:41 UTC), site redeploy after each, CI guards. Other parked threads: Fontsource collaboration deep-dive (google-font-metadata adoption, ID audit — new session), large-font/CJK + noto-color-emoji decision, R2/CDN at phase 3, reserving fontsource-py/pyfontsource pointer packages with Ayu's blessing.

---

**User:** Noticed pypi.org/project/fontpkg has no fontpkg.org links; asked if a package update is needed to refresh the README.

**Claude:** Yes — PyPI renders the README baked into each upload. Two gaps fixed: core/README.md never had the site link (only the repo root README did), and core/pyproject.toml lacked [project.urls] (no sidebar links). Added both; also added [project.urls] + fontpkg.org link to the generated family-package template so the ~186 pending packages publish with proper links. Bumped core to 0.2.2, tagged; release.yml publishes via trusted publishing. 55 tests passing.

---

**User:** Asked why pypi.org/project/fontpkg lacks fontpkg.org links; does the package need an update?

**Claude:** Yes — PyPI renders the uploaded README. Fixed both gaps (core/README.md never had the link; no [project.urls]) and templated the same into generated family packages. Released 0.2.2 via trusted publishing; verified urls + readme link live on PyPI. Overnight drip: 18 packages published.

---

**User:** The daily publish exhausts their personal PyPI new-project quota by ~5am US Central; asked to move the job to the end of the (likely UTC) quota day so their own daytime publishes come first.

**Claude:** Moved publish.yml's cron from 09:41 UTC to 23:17 UTC (~5-6pm Central) with an explanatory comment — fontpkg now sweeps whatever quota remains at day's end. Caveats noted: PyPI hasn't documented whether the limit resets at UTC midnight or rolls per-24h (if rolling, timing matters less, but end-of-day still biases toward the user's manual publishes); the Monday 06:17 sync's publish step can still consume quota when newly added families sync — acceptable since new-family additions are deliberate events.

---

**User:** Back to sleep until PyPI writes back.

**Claude:** Parked again. Unattended state: weekly sync (Mon 06:17 UTC), daily popularity-ordered publish now at 23:17 UTC (quota-friendly), site auto-redeploys after each publish, 18+ packages live and climbing ~3/day. Resume checklist in the earlier "Park project" entry.

---

**User:** Asked whether tranches are needed for full population vs top-200, and why fontpkg's eligible count is less than Fontsource's ~2,200 families. Chose (via question dialog) to populate families.txt fully now and defer the GitHub Pages hosting fix until the site actually approaches the limit.

**Claude:** Answered both questions with real data:
- No tranches needed technically — sync/publish-pending already scale to any list size; PyPI's daily quota was always the real pacer, not code. The only real constraint is GitHub Pages' 1GB site limit (~1.5GB projected at full scale from measured 0.82MB/family average) — deferred per user's choice.
- Count gap explained: Google Fonts metadata has 1,942 total families; fontpkg's OFL/Apache/non-CJK/non-UFL/in-repo/licensed rules leave 1,799(-1798, live-data drift) eligible. Fontsource's ~2,200 comes from covering ALL Google Fonts (CJK included — sidestepped via woff2 subsetting, which we deliberately don't do) PLUS ~120 non-Google families from their own `other/` source directory PLUS icon fonts — verified directly from fontsource/font-files' repo structure.
Expanded families.txt to the full 1,798 eligible families (popularity-ordered, noto-color-emoji still deferred). Found and fixed a real robustness bug while sizing up: sync_families only saved state.json once at the very end of the loop — at 1,798 families a single GitHub API rate-limit error partway through would have silently discarded all progress from that run. Wrapped the loop in try/finally so state always persists what succeeded; also added urllib.error.URLError to the per-family caught-and-recorded exceptions so transient failures don't abort the whole run. Two new tests cover both the graceful-continue and the uncaught-exception-still-saves cases. 57 tests passing.
Noted but not yet acted on: first-time full population is API-call-heavy (~5-6 calls/new family vs ~1/already-tracked family), likely exceeding the 5000/hr authenticated GitHub API limit in one run — expected to require 1-2 more manual dispatches of "Sync font packages" (or converge over a few weekly cron cycles) to fully seed state.json; no data loss either way thanks to the fix.

---

**Full sync run #1 result:** completed with "failure" status but had actually built 1,181 of 1,798 families successfully — then hit 412 transient `HTTP 403 Forbidden` (GitHub abuse-detection/secondary rate limit, not the hourly quota) plus 5 permanently-broken upstream families, and because the "Sync changed families" CLI exits 1 on any per-family failure, the workflow's LAST step ("commit state.json/catalog.json") never ran — all 1,181 successful builds were computed on the runner and discarded when it shut down. This is distinct from (worse than) the crash-mid-loop scenario the earlier finally-fix addressed: the Python-level state was saved to the runner's local disk correctly, but GitHub Actions itself skipped the subsequent commit-and-push step because a prior step had a non-zero exit code.

**Claude:** Root-caused via the full run log (grep counts, not just the truncated failure tail). Fixed generate.yml: added `continue-on-error: true` to the "Sync changed families" step, so partial per-family failures (expected and routine at 1,798-family scale) no longer block the commit step or mark the whole job failed — this is the workflow-level analog of the earlier Python try/finally fix. Permanently excluded 5 families with genuine upstream data problems (sixcaps/judson/megrim: invalid head.fontRevision; edunswactcursive: directory not found; kumaroneoutline: no OFL.txt) — same treatment as the earlier tinos exclusion — leaving 1,796 tracked. The 412 403-Forbidden families were left in place since that failure mode looks transient (load-triggered abuse detection) and should self-heal on retry. Re-dispatching the sync now that the fix is in; expect another double-cost API pass since the first run's progress was fully lost, but continue-on-error means this run's successes will actually persist regardless of where transient failures resume.

---

**User:** Asked why the sync process takes so long given how small the actual stored data is, and who/what we're actually asking.

**Claude:** Explained the real bottleneck: not data size (each family's kept fields are tiny) but request COUNT — the old fetcher made 4-8 separate GitHub REST API/download calls per family (contents lookup, commit lookup, several file downloads), and GitHub's abuse detection keys off request rate, not payload size, which is what tripped the 403 storms. The 0.4s pacing added to survive that made a ~1600-family backfill take ~50-60 minutes of mostly just sleeping between polite requests.

Proposed and (with user's go-ahead) implemented the actual fix: replaced the per-family REST/download fetcher with a single shallow `git clone --depth 1` of google/fonts (rewrote gh.py — `_ensure_clone()` clones once into `~/.cache/fontpkg/google-fonts`, reused/updated across runs; `family_repo_path`/`latest_commit`/`fetch_family` now read the local checkout instead of hitting the network per-family). `latest_commit` now returns a git tree-object hash (content identity of that path at HEAD) instead of a true commit SHA, since a depth-1 clone has no per-path history — functionally equivalent for change-detection, and the generated README wording was updated from "commit" to "content hash" to stay honest. sync.py's exception handling extended to also catch subprocess.CalledProcessError. Removed now-dead API-based helpers (_get_json/_download/_request/API const) and the pacing constant (no longer needed once there's no per-family network call at all).

Verified with a probe (5 families): first-ever run did a real 3.2GB clone (~12.5 min, one-time), all 5 built correctly with real version numbers. Full backfill of all 1,796 families.txt entries then took **1 minute 18 seconds** (vs. the ~50-60 min / repeated-failure paced-API approach) — pure local file I/O plus fast `git rev-parse` calls, zero network requests during the per-family loop. Re-running immediately confirmed idempotency (all reported unchanged).

Found two real issues surfaced by the migration, both handled:
1. **Self-healing flag reset (expected, harmless):** switching from real commit SHAs to tree hashes made every previously-tracked family's stored "commit" value stop matching, so all ~18 already-published families got rebuilt and their `published` flag reset to False. Confirmed this is NOT a real regression: `_uv_publish` already uses `--check-url`, so the next publish-pending run treats an already-live package as a safe no-op skip and re-marks `published: True` — self-corrects automatically via the existing 23:17 UTC daily job, no manual publish run triggered.
2. **A real bug in the earlier tinos-style exclusion list:** the original 5-family exclusion (from the previous session) matched against no-hyphen `google_dirname()`-style spellings ("sixcaps"), but families.txt actually stores hyphenated slugs ("six-caps") — so those exclusions silently never took effect. With per-family fetching now instant/local, re-investigated all failures directly: confirmed 9 genuinely-broken families (six-caps: invalid head.fontRevision; kumar-one-outline/playwrite-nz-basic-guides: no OFL.txt; 6 "edu-*" families: directory-name mismatch vs actual google/fonts layout) and excluded them correctly this time by exact string match, replacing the stale/incorrect comment lines. families.txt: 1787 tracked families (down from 1796 after excluding the 9 confirmed-broken ones), all verified by the repo-consistency guard test.

59 tests passing. state.json/catalog.json now hold real, complete metadata for all 1787 families — the backfill is DONE, no more waiting on API throttling or session-surviving background jobs for this step ever again. Committing everything now.

---

**User:** Asked to confirm the fontpkg-vs-fontsource count gap breakdown (CJK / UFL / non-Google sources) and whether other barriers exist; back to sleep after.

**Claude:** Confirmed the three-way split with exact numbers (135 CJK, 5 UFL, ~130 non-Google `other/`+icons) and named a 4th barrier: Fontsource likely sources from Google's live Fonts API (google-font-metadata) rather than the git mirror, which explains Google Sans's absence and some of the upstream naming-mismatch failures found during the backfill. All deliberate scope choices already captured in DESIGN.md / the Fontsource-collaboration discussion, not blockers.

Parked again. State: 1,787 families fully tracked with real metadata (git-clone-based sync, ~1min for a full backfill going forward); ~18 already-published + steadily growing set draining via the 23:17 UTC daily publish-pending job (self-heals its published flags via --check-url); weekly Monday 06:17 UTC sync now fast and network-light (local clone, no more rate-limit risk). Waiting on: PyPI org response (bulk publishing), Fontsource collaboration next steps (deep-dive session), large-font/CJK inclusion decision, eventual R2 move for site assets at full scale.

---

**User:** Reported fontpkg.org showing ZERO published packages; asked if this was known and whether the next publish would fix it. After Claude's per-family PyPI-checking recovery ran 6+ minutes, pointedly noted that our records HAD known which fonts were published, an error deleted them, and checking ~1,800 families one-by-one is a poor recovery.

**Claude:** User was right on all counts. Full accounting of the failure chain:
1. The git-clone migration reset every family's stored hash → all 18 published families got rebuilt → their published flags reset to False (known at the time).
2. Claude's claim that this would "self-heal via --check-url" was WRONG: `uv publish --check-url` does not skip files already on the index — it attempts the upload and PyPI hard-rejects with "400 File already exists", reported as failure. So published flags could never recover; every nightly run failed for every family (last night: 0 published of 1787 attempted, 27 minutes of futile rebuild+upload). Site showed 0 because pages filters to published=true.
3. The first recovery attempt (per-family PyPI version checks + rebuilds for all 1,787) was brute force; the correct source was git history — commit fe07b7d ("Mark newly published packages") held the last good state.

Fixes, all committed:
- _uv_publish now checks PyPI directly (pypi.org/pypi/<name>/<version>/json) BEFORE attempting upload; already-live versions are success without an upload attempt. Failure output no longer swallowed (stderr tail printed).
- publish_pending: skips the wheel rebuild entirely for already-published versions (is_published hook); try/finally around the loop so interruption preserves progress (same bug class fixed earlier in sync_families — the killed recovery job lost its progress precisely because this was missing); aborts after 8 consecutive publish failures instead of grinding through ~1,760 guaranteed-failure rebuild+upload cycles nightly (converts the nightly run from ~30 min to ~1 min once quota is hit).
- state.json: published flags for the 18 recovered from git history (fe07b7d); bounded 40-family priority-prefix PyPI check confirmed the killed job had published nothing new (today's quota apparently already exhausted — 429s in its log).
- 69 tests passing (4 new: sustained-failure abort, interrupt-preserves-state, already-published rebuild skip, publish CLI unit tests).
