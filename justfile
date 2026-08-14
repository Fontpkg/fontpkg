default: test

sync:
    uv sync --all-packages

test:
    uv run pytest core/tests generator/tests

build +families:
    uv run fontpkg-gen build {{families}} --out build --wheel

sync-fonts:
    GITHUB_TOKEN=$(gh auth token) uv run fontpkg-gen sync --families-file families.txt --state state.json --out build --wheel

watch:
    uv run pytest core/tests generator/tests -f
