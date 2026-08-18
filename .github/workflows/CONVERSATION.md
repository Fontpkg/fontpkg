
---

**User:** Asked to update GitHub Actions pinned to Node 20-era versions (deprecation warnings on all workflows).

**Claude:** Checked latest releases and bumped all five workflows: checkout v4→v7, setup-uv v5→v10, upload-artifact v4→v7, configure-pages v5→v6, upload-pages-artifact v3→v5, deploy-pages v4→v5. Also fixed a families.txt header comment that had split a sentence. Verified CI green and warning-free after the bump.
