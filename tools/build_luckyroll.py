"""Build and verify the standalone LuckyRoll XIPivot DAT overlay pack.

Generates 44 patched retail FFXI DAT files (31 Phantom Rolls, 6 Wild Card,
6 Cutting Cards, 1 Snake Eye) with ultra-readable 256x256 DXT3 Arabic numerals
(1-11) and 512x256 BUST! graphics, per-roll Lucky/Unlucky/11 color coding,
outward-only Euclidean distance-transform black outlines, drop shadows, Lucky
star badges, XI/Jackpot Royal Crown badges, and 33 custom per-roll Tarot Cards.
"""

from __future__ import annotations

import argparse
import math
import os
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def _detect_retail_root() -> Path:
    """Return the first detected retail FINAL FANTASY XI directory containing ROM/."""
    candidates = [
        Path(r"C:\Program Files (x86)\Steam\steamapps\common\FFXINA\SquareEnix\FINAL FANTASY XI"),
        Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY XI\SquareEnix\FINAL FANTASY XI"),
        Path(r"C:\Program Files (x86)\PlayOnline\SquareEnix\FINAL FANTASY XI"),
        Path(r"C:\Program Files\PlayOnline\SquareEnix\FINAL FANTASY XI"),
    ]
    for candidate in candidates:
        if (candidate / "ROM").is_dir():
            return candidate
    return candidates[0]


REPO_ROOT = Path(__file__).resolve().parent.parent
RETAIL_ROOT = _detect_retail_root()
DEFAULT_OUT_PACK = REPO_ROOT / "LuckyRoll"
DEFAULT_PREVIEW_DIR = REPO_ROOT / "assets"
FONT_PATH = Path(r"C:\Windows\Fonts\seguibl.ttf")

SUPERSAMPLE = 4
TEX_SIZE_NUM = 256
TEX_SIZE_BUST = (512, 256)

# Authoritative 31 Phantom Rolls verified against retail FTABLE.DAT (4412 + animId),
# LandSandBoat corsair.lua, and BG-Wiki.
PHANTOM_ROLLS: List[Tuple[str, str, int, int]] = [
    ("ROM/163/90.DAT", "Fighter's Roll", 5, 9),
    ("ROM/162/50.DAT", "Monk's Roll", 3, 7),
    ("ROM/164/45.DAT", "Healer's Roll", 3, 7),
    ("ROM/164/46.DAT", "Wizard's Roll", 5, 9),
    ("ROM/164/47.DAT", "Warlock's Roll", 4, 8),
    ("ROM/164/48.DAT", "Rogue's Roll", 5, 9),
    ("ROM/164/49.DAT", "Gallant's Roll", 3, 7),
    ("ROM/164/50.DAT", "Chaos Roll", 4, 8),
    ("ROM/164/51.DAT", "Beast Roll", 4, 8),
    ("ROM/164/52.DAT", "Choral Roll", 2, 6),
    ("ROM/164/53.DAT", "Hunter's Roll", 4, 8),
    ("ROM/164/54.DAT", "Samurai Roll", 2, 6),
    ("ROM/164/55.DAT", "Ninja Roll", 4, 8),
    ("ROM/164/56.DAT", "Drachen Roll", 4, 8),
    ("ROM/164/57.DAT", "Evoker's Roll", 5, 9),
    ("ROM/164/58.DAT", "Magus's Roll", 2, 6),
    ("ROM/164/59.DAT", "Corsair's Roll", 5, 9),
    ("ROM/164/60.DAT", "Puppet Roll", 3, 7),
    ("ROM/164/61.DAT", "Dancer's Roll", 3, 7),
    ("ROM/198/107.DAT", "Scholar's Roll", 2, 6),
    ("ROM/246/101.DAT", "Bolter's Roll", 3, 9),
    ("ROM/246/102.DAT", "Caster's Roll", 2, 7),
    ("ROM/256/87.DAT", "Courser's Roll", 3, 9),
    ("ROM/256/88.DAT", "Blitzer's Roll", 4, 9),
    ("ROM/261/40.DAT", "Tactician's Roll", 5, 8),
    ("ROM/262/28.DAT", "Allies' Roll", 3, 10),
    ("ROM/265/25.DAT", "Miser's Roll", 5, 7),
    ("ROM/265/32.DAT", "Companion's Roll", 2, 10),
    ("ROM/265/33.DAT", "Avenger's Roll", 4, 8),
    ("ROM/321/72.DAT", "Naturalist's Roll", 3, 7),
    ("ROM/321/73.DAT", "Runeist's Roll", 4, 8),
]

WILD_CARD_DATS = [f"ROM/165/{i}.DAT" for i in range(17, 23)]
CUTTING_CARDS_DATS = [f"ROM/306/{i}.DAT" for i in range(122, 128)]
SNAKE_EYE_DAT = "ROM/184/80.DAT"

# 3-stop vertical gradients (top, mid, bottom) in RGB
PALETTES: Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]] = {
    "normal": ((255, 255, 255), (236, 244, 255), (186, 202, 224)),
    "lucky": ((188, 255, 214), (20, 242, 110), (0, 165, 64)),
    "unlucky": ((255, 152, 152), (255, 34, 34), (180, 0, 14)),
    "eleven": ((255, 250, 190), (255, 208, 20), (230, 126, 0)),
    "snake_eye": ((255, 255, 245), (255, 234, 130), (232, 166, 22)),
    "bust": ((255, 140, 140), (255, 26, 26), (168, 0, 12)),
    "star_gold": ((255, 252, 200), (255, 212, 36), (232, 138, 0)),
    "crown_gold": ((255, 252, 200), (255, 212, 28), (224, 124, 0)),
}

TEX_SIZE_CARD = (256, 512)
CARD_ASPECT_SCALE_X = (256.0 / 512.0) / (1.44 / 2.42)  # 0.8403 compensates 1.19x 3D card stretch

METAL_GRADIENTS: Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]] = {
    "gold": ((214, 184, 98), (168, 124, 34), (92, 60, 12)),
    "silver": ((206, 214, 224), (144, 156, 172), (72, 82, 98)),
    "steel": ((168, 178, 192), (108, 118, 134), (48, 56, 68)),
    "copper": ((214, 152, 108), (156, 88, 46), (82, 40, 16)),
    "crimson_metal": ((218, 92, 102), (156, 30, 44), (74, 10, 18)),
}


@dataclass(frozen=True)
class CardTheme:
    key: str
    title: str
    crest: str
    stat_tag: str
    pattern: str
    bg_dark: Tuple[int, int, int]
    bg_mid: Tuple[int, int, int]
    accent: Tuple[int, int, int]
    metal: str


CARD_THEMES: Dict[str, CardTheme] = {
    "ROM/163/90.DAT": CardTheme("fighter", "FIGHTER", "WAR", "DOUBLE ATK", "chevrons", (20, 24, 32), (50, 56, 70), (232, 78, 38), "steel"),
    "ROM/162/50.DAT": CardTheme("monk", "MONK", "MNK", "SUBTLE BLOW", "sunburst", (44, 22, 6), (112, 56, 12), (228, 142, 32), "gold"),
    "ROM/164/45.DAT": CardTheme("healer", "HEALER", "WHM", "CURE POT", "sunburst", (58, 60, 70), (118, 120, 132), (220, 76, 92), "silver"),
    "ROM/164/46.DAT": CardTheme("wizard", "WIZARD", "BLM", "MAGIC ATK", "rings", (22, 10, 48), (64, 24, 122), (168, 96, 240), "gold"),
    "ROM/164/47.DAT": CardTheme("warlock", "WARLOCK", "RDM", "MAGIC ACC", "stripes", (44, 10, 22), (102, 20, 50), (220, 96, 144), "silver"),
    "ROM/164/48.DAT": CardTheme("rogue", "ROGUE", "THF", "CRIT RATE", "lattice", (8, 34, 26), (18, 80, 60), (58, 196, 148), "silver"),
    "ROM/164/49.DAT": CardTheme("gallant", "GALLANT", "PLD", "DEFENSE", "chevrons", (10, 24, 54), (24, 60, 132), (108, 166, 240), "silver"),
    "ROM/164/50.DAT": CardTheme("chaos", "CHAOS", "DRK", "ATTACK", "lattice", (12, 8, 12), (32, 12, 18), (214, 28, 52), "crimson_metal"),
    "ROM/164/51.DAT": CardTheme("beast", "BEAST", "BST", "PET ATK", "lattice", (38, 22, 10), (94, 54, 22), (204, 142, 64), "copper"),
    "ROM/164/52.DAT": CardTheme("choral", "CHORAL", "BRD", "SPELL INT", "stripes", (42, 14, 42), (104, 36, 104), (226, 120, 214), "gold"),
    "ROM/164/53.DAT": CardTheme("hunter", "HUNTER", "RNG", "ACCURACY", "lattice", (10, 36, 16), (24, 88, 36), (88, 194, 102), "copper"),
    "ROM/164/54.DAT": CardTheme("samurai", "SAMURAI", "SAM", "STORE TP", "sunburst", (42, 10, 8), (104, 22, 14), (236, 120, 42), "gold"),
    "ROM/164/55.DAT": CardTheme("ninja", "NINJA", "NIN", "EVASION", "stripes", (14, 18, 38), (36, 42, 90), (118, 136, 220), "steel"),
    "ROM/164/56.DAT": CardTheme("drachen", "DRACHEN", "DRG", "PET ACC", "chevrons", (8, 28, 56), (20, 70, 136), (84, 174, 244), "silver"),
    "ROM/164/57.DAT": CardTheme("evoker", "EVOKER", "SMN", "REFRESH", "rings", (8, 34, 58), (18, 86, 134), (78, 198, 242), "gold"),
    "ROM/164/58.DAT": CardTheme("magus", "MAGUS", "BLU", "MAGIC DEF", "stripes", (8, 36, 50), (16, 88, 116), (58, 204, 224), "gold"),
    "ROM/164/59.DAT": CardTheme("corsair", "CORSAIR", "COR", "EXP / CP", "stripes", (10, 20, 44), (24, 48, 104), (222, 174, 64), "gold"),
    "ROM/164/60.DAT": CardTheme("puppet", "PUPPET", "PUP", "PET MACC", "lattice", (18, 36, 36), (48, 80, 74), (222, 134, 74), "copper"),
    "ROM/164/61.DAT": CardTheme("dancer", "DANCER", "DNC", "REGEN", "stripes", (48, 10, 32), (118, 22, 78), (242, 96, 166), "gold"),
    "ROM/198/107.DAT": CardTheme("scholar", "SCHOLAR", "SCH", "CONS MP", "rings", (12, 36, 40), (26, 84, 92), (214, 196, 138), "gold"),
    "ROM/246/101.DAT": CardTheme("bolter", "BOLTER", "SPD", "MOVE SPD", "chevrons", (6, 40, 26), (16, 100, 66), (56, 224, 154), "silver"),
    "ROM/246/102.DAT": CardTheme("caster", "CASTER", "FC", "FAST CAST", "rings", (22, 16, 56), (54, 40, 136), (136, 126, 244), "silver"),
    "ROM/256/87.DAT": CardTheme("courser", "COURSER", "SNP", "SNAPSHOT", "sunburst", (42, 28, 10), (106, 72, 20), (226, 174, 60), "copper"),
    "ROM/256/88.DAT": CardTheme("blitzer", "BLITZER", "HST", "HASTE", "sunburst", (46, 18, 6), (118, 48, 12), (242, 134, 38), "gold"),
    "ROM/261/40.DAT": CardTheme("tactician", "TACTICIAN", "TP", "REGAIN", "chevrons", (8, 28, 52), (20, 72, 122), (74, 202, 242), "gold"),
    "ROM/262/28.DAT": CardTheme("allies", "ALLIES", "SC", "SC DMG", "rings", (34, 14, 52), (88, 32, 126), (204, 116, 246), "silver"),
    "ROM/265/25.DAT": CardTheme("miser", "MISER", "STP", "SAVE TP", "lattice", (10, 38, 18), (24, 94, 42), (98, 214, 114), "gold"),
    "ROM/265/32.DAT": CardTheme("companion", "COMPANION", "PET", "PET REGEN", "lattice", (20, 36, 14), (52, 88, 30), (156, 216, 104), "copper"),
    "ROM/265/33.DAT": CardTheme("avenger", "AVENGER", "CTR", "COUNTER", "chevrons", (22, 22, 28), (58, 58, 70), (220, 68, 78), "steel"),
    "ROM/321/72.DAT": CardTheme("naturalist", "NATURALIST", "GEO", "ENH DUR", "rings", (8, 40, 24), (20, 100, 62), (72, 226, 148), "gold"),
    "ROM/321/73.DAT": CardTheme("runeist", "RUNEIST", "RUN", "MAGIC EVA", "rings", (16, 20, 54), (42, 50, 126), (118, 176, 250), "silver"),
    "WILD_CARD": CardTheme("wild_card", "WILD CARD", "WC", "SP RESET", "sunburst", (24, 18, 6), (70, 48, 14), (234, 192, 56), "gold"),
    "CUTTING_CARDS": CardTheme("cutting", "CUTTING", "CC", "SP RECAST", "lattice", (38, 8, 16), (92, 18, 34), (232, 86, 112), "gold"),
}


@dataclass(frozen=True)
class DatSection:
    offset: int
    name: bytes
    stype: int
    size: int
    raw: bytes


def parse_sections(data: bytes) -> List[DatSection]:
    """Parse sequential 16-byte-aligned FFXI DAT sections to EOF."""
    sections: List[DatSection] = []
    pos = 0
    total = len(data)
    while pos + 16 <= total:
        name = data[pos : pos + 4]
        meta = struct.unpack_from("<I", data, pos + 4)[0]
        stype = meta & 0x7F
        ssize = ((meta >> 7) & 0x7FFFF) * 16
        if ssize == 0 or pos + ssize > total:
            raise ValueError(f"Invalid section at 0x{pos:X}: type=0x{stype:02X}, size={ssize}")
        sections.append(DatSection(pos, name, stype, ssize, data[pos : pos + ssize]))
        pos += ssize
    if pos != total:
        raise ValueError(f"Trailing {total - pos} unparsed bytes after 0x{pos:X}")
    return sections


def _exact_edt_window(fg_mask: np.ndarray, max_radius: int) -> np.ndarray:
    """Compute exact Euclidean distance to nearest True pixel, capped at max_radius + 1."""
    h, w = fg_mask.shape
    ys, xs = np.nonzero(fg_mask)
    if len(ys) == 0:
        return np.full((h, w), float(max_radius + 1), dtype=np.float32)

    pad = max_radius + 2
    y0 = max(0, int(ys.min()) - pad)
    y1 = min(h, int(ys.max()) + pad + 1)
    x0 = max(0, int(xs.min()) - pad)
    x1 = min(w, int(xs.max()) + pad + 1)

    roi = fg_mask[y0:y1, x0:x1]
    rh, rw = roi.shape
    inf_val = float((max_radius + 2) ** 2 * 2)

    # Pass 1: exact 1D horizontal squared distance
    d2_x = np.where(roi, 0.0, inf_val).astype(np.float32)
    for dx in range(1, max_radius + 2):
        d2 = float(dx * dx)
        d2_x[:, dx:] = np.minimum(d2_x[:, dx:], np.where(roi[:, :-dx], d2, inf_val))
        d2_x[:, :-dx] = np.minimum(d2_x[:, :-dx], np.where(roi[:, dx:], d2, inf_val))

    # Pass 2: exact 1D vertical squared distance over horizontal minima
    d2_xy = d2_x.copy()
    for dy in range(1, max_radius + 2):
        d2 = float(dy * dy)
        d2_xy[dy:, :] = np.minimum(d2_xy[dy:, :], d2_x[:-dy, :] + d2)
        d2_xy[:-dy, :] = np.minimum(d2_xy[:-dy, :], d2_x[dy:, :] + d2)

    out = np.full((h, w), float(max_radius + 1), dtype=np.float32)
    out[y0:y1, x0:x1] = np.sqrt(np.minimum(d2_xy, float((max_radius + 1) ** 2)))
    return out


