#!/usr/bin/env python3
"""
Benchmark de compression — PNG vs EAU (Lossless) vs SODA (Lossy) vs BEER (Lossy) vs JPEG (Lossy).

Usage :
    python benchmark.py [image.png] [--quality N]

Compare la taille d'une image PNG avec ses versions encodées en .eau, .soda, .beer et .jpg
et affiche le gain de compression en pourcentage.

Si aucun argument n'est fourni, utilise 'test_image.png' par défaut.
"""

import os
import sys
import time
import argparse
from pathlib import Path

from PIL import Image
import numpy as np

from eau_format import encode_image, decode_image
from soda_format import encode_soda, decode_soda
from beer_format import encode_beer, decode_beer

# ── Couleurs ANSI (Windows-friendly) ───────────────────────────────────────
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"
    # Désactiver les couleurs si non supporté
    if os.name == "nt" and not os.environ.get("TERM"):
        HEADER = BLUE = CYAN = GREEN = YELLOW = RED = BOLD = UNDERLINE = ""
        END = ""


def format_size(size: int) -> str:
    """Formate une taille en octets avec l'unité appropriée."""
    if size < 1024:
        return f"{size} o"
    elif size < 1024 * 1024:
        return f"{size/1024:.2f} Ko"
    else:
        return f"{size/1024/1024:.2f} Mo"


def compute_psnr(original: np.ndarray, decoded: np.ndarray) -> float:
    """Calcule le PSNR (Peak Signal-to-Noise Ratio) entre deux images RGB."""
    mse = np.mean((original.astype(np.float32) - decoded.astype(np.float32)) ** 2)
    if mse == 0:
        return float("inf")
    max_pixel = 255.0
    return 20 * np.log10(max_pixel / np.sqrt(mse))


def compute_ssim(original: np.ndarray, decoded: np.ndarray) -> float:
    """
    Calcule une approximation du SSIM (Structural Similarity Index) entre deux images.

    Il s'agit d'une version simplifiée pour un usage de benchmark.
    """
    # Constantes SSIM
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    # Moyennes
    mu_x = np.mean(original, axis=(0, 1))
    mu_y = np.mean(decoded, axis=(0, 1))

    # Variances et covariance
    sigma_x_sq = np.var(original, axis=(0, 1))
    sigma_y_sq = np.var(decoded, axis=(0, 1))
    sigma_xy = np.mean((original - mu_x) * (decoded - mu_y), axis=(0, 1))

    # SSIM par canal
    ssim = (2 * mu_x * mu_y + C1) * (2 * sigma_xy + C2)
    ssim /= (mu_x ** 2 + mu_y ** 2 + C1) * (sigma_x_sq + sigma_y_sq + C2)

    return float(np.mean(ssim))


