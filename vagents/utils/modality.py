import base64
from PIL import Image
from io import BytesIO


def resize_image(
    image: Image.Image, size=(128, 128), resample=Image.Resampling.BILINEAR
):
    return image.resize(size, resample=resample)


def image_to_base64(image: Image.Image):
    if isinstance(image, Image.Image) and image.mode != "RGB":
        print("Converting image to RGB mode for base64 encoding.")
        image = image.convert("RGB")
    image = resize_image(image)
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str