def _apply_vertical_gradient(
    alpha_mask: np.ndarray,
    palette_key: str,
    inner_bevel: bool = True,
) -> np.ndarray:
    """Colorize an alpha mask [0..255] with a 3-stop vertical gradient mapped to its bbox."""
    h, w = alpha_mask.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    ys, _ = np.nonzero(alpha_mask > 8)
    if len(ys) == 0:
        return rgba

    y_min = int(ys.min())
    y_max = max(y_min + 1, int(ys.max()))
    t_row = np.clip((np.arange(h, dtype=np.float32) - y_min) / (y_max - y_min), 0.0, 1.0)

    c_top, c_mid, c_bot = [np.array(c, dtype=np.float32) for c in PALETTES[palette_key]]
    grad = np.zeros((h, 3), dtype=np.float32)
    upper = t_row <= 0.48
    t_up = t_row[upper, None] / 0.48
    t_dn = (t_row[~upper, None] - 0.48) / 0.52
    grad[upper] = c_top * (1.0 - t_up) + c_mid * t_up
    grad[~upper] = c_mid * (1.0 - t_dn) + c_bot * t_dn

    rgb = np.broadcast_to(grad[:, None, :], (h, w, 3)).copy()
    if inner_bevel:
        # Subtle crisp bright highlight along upper edge without washing out hue
        shine = np.clip(1.0 - t_row * 3.8, 0.0, 1.0)[:, None, None] * 0.14
        rgb = rgb * (1.0 - shine) + 255.0 * shine

    rgba[:, :, :3] = np.clip(np.round(rgb), 0, 255).astype(np.uint8)
    rgba[:, :, 3] = alpha_mask
    return rgba


def _measure_glyph(font: ImageFont.FreeTypeFont, ch: str) -> Tuple[int, int, int, int]:
    """Return Pillow getbbox (left, top, right, bottom) for a single character."""
    return font.getbbox(ch)


def _render_text_mask(
    canvas_size: Tuple[int, int],
    chars: str,
    font_size: int,
    tracking_px: int,
    center_xy: Tuple[int, int],
    scale_x: float = 1.0,
) -> np.ndarray:
    """Render characters with explicit per-glyph spacing into an alpha mask."""
    font = ImageFont.truetype(str(FONT_PATH), font_size)
    boxes = [_measure_glyph(font, ch) for ch in chars]
    widths = [b[2] - b[0] for b in boxes]
    total_w = sum(widths) + tracking_px * max(0, len(chars) - 1)
    min_top = min(b[1] for b in boxes)
    max_bot = max(b[3] for b in boxes)
    total_h = max_bot - min_top

    # Render onto temporary tight canvas if horizontal compression is requested
    tmp_w = max(canvas_size[0], total_w + 128)
    tmp_h = max(canvas_size[1], total_h + 128)
    tmp = Image.new("L", (tmp_w, tmp_h), 0)
    draw = ImageDraw.Draw(tmp)

    cur_x = (tmp_w - total_w) // 2
    base_y = (tmp_h - total_h) // 2 - min_top
    for ch, b, gw in zip(chars, boxes, widths):
        draw.text((cur_x - b[0], base_y), ch, fill=255, font=font)
        cur_x += gw + tracking_px

    if abs(scale_x - 1.0) > 1e-3:
        new_w = max(1, int(round(tmp_w * scale_x)))
        tmp = tmp.resize((new_w, tmp_h), Image.Resampling.LANCZOS)

    # Crop around rendered mask and paste centered at center_xy
    arr = np.array(tmp, dtype=np.uint8)
    ys, xs = np.nonzero(arr > 0)
    if len(ys) == 0:
        return np.zeros((canvas_size[1], canvas_size[0]), dtype=np.uint8)
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    cropped = tmp.crop((x0, y0, x1, y1))

    out = Image.new("L", canvas_size, 0)
    px = center_xy[0] - (x1 - x0) // 2
    py = center_xy[1] - (y1 - y0) // 2
    out.paste(cropped, (px, py))
    return np.array(out, dtype=np.uint8)


def _draw_star_rgba(
    canvas_size: Tuple[int, int],
    center_xy: Tuple[int, int],
    outer_r: float,
    inner_r: float,
) -> np.ndarray:
    """Draw a crisp 5-point golden star mask & RGBA layer."""
    cx, cy = center_xy
    pts: List[Tuple[float, float]] = []
    for k in range(10):
        ang = -np.pi / 2.0 + k * (np.pi / 5.0)
        r = outer_r if k % 2 == 0 else inner_r
        pts.append((cx + r * float(np.cos(ang)), cy + r * float(np.sin(ang))))
    mask_img = Image.new("L", canvas_size, 0)
    draw = ImageDraw.Draw(mask_img)
    draw.polygon(pts, fill=255)
    mask = np.array(mask_img, dtype=np.uint8)
    return _apply_vertical_gradient(mask, "star_gold", inner_bevel=True)


def _draw_crown_rgba(
    canvas_size: Tuple[int, int],
    center_x: int,
    bottom_y: int,
    width: float,
    height: float,
) -> np.ndarray:
    """Draw a bold geometric 3-peak Royal Crown with base band & peak tips."""
    hw = width * 0.5
    band_h = height * 0.22
    band_gap = height * 0.08
    body_bot = bottom_y - band_h - band_gap
    body_top = bottom_y - height

    # Crisp 3-peak silhouette
    pts = [
        (center_x - hw * 0.86, body_bot),
        (center_x - hw, body_top + height * 0.24),
        (center_x - hw * 0.44, body_top + height * 0.56),
        (center_x, body_top),
        (center_x + hw * 0.44, body_top + height * 0.56),
        (center_x + hw, body_top + height * 0.24),
        (center_x + hw * 0.86, body_bot),
    ]
    mask_img = Image.new("L", canvas_size, 0)
    draw = ImageDraw.Draw(mask_img)
    draw.polygon(pts, fill=255)

    # Bottom curved/rounded crown band
    draw.rounded_rectangle(
        [
            center_x - hw * 0.86,
            bottom_y - band_h,
            center_x + hw * 0.86,
            bottom_y,
        ],
        radius=band_h * 0.38,
        fill=255,
    )

    # Bold pearl tips on each of the 3 peaks
    tip_r = width * 0.075
    for px, py in [
        (center_x - hw, body_top + height * 0.21),
        (center_x, body_top - tip_r * 0.15),
        (center_x + hw, body_top + height * 0.21),
    ]:
        draw.ellipse([px - tip_r, py - tip_r, px + tip_r, py + tip_r], fill=255)

    mask = np.array(mask_img, dtype=np.uint8)
    rgba = _apply_vertical_gradient(mask, "crown_gold", inner_bevel=True)

    # Center crimson-ruby diamond jewel in the crown body for extra legibility
    jewel_cy = body_bot - (body_bot - (body_top + height * 0.56)) * 0.52
    jr = width * 0.075
    j_pts = [
        (center_x, jewel_cy - jr * 1.15),
        (center_x + jr * 0.9, jewel_cy),
        (center_x, jewel_cy + jr * 1.15),
        (center_x - jr * 0.9, jewel_cy),
    ]
    j_img = Image.new("L", canvas_size, 0)
    ImageDraw.Draw(j_img).polygon(j_pts, fill=255)
    j_mask = np.array(j_img, dtype=np.uint8) > 127
    rgba[j_mask, 0] = 235
    rgba[j_mask, 1] = 28
    rgba[j_mask, 2] = 36
    return rgba


def _composite_with_outward_outline(
    fg_rgba: np.ndarray,
    outline_radius_4x: int,
    shadow_offset_y_4x: int = 18,
    shadow_blur_4x: float = 10.0,
    shadow_opacity: float = 0.52,
) -> Image.Image:
    """Wrap fg_rgba in a 100% outward-only solid black border and soft drop shadow."""
    h, w, _ = fg_rgba.shape
    fg_alpha = fg_rgba[:, :, 3]
    dist = _exact_edt_window(fg_alpha >= 128, outline_radius_4x + 4)

    # 2px anti-aliased transition strictly on the outside edge of the black outline
    outline_alpha = np.clip((outline_radius_4x + 1.5 - dist) / 3.0, 0.0, 1.0)
    outline_alpha_u8 = np.round(outline_alpha * 255.0).astype(np.uint8)

    outline_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    outline_arr = np.zeros((h, w, 4), dtype=np.uint8)
    outline_arr[:, :, 3] = outline_alpha_u8
    outline_img = Image.fromarray(outline_arr, "RGBA")

    # Soft dark drop shadow strictly behind outline
    sh_mask = Image.fromarray(outline_alpha_u8, "L")
    sh_shifted = Image.new("L", (w, h), 0)
    sh_shifted.paste(sh_mask, (0, shadow_offset_y_4x))
    sh_blurred = sh_shifted.filter(ImageFilter.GaussianBlur(radius=shadow_blur_4x))
    sh_arr = np.zeros((h, w, 4), dtype=np.uint8)
    sh_arr[:, :, 3] = np.clip(
        np.round(np.array(sh_blurred, dtype=np.float32) * shadow_opacity), 0, 255
    ).astype(np.uint8)
    shadow_img = Image.fromarray(sh_arr, "RGBA")

    fg_img = Image.fromarray(fg_rgba, "RGBA")
    composed = Image.alpha_composite(shadow_img, outline_img)
    composed = Image.alpha_composite(composed, fg_img)
    return composed