def run_benchmark(input_path: str, soda_quality: int = 80):
    """Exécute le benchmark complet pour une image donnée."""
    input_path = Path(input_path)

    if not input_path.exists():
        print(f"{Colors.RED}Erreur : le fichier '{input_path}' n'existe pas.{Colors.END}")
        sys.exit(1)

    # ── Informations sur l'image source ────────────────────────────────────
    img = Image.open(input_path).convert("RGB")
    width, height = img.size
    n_pixels = width * height
    raw_size = n_pixels * 3  # Taille non compressée (RGB, 3 octets/pixel)

    png_size = input_path.stat().st_size
    pixels_np = np.array(img, dtype=np.uint8)

    # ── Chemins de sortie ─────────────────────────────────────────────────
    eau_path = input_path.with_suffix(".eau")
    soda_path = input_path.with_suffix(".soda")
    beer_path = input_path.with_suffix(".beer")
    jpg_path = input_path.with_suffix(".jpg")

    # ── En-tête ────────────────────────────────────────────────────────────
    print(f"\n{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}║    Benchmark de compression — PNG vs EAU vs SODA vs BEER    ║{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}╚══════════════════════════════════════════════════════════╝{Colors.END}\n")

    print(f"{Colors.BOLD}Fichier source :{Colors.END} {input_path.name}")
    print(f"{Colors.BOLD}Dimensions :{Colors.END}     {width} × {height} px ({n_pixels:,} pixels)")
    print(f"{Colors.BOLD}Qualité SODA/BEER :{Colors.END}   {soda_quality}")
    print(f"{'─' * 55}\n")

    # ══════════════════════════════════════════════════════════════════════
    #  1. Encodage EAU (lossless)
    # ══════════════════════════════════════════════════════════════════════
    print(f"{Colors.BOLD}{Colors.BLUE}[1/5] Encodage EAU (lossless)...{Colors.END}")
    t_start = time.perf_counter()
    encode_image(str(input_path), str(eau_path))
    t_eau_encode = time.perf_counter() - t_start

    eau_size = eau_path.stat().st_size

    # Décodage EAU (vérification)
    t_start = time.perf_counter()
    decoded_eau = decode_image(str(eau_path))
    t_eau_decode = time.perf_counter() - t_start

    # Vérification pixel-perfect
    eau_diff_pixels = 0
    for y in range(height):
        for x in range(width):
            if img.getpixel((x, y)) != decoded_eau.getpixel((x, y)):
                eau_diff_pixels += 1

    eau_psnr = compute_psnr(pixels_np, np.array(decoded_eau, dtype=np.uint8))
    eau_ssim = compute_ssim(pixels_np, np.array(decoded_eau, dtype=np.uint8))

    # ══════════════════════════════════════════════════════════════════════
    #  2. Encodage SODA (lossy)
    # ══════════════════════════════════════════════════════════════════════
    print(f"{Colors.BOLD}{Colors.YELLOW}[2/5] Encodage SODA (lossy, quality={soda_quality})...{Colors.END}")
    t_start = time.perf_counter()
    encode_soda(str(input_path), str(soda_path), quality=soda_quality)
    t_soda_encode = time.perf_counter() - t_start

    soda_size = soda_path.stat().st_size

    # Décodage SODA
    t_start = time.perf_counter()
    decoded_soda = decode_soda(str(soda_path))
    t_soda_decode = time.perf_counter() - t_start

    # Analyse de perte SODA
    soda_diff_pixels = 0
    for y in range(height):
        for x in range(width):
            if img.getpixel((x, y)) != decoded_soda.getpixel((x, y)):
                soda_diff_pixels += 1

    soda_pixels_np = np.array(decoded_soda, dtype=np.uint8)
    soda_psnr = compute_psnr(pixels_np, soda_pixels_np)
    soda_ssim = compute_ssim(pixels_np, soda_pixels_np)

    # ══════════════════════════════════════════════════════════════════════
    #  3. Encodage BEER (lossy, type WebP)
    # ══════════════════════════════════════════════════════════════════════
    print(f"{Colors.BOLD}{Colors.GREEN}[3/5] Encodage BEER (lossy, quality={soda_quality})...{Colors.END}")
    t_start = time.perf_counter()
    encode_beer(str(input_path), str(beer_path), quality=soda_quality)
    t_beer_encode = time.perf_counter() - t_start

    beer_size = beer_path.stat().st_size

    # Décodage BEER
    t_start = time.perf_counter()
    decoded_beer = decode_beer(str(beer_path))
    t_beer_decode = time.perf_counter() - t_start

    # Analyse de perte BEER
    beer_diff_pixels = 0
    beer_pixels_np = np.array(decoded_beer, dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            if img.getpixel((x, y)) != decoded_beer.getpixel((x, y)):
                beer_diff_pixels += 1

    beer_psnr = compute_psnr(pixels_np, beer_pixels_np)
    beer_ssim = compute_ssim(pixels_np, beer_pixels_np)

    # ══════════════════════════════════════════════════════════════════════
    #  4. Encodage JPEG (lossy standard)
    # ══════════════════════════════════════════════════════════════════════
    jpg_quality = soda_quality  # Même qualité pour comparaison équitable
    print(f"{Colors.BOLD}{Colors.GREEN}[4/5] Encodage JPEG (lossy, quality={jpg_quality})...{Colors.END}")
    t_start = time.perf_counter()
    # JPEG utilise une échelle de qualité différente (Pillow: 1-95, on garde la même)
    img.save(str(jpg_path), "JPEG", quality=jpg_quality, optimize=True)
    t_jpeg_encode = time.perf_counter() - t_start

    jpg_size = jpg_path.stat().st_size

    # Décodage JPEG
    t_start = time.perf_counter()
    decoded_jpeg = Image.open(jpg_path).convert("RGB")
    t_jpeg_decode = time.perf_counter() - t_start

    # Analyse de perte JPEG
    jpeg_diff_pixels = 0
    jpeg_pixels_np = np.array(decoded_jpeg, dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            if img.getpixel((x, y)) != decoded_jpeg.getpixel((x, y)):
                jpeg_diff_pixels += 1

    jpeg_psnr = compute_psnr(pixels_np, jpeg_pixels_np)
    jpeg_ssim = compute_ssim(pixels_np, jpeg_pixels_np)

    # ══════════════════════════════════════════════════════════════════════
    #  5. Résumé
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n{Colors.BOLD}[5/5] Analyse des résultats...{Colors.END}")

    # ── Tableau des résultats ──────────────────────────────────────────────
    print(f"\n{Colors.BOLD}{'=' * 75}{Colors.END}")
    print(f"{Colors.BOLD}{'RÉSULTATS':^75}{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 75}{Colors.END}")

    # Ligne d'en-tête
    print(f"{'Format':<12} {'Taille':<14} {'Ratio vs RAW':<14} {'Qualité':<14} {'PSNR':<12} {'SSIM':<12}")
    print(f"{'─' * 12} {'─' * 14} {'─' * 14} {'─' * 14} {'─' * 12} {'─' * 12}")

    # Ligne RAW
    print(f"{'RAW':<12} {format_size(raw_size):<14} {'100%':<14} {'—':<14} {'—':<12} {'—':<12}")

    # Ligne PNG
    png_ratio = png_size / raw_size * 100
    print(f"{'PNG':<12} {format_size(png_size):<14} {png_ratio:>6.2f}%{'':<8} {'lossless':<14} {'∞':<12} {'1.0000':<12}")

    # Ligne EAU
    eau_ratio = eau_size / raw_size * 100
    eau_lossless = "✓" if eau_diff_pixels == 0 else "✗"
    print(f"{'EAU':<12} {format_size(eau_size):<14} {eau_ratio:>6.2f}%{'':<8} {'lossless ' + eau_lossless:<14} {eau_psnr:>8.2f}  {'':<2} {eau_ssim:>6.4f}  ")

    # Ligne SODA
    soda_ratio = soda_size / raw_size * 100
    soda_loss_str = f"{soda_diff_pixels:,} px diff"
    print(f"{'SODA':<12} {format_size(soda_size):<14} {soda_ratio:>6.2f}%{'':<8} {soda_loss_str:<14} {soda_psnr:>8.2f}  {'':<2} {soda_ssim:>6.4f}  ")

    # Ligne BEER
    beer_ratio = beer_size / raw_size * 100
    beer_loss_str = f"{beer_diff_pixels:,} px diff"
    print(f"{'BEER':<12} {format_size(beer_size):<14} {beer_ratio:>6.2f}%{'':<8} {beer_loss_str:<14} {beer_psnr:>8.2f}  {'':<2} {beer_ssim:>6.4f}  ")

    # Ligne JPEG
    jpeg_ratio = jpg_size / raw_size * 100
    jpeg_loss_str = f"{jpeg_diff_pixels:,} px diff"
    print(f"{'JPEG':<12} {format_size(jpg_size):<14} {jpeg_ratio:>6.2f}%{'':<8} {jpeg_loss_str:<14} {jpeg_psnr:>8.2f}  {'':<2} {jpeg_ssim:>6.4f}  ")

    print(f"{'─' * 75}")

    # ── Gains / Pertes ─────────────────────────────────────────────────────
    print(f"\n{Colors.BOLD}Comparaison des gains :{Colors.END}")

    # EAU vs PNG
    if eau_size < png_size:
        eau_gain = (1 - eau_size / png_size) * 100
        print(f"  {Colors.GREEN}EAU vs PNG    : {Colors.BOLD}{eau_gain:+.2f}%{Colors.END} (réduction)")
    else:
        eau_perte = (eau_size / png_size - 1) * 100
        print(f"  {Colors.YELLOW}EAU vs PNG    : {Colors.BOLD}{eau_perte:+.2f}%{Colors.END} (plus gros)")

    # SODA vs PNG
    if soda_size < png_size:
        soda_gain = (1 - soda_size / png_size) * 100
        print(f"  {Colors.GREEN}SODA vs PNG   : {Colors.BOLD}{soda_gain:+.2f}%{Colors.END} (réduction)")
    else:
        soda_perte = (soda_size / png_size - 1) * 100
        print(f"  {Colors.YELLOW}SODA vs PNG   : {Colors.BOLD}{soda_perte:+.2f}%{Colors.END} (plus gros)")

    # SODA vs EAU
    if soda_size < eau_size:
        soda_vs_eau_gain = (1 - soda_size / eau_size) * 100
        print(f"  {Colors.GREEN}SODA vs EAU   : {Colors.BOLD}{soda_vs_eau_gain:+.2f}%{Colors.END} (réduction)")
    else:
        soda_vs_eau_perte = (soda_size / eau_size - 1) * 100
        print(f"  {Colors.YELLOW}SODA vs EAU   : {Colors.BOLD}{soda_vs_eau_perte:+.2f}%{Colors.END} (plus gros)")

    # BEER vs PNG
    if beer_size < png_size:
        beer_gain = (1 - beer_size / png_size) * 100
        print(f"  {Colors.GREEN}BEER vs PNG   : {Colors.BOLD}{beer_gain:+.2f}%{Colors.END} (réduction)")
    else:
        beer_perte = (beer_size / png_size - 1) * 100
        print(f"  {Colors.YELLOW}BEER vs PNG   : {Colors.BOLD}{beer_perte:+.2f}%{Colors.END} (plus gros)")

    # BEER vs EAU
    if beer_size < eau_size:
        beer_vs_eau_gain = (1 - beer_size / eau_size) * 100
        print(f"  {Colors.GREEN}BEER vs EAU   : {Colors.BOLD}{beer_vs_eau_gain:+.2f}%{Colors.END} (réduction)")
    else:
        beer_vs_eau_perte = (beer_size / eau_size - 1) * 100
        print(f"  {Colors.YELLOW}BEER vs EAU   : {Colors.BOLD}{beer_vs_eau_perte:+.2f}%{Colors.END} (plus gros)")

    # BEER vs SODA
    if beer_size < soda_size:
        beer_vs_soda_gain = (1 - beer_size / soda_size) * 100
        print(f"  {Colors.GREEN}BEER vs SODA  : {Colors.BOLD}{beer_vs_soda_gain:+.2f}%{Colors.END} (réduction)")
    else:
        beer_vs_soda_perte = (beer_size / soda_size - 1) * 100
        print(f"  {Colors.YELLOW}BEER vs SODA  : {Colors.BOLD}{beer_vs_soda_perte:+.2f}%{Colors.END} (plus gros)")

    # JPEG vs PNG
    if jpg_size < png_size:
        jpg_gain = (1 - jpg_size / png_size) * 100
        print(f"  {Colors.GREEN}JPEG vs PNG   : {Colors.BOLD}{jpg_gain:+.2f}%{Colors.END} (réduction)")
    else:
        jpg_perte = (jpg_size / png_size - 1) * 100
        print(f"  {Colors.YELLOW}JPEG vs PNG   : {Colors.BOLD}{jpg_perte:+.2f}%{Colors.END} (plus gros)")

    # SODA vs JPEG
    if soda_size < jpg_size:
        soda_vs_jpg_gain = (1 - soda_size / jpg_size) * 100
        print(f"  {Colors.GREEN}SODA vs JPEG  : {Colors.BOLD}{soda_vs_jpg_gain:+.2f}%{Colors.END} (réduction)")
    else:
        soda_vs_jpg_perte = (soda_size / jpg_size - 1) * 100
        print(f"  {Colors.YELLOW}SODA vs JPEG  : {Colors.BOLD}{soda_vs_jpg_perte:+.2f}%{Colors.END} (plus gros)")

    # BEER vs JPEG
    if beer_size < jpg_size:
        beer_vs_jpg_gain = (1 - beer_size / jpg_size) * 100
        print(f"  {Colors.GREEN}BEER vs JPEG  : {Colors.BOLD}{beer_vs_jpg_gain:+.2f}%{Colors.END} (réduction)")
    else:
        beer_vs_jpg_perte = (beer_size / jpg_size - 1) * 100
        print(f"  {Colors.YELLOW}BEER vs JPEG  : {Colors.BOLD}{beer_vs_jpg_perte:+.2f}%{Colors.END} (plus gros)")

    # ── Temps d'exécution ──────────────────────────────────────────────────
    print(f"\n{Colors.BOLD}Performance :{Colors.END}")
    print(f"  {'Format':<10} {'Encodage':<14} {'Décodage':<14}")
    print(f"  {'─' * 10} {'─' * 14} {'─' * 14}")
    print(f"  {'EAU':<10} {t_eau_encode*1000:>8.1f} ms{'':<4} {t_eau_decode*1000:>8.1f} ms")
    print(f"  {'SODA':<10} {t_soda_encode*1000:>8.1f} ms{'':<4} {t_soda_decode*1000:>8.1f} ms")
    print(f"  {'BEER':<10} {t_beer_encode*1000:>8.1f} ms{'':<4} {t_beer_decode*1000:>8.1f} ms")
    print(f"  {'JPEG':<10} {t_jpeg_encode*1000:>8.1f} ms{'':<4} {t_jpeg_decode*1000:>8.1f} ms")

    # ── Vérification d'intégrité ───────────────────────────────────────────
    print(f"\n{Colors.BOLD}Vérification d'intégrité :{Colors.END}")
    if eau_diff_pixels == 0:
        print(f"  {Colors.GREEN}✓ EAU  : Aucune perte — identique pixel pour pixel{Colors.END}")
    else:
        print(f"  {Colors.RED}✗ EAU  : {eau_diff_pixels} pixels différents !{Colors.END}")

    print(f"  {Colors.YELLOW}⚠ SODA : {soda_diff_pixels:,} pixels différents ({soda_diff_pixels/n_pixels*100:.2f}%){Colors.END}")
    print(f"  {Colors.YELLOW}⚠ BEER : {beer_diff_pixels:,} pixels différents ({beer_diff_pixels/n_pixels*100:.2f}%){Colors.END}")
    print(f"  {Colors.YELLOW}⚠ JPEG : {jpeg_diff_pixels:,} pixels différents ({jpeg_diff_pixels/n_pixels*100:.2f}%){Colors.END}")

    # ── Qualité visuelle (PSNR/SSIM) ───────────────────────────────────────
    print(f"\n{Colors.BOLD}Qualité visuelle :{Colors.END}")
    print(f"  {'Format':<10} {'PSNR':<12} {'SSIM':<12} {'Interprétation':<20}")
    print(f"  {'─' * 10} {'─' * 12} {'─' * 12} {'─' * 20}")
    print(f"  {'EAU':<10} {'∞':<12} {'1.0000':<12} {'Parfait (lossless)':<20}")
    print(f"  {'SODA':<10} {soda_psnr:>8.2f}  {'':<2} {soda_ssim:>6.4f}  {'':<2} {'SODA lossy':<20}")
    print(f"  {'BEER':<10} {beer_psnr:>8.2f}  {'':<2} {beer_ssim:>6.4f}  {'':<2} {'BEER lossy (type WebP)':<20}")
    print(f"  {'JPEG':<10} {jpeg_psnr:>8.2f}  {'':<2} {jpeg_ssim:>6.4f}  {'':<2} {'JPEG lossy':<20}")

    # ── Fichiers créés ─────────────────────────────────────────────────────
    print(f"\n{'─' * 75}")
    print(f"Fichiers créés :")
    print(f"  {Colors.BOLD}{eau_path}{Colors.END}  ({format_size(eau_size)})")
    print(f"  {Colors.BOLD}{soda_path}{Colors.END}  ({format_size(soda_size)})")
    print(f"  {Colors.BOLD}{beer_path}{Colors.END}  ({format_size(beer_size)})")
    print(f"  {Colors.BOLD}{jpg_path}{Colors.END}  ({format_size(jpg_size)})")

    print(f"\nPour visualiser un fichier .eau : {Colors.BOLD}python eau_viewer.py {eau_path.name}{Colors.END}")
    print(f"Pour visualiser un fichier .soda: {Colors.BOLD}python eau_viewer.py {soda_path.name}{Colors.END}")
    print(f"Pour visualiser un fichier .beer: {Colors.BOLD}python eau_viewer.py {beer_path.name}{Colors.END}")

    return {
        "png_size": png_size,
        "eau_size": eau_size,
        "soda_size": soda_size,
        "beer_size": beer_size,
        "jpg_size": jpg_size,
        "raw_size": raw_size,
        "soda_psnr": soda_psnr,
        "beer_psnr": beer_psnr,
        "jpeg_psnr": jpeg_psnr,
        "soda_ssim": soda_ssim,
        "beer_ssim": beer_ssim,
        "jpeg_ssim": jpeg_ssim,
        "eau_diff_pixels": eau_diff_pixels,
        "soda_diff_pixels": soda_diff_pixels,
        "beer_diff_pixels": beer_diff_pixels,
        "jpeg_diff_pixels": jpeg_diff_pixels,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark de compression — PNG vs EAU vs SODA vs BEER vs JPEG"
    )
    parser.add_argument("input", nargs="?", default=None,
                        help="Image source (PNG, JPEG, etc.)")
    parser.add_argument("--quality", "-q", type=int, default=80,
                        help="Qualité pour SODA et JPEG (1–100, défaut: 80)")
    args = parser.parse_args()

    # Gestion des arguments
    if args.input:
        input_path = args.input
    else:
        # Chercher test_image.png par défaut
        default = Path("test_image.png")
        if default.exists():
            input_path = str(default)
        else:
            print(f"{Colors.RED}Erreur : aucun fichier spécifié et test_image.png introuvable.{Colors.END}")
            print(f"Usage : python benchmark.py [image.png] [--quality N]")
            sys.exit(1)

    run_benchmark(input_path, soda_quality=args.quality)


if __name__ == "__main__":
    main()