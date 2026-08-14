# How secrets work in this project

*Written August 2026. If you're reading this years later: yes, this is still how it
works, unless someone deleted the 1Password vault.*

## The one-sentence version

`.env` files in this project contain **1Password references, not secrets** — the real
values live in a 1Password vault, and `op run` injects them into commands at runtime.

## Why it was set up this way (the 2026 reasoning)

Projects live in `~/Dropbox/Projects/` so they sync across machines. That meant a
classic plaintext `.env` file would sync every API token to Dropbox's servers and every
logged-in device — discovered when a PyPI token spent a while doing exactly that.
1Password was already in use, already synced across machines, and already encrypted, so
it became the secrets backend. The `.env` *file* survives as a pointer layer because
every tool already understands the env-var convention.

## What the pieces are

- **`.env`** (gitignored) — contains lines like:
  ```
  PYPI_TOKEN=op://Development/fontpkg-ci/pypi-token
  ```
  That's a *reference*: vault `Development`, item `fontpkg-ci`, field `pypi-token`.
  This file holds no secrets and is safe anywhere.
- **`.env.example`** (committed) — documents which variables the project needs, with
  placeholder values. The contract, not the credentials.
- **The 1Password vault** — where the actual values live. Edit them in the 1Password
  app; nothing in the repo changes when a token rotates.
- **`op`** — the 1Password CLI (`brew install 1password-cli`). Sign-in is delegated to
  the 1Password app with biometric unlock.

## How to run things

Prefix any command that needs secrets with `op run`:

```bash
op run --env-file=.env -- uv publish dist/*
```

`op` resolves every `op://` reference into the child process's environment. Plaintext
never touches disk; the first use per session prompts Touch ID.

## FAQ for future-you

**I'm on a new machine.** Install the 1Password app + CLI, sign in. Done — the vault
synced everything.

**I need to add a secret.** Add the value to a vault item in 1Password, add a
`NAME=op://vault/item/field` line to `.env`, and a placeholder line to `.env.example`.

**I'm a contributor without 1Password.** Ignore all of this: copy `.env.example` to
`.env`, paste your own plaintext values, run commands normally. `op://` syntax is the
maintainer's private convention; nothing in the project requires it. (Maintainers: this
is why justfile recipes and scripts must read plain env vars and never hardwire `op run`.)

**Where does CI get secrets?** GitHub Actions secrets (`PYPI_TOKEN`) and PyPI Trusted
Publishing — 1Password is not involved in CI at all.

**What if 1Password goes away?** Export the vault items and fall back to any other
env-var source. Only the storage is 1Password-specific; the project itself just reads
environment variables.
