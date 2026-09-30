from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

CropMode = Literal["fill", "fit", "custom"]
OutputFormat = Literal["JPEG", "PNG", "WEBP"]
BackgroundMode = Literal["original", "transparent", "color"]


@dataclass
class OutputSettings:
    name: str = "3:4"
    width: float = 900
    height: float = 1200
    unit: Literal["px", "mm", "cm", "inch"] = "px"
    dpi: int = 300
    crop_mode: CropMode = "fill"
    background: str = "#FFFFFF"
    output_format: OutputFormat = "JPEG"
    quality: int = 95
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0

    def clone(self) -> "OutputSettings":
        return replace(self)


@dataclass
class PhotoTask:
    source_path: Path
    settings: OutputSettings = field(default_factory=OutputSettings)
    rotation: int = 0

    # V0.2 background-removal state. This is deliberately separate from source pixels.
    mask_png: bytes | None = None
    mask_status: str = "미실행"
    background_mode: BackgroundMode = "original"
    background_color: str = "#FFFFFF"

    @property
    def display_name(self) -> str:
        return self.source_path.name
