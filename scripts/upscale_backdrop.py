"""Upscale the home page's tardigrade photo 4x with Real-ESRGAN and write it into the site.

Run from the repository root on a machine with the backend's environment (it needs torch and Pillow):

    .venv/bin/python scripts/upscale_backdrop.py

Downloads the 1000 x 721 electron micrograph from Duda's image server and the Real-ESRGAN x4plus
weights (67 MB, checked against their SHA-256 and cached in ~/.cache/anhydra), upscales the photo on
the CPU in tiles, and saves WebP copies at several widths to frontend/anhydra-site/public/backdrop/.
Rebuild the site afterwards so they are copied into dist. Takes a few minutes on a CPU.

The network is Real-ESRGAN's RRDBNet (Wang et al., 2021; BSD-3-Clause, github.com/xinntao/Real-ESRGAN),
written out here so the script needs nothing beyond torch.
"""
import argparse
import hashlib
import io
from pathlib import Path
import sys
import urllib.request

import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "frontend" / "anhydra-site" / "public" / "backdrop"
SOURCE = "https://irp.cdn-website.com/9ec79508/dms3rep/multi/opt/tardigrade-sem-base-1920w.png"
WEIGHTS_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
WEIGHTS_SHA256 = "4fa0d38905f75ac06eb49a7951b426670021be3018265fd191d2125df9d682f1"
WEIGHTS = Path.home() / ".cache" / "anhydra" / "RealESRGAN_x4plus.pth"
SOURCE_WIDTH = 1000
WIDTHS = (1280, 1920, 2560, 3840)  # must match the srcSet in src/components/Backdrop.tsx
TILE, PAD = 192, 12


class ResidualDenseBlock(nn.Module):
    def __init__(self, feat=64, grow=32):
        super().__init__()
        self.conv1 = nn.Conv2d(feat, grow, 3, 1, 1)
        self.conv2 = nn.Conv2d(feat + grow, grow, 3, 1, 1)
        self.conv3 = nn.Conv2d(feat + 2 * grow, grow, 3, 1, 1)
        self.conv4 = nn.Conv2d(feat + 3 * grow, grow, 3, 1, 1)
        self.conv5 = nn.Conv2d(feat + 4 * grow, feat, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x


class RRDB(nn.Module):
    def __init__(self, feat=64, grow=32):
        super().__init__()
        self.rdb1 = ResidualDenseBlock(feat, grow)
        self.rdb2 = ResidualDenseBlock(feat, grow)
        self.rdb3 = ResidualDenseBlock(feat, grow)

    def forward(self, x):
        return self.rdb3(self.rdb2(self.rdb1(x))) * 0.2 + x


class RRDBNet(nn.Module):
    def __init__(self, feat=64, blocks=23, grow=32):
        super().__init__()
        self.conv_first = nn.Conv2d(3, feat, 3, 1, 1)
        self.body = nn.Sequential(*(RRDB(feat, grow) for _ in range(blocks)))
        self.conv_body = nn.Conv2d(feat, feat, 3, 1, 1)
        self.conv_up1 = nn.Conv2d(feat, feat, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(feat, feat, 3, 1, 1)
        self.conv_hr = nn.Conv2d(feat, feat, 3, 1, 1)
        self.conv_last = nn.Conv2d(feat, 3, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x):
        feat = self.conv_first(x)
        feat = feat + self.conv_body(self.body(feat))
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode="nearest")))
        feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode="nearest")))
        return self.conv_last(self.lrelu(self.conv_hr(feat)))


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def load_model() -> RRDBNet:
    if not WEIGHTS.exists():
        print(f"Downloading {WEIGHTS_URL}", file=sys.stderr)
        WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
        WEIGHTS.write_bytes(fetch(WEIGHTS_URL))
    if hashlib.sha256(WEIGHTS.read_bytes()).hexdigest() != WEIGHTS_SHA256:
        WEIGHTS.unlink()
        raise SystemExit(f"{WEIGHTS} did not match its checksum and was deleted; run again to re-download.")
    model = RRDBNet()
    model.load_state_dict(torch.load(WEIGHTS, map_location="cpu", weights_only=True)["params_ema"])
    return model.eval()


@torch.inference_mode()
def upscale(model: RRDBNet, img: Image.Image) -> Image.Image:
    """4x upscale in overlapping tiles, so memory stays small whatever the image size."""
    x = torch.from_numpy(np.asarray(img.convert("RGB"), dtype=np.float32) / 255).permute(2, 0, 1)[None]
    _, _, h, w = x.shape
    out = torch.zeros(1, 3, h * 4, w * 4)
    tiles = [(t, l) for t in range(0, h, TILE) for l in range(0, w, TILE)]
    for i, (top, left) in enumerate(tiles, 1):
        bottom, right = min(top + TILE, h), min(left + TILE, w)
        t0, l0 = max(top - PAD, 0), max(left - PAD, 0)
        y = model(x[:, :, t0:min(bottom + PAD, h), l0:min(right + PAD, w)])
        out[:, :, top * 4:bottom * 4, left * 4:right * 4] = y[
            :, :, (top - t0) * 4:(bottom - t0) * 4, (left - l0) * 4:(right - l0) * 4]
        print(f"\rtile {i}/{len(tiles)}", end="", file=sys.stderr, flush=True)
    print(file=sys.stderr)
    arr = (out[0].clamp(0, 1).permute(1, 2, 0).numpy() * 255).round().astype(np.uint8)
    return Image.fromarray(arr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--source", default=SOURCE, help="URL or file path of the photo to upscale")
    args = parser.parse_args()
    src = Path(args.source)
    data = src.read_bytes() if src.exists() else fetch(args.source)
    img = Image.open(io.BytesIO(data))
    print(f"Source {img.width} x {img.height}", file=sys.stderr)
    # The original is 1000px wide; a larger file is the image server's own enlargement, so shrink it
    # back and let the model do the enlarging.
    if img.width > SOURCE_WIDTH:
        img = img.resize((SOURCE_WIDTH, round(img.height * SOURCE_WIDTH / img.width)), Image.LANCZOS)
    big = upscale(load_model(), img)
    if img.mode in ("L", "LA"):
        big = big.convert("L")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for width in WIDTHS:
        height = round(big.height * width / big.width)
        path = OUT_DIR / f"tardigrade-{width}w.webp"
        big.resize((width, height), Image.LANCZOS).save(path, "WEBP", quality=82, method=6)
        print(f"Wrote {path.relative_to(ROOT)} ({width} x {height}, {path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
