# pdith

Picture dithering utility

---

I wrote something similar in rust called [rdith](https://github.com/readrawhex/rdith)
a little bit ago, but I wanted something quicker to install and compile on
my phone.

### install

```bash
git clone <this repo>
cd <this repo>
pipx install .
```

### usage

```
usage: pdith.py [-h] [-l] [-i [INDIVIDUAL]] [-b BACKGROUND] [-M MASK]
                [-o OUTPUT] [-r RESOLUTION] [-m MATRIX_M] [-n MATRIX_N]
                [-s SEED]
                images [images ...]

picture dithering utility

positional arguments:
  images                images to use in dither

options:
  -h, --help            show this help message and exit
  -l, --layer           use layer mode for dithering (default)
  -i [INDIVIDUAL], --individual [INDIVIDUAL]
                        use individual mode for dithering with provided
                        background color (default=#000)
  -b BACKGROUND, --background BACKGROUND
                        use individual mode for dithering with provided
                        background image
  -M MASK, --mask MASK  use image as mask for determining dithering on input
                        (only for -i mode or 2 image -l mode)
  -o OUTPUT, --output OUTPUT
                        output directory to write files to
  -r RESOLUTION, --resolution RESOLUTION
                        size of individual pixels in dither matrix
  -m MATRIX_M, --matrix-m MATRIX_M
                        matrix resolution, or matrix width if used with -n
  -n MATRIX_N, --matrix-n MATRIX_N
                        matrix resolution, or matrix height if used with -m
  -s SEED, --seed SEED  seed for matrix generation
```
