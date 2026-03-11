import argparse
import itertools
import json
import magic
import numpy as np
import numpy.typing as npt
import os
import re
import subprocess
import sys
import tempfile
from itertools import repeat
from moviepy import VideoClip, VideoFileClip
from moviepy.video.fx import Resize
from PIL import Image
from pathlib import PurePath
from typing import Iterator


_setup = {
    # global values for frame / video resizing
    "dimensions": None,
    "frame_length": None,
    "duration": None,
    "fps": None,
}
_tempfiles = [
    # temporary filenames to delete post final output
]

# weights for RGB values to determine brightness
bweights = np.array([0.2126, 0.7152, 0.0722])


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
    new_suffix = ".png"
    if _setup["frame_length"] > 1:
        new_suffix = ".mp4"
    path = os.path.join(outdir, filepath.name.replace(filepath.suffix, new_suffix))
    i = 1
    last_suffix = new_suffix
    while os.path.exists(path):
        dup_suffix = f"_{i}{new_suffix}"
        path = path.replace(last_suffix, dup_suffix)
        last_suffix = dup_suffix
        i += 1
    return path


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


def get_matrix(
    width: int,
    height: int,
    seed: int = None,
    dims: (int, int) = None,
    res: int = 1,
    curve: float = 1,
) -> [[(int, int, int)]]:
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
    :param res: "block" size of pixels within matrix
    :vartype res: int
    :param curve: curve values within matrix by applying exponent `curve`
    :vartype curve: float
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

    if curve != 1:
        tmp = m.astype(np.float32)
        np.divide(tmp, 255.0, out=tmp)
        np.power(tmp, curve, out=tmp)
        np.multiply(tmp, 255.0, out=tmp)
        np.clip(tmp, 0, 255, out=tmp)
        m = tmp.astype(np.uint8)

    if res > 1:
        m = np.repeat(m, res, axis=0)
        m = np.repeat(m, res, axis=1)
    if dims:
        f_h, f_w = dims
        m = m[np.arange(f_h) % height][:, np.arange(f_w) % width]

    return m


def is_video(filepath: str) -> bool:
    """Check if file at filepath is video or image

    :param filepath: path to file to check
    :vartype filepath: str
    :returns: a boolean answer, `True` if video, `False` if image
    :rtype: bool
    """
    mime = magic.from_file(filepath, mime=True)
    if mime.startswith("video"):
        return True
    elif mime.startswith("image"):
        return False
    raise Exception(f"{mime} mimetype unsupported")


def get_frame_count(filepath: str) -> int:
    """Returns the number of frames from a video using `ffprobe`

    :param filepath: path to video file
    :vartype filepath: str
    :returns: number of frames in video
    :rtype: int
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-count_frames",
        "-show_entries",
        "stream=nb_read_frames",
        "-of",
        "json",
        filepath,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    return int(data["streams"][0]["nb_read_frames"])


def rescale_video(
    clip: VideoFileClip, frame_length: int = None, dims: (int, int) = None
) -> VideoFileClip:
    """Rescale a video's length & size w/ `ffmpeg`

    :param clip: video clip
    :vartype clip: VideoFileClip
    :param frame_length: target number of frames to scale to
    :vartype frame_length: int
    :param dims: new dimensions for video (H x W)
    :vartype dims: (int, int)
    :returns: a new video clip of the scaled video
    :rtype: VideoFileClip
    """
    if frame_length is None and dims is None:
        raise TypeError("at least one of frame_rate or dims arguments must be provided")

    if frame_length:
        target_fps = frame_length / clip.duration
        input_path = clip.filename

        tmp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp_path = tmp_file.name
        tmp_file.close()

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-filter:v",
            "fps=" + str(target_fps),
            # "-c:a", "copy", to copy original audio
            tmp_path,
        ]
        subprocess.run(cmd, check=True)
        clip = VideoFileClip(tmp_path)
        _tempfiles.append(tmp_path)
    if dims:
        clip = clip.resized(new_size=(dims[1], dims[0]))
    return clip


def open_file(filepath: str, reset: bool = False) -> Iterator[npt.NDArray[np.uint8]]:
    """Open file at filepath and set up global vars if necessary

    :param filepath: path to file to open
    :vartype filepath: str
    :param reset: reset any global variables set up from opening initial video
    :vartype reset: bool
    :returns: pixel content as iterator of numpy arrays
    :rtype: Iterator[npt.NDArray[np.unit8]]
    """
    global _setup

    if is_video(filepath):
        video = VideoFileClip(filepath, audio=False)

        new_dims = None
        new_length = None
        if _setup["dimensions"] is None or reset:
            _setup["dimensions"] = (video.h, video.w)
        else:
            new_dims = _setup["dimensions"]

        if _setup["frame_length"] is None or reset:
            _setup["frame_length"] = get_frame_count(filepath)
            _setup["fps"] = video.fps
            _setup["duration"] = video.duration
        else:
            new_length = _setup["frame_length"]

        if new_dims or new_length:
            video = rescale_video(video, new_length, new_dims)

        return itertools.cycle(video.iter_frames())
    else:
        img = Image.open(filepath).convert("RGB")

        if _setup["dimensions"] is None or reset:
            _setup["dimensions"] = (img.size[1], img.size[0])
        else:
            img = img.resize(
                (_setup["dimensions"][1], _setup["dimensions"][0]),
                Image.Resampling.LANCZOS,
            )

        if _setup["frame_length"] is None or reset:
            _setup["frame_length"] = 1
            _setup["fps"] = None
            _setup["duration"] = None
            return iter([np.asarray(img)])
        return itertools.cycle(repeat(np.asarray(img), _setup["frame_length"]))


def dither(
    bf: npt.NDArray[np.uint8],
    tf: npt.NDArray[np.uint8],
    m: npt.NDArray[np.uint8],
    invert: bool = False,
) -> npt.NDArray[np.uint8]:
    """Dither frame using dither matrix with specified background frame

    The shapes for the arguments should be as follows:

    - `bf.shape = (H, W, 3)`
    - `tf.shape = (H, W, 3)`
    - `m.shape = (H, W, 1)`

    :param bf: background frame
    :vartype bf: npt.NDArray[np.uint8]
    :param tf: top frame to dither
    :vartype tf: npt.NDArray[np.uint8]
    :param m: dithering matrix
    :vartype m: npt.NDArray[np.uint8]
    :param invert: invert dithering mask
    :vartype invert: bool
    :returns: dithered output frame
    :rtype: npt.NDArray[np.uint8]
    """
    brightness = (tf @ bweights).astype(np.uint8)
    if invert:
        mask = brightness < m
    else:
        mask = brightness >= m
    mask = mask[..., None]

    out = bf.copy()
    out[mask] = tf[mask]
    return out


def create_output(filename: str, generators: [iter], args: argparse.Namespace):
    """Generate dithered output using ordered generators and arguments

    :param filename: name of base file to compute output filename from
    :vartype filename: str
    :param generators: list of generators in order of desired dither layering
    :vartype generators: [iter]
    :param args: argparse arguments
    :vartype args: argparse.Namespace
    """
    ms = [
        get_matrix(
            args.matrix_m,
            args.matrix_n,
            args.seed,
            _setup["dimensions"],
            args.resolution,
            args.curve,
        )
        for x in range(0, len(generators) - 1)
    ]

    def generate():
        """recursive layered dithering"""
        frame = next(generators[-1])
        for i in reversed(range(len(ms))):
            bf = next(generators[i])
            frame = dither(bf, frame, ms[i], args.invert)
        return frame

    of = output_filepath(filename, args.output)
    if _setup["frame_length"] == 1:
        img = Image.fromarray(generate())
        img.save(of)
    else:
        clip = VideoClip(lambda t: generate(), duration=_setup["duration"])
        clip.fps = _setup["fps"]
        clip.write_videofile(of)
    print(of)


def main():
    try:
        parser = argparse.ArgumentParser(description="picture dithering utility")
        parser.add_argument("images", nargs="+", help="images to use in dither")
        parser.add_argument(
            "-l",
            "--layer",
            action="store_true",
            help="use layer mode for dithering (default)",
        )
        parser.add_argument(
            "-s",
            "--individual",
            type=str,
            nargs="?",
            const="#000",
            default=None,
            help="use individual mode for dithering with provided background color (default=#000)",
        )
        parser.add_argument(
            "-i", "--invert", action="store_true", help="invert mask for dithering"
        )
        parser.add_argument(
            "-b",
            "--background",
            type=str,
            help="use individual mode for dithering with provided background image",
        )
        parser.add_argument(
            "-f",
            "--mask",
            type=str,
            help="use image as mask for determining dithering on input (only for -i mode or 2 image -l mode)",
        )
        parser.add_argument(
            "-o",
            "--output",
            type=str,
            default="output",
            help="output directory to write files to",
        )
        parser.add_argument(
            "-r",
            "--resolution",
            type=int,
            default=1,
            help="size of individual pixels in dither matrix",
        )
        parser.add_argument(
            "-m",
            "--matrix-m",
            type=int,
            default=8,
            help="matrix resolution, or matrix width if used with -n",
        )
        parser.add_argument(
            "-n",
            "--matrix-n",
            type=int,
            help="matrix resolution, or matrix height if used with -m",
        )
        parser.add_argument(
            "-c",
            "--curve",
            type=float,
            default=1,
            help="curve threshold values within dither matrix by exponent CURVE",
        )
        parser.add_argument("--seed", type=int, help="seed for matrix generation")
        args = parser.parse_args()

        os.makedirs(args.output, exist_ok=True)

        if args.individual or args.background:
            bg_img = open_file(args.background) if args.background else None
            color_value = from_hex(args.individual) if args.individual else None

            for f in args.images:
                if args.background:
                    bg_frames = open_file(args.background, reset=True)
                    frames = open_file(f)
                else:
                    frames = open_file(f, reset=True)
                    bg_frames = itertools.cycle(
                        repeat(
                            np.full(
                                (_setup["dimensions"][0], _setup["dimensions"][1], 3),
                                color_value,
                                dtype=np.uint8,
                            ),
                            _setup["frame_length"],
                        )
                    )

                create_output(f, [bg_frames, frames], args)
        else:
            if len(args.images) < 2:
                raise Exception("must provide 2 or more files for layered dithering")

            frames = open_file(args.images[0])
            generators = [frames] + [open_file(x) for x in args.images[1:]]
            create_output(args.images[0], generators, args)

        for f in _tempfiles:
            os.remove(f)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
