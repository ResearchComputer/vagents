from io import BytesIO

import pytest
from PIL import Image

from vagents.utils.modality import image_to_base64, resize_image
from vagents.core.wrappers import multimodal


def make_image(mode="RGB", size=(256, 256), color=(255, 0, 0)):
    img = Image.new(mode, size, color=color if mode == "RGB" else 128)
    return img


def test_image_to_base64_converts_and_resizes():
    img = make_image(mode="L", size=(512, 512))  # non-RGB
    b64 = image_to_base64(img)
    assert isinstance(b64, str)
    # Basic sanity: base64 strings length should be > 0
    assert len(b64) > 10


def test_resize_image_dimensions():
    img = make_image(size=(300, 200))
    resized = resize_image(img, size=(128, 128))
    assert resized.size == (128, 128)


def test_multimodal_wrapper_injects_image_content():
    @multimodal(input_type="image", param=["img"])  # wrap a simple prompt function
    def prompt(img=None):
        return "Describe the image"

    img = make_image()
    messages = prompt(img=img)
    assert isinstance(messages, list)
    assert messages[0]["role"] == "user"
    content = messages[0]["content"]
    # Expect one text part and one image_url part
    assert any(part.get("type") == "text" for part in content)
    assert any(part.get("type") == "image_url" for part in content)
