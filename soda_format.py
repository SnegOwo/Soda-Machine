#!/usr/bin/env python3
"""
Format d'image .soda — Spécification
=====================================
Structure binaire d'un fichier .soda :
  [0:4]   Magic bytes  — b"SODA" (4 octets)
  [4:6]   Largeur       — entier 16 bits non signé, big-endian
  [6:8]   Hauteur       — entier 16 bits non signé, big-endian
  [8]     Qualité       — 1 octet (1–100)
  [9:]    Données       — flux RGB quantifié, filtré (Delta horizontal)
                          puis compressé LZMA (preset 9)

Quantification (perte) :
  Selon le facteur de qualité (1–100), les valeurs RGB sont divisées par
  un pas de quantification, arrondies, puis multipliées par le même pas.
  Cela réduit le nombre de niveaux de couleur distincts, supprimant le
  bruit de fond et améliorant la compressibilité.

  Pas de quantification = max(1, round((101 - quality) * 0.5))

  Qualité   Pas     Niveaux/canal
  ───────   ───     ─────────────
  100        1      256 (aucune perte)
   80       11       24
   50       26       10
    1       50        6

Filtrage Delta horizontal :
  Identique au format .eau — chaque pixel est remplacé par sa différence
  avec le pixel immédiatement à gauche dans la même ligne.

Compression :
  LZMA avec niveau de compression 9 (maximum).
"""

import struct
import lzma
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image

# ── Constantes ──────────────────────────────────────────────────────────────
MAGIC = b"SODA"
LZMA_PRESET = 9
HEADER_SIZE = 9  # 4 (magic) + 2 (width) + 2 (height) + 1 (quality)


# ── Utilitaires de quantification ──────────────────────────────────────────

def _compute_quant_step(quality: int) -> int:
    """
    Calcule le pas de quantification à partir du facteur de qualité (1–100).

    Plus la qualité est basse, plus le pas est grand → plus de perte
    mais meilleure compression.
    """
    quality = max(1, min(100, quality))
    step = max(1, round((101 - quality) * 0.5))
    return step


def _quantize(pixels: np.ndarray, step: int) -> np.ndarray:
    """
    Applique la quantification sur un tableau (H, W, 3) uint8.

    Chaque valeur est arrondie au multiple de `step` le plus proche.
    """
    if step <= 1:
        return pixels.copy()
    # Division entière puis multiplication pour arrondir au step supérieur
    # On utilise la formule : round(x / step) * step
    # On convertit en int16 pour éviter les débordements
    quantized = np.round(pixels.astype(np.float32) / step) * step
    return np.clip(quantized, 0, 255).astype(np.uint8)


# ── Filtrage Delta (identique à .eau) ──────────────────────────────────────

def _apply_horizontal_delta(pixels: np.ndarray) -> np.ndarray:
    """
    Applique le filtre Delta horizontal sur un tableau (H, W, 3) uint8.
    """
    H, W, _ = pixels.shape
    delta = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        delta[y, 0] = pixels[y, 0]
        for x in range(1, W):
            delta[y, x] = (pixels[y, x].astype(np.int16) - pixels[y, x - 1].astype(np.int16)) & 0xFF
    return delta


def _inverse_horizontal_delta(delta: np.ndarray) -> np.ndarray:
    """
    Applique l'inverse du filtre Delta horizontal.
    """
    H, W, _ = delta.shape
    reconstructed = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        reconstructed[y, 0] = delta[y, 0]
        for x in range(1, W):
            reconstructed[y, x] = (reconstructed[y, x - 1].astype(np.uint16) + delta[y, x].astype(np.uint16)) & 0xFF
    return reconstructed


# ── Encodage ────────────────────────────────────────────────────────────────

