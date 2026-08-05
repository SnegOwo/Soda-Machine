# 🌊 EAU & 🥤 SODA & 🍺 BEER — Custom Image Formats

> **EAU** — **E**fficient **A**nd **U**nique : format lossless (delta horizontal + LZMA).
>
> **SODA** — **S**imple **O**ptimized **D**elta **A**rtifact : format lossy (quantization + LZMA), bien plus petit qu'EAU.
>
> **BEER** — **B**lock **E**ncoded **E**fficient **R**aster : format lossy style WebP (YCbCr 4:2:0 + DCT 8×8 + LZMA), le plus petit de la famille.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-12.2%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📦 Installation

```bash
pip install pillow numpy
```

---

## 🚀 Usage

### En ligne de commande

```bash
# Encoder
python eau_format.py encode input.png output.eau
python soda_format.py encode input.png output.soda --quality 80
python beer_format.py encode input.png output.beer --quality 75

# Décoder
python eau_format.py decode image.eau restored.png
python soda_format.py decode image.soda restored.png
python beer_format.py decode image.beer restored.png
```

### En Python

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

### Visionneuse graphique

```bash
python eau_viewer.py image.eau
```

Fonctionnalités : zoom, export PNG, conversion entre formats, métadonnées.

### Benchmark

```bash
python benchmark.py test_image.png --quality 60
```

Compare PNG / EAU / SODA / BEER / JPEG (taille, PSNR, SSIM, temps).

---

## 📁 Structure

```
├── eau_format.py        # Encodage/décodage EAU (lossless)
├── soda_format.py       # Encodage/décodage SODA (lossy)
├── beer_format.py       # Encodage/décodage BEER (lossy, style WebP)
├── eau_viewer.py        # Visionneuse Tkinter
├── benchmark.py         # Benchmark de compression
├── create_test_image.py # Générateur d'image de test
├── build_exe.py         # Build de l'exécutable (PyInstaller)
├── dist/                # Exécutables pré-compilés
└── README.md
```

---

## 📊 Formats

| Format | Perte | Compression | Idéal pour |
|--------|-------|-------------|------------|
| **EAU** | Lossless | Delta + LZMA | Images où chaque pixel doit être préservé |
| **SODA** | Lossy | Quantization + Delta + LZMA | Photos, dégradés (≈75% plus petit qu'EAU) |
| **BEER** | Lossy | YCbCr 4:2:0 + DCT 8×8 + LZMA | Le plus petit possible (style WebP) |

Limites communes : dimensions max 65535×65535, plus lent que PNG/JPEG (LZMA), formats non standard du web.

---

## 📄 License

Sous licence [MIT](LICENSE).

<div align="center">
  <sub>Built with ❤️ using Python, Pillow, and NumPy</sub>
</div>