import json
import os
import urllib.request
from pathlib import Path

DEFAULT_CATALOG_URL = "https://raw.githubusercontent.com/Fontpkg/fontpkg/main/catalog.json"


def fetch_catalog(source: str | None = None) -> dict[str, dict]:
    src = source or os.environ.get("FONTPKG_CATALOG_URL") or DEFAULT_CATALOG_URL
    if "://" not in src:
        return json.loads(Path(src).read_text(encoding="utf-8"))
    request = urllib.request.Request(src, headers={"User-Agent": "fontpkg-cli"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def search_catalog(catalog: dict[str, dict], query: str | None) -> list[dict]:
    entries = sorted(catalog.values(), key=lambda e: e["slug"])
    if not query:
        return entries
    q = query.strip().lower()
    return [
        e
        for e in entries
        if q in e["slug"]
        or q in e["family"].lower()
        or any(q in c.lower() for c in e.get("category", []))
    ]
