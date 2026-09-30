from __future__ import annotations

from pathlib import Path
from typing import Tuple

from PIL import Image, ImageColor, ImageOps

from .models import OutputSettings


SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def physical_to_px(value: float, unit: str, dpi: int) -> int:
    if unit == "px":
        return max(1, int(round(value)))
    if unit == "mm":
        inches = value / 25.4
    elif unit == "cm":
        inches = value / 2.54
    elif unit == "inch":
        inches = value
    else:
        raise ValueError(f"Unsupported unit: {unit}")
    return max(1, int(round(inches * dpi)))


def target_size(settings: OutputSettings) -> Tuple[int, int]:
    return (
        physical_to_px(settings.width, settings.unit, settings.dpi),
        physical_to_px(settings.height, settings.unit, settings.dpi),
    )


def load_image(path: Path, rotation: int = 0) -> Image.Image:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    if rotation % 360:
        img = img.rotate(-rotation, expand=True)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
    return img


def _custom_fill_crop(img: Image.Image, target_ratio: float, zoom: float, pan_x: float, pan_y: float) -> Image.Image:
    src_w, src_h = img.size
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        base_h = src_h
        base_w = src_h * target_ratio
    else:
        base_w = src_w
        base_h = src_w / target_ratio

    zoom = max(1.0, min(float(zoom), 8.0))
    crop_w = max(1.0, base_w / zoom)
    crop_h = max(1.0, base_h / zoom)

    max_x = max(0.0, src_w - crop_w)
    max_y = max(0.0, src_h - crop_h)
    px = max(-1.0, min(1.0, float(pan_x)))
    py = max(-1.0, min(1.0, float(pan_y)))
    left = max_x * ((px + 1.0) / 2.0)
    top = max_y * ((py + 1.0) / 2.0)

    box = (
        int(round(left)),
        int(round(top)),
        int(round(left + crop_w)),
        int(round(top + crop_h)),
    )
    return img.crop(box)


def render_image(img: Image.Image, settings: OutputSettings) -> Image.Image:
    tw, th = target_size(settings)
    target_ratio = tw / th

    if settings.crop_mode in {"fill", "custom"}:
        zoom = settings.zoom if settings.crop_mode == "custom" else 1.0
        pan_x = settings.pan_x if settings.crop_mode == "custom" else 0.0
        pan_y = settings.pan_y if settings.crop_mode == "custom" else 0.0
        cropped = _custom_fill_crop(img, target_ratio, zoom, pan_x, pan_y)
        return cropped.resize((tw, th), Image.Resampling.LANCZOS)

    working = img.convert("RGBA")
    working.thumbnail((tw, th), Image.Resampling.LANCZOS)
    try:
        bg_rgb = ImageColor.getrgb(settings.background)
    except ValueError:
        bg_rgb = (255, 255, 255)
    canvas = Image.new("RGBA", (tw, th), (*bg_rgb, 255))
    x = (tw - working.width) // 2
    y = (th - working.height) // 2
    canvas.alpha_composite(working, (x, y))
    return canvas


def export_image(img: Image.Image, settings: OutputSettings, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fmt = settings.output_format.upper()
    out = img
    kwargs = {"dpi": (settings.dpi, settings.dpi)}

    if fmt == "JPEG":
        if out.mode != "RGB":
            rgb = Image.new("RGB", out.size, "white")
            if out.mode == "RGBA":
                rgb.paste(out, mask=out.getchannel("A"))
            else:
                rgb.paste(out.convert("RGB"))
            out = rgb
        kwargs.update({"quality": settings.quality, "subsampling": 0, "optimize": True})
    elif fmt == "WEBP":
        kwargs.update({"quality": settings.quality, "method": 6})
    elif fmt == "PNG":
        kwargs.update({"optimize": True})
    else:
        raise ValueError(f"Unsupported format: {fmt}")

    out.save(destination, format=fmt, **kwargs)
    return destination


def extension_for(fmt: str) -> str:
    return {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[fmt.upper()]


def suggested_filename(source: Path, settings: OutputSettings) -> str:
    label = settings.name.replace(" ", "_").replace("/", "-")
    return f"{source.stem}_{label}{extension_for(settings.output_format)}"


def ensure_extension(path: Path, fmt: str) -> Path:
    expected = extension_for(fmt)
    if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        return path.with_suffix(expected)
    return path


def unique_destination(folder: Path, filename: str) -> Path:
    candidate = folder / filename
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    counter = 2
    while True:
        candidate = folder / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
