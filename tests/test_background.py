from PIL import Image

from sambo_photo.background_engine import mask_from_png, mask_to_png, review_mask


def test_mask_roundtrip():
    mask = Image.new("L", (32, 20), 0)
    mask.putpixel((10, 10), 255)
    encoded = mask_to_png(mask)
    decoded = mask_from_png(encoded)
    assert decoded is not None
    assert decoded.size == (32, 20)
    assert decoded.getpixel((10, 10)) == 255


def test_empty_mask_requires_review():
    mask = Image.new("L", (100, 100), 0)
    status, reasons = review_mask(mask)
    assert status == "검토 필요"
    assert reasons


def test_reasonable_center_mask_is_draft():
    mask = Image.new("L", (100, 100), 0)
    for y in range(20, 80):
        for x in range(30, 70):
            mask.putpixel((x, y), 255)
    status, _ = review_mask(mask)
    assert status == "자동 초안"