def render_roll_graphic(kind: str, value: object) -> Image.Image:
    """Render a supersampled roll graphic and downsample to target DXT3 resolution."""
    if kind == "bust":
        w1, h1 = TEX_SIZE_BUST
        w4, h4 = w1 * SUPERSAMPLE, h1 * SUPERSAMPLE
        mask = _render_text_mask(
            canvas_size=(w4, h4),
            chars="BUST!",
            font_size=570,
            tracking_px=26,
            center_xy=(w4 // 2, h4 // 2 - 14),
            scale_x=0.92,
        )
        fg = _apply_vertical_gradient(mask, "bust", inner_bevel=True)
        full = _composite_with_outward_outline(
            fg, outline_radius_4x=40, shadow_offset_y_4x=18, shadow_blur_4x=10.0
        )
        return full.resize((w1, h1), Image.Resampling.LANCZOS)

    w1 = h1 = TEX_SIZE_NUM
    w4 = h4 = w1 * SUPERSAMPLE
    num = int(value)
    txt = str(num)

    badge_rgba: Optional[np.ndarray] = None
    if kind == "eleven":
        # Center Royal Crown cleanly above a giant separated '11' (or '6' for Wild/Cutting Cards)
        font_sz = 575 if txt == "11" else 590
        trk = 104 if txt == "11" else 0
        sx = 0.96 if txt == "11" else 1.0
        mask = _render_text_mask(
            canvas_size=(w4, h4),
            chars=txt,
            font_size=font_sz,
            tracking_px=trk,
            center_xy=(w4 // 2, 652),
            scale_x=sx,
        )
        fg = _apply_vertical_gradient(mask, "eleven", inner_bevel=True)
        badge_rgba = _draw_crown_rgba(
            canvas_size=(w4, h4),
            center_x=w4 // 2,
            bottom_y=360,
            width=350.0,
            height=205.0,
        )
    elif kind in ("lucky", "snake_eye"):
        # Shift digit slightly down-left so the golden star gleams cleanly in top-right
        pal = "snake_eye" if kind == "snake_eye" else "lucky"
        mask = _render_text_mask(
            canvas_size=(w4, h4),
            chars=txt,
            font_size=700,
            tracking_px=0,
            center_xy=(440, 560),
            scale_x=1.0,
        )
        fg = _apply_vertical_gradient(mask, pal, inner_bevel=True)
        badge_rgba = _draw_star_rgba(
            canvas_size=(w4, h4),
            center_xy=(784, 212),
            outer_r=100.0,
            inner_r=44.0,
        )
    elif kind in ("normal", "unlucky"):
        pal = kind
        if len(txt) == 2:
            # '10': bold separated '1' and '0' filling safe area cleanly
            mask = _render_text_mask(
                canvas_size=(w4, h4),
                chars=txt,
                font_size=710,
                tracking_px=72,
                center_xy=(w4 // 2, 504),
                scale_x=0.83,
            )
        else:
            mask = _render_text_mask(
                canvas_size=(w4, h4),
                chars=txt,
                font_size=830,
                tracking_px=0,
                center_xy=(w4 // 2, 504),
                scale_x=1.0,
            )
        fg = _apply_vertical_gradient(mask, pal, inner_bevel=True)
    else:
        raise ValueError(f"Unknown graphic kind: {kind}")

    if badge_rgba is not None:
        # Composite badge strictly over fg (non-overlapping in practice)
        fg_img = Image.alpha_composite(
            Image.fromarray(fg, "RGBA"), Image.fromarray(badge_rgba, "RGBA")
        )
        fg = np.array(fg_img, dtype=np.uint8)

    full = _composite_with_outward_outline(
        fg, outline_radius_4x=40, shadow_offset_y_4x=18, shadow_blur_4x=10.0
    )
    return full.resize((w1, h1), Image.Resampling.LANCZOS)


def _aspect_text_mask(
    canvas_size: Tuple[int, int],
    chars: str,
    max_font_size: int,
    max_width: int,
    tracking_px: int,
    center_xy: Tuple[int, int],
    scale_x: float = CARD_ASPECT_SCALE_X,
) -> np.ndarray:
    """Render text at up to max_font_size, shrinking cleanly to fit max_width."""
    font_size = max_font_size
    while font_size > 24:
        mask = _render_text_mask(
            canvas_size=canvas_size,
            chars=chars,
            font_size=font_size,
            tracking_px=tracking_px,
            center_xy=center_xy,
            scale_x=scale_x,
        )
        _, xs = np.nonzero(mask > 20)
        if len(xs) == 0 or (int(xs.max()) - int(xs.min()) + 1) <= max_width:
            return mask
        w_cur = int(xs.max()) - int(xs.min()) + 1
        font_size = max(24, int(font_size * (max_width / w_cur) * 0.96))
    return mask


def _draw_aspect_star_mask(
    canvas_size: Tuple[int, int],
    center_xy: Tuple[int, int],
    outer_r: float,
    inner_r: float,
    scale_x: float = CARD_ASPECT_SCALE_X,
) -> np.ndarray:
    """Draw an aspect-compensated 5-point star alpha mask."""
    cx, cy = center_xy
    pts: List[Tuple[float, float]] = []
    for k in range(10):
        ang = -math.pi / 2.0 + k * (math.pi / 5.0)
        r = outer_r if k % 2 == 0 else inner_r
        pts.append((cx + r * scale_x * math.cos(ang), cy + r * math.sin(ang)))
    img = Image.new("L", canvas_size, 0)
    ImageDraw.Draw(img).polygon(pts, fill=255)
    return np.array(img, dtype=np.uint8)


def _draw_aspect_x_mask(
    canvas_size: Tuple[int, int],
    center_xy: Tuple[int, int],
    half_size: float,
    arm_half_w: float,
    scale_x: float = CARD_ASPECT_SCALE_X,
) -> np.ndarray:
    """Draw a bold beveled X alpha mask compensated for card aspect ratio."""
    cx, cy = center_xy
    img = Image.new("L", canvas_size, 0)
    draw = ImageDraw.Draw(img)
    for sign in (-1.0, 1.0):
        # Diagonal bar from (-hs, -sign*hs) to (+hs, +sign*hs)
        dx = half_size
        dy = sign * half_size
        # Perpendicular unit vector in unstretched coords
        px_u = -sign / math.sqrt(2.0) * arm_half_w
        py_u = 1.0 / math.sqrt(2.0) * arm_half_w
        poly = [
            (cx + (-dx + px_u) * scale_x, cy + (-dy + py_u)),
            (cx + (dx + px_u) * scale_x, cy + (dy + py_u)),
            (cx + (dx - px_u) * scale_x, cy + (dy - py_u)),
            (cx + (-dx - px_u) * scale_x, cy + (-dy - py_u)),
        ]
        draw.polygon(poly, fill=255)
    return np.array(img, dtype=np.uint8)


def _apply_custom_gradient(
    alpha_mask: np.ndarray,
    stops: Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]],
    inner_bevel: bool = True,
) -> np.ndarray:
    """Colorize an alpha mask using an explicit 3-stop RGB gradient."""
    h, w = alpha_mask.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    ys, _ = np.nonzero(alpha_mask > 8)
    if len(ys) == 0:
        return rgba
    y_min = int(ys.min())
    y_max = max(y_min + 1, int(ys.max()))
    t_row = np.clip((np.arange(h, dtype=np.float32) - y_min) / (y_max - y_min), 0.0, 1.0)
    c_top, c_mid, c_bot = [np.array(c, dtype=np.float32) for c in stops]
    grad = np.zeros((h, 3), dtype=np.float32)
    upper = t_row <= 0.48
    t_up = t_row[upper, None] / 0.48
    t_dn = (t_row[~upper, None] - 0.48) / 0.52
    grad[upper] = c_top * (1.0 - t_up) + c_mid * t_up
    grad[~upper] = c_mid * (1.0 - t_dn) + c_bot * t_dn
    rgb = np.broadcast_to(grad[:, None, :], (h, w, 3)).copy()
    if inner_bevel:
        shine = np.clip(1.0 - t_row * 3.8, 0.0, 1.0)[:, None, None] * 0.14
        rgb = rgb * (1.0 - shine) + 255.0 * shine
    rgba[:, :, :3] = np.clip(np.round(rgb), 0, 255).astype(np.uint8)
    rgba[:, :, 3] = alpha_mask
    return rgba


def _vertical_gradient_rgb(
    w: int, h: int, top_rgb: Tuple[int, int, int], bot_rgb: Tuple[int, int, int]
) -> np.ndarray:
    """Generate a smooth HxWx3 RGB vertical linear gradient."""
    t = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    c0 = np.array(top_rgb, dtype=np.float32)[None, None, :]
    c1 = np.array(bot_rgb, dtype=np.float32)[None, None, :]
    col = np.clip(np.round(c0 * (1.0 - t) + c1 * t), 0, 255).astype(np.uint8)
    return np.broadcast_to(col, (h, w, 3)).copy()


def _metal_mid_rgb(metal: str) -> Tuple[int, int, int]:
    return METAL_GRADIENTS[metal][1]


def _draw_metallic_card_frame(canvas: Image.Image, theme: CardTheme) -> None:
    """Draw rounded metallic tarot outer rim, bleed edge, inner trim, and corner diamonds."""
    w, h = canvas.size
    m_top, m_mid, m_bot = METAL_GRADIENTS[theme.metal]

    # Rounded mask separating interior art [76..w-77, 76..h-77] from outer rim
    rim_mask = Image.new("L", (w, h), 255)
    ImageDraw.Draw(rim_mask).rounded_rectangle([68, 68, w - 69, h - 69], radius=82, fill=0)

    # Metallic bevel gradient across the outer rim & bleed region
    rim_grad = _vertical_gradient_rgb(w, h, m_top, m_bot)
    rim_rgba = np.dstack([rim_grad, np.array(rim_mask, dtype=np.uint8)])
    canvas.alpha_composite(Image.fromarray(rim_rgba, "RGBA"))

    draw = ImageDraw.Draw(canvas)
    # Dark outer edge bevel and crisp inner black groove
    draw.rounded_rectangle([14, 14, w - 15, h - 15], radius=118, outline=(16, 18, 24), width=12)
    draw.rounded_rectangle([62, 62, w - 63, h - 63], radius=86, outline=(10, 12, 18), width=10)
    # Crisp job-colored inner accent trim
    draw.rounded_rectangle([74, 74, w - 75, h - 75], radius=78, outline=theme.accent + (255,), width=10)
    # Thin dark inner hairline inside accent trim
    draw.rounded_rectangle([84, 84, w - 85, h - 85], radius=70, outline=(10, 12, 18), width=6)

    # Corner diamond studs at all 4 inner corners
    for cx, cy in [(126, 126), (w - 127, 126), (126, h - 127), (w - 127, h - 127)]:
        rx, ry = 22, 26
        pts = [(cx, cy - ry), (cx + rx, cy), (cx, cy + ry), (cx - rx, cy)]
        draw.polygon(pts, fill=m_top + (255,), outline=(12, 14, 20), width=4)


def _draw_divider_bar(draw: ImageDraw.ImageDraw, w: int, y_mid: int, theme: CardTheme) -> None:
    """Draw a metallic horizontal bar with dark bevels and a central diamond clasp."""
    m_top, m_mid, m_bot = METAL_GRADIENTS[theme.metal]
    draw.rectangle([74, y_mid - 14, w - 75, y_mid + 14], fill=(10, 12, 18, 255))
    draw.rectangle([78, y_mid - 9, w - 79, y_mid + 9], fill=m_mid + (255,))
    draw.rectangle([78, y_mid - 9, w - 79, y_mid - 4], fill=m_top + (255,))
    draw.rectangle([78, y_mid + 4, w - 79, y_mid + 9], fill=m_bot + (255,))
    cx = w // 2
    pts = [(cx, y_mid - 22), (cx + 22, y_mid), (cx, y_mid + 22), (cx - 22, y_mid)]
    draw.polygon(pts, fill=theme.accent + (255,), outline=(12, 14, 20), width=5)


def render_card_front(
    theme: CardTheme, lucky: int, unlucky: int, is_special_6: bool = False
) -> Image.Image:
    """Render 256x512 DXT3 Card Front (d0): Roll Title, Dark Window, Lucky/Unlucky Footer."""
    w1, h1 = TEX_SIZE_CARD
    w4, h4 = w1 * SUPERSAMPLE, h1 * SUPERSAMPLE  # 1024 x 2048

    canvas = Image.new("RGBA", (w4, h4), (10, 12, 18, 255))

    # 1. Top Banner Plate (y = 70..514) with subtle pattern watermark
    top_rgb = _vertical_gradient_rgb(w4, 444, theme.bg_mid, theme.bg_dark)
    canvas.paste(Image.fromarray(top_rgb, "RGB").convert("RGBA"), (0, 70))
    tdraw = ImageDraw.Draw(canvas)
    hdr_tint = tuple(min(255, int(c * 1.25) + 12) for c in theme.bg_mid) + (110,)
    if theme.pattern == "stripes":
        for sx in range(84, w4 - 84, 52):
            tdraw.rectangle([sx, 74, sx + 14, 510], fill=hdr_tint)
    elif theme.pattern == "chevrons":
        for sx in range(120, w4 - 120, 120):
            tdraw.line([(sx - 50, 500), (sx, 380), (sx + 50, 500)], fill=hdr_tint, width=14)
    elif theme.pattern == "sunburst":
        for k in range(-4, 5):
            tdraw.line([(w4 // 2, 510), (w4 // 2 + k * 140, 74)], fill=hdr_tint, width=14)
    elif theme.pattern == "rings":
        tdraw.ellipse([w4 // 2 - 220, 70, w4 // 2 + 220, 514], outline=hdr_tint, width=12)
        tdraw.ellipse([w4 // 2 - 360, -30, w4 // 2 + 360, 610], outline=hdr_tint, width=12)
    else:  # lattice
        for sx in range(-300, w4 + 300, 110):
            tdraw.line([(sx, 74), (sx + 320, 510)], fill=hdr_tint, width=12)
            tdraw.line([(sx + 320, 74), (sx, 510)], fill=hdr_tint, width=12)

    # 2. Center Velvet Window (y = 514..1534) — ultra dark with subtle radial falloff
    win_h = 1020
    yy, xx = np.mgrid[0:win_h, 0:w4]
    dx = (xx - w4 * 0.5) / (w4 * 0.45)
    dy = (yy - win_h * 0.5) / (win_h * 0.50)
    rad = np.clip(np.sqrt(dx * dx + dy * dy), 0.0, 1.0)
    edge_tint = np.array(theme.bg_dark, dtype=np.float32) * 0.36
    core_tint = np.array([5.0, 7.0, 11.0], dtype=np.float32)
    w_rgb = core_tint[None, None, :] * (1.0 - (rad[:, :, None] ** 1.6)) + edge_tint[None, None, :] * (
        rad[:, :, None] ** 1.6
    )
    w_rgba = np.zeros((win_h, w4, 4), dtype=np.uint8)
    w_rgba[:, :, :3] = np.clip(np.round(w_rgb), 0, 255).astype(np.uint8)
    w_rgba[:, :, 3] = 255
    canvas.paste(Image.fromarray(w_rgba, "RGBA"), (0, 514))

    # 3. Bottom Footer Plate (y = 1534..1978)
    foot_top = tuple(min(255, int(c * 0.45) + 8) for c in theme.bg_mid)
    foot_bot = tuple(min(255, int(c * 0.35) + 5) for c in theme.bg_dark)
    foot_rgb = _vertical_gradient_rgb(w4, 444, foot_top, foot_bot)
    canvas.paste(Image.fromarray(foot_rgb, "RGB").convert("RGBA"), (0, 1534))

    # Subtle L-bracket corner flourishes strictly in outer corners of dark window
    draw = ImageDraw.Draw(canvas)
    br_col = tuple(min(255, int(c * 0.65) + 25) for c in theme.accent) + (255,)
    for bx, sx in [(118, 1), (w4 - 119, -1)]:
        for by, sy in [(556, 1), (1492, -1)]:
            draw.line([(bx, by + sy * 56), (bx, by), (bx + sx * 52, by)], fill=br_col, width=7)

    # Outer metallic tarot border & divider bars
    _draw_metallic_card_frame(canvas, theme)
    draw = ImageDraw.Draw(canvas)
    _draw_divider_bar(draw, w4, 514, theme)
    _draw_divider_bar(draw, w4, 1534, theme)

    # Vertical center separator in bottom footer
    m_mid = _metal_mid_rgb(theme.metal)
    draw.rectangle([w4 // 2 - 4, 1584, w4 // 2 + 4, 1916], fill=m_mid + (210,))

    # 4. Roll Title in Top Banner
    title_mask = _aspect_text_mask(
        canvas_size=(w4, h4),
        chars=theme.title,
        max_font_size=196,
        max_width=760,
        tracking_px=10,
        center_xy=(w4 // 2, 294),
        scale_x=CARD_ASPECT_SCALE_X,
    )
    title_fg = _apply_vertical_gradient(title_mask, "normal", inner_bevel=True)
    title_comp = _composite_with_outward_outline(
        title_fg, outline_radius_4x=14, shadow_offset_y_4x=8, shadow_blur_4x=4.0
    )
    canvas = Image.alpha_composite(canvas, title_comp)

    # 5. Bottom Cheat-Sheet Footer: Left = Star + Lucky, Right = X + Unlucky (or Crown + 6)
    footer_y = 1756
    # Left half: [100 .. 496], center ~298
    lky_txt = str(lucky)
    if len(lky_txt) == 2:
        star_cx, num_cx, l_fsz, l_sx = 186, 366, 215, 0.72
    else:
        star_cx, num_cx, l_fsz, l_sx = 206, 366, 250, CARD_ASPECT_SCALE_X

    star_mask = _draw_aspect_star_mask(
        (w4, h4), center_xy=(star_cx, footer_y), outer_r=66.0, inner_r=29.0
    )
    star_fg = _apply_vertical_gradient(star_mask, "star_gold", inner_bevel=True)
    lky_mask = _render_text_mask(
        (w4, h4),
        chars=lky_txt,
        font_size=l_fsz,
        tracking_px=14 if len(lky_txt) == 2 else 0,
        center_xy=(num_cx, footer_y - 4),
        scale_x=l_sx,
    )
    lky_fg = _apply_vertical_gradient(lky_mask, "lucky", inner_bevel=True)

    # Right half: [528 .. 924], center ~726
    if is_special_6:
        # Mini Royal Crown + Gold 6
        cr_w, cr_h = 116.0 * CARD_ASPECT_SCALE_X, 78.0
        cr_cx, cr_bot = 636, footer_y + 38
        hw = cr_w * 0.5
        band_h = cr_h * 0.22
        body_bot = cr_bot - band_h - cr_h * 0.08
        body_top = cr_bot - cr_h
        cr_pts = [
            (cr_cx - hw * 0.86, body_bot),
            (cr_cx - hw, body_top + cr_h * 0.24),
            (cr_cx - hw * 0.44, body_top + cr_h * 0.56),
            (cr_cx, body_top),
            (cr_cx + hw * 0.44, body_top + cr_h * 0.56),
            (cr_cx + hw, body_top + cr_h * 0.24),
            (cr_cx + hw * 0.86, body_bot),
        ]
        cr_img = Image.new("L", (w4, h4), 0)
        cd = ImageDraw.Draw(cr_img)
        cd.polygon(cr_pts, fill=255)
        cd.rounded_rectangle(
            [cr_cx - hw * 0.86, cr_bot - band_h, cr_cx + hw * 0.86, cr_bot],
            radius=band_h * 0.35,
            fill=255,
        )
        right_icon_fg = _apply_vertical_gradient(
            np.array(cr_img, dtype=np.uint8), "crown_gold", inner_bevel=True
        )
        r_txt, r_pal, r_cx, r_fsz, r_sx = "6", "eleven", 790, 250, CARD_ASPECT_SCALE_X
    else:
        unl_txt = str(unlucky)
        if len(unl_txt) == 2:
            x_cx, r_cx, r_fsz, r_sx = 612, 792, 215, 0.72
        else:
            x_cx, r_cx, r_fsz, r_sx = 634, 792, 250, CARD_ASPECT_SCALE_X
        x_mask = _draw_aspect_x_mask(
            (w4, h4), center_xy=(x_cx, footer_y), half_size=52.0, arm_half_w=17.0
        )
        right_icon_fg = _apply_vertical_gradient(x_mask, "unlucky", inner_bevel=True)
        r_txt, r_pal = unl_txt, "unlucky"

    r_mask = _render_text_mask(
        (w4, h4),
        chars=r_txt,
        font_size=r_fsz,
        tracking_px=14 if len(r_txt) == 2 else 0,
        center_xy=(r_cx, footer_y - 4),
        scale_x=r_sx,
    )
    r_fg = _apply_vertical_gradient(r_mask, r_pal, inner_bevel=True)

    # Combine all 4 footer icons/digits onto one fg layer and outline together cleanly
    footer_fg = Image.alpha_composite(Image.fromarray(star_fg, "RGBA"), Image.fromarray(lky_fg, "RGBA"))
    footer_fg = Image.alpha_composite(footer_fg, Image.fromarray(right_icon_fg, "RGBA"))
    footer_fg = Image.alpha_composite(footer_fg, Image.fromarray(r_fg, "RGBA"))
    footer_comp = _composite_with_outward_outline(
        np.array(footer_fg, dtype=np.uint8),
        outline_radius_4x=13,
        shadow_offset_y_4x=7,
        shadow_blur_4x=3.5,
    )
    canvas = Image.alpha_composite(canvas, footer_comp)
    return canvas.resize((w1, h1), Image.Resampling.LANCZOS)


def _draw_back_pattern(
    draw: ImageDraw.ImageDraw, w4: int, h4: int, theme: CardTheme, cx: int, cy: int
) -> None:
    """Draw one of 5 bold, DXT3-friendly tarot card-back patterns."""
    pat_col = tuple(min(255, int(c * 1.18) + 10) for c in theme.bg_mid) + (185,)
    acc_col = tuple(min(255, int(c * 0.55) + 12) for c in theme.accent) + (115,)

    if theme.pattern == "sunburst":
        for k in range(18):
            ang = k * (2.0 * math.pi / 18.0)
            col = acc_col if k % 2 == 0 else pat_col
            x1 = cx + int(round(1350 * CARD_ASPECT_SCALE_X * math.cos(ang)))
            y1 = cy + int(round(1350 * math.sin(ang)))
            draw.line([(cx, cy), (x1, y1)], fill=col, width=18)
    elif theme.pattern == "chevrons":
        step = 155
        for y0 in range(-300, h4 + 400, step):
            draw.line([(0, y0 + 260), (cx, y0), (w4, y0 + 260)], fill=pat_col, width=18)
            draw.line([(0, y0 + 335), (cx, y0 + 75), (w4, y0 + 335)], fill=acc_col, width=10)
    elif theme.pattern == "rings":
        for idx, ry_r in enumerate((230, 410, 590, 770, 950)):
            rx_r = int(round(ry_r * CARD_ASPECT_SCALE_X))
            col = acc_col if idx % 2 == 1 else pat_col
            draw.ellipse([cx - rx_r, cy - ry_r, cx + rx_r, cy + ry_r], outline=col, width=14)
        for k in range(8):
            ang = k * (math.pi / 4.0)
            x1 = cx + int(round(1200 * CARD_ASPECT_SCALE_X * math.cos(ang)))
            y1 = cy + int(round(1200 * math.sin(ang)))
            draw.line([(cx, cy), (x1, y1)], fill=acc_col, width=12)
    elif theme.pattern == "stripes":
        for x0 in range(96, w4 - 96, 86):
            draw.rectangle([x0, 96, x0 + 24, h4 - 96], fill=pat_col)
            draw.rectangle([x0 + 36, 96, x0 + 48, h4 - 96], fill=acc_col)
    else:  # lattice
        step_y = 200
        for k in range(-12, 20):
            y0 = k * step_y
            y1 = y0 + int(round(w4 / CARD_ASPECT_SCALE_X))
            y1_neg = y0 - int(round(w4 / CARD_ASPECT_SCALE_X))
            draw.line([(0, y0), (w4, y1)], fill=pat_col, width=15)
            draw.line([(0, y0), (w4, y1_neg)], fill=pat_col, width=15)


def _medallion_geometry(
    pattern: str, cx: int, cy: int, ry: int
) -> Tuple[Optional[List[Tuple[int, int]]], Optional[List[Tuple[int, int]]], float, int]:
    """Return (outer_pts, inner_pts, crest_width_ratio, crest_y_offset) for medallion shape."""
    rx = int(round(ry * CARD_ASPECT_SCALE_X))
    if pattern == "sunburst":
        # Circle handled as ellipse in caller
        return None, None, 1.38, -3
    if pattern == "chevrons":
        # Bold Heraldic Shield
        outer = [
            (cx - rx, cy - int(ry * 0.84)),
            (cx, cy - int(ry * 0.96)),
            (cx + rx, cy - int(ry * 0.84)),
            (cx + rx, cy + int(ry * 0.16)),
            (cx + int(rx * 0.62), cy + int(ry * 0.66)),
            (cx, cy + ry),
            (cx - int(rx * 0.62), cy + int(ry * 0.66)),
            (cx - rx, cy + int(ry * 0.16)),
        ]
        rx_i, ry_i = rx - 24, ry - 28
        inner = [
            (cx - rx_i, cy - int(ry_i * 0.82)),
            (cx, cy - int(ry_i * 0.94)),
            (cx + rx_i, cy - int(ry_i * 0.82)),
            (cx + rx_i, cy + int(ry_i * 0.14)),
            (cx + int(rx_i * 0.60), cy + int(ry_i * 0.64)),
            (cx, cy + ry_i),
            (cx - int(rx_i * 0.60), cy + int(ry_i * 0.64)),
            (cx - rx_i, cy + int(ry_i * 0.14)),
        ]
        return outer, inner, 1.38, -22
    if pattern == "rings":
        # Flat-top/flat-side Octagon
        outer = [
            (cx + int(round(rx * math.cos((k + 0.5) * math.pi / 4.0))),
             cy + int(round(ry * math.sin((k + 0.5) * math.pi / 4.0))))
            for k in range(8)
        ]
        rx_i, ry_i = rx - 24, ry - 28
        inner = [
            (cx + int(round(rx_i * math.cos((k + 0.5) * math.pi / 4.0))),
             cy + int(round(ry_i * math.sin((k + 0.5) * math.pi / 4.0))))
            for k in range(8)
        ]
        return outer, inner, 1.34, -3
    if pattern == "stripes":
        # Pointy-top Hexagon
        outer = [
            (cx + int(round(rx * math.cos(-math.pi / 2.0 + k * math.pi / 3.0))),
             cy + int(round(ry * math.sin(-math.pi / 2.0 + k * math.pi / 3.0))))
            for k in range(6)
        ]
        rx_i, ry_i = rx - 24, ry - 28
        inner = [
            (cx + int(round(rx_i * math.cos(-math.pi / 2.0 + k * math.pi / 3.0))),
             cy + int(round(ry_i * math.sin(-math.pi / 2.0 + k * math.pi / 3.0))))
            for k in range(6)
        ]
        return outer, inner, 1.24, -3
    # lattice -> Diamond
    outer = [(cx, cy - ry), (cx + rx, cy), (cx, cy + ry), (cx - rx, cy)]
    inner = [(cx, cy - ry + 28), (cx + rx - 24, cy), (cx, cy + ry - 28), (cx - rx + 24, cy)]
    return outer, inner, 1.08, -3


def render_card_back(theme: CardTheme) -> Image.Image:
    """Render 256x512 DXT3 Card Back (c0): Distinct Pattern, Medallion, Name Ribbon & Stat Tag."""
    w1, h1 = TEX_SIZE_CARD
    w4, h4 = w1 * SUPERSAMPLE, h1 * SUPERSAMPLE  # 1024 x 2048

    # Rich vertical satin gradient (dark -> mid -> dark)
    top_half = _vertical_gradient_rgb(w4, h4 // 2, theme.bg_dark, theme.bg_mid)
    bot_half = _vertical_gradient_rgb(w4, h4 // 2, theme.bg_mid, theme.bg_dark)
    bg_rgb = np.vstack([top_half, bot_half])
    canvas = Image.fromarray(bg_rgb, "RGB").convert("RGBA")

    draw = ImageDraw.Draw(canvas)
    cx, cy = w4 // 2, 765
    _draw_back_pattern(draw, w4, h4, theme, cx, cy)

    # Inner decorative tarot double frame
    m_top, m_mid, m_bot = METAL_GRADIENTS[theme.metal]
    draw.rounded_rectangle([118, 118, w4 - 119, h4 - 119], radius=54, outline=m_mid + (210,), width=10)

    # Outer metallic border
    _draw_metallic_card_frame(canvas, theme)
    draw = ImageDraw.Draw(canvas)

    # Medallion shaped by theme.pattern
    ry = 310
    rx = int(round(ry * CARD_ASPECT_SCALE_X))
    outer_pts, inner_pts, width_ratio, crest_dy = _medallion_geometry(theme.pattern, cx, cy, ry)
    core_col = tuple(max(8, int(c * 0.36)) for c in theme.bg_dark) + (255,)

    if outer_pts is None:
        # Sunburst -> Circle Medallion
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(10, 12, 18, 255), outline=m_top + (255,), width=16)
        draw.ellipse(
            [cx - rx + 24, cy - ry + 28, cx + rx - 24, cy + ry - 28],
            fill=core_col,
            outline=theme.accent + (255,),
            width=8,
        )
    else:
        draw.polygon(outer_pts, fill=(10, 12, 18, 255))
        draw.polygon(inner_pts, fill=core_col)
        draw.polygon(outer_pts, outline=m_top + (255,), width=16)
        draw.polygon(inner_pts, outline=theme.accent + (255,), width=8)

    # Bold Job/Roll Crest Code centered cleanly inside the medallion
    crest_mask = _aspect_text_mask(
        canvas_size=(w4, h4),
        chars=theme.crest,
        max_font_size=168,
        max_width=int(rx * width_ratio),
        tracking_px=10,
        center_xy=(cx, cy + crest_dy),
        scale_x=CARD_ASPECT_SCALE_X,
    )
    crest_fg = _apply_custom_gradient(crest_mask, METAL_GRADIENTS[theme.metal], inner_bevel=True)
    crest_comp = _composite_with_outward_outline(
        crest_fg, outline_radius_4x=14, shadow_offset_y_4x=8, shadow_blur_4x=4.0
    )
    canvas = Image.alpha_composite(canvas, crest_comp)

    # Lower Name Ribbon Banner (y = 1230..1490)
    draw = ImageDraw.Draw(canvas)
    rib_top, rib_bot = 1230, 1490
    draw.rounded_rectangle(
        [108, rib_top, w4 - 109, rib_bot],
        radius=36,
        fill=theme.bg_dark + (245,),
        outline=m_top + (255,),
        width=12,
    )
    draw.rounded_rectangle(
        [124, rib_top + 16, w4 - 125, rib_bot - 16],
        radius=24,
        outline=theme.accent + (220,),
        width=6,
    )

    name_mask = _aspect_text_mask(
        canvas_size=(w4, h4),
        chars=theme.title,
        max_font_size=158,
        max_width=690,
        tracking_px=8,
        center_xy=(cx, (rib_top + rib_bot) // 2 - 4),
        scale_x=CARD_ASPECT_SCALE_X,
    )
    name_fg = _apply_vertical_gradient(name_mask, "normal", inner_bevel=True)
    name_comp = _composite_with_outward_outline(
        name_fg, outline_radius_4x=12, shadow_offset_y_4x=6, shadow_blur_4x=3.5
    )
    canvas = Image.alpha_composite(canvas, name_comp)

    # Stat Tag Pill (y = 1550..1765)
    draw = ImageDraw.Draw(canvas)
    st_top, st_bot = 1550, 1765
    draw.rounded_rectangle(
        [140, st_top, w4 - 141, st_bot],
        radius=42,
        fill=(10, 12, 18, 240),
        outline=theme.accent + (255,),
        width=9,
    )
    stat_mask = _aspect_text_mask(
        canvas_size=(w4, h4),
        chars=theme.stat_tag,
        max_font_size=114,
        max_width=630,
        tracking_px=6,
        center_xy=(cx, (st_top + st_bot) // 2 - 2),
        scale_x=CARD_ASPECT_SCALE_X,
    )
    stat_top_c = tuple(min(255, int(c * 0.45 + 150)) for c in theme.accent)
    stat_fg = _apply_custom_gradient(stat_mask, (stat_top_c, theme.accent, theme.accent), inner_bevel=True)
    stat_comp = _composite_with_outward_outline(
        stat_fg, outline_radius_4x=10, shadow_offset_y_4x=5, shadow_blur_4x=3.0
    )
    canvas = Image.alpha_composite(canvas, stat_comp)
    return canvas.resize((w1, h1), Image.Resampling.LANCZOS)


def _card_group_offsets(tag: str, sec_len: int) -> Tuple[int, int, List[int]]:
    """Return (vertex_start, num_cd_verts, list_of_48_vert_group_offsets) for c1-c6 or wc."""
    if tag in ("c1", "c2", "c3", "c4", "c5", "c6"):
        if sec_len != 4400:
            raise ValueError(f"{tag}: expected 4400 bytes, got {sec_len}")
        v_start = 0x4E
        return v_start, 96, [v_start, v_start + 48 * 36]
    if tag == "wc":
        if sec_len != 26096:
            raise ValueError(f"wc: expected 26096 bytes, got {sec_len}")
        v_start = 0xA8
        groups = [v_start + g * 48 * 36 for g in range(12)]
        return v_start, 576, groups
    raise ValueError(f"Unsupported card mesh tag: {tag}")


def unwrap_card_mesh_section(sec: DatSection) -> bytes:
    """Un-mirror c0/d0 UVs across each 48-vert card face; flip wc ring outward so numbers face out."""
    tag = sec.name.decode("ascii", "replace").strip()
    _, _, groups = _card_group_offsets(tag, len(sec.raw))
    buf = bytearray(sec.raw)

    if tag == "wc":
        # Swap sub[0] (outside, r=2.510) and sub[1] (inside, r=2.490) texture slots so Front (d0) faces OUT!
        s0 = bytes(buf[0x28:0x38])
        s1 = bytes(buf[0x38:0x48])
        buf[0x28:0x38] = s1
        buf[0x38:0x48] = s0

    for g_off in groups:
        xs: List[float] = []
        ys: List[float] = []
        zs: List[float] = []
        norms: List[Tuple[float, float, float]] = []
        for i in range(48):
            vo = g_off + i * 36
            px, py, pz, nx, ny, nz = struct.unpack_from("<6f", buf, vo)
            xs.append(px)
            ys.append(py)
            zs.append(pz)
            norms.append((nx, ny, nz))

        cx = 0.5 * (min(xs) + max(xs))
        cy = 0.5 * (min(ys) + max(ys))
        cz = 0.5 * (min(zs) + max(zs))
        nx0, _, nz0 = norms[0]
        rlen = math.hypot(nz0, -nx0)
        if rlen < 1e-5:
            raise ValueError(f"{tag}: degenerate horizontal normal at group 0x{g_off:X}")
        rx, rz = nz0 / rlen, -nx0 / rlen

        for i in range(48):
            vo = g_off + i * 36
            lx = (xs[i] - cx) * rx + (zs[i] - cz) * rz
            ly = ys[i] - cy
            u = max(0.016, min(0.984, 0.016 + (lx / 1.44 + 0.5) * (0.984 - 0.016)))
            v = max(0.016, min(0.984, 0.016 + (ly / 2.42 + 0.5) * (0.984 - 0.016)))
            struct.pack_into("<4B2f", buf, vo + 24, 178, 178, 178, 128, u, v)

    if tag == "wc":
        # Flip sub[2..7] (j2, j1, j3, j4, j5, j6: 6 * 8 tris = 144 verts) outward by +0.040 to r=2.520
        j_start = 0xA8 + 576 * 36
        for tri in range(48):
            t_off = j_start + tri * 3 * 36
            verts_new = []
            for k in range(3):
                vo = t_off + k * 36
                px, py, pz, nx, ny, nz, b, g, r, a, u, v = struct.unpack_from("<6f4B2f", buf, vo)
                verts_new.append((
                    px + 0.040 * nx,
                    py,
                    pz + 0.040 * nz,
                    -nx,
                    -ny,
                    -nz,
                    b,
                    g,
                    r,
                    a,
                    1.0 - u,
                    v,
                ))
            # Write v0', v2', v1' to reverse triangle winding for negated outward normal
            for dst_k, vdata in enumerate((verts_new[0], verts_new[2], verts_new[1])):
                struct.pack_into("<6f4B2f", buf, t_off + dst_k * 36, *vdata)

    return bytes(buf)


RENAMED_COR_SUFFIXES = (
    "d0",
    "c0",
    "bust",
    "j1",
    "j2",
    "j3",
    "j4",
    "j5",
    "j6",
    "j7",
    "j8",
    "j9",
    "j10",
    "j11",
)
RENAMED_COR_OLD_NAMES: Dict[bytes, str] = {
    f"cor_cd01{s}".ljust(16).encode("ascii"): s for s in RENAMED_COR_SUFFIXES
}


def rename_mesh_tex_refs(sec_name: bytes, sec_bytes: bytes, prefix_8: bytes) -> Tuple[bytes, int]:
    """Rename exact 16-byte cor_cd01* submesh texture slots in a 0x1F mesh header."""
    if len(prefix_8) != 8:
        raise ValueError(f"Expected 8-byte texture prefix, got {prefix_8!r}")
    num_sub = struct.unpack_from("<H", sec_bytes, 0x14)[0]
    tex_off = 0x18 + max(6, num_sub * 2)
    if tex_off + num_sub * 16 > len(sec_bytes):
        raise ValueError(f"{sec_name!r}: 0x1F texture table exceeds section length")

    buf = bytearray(sec_bytes)
    renamed = 0
    for slot in range(num_sub):
        off = tex_off + slot * 16
        cur = bytes(buf[off : off + 16])
        suffix = RENAMED_COR_OLD_NAMES.get(cur)
        if suffix is not None:
            buf[off : off + 16] = prefix_8 + suffix.ljust(8).encode("ascii")
            renamed += 1
    return bytes(buf), renamed


def verify_card_mesh_section(
    rel: str, retail_sec: DatSection, mod_sec: DatSection, tex_prefix: Optional[bytes] = None
) -> int:
    """Verify card mesh sizes, un-mirrored UVs, and outward-flipped wc spinning ring."""
    tag = mod_sec.name.decode("ascii", "replace").strip()
    if len(mod_sec.raw) != len(retail_sec.raw):
        raise AssertionError(f"{rel} {tag}: mesh size changed {len(retail_sec.raw)} -> {len(mod_sec.raw)}")

    v_start, n_cd_verts, groups = _card_group_offsets(tag, len(mod_sec.raw))
    cd_end = v_start + n_cd_verts * 36

    exp_raw_base = bytearray(retail_sec.raw)
    if tag == "wc":
        # Expect swapped sub[0] (d0) and sub[1] (c0) texture slots
        s0 = bytes(exp_raw_base[0x28:0x38])
        s1 = bytes(exp_raw_base[0x38:0x48])
        exp_raw_base[0x28:0x38] = s1
        exp_raw_base[0x38:0x48] = s0

    renamed_cnt = 0
    if tex_prefix is not None:
        renamed_full, renamed_cnt = rename_mesh_tex_refs(retail_sec.name, bytes(exp_raw_base), tex_prefix)
        expected_hdr = renamed_full[:v_start]
    else:
        expected_hdr = bytes(exp_raw_base[:v_start])

    if mod_sec.raw[:v_start] != expected_hdr:
        raise AssertionError(f"{rel} {tag}: mesh header/tex table mismatch")

    if tag != "wc":
        if mod_sec.raw[cd_end:] != retail_sec.raw[cd_end:]:
            raise AssertionError(f"{rel} {tag}: j-submesh or trailing pad modified")
    else:
        # Verify wc sub[0] is d0 (front outside) and sub[1] is c0 (back inside)
        if not mod_sec.raw[0x28:0x38].rstrip(b" \x00").endswith(b"d0"):
            raise AssertionError(f"{rel} wc: sub[0] is not d0 ({mod_sec.raw[0x28:0x38]!r})")
        if not mod_sec.raw[0x38:0x48].rstrip(b" \x00").endswith(b"c0"):
            raise AssertionError(f"{rel} wc: sub[1] is not c0 ({mod_sec.raw[0x38:0x48]!r})")
        # Verify trailing 8 pad bytes untouched
        j_end = cd_end + 144 * 36
        if mod_sec.raw[j_end:] != retail_sec.raw[j_end:]:
            raise AssertionError(f"{rel} wc: trailing padding altered")
        # Verify all 6 outward-flipped j-submeshes (24 verts each)
        for si in range(6):
            svo = cd_end + si * 24 * 36
            verts_24 = []
            for tri in range(8):
                tri_pts = []
                for k in range(3):
                    px, py, pz, nx, ny, nz, b, g, r, a, u, v = struct.unpack_from(
                        "<6f4B2f", mod_sec.raw, svo + (tri * 3 + k) * 36
                    )
                    rad = math.hypot(px, pz)
                    if not (2.51 < rad < 2.60):
                        raise AssertionError(f"{rel} wc j-sub[{si}]: unexpected vertex radius {rad:.4f}")
                    tri_pts.append((px, py, pz, nx, ny, nz, u, v))
                    verts_24.append((px, py, pz, nx, ny, nz, u, v))
                p0, p1, p2 = tri_pts
                e1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
                e2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
                cr = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
                dot_wn = cr[0] * p0[3] + cr[1] * p0[4] + cr[2] * p0[5]
                if dot_wn <= 0.1:
                    raise AssertionError(f"{rel} wc j-sub[{si}] tri[{tri}]: bad winding dot={dot_wn:.3f}")
            cx = 0.5 * (min(t[0] for t in verts_24) + max(t[0] for t in verts_24))
            cz = 0.5 * (min(t[2] for t in verts_24) + max(t[2] for t in verts_24))
            c_rad = math.hypot(cx, cz)
            if not (2.51 < c_rad < 2.53):
                raise AssertionError(f"{rel} wc j-sub[{si}]: unexpected center radius {c_rad:.4f}")
            nx0, _, nz0 = verts_24[0][3:6]
            if nx0 * cx + nz0 * cz > -2.45:
                raise AssertionError(f"{rel} wc j-sub[{si}]: normal does not point outward-visible (dot={nx0*cx+nz0*cz:.2f})")
            tl = min(verts_24, key=lambda t: t[6] + t[7])
            tr = min(verts_24, key=lambda t: (1.0 - t[6]) + t[7])
            du_x, du_z = tr[0] - tl[0], tr[2] - tl[2]
            if du_x * nz0 + du_z * (-nx0) <= 0.5:
                raise AssertionError(f"{rel} wc j-sub[{si}]: UV u is mirrored!")

    for g_off in groups:
        us: List[float] = []
        vs: List[float] = []
        for i in range(48):
            vo = g_off + i * 36
            if mod_sec.raw[vo : vo + 24] != retail_sec.raw[vo : vo + 24]:
                raise AssertionError(f"{rel} {tag}: pos/normal changed at 0x{vo:X}")
            b, g, r, a, u, v = struct.unpack_from("<4B2f", mod_sec.raw, vo + 24)
            if (b, g, r, a) != (178, 178, 178, 128):
                raise AssertionError(f"{rel} {tag}: non-neutral bgra {(b, g, r, a)} at 0x{vo:X}")
            if not (0.0159 <= u <= 0.9841 and 0.0159 <= v <= 0.9841):
                raise AssertionError(f"{rel} {tag}: UV out of bounds ({u:.4f}, {v:.4f})")
            us.append(u)
            vs.append(v)
        if min(us) > 0.05 or max(us) < 0.95 or min(vs) > 0.05 or max(vs) < 0.95:
            raise AssertionError(
                f"{rel} {tag}: UVs do not span full un-mirrored card "
                f"u=[{min(us):.3f},{max(us):.3f}] v=[{min(vs):.3f},{max(vs):.3f}]"
            )
    return renamed_cnt


def encode_dxt3(img: Image.Image) -> bytes:
    """Encode an RGBA Pillow image to top-down DXT3 bytes with alpha-masked endpoints."""
    rgba = np.array(img.convert("RGBA"), dtype=np.uint8)
    h, w, _ = rgba.shape
    if h % 4 != 0 or w % 4 != 0:
        raise ValueError(f"DXT3 dimensions must be multiples of 4, got {w}x{h}")

    blocks = (
        rgba.reshape(h // 4, 4, w // 4, 4, 4)
        .transpose(0, 2, 1, 3, 4)
        .reshape(-1, 16, 4)
    )
    n = blocks.shape[0]

    # 1. Explicit 4-bit alpha block (little-endian uint64)
    a4 = np.clip(np.round(blocks[:, :, 3].astype(np.float32) / 17.0), 0, 15).astype(np.uint64)
    a_shifts = (np.arange(16, dtype=np.uint64) * 4)[None, :]
    alpha_u64 = np.bitwise_or.reduce(a4 << a_shifts, axis=1)

    # 2. Color block: ignore fully transparent pixels so black (0,0,0,0) never bleeds!
    vis = blocks[:, :, 3] > 0  # (N, 16)
    rgb = blocks[:, :, :3].astype(np.float32)  # (N, 16, 3)

    # Zero out invisible pixels in mean/min/max calculations
    vis_cnt = vis.sum(axis=1)  # (N,)
    non_empty = vis_cnt > 0
    rgb_masked = np.where(vis[:, :, None], rgb, 0.0)

    c0_u16 = np.zeros(n, dtype=np.uint16)
    c1_u16 = np.zeros(n, dtype=np.uint16)
    idx_u32 = np.zeros(n, dtype=np.uint32)

    if np.any(non_empty):
        rgb_ne = rgb[non_empty]  # (M, 16, 3)
        vis_ne = vis[non_empty]  # (M, 16)
        cnt_ne = vis_cnt[non_empty].astype(np.float32)[:, None]  # (M, 1)

        mean = np.where(vis_ne[:, :, None], rgb_ne, 0.0).sum(axis=1) / cnt_ne  # (M, 3)
        centered = np.where(vis_ne[:, :, None], rgb_ne - mean[:, None, :], 0.0)  # (M, 16, 3)

        # Principal axis of visible colors via 3 power iterations on 3x3 covariance
        cov = np.einsum("mpi,mpj->mij", centered, centered)
        axis = np.broadcast_to(
            np.array([0.57735, 0.57735, 0.57735], dtype=np.float32), (cov.shape[0], 3)
        ).copy()
        for _ in range(3):
            nxt = np.einsum("mij,mj->mi", cov, axis)
            nrm = np.linalg.norm(nxt, axis=1, keepdims=True)
            valid_nrm = nrm[:, 0] > 1e-6
            axis[valid_nrm] = nxt[valid_nrm] / nrm[valid_nrm]

        proj = np.einsum("mpi,mi->mp", centered, axis)
        proj_max = np.where(vis_ne, proj, -1e9)
        proj_min = np.where(vis_ne, proj, 1e9)
        i_max = np.argmax(proj_max, axis=1)
        i_min = np.argmin(proj_min, axis=1)

        m_idx = np.arange(rgb_ne.shape[0])
        p_max = rgb_ne[m_idx, i_max]  # (M, 3)
        p_min = rgb_ne[m_idx, i_min]  # (M, 3)

        def to_rgb565(p: np.ndarray) -> np.ndarray:
            r5 = np.clip(np.round(p[:, 0] * 31.0 / 255.0), 0, 31).astype(np.uint16)
            g6 = np.clip(np.round(p[:, 1] * 63.0 / 255.0), 0, 63).astype(np.uint16)
            b5 = np.clip(np.round(p[:, 2] * 31.0 / 255.0), 0, 31).astype(np.uint16)
            return (r5 << 11) | (g6 << 5) | b5

        c0 = to_rgb565(p_max)
        c1 = to_rgb565(p_min)
        swap = c0 < c1
        c0_s = np.where(swap, c1, c0)
        c1_s = np.where(swap, c0, c1)

        def expand_565(c: np.ndarray) -> np.ndarray:
            r5 = (c >> 11) & 0x1F
            g6 = (c >> 5) & 0x3F
            b5 = c & 0x1F
            r8 = (r5 << 3) | (r5 >> 2)
            g8 = (g6 << 2) | (g6 >> 4)
            b8 = (b5 << 3) | (b5 >> 2)
            return np.stack([r8, g8, b8], axis=-1).astype(np.float32)

        e0 = expand_565(c0_s)
        e1 = expand_565(c1_s)
        e2 = np.floor((2.0 * e0 + e1) / 3.0)
        e3 = np.floor((e0 + 2.0 * e1) / 3.0)
        pal = np.stack([e0, e1, e2, e3], axis=1)  # (M, 4, 3)

        diff = rgb_ne[:, :, None, :] - pal[:, None, :, :]  # (M, 16, 4, 3)
        dist2 = np.sum(diff * diff, axis=3)  # (M, 16, 4)
        best = np.argmin(dist2, axis=2).astype(np.uint32)  # (M, 16)
        # Keep invisible pixels cleanly at index closest to black (doesn't affect visible)
        i_shifts = (np.arange(16, dtype=np.uint32) * 2)[None, :]
        packed_idx = np.bitwise_or.reduce(best << i_shifts, axis=1)

        c0_u16[non_empty] = c0_s
        c1_u16[non_empty] = c1_s
        idx_u32[non_empty] = packed_idx

    dxt_dtype = np.dtype([("a", "<u8"), ("c0", "<u2"), ("c1", "<u2"), ("idx", "<u4")])
    out = np.empty(n, dtype=dxt_dtype)
    out["a"] = alpha_u64
    out["c0"] = c0_u16
    out["c1"] = c1_u16
    out["idx"] = idx_u32
    return out.tobytes()


def decode_dxt3(buf: bytes, w: int, h: int) -> Image.Image:
    """Decode top-down FFXI DXT3 byte stream back to an RGBA Pillow image."""
    dxt_dtype = np.dtype([("a", "<u8"), ("c0", "<u2"), ("c1", "<u2"), ("idx", "<u4")])
    arr = np.frombuffer(buf, dtype=dxt_dtype, count=(w // 4) * (h // 4))

    a_shifts = (np.arange(16, dtype=np.uint64) * 4)[None, :]
    a4 = ((arr["a"][:, None] >> a_shifts) & 0xF).astype(np.uint8)
    a8 = a4 * np.uint8(17)

    def expand_565(c: np.ndarray) -> np.ndarray:
        r5 = (c >> 11) & 0x1F
        g6 = (c >> 5) & 0x3F
        b5 = c & 0x1F
        r8 = (r5 << 3) | (r5 >> 2)
        g8 = (g6 << 2) | (g6 >> 4)
        b8 = (b5 << 3) | (b5 >> 2)
        return np.stack([r8, g8, b8], axis=-1).astype(np.int32)

    e0 = expand_565(arr["c0"])
    e1 = expand_565(arr["c1"])
    e2 = (2 * e0 + e1) // 3
    e3 = (e0 + 2 * e1) // 3
    pal = np.stack([e0, e1, e2, e3], axis=1).astype(np.uint8)  # (N, 4, 3)

    i_shifts = (np.arange(16, dtype=np.uint32) * 2)[None, :]
    idx = (arr["idx"][:, None] >> i_shifts) & 3  # (N, 16)
    rgb = pal[np.arange(len(arr))[:, None], idx]  # (N, 16, 3)

    rgba_blocks = np.concatenate([rgb, a8[:, :, None]], axis=-1)  # (N, 16, 4)
    img_arr = (
        rgba_blocks.reshape(h // 4, w // 4, 4, 4, 4)
        .transpose(0, 2, 1, 3, 4)
        .reshape(h, w, 4)
    )
    return Image.fromarray(img_arr, "RGBA")


def build_0x20_section(
    sec_name: bytes, tex_name_16: bytes, w: int, h: int, dxt_bytes: bytes
) -> bytes:
    """Build a valid 16-byte-aligned FFXI 0x20 (0xA1 3TXD DXT3) texture section."""
    dxt_sz = w * h
    if len(dxt_bytes) != dxt_sz:
        raise ValueError(f"Expected {dxt_sz} DXT3 bytes for {w}x{h}, got {len(dxt_bytes)}")
    raw_len = 85 + dxt_sz
    ssize = ((raw_len + 15) // 16) * 16
    pad = ssize - raw_len
    meta = ((ssize // 16) << 7) | 0x20

    header = bytearray()
    header += sec_name
    header += struct.pack("<I", meta)
    header += b"\x00" * 8
    header.append(0xA1)
    header += tex_name_16
    header += struct.pack("<IiiHHIIiiII", 40, w, h, 1, 8, 0, 0, 0, 0, 0, 0x20)
    header += b"3TXD"
    header += struct.pack("<II", dxt_sz, w * 4)
    if len(header) != 85:
        raise AssertionError(f"Header must be 85 bytes, got {len(header)}")
    return bytes(header) + dxt_bytes + (b"\x00" * pad)


CARD_MESH_TAGS = ("c1", "c2", "c3", "c4", "c5", "c6", "wc")
THEME_BY_KEY: Dict[str, CardTheme] = {t.key: t for t in CARD_THEMES.values()}

PHANTOM_RETAIL_LIFE = 88
PHANTOM_EXTEND_LIFE = 150
PHANTOM_TAIL_DELTA = PHANTOM_EXTEND_LIFE - PHANTOM_RETAIL_LIFE
PHANTOM_PJ_GENS: Set[str] = {f"pj{i:02d}" for i in range(1, 12)} | {"pjbu"}
PHANTOM_YC_SCHEDS: Set[str] = {f"yc{i:02d}" for i in range(1, 13)}
PHANTOM_JA00_FLOATS: List[float] = [0.0, 0.0, 0.20, 0.42, 0.88, 0.42, 0.95, 0.04, 1.0, 0.0, 0.0, 0.0]
PHANTOM_JA01_FLOATS: List[float] = [0.0, 0.0, 0.08, 0.42, 0.82, 0.42, 0.93, 0.04, 1.0, 0.0, 0.0, 0.0]

CARD_SP_RETAIL_LIFE = 64
CARD_SP_EXTEND_LIFE = 120
CARD_SP_TAIL_DELTA = 30
CARD_SP_JA00_FLOATS: List[float] = [0.0, 0.0, 0.13, 0.42, 0.85, 0.42, 0.91, 0.18, 0.955, 0.052, 1.0, 0.0]
CARD_SP_JSSX_TIMES: List[float] = [0.85, 0.87, 0.89, 0.92, 1.0]


def build_timing_map() -> Dict[str, Tuple[str, Optional[int]]]:
    """Return mapping: rel_dat_path -> (timing_mode, sp_index_or_none)."""
    timing: Dict[str, Tuple[str, Optional[int]]] = {}
    for rel, _, _, _ in PHANTOM_ROLLS:
        timing[rel] = ("phantom", None)
    for idx, rel in enumerate(WILD_CARD_DATS, start=1):
        timing[rel] = ("card_sp", idx)
    for idx, rel in enumerate(CUTTING_CARDS_DATS, start=1):
        timing[rel] = ("card_sp", idx)
    return timing


def patch_0x05_life(raw: bytes, old_life: int, new_life: int) -> bytes:
    """Extend particle lifetime (uint16 frames at +0xC2) inside a 0x05 generator."""
    cur_life = struct.unpack_from("<H", raw, 0xC2)[0]
    if cur_life != old_life:
        raise ValueError(f"0x05 generator unexpected lifetime {cur_life} != {old_life}")
    buf = bytearray(raw)
    struct.pack_into("<H", buf, 0xC2, new_life)
    return bytes(buf)


def patch_0x07_duration(
    raw: bytes,
    target_gen_tags: Set[str],
    old_dur: int,
    new_dur: int,
    tail_delta: int,
    expected_tail_f1: Optional[int] = None,
) -> bytes:
    """Extend a target generator spawn duration (f2) and tail wait (f1 + total_frames) in a 0x07 scheduler."""
    main_off, end_off, tf = struct.unpack_from("<III", raw, 0x24)
    buf = bytearray(raw)

    off = main_off
    sum_f1 = 0
    patched_gen = 0
    last_cmd_off: Optional[int] = None
    while off < end_off:
        op = buf[off]
        dw = buf[off + 1]
        if dw == 0:
            raise ValueError(f"Invalid zero-length command at +0x{off:x}")
        sz = dw * 4
        if op == 0x00:
            break
        if op != 0x01:
            f1, f2 = struct.unpack_from("<HH", buf, off + 4)
            sum_f1 += f1
            last_cmd_off = off
            if op == 0x02 and sz >= 12:
                tag = bytes(buf[off + 8 : off + 12]).decode("ascii", "replace").strip()
                if tag in target_gen_tags:
                    if f2 != old_dur:
                        raise ValueError(f"0x07 tag {tag!r} unexpected dur {f2} != {old_dur}")
                    struct.pack_into("<H", buf, off + 6, new_dur)
                    patched_gen += 1
        off += sz

    if sum_f1 != tf:
        raise ValueError(f"0x07 pre-patch frame sum {sum_f1} != total_frames {tf}")
    if patched_gen != 1:
        raise ValueError(f"0x07 expected 1 target generator match, got {patched_gen}")
    if last_cmd_off is None:
        raise ValueError("0x07 scheduler missing non-START commands")

    tail_f1 = struct.unpack_from("<H", buf, last_cmd_off + 4)[0]
    if expected_tail_f1 is not None and tail_f1 != expected_tail_f1:
        raise ValueError(f"0x07 tail f1 {tail_f1} != expected {expected_tail_f1}")
    struct.pack_into("<H", buf, last_cmd_off + 4, tail_f1 + tail_delta)
    new_tf = tf + tail_delta
    struct.pack_into("<I", buf, 0x2C, new_tf)

    # Re-walk to verify frame invariant
    off = main_off
    check_sum = 0
    while off < end_off:
        op, dw = buf[off], buf[off + 1]
        if op == 0x00:
            break
        if op != 0x01:
            check_sum += struct.unpack_from("<H", buf, off + 4)[0]
        off += dw * 4
    if check_sum != new_tf or len(buf) != len(raw):
        raise AssertionError(f"0x07 post-patch frame mismatch sum={check_sum} tf={new_tf}")
    return bytes(buf)


def patch_0x19_floats(raw: bytes, new_floats: List[float]) -> bytes:
    """Replace 0x19 keyframe (time, value) float pairs in-place after validating monotonic timestamps."""
    n_floats = (len(raw) - 16) // 4
    if n_floats != len(new_floats):
        raise ValueError(f"0x19 float count mismatch: section has {n_floats}, got {len(new_floats)}")

    prev_t = -1.0
    for idx in range(0, n_floats, 2):
        t = new_floats[idx]
        if t < prev_t or t < 0.0 or t > 1.0:
            raise ValueError(f"0x19 non-monotonic or out-of-range timestamp {t} after {prev_t}")
        prev_t = t
        if t >= 1.0 - 1e-6:
            break

    buf = bytearray(raw)
    struct.pack_into(f"<{n_floats}f", buf, 16, *new_floats)
    return bytes(buf)


def _scale_0x19_interior_times(raw: bytes, ratio: float) -> bytes:
    """Scale interior timestamps (0 < t < 1 before first t == 1.0) in a 0x19 keyframe section."""
    n_floats = (len(raw) - 16) // 4
    floats = list(struct.unpack_from(f"<{n_floats}f", raw, 16))
    for idx in range(0, n_floats, 2):
        t = floats[idx]
        if t >= 1.0 - 1e-6:
            break
        if t > 0.0:
            floats[idx] = t * ratio
    return patch_0x19_floats(raw, floats)


def patch_timing_section(
    sec: DatSection, timing_mode: Optional[Tuple[str, Optional[int]]]
) -> Optional[bytes]:
    """Return duration-extended bytes for targeted 0x05/0x07/0x19 sections, or None if untouched."""
    if timing_mode is None:
        return None
    mode, sp_idx = timing_mode
    tag = sec.name.decode("ascii", "replace").strip()

    if mode == "phantom":
        if sec.stype == 0x05 and tag in PHANTOM_PJ_GENS:
            return patch_0x05_life(sec.raw, PHANTOM_RETAIL_LIFE, PHANTOM_EXTEND_LIFE)
        if sec.stype == 0x07 and tag in PHANTOM_YC_SCHEDS:
            return patch_0x07_duration(
                sec.raw, PHANTOM_PJ_GENS, PHANTOM_RETAIL_LIFE, PHANTOM_EXTEND_LIFE, PHANTOM_TAIL_DELTA
            )
        if sec.stype == 0x19:
            if tag == "ja00":
                return patch_0x19_floats(sec.raw, PHANTOM_JA00_FLOATS)
            if tag == "ja01":
                return patch_0x19_floats(sec.raw, PHANTOM_JA01_FLOATS)
            if tag in ("pjsx", "pjyy"):
                return _scale_0x19_interior_times(sec.raw, PHANTOM_RETAIL_LIFE / PHANTOM_EXTEND_LIFE)
        return None

    if mode == "card_sp":
        assert sp_idx is not None
        target_j = f"j0{sp_idx}0"
        if sec.stype == 0x05 and tag == target_j:
            return patch_0x05_life(sec.raw, CARD_SP_RETAIL_LIFE, CARD_SP_EXTEND_LIFE)
        if sec.stype == 0x07 and tag.startswith("xc"):
            return patch_0x07_duration(
                sec.raw,
                {target_j},
                CARD_SP_RETAIL_LIFE,
                CARD_SP_EXTEND_LIFE,
                CARD_SP_TAIL_DELTA,
                expected_tail_f1=52,
            )
        if sec.stype == 0x19:
            if tag == "ja00":
                return patch_0x19_floats(sec.raw, CARD_SP_JA00_FLOATS)
            if tag in ("jpy0", "jry0"):
                return _scale_0x19_interior_times(sec.raw, CARD_SP_RETAIL_LIFE / CARD_SP_EXTEND_LIFE)
            if tag == "jssx":
                n_floats = (len(sec.raw) - 16) // 4
                if n_floats != 16:
                    raise ValueError(f"card_sp jssx expected 16 floats, got {n_floats}")
                floats = list(struct.unpack_from("<16f", sec.raw, 16))
                ratio = CARD_SP_RETAIL_LIFE / CARD_SP_EXTEND_LIFE
                floats[2] *= ratio
                floats[4] *= ratio
                for pair_idx, new_t in enumerate(CARD_SP_JSSX_TIMES, start=3):
                    floats[pair_idx * 2] = new_t
                return patch_0x19_floats(sec.raw, floats)
        return None

    raise ValueError(f"Unknown timing_mode: {timing_mode!r}")


def build_target_map() -> Dict[str, Tuple[str, Dict[str, Tuple[str, object]], bool, Optional[bytes]]]:
    """Return mapping: rel_dat_path -> (label, {sec_tag_str: (kind, value)}, has_cards, tex_prefix)."""
    targets: Dict[str, Tuple[str, Dict[str, Tuple[str, object]], bool, Optional[bytes]]] = {}

    for roll_idx, (rel, label, lucky, unlucky) in enumerate(PHANTOM_ROLLS, start=1):
        spec: Dict[str, Tuple[str, object]] = {}
        for n in range(1, 12):
            if n == 11:
                kind = "eleven"
            elif n == lucky:
                kind = "lucky"
            elif n == unlucky:
                kind = "unlucky"
            else:
                kind = "normal"
            spec[f"j{n}"] = (kind, n)
        spec["bust"] = ("bust", "BUST!")
        t_key = CARD_THEMES[rel].key
        spec["d0"] = ("card_front", (t_key, lucky, unlucky, False))
        spec["c0"] = ("card_back", t_key)
        tex_prefix = f"cor_r{roll_idx:02d}_".encode("ascii")
        targets[rel] = (label, spec, True, tex_prefix)

    for idx, rel in enumerate(WILD_CARD_DATS, start=1):
        spec = {
            f"j{n}": ("eleven" if n == 6 else ("lucky" if n == 5 else "normal"), n)
            for n in range(1, 7)
        }
        spec["d0"] = ("card_front", ("wild_card", 5, 6, True))
        spec["c0"] = ("card_back", "wild_card")
        targets[rel] = (f"Wild Card #{idx}", spec, True, None)

    for idx, rel in enumerate(CUTTING_CARDS_DATS, start=1):
        spec = {
            f"j{n}": ("eleven" if n == 6 else ("lucky" if n == 5 else "normal"), n)
            for n in range(1, 7)
        }
        spec["d0"] = ("card_front", ("cutting", 5, 6, True))
        spec["c0"] = ("card_back", "cutting")
        targets[rel] = (f"Cutting Cards #{idx}", spec, True, None)

    targets[SNAKE_EYE_DAT] = ("Snake Eye", {"j1": ("snake_eye", 1)}, False, None)
    return targets


def patch_dat(
    retail_path: Path,
    out_path: Path,
    spec: Dict[str, Tuple[str, object]],
    unwrap_cards: bool,
    tex_prefix: Optional[bytes],
    dxt_cache: Dict[Tuple[str, object], Tuple[int, int, bytes]],
    timing_mode: Optional[Tuple[str, Optional[int]]] = None,
    extend_duration: bool = False,
) -> Tuple[int, int, int, int]:
    """Patch target 0x20 textures, unwrap 0x1F card meshes, isolate tex namespaces, and optionally extend timing."""
    raw = retail_path.read_bytes()
    sections = parse_sections(raw)
    out_chunks: List[bytes] = []
    replaced = 0
    unwrapped = 0
    renamed_refs = 0
    timed = 0

    for sec in sections:
        tag = sec.name.decode("ascii", "replace").strip()
        if sec.stype == 0x20 and tag in spec:
            if sec.raw[0x10] != 0xA1 or sec.raw[0x49:0x4D] != b"3TXD":
                raise ValueError(
                    f"Unexpected texture format in {retail_path} section {tag}: "
                    f"fmt=0x{sec.raw[0x10]:02X}, magic={sec.raw[0x49:0x4D]!r}"
                )
            tex_name_16 = sec.raw[0x11:0x21]
            if tex_prefix is not None:
                if tex_name_16 not in RENAMED_COR_OLD_NAMES:
                    raise ValueError(
                        f"{retail_path} {tag}: unexpected texture name {tex_name_16!r} for rename"
                    )
                tex_name_16 = tex_prefix + tex_name_16[8:]
            key = spec[tag]
            w, h, dxt_bytes = dxt_cache[key]
            out_chunks.append(build_0x20_section(sec.name, tex_name_16, w, h, dxt_bytes))
            replaced += 1
        elif sec.stype == 0x1F:
            chunk = unwrap_card_mesh_section(sec) if (unwrap_cards and tag in CARD_MESH_TAGS) else sec.raw
            if unwrap_cards and tag in CARD_MESH_TAGS:
                unwrapped += 1
            if tex_prefix is not None:
                chunk, cnt = rename_mesh_tex_refs(sec.name, chunk, tex_prefix)
                renamed_refs += cnt
            out_chunks.append(chunk)
        else:
            patched_timing = patch_timing_section(sec, timing_mode) if extend_duration else None
            if patched_timing is not None:
                out_chunks.append(patched_timing)
                timed += 1
            else:
                out_chunks.append(sec.raw)

    if replaced != len(spec):
        raise ValueError(
            f"{retail_path}: expected {len(spec)} texture replacements, replaced {replaced}"
        )
    if unwrap_cards and unwrapped != len(CARD_MESH_TAGS):
        raise ValueError(
            f"{retail_path}: expected {len(CARD_MESH_TAGS)} card meshes, unwrapped {unwrapped}"
        )
    if tex_prefix is not None and renamed_refs != 38:
        raise ValueError(
            f"{retail_path}: expected 38 0x1F texture ref renames, got {renamed_refs}"
        )
    if extend_duration and timing_mode is not None:
        exp_timed = 28 if timing_mode[0] == "phantom" else 6
        if timed != exp_timed:
            raise ValueError(
                f"{retail_path}: expected {exp_timed} timing patches ({timing_mode[0]}), got {timed}"
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(b"".join(out_chunks))
    return replaced, unwrapped, renamed_refs, timed


def _classify_decoded_color(img: Image.Image) -> str:
    """Classify dominant visible interior color of a decoded DXT3 texture for verification."""
    arr = np.array(img, dtype=np.float32)
    vis = arr[:, :, 3] > 180
    # Filter out black outline pixels (brightness > 65)
    bright = vis & (arr[:, :, :3].max(axis=2) > 65)
    if not np.any(bright):
        return "empty"
    r, g, b = arr[bright, 0].mean(), arr[bright, 1].mean(), arr[bright, 2].mean()
    if g > r + 40 and g > b + 20:
        return "green"
    if r > g + 60 and r > b + 60:
        return "red"
    if r > b + 50 and g > b + 35:
        return "gold"
    if r > 175 and g > 175 and b > 175:
        return "white"
    return f"other({r:.0f},{g:.0f},{b:.0f})"


def verify_pack(
    pack_dir: Path,
    retail_root: Path = RETAIL_ROOT,
    extend_duration: bool = False,
) -> Tuple[int, int, int, int, int]:
    """Verify binary integrity, namespace isolation, card meshes, DXT3 textures, and optional timing."""
    targets = build_target_map()
    timing_map = build_timing_map() if extend_duration else {}
    dat_count = 0
    tex_count = 0
    mesh_count = 0
    timing_count = 0
    unique_roll_tex_names = set()
    expected_color = {
        "normal": "white",
        "lucky": "green",
        "unlucky": "red",
        "eleven": "gold",
        "snake_eye": "gold",
        "bust": "red",
    }

    for rel, (label, spec, has_cards, tex_prefix) in targets.items():
        retail_p = retail_root / rel
        mod_p = pack_dir / rel
        if not mod_p.exists():
            raise FileNotFoundError(f"Missing generated DAT: {mod_p}")

        mod_bytes = mod_p.read_bytes()
        r_secs = parse_sections(retail_p.read_bytes())
        m_secs = parse_sections(mod_bytes)
        if len(r_secs) != len(m_secs):
            raise AssertionError(f"{rel}: section count mismatch {len(r_secs)} vs {len(m_secs)}")

        seen_tags = set()
        seen_meshes = set()
        renamed_refs = 0
        dat_timed = 0
        timing_mode = timing_map.get(rel)
        for rs, ms in zip(r_secs, m_secs):
            if rs.name != ms.name or rs.stype != ms.stype:
                raise AssertionError(f"{rel}: section mismatch {rs.name!r} vs {ms.name!r}")
            tag = ms.name.decode("ascii", "replace").strip()
            if ms.stype == 0x20 and tag in spec:
                kind, _ = spec[tag]
                if kind == "bust":
                    expected_w, expected_h = TEX_SIZE_BUST
                elif kind in ("card_front", "card_back"):
                    expected_w, expected_h = TEX_SIZE_CARD
                else:
                    expected_w, expected_h = (TEX_SIZE_NUM, TEX_SIZE_NUM)
                if ms.raw[0x10] != 0xA1 or ms.raw[0x49:0x4D] != b"3TXD":
                    raise AssertionError(f"{rel} {tag}: invalid 0x20 header magic")
                exp_name = rs.raw[0x11:0x21]
                if tex_prefix is not None:
                    exp_name = tex_prefix + rs.raw[0x19:0x21]
                    if exp_name in unique_roll_tex_names:
                        raise AssertionError(f"{rel} {tag}: duplicate global texture name {exp_name!r}")
                    unique_roll_tex_names.add(exp_name)
                if ms.raw[0x11:0x21] != exp_name:
                    raise AssertionError(
                        f"{rel} {tag}: texture name mismatch {ms.raw[0x11:0x21]!r} != {exp_name!r}"
                    )
                w, h = struct.unpack_from("<II", ms.raw, 37)
                dxt_sz, stride = struct.unpack_from("<II", ms.raw, 77)
                if (w, h) != (expected_w, expected_h) or dxt_sz != w * h or stride != w * 4:
                    raise AssertionError(
                        f"{rel} {tag}: bad dims/sizes ({w}x{h}, dxt={dxt_sz}, stride={stride})"
                    )
                decoded = decode_dxt3(ms.raw[85 : 85 + dxt_sz], w, h)
                if kind in expected_color:
                    got_color = _classify_decoded_color(decoded)
                    exp_color = expected_color[kind]
                    if got_color != exp_color:
                        raise AssertionError(
                            f"{rel} ({label}) {tag} [{kind}]: expected {exp_color}, decoded {got_color}"
                        )
                elif kind == "card_front":
                    # Confirm dark velvet center window stays dark behind floating numbers
                    center_arr = np.array(decoded, dtype=np.float32)[160:350, 72:184, :3]
                    if center_arr.mean() > 35.0:
                        raise AssertionError(
                            f"{rel} ({label}) {tag}: card center window too bright ({center_arr.mean():.1f})"
                        )
                seen_tags.add(tag)
                tex_count += 1
            elif has_cards and ms.stype == 0x1F and tag in CARD_MESH_TAGS:
                renamed_refs += verify_card_mesh_section(rel, rs, ms, tex_prefix=tex_prefix)
                seen_meshes.add(tag)
                mesh_count += 1
            elif ms.stype == 0x1F and tex_prefix is not None:
                expected_raw, r_cnt = rename_mesh_tex_refs(rs.name, rs.raw, tex_prefix)
                if ms.raw != expected_raw:
                    raise AssertionError(f"{rel} {tag}: 0x1F mesh mismatch outside texture ref rename!")
                renamed_refs += r_cnt
            else:
                expected_timing = patch_timing_section(rs, timing_mode) if extend_duration else None
                if expected_timing is not None:
                    if ms.raw != expected_timing:
                        raise AssertionError(f"{rel} {tag}: timing section does not match extended timing!")
                    dat_timed += 1
                    timing_count += 1
                elif rs.raw != ms.raw:
                    raise AssertionError(f"{rel} {tag}: non-target section altered!")

        if seen_tags != set(spec.keys()):
            raise AssertionError(f"{rel}: missing patched tags {set(spec.keys()) - seen_tags}")
        if has_cards and seen_meshes != set(CARD_MESH_TAGS):
            raise AssertionError(f"{rel}: missing unwrapped card meshes {set(CARD_MESH_TAGS) - seen_meshes}")
        if tex_prefix is not None:
            if renamed_refs != 38:
                raise AssertionError(f"{rel}: expected 38 renamed 0x1F refs, got {renamed_refs}")
            for old_name in RENAMED_COR_OLD_NAMES:
                if old_name in mod_bytes:
                    raise AssertionError(f"{rel}: leftover colliding texture name {old_name!r}")
        if extend_duration and timing_mode is not None:
            exp_dat_timed = 28 if timing_mode[0] == "phantom" else 6
            if dat_timed != exp_dat_timed:
                raise AssertionError(f"{rel}: expected {exp_dat_timed} timing sections, got {dat_timed}")
        dat_count += 1

    if len(unique_roll_tex_names) != 31 * 14:
        raise AssertionError(f"Expected 434 unique roll texture names, got {len(unique_roll_tex_names)}")
    if extend_duration and timing_count != 940:
        raise AssertionError(f"Expected 940 extended timing sections, got {timing_count}")
    return dat_count, tex_count, mesh_count, len(unique_roll_tex_names), timing_count


def _extract_dat_texture(dat_path: Path, tag: str) -> Image.Image:
    """Decode a named 0x20 DXT3 texture directly from a DAT file."""
    secs = parse_sections(dat_path.read_bytes())
    for sec in secs:
        if sec.stype == 0x20 and sec.name.decode("ascii", "replace").strip() == tag:
            w, h = struct.unpack_from("<II", sec.raw, 37)
            dxt_sz = struct.unpack_from("<I", sec.raw, 77)[0]
            return decode_dxt3(sec.raw[85 : 85 + dxt_sz], w, h)
    raise KeyError(f"{tag} not found in {dat_path}")


def _checker_bg(w: int, h: int, dark: bool) -> Image.Image:
    """Create a subtle Sortie-dark or snow-bright tile backdrop for preview legibility."""
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    chk = ((xx // 16) + (yy // 16)) & 1
    if dark:
        arr[chk == 0] = (20, 24, 34)
        arr[chk == 1] = (28, 34, 46)
    else:
        arr[chk == 0] = (238, 242, 248)
        arr[chk == 1] = (218, 224, 234)
    return Image.fromarray(arr, "RGB").convert("RGBA")


def generate_preview_sheet(
    pack_dir: Path,
    preview_paths: Iterable[Path],
    compare_root: Optional[Path] = None,
    retail_root: Path = RETAIL_ROOT,
) -> None:
    """Composite post-DXT3-roundtrip decoded textures over dark and bright backdrops."""
    w_sheet = 1480
    h_sheet = 1140
    sheet = Image.new("RGB", (w_sheet, h_sheet), (14, 17, 24))
    draw = ImageDraw.Draw(sheet)

    title_font = ImageFont.truetype(str(FONT_PATH), 26)
    sub_font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 16)
    hdr_font = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 18)
    lbl_font = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 13)

    draw.text(
        (28, 20),
        "LuckyRoll - Post-DXT3 Roundtrip Preview (256x256 / 512x256 BUST!)",
        fill=(255, 255, 255),
        font=title_font,
    )
    draw.text(
        (28, 54),
        "All 31 Phantom Rolls + Wild Card + Cutting Cards + Snake Eye  |  White=Normal  Green+Star=Lucky  Red=Unlucky  Gold+Crown=11/Jackpot",
        fill=(185, 200, 220),
        font=sub_font,
    )

    def paste_tile(
        tx: int, ty: int, img: Image.Image, tile_w: int, tile_h: int, dark: bool, caption: str
    ) -> None:
        bg = _checker_bg(tile_w, tile_h, dark=dark)
        scaled = img.resize((tile_w, tile_h), Image.Resampling.LANCZOS)
        comp = Image.alpha_composite(bg, scaled).convert("RGB")
        sheet.paste(comp, (tx, ty))
        draw.rectangle([tx, ty, tx + tile_w - 1, ty + tile_h - 1], outline=(70, 82, 102), width=1)
        draw.text((tx + 4, ty + tile_h + 4), caption, fill=(210, 220, 235), font=lbl_font)

    # Row 1: Samurai Roll (ROM/164/54.DAT, Lucky=2, Unlucky=6) 1..11 + BUST! on DARK backdrop
    sam_dat = pack_dir / "ROM/164/54.DAT"
    draw.text(
        (28, 92),
        "Samurai Roll (ROM/164/54.DAT - Lucky: 2, Unlucky: 6) on Dark Sortie Backdrop",
        fill=(130, 235, 175),
        font=hdr_font,
    )
    for n in range(1, 12):
        img = _extract_dat_texture(sam_dat, f"j{n}")
        tag = "2 [LKY]" if n == 2 else ("6 [UNL]" if n == 6 else ("11 [MAX]" if n == 11 else str(n)))
        paste_tile(28 + (n - 1) * 108, 122, img, 96, 96, dark=True, caption=tag)
    bust_img = _extract_dat_texture(sam_dat, "bust")
    paste_tile(28 + 11 * 108, 122, bust_img, 192, 96, dark=True, caption="BUST! (512x256)")

    # Row 2: Chaos Roll (4 Lucky) + Fighter's Roll (5 Lucky) + Healer's Roll (3 Lucky) on BRIGHT snow backdrop
    draw.text(
        (28, 256),
        "Chaos (Lucky 4), Fighter (Lucky 5), Healer (Lucky 3) & Samurai on Bright White/Snow Backdrop",
        fill=(255, 224, 120),
        font=hdr_font,
    )
    chaos_dat = pack_dir / "ROM/164/50.DAT"
    fighter_dat = pack_dir / "ROM/163/90.DAT"
    healer_dat = pack_dir / "ROM/164/45.DAT"
    chaos_picks = [
        (healer_dat, "j3", "Healer 3 [LKY]", False),
        (chaos_dat, "j4", "Chaos 4 [LKY]", False),
        (fighter_dat, "j5", "Fighter 5 [LKY]", False),
        (chaos_dat, "j5", "Chaos 5", False),
        (chaos_dat, "j6", "Chaos 6", False),
        (chaos_dat, "j8", "Chaos 8 [UNL]", False),
        (chaos_dat, "j9", "Chaos 9", False),
        (chaos_dat, "j10", "Chaos 10", False),
        (chaos_dat, "j11", "Chaos 11", False),
        (sam_dat, "j2", "Samurai 2 [LKY]", False),
        (sam_dat, "j6", "Samurai 6 [UNL]", False),
        (sam_dat, "bust", "BUST! (Snow)", False),
    ]
    x_cur = 28
    for datp, sec, cap, dk in chaos_picks:
        img = _extract_dat_texture(datp, sec)
        tw = 176 if sec == "bust" else 92
        paste_tile(x_cur, 286, img, tw, 92, dark=dk, caption=cap)
        x_cur += tw + 13

    # Row 3: Wild Card (ROM/165/17.DAT) 1..6 + Snake Eye (ROM/184/80.DAT) + Retail vs LuckyRoll Comparison
    cmp_dir = compare_root if compare_root is not None else retail_root
    is_retail_cmp = cmp_dir.resolve() == retail_root.resolve()
    cmp_title = "Retail Roman" if is_retail_cmp else cmp_dir.name
    cmp_prefix = "Retail" if is_retail_cmp else cmp_dir.name[:10]
    draw.text(
        (28, 424),
        f"Wild Card (ROM/165/17.DAT: 1-6), Snake Eye (ROM/184/80.DAT), & {cmp_title} vs LuckyRoll Comparison",
        fill=(140, 200, 255),
        font=hdr_font,
    )
    wc_dat = pack_dir / "ROM/165/17.DAT"
    for n in range(1, 7):
        img = _extract_dat_texture(wc_dat, f"j{n}")
        cap = f"WC {n}" + (" [LKY]" if n == 5 else (" [MAX]" if n == 6 else ""))
        paste_tile(28 + (n - 1) * 108, 454, img, 96, 96, dark=True, caption=cap)

    se_img = _extract_dat_texture(pack_dir / SNAKE_EYE_DAT, "j1")
    paste_tile(28 + 6 * 108, 454, se_img, 96, 96, dark=True, caption="SnakeEye 1")

    # Side-by-side base Roman vs LuckyRoll Arabic (Samurai 4, 5, 6)
    cmp_sam = cmp_dir / "ROM/164/54.DAT"
    if cmp_sam.exists():
        x_cmp = 28 + 7 * 108 + 26
        for idx, n in enumerate((4, 5, 6)):
            old_img = _extract_dat_texture(cmp_sam, f"j{n}")
            paste_tile(x_cmp + idx * 108, 454, old_img, 96, 96, dark=True, caption=f"{cmp_prefix} j{n}")
        for idx, n in enumerate((4, 5, 6)):
            new_img = _extract_dat_texture(sam_dat, f"j{n}")
            paste_tile(x_cmp + (idx + 3) * 108, 454, new_img, 96, 96, dark=True, caption=f"New j{n}")

    # Row 4: Native 1:1 256x256 inspection tiles (no downscale) for 4, 5, 6, 10, 11
    draw.text(
        (28, 594),
        "Native 1:1 Pixel Inspection (Actual 256x256 In-Game Texture Resolution)",
        fill=(255, 255, 255),
        font=hdr_font,
    )
    native_picks = [
        (chaos_dat, "j4", "Chaos 4 (Lucky)", True),
        (fighter_dat, "j5", "Fighter 5 (Lucky)", True),
        (sam_dat, "j6", "Samurai 6 (Unlucky)", True),
        (chaos_dat, "j10", "Chaos 10 (Normal)", False),
        (sam_dat, "j11", "Samurai 11 (Jackpot)", True),
    ]
    for idx, (datp, sec, cap, dk) in enumerate(native_picks):
        img = _extract_dat_texture(datp, sec)
        paste_tile(28 + idx * 282, 628, img, 256, 256, dark=dk, caption=cap)

    # Row 5: Native 512x256 BUST! preview
    paste_tile(28, 922, bust_img, 360, 180, dark=True, caption="BUST! (Dark)")
    paste_tile(420, 922, bust_img, 360, 180, dark=False, caption="BUST! (Bright)")

    # Legend box at bottom right
    draw.rectangle([820, 922, 1450, 1102], fill=(22, 27, 38), outline=(70, 82, 102), width=1)
    legend_lines = [
        ("Color & Badge Key:", (255, 255, 255)),
        ("  White + Black Outline = Standard Roll (1 - 10)", (225, 235, 250)),
        ("  Emerald Green + Gold Star = Roll-Specific LUCKY Number", (40, 240, 120)),
        ("  Crimson Red = Roll-Specific UNLUCKY Number", (255, 70, 70)),
        ("  Radiant Gold + Royal Crown = Roll 11 / Wild Card 6 / Cutting Cards 6", (255, 215, 50)),
        ("  Gold-White + Star = Snake Eye (1)  |  512x256 Crimson = BUST!", (255, 234, 130)),
    ]
    for i, (txt, col) in enumerate(legend_lines):
        draw.text((840, 936 + i * 26), txt, fill=col, font=sub_font if i > 0 else hdr_font)

    for p in preview_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(p, "PNG")


def generate_cards_preview_sheet(pack_dir: Path, preview_paths: Iterable[Path]) -> None:
    """Showcase decoded 256x512 Card Fronts (with overlaid jN numbers) + Card Backs at 1.44:2.42."""
    picks = [
        ("ROM/164/50.DAT", "j4", "Chaos 4 [LKY]"),
        ("ROM/163/90.DAT", "j5", "Fighter 5 [LKY]"),
        ("ROM/164/54.DAT", "j6", "Samurai 6 [UNL]"),
        ("ROM/164/47.DAT", "j8", "Warlock 8 [UNL]"),
        ("ROM/164/60.DAT", "j3", "Puppet 3 [LKY]"),
        ("ROM/164/45.DAT", "j3", "Healer 3 [LKY]"),
        ("ROM/164/46.DAT", "j11", "Wizard 11 [MAX]"),
        ("ROM/246/101.DAT", "j3", "Bolter 3 [LKY]"),
        ("ROM/261/40.DAT", "j5", "Tactician 5 [LKY]"),
        ("ROM/321/72.DAT", "j3", "Naturalist 3 [LKY]"),
        ("ROM/165/17.DAT", "j6", "Wild Card 6 [MAX]"),
        ("ROM/306/122.DAT", "j5", "Cutting 5 [LKY]"),
    ]

    cw, ch = 168, 282  # Exact 1.44 : 2.42 3D card aspect ratio
    cols = 4
    rows = 3
    pair_gap = 10
    cell_w = cw * 2 + pair_gap
    col_gap = 28
    row_gap = 46

    w_sheet = 32 * 2 + cols * cell_w + (cols - 1) * col_gap
    h_sheet = 110 + rows * ch + (rows - 1) * row_gap + 38
    sheet = Image.new("RGB", (w_sheet, h_sheet), (14, 17, 24))
    draw = ImageDraw.Draw(sheet)

    title_font = ImageFont.truetype(str(FONT_PATH), 26)
    sub_font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 16)
    lbl_font = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 15)

    draw.text(
        (32, 20),
        "LuckyRoll - Distinctive Tarot Cards (MODULATE2X-Calibrated, Outward wc Ring)",
        fill=(255, 255, 255),
        font=title_font,
    )
    draw.text(
        (32, 54),
        "5 Patterns & Medallions + Stat Tags  |  Spinning ring (wc) flipped outward; winning card (c1-c6) faces forward",
        fill=(185, 200, 220),
        font=sub_font,
    )

    # Rounded mask matching the 3D card mesh corner bevel (~11% corner inset)
    card_mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(card_mask).rounded_rectangle([0, 0, cw - 1, ch - 1], radius=16, fill=255)
    num_w = round(cw * (1.20 / 1.44))  # 140
    num_h = round(ch * (1.20 / 2.42))  # 140
    nx0 = (cw - num_w) // 2
    ny0 = (ch - num_h) // 2

    for idx, (rel, j_tag, caption) in enumerate(picks):
        r = idx // cols
        c = idx % cols
        x0 = 32 + c * (cell_w + col_gap)
        y0 = 104 + r * (ch + row_gap)

        dat_path = pack_dir / rel
        front_img = _extract_dat_texture(dat_path, "d0").resize((cw, ch), Image.Resampling.LANCZOS)
        back_img = _extract_dat_texture(dat_path, "c0").resize((cw, ch), Image.Resampling.LANCZOS)
        num_img = _extract_dat_texture(dat_path, j_tag).resize((num_w, num_h), Image.Resampling.LANCZOS)

        # Composite number strictly in its exact 3D mesh span over Front
        front_comp = front_img.copy()
        front_comp.paste(num_img, (nx0, ny0), num_img)

        sheet.paste(front_comp.convert("RGB"), (x0, y0), card_mask)
        sheet.paste(back_img.convert("RGB"), (x0 + cw + pair_gap, y0), card_mask)
        draw.rounded_rectangle([x0, y0, x0 + cw - 1, y0 + ch - 1], radius=16, outline=(80, 92, 114), width=1)
        draw.rounded_rectangle(
            [x0 + cw + pair_gap, y0, x0 + cell_w - 1, y0 + ch - 1],
            radius=16,
            outline=(80, 92, 114),
            width=1,
        )
        draw.text((x0 + 4, y0 + ch + 7), f"{caption}  (Front / Back)", fill=(225, 234, 248), font=lbl_font)

    for p in preview_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(p, "PNG")


def create_shareable_zip(pack_dir: Path, zip_path: Path) -> None:
    """Package pack_dir into a shareable zip with pack_dir.name as the archive root."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for file_path in sorted(pack_dir.rglob("*")):
            if file_path.is_file():
                arcname = Path(pack_dir.name) / file_path.relative_to(pack_dir)
                zf.write(file_path, arcname.as_posix())


def build_all(
    out_pack: Path,
    zip_path: Optional[Path],
    num_preview_paths: List[Path],
    cards_preview_paths: List[Path],
    retail_root: Path = RETAIL_ROOT,
    compare_root: Optional[Path] = None,
    skip_zip: bool = False,
    extend_duration: bool = False,
) -> None:
    """Render all unique roll & card graphics once, patch all 44 retail DATs, and emit previews."""
    targets = build_target_map()
    timing_map = build_timing_map() if extend_duration else {}
    unique_keys = sorted(
        {kv for _, spec, _, _ in targets.values() for kv in spec.values()},
        key=lambda kv: (kv[0], repr(kv[1])),
    )

    print(f"Rendering & DXT3-encoding {len(unique_keys)} unique textures...")
    dxt_cache: Dict[Tuple[str, object], Tuple[int, int, bytes]] = {}
    for key in unique_keys:
        kind, val = key
        if kind == "card_front":
            t_key, lky, unl, is_sp6 = val  # type: ignore[misc]
            img = render_card_front(THEME_BY_KEY[t_key], lky, unl, is_special_6=is_sp6)
        elif kind == "card_back":
            img = render_card_back(THEME_BY_KEY[str(val)])
        else:
            img = render_roll_graphic(kind, val)
        w, h = img.size
        dxt_cache[key] = (w, h, encode_dxt3(img))

    print(f"Patching {len(targets)} retail DATs into {out_pack}...")
    total_tex = 0
    total_meshes = 0
    total_renamed = 0
    total_timed = 0
    for rel, (label, spec, has_cards, tex_prefix) in targets.items():
        retail_p = retail_root / rel
        out_p = out_pack / rel
        r_tex, u_mesh, r_ref, r_timed = patch_dat(
            retail_p,
            out_p,
            spec,
            has_cards,
            tex_prefix,
            dxt_cache,
            timing_mode=timing_map.get(rel),
            extend_duration=extend_duration,
        )
        total_tex += r_tex
        total_meshes += u_mesh
        total_renamed += r_ref
        total_timed += r_timed

    timing_msg = f", {total_timed} extended timing secs" if extend_duration else ""
    print(
        f"Patched {len(targets)} DATs ({total_tex} textures, {total_meshes} card meshes, "
        f"{total_renamed} isolated mesh refs{timing_msg}). Verifying..."
    )
    dat_cnt, tex_cnt, mesh_cnt, uniq_cnt, ver_timed = verify_pack(
        out_pack, retail_root=retail_root, extend_duration=extend_duration
    )
    ver_timing_msg = f", and {ver_timed} extended timing sections" if extend_duration else ""
    print(
        f"PASS: Verified {dat_cnt} DATs, {tex_cnt} DXT3 textures, "
        f"{mesh_cnt} card meshes, {uniq_cnt} unique roll texture names{ver_timing_msg}."
    )

    if num_preview_paths:
        generate_preview_sheet(
            out_pack,
            num_preview_paths,
            compare_root=compare_root,
            retail_root=retail_root,
        )
        for p in num_preview_paths:
            print(f"Preview written: {p}")

    if cards_preview_paths:
        generate_cards_preview_sheet(out_pack, cards_preview_paths)
        for p in cards_preview_paths:
            print(f"Cards preview written: {p}")

    if not skip_zip and zip_path is not None:
        create_shareable_zip(out_pack, zip_path)
        print(f"Zip written: {zip_path} ({zip_path.stat().st_size:,} bytes)")


def main() -> None:
    global FONT_PATH
    parser = argparse.ArgumentParser(description="Build and verify LuckyRoll XIPivot pack.")
    parser.add_argument("--verify", action="store_true", help="Verify an existing LuckyRoll build only.")
    parser.add_argument(
        "--extend-duration",
        action="store_true",
        help="Extend floating result number display durations on Phantom Rolls, Wild Card, and Cutting Cards.",
    )
    parser.add_argument(
        "--ffxi-root",
        type=Path,
        default=RETAIL_ROOT,
        help="Path to retail FINAL FANTASY XI directory containing ROM/.",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PACK, help="Output pack folder.")
    parser.add_argument(
        "--preview-dir",
        type=Path,
        default=DEFAULT_PREVIEW_DIR,
        help="Directory for preview_numbers.png and preview_cards.png.",
    )
    parser.add_argument("--skip-previews", action="store_true", help="Skip generating preview images.")
    parser.add_argument("--zip", type=Path, default=None, help="Optional output path for shareable XIPivot zip.")
    parser.add_argument(
        "--compare-root",
        type=Path,
        default=None,
        help="Optional base DAT pack for Row 3 preview comparison (defaults to --ffxi-root).",
    )
    parser.add_argument("--font", type=Path, default=FONT_PATH, help="TrueType font for numeral rendering.")
    args = parser.parse_args()

    FONT_PATH = args.font
    retail_root: Path = args.ffxi_root
    if not (retail_root / "ROM").is_dir():
        parser.error(f"Retail ROM directory not found under --ffxi-root: {retail_root}")

    if args.verify:
        dat_cnt, tex_cnt, mesh_cnt, uniq_cnt, ver_timed = verify_pack(
            args.out, retail_root=retail_root, extend_duration=args.extend_duration
        )
        if args.extend_duration:
            print(
                f"VERIFY PASS: {dat_cnt}/44 DATs, {tex_cnt}/531 textures, "
                f"{mesh_cnt}/301 card meshes, {uniq_cnt}/434 unique roll texture names, "
                f"and {ver_timed}/940 extended timing sections verified cleanly."
            )
        else:
            print(
                f"VERIFY PASS: {dat_cnt}/44 DATs, {tex_cnt}/531 textures, "
                f"{mesh_cnt}/301 card meshes, and {uniq_cnt}/434 unique roll texture names verified cleanly."
            )
        return

    compare_root = args.compare_root if args.compare_root is not None else retail_root
    num_previews = [] if args.skip_previews else [args.preview_dir / "preview_numbers.png"]
    card_previews = [] if args.skip_previews else [args.preview_dir / "preview_cards.png"]
    build_all(
        args.out,
        args.zip,
        num_previews,
        card_previews,
        retail_root=retail_root,
        compare_root=compare_root,
        skip_zip=(args.zip is None),
        extend_duration=args.extend_duration,
    )


if __name__ == "__main__":
    main()
