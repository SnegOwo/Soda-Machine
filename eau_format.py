#!/usr/bin/env python3
"""
Format d'image .eau — Spécification
====================================
Structure binaire d'un fichier .eau :
  [0:4]   Magic bytes  — b"EAU1" (4 octets)
  [4:6]   Largeur       — entier 16 bits non signé, big-endian
  [6:8]   Hauteur       — entier 16 bits non signé, big-endian
  [8:]    Données       — flux RGB filtré (Delta horizontal) puis compressé LZMA (preset 9)

Filtrage Delta horizontal :
  Chaque pixel (R, G, B) est remplacé par sa différence avec le pixel
  immédiatement à gauche dans la même ligne. Le premier pixel de chaque
  ligne est stocké tel quel (delta = 0 par rapport à un pixel noir).

Compression :
  L'algorithme LZMA avec niveau de compression 9 (maximum).
"""

import struct
import lzma
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image

# ── Constantes ──────────────────────────────────────────────────────────────
MAGIC = b"EAU1"
LZMA_PRESET = 9
HEADER_SIZE = 8  # 4 (magic) + 2 (width) + 2 (height)


# ── Encodage ────────────────────────────────────────────────────────────────

def _apply_horizontal_delta(pixels: np.ndarray) -> np.ndarray:
    """
    Applique le filtre Delta horizontal sur un tableau (H, W, 3) uint8.
    Chaque pixel est remplacé par (R - R_left) mod 256.
    Le premier pixel de chaque ligne est conservé tel quel.
    Retourne un tableau uint8 (arithmétique modulo 256).
    """
    H, W, _ = pixels.shape
    delta = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        # Premier pixel de la ligne : stocké tel quel
        delta[y, 0] = pixels[y, 0]
        for x in range(1, W):
            # Différence modulo 256
            delta[y, x] = (pixels[y, x].astype(np.int16) - pixels[y, x - 1].astype(np.int16)) & 0xFF
    return delta


def encode_image(input_path: str, output_eau_path: str) -> None:
    """
    Encode une image PNG (ou tout format supporté par Pillow) au format .eau.

    Args:
        input_path:  Chemin de l'image source.
        output_eau_path: Chemin du fichier .eau à créer.
    """
    # Charger l'image avec Pillow
    img = Image.open(input_path).convert("RGB")
    width, height = img.size

    # Convertir en numpy array (H, W, 3) uint8
    pixels = np.array(img, dtype=np.uint8)

    # Appliquer le filtre Delta horizontal
    filtered = _apply_horizontal_delta(pixels)

    # Sérialiser en bytes (H × W × 3 octets)
    raw_bytes = filtered.tobytes()

    # Compresser avec LZMA preset 9
    compressed = lzma.compress(raw_bytes, preset=LZMA_PRESET)

    # Assembler le fichier .eau
    with open(output_eau_path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack(">H", width))
        f.write(struct.pack(">H", height))
        f.write(compressed)

    print(f"[EAU] Encodé : {input_path} → {output_eau_path}")
    print(f"      Dimensions : {width}×{height}")
    print(f"      Taille compressée : {len(compressed)} octets")


# ── Décodage ────────────────────────────────────────────────────────────────

def _inverse_horizontal_delta(delta: np.ndarray) -> np.ndarray:
    """
    Applique l'inverse du filtre Delta horizontal.
    delta : tableau (H, W, 3) uint8.
    Retourne un tableau (H, W, 3) uint8 (arithmétique modulo 256).
    """
    H, W, _ = delta.shape
    reconstructed = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        reconstructed[y, 0] = delta[y, 0]
        for x in range(1, W):
            # Reconstruction modulo 256
            reconstructed[y, x] = (reconstructed[y, x - 1].astype(np.uint16) + delta[y, x].astype(np.uint16)) & 0xFF
    return reconstructed


def decode_image(input_eau_path: str) -> Image.Image:
    """
    Décode un fichier .eau et retourne une image PIL.

    Args:
        input_eau_path: Chemin du fichier .eau.

    Returns:
        Une instance PIL.Image (mode RGB).
    """
    with open(input_eau_path, "rb") as f:
        data = f.read()

    # Valider le magic number
    if data[:4] != MAGIC:
        raise ValueError(f"Magic number invalide : {data[:4]!r} (attendu {MAGIC!r})")

    # Lire les métadonnées
    width = struct.unpack(">H", data[4:6])[0]
    height = struct.unpack(">H", data[6:8])[0]

    # Décompresser
    compressed = data[8:]
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

    return Image.fromarray(pixels, mode="RGB")


# ── CLI simple ──────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Outil de conversion .eau")
    parser.add_argument("action", choices=["encode", "decode"], help="Action à effectuer")
    parser.add_argument("input", help="Fichier d'entrée")
    parser.add_argument("output", help="Fichier de sortie")
    args = parser.parse_args()

    if args.action == "encode":
        encode_image(args.input, args.output)
    else:
        img = decode_image(args.input)
        img.save(args.output)
        print(f"[EAU] Décodé : {args.input} → {args.output}")


if __name__ == "__main__":
    main()