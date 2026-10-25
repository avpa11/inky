"""Exact Spectra 6 ink order used by the 4-inch E640 driver."""
from PIL import Image

COLORS = [(0, 0, 0), (255, 255, 255), (255, 255, 0),
          (255, 0, 0), (0, 0, 255), (0, 255, 0)]


def indexed_image(image):
    """Use solid ink colors; a six-color P image disables driver dithering."""
    palette = Image.new("P", (1, 1))
    palette.putpalette([channel for color in COLORS for channel in color])
    return image.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE)
