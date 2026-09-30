from PIL import Image

from sambo_photo.image_engine import render_image, target_size
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
