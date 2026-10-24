# 🥤 Soda Machine — Custom Image Formats (EAU • SODA • BEER)

> **EAU** — **E**fficient **A**nd **U**nique : lossless format (horizontal delta + LZMA).
>
> **SODA** — **S**imple **O**ptimized **D**elta **A**rtifact : lossy format (quantization + LZMA), much smaller than EAU.
>
> **BEER** — **B**lock **E**ncoded **E**fficient **R**aster : lossy WebP-style format (YCbCr 4:2:0 + 8×8 DCT + LZMA), the smallest of the family.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-12.2%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
[![Release](https://img.shields.io/github/v/release/SnegOwo/Soda-Machine)](https://github.com/SnegOwo/Soda-Machine/releases/latest)

---

## 📖 About

**Soda Machine** is a collection of experimental, custom image compression formats written in Python. It demonstrates delta filtering, quantization, DCT, and LZMA compression through three codecs: **EAU** (lossless), **SODA** (lossy), and **BEER** (lossy, WebP-style).

🎬 This project was made for my own YouTube video (in French):  
[▶️ Watch the video](https://youtu.be/KI-OUNkx_Og?si=3UaXkhH8iG87iPvW)

---

## 📦 Installation

```bash
pip install pillow numpy
```

---

## 🚀 Usage

### Command line

```bash
# Encode
python eau_format.py encode input.png output.eau
python soda_format.py encode input.png output.soda --quality 80
python beer_format.py encode input.png output.beer --quality 75

# Decode
python eau_format.py decode image.eau restored.png
python soda_format.py decode image.soda restored.png
python beer_format.py decode image.beer restored.png
```

### In Python

```python
from eau_format import encode_image, decode_image
from soda_format import encode_soda, decode_soda
from beer_format import encode_beer, decode_beer

encode_image("input.png", "output.eau")
encode_soda("input.png", "output.soda", quality=80)
encode_beer("input.png", "output.beer", quality=75)

img = decode_image("image.eau")
img.save("restored.png")
```

### Graphical viewer

```bash
python eau_viewer.py image.eau
```

Features: zoom, PNG export, format conversion, metadata.

### Benchmark

```bash
python benchmark.py test_image.png --quality 60
```

Compares PNG / EAU / SODA / BEER / JPEG (size, PSNR, SSIM, time).

---

## 📁 Structure

```
├── eau_format.py        # Encode/decode EAU (lossless)
├── soda_format.py       # Encode/decode SODA (lossy)
├── beer_format.py       # Encode/decode BEER (lossy, WebP-style)
├── eau_viewer.py        # Tkinter viewer
├── benchmark.py         # Compression benchmark
├── create_test_image.py # Test image generator
├── build_exe.py         # Executable build (PyInstaller)
├── dist/                # Pre-compiled executables (not committed)
├── GUIDE.md             # Detailed .eau format guide (French)
├── LICENSE
└── README.md
```

---

## 📊 Formats

| Format | Lossy | Compression | Best for |
|--------|-------|-------------|----------|
| **EAU** | No | Delta + LZMA | Images where every pixel must be preserved |
| **SODA** | Yes | Quantization + Delta + LZMA | Photos, gradients (≈75% smaller than EAU) |
| **BEER** | Yes | YCbCr 4:2:0 + DCT 8×8 + LZMA | Smallest possible file (WebP-style) |

Common limits: max 65535×65535 dimensions, slower than PNG/JPEG (LZMA), non-standard web formats.

---

## 📄 License

Under the [MIT License](LICENSE).

<div align="center">
  <sub>Built with ❤️ using Python, Pillow, and NumPy</sub><br>
  <sub>Repository: <a href="https://github.com/SnegOwo/Soda-Machine">https://github.com/SnegOwo/Soda-Machine</a></sub>
</div>
