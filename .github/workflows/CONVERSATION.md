
---

**User:** Asked to update GitHub Actions pinned to Node 20-era versions (deprecation warnings on all workflows).

**Claude:** Checked latest releases and bumped all five workflows: checkout v4→v7, setup-uv v5→v10, upload-artifact v4→v7, configure-pages v5→v6, upload-pages-artifact v3→v5, deploy-pages v4→v5. Also fixed a families.txt header comment that had split a sentence. Verified CI green and warning-free after the bump.

---

**User:** Noticed fontpkg.org showed 10 families vs 14 on PyPI; asked why. Mid-turn: also requested a family-count display in the site controls (like fontsource.org's "2,096 font families").

**Claude:** Root cause: pages.yml only redeployed after the weekly sync; daily publish runs flip packages to published without redeploying — site lagged at Monday state. Fixed: pages.yml now also triggers on "Publish pending packages" completion; catch-up deploy verified 14 families live. Also: publish-pending now drains in popularity order via --priority-file families.txt (was alphabetical — Roboto would have waited months behind the A's; test added), and the site controls show a live count ("N font families", "n of N" when filtered). 55 tests passing.
