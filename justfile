default: test

sync:
    uv sync --all-packages

test:
    uv run pytest core/tests generator/tests

build +families:
    uv run fontpkg-gen build {{families}} --out build --wheel

watch:
    uv run pytest core/tests generator/tests -f
