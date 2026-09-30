from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageColor, ImageDraw
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QLabel

from .background_engine import mask_to_png


def _checkerboard(size: tuple[int, int], tile: int = 24) -> Image.Image:
    w, h = size
    out = Image.new("RGBA", size, (238, 238, 238, 255))
    draw = ImageDraw.Draw(out)
    alt = (205, 205, 205, 255)
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            if ((x // tile) + (y // tile)) % 2:
                draw.rectangle((x, y, min(x + tile, w), min(y + tile, h)), fill=alt)
    return out


class MaskEditor(QLabel):
    maskChanged = Signal(bytes)

    def __init__(self):
        super().__init__("사진을 추가하세요")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(600, 560)
        self.setMouseTracking(True)
        self.setObjectName("preview")

        self._image: Image.Image | None = None
        self._mask: Image.Image | None = None
        self._view_mode = "result"
        self._background_mode = "transparent"
        self._background_color = "#FFFFFF"
        self._brush_mode = "restore"
        self._brush_size = 40
        self._painting = False
        self._display_size = (0, 0)
        self._display_offset = (0, 0)

    def set_document(
        self,
        image: Image.Image | None,
        mask: Image.Image | None,
        view_mode: str = "result",
        background_mode: str = "transparent",
        background_color: str = "#FFFFFF",
    ):
        self._image = image.convert("RGBA") if image else None
        self._mask = mask.convert("L") if mask else None
        self._view_mode = view_mode
        self._background_mode = background_mode
        self._background_color = background_color
        self.refresh()

    def set_view_mode(self, value: str):
        self._view_mode = value
        self.refresh()

    def set_background(self, mode: str, color: str):
        self._background_mode = mode
        self._background_color = color
        self.refresh()

    def set_brush(self, mode: str, size: int):
        self._brush_mode = mode
        self._brush_size = max(1, int(size))

    def mask(self) -> Image.Image | None:
        return self._mask.copy() if self._mask else None

    def _composite(self) -> Image.Image | None:
        if self._image is None:
            return None
        if self._view_mode == "original" or self._mask is None:
            return self._image.copy()
        if self._view_mode == "mask":
            return self._mask.convert("RGBA")

        fg = self._image.copy()
        fg.putalpha(self._mask)
        if self._background_mode == "color":
            try:
                rgb = ImageColor.getrgb(self._background_color)
            except ValueError:
                rgb = (255, 255, 255)
            bg = Image.new("RGBA", fg.size, (*rgb, 255))
        else:
            bg = _checkerboard(fg.size)
        bg.alpha_composite(fg)
        return bg

    def refresh(self):
        img = self._composite()
        if img is None:
            self.clear()
            self.setText("사진을 추가하세요")
            return
        max_w = max(1, self.width() - 20)
        max_h = max(1, self.height() - 20)
        preview = img.copy()
        preview.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        qimg = ImageQt(preview)
        pix = QPixmap.fromImage(qimg)
        self._display_size = (pix.width(), pix.height())
        self._display_offset = (
            (self.width() - pix.width()) // 2,
            (self.height() - pix.height()) // 2,
        )
        self.setText("")
        self.setPixmap(pix)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh()

    def _paint_at(self, event: QMouseEvent):
        if self._image is None or self._mask is None:
            return
        dw, dh = self._display_size
        ox, oy = self._display_offset
        if dw <= 0 or dh <= 0:
            return
        px = event.position().x() - ox
        py = event.position().y() - oy
        if not (0 <= px < dw and 0 <= py < dh):
            return

        x = int(px * self._mask.width / dw)
        y = int(py * self._mask.height / dh)
        radius = max(1, int(self._brush_size * self._mask.width / max(1, dw) / 2))
        value = 255 if self._brush_mode == "restore" else 0
        draw = ImageDraw.Draw(self._mask)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=value)
        self.refresh()
        self.maskChanged.emit(mask_to_png(self._mask))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._painting = True
            self._paint_at(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._painting:
            self._paint_at(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._painting = False
