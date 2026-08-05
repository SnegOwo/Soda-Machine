#!/usr/bin/env python3
"""
Visionneuse et convertisseur d'images .eau / .soda — Interface graphique Tkinter.

Usage :
    python eau_viewer.py [chemin_fichier]

Fonctionnalités :
    • Ouvrir tout format image (PNG, JPEG, BMP, GIF, .eau, .soda, .beer, etc.)
    • Convertir n'importe quelle image ouverte en .eau (lossless) ou .soda (lossy)
    • Afficher les métadonnées (dimensions, taille compressée, qualité)
    • Zoom avant/arrière
    • Exporter au format PNG
"""

import os
import sys
import struct
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from pathlib import Path

from PIL import Image, ImageTk

from eau_format import decode_image, encode_image
from soda_format import decode_soda, encode_soda
from beer_format import decode_beer, encode_beer

# ── Couleurs du thème sombre ────────────────────────────────────────────────
BG_COLOR = "#1e1e2e"
FRAME_COLOR = "#2a2a3e"
TEXT_COLOR = "#cdd6f4"
ACCENT_COLOR = "#89b4fa"
BUTTON_COLOR = "#313244"
HIGHLIGHT_COLOR = "#45475a"

# Extensions d'images standard supportées
STANDARD_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".webp", ".ico")
BEER_QUALITY_DEFAULT = 75


