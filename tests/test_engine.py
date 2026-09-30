from PIL import Image

from sambo_photo.image_engine import apply_foreground_mask, render_image, target_size
from sambo_photo.models import OutputSettings


def test_35x45mm_300dpi():
    s = OutputSettings(width=35, height=45, unit="mm", dpi=300)
    assert target_size(s) == (413, 531)


def test_fill_output_size():
    img = Image.new("RGB", (1600, 900), "red")
    s = OutputSettings(width=900, height=1200, unit="px", crop_mode="fill")
    out = render_image(img, s)
    assert out.size == (900, 1200)


def test_fit_output_size():
    img = Image.new("RGB", (1600, 900), "red")
    s = OutputSettings(width=900, height=1200, unit="px", crop_mode="fit", background="#FFFFFF")
    out = render_image(img, s)
    assert out.size == (900, 1200)


def test_transparent_mask_is_non_destructive():
    img = Image.new("RGB", (8, 8), "red")
    mask = Image.new("L", (8, 8), 0)
    mask.putpixel((4, 4), 255)

    out = apply_foreground_mask(img, mask, "transparent")
    assert out.mode == "RGBA"
    assert out.getpixel((0, 0))[3] == 0
    assert out.getpixel((4, 4))[3] == 255
    assert img.mode == "RGB"
    assert img.getpixel((0, 0)) == (255, 0, 0)


def test_color_background_composite():
    img = Image.new("RGB", (4, 4), "red")
    mask = Image.new("L", (4, 4), 0)
    out = apply_foreground_mask(img, mask, "color", "#00FF00")
    assert out.getpixel((0, 0))[:3] == (0, 255, 0)
