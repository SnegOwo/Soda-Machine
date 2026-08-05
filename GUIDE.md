# 📖 Guide d'utilisation du format .eau

## 📋 Table des matières

1. [Prérequis](#-prérequis)
2. [Installation](#-installation)
3. [Structure du projet](#-structure-du-projet)
4. [Encodage : convertir une image en .eau](#-encodage-convertir-une-image-en-eau)
5. [Décodage : convertir un .eau en PNG](#-décodage-convertir-un-eau-en-png)
6. [Visionneuse graphique](#-visionneuse-graphique)
7. [Benchmark : comparer les performances](#-benchmark-comparer-les-performances)
8. [Créer une image de test](#-créer-une-image-de-test)
9. [Exemple complet : workflow typique](#-exemple-complet-workflow-typique)
10. [Dépannage](#-dépannage)

---

## ✅ Prérequis

- **Python 3.11+** installé
- **Pillow** (bibliothèque de traitement d'images)
- **NumPy** (calcul matriciel)

Vérifie que tout est OK :

```bash
python --version
pip show pillow numpy
```

---

## 📦 Installation

### 1. Télécharge les fichiers

Place tous les fichiers du projet dans un même dossier :

```
mon-projet-eau/
├── eau_format.py        # Moteur principal
├── eau_viewer.py        # Visionneuse
├── benchmark.py         # Outil de test
├── create_test_image.py # Générateur d'image test
└── GUIDE.md             # Ce guide
```

### 2. Installe les dépendances (si pas déjà fait)

```bash
pip install pillow numpy
```

C'est tout ! Aucune autre dépendance n'est nécessaire.

---

## 📁 Structure du projet

| Fichier | Rôle |
|---------|------|
| `eau_format.py` | Contient `encode_image()` et `decode_image()` — le cœur du format |
| `eau_viewer.py` | Interface graphique pour visualiser les fichiers `.eau` |
| `benchmark.py` | Compare la compression PNG vs EAU sur une image |
| `create_test_image.py` | Génère une image de test (512×512 avec dégradés et formes) |
| `test_image.png` | Image de test générée par le script ci-dessus |

---

## 🔄 Encodage : convertir une image en .eau

### Méthode 1 : en ligne de commande

```bash
python eau_format.py encode mon_image.png mon_image.eau
```

### Méthode 2 : dans un script Python

```python
from eau_format import encode_image

encode_image("mon_image.png", "mon_image.eau")
```

### Méthode 3 : avec le benchmark

```bash
python benchmark.py mon_image.png
```

Cette méthode encode ET affiche les statistiques de compression.

**Formats d'entrée supportés :** PNG, JPEG, BMP, GIF, TIFF, WebP, etc. (tout ce que Pillow supporte).

---

## 🔁 Décodage : convertir un .eau en PNG

### En ligne de commande

```bash
python eau_format.py decode mon_image.eau mon_image_restauree.png
```

### Dans un script Python

```python
from eau_format import decode_image

# decode_image() retourne un objet PIL.Image
img = decode_image("mon_image.eau")
img.save("mon_image_restauree.png")

# Tu peux aussi l'afficher directement
img.show()
```

---

## 🖼️ Visionneuse graphique

### Lancer la visionneuse

```bash
# Avec un fichier .eau directement
python eau_viewer.py test_image.eau

# Ou lancer la visionneuse vide, puis ouvrir un fichier via le menu
python eau_viewer.py
```

### Interface

![Interface de la visionneuse](https://via.placeholder.com/600x400/1e1e2e/cdd6f4?text=Interface+EAU+Viewer)

La visionneuse propose une interface au thème sombre avec :

| Fonction | Raccourci | Description |
|----------|-----------|-------------|
| 📂 Ouvrir un fichier | `Ctrl+O` | Ouvre un fichier `.eau` via la boîte de dialogue |
| 💾 Exporter en PNG | `Ctrl+S` | Sauvegarde l'image au format PNG |
| 🔍 Zoom avant | `Ctrl++` | Agrandit l'image (x1.25 à chaque clic) |
| 🔍 Zoom arrière | `Ctrl+-` | Réduit l'image |
| 🔄 Zoom 100% | `Ctrl+0` | Réinitialise le zoom à 1:1 |
| ℹ️ Métadonnées | Menu Affichage | Affiche les infos détaillées du fichier |
| ❌ Quitter | `Ctrl+Q` | Ferme la visionneuse |

### Fonctionnalités visuelles

- **Panneau d'info** en haut : nom du fichier, dimensions, taille, zoom
- **Barre d'état** en bas : messages de statut
- **Barre de défilement** : l'image défile si elle est plus grande que la fenêtre
- **Boutons de zoom** : en bas à droite de l'interface

---

## 📊 Benchmark : comparer les performances

### Utilisation simple

```bash
# Utilise test_image.png par défaut
python benchmark.py
```

### Sur une image précise

```bash
python benchmark.py ma_photo.png
```

### Ce que le benchmark affiche

```
╔══════════════════════════════════════════════╗
║      Benchmark de compression .eau          ║
╚══════════════════════════════════════════════╝

Fichier source : test_image.png
Dimensions :     512 × 512 px (262,144 pixels)

[EAU] Encodé : test_image.png → test_image.eau
      Dimensions : 512×512
      Taille compressée : 6248 octets

==================================================
                    RÉSULTATS
==================================================
Format       Taille         Ratio        Taux
──────────── ────────────── ──────────── ────────────
PNG          11.93 Ko         1.55%
EAU          6.11 Ko          0.80%
RAW          768.00 Ko      100%
──────────────────────────────────────────────────

✅ Gain EAU vs PNG : 48.80% de réduction

Performance :
  Encodage : 599.8 ms
  Décodage : 532.0 ms

Vérification d'intégrité :
  ✓ Aucune perte — l'image est identique pixel pour pixel
```

### Interprétation des résultats

| Colonne | Signification |
|---------|---------------|
| **Format** | PNG, EAU, ou RAW (non compressé) |
| **Taille** | Taille du fichier sur le disque |
| **Ratio** | Pourcentage par rapport à RAW (100% = non compressé) |
| **Gain** | Réduction de taille d'EAU par rapport à PNG |

---

## 🎨 Créer une image de test

```bash
python create_test_image.py
```

Génère `test_image.png` (512×512 px) avec :
- Fond dégradé (bleu-violet)
- Cercle rouge
- Rectangle bleu
- Triangle vert
- Ligne diagonale jaune
- Texte "EAU" en blanc

Utile pour tester rapidement l'encodage/décodage.

---

## 🚀 Exemple complet : workflow typique

```bash
# 1. (Optionnel) Crée une image de test
python create_test_image.py

# 2. Encode une image au format .eau
python eau_format.py encode test_image.png test_image.eau

# 3. Vérifie la compression avec le benchmark
python benchmark.py test_image.png

# 4. Visualise le résultat
python eau_viewer.py test_image.eau

# 5. (Optionnel) Décode et exporte en PNG
python eau_format.py decode test_image.eau test_image_restored.png
```

### Dans un script Python complet

```python
from eau_format import encode_image, decode_image
from PIL import Image

# === ENCODAGE ===
print("Encodage en cours...")
encode_image("photo.png", "photo.eau")

# === DÉCODAGE ===
print("Décodage en cours...")
img = decode_image("photo.eau")

# L'image est identique à l'originale (sans perte)
img.save("photo_restored.png")

# Affiche les propriétés
print(f"Dimensions : {img.width} × {img.height}")
print(f"Mode : {img.mode}")
```

---

## 🔧 Dépannage

### "Magic number invalide"

Le fichier n'est pas un fichier `.eau` valide ou est corrompu.

```bash
# Vérifie le magic number avec Python
python -c "
with open('fichier.eau', 'rb') as f:
    print(repr(f.read(4)))
"
# Doit afficher : b'EAU1'
```

### "Erreur de décompression LZMA"

Le fichier `.eau` est corrompu ou a été modifié après encodage.

### L'image décodée a des couleurs étranges

Le fichier `.eau` a peut-être été encodé avec une version antérieure du code. Ré-encode l'image source avec la version actuelle.

### La visionneuse ne s'ouvre pas

```bash
# Vérifie que tkinter est installé
python -c "import tkinter; print('OK')"

# Si erreur, installe tkinter :
# Sur Ubuntu/Debian : sudo apt install python3-tk
# Sur Windows : tkinter est inclus avec Python
```

### "ModuleNotFoundError: No module named 'PIL'"

```bash
pip install pillow
```

### "ModuleNotFoundError: No module named 'numpy'"

```bash
pip install numpy
```

---

## 💡 Astuces

- **Pour de meilleurs résultats de compression** : les images avec des grands dégradés (photos, rendus) se compressent mieux que les images avec beaucoup de bords nets (texte, captures d'écran).
- **Le format .eau n'est pas destiné à remplacer PNG** — c'est un format expérimental pour illustrer les concepts de filtrage delta et de compression LZMA.
- **Dimensions max** : 65535 × 65535 pixels (limite du header 16 bits).
- **Utilisation mémoire** : le décodage charge l'image entière en mémoire + les données décompressées. Pour les très grandes images, la RAM peut être un facteur limitant.

---

<div align="center">
  <sub>📖 Guide généré pour le projet EAU — Custom Image Format</sub>
</div>