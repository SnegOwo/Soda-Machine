#!/usr/bin/env python3
"""
Format d'image .beer — Spécification
=====================================
Le format .beer est un format d'image avec perte, inspiré de WebP/JPEG,
conçu pour être le plus petit possible tout en gardant une qualité correcte.

Pipeline de compression (style WebP) :
  1. Conversion RGB → YCbCr (espace de luminance/chrominance)
  2. Sous-échantillonnage chroma 4:2:0 (qualité < 95) — la chrominance
     est réduite de moitié dans les deux dimensions (÷4 de données)
  3. DCT 8×8 (transformée en cosinus discrète, DCT-II orthonormale)
     sur chaque plan (Y, Cb, Cr)
  4. Quantification avec les tables JPEG standard (luminance + chrominance)
     mises à l'échelle selon la qualité (1–100)
  5. Parcours en zigzag des coefficients (les basses fréquences d'abord)
  6. Codage par blocs : DC prédictif (delta) + RLE des zéros AC,
     terme EOB
  7. Compression finale LZMA (preset 9)

Structure binaire d'un fichier .beer :
  [0:4]   Magic bytes        — b"BEER" (4 octets)
  [4:6]   Largeur            — entier 16 bits non signé, big-endian
  [6:8]   Hauteur            — entier 16 bits non signé, big-endian
  [8]     Qualité            — 1 octet (1–100)
  [9]     Sous-échantillonnage — 1 octet (0 = 4:2:0, 1 = 4:4:4)
  [10:]   Données            — flux des 3 plans (Y, Cb, Cr), chacun
                               préfixé par sa longueur (u32 BE),
                               compressés LZMA (preset 9)

Pourquoi .beer est-il si petit ?
  • La chrominance est sous-échantillonnée (l'œil y est moins sensible)
  • La DCT concentre l'énergie dans les basses fréquences
  • La quantification élimine les hautes fréquences imperceptibles
  • Le zigzag + RLE produit de très longs runs de zéros
  • LZMA comprime le résultat final

Différence avec .eau / .soda :
  .eau  = lossless pur (delta horizontal + LZMA)
  .soda = lossy simple (quantification RGB + delta + LZMA)
  .beer = lossy type WebP (YCbCr 4:2:0 + DCT 8×8 + quantification JPEG)
          → nettement plus petit à qualité visuelle équivalente
"""

import struct
import lzma
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image

# ── Constantes ──────────────────────────────────────────────────────────────
MAGIC = b"BEER"
LZMA_PRESET = 9
HEADER_SIZE = 10  # 4 (magic) + 2 (width) + 2 (height) + 1 (quality) + 1 (subsampling)

SUB_420 = 0  # Chroma sous-échantillonné 4:2:0 (par défaut)
SUB_444 = 1  # Aucun sous-échantillonnage 4:4:4 (qualité ≥ 95)

EOB = 0xFF  # Marqueur de fin de bloc

# ── Matrice DCT-II orthonormale 8×8 ─────────────────────────────────────────

def _build_dct_matrix(n: int = 8) -> np.ndarray:
    """
    Construit la matrice de DCT-II orthonormale (n × n).

    La base est orthonormale, donc la matrice inverse = transposée.
    """
    k = np.arange(n)
    u = k.reshape(-1, 1)
    mat = np.cos((2 * k[None, :] + 1) * u * np.pi / (2 * n))
    c = np.full(n, np.sqrt(2.0 / n))
    c[0] = np.sqrt(1.0 / n)
    return mat * c[:, None]


DCT_MAT = _build_dct_matrix(8)

# ── Tables de quantification JPEG standard ─────────────────────────────────

LUMA_Q = np.array([
    16, 11, 10, 16, 24, 40, 51, 61,
    12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56,
    14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68, 109, 103, 77,
    24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101,
    72, 92, 95, 98, 112, 100, 103, 99,
], dtype=np.float64).reshape(8, 8)

