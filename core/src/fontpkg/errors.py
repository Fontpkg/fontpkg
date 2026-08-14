class FontpkgError(Exception):
    pass


class FamilyNotInstalled(FontpkgError, LookupError):
    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(
            f"font family {slug!r} is not installed — add it with: uv add fontpkg-{slug}"
        )


class StyleNotAvailable(FontpkgError, LookupError):
    pass


class WeightNotAvailable(FontpkgError, LookupError):
    pass
