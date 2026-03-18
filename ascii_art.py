import requests
from PIL import Image
from io import BytesIO

ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]


def resized_gray_image(image, new_width=40):
    """
    Resize and convert image to grayscale.
    """
    width, height = image.size
    aspect_ratio = height / width
    # 0.55 is a correction factor as terminal characters are taller than they are wide
    new_height = int(aspect_ratio * new_width * 0.55)
    img = image.resize((new_width, new_height))
    return img.convert("L")


def pixels_to_ascii(image):
    """
    Map grayscale pixels to ASCII characters.
    """
    pixels = image.getdata()
    # 255 / 11 (len(ASCII_CHARS)) ~= 23.  Using 25 for safe integer division mapping.
    characters = "".join([ASCII_CHARS[pixel // 25] for pixel in pixels])
    return characters


def image_url_to_ascii(url, new_width=40):
    """
    Convert an image URL to a colored ASCII string using ANSI escape codes.
    """
    if not url:
        return ""

    try:
        response = requests.get(url, timeout=5)
        image = Image.open(BytesIO(response.content))
    except Exception:
        return ""

    # Resize image
    width, height = image.size
    aspect_ratio = height / width
    # Calculate new height to maintain aspect ratio, considering terminal character dimensions
    # ASCII chars are taller than they are wide (approx ~2x)
    # Since we are using '██' (double width), we effectively make each "cell" square.
    # So we can just scale by aspect ratio directly without additional correction factor.
    new_height = int(aspect_ratio * new_width)
    if new_height > 60:
        new_height = 60
        new_width = int(new_height / aspect_ratio)

    # Resize and ensure RGB mode
    img = image.resize((new_width, new_height))
    img = img.convert("RGB")

    pixels = img.getdata()

    ascii_str = ""
    for i, pixel in enumerate(pixels):
        r, g, b = pixel
        ascii_str += f"\033[38;2;{r};{g};{b}m██\033[0m"

        # Add newline at the end of each row
        if (i + 1) % new_width == 0:
            ascii_str += "\n"

    return ascii_str
