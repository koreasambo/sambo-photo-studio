from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Preset:
    category: str
    name: str
    width: float
    height: float
    unit: str
    dpi: int = 300


class PresetManager:
    def __init__(self, preset_dir: Path):
        self.preset_dir = preset_dir
        self._items: dict[str, list[Preset]] = {}
        self.reload()

    def reload(self) -> None:
        items: dict[str, list[Preset]] = {}
        for path in sorted(self.preset_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            category = data["category"]
            items[category] = [Preset(category=category, **row) for row in data["presets"]]
        self._items = items

    @property
    def categories(self) -> list[str]:
        return list(self._items.keys())

    def presets(self, category: str) -> list[Preset]:
        return list(self._items.get(category, []))

    def find(self, category: str, name: str) -> Preset | None:
        for preset in self._items.get(category, []):
            if preset.name == name:
                return preset
        return None
