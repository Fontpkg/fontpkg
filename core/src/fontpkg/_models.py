from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Axis:
    tag: str
    min: float
    max: float


@dataclass(frozen=True)
class FontFile:
    path: Path
    style: str
    weight: int | None
    variable: bool
    wght_min: int | None = None
    wght_max: int | None = None

    def covers(self, weight: int) -> bool:
        if self.variable and self.wght_min is not None and self.wght_max is not None:
            return self.wght_min <= weight <= self.wght_max
        return self.weight == weight


@dataclass(frozen=True)
class Family:
    name: str
    slug: str
    version: str
    license: str
    files: tuple[FontFile, ...]
    axes: tuple[Axis, ...] = ()

    @property
    def styles(self) -> list[str]:
        return sorted({f.style for f in self.files})

    @property
    def weights(self) -> list[int]:
        return sorted({f.weight for f in self.files if f.weight is not None})

    @property
    def weight_range(self) -> tuple[int, int] | None:
        lows: list[int] = [f.wght_min for f in self.files if f.wght_min is not None]
        highs: list[int] = [f.wght_max for f in self.files if f.wght_max is not None]
        lows += [w for w in self.weights]
        highs += [w for w in self.weights]
        if not lows:
            return None
        return (min(lows), max(highs))

    @property
    def is_variable(self) -> bool:
        return any(f.variable for f in self.files)


def family_from_metadata(meta: dict[str, Any], root: Any) -> Family:
    axes = tuple(Axis(a["tag"], float(a["min"]), float(a["max"])) for a in meta.get("axes", []))
    wght = next((a for a in axes if a.tag == "wght"), None)
    files = []
    for entry in meta["files"]:
        node = root
        for part in entry["path"].split("/"):
            node = node / part
        variable = bool(entry.get("variable"))
        weight = entry.get("weight")
        files.append(
            FontFile(
                path=Path(str(node)),
                style=entry.get("style", "normal"),
                weight=int(weight) if weight is not None else None,
                variable=variable,
                wght_min=int(wght.min) if variable and wght else None,
                wght_max=int(wght.max) if variable and wght else None,
            )
        )
    return Family(
        name=meta["family"],
        slug=meta["slug"],
        version=str(meta["version"]),
        license=meta["license"],
        files=tuple(files),
        axes=axes,
    )
