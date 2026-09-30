from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageChops, ImageStat

_SESSION = None


def mask_to_png(mask: Image.Image) -> bytes:
    out = BytesIO()
    mask.convert("L").save(out, format="PNG", optimize=True)
    return out.getvalue()


def mask_from_png(data: bytes | None) -> Image.Image | None:
    if not data:
        return None
    with Image.open(BytesIO(data)) as img:
        return img.convert("L").copy()


def create_auto_mask(img: Image.Image, model_name: str = "u2netp") -> Image.Image:
    """Create a foreground mask. Model weights may be downloaded on first use."""
    global _SESSION
    try:
        from rembg import new_session, remove
    except ImportError as exc:
        raise RuntimeError("배경제거 엔진(rembg)이 설치되지 않았습니다.") from exc

    if _SESSION is None:
        _SESSION = new_session(model_name)

    rgb = img.convert("RGB")
    mask = remove(
        rgb,
        session=_SESSION,
        only_mask=True,
        post_process_mask=True,
    )
    if not isinstance(mask, Image.Image):
        mask = Image.open(BytesIO(mask))
    return mask.convert("L").resize(rgb.size, Image.Resampling.LANCZOS)


def review_mask(mask: Image.Image) -> tuple[str, list[str]]:
    """Heuristic review flag; deliberately not presented as model confidence."""
    m = mask.convert("L")
    w, h = m.size
    hist = m.histogram()
    total = max(1, w * h)
    foreground = sum(hist[128:]) / total

    reasons: list[str] = []
    if foreground < 0.015:
        reasons.append("전경이 지나치게 작음")
    if foreground > 0.97:
        reasons.append("배경이 거의 제거되지 않음")

    band = max(1, min(w, h) // 40)
    border = Image.new("L", (w, h), 0)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(border)
    draw.rectangle((0, 0, w - 1, h - 1), outline=255, width=band)
    border_pixels = ImageChops.multiply(m, border)
    border_mean = ImageStat.Stat(border_pixels).mean[0] / 255.0
    if border_mean > 0.08:
        reasons.append("피사체가 화면 가장자리에 많이 닿음")

    return ("검토 필요" if reasons else "자동 초안"), reasons