CHROMA_Q = np.array([
    17, 18, 24, 47, 99, 99, 99, 99,
    18, 21, 26, 66, 99, 99, 99, 99,
    24, 26, 56, 99, 99, 99, 99, 99,
    47, 66, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
], dtype=np.float64).reshape(8, 8)

# Table d'index du parcours en zigzag (ordre JPEG standard)
ZIGZAG = np.array([
     0,  1,  8, 16,  9,  2,  3, 10,
    17, 24, 32, 25, 18, 11,  4,  5,
    12, 19, 26, 33, 40, 48, 41, 34,
    27, 20, 13,  6,  7, 14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36,
    29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46,
    53, 60, 61, 54, 47, 55, 62, 63,
], dtype=np.int32)

# Table inverse du zigzag : INV_ZIGZAG[position_zigzag] = index ligne-majeure
INV_ZIGZAG = np.zeros(64, dtype=np.int32)
INV_ZIGZAG[ZIGZAG] = np.arange(64)


# ── Conversion de couleur RGB ↔ YCbCr ──────────────────────────────────────

def _rgb_to_ycbcr(rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Convertit un tableau (H, W, 3) uint8/f64 RGB en trois plans Y, Cb, Cr
    (valeurs flottantes 0–255).
    """
    r = rgb[..., 0].astype(np.float64)
    g = rgb[..., 1].astype(np.float64)
    b = rgb[..., 2].astype(np.float64)

    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = -0.168736 * r - 0.331264 * g + 0.5 * b + 128.0
    cr = 0.5 * r - 0.418688 * g - 0.081312 * b + 128.0
    return y, cb, cr


def _ycbcr_to_rgb(y: np.ndarray, cb: np.ndarray, cr: np.ndarray) -> np.ndarray:
    """
    Reconstitue un tableau (H, W, 3) RGB uint8 depuis les plans Y, Cb, Cr.
    """
    cb_ = cb - 128.0
    cr_ = cr - 128.0

    r = y + 1.402 * cr_
    g = y - 0.344136 * cb_ - 0.714136 * cr_
    b = y + 1.772 * cb_

    out = np.stack([r, g, b], axis=-1)
    return np.clip(out, 0, 255).astype(np.uint8)


# ── Sous-échantillonnage chroma 4:2:0 ──────────────────────────────────────

def _subsample420(plane: np.ndarray) -> np.ndarray:
    """
    Réduit un plan (H, W) à (ceil(H/2), ceil(W/2)) par moyenne 2×2.
    Les bords impairs sont recopiés (réplication).
    """
    H, W = plane.shape
    H2 = (H + 1) // 2
    W2 = (W + 1) // 2
    padded = np.zeros((H2 * 2, W2 * 2), dtype=np.float64)
    padded[:H, :W] = plane
    if H % 2 == 1:
        padded[H, :] = padded[H - 1, :]
    if W % 2 == 1:
        padded[:, W] = padded[:, W - 1]
    avg = (
        padded[0::2, 0::2]
        + padded[0::2, 1::2]
        + padded[1::2, 0::2]
        + padded[1::2, 1::2]
    ) * 0.25
    return avg


def _upsample420(plane: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    """
    Agrandit un plan sous-échantillonné (H2, W2) vers (target_h, target_w)
    par interpolation bilinéaire (via Pillow).
    """
    H2, W2 = plane.shape
    arr = np.clip(plane, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, mode="L")
    img = img.resize((W2 * 2, H2 * 2), Image.BILINEAR)
    up = np.array(img, dtype=np.float64)
    return up[:target_h, :target_w]


# ── Mise à l'échelle des tables de quantification ─────────────────────────

def _scale_quant_table(table: np.ndarray, quality: int) -> np.ndarray:
    """
    Met la table de quantification JPEG à l'échelle selon la qualité (1–100).

    Même formule que JPEG standard :
      qualité < 50 : scale = 5000 / qualité
      qualité ≥ 50 : scale = 200 - 2 × qualité
    """
    quality = max(1, min(100, quality))
    if quality < 50:
        s = 5000 / quality
    else:
        s = 200 - 2 * quality
    scaled = np.floor((table * s + 50) / 100)
    return np.clip(scaled, 1, 255).astype(np.int32)


# ── Découpage en blocs 8×8 ─────────────────────────────────────────────────

def _plane_to_blocks(plane: np.ndarray, H: int, W: int) -> np.ndarray:
    """
    Découpe un plan (H, W) en blocs 8×8 (rembourré par zéros).
    Retourne un tableau (nombre_blocs, 8, 8).
    """
    ph = (H + 7) // 8 * 8
    pw = (W + 7) // 8 * 8
    padded = np.zeros((ph, pw), dtype=np.float64)
    padded[:H, :W] = plane
    blocks = padded.reshape(ph // 8, 8, pw // 8, 8).transpose(0, 2, 1, 3)
    return blocks.reshape(-1, 8, 8)


def _blocks_to_plane(blocks: np.ndarray, H: int, W: int) -> np.ndarray:
    """
    Rassemble des blocs (nombre_blocs, 8, 8) en un plan (H, W) recadré.
    """
    ph = (H + 7) // 8 * 8
    pw = (W + 7) // 8 * 8
    nb_y = ph // 8
    nb_x = pw // 8
    padded = blocks.reshape(nb_y, nb_x, 8, 8).transpose(0, 2, 1, 3).reshape(ph, pw)
    return padded[:H, :W]


# ── Codage / décodage d'un bloc (DC prédictif + RLE AC) ────────────────────

def _encode_block(qz: np.ndarray, prev_dc: int) -> Tuple[bytes, int]:
    """
    Encode les 64 coefficients zigzag d'un bloc.

    Format :
      [DC delta : i16 BE]
      puis symboles AC jusqu'à EOB :
        [run de zéros : u8][valeur : i16 BE]   (run < 64)
        [EOB : 0xFF]                           (fin de bloc)

    Retourne (octets encodés, nouveau DC).
    """
    dc = int(np.clip(int(qz[0]) - prev_dc, -32768, 32767))
    out = bytearray(struct.pack(">h", dc))
    i = 1
    while i < 64:
        if qz[i] == 0:
            run = 0
            while i < 64 and qz[i] == 0:
                run += 1
                i += 1
            if i >= 64:
                out.append(EOB)
                break
            out.append(run)
            out += struct.pack(">h", int(qz[i]))
        else:
            out.append(0)
            out += struct.pack(">h", int(qz[i]))
        i += 1
    else:
        out.append(EOB)
    return bytes(out), int(qz[0])


def _decode_block(buf: bytes, pos: int, prev_dc: int) -> Tuple[np.ndarray, int, int]:
    """
    Décode un bloc zigzag. Retourne (tableau 64 int32, nouvelle position, DC).

    Le `else` du `while` est atteint quand la boucle se termine parce que les
    63 coefficients non-DC sont tous remplis (i == 64). Dans ce cas, l'encodeur
    a écrit un EOB juste après la dernière valeur : on le consomme ici pour
    garder l'alignement exact du flux.
    """
    dc_delta = struct.unpack_from(">h", buf, pos)[0]
    pos += 2
    dc = int(prev_dc) + int(dc_delta)

    q = np.zeros(64, dtype=np.int32)
    q[0] = dc
    i = 1
    while i < 64:
        run = buf[pos]
        pos += 1
        if run == EOB:
            break
        val = struct.unpack_from(">h", buf, pos)[0]
        pos += 2
        i += run
        if i >= 64:
            break
        q[i] = val
        i += 1
    else:
        # 63 coefficients remplis : l'encodeur a émis un EOB terminal.
        # Le consommer pour rester aligné sur le bloc suivant.
        if pos < len(buf) and buf[pos] == EOB:
            pos += 1
    return q, pos, dc


# ── Encodage / décodage d'un plan complet ──────────────────────────────────

def _encode_plane(plane: np.ndarray, H: int, W: int, qtable: np.ndarray) -> bytes:
    """
    Encode un plan entier :
      blocs 8×8 → DCT → quantification → zigzag → DC prédictif + RLE.
    """
    blocks = _plane_to_blocks(plane, H, W) - 128.0
    dct = DCT_MAT @ blocks @ DCT_MAT.T
    q = np.round(dct / qtable).astype(np.int32)
    qz = np.clip(q.reshape(-1, 64)[:, ZIGZAG], -32768, 32767)

    out = bytearray()
    prev_dc = 0
    for row in qz:
        enc, prev_dc = _encode_block(row, prev_dc)
        out += enc
    return bytes(out)


def _decode_plane(buf: bytes, pos: int, H: int, W: int, qtable: np.ndarray) -> Tuple[np.ndarray, int]:
    """
    Décode un plan entier. Retourne (plan (H, W) flottant, nouvelle position).
    """
    num_blocks = ((H + 7) // 8) * ((W + 7) // 8)
    qz = np.zeros((num_blocks, 64), dtype=np.int32)
    prev_dc = 0
    for i in range(num_blocks):
        row, pos, prev_dc = _decode_block(buf, pos, prev_dc)
        qz[i] = row

    q = qz[:, INV_ZIGZAG].reshape(num_blocks, 8, 8).astype(np.float64) * qtable
    blocks = DCT_MAT.T @ q @ DCT_MAT
    plane = _blocks_to_plane(blocks, H, W) + 128.0
    return plane, pos


# ── Encodage ────────────────────────────────────────────────────────────────

def encode_beer(input_path: str, output_beer_path: str, quality: int = 75) -> None:
    """
    Encode une image au format .beer (lossy, type WebP).

    Args:
        input_path:       Chemin de l'image source.
        output_beer_path: Chemin du fichier .beer à créer.
        quality:          Facteur de qualité (1–100, défaut: 75).
                          Souvent, une qualité de 75 donne un excellent
                          compromis taille/qualité (comme WebP/JPEG).
    """
    quality = max(1, min(100, quality))

    # Charger l'image
    img = Image.open(input_path).convert("RGB")
    width, height = img.size
    rgb = np.array(img, dtype=np.float64)

    # Conversion RGB → YCbCr
    y, cb, cr = _rgb_to_ycbcr(rgb)

    # Sous-échantillonnage chroma (4:2:0 sauf qualité très élevée)
    subsampling = SUB_444 if quality >= 95 else SUB_420
    if subsampling == SUB_420:
        cb_s = _subsample420(cb)
        cr_s = _subsample420(cr)
        ch_h, ch_w = cb_s.shape
    else:
        cb_s, cr_s = cb, cr
        ch_h, ch_w = height, width

    # Tables de quantification
    q_y = _scale_quant_table(LUMA_Q, quality)
    q_c = _scale_quant_table(CHROMA_Q, quality)

    # Encoder chaque plan
    y_stream = _encode_plane(y, height, width, q_y)
    cb_stream = _encode_plane(cb_s, ch_h, ch_w, q_c)
    cr_stream = _encode_plane(cr_s, ch_h, ch_w, q_c)

    # Assembler les flux (longueur u32 BE + données) puis compresser LZMA
    payload = b"".join(
        struct.pack(">I", len(s)) + s
        for s in (y_stream, cb_stream, cr_stream)
    )
    compressed = lzma.compress(payload, preset=LZMA_PRESET)

    # Écrire le fichier .beer
    with open(output_beer_path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack(">H", width))
        f.write(struct.pack(">H", height))
        f.write(struct.pack("B", quality))
        f.write(struct.pack("B", subsampling))
        f.write(compressed)

    # Tailles de référence
    raw_size = width * height * 3
    chroma_label = "4:2:0" if subsampling == SUB_420 else "4:4:4"

    print(f"[BEER] Encodé : {input_path} → {output_beer_path}")
    print(f"       Dimensions : {width}×{height}")
    print(f"       Qualité : {quality} (chroma {chroma_label})")
    print(f"       Taille compressée : {len(compressed)} octets")
    print(f"       Taille RAW : {raw_size} octets")
    print(f"       Ratio : {len(compressed) / raw_size * 100:.2f}%")


# ── Décodage ────────────────────────────────────────────────────────────────

def decode_beer(input_beer_path: str) -> Image.Image:
    """
    Décode un fichier .beer et retourne une image PIL.

    Args:
        input_beer_path: Chemin du fichier .beer.

    Returns:
        Une instance PIL.Image (mode RGB).
    """
    with open(input_beer_path, "rb") as f:
        data = f.read()

    # Valider le magic number
    if data[:4] != MAGIC:
        raise ValueError(f"Magic number invalide : {data[:4]!r} (attendu {MAGIC!r})")

    # Lire les métadonnées
    width = struct.unpack(">H", data[4:6])[0]
    height = struct.unpack(">H", data[6:8])[0]
    quality = data[8]
    subsampling = data[9]

    # Décompresser
    try:
        payload = lzma.decompress(data[HEADER_SIZE:])
    except lzma.LZMAError as e:
        raise ValueError(f"Erreur de décompression LZMA : {e}")

    # Lire les trois flux (Y, Cb, Cr)
    pos = 0
    streams = []
    for i in range(3):
        if pos + 4 > len(payload):
            raise ValueError("Fichier .beer tronqué (en-têtes de flux manquants)")
        length = struct.unpack_from(">I", payload, pos)[0]
        pos += 4
        if pos + length > len(payload):
            raise ValueError("Fichier .beer tronqué (données de flux manquantes)")
        streams.append(payload[pos:pos + length])
        pos += length

    y_stream, cb_stream, cr_stream = streams

    # Tables de quantification
    q_y = _scale_quant_table(LUMA_Q, quality)
    q_c = _scale_quant_table(CHROMA_Q, quality)

    # Déterminer les dimensions des plans chroma
    if subsampling == SUB_420:
        ch_h = (height + 1) // 2
        ch_w = (width + 1) // 2
    else:
        ch_h, ch_w = height, width

    # Décoder chaque plan
    y, pos = _decode_plane(y_stream, 0, height, width, q_y)
    cb_s, _ = _decode_plane(cb_stream, 0, ch_h, ch_w, q_c)
    cr_s, _ = _decode_plane(cr_stream, 0, ch_h, ch_w, q_c)

    # Ré-échantillonner la chrominance si nécessaire
    if subsampling == SUB_420:
        cb = _upsample420(cb_s, height, width)
        cr = _upsample420(cr_s, height, width)
    else:
        cb, cr = cb_s, cr_s

    # Conversion YCbCr → RGB
    rgb = _ycbcr_to_rgb(y, cb, cr)

    chroma_label = "4:2:0" if subsampling == SUB_420 else "4:4:4"
    print(f"[BEER] Décodé : {input_beer_path}")
    print(f"       Dimensions : {width}×{height}")
    print(f"       Qualité : {quality} (chroma {chroma_label})")

    return Image.fromarray(rgb, mode="RGB")


# ── CLI simple ──────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Outil de conversion .beer (lossy, type WebP)")
    parser.add_argument("action", choices=["encode", "decode"], help="Action à effectuer")
    parser.add_argument("input", help="Fichier d'entrée")
    parser.add_argument("output", help="Fichier de sortie")
    parser.add_argument("--quality", "-q", type=int, default=75, help="Qualité (1–100, défaut: 75)")
    args = parser.parse_args()

    if args.action == "encode":
        encode_beer(args.input, args.output, quality=args.quality)
    else:
        img = decode_beer(args.input)
        img.save(args.output)
        print(f"[BEER] Décodé : {args.input} → {args.output}")


if __name__ == "__main__":
    main()