def encode_soda(input_path: str, output_soda_path: str, quality: int = 80) -> None:
    """
    Encode une image au format .soda avec perte.

    Args:
        input_path:       Chemin de l'image source.
        output_soda_path: Chemin du fichier .soda à créer.
        quality:          Facteur de qualité (1–100, défaut: 80).
                          Plus la valeur est élevée, meilleure est la qualité
                          mais plus le fichier est gros.
    """
    # Charger l'image avec Pillow
    img = Image.open(input_path).convert("RGB")
    width, height = img.size

    # Convertir en numpy array (H, W, 3) uint8
    pixels = np.array(img, dtype=np.uint8)

    # Calculer le pas de quantification
    quant_step = _compute_quant_step(quality)

    # Appliquer la quantification (perte)
    quantized = _quantize(pixels, quant_step)

    # Appliquer le filtre Delta horizontal
    filtered = _apply_horizontal_delta(quantized)

    # Sérialiser en bytes (H × W × 3 octets)
    raw_bytes = filtered.tobytes()

    # Compresser avec LZMA preset 9
    compressed = lzma.compress(raw_bytes, preset=LZMA_PRESET)

    # Assembler le fichier .soda
    with open(output_soda_path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack(">H", width))
        f.write(struct.pack(">H", height))
        f.write(struct.pack("B", quality))
        f.write(compressed)

    # Taille de l'image quantifiée théorique (taille RAW)
    quantized_raw_size = width * height * 3

    print(f"[SODA] Encodé : {input_path} → {output_soda_path}")
    print(f"       Dimensions : {width}×{height}")
    print(f"       Qualité : {quality} (pas de quantification : {quant_step})")
    print(f"       Taille compressée : {len(compressed)} octets")
    print(f"       Taille RAW (quantifié) : {quantized_raw_size} octets")
    print(f"       Ratio : {len(compressed) / quantized_raw_size * 100:.2f}%")


# ── Décodage ────────────────────────────────────────────────────────────────

def decode_soda(input_soda_path: str) -> Image.Image:
    """
    Décode un fichier .soda et retourne une image PIL.

    Args:
        input_soda_path: Chemin du fichier .soda.

    Returns:
        Une instance PIL.Image (mode RGB).
    """
    with open(input_soda_path, "rb") as f:
        data = f.read()

    # Valider le magic number
    if data[:4] != MAGIC:
        raise ValueError(f"Magic number invalide : {data[:4]!r} (attendu {MAGIC!r})")

    # Lire les métadonnées
    width = struct.unpack(">H", data[4:6])[0]
    height = struct.unpack(">H", data[6:8])[0]
    quality = data[8]

    # Décompresser
    compressed = data[9:]
    try:
        raw_bytes = lzma.decompress(compressed)
    except lzma.LZMAError as e:
        raise ValueError(f"Erreur de décompression LZMA : {e}")

    # Vérifier la taille
    expected_size = width * height * 3
    if len(raw_bytes) != expected_size:
        raise ValueError(
            f"Taille de données incohérente : {len(raw_bytes)} octets "
            f"(attendu {expected_size} pour {width}×{height}×3)"
        )

    # Reconstruire l'image
    delta = np.frombuffer(raw_bytes, dtype=np.uint8).reshape((height, width, 3))
    pixels = _inverse_horizontal_delta(delta)

    quant_step = _compute_quant_step(quality)
    print(f"[SODA] Décodé : {input_soda_path}")
    print(f"       Dimensions : {width}×{height}")
    print(f"       Qualité : {quality} (pas de quantification : {quant_step})")

    return Image.fromarray(pixels, mode="RGB")


# ── CLI simple ──────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Outil de conversion .soda (lossy)")
    parser.add_argument("action", choices=["encode", "decode"], help="Action à effectuer")
    parser.add_argument("input", help="Fichier d'entrée")
    parser.add_argument("output", help="Fichier de sortie")
    parser.add_argument("--quality", "-q", type=int, default=80, help="Qualité (1–100, défaut: 80)")
    args = parser.parse_args()

    if args.action == "encode":
        encode_soda(args.input, args.output, quality=args.quality)
    else:
        img = decode_soda(args.input)
        img.save(args.output)
        print(f"[SODA] Décodé : {args.input} → {args.output}")


if __name__ == "__main__":
    main()