# pdith

Picture and video dithering utility.

The positional `images` arguments can either be video or image
files. Make sure that `ffmpeg` and `ffprobe` are both installed and
accessible on your system for video functionality to work properly.

The first video file argument provided in `images` determines the fps
and duration of the output video.

---

### install

```bash
git clone <this repo>
cd <this repo>
pipx install .
```

### usage

```
usage: pdith.py [-h] [-l] [-s [INDIVIDUAL]] [-i] [-b BACKGROUND] [-f MASK]
                [-o OUTPUT] [-r RESOLUTION] [-m MATRIX_M] [-n MATRIX_N]
                [-c CURVE] [--seed SEED]
                images [images ...]

picture dithering utility

positional arguments:
  images                images to use in dither

options:
  -h, --help            show this help message and exit
  -l, --layer           use layer mode for dithering (default)
  -s [INDIVIDUAL], --individual [INDIVIDUAL]
                        use individual mode for dithering with provided
                        background color (default=#000)
  -i, --invert          invert mask for dithering
  -b BACKGROUND, --background BACKGROUND
                        use individual mode for dithering with provided
                        background image
  -f MASK, --mask MASK  use image as mask for determining dithering on input
                        (only for -i mode or 2 image -l mode)
  -o OUTPUT, --output OUTPUT
                        output directory to write files to
  -r RESOLUTION, --resolution RESOLUTION
                        size of individual pixels in dither matrix
  -m MATRIX_M, --matrix-m MATRIX_M
                        matrix resolution, or matrix width if used with -n
  -n MATRIX_N, --matrix-n MATRIX_N
                        matrix resolution, or matrix height if used with -m
  -c CURVE, --curve CURVE
                        curve threshold values within dither matrix by
                        exponent CURVE
  --seed SEED           seed for matrix generation
```
