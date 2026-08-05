#!/usr/bin/env python3
"""
Script de build pour créer l'exécutable ImagesSH.exe.

Usage :
    python build_exe.py

Prérequis :
    pip install pyinstaller

Créé :
    dist/ImagesSH.exe  — exécutable autonome (sans console)
    dist/ImagesSH.exe  — peut être associé aux fichiers .eau et .soda
"""

import subprocess
import sys
import os

def main():
    # Chemin du répertoire courant
    root_dir = os.path.dirname(os.path.abspath(__file__))

    # Arguments PyInstaller
    args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",           # Un seul .exe
        "--windowed",          # Pas de console (GUI)
        "--name", "ImagesSH",  # Nom du .exe
        # Chemins de données supplémentaires si besoin
        "--add-data", f"eau_format.py{os.pathsep}.",
        "--add-data", f"soda_format.py{os.pathsep}.",
        "--add-data", f"beer_format.py{os.pathsep}.",
        # Nettoyage
        "--clean",
        "--noconfirm",
        # Fichier d'entrée
        os.path.join(root_dir, "eau_viewer.py"),
    ]

    print("=" * 60)
    print("Build de ImagesSH.exe avec PyInstaller")
    print("=" * 60)
    print(f"Commande : {' '.join(args)}")
    print()

    # Exécuter PyInstaller
    result = subprocess.run(args, cwd=root_dir)

    if result.returncode == 0:
        print()
        print("=" * 60)
        print("✅ Build réussi !")
        print(f"   Exécutable : {os.path.join(root_dir, 'dist', 'ImagesSH.exe')}")
        print("=" * 60)
        print()
        print("Pour associer les fichiers .eau et .soda :")
        print("  1. Faites un clic droit sur un fichier .eau ou .soda")
        print("  2. Choisissez 'Ouvrir avec' > 'Choisir une autre application'")
        print("  3. Sélectionnez dist/ImagesSH.exe")
        print("  4. Cochez 'Toujours utiliser cette application'")
        print()
        print("Ou exécutez register_file_association.bat (en tant qu'admin)")
    else:
        print()
        print("❌ Erreur lors du build")
        sys.exit(1)


if __name__ == "__main__":
    main()