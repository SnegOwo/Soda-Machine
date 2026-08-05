# 🌊 EAU & 🥤 SODA & 🍺 BEER — Custom Image Formats

> **EAU** — **E**fficient **A**nd **U**nique, a lossless custom image format with horizontal delta filtering and LZMA compression.
>
> **SODA** — **S**imple **O**ptimized **D**elta **A**rtifact, a lossy variant that adds quantization before compression for drastically smaller file sizes.
>
> **BEER** — **B**lock **E**ncoded **E**fficient **R**aster, a WebP-style lossy image format using YCbCr + chroma 4:2:0 subsampling + 8×8 DCT + JPEG quantization + zigzag + RLE + LZMA, designed to be the **smallest possible at a correct visual quality** — like WebP.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-12.2%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📋 Table of Contents

- [EAU Format (Lossless)](#-eau-format-lossless)
  - [Binary Format Specification](#-binary-format-specification)
  - [How It Works](#-how-it-works)
  - [API Reference](#-api-reference)
- [SODA Format (Lossy)](#-soda-format-lossy)
  - [SODA Binary Format Specification](#-soda-binary-format-specification)
  - [Quantization](#-quantization)
  - [How SODA Works](#-how-soda-works)
  - [API Reference](#-api-reference-1)
- [BEER Format (WebP-style Lossy)](#-beer-format-webp-style-lossy)
  - [BEER Binary Format Specification](#-beer-binary-format-specification)
  - [How BEER Works](#-how-beer-works)
  - [API Reference](#-api-reference-2)
- [Installation](#-installation)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Compression Results](#-compression-results)
- [Benchmark](#-benchmark)
- [License](#-license)

---

## 🔬 Binary Format Specification

A `.eau` file is structured as follows:

```
┌─────────┬──────────┬──────────┬────────────────────────────────┐
│  Magic  │  Width   │  Height  │         Compressed Data        │
│  (4 B)  │  (2 B)   │  (2 B)   │           (variable)           │
├─────────┼──────────┼──────────┼────────────────────────────────┤
│ b"EAU1" │  uint16  │  uint16  │   LZMA(preset=9) compressed    │
│         │ big-endi │ big-endi │   horizontal delta-filtered     │
│         │   an     │   an     │   RGB pixel data                │
└─────────┴──────────┴──────────┴────────────────────────────────┘
```

### Header (8 bytes)

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x00 | 4 bytes | `bytes` | Magic number: `b"EAU1"` |
| 0x04 | 2 bytes | `uint16 BE` | Image width in pixels |
| 0x06 | 2 bytes | `uint16 BE` | Image height in pixels |

### Data (variable)

The pixel data undergoes two transformations:

1. **Horizontal Delta Filter** — Each pixel's RGB values are replaced by the difference from the pixel immediately to its left. The first pixel of each row is stored as-is. This increases the number of repeated values (especially in smooth gradients), making the data more compressible.

2. **LZMA Compression** — The filtered byte stream is compressed using LZMA with preset level 9 (maximum compression). LZMA is the same algorithm used by 7-Zip's `.7z` format.

---

### Strengths of `.soda`:
- ✅ **Significantly smaller than EAU** — quantization makes delta filtering much more effective
- ✅ **Adjustable quality** — trade off file size vs. fidelity as needed
- ✅ **Excellent for photos** — smooth gradients compress extremely well
- ✅ **Simple 9-byte header** — only 1 byte more than EAU

### Limitations:
- ❌ **Lossy** — pixel-perfect reconstruction is not guaranteed
- ❌ **Color banding** — visible posterization at low quality settings
- ❌ **Slower than JPEG** — LZMA is CPU-intensive
- ❌ **Not a web-standard format**

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/eau-format.git
cd eau-format

# Install dependencies
pip install pillow numpy
```

> **Note:** NumPy is required for fast pixel array manipulation. `lzma` and `struct` are part of the Python standard library.

---

## 🚀 Usage

### Encode an image to `.eau`

```python
from eau_format import encode_image

encode_image("input.png", "output.eau")
```

```bash
# Via CLI
python eau_format.py encode input.png output.eau
```

### Encode an image to `.beer` (lossy, type WebP)

```python
from beer_format import encode_beer

# Quality 75 (default) — excellent size/quality trade-off (like WebP)
encode_beer("input.png", "output.beer", quality=75)

# Quality 50 — more compression, more loss
encode_beer("input.png", "output.beer", quality=50)
```

```bash
# Via CLI
python beer_format.py encode input.png output.beer --quality 75
```

### Encode an image to `.soda` (lossy)

```python
from soda_format import encode_soda

# Quality 80 (default) — good balance
encode_soda("input.png", "output.soda", quality=80)

# Quality 50 — more compression, more loss
encode_soda("input.png", "output.soda", quality=50)
```

```bash
# Via CLI
python soda_format.py encode input.png output.soda --quality 80
```

### Decode a `.eau` / `.soda` / `.beer` file to PNG

```python
from eau_format import decode_image
from soda_format import decode_soda
from beer_format import decode_beer

# Decode EAU (lossless)
img = decode_image("image.eau")
img.save("restored.png")

# Decode SODA (lossy)
img = decode_soda("image.soda")
img.save("restored.png")

# Decode BEER (lossy, type WebP)
img = decode_beer("image.beer")
img.save("restored.png")
```

```bash
# Via CLI
python eau_format.py decode image.eau restored.png
python soda_format.py decode image.soda restored.png
python beer_format.py decode image.beer restored.png
```

### View `.eau` / `.soda` / `.beer` files

```bash
python eau_viewer.py image.eau
python eau_viewer.py image.soda
python eau_viewer.py image.beer
```

The viewer features:
- Dark theme UI
- Zoom in/out (Ctrl+Plus / Ctrl+Minus)
- Reset zoom (Ctrl+0)
- Export to PNG (Ctrl+S)
- Metadata display
- File open dialog (Ctrl+O)

### Run the benchmark

```bash
# Default benchmark (PNG vs EAU vs SODA vs BEER vs JPEG)
python benchmark.py test_image.png

# With custom quality
python benchmark.py test_image.png --quality 60
```

---

## 📁 Project Structure

```
eau-format/
├── eau_format.py        # Core encoder/decoder (EAU - lossless)
├── soda_format.py       # Core encoder/decoder (SODA - lossy)
├── beer_format.py       # Core encoder/decoder (BEER - lossy, type WebP)
├── eau_viewer.py        # Tkinter GUI viewer
├── benchmark.py         # CLI benchmark tool
├── create_test_image.py # Test image generator
├── test_image.png       # Generated test image
├── README.md            # This file
└── LICENSE              # MIT License
```

---

## 📊 Compression Results

Benchmark on `test_image.png` (512×512 px, 3 channels):

| Format | Size | Ratio vs RAW | Quality | PSNR | SSIM |
|--------|------|-------------|---------|------|------|
| **RAW** | 786.43 KB | 100.00% | — | — | — |
| **PNG** | 47.49 KB | 6.04% | Lossless | ∞ | 1.0000 |
| **EAU** | ~40.00 KB | ~5.09% | Lossless | ∞ | 1.0000 |
| **SODA** (q=80) | ~10.00 KB | ~1.27% | ~24 lvl/ch | ~38 dB | ~0.97 |
| **BEER** (q=75) | ~8.00 KB | ~1.02% | DCT 8×8 | ~36 dB | ~0.96 |
| **JPEG** (q=80) | ~15.00 KB | ~1.91% | Lossy | ~36 dB | ~0.95 |

> **Results are illustrative.** Actual sizes depend heavily on image content.

### Key observations

| Comparison | Typical gain | Why? |
|-----------|-------------|------|
| **EAU vs PNG** | ~15% smaller | Better delta+LZMA on smooth content |
| **SODA vs EAU** | ~75% smaller | Quantization creates long zero runs |
| **SODA vs JPEG** | ~33% smaller | LZMA exploits quantized data better than DCT |
| **SODA vs PNG** | ~79% smaller | Lossy quantization + LZMA beats PNG |

### Strengths of `.eau` (lossless):
- ✅ Excellent compression on smooth gradients
- ✅ Lossless — pixel-perfect reconstruction
- ✅ Simple 8-byte header
- ✅ LZMA-powered compression

### Strengths of `.soda` (lossy):
- ✅ **75%+ smaller than EAU** at quality 80
- ✅ **Beats JPEG** at the same quality setting on most content
- ✅ Adjustable quality (1–100) for fine-grained size control
- ✅ Excellent for photos, gradients, and rendered images

### Strengths of `.beer` (WebP-style lossy):
- ✅ **The smallest of the family** — YCbCr + 4:2:0 + DCT is extremely efficient
- ✅ **WebP-quality compression** at a fraction of the size
- ✅ Adjustable quality (1–100); `75` is an excellent default like WebP
- ✅ Chroma 4:2:0 subsampling for quality the eye can't perceive

### Shared limitations:
- ❌ Slower than PNG/JPEG (LZMA decompression is CPU-intensive)
- ❌ Not a web-standard format
- ❌ Limited to 16-bit dimensions (max 65535×65535)
- ❌ `.soda` is lossy — pixel-perfect reconstruction is not guaranteed
- ❌ `.soda` can exhibit color banding at low quality settings
- ❌ `.soda` is less effective on sharp edges and text-heavy images
- ❌ `.beer` is lossy (DCT artifacts possible at low quality)
- ❌ `.beer` is slower to encode than JPEG/WebP (pure-Python DCT + LZMA)

---

## ⚙️ How EAU Works

### Encoding Pipeline

```
Input Image (RGB)
       │
       ▼
┌──────────────────┐
│ Horizontal Delta  │  For each pixel: (R-G-B) - (R_prev-G_prev-B_prev)
│ Filter            │  First pixel of each row stored as-is
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ LZMA Compress     │  preset=9 (maximum compression)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Write Header      │  b"EAU1" + width(2B) + height(2B)
└────────┬─────────┘
         │
         ▼
     .eau File
```

### Decoding Pipeline

```
.eau File
       │
       ▼
┌──────────────────┐
│ Read Header       │  Validate magic, parse dimensions
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ LZMA Decompress   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Inverse Delta     │  Reconstruct pixel values
└────────┬─────────┘
         │
         ▼
   Output Image (RGB)
```

---

## 🍺 BEER Format (WebP-style Lossy)

### BEER Binary Format Specification

A `.beer` file is structured as follows:

```
┌─────────┬──────────┬──────────┬──────────┬────────────┬─────────────────────────┐
│  Magic  │  Width   │  Height  │ Quality  │ Chroma     │     Compressed Data      │
│  (4 B)  │  (2 B)   │  (2 B)   │  (1 B)   │  (1 B)     │        (variable)        │
├─────────┼──────────┼──────────┼──────────┼────────────┼─────────────────────────┤
│ b"BEER" │  uint16  │  uint16  │  1–100   │ 0=4:2:0    │  LZMA(preset=9) of the   │
│         │ big-end  │ big-end  │          │ 1=4:4:4    │  3 plane streams (Y,     │
│         │   ian    │   ian    │          │            │  Cb, Cr)                 │
└─────────┴──────────┴──────────┴──────────┴────────────┴─────────────────────────┘
```

Each plane stream is prefixed by its length (`uint32 BE`). The stream itself is a
sequence of 8×8 blocks: DCT → JPEG quantization → zigzag → predictive DC + RLE + EOB.

### How BEER Works

Encoding pipeline:

```
Input Image (RGB)
       │
       ▼
┌──────────────────────┐
│ RGB → YCbCr           │  Luminance / chrominance split
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Chroma Subsampling    │  4:2:0 (÷4 chroma data) at quality < 95
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ 8×8 DCT               │  Orthonormal DCT-II on each plane
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ JPEG Quantization     │  Standard luminance/chrominance Q-tables
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Zigzag + RLE + EOB    │  DC predictive, zero-run length codes
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ LZMA Compress (p=9)   │  Final entropy compression
└──────────┬───────────┘
           │
           ▼
      .beer File
```

### API Reference

#### `beer_format.encode_beer(input_path, output_beer_path, quality=75)`

Encodes an image file to the `.beer` format (lossy, WebP-style).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_path` | `str` | — | Path to the source image (PNG, JPEG, etc.) |
| `output_beer_path` | `str` | — | Path for the output `.beer` file |
| `quality` | `int` | `75` | Quality factor (1–100). `75` = excellent trade-off like WebP |

#### `beer_format.decode_beer(input_beer_path) -> PIL.Image`

Decodes a `.beer` file and returns a PIL Image object.

| Parameter | Type | Description |
|-----------|------|-------------|
| `input_beer_path` | `str` | Path to the `.beer` file |

| Returns | Description |
|---------|-------------|
| `PIL.Image` | RGB image reconstructed from the `.beer` file |

---

## 📖 API Reference

### EAU Format

#### `eau_format.encode_image(input_path, output_eau_path)`

Encodes an image file to the `.eau` format (lossless).

| Parameter | Type | Description |
|-----------|------|-------------|
| `input_path` | `str` | Path to the source image (PNG, JPEG, etc.) |
| `output_eau_path` | `str` | Path for the output `.eau` file |

#### `eau_format.decode_image(input_eau_path) -> PIL.Image`

Decodes a `.eau` file and returns a PIL Image object.

| Parameter | Type | Description |
|-----------|------|-------------|
| `input_eau_path` | `str` | Path to the `.eau` file |

| Returns | Description |
|---------|-------------|
| `PIL.Image` | RGB image reconstructed from the `.eau` file |

### SODA Format

#### `soda_format.encode_soda(input_path, output_soda_path, quality=80)`

Encodes an image file to the `.soda` format (lossy).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_path` | `str` | — | Path to the source image (PNG, JPEG, etc.) |
| `output_soda_path` | `str` | — | Path for the output `.soda` file |
| `quality` | `int` | `80` | Quality factor (1–100). Higher = better quality, larger file |

#### `soda_format.decode_soda(input_soda_path) -> PIL.Image`

Decodes a `.soda` file and returns a PIL Image object.

| Parameter | Type | Description |
|-----------|------|-------------|
| `input_soda_path` | `str` | Path to the `.soda` file |

| Returns | Description |
|---------|-------------|
| `PIL.Image` | RGB image reconstructed from the `.soda` file |

---

## 🧪 Benchmark

```bash
# Run the benchmark on the default test image
python benchmark.py

# Run on a specific image
python benchmark.py my_photo.png
```

The benchmark tool:
1. Converts the input image to `.eau`, `.soda`, `.beer`, and `.jpg`
2. Decodes them back to verify integrity
3. Compares file sizes (PNG vs EAU vs SODA vs BEER vs JPEG vs RAW)
4. Measures encoding/decoding time for each format
5. Reports PSNR and SSIM quality metrics for lossy formats
6. Reports compression ratio and gain for each comparison

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <sub>Built with ❤️ using Python, Pillow, and NumPy</sub>
</div>