#!/usr/bin/env python3
"""Crée une image PNG de test pour valider le format .eau."""

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Créer une image 512×512 avec dégradés et formes
img = Image.new("RGB", (512, 512), color=(30, 30, 40))
draw = ImageDraw.Draw(img)

# Fond dégradé
for y in range(512):
    r = int(30 + (y / 511) * 100)
    g = int(30 + (y / 511) * 50)
    b = int(40 + (y / 511) * 150)
    for x in range(512):
        r2 = int(r + (x / 511) * 80)
        g2 = int(g + (x / 511) * 60)
        b2 = int(b + (x / 511) * 40)
        img.putpixel((x, y), (min(r2, 255), min(g2, 255), min(b2, 255)))

# Cercle rouge
draw.ellipse([50, 50, 200, 200], fill=(220, 40, 40), outline=(255, 200, 200), width=3)

# Rectangle bleu
draw.rectangle([300, 80, 460, 230], fill=(30, 80, 220), outline=(150, 200, 255), width=3)

# Triangle vert
draw.polygon([(150, 350), (60, 480), (240, 480)], fill=(40, 200, 60), outline=(150, 255, 180), width=3)

# Ligne diagonale
for i in range(300, 450):
    draw.point((i, i - 100), fill=(255, 255, 100))

# Pixel art "EAU" text
# On dessine du texte
try:
    font = ImageFont.truetype("arial.ttf", 48)
except IOError:
    font = ImageFont.load_default()
draw.text((180, 280), "EAU", fill=(255, 255, 255), font=font)

# Sauvegarder
img.save("test_image.png")
print(f"Image de test créée : test_image.png ({img.size[0]}×{img.size[1]})")