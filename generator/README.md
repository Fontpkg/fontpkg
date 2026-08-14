# fontpkg-generator

Generates `fontpkg-<family>` PyPI packages from the
[google/fonts](https://github.com/google/fonts) repository. Only OFL-1.1 and
Apache-2.0 families are built; binaries are shipped byte-for-byte unmodified with
their license text.

```bash
uv run fontpkg-gen build roboto inter --out build --wheel
```
