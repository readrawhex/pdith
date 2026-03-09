import argparse
import re
import numpy as np
import os
import sys
from PIL import Image
from pathlib import PurePath

def output_filepath(filename: str, outdir: str) -> str:
    """Generate the output filepath

    :param filename: input filepath
    :vartype filename: str
    :param outdir: parent directory of output filepath
    :vartype outdir: str
    :returns: output filepath for file
    :rtype: str
    """
    filepath = PurePath(filename)
    return os.path.join(outdir, filepath.name.replace(filepath.suffix, ".png"))


def from_hex(hexstr: str) -> (int, int, int):
    """Get color tuple from hex string

    :param hexstr: the input hex representation of the color as str
    :vartype hexstr: str
    :returns: a tuple containing the RGB color value
    :rtype: (int, int, int)
    """
    if not re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$").match(hexstr):
        raise ValueError("argument is not a valid hex color")
    hexstr = hexstr.strip("#")
    if len(hexstr) > 3:
        return (int(hexstr[0:2], 16), int(hexstr[2:4], 16), int(hexstr[4:6], 16))
    return (int(hexstr[0] * 2, 16), int(hexstr[1] * 2, 16), int(hexstr[2] * 2, 16))


def get_matrix(width: int, height: int, seed: int = None, dims: (int, int) = None, res: int = 1) -> [[(int, int, int)]]:
    """Generate a matrix for use with dithering.

    Generate a matrix for use with dithering calculations, where an argument for `seed` can
    be provided to produce the same result each time the function is called. A numpy 2D array
    shape can be provided with the `dims` argument, to repeat the matrix such that
    its final shape is equivalent.

    :param seed: seed to use for matrix generation, `None` for random seed
    :vartype seed: int
    :param width: width of returned matrix
    :vartype width: int
    :param height: height of returned matrix
    :vartype height: int
    :returns: a matrix of RGB color tuples (height X width)
    :rtype: [[int]]
    """
    if width is None and height is None:
        width = 8
        height = 8
    elif width is None or height is None:
        width = width if width else height
        height = height if height else width

    if width < 1 or height < 1:
        raise ValueError("width and height values must be positive")
    if res < 1:
        raise ValueError("matrix resolution must be positive")

    rng = np.random.default_rng(seed)
    m = rng.integers(0, 256, size=(height, width), dtype=np.uint8)

    if res > 1:
        m = np.repeat(m, res, axis=0)
        m = np.repeat(m, res, axis=1)
    if dims:
        f_h, f_w = dims
        m = m[np.arange(f_h) % height][:, np.arange(f_w) % width]

    return m




def main():
    try:
        parser = argparse.ArgumentParser(description="picture dithering utility")
        parser.add_argument("images", nargs="+", help="images to use in dither")
        parser.add_argument("-l", "--layer", action="store_true", help="use layer mode for dithering (default)")
        parser.add_argument("-s", "--individual", type=str, nargs="?", const="#000", default=None, help="use individual mode for dithering with provided background color (default=#000)")
        parser.add_argument("-i", "--invert", action="store_true", help="invert mask for dithering")
        parser.add_argument("-b", "--background", type=str, help="use individual mode for dithering with provided background image")
        parser.add_argument("-f", "--mask", type=str, help="use image as mask for determining dithering on input (only for -i mode or 2 image -l mode)")
        parser.add_argument("-o", "--output", type=str, default="output", help="output directory to write files to")
        parser.add_argument("-r", "--resolution", type=int, default=1, help="size of individual pixels in dither matrix")
        parser.add_argument("-m", "--matrix-m", type=int, default=8, help="matrix resolution, or matrix width if used with -n")
        parser.add_argument("-n", "--matrix-n", type=int, help="matrix resolution, or matrix height if used with -m")
        parser.add_argument("--seed", type=int, help="seed for matrix generation")
        args = parser.parse_args()

        os.makedirs(args.output, exist_ok=True)

        bweights = np.array([0.2126, 0.7152, 0.0722])

        if args.individual or args.background:
            bg_img = None
            if args.background:
                bg_img = Image.open(args.background).convert("RGB")
            else:
                color_value = from_hex(args.individual)

            for f in args.images:
                img = Image.open(f).convert("RGB")
                pixels = np.asarray(img)
                brightness = pixels @ bweights

                if bg_img:
                    bg_img_sized = bg_img.resize(img.size, Image.Resampling.LANCZOS)
                    bg = np.asarray(bg_img_sized)
                else:
                    bg = np.full(pixels.shape, color_value, dtype=np.uint8)

                matrix = get_matrix(args.matrix_m, args.matrix_n, args.seed, brightness.shape, args.resolution)

                result = np.zeros_like(pixels, dtype=np.uint8)
                result = np.where(
                    brightness[..., None] < matrix[..., None] if args.invert else brightness[..., None] >= matrix[..., None], 
                    pixels, 
                    bg
                )

                img = Image.fromarray(result)
                img.save(output_filepath(f, args.output))
        else:
            if len(args.images) < 2:
                raise Exception("must provide 2 or more files for layered dithering")
            
            for i, f in enumerate(args.images):
                if i == 0:
                    img = Image.open(f).convert("RGB")
                    pixels = np.asarray(img).copy()
                    continue

                new_img = Image.open(f).convert("RGB").resize(img.size, Image.Resampling.LANCZOS)
                new_pixels = np.asarray(new_img)
                brightness = new_pixels @ bweights

                matrix = get_matrix(args.matrix_m, args.matrix_n, args.seed, brightness.shape, args.resolution)
                pixels = np.where(
                    brightness[..., None] < matrix[..., None] if args.invert else brightness[..., None] >= matrix[..., None], 
                    new_pixels, 
                    pixels
                )

            img = Image.fromarray(pixels)
            img.save(output_filepath(args.images[0], args.output))
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