class EauViewer:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ImagesSH - Visionneuse & Convertisseur")
        self.root.configure(bg=BG_COLOR)
        self.root.minsize(800, 600)

        # Variables d'état
        self.current_path: str | None = None
        self.current_format: str | None = None  # "eau", "soda", "beer", "image" (standard)
        self.pil_image: Image.Image | None = None
        self.tk_image: ImageTk.PhotoImage | None = None
        self.zoom_level: float = 1.0

        # Configurer le style
        self._setup_styles()

        # Barre de menu
        self._setup_menu()

        # Zone de contenu
        self._setup_ui()

        # Raccourcis clavier
        self._setup_shortcuts()

        # Charger un fichier passé en argument
        if len(sys.argv) > 1:
            self.open_file(sys.argv[1])

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TLabelframe", background=BG_COLOR, foreground=TEXT_COLOR)
        style.configure("TLabelframe.Label", background=BG_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10, "bold"))

    def _setup_menu(self):
        menubar = tk.Menu(self.root, bg=FRAME_COLOR, fg=TEXT_COLOR,
                          activebackground=ACCENT_COLOR, activeforeground=BG_COLOR)

        # ── Menu Fichier ──
        file_menu = tk.Menu(menubar, tearoff=0, bg=FRAME_COLOR, fg=TEXT_COLOR,
                            activebackground=ACCENT_COLOR, activeforeground=BG_COLOR)
        file_menu.add_command(label="Ouvrir une image...", command=self.open_file_dialog, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Convertir en .eau (lossless)...", command=self.convert_to_eau_dialog, accelerator="Ctrl+E")
        file_menu.add_command(label="Convertir en .soda (lossy)...", command=self.convert_to_soda_dialog, accelerator="Ctrl+D")
        file_menu.add_command(label="Convertir en .beer (lossy, type WebP)...", command=self.convert_to_beer_dialog, accelerator="Ctrl+B")
        file_menu.add_separator()
        file_menu.add_command(label="Exporter en PNG...", command=self.export_png, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.root.quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="Fichier", menu=file_menu)

        # ── Menu Affichage ──
        view_menu = tk.Menu(menubar, tearoff=0, bg=FRAME_COLOR, fg=TEXT_COLOR,
                            activebackground=ACCENT_COLOR, activeforeground=BG_COLOR)
        view_menu.add_command(label="Zoom avant", command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="Zoom arrière", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="Zoom 100%", command=self.zoom_reset, accelerator="Ctrl+0")
        view_menu.add_separator()
        view_menu.add_command(label="Afficher les métadonnées", command=self.show_metadata)
        menubar.add_cascade(label="Affichage", menu=view_menu)

        self.root.config(menu=menubar)

    def _setup_ui(self):
        # Panneau principal
        self.main_frame = tk.Frame(self.root, bg=BG_COLOR)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Barre d'info en haut
        self.info_bar = tk.Label(
            self.main_frame, text="Aucun fichier ouvert",
            bg=FRAME_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 10),
            anchor=tk.W, padx=10, pady=6
        )
        self.info_bar.pack(fill=tk.X, pady=(0, 8))

        # Zone d'affichage de l'image avec scroll
        canvas_frame = tk.Frame(self.main_frame, bg=FRAME_COLOR, highlightbackground=HIGHLIGHT_COLOR, highlightthickness=1)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            canvas_frame, bg="#1a1a2e", highlightthickness=0,
            confine=True, scrollregion=(0, 0, 0, 0)
        )
        self.h_scroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.h_scroll.grid(row=1, column=0, sticky="ew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        # ── Bouton central "Ouvrir un fichier" ──────────────────────────────
        self.center_frame = tk.Frame(canvas_frame, bg="#1a1a2e")
        self.center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        open_icon = tk.Label(self.center_frame, text="📂", font=("Segoe UI", 48),
                             bg="#1a1a2e", fg=TEXT_COLOR)
        open_icon.pack(pady=(0, 10))

        self.open_btn = tk.Button(
            self.center_frame,
            text="Ouvrir une image",
            command=self.open_file_dialog,
            bg=ACCENT_COLOR, fg=BG_COLOR,
            font=("Segoe UI", 14, "bold"),
            relief=tk.FLAT, padx=30, pady=12,
            cursor="hand2",
            activebackground="#a6c8ff",
            activeforeground=BG_COLOR
        )
        self.open_btn.pack(pady=5)

        hint_label = tk.Label(
            self.center_frame,
            text="Formats supportés : PNG, JPEG, BMP, GIF, WEBP, .eau, .soda, .beer\n"
                 "ou utilisez Ctrl+O pour ouvrir",
            bg="#1a1a2e", fg="#6c7086",
            font=("Segoe UI", 9), justify=tk.CENTER
        )
        hint_label.pack(pady=(10, 0))

        # Barre d'état en bas
        self.status_bar = tk.Label(
            self.main_frame, text="Prêt",
            bg=FRAME_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 9),
            anchor=tk.W, padx=10, pady=4
        )
        self.status_bar.pack(fill=tk.X, pady=(8, 0))

        # Boutons de zoom et conversion
        self.bottom_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        self.bottom_frame.pack(fill=tk.X, pady=(4, 0))

        # Boutons de conversion (à gauche)
        self.convert_btn_frame = tk.Frame(self.bottom_frame, bg=BG_COLOR)
        self.convert_btn_frame.pack(side=tk.LEFT)

        btn_style = {"bg": BUTTON_COLOR, "fg": TEXT_COLOR, "font": ("Segoe UI", 9),
                      "relief": tk.FLAT, "padx": 12, "pady": 2, "cursor": "hand2"}

        self.btn_to_eau = tk.Button(self.convert_btn_frame, text="→ .eau", command=self.convert_to_eau_dialog, **btn_style)
        self.btn_to_eau.pack(side=tk.LEFT, padx=2)

        self.btn_to_soda = tk.Button(self.convert_btn_frame, text="→ .soda", command=self.convert_to_soda_dialog, **btn_style)
        self.btn_to_soda.pack(side=tk.LEFT, padx=2)

        self.btn_to_beer = tk.Button(self.convert_btn_frame, text="→ .beer", command=self.convert_to_beer_dialog, **btn_style)
        self.btn_to_beer.pack(side=tk.LEFT, padx=2)

        # Zoom (à droite)
        self.zoom_label = tk.Label(self.bottom_frame, text="Zoom: 100%", bg=BG_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 9))
        self.zoom_label.pack(side=tk.RIGHT, padx=5)

        btn_zoom_in = tk.Button(self.bottom_frame, text="+", command=self.zoom_in, **btn_style)
        btn_zoom_in.pack(side=tk.RIGHT, padx=2)
        btn_zoom_reset = tk.Button(self.bottom_frame, text="100%", command=self.zoom_reset, **btn_style)
        btn_zoom_reset.pack(side=tk.RIGHT, padx=2)
        btn_zoom_out = tk.Button(self.bottom_frame, text="−", command=self.zoom_out, **btn_style)
        btn_zoom_out.pack(side=tk.RIGHT, padx=2)

    def _setup_shortcuts(self):
        self.root.bind("<Control-o>", lambda e: self.open_file_dialog())
        self.root.bind("<Control-e>", lambda e: self.convert_to_eau_dialog())
        self.root.bind("<Control-d>", lambda e: self.convert_to_soda_dialog())
        self.root.bind("<Control-b>", lambda e: self.convert_to_beer_dialog())
        self.root.bind("<Control-s>", lambda e: self.export_png())
        self.root.bind("<Control-q>", lambda e: self.root.quit())
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-0>", lambda e: self.zoom_reset())
        self.root.bind("<Key-equal>", lambda e: self.zoom_in())

    # ── Détection de format ─────────────────────────────────────────────────

    def _detect_format(self, path: str) -> str:
        """
        Détecte le format du fichier.
        Retourne "eau", "soda", "image" (format standard), ou lève une exception.
        """
        # Vérifier d'abord les magic bytes
        with open(path, "rb") as f:
            magic = f.read(4)
        if magic == b"EAU1":
            return "eau"
        elif magic == b"SODA":
            return "soda"
        elif magic == b"BEER":
            return "beer"

        # Vérifier l'extension pour les formats standard
        ext = Path(path).suffix.lower()
        if ext in STANDARD_EXTENSIONS:
            return "image"

        # Tentative d'ouverture avec PIL pour les formats exotiques
        try:
            with Image.open(path) as img:
                img.verify()
            return "image"
        except Exception:
            raise ValueError(f"Format non reconnu ou image invalide : {path}")

    # ── Ouverture de fichier ────────────────────────────────────────────────

    def open_file_dialog(self):
        path = filedialog.askopenfilename(
            title="Ouvrir une image",
            filetypes=[
                 ("Toutes les images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tiff;*.tif;*.webp;*.ico;*.eau;*.soda;*.beer"),
                ("Image PNG", "*.png"),
                ("Image JPEG", "*.jpg;*.jpeg"),
                ("Image BMP", "*.bmp"),
                ("Image GIF", "*.gif"),
                ("Image WEBP", "*.webp"),
                ("Fichier EAU", "*.eau"),
                 ("Fichier SODA", "*.soda"),
                 ("Fichier BEER", "*.beer"),
                ("Tous les fichiers", "*.*")
            ]
        )
        if path:
            self.open_file(path)

    def open_file(self, path: str):
        try:
            fmt = self._detect_format(path)

            if fmt == "eau":
                self.pil_image = decode_image(path)
            elif fmt == "soda":
                self.pil_image = decode_soda(path)
            elif fmt == "beer":
                self.pil_image = decode_beer(path)
            else:  # image standard
                self.pil_image = Image.open(path).convert("RGB")

            self.current_path = path
            self.current_format = fmt
            self.zoom_level = 1.0
            self._hide_center_button()
            self._display_image()
            self._update_info(path)

            fmt_display = fmt.upper() if fmt in ("eau", "soda", "beer") else Path(path).suffix[1:].upper()
            self.status_bar.config(text=f"Image {fmt_display} chargée : {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le fichier :\n{e}")
            self.status_bar.config(text="Erreur lors du chargement")

    def _hide_center_button(self):
        """Cache le bouton central quand une image est chargée."""
        if hasattr(self, 'center_frame') and self.center_frame.winfo_exists():
            self.center_frame.place_forget()

    def _show_center_button(self):
        """Affiche le bouton central quand aucune image n'est chargée."""
        if hasattr(self, 'center_frame') and self.center_frame.winfo_exists():
            self.center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    # ── Affichage ───────────────────────────────────────────────────────────

    def _display_image(self):
        if self.pil_image is None:
            return

        # Redimensionner selon le zoom
        w = int(self.pil_image.width * self.zoom_level)
        h = int(self.pil_image.height * self.zoom_level)

        # Limiter la taille maximale pour éviter les problèmes de mémoire
        max_dim = 4000
        if w > max_dim or h > max_dim:
            factor = min(max_dim / w, max_dim / h)
            w = int(w * factor)
            h = int(h * factor)

        if w < 1 or h < 1:
            w, h = 1, 1

        resized = self.pil_image.resize((w, h), Image.NEAREST if self.zoom_level < 0.5 else Image.BICUBIC)
        self.tk_image = ImageTk.PhotoImage(resized)

        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0, 0, w, h))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        self.zoom_label.config(text=f"Zoom: {int(self.zoom_level * 100)}%")

    def _update_info(self, path: str):
        file_size = os.path.getsize(path)
        if self.pil_image:
            name = os.path.basename(path)
            fmt_label = self.current_format.upper() if self.current_format else "?"
            quality_info = ""
            if self.current_format in ("soda", "beer"):
                with open(self.current_path, "rb") as f:
                    _ = f.read(8)  # skip magic + width + height
                    quality = struct.unpack("B", f.read(1))[0]
                quality_info = f"  |  Qualité: {quality}"
            elif self.current_format == "image":
                fmt_label = Path(path).suffix[1:].upper()
            self.info_bar.config(
                text=f"📄 {name}  |  {fmt_label}  |  {self.pil_image.width}×{self.pil_image.height} px  "
                     f"|  Taille fichier : {file_size:,} octets{quality_info}"
            )

    # ── Zoom ────────────────────────────────────────────────────────────────

    def zoom_in(self):
        if self.pil_image:
            self.zoom_level = min(self.zoom_level * 1.25, 10.0)
            self._display_image()
            self._update_info(self.current_path)

    def zoom_out(self):
        if self.pil_image:
            self.zoom_level = max(self.zoom_level / 1.25, 0.05)
            self._display_image()
            self._update_info(self.current_path)

    def zoom_reset(self):
        if self.pil_image:
            self.zoom_level = 1.0
            self._display_image()
            self._update_info(self.current_path)

    # ── Conversion ──────────────────────────────────────────────────────────

    def _save_temp_image(self) -> str | None:
        """Sauvegarde l'image PIL actuelle dans un fichier temporaire PNG et retourne le chemin."""
        if self.pil_image is None:
            return None
        temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_temp_convert.png")
        self.pil_image.save(temp_path, "PNG")
        return temp_path

    def _clean_temp_image(self, temp_path: str):
        """Supprime le fichier temporaire."""
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

    def convert_to_beer_dialog(self):
        if self.pil_image is None:
            messagebox.showwarning("Aucune image", "Ouvrez d'abord une image.")
            return

        # Boîte de dialogue pour choisir la qualité
        quality = self._ask_quality_beer()
        if quality is None:
            return  # L'utilisateur a annulé

        default_name = "output.beer"
        if self.current_path:
            default_name = Path(self.current_path).with_suffix(".beer").name

        path = filedialog.asksaveasfilename(
            title="Convertir en .beer (lossy, type WebP)",
            defaultextension=".beer",
            filetypes=[("Fichier BEER", "*.beer"), ("Tous les fichiers", "*.*")],
            initialfile=default_name
        )
        if not path:
            return

        try:
            temp_path = self._save_temp_image()
            if temp_path is None:
                return

            self.status_bar.config(text=f"Conversion en .beer (qualité {quality}) en cours...")
            self.root.update()

            encode_beer(temp_path, path, quality=quality)

            self._clean_temp_image(temp_path)

            self.status_bar.config(text=f"✅ Converti en .beer (qualité {quality}) : {os.path.basename(path)}")

            # Ouvrir le fichier converti
            self.open_file(path)
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec de la conversion en .beer :\n{e}")
            self.status_bar.config(text="Erreur lors de la conversion")

    def _ask_quality_beer(self) -> int | None:
        """Affiche une boîte de dialogue simple pour choisir la qualité .beer (1-100)."""
        quality = simpledialog.askinteger(
            "Qualité .beer",
            "Choisissez la qualité de compression (1-100) :\n\n"
            "100 = meilleure qualité (fichier plus gros)\n"
            "1   = compression maximale (fichier plus petit)\n"
            "75  = excellent compromis taille/qualité (recommandé, comme WebP)",
            parent=self.root,
            minvalue=1,
            maxvalue=100,
            initialvalue=BEER_QUALITY_DEFAULT
        )
        return quality

    def convert_to_eau_dialog(self):
        if self.pil_image is None:
            messagebox.showwarning("Aucune image", "Ouvrez d'abord une image.")
            return

        default_name = "output.eau"
        if self.current_path:
            default_name = Path(self.current_path).with_suffix(".eau").name

        path = filedialog.asksaveasfilename(
            title="Convertir en .eau (lossless)",
            defaultextension=".eau",
            filetypes=[("Fichier EAU", "*.eau"), ("Tous les fichiers", "*.*")],
            initialfile=default_name
        )
        if not path:
            return

        try:
            temp_path = self._save_temp_image()
            if temp_path is None:
                return

            self.status_bar.config(text="Conversion en .eau en cours...")
            self.root.update()

            encode_image(temp_path, path)

            self._clean_temp_image(temp_path)

            self.status_bar.config(text=f"✅ Converti en .eau : {os.path.basename(path)}")

            # Ouvrir le fichier converti
            self.open_file(path)
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec de la conversion en .eau :\n{e}")
            self.status_bar.config(text="Erreur lors de la conversion")

    def convert_to_soda_dialog(self):
        if self.pil_image is None:
            messagebox.showwarning("Aucune image", "Ouvrez d'abord une image.")
            return

        # Boîte de dialogue pour choisir la qualité
        quality = self._ask_quality()
        if quality is None:
            return  # L'utilisateur a annulé

        default_name = "output.soda"
        if self.current_path:
            default_name = Path(self.current_path).with_suffix(".soda").name

        path = filedialog.asksaveasfilename(
            title="Convertir en .soda (lossy)",
            defaultextension=".soda",
            filetypes=[("Fichier SODA", "*.soda"), ("Tous les fichiers", "*.*")],
            initialfile=default_name
        )
        if not path:
            return

        try:
            temp_path = self._save_temp_image()
            if temp_path is None:
                return

            self.status_bar.config(text=f"Conversion en .soda (qualité {quality}) en cours...")
            self.root.update()

            encode_soda(temp_path, path, quality=quality)

            self._clean_temp_image(temp_path)

            self.status_bar.config(text=f"✅ Converti en .soda (qualité {quality}) : {os.path.basename(path)}")

            # Ouvrir le fichier converti
            self.open_file(path)
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec de la conversion en .soda :\n{e}")
            self.status_bar.config(text="Erreur lors de la conversion")

    def _ask_quality(self) -> int | None:
        """Affiche une boîte de dialogue simple pour choisir la qualité (1-100)."""
        quality = simpledialog.askinteger(
            "Qualité .soda",
            "Choisissez la qualité de compression (1-100) :\n\n"
            "100 = meilleure qualité (fichier plus gros)\n"
            "1   = compression maximale (fichier plus petit)\n"
            "80  = bon équilibre (recommandé)",
            parent=self.root,
            minvalue=1,
            maxvalue=100,
            initialvalue=80
        )
        return quality

    # ── Export PNG ──────────────────────────────────────────────────────────

    def export_png(self):
        if self.pil_image is None:
            messagebox.showwarning("Aucune image", "Ouvrez d'abord un fichier.")
            return

        default_name = "output.png"
        if self.current_path:
            default_name = Path(self.current_path).with_suffix(".png").name

        path = filedialog.asksaveasfilename(
            title="Exporter au format PNG",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("Tous les fichiers", "*.*")],
            initialfile=default_name
        )
        if path:
            try:
                self.pil_image.save(path)
                self.status_bar.config(text=f"Exporté PNG : {path}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible d'exporter :\n{e}")

    # ── Métadonnées ─────────────────────────────────────────────────────────

    def show_metadata(self):
        if self.pil_image is None:
            messagebox.showwarning("Aucune image", "Ouvrez d'abord une image.")
            return

        fmt = self.current_format or "?"
        file_size = os.path.getsize(self.current_path) if self.current_path else 0
        n_pixels = self.pil_image.width * self.pil_image.height
        bpp = (file_size * 8) / n_pixels if n_pixels > 0 else 0

        if fmt == "soda":
            with open(self.current_path, "rb") as f:
                _ = f.read(8)  # skip magic + width + height
                quality = struct.unpack("B", f.read(1))[0]
            loss_info = f"Qualité : {quality} (lossy)"
        elif fmt == "beer":
            with open(self.current_path, "rb") as f:
                _ = f.read(8)  # skip magic + width + height
                quality = struct.unpack("B", f.read(1))[0]
                subsampling = struct.unpack("B", f.read(1))[0]
            chroma = "4:2:0" if subsampling == 0 else "4:4:4"
            loss_info = f"Qualité : {quality} (lossy, chroma {chroma})"
        elif fmt == "eau":
            loss_info = "Lossless"
        else:
            # Image standard
            loss_info = "Format standard (non compressé EAU/SODA/BEER)"

        fmt_name = {"eau": "EAU1", "soda": "SODA", "beer": "BEER", "image": Path(self.current_path).suffix[1:].upper() if self.current_path else "?"}
        fmt_display = fmt_name.get(fmt, fmt.upper())

        if fmt in ("eau", "soda"):
            compression_info = "Compression : LZMA preset 9\nFiltre : Delta horizontal (RGB)\n"
        elif fmt == "beer":
            compression_info = (
                "Compression : LZMA preset 9\n"
                "Pipeline : YCbCr → chroma 4:2:0 → DCT 8×8 → quantification → zigzag → RLE\n"
            )
        else:
            compression_info = ""

        msg = (
            f"Fichier : {os.path.basename(self.current_path) if self.current_path else 'N/A'}\n"
            f"Dimensions : {self.pil_image.width} × {self.pil_image.height} px\n"
            f"Nombre de pixels : {n_pixels:,}\n"
            f"Taille fichier : {file_size:,} octets ({file_size/1024:.1f} Ko)\n"
            f"Bits par pixel : {bpp:.2f} bpp\n"
            f"Format : .{fmt} ({fmt_display})\n"
            f"{compression_info}"
            f"{loss_info}"
        )
        messagebox.showinfo(f"Métadonnées", msg)


def main():
    root = tk.Tk()
    app = EauViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()