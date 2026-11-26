#!/usr/bin/env python3
"""
Procedural Pixel-Art Sprite Generator & Custom Frame Importer
for the Tidbyt Weather-Reactive Capybara Clock (Lumei & Lulu).

Character Design (faithful to reference artwork):
  - Lumei (Left): Bright golden butter-yellow capybara wearing a pale blush-pink
    ruffled lace bonnet topped with a cream halo ring, tiny orange nub, and
    bright green V-shaped twin-leaf sprout, plus a puffy baby-pink bloomer
    romper, rosy cheeks, wide sparkling eyes, and a big happy smile.
  - Lulu (Right): Chubby pear-shaped golden butter-yellow capybara with a warm
    peach-orange lower muzzle/snout, iconic sleepy half-lidded eyes, a plump
    tangerine with green stem on his head, and bright orange-coral strawberry
    shorts.

Generates 32x32 animated GIF and WebP sprites for all 6 weather states:
  - sunny, rainy, snowy, windy, thunderstorm, default

Loop Timing & Seamlessness Contract:
  - Canvas:       32 x 32 px
  - Frame count:  150 frames
  - Frame delay:  100 ms (10 FPS)
  - Total loop:   15.0 seconds (15,000 ms), loop=0 (infinite)
  - Every periodic oscillator uses a divisor of 150 (30, 50, 75, 150).
  - Every particle wraps via exact modulo arithmetic over 32 px so pos(150) == pos(0).
  - Every one-off event (watermelon bites, lightning strikes) resolves cleanly
    back to the resting state well before frame 150.
"""

from __future__ import annotations

import argparse
import base64
import io
import math
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Core Animation Timing Constants (15-second seamless loop)
# ---------------------------------------------------------------------------
WIDTH = 32
HEIGHT = 32
NUM_FRAMES = 150
FRAME_DELAY_MS = 100  # 150 * 100 ms = 15,000 ms (15.0s at 10 FPS)
TOTAL_DURATION_MS = NUM_FRAMES * FRAME_DELAY_MS

STATES = ("sunny", "rainy", "snowy", "windy", "thunderstorm", "default")

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
CUSTOM_DIR = ASSETS_DIR / "custom"
PREVIEWS_DIR = ASSETS_DIR / "previews"
STAR_FILE = ROOT_DIR / "capybara_clock.star"

SPRITE_BEGIN_MARKER = "# --- BEGIN GENERATED SPRITES (DO NOT EDIT MANUALLY) ---"
SPRITE_END_MARKER = "# --- END GENERATED SPRITES ---"

RGBA = Tuple[int, int, int, int]

# ---------------------------------------------------------------------------
# Palette (sampled & tuned from Lumei & Lulu reference for Tidbyt LEDs)
# ---------------------------------------------------------------------------
C = {
    # Shared golden butter-yellow coat (Lumei & Lulu)
    "gold_hi": (255, 232, 128, 255),
    "gold_main": (248, 204, 72, 255),
    "gold_shade": (222, 162, 46, 255),
    "gold_dark": (184, 120, 32, 255),
    # Lulu's warm peach-orange snout/cheeks & eyelids
    "snout_main": (242, 148, 58, 255),
    "snout_hi": (252, 184, 102, 255),
    "snout_shade": (214, 114, 38, 255),
    "mouth_line": (136, 68, 28, 255),
    # Lumei's rosy blush & happy smile
    "cheek_peach": (246, 146, 116, 255),
    "smile_dark": (110, 36, 44, 255),
    "smile_tongue": (224, 102, 112, 255),
    # Lumei's pale blush-pink ruffled bonnet & puffy bloomer romper
    "bonnet_ruffle": (255, 240, 240, 255),
    "bonnet_pink": (246, 206, 212, 255),
    "bonnet_dot": (226, 174, 184, 255),
    "romper_hi": (252, 214, 220, 255),
    "romper_main": (242, 174, 188, 255),
    "romper_shade": (212, 130, 148, 255),
    # Lumei's halo ring & twin-leaf sprout
    "halo_cream": (252, 236, 178, 255),
    "halo_shade": (224, 198, 130, 255),
    "sprout_hi": (176, 236, 98, 255),
    "sprout_green": (118, 204, 62, 255),
    # Lulu's plump tangerine & orange-coral strawberry shorts
    "orange_hi": (255, 176, 56, 255),
    "orange_main": (246, 114, 22, 255),
    "orange_dark": (196, 76, 12, 255),
    "stem_green": (96, 168, 44, 255),
    "shorts_main": (242, 104, 52, 255),
    "shorts_hi": (252, 142, 82, 255),
    "shorts_dark": (196, 68, 30, 255),
    "shorts_seed": (255, 232, 136, 255),
    # Eyes & basics
    "eye": (24, 16, 14, 255),
    "white": (255, 255, 255, 255),
    "phone_body": (68, 74, 88, 255),
    "phone_dark": (40, 44, 54, 255),
    "phone_glow": (180, 224, 255, 255),
    # Sunny props
    "sun_core": (255, 224, 64, 255),
    "sun_ray": (255, 158, 28, 255),
    "shades_frame": (20, 24, 38, 255),
    "shades_lens": (42, 58, 96, 255),
    "shades_glint": (190, 232, 255, 255),
    "melon_rind": (44, 192, 82, 255),
    "melon_pith": (235, 248, 235, 255),
    "melon_pink": (255, 72, 104, 255),
    "melon_seed": (32, 22, 26, 255),
    # Rainy props
    "umb_blue": (46, 120, 242, 255),
    "umb_light": (118, 178, 255, 255),
    "umb_dark": (24, 72, 172, 255),
    "umb_handle": (162, 104, 58, 255),
    "rain_bright": (146, 208, 255, 255),
    "rain_dim": (68, 134, 216, 255),
    # Snowy props
    "snow_bright": (242, 248, 255, 255),
    "snow_mid": (176, 212, 244, 255),
    "snow_ground": (214, 232, 248, 255),
    "snow_shadow": (142, 176, 214, 255),
    "scarf_red": (236, 56, 68, 255),
    "scarf_gold": (255, 208, 72, 255),
    "scarf_teal": (44, 204, 196, 255),
    "scarf_mint": (186, 248, 242, 255),
    # Windy props
    "wind_streak": (112, 178, 198, 255),
    "wind_dim": (58, 104, 124, 255),
    "leaf_orange": (250, 122, 34, 255),
    "leaf_gold": (252, 204, 44, 255),
    "leaf_red": (234, 66, 66, 255),
    "leaf_sage": (132, 206, 68, 255),
    # Thunderstorm props
    "cloud_dark": (36, 46, 68, 255),
    "cloud_mid": (56, 70, 98, 255),
    "bolt_core": (255, 255, 230, 255),
    "bolt_glow": (255, 224, 72, 255),
    "blanket_main": (124, 72, 216, 255),
    "blanket_hi": (168, 126, 246, 255),
    "blanket_dark": (78, 42, 148, 255),
    "blanket_star": (255, 224, 118, 255),
    # Default / Night props
    "star_bright": (255, 248, 208, 255),
    "star_dim": (138, 162, 204, 255),
    "moon": (255, 236, 152, 255),
    "grass_dark": (24, 58, 42, 255),
    "grass_mid": (38, 88, 56, 255),
    "grass_hi": (66, 128, 76, 255),
    "heart": (255, 108, 148, 255),
}


# ---------------------------------------------------------------------------
# Low-level Pixel Drawing Helpers
# ---------------------------------------------------------------------------
class Canvas:
    """Bounds-safe 32x32 RGBA pixel canvas."""

    def __init__(self, bg: RGBA = (6, 10, 20, 255)):
        self.img = Image.new("RGBA", (WIDTH, HEIGHT), bg)
        self.px = self.img.load()

    def set(self, x: int, y: int, color: RGBA) -> None:
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            if color[3] == 255:
                self.px[x, y] = color
            elif color[3] > 0:
                bg = self.px[x, y]
                a = color[3] / 255.0
                r = int(round(color[0] * a + bg[0] * (1.0 - a)))
                g = int(round(color[1] * a + bg[1] * (1.0 - a)))
                b = int(round(color[2] * a + bg[2] * (1.0 - a)))
                self.px[x, y] = (r, g, b, 255)

    def rect(self, x: int, y: int, w: int, h: int, color: RGBA) -> None:
        for dy in range(h):
            for dx in range(w):
                self.set(x + dx, y + dy, color)

    def hline(self, x: int, y: int, length: int, color: RGBA) -> None:
        for dx in range(length):
            self.set(x + dx, y, color)

    def vline(self, x: int, y: int, length: int, color: RGBA) -> None:
        for dy in range(length):
            self.set(x, y + dy, color)

    def gradient_v(
        self,
        top: RGBA,
        bottom: RGBA,
        y0: int = 0,
        y1: int = HEIGHT,
        bands: int = 4,
    ) -> None:
        """Crisp stepped pixel-art sky bands (authentic on LEDs & compresses cleanly)."""
        span = max(1, y1 - y0)
        for y in range(y0, y1):
            band_idx = min(bands - 1, ((y - y0) * bands) // span)
            t = band_idx / max(1, bands - 1)
            col = (
                int(round(top[0] + (bottom[0] - top[0]) * t)),
                int(round(top[1] + (bottom[1] - top[1]) * t)),
                int(round(top[2] + (bottom[2] - top[2]) * t)),
                255,
            )
            self.hline(0, y, WIDTH, col)


# ---------------------------------------------------------------------------
# Seamless Loop Math Helpers (all guaranteed periodic over NUM_FRAMES = 150)
# ---------------------------------------------------------------------------
def wave_sin(frame: int, cycles: int, phase: float = 0.0) -> float:
    """Exact periodic sine wave completing `cycles` integer cycles in NUM_FRAMES."""
    return math.sin(2.0 * math.pi * cycles * frame / NUM_FRAMES + phase)


def bob_offset(frame: int, period: int = 30, phase: int = 0) -> int:
    """Crisp 0/1 px vertical breathing bob whose period divides NUM_FRAMES."""
    assert NUM_FRAMES % period == 0, f"Period {period} must divide {NUM_FRAMES}"
    t = (frame + phase) % period
    return 1 if t >= period // 2 else 0


def wrap_pos(start: int, cycles: int, frame: int, size: int = WIDTH, direction: int = 1) -> int:
    """
    Exact toroidal particle position over `size` pixels.
    At frame=0 and frame=NUM_FRAMES, returns `start % size` identically.
    """
    delta = (cycles * size * frame) // NUM_FRAMES
    return (start + direction * delta) % size


# ---------------------------------------------------------------------------
# Character Sprite Primitives (faithful to Lumei & Lulu reference image)
# ---------------------------------------------------------------------------
def draw_lumei(
    c: Canvas,
    ox: int,
    oy: int,
    *,
    blink: bool = False,
    squint: bool = False,
    startled: bool = False,
    sunglasses: bool = False,
    glint_x: int = -1,
    scarf: bool = False,
    scarf_flutter: int = 0,
    lean_x: int = 0,
    sprout_sway: int = 0,
) -> None:
    """
    Draw Lumei (LEFT character, ~13w x 18h from sprout to feet):
      - Bright green V-shaped twin-leaf sprout atop a tiny orange nub + cream halo ring
      - Pale blush-pink dotted bonnet with fluffy cream-white scalloped ruffle brim
      - Round golden butter-yellow face, big cheerful eyes, rosy cheeks, wide happy smile
      - Puffy baby-pink bloomer romper with clasped golden paws & little yellow feet
    Anchor (ox, oy) is top-left of her bonnet crown; sprout sits at oy-3..oy-1.
    """
    hx = ox + lean_x
    bx = ox

    # --- V-shaped green twin-leaf sprout + tiny orange nub + cream halo ring ---
    cx = hx + 5
    # Twin V leaves
    c.set(cx - 1 + sprout_sway, oy - 3, C["sprout_hi"])
    c.set(cx + 1 + sprout_sway, oy - 3, C["sprout_hi"])
    c.set(cx + sprout_sway, oy - 2, C["sprout_green"])
    # Cream halo ring + orange nub
    c.hline(cx - 2, oy - 1, 5, C["halo_cream"])
    c.set(cx, oy - 1, C["orange_main"])
    c.set(cx - 2, oy - 1, C["halo_shade"])
    c.set(cx + 2, oy - 1, C["halo_shade"])
    c.hline(cx - 1, oy, 3, C["orange_dark"])

    # --- Pale Blush-Pink Bonnet Dome (wraps top & left-back of head) ---
    c.hline(hx + 2, oy, 7, C["bonnet_pink"])
    c.hline(hx + 4, oy, 3, C["orange_dark"])  # tiny orange base seated on bonnet
    c.rect(hx + 1, oy + 1, 9, 4, C["bonnet_pink"])
    c.rect(hx, oy + 3, 3, 5, C["bonnet_pink"])
    # Subtle bonnet polka dots
    c.set(hx + 3, oy + 1, C["bonnet_dot"])
    c.set(hx + 7, oy + 1, C["bonnet_dot"])
    c.set(hx + 1, oy + 5, C["bonnet_dot"])
    # Fluffy scalloped white/cream lace ruffle framing her face!
    c.set(hx + 3, oy + 2, C["bonnet_ruffle"])
    c.set(hx + 5, oy + 2, C["bonnet_ruffle"])
    c.set(hx + 7, oy + 2, C["bonnet_ruffle"])
    c.set(hx + 9, oy + 2, C["bonnet_ruffle"])
    c.set(hx + 2, oy + 3, C["bonnet_ruffle"])
    c.set(hx + 1, oy + 4, C["bonnet_ruffle"])
    c.set(hx + 1, oy + 6, C["bonnet_ruffle"])
    c.set(hx, oy + 7, C["bonnet_ruffle"])
    c.set(hx + 10, oy + 3, C["bonnet_ruffle"])
    # Cute little golden ear poking out on the left bonnet edge
    c.rect(hx + 1, oy + 2, 2, 2, C["gold_main"])
    c.set(hx + 1, oy + 3, C["gold_dark"])

    # --- Round Golden Butter-Yellow Face (facing right toward Lulu) ---
    c.hline(hx + 4, oy + 3, 6, C["gold_hi"])
    c.rect(hx + 3, oy + 4, 8, 5, C["gold_main"])
    c.hline(hx + 3, oy + 8, 8, C["gold_shade"])
    c.hline(hx + 4, oy + 9, 6, C["gold_shade"])
    # Soft round golden left cheek fullness
    c.vline(hx + 2, oy + 5, 3, C["gold_main"])
    c.set(hx + 2, oy + 7, C["gold_shade"])
    # Rosy peach cheeks
    c.hline(hx + 4, oy + 7, 2, C["cheek_peach"])
    c.set(hx + 10, oy + 7, C["cheek_peach"])

    # --- Eyes (big bright cheerful cartoon eyes with white sclera!) ---
    if sunglasses:
        c.hline(hx + 3, oy + 5, 8, C["shades_frame"])
        c.rect(hx + 3, oy + 5, 3, 2, C["shades_lens"])
        c.rect(hx + 7, oy + 5, 3, 2, C["shades_lens"])
        c.set(hx + 6, oy + 5, C["shades_frame"])
        if 0 <= glint_x <= 6:
            gx = hx + 3 + glint_x
            if hx + 3 <= gx <= hx + 5 or hx + 7 <= gx <= hx + 9:
                c.set(gx, oy + 5, C["shades_glint"])
    elif squint:
        c.hline(hx + 4, oy + 5, 2, C["eye"])
        c.hline(hx + 8, oy + 5, 2, C["eye"])
    elif blink:
        c.hline(hx + 4, oy + 6, 2, C["eye"])
        c.hline(hx + 8, oy + 6, 2, C["eye"])
    elif startled:
        c.rect(hx + 4, oy + 5, 2, 2, C["white"])
        c.set(hx + 5, oy + 6, C["eye"])
        c.rect(hx + 8, oy + 5, 2, 2, C["white"])
        c.set(hx + 9, oy + 6, C["eye"])
    else:
        # Left eye (white sclera on left + big dark pupil on right)
        c.rect(hx + 4, oy + 5, 2, 2, C["eye"])
        c.set(hx + 4, oy + 5, C["white"])
        c.set(hx + 4, oy + 6, C["white"])
        # Right eye (1px golden cheek margin on outer right)
        c.rect(hx + 8, oy + 5, 2, 2, C["eye"])
        c.set(hx + 8, oy + 5, C["white"])

    # --- Joyful Open Smile (centered cleanly between her eyes & cheeks) ---
    if startled:
        c.set(hx + 7, oy + 8, C["smile_dark"])
    else:
        c.hline(hx + 6, oy + 7, 2, C["smile_dark"])
        c.set(hx + 7, oy + 8, C["smile_tongue"])

    # --- Puffy Baby-Pink Bloomer Romper ---
    # Collar & upper romper
    c.hline(bx + 3, oy + 10, 7, C["romper_hi"])
    c.rect(bx + 2, oy + 11, 9, 2, C["romper_main"])
    c.vline(bx + 2, oy + 11, 2, C["romper_shade"])
    # Puffy round bloomer shorts
    c.rect(bx + 2, oy + 13, 9, 3, C["romper_main"])
    c.hline(bx + 3, oy + 13, 7, C["romper_hi"])
    c.vline(bx + 2, oy + 13, 3, C["romper_shade"])
    c.hline(bx + 2, oy + 15, 9, C["romper_shade"])
    # Bloomer ruffled leg cuffs
    c.hline(bx + 3, oy + 15, 3, C["bonnet_ruffle"])
    c.hline(bx + 7, oy + 15, 3, C["bonnet_ruffle"])
    # Cute little golden paws clasped happily in front!
    c.rect(bx + 6, oy + 11, 4, 2, C["gold_main"])
    c.set(bx + 7, oy + 11, C["gold_hi"])
    c.set(bx + 8, oy + 12, C["gold_shade"])

    # --- Cozy Winter Scarf (snowy state) ---
    if scarf:
        c.hline(bx + 2, oy + 10, 9, C["scarf_teal"])
        c.set(bx + 4, oy + 10, C["scarf_mint"])
        c.set(bx + 7, oy + 10, C["scarf_mint"])
        c.rect(bx, oy + 11 + scarf_flutter, 2, 2, C["scarf_teal"])
        c.set(bx, oy + 12 + scarf_flutter, C["scarf_mint"])

    # --- Tiny Yellow Feet ---
    c.hline(bx + 3, oy + 16, 3, C["gold_main"])
    c.set(bx + 3, oy + 16, C["gold_shade"])
    c.hline(bx + 7, oy + 16, 3, C["gold_main"])
    c.set(bx + 7, oy + 16, C["gold_shade"])


def draw_lulu(
    c: Canvas,
    ox: int,
    oy: int,
    *,
    blink: bool = False,
    squint: bool = False,
    startled: bool = False,
    sunglasses: bool = False,
    glint_x: int = -1,
    scarf: bool = False,
    scarf_flutter: int = 0,
    lean_x: int = 0,
    orange_shift: int = 0,
    holding_phone: bool = False,
    phone_glow: bool = False,
) -> None:
    """
    Draw Lulu (RIGHT character, ~14w x 17h from tangerine to feet):
      - Plump bright tangerine with tiny green stem atop his golden head
      - Pear-shaped chubby golden-yellow head with two small round ears
      - Wide peach-orange lower snout/cheeks & iconic sleepy half-lidded eyes
      - Bright orange-coral strawberry shorts & chubby sitting yellow feet
    Anchor (ox, oy) is top-left of his head box; tangerine sits at oy-3..oy-1.
    """
    hx = ox + lean_x
    bx = ox

    # --- Plump Tangerine with Tiny Green Stem on Head ---
    tx = hx + 5 + orange_shift
    ty = oy - 2
    c.set(tx + 1, ty - 1, C["stem_green"])
    c.hline(tx, ty, 3, C["orange_main"])
    c.set(tx, ty, C["orange_hi"])
    c.hline(tx, ty + 1, 3, C["orange_main"])
    c.set(tx + 2, ty + 1, C["orange_dark"])

    # --- Small Round Golden Ears ---
    c.rect(hx + 2, oy + 1, 2, 2, C["gold_main"])
    c.set(hx + 2, oy + 2, C["gold_dark"])
    c.rect(hx + 10, oy + 1, 2, 2, C["gold_main"])
    c.set(hx + 11, oy + 2, C["gold_dark"])

    # --- Iconic Pear-Shaped Chubby Golden Head ---
    # Narrower rounded golden forehead
    c.hline(hx + 4, oy, 6, C["gold_hi"])
    c.hline(hx + 3, oy + 1, 8, C["gold_hi"])
    c.rect(hx + 2, oy + 2, 10, 3, C["gold_main"])
    c.vline(hx + 11, oy + 2, 3, C["gold_shade"])
    # Wide chubby lower head & soft rounded peach-orange muzzle/cheeks!
    c.rect(hx + 1, oy + 5, 12, 4, C["gold_main"])
    c.vline(hx + 12, oy + 5, 4, C["gold_shade"])
    c.hline(hx + 2, oy + 9, 10, C["gold_shade"])
    # Soft rounded peach-orange muzzle glow across his chubby lower face
    c.hline(hx + 3, oy + 5, 6, C["snout_hi"])
    c.hline(hx + 2, oy + 6, 8, C["snout_hi"])
    c.hline(hx + 2, oy + 7, 8, C["snout_main"])
    c.hline(hx + 3, oy + 8, 6, C["snout_main"])
    c.hline(hx + 4, oy + 9, 4, C["snout_shade"])
    # Subtle tiny 2px deadpan mouth
    c.hline(hx + 5, oy + 8, 2, C["mouth_line"])

    # --- Iconic Sleepy Half-Lidded Eyes! ---
    if sunglasses:
        c.hline(hx + 2, oy + 3, 9, C["shades_frame"])
        c.rect(hx + 2, oy + 3, 4, 2, C["shades_lens"])
        c.rect(hx + 7, oy + 3, 4, 2, C["shades_lens"])
        c.set(hx + 6, oy + 3, C["shades_frame"])
        if 0 <= glint_x <= 7:
            gx = hx + 2 + glint_x
            if hx + 2 <= gx <= hx + 5 or hx + 7 <= gx <= hx + 10:
                c.set(gx, oy + 3, C["shades_glint"])
    elif squint:
        c.hline(hx + 3, oy + 4, 2, C["eye"])
        c.hline(hx + 7, oy + 4, 2, C["eye"])
    elif blink:
        c.hline(hx + 3, oy + 4, 2, C["mouth_line"])
        c.hline(hx + 7, oy + 4, 2, C["mouth_line"])
    elif startled:
        # Wide-open surprised eyes during thunder!
        c.rect(hx + 3, oy + 3, 2, 2, C["white"])
        c.set(hx + 3, oy + 4, C["eye"])
        c.rect(hx + 7, oy + 3, 2, 2, C["white"])
        c.set(hx + 7, oy + 4, C["eye"])
    else:
        # Heavy sleepy golden upper eyelids covering top half of eyes
        c.hline(hx + 3, oy + 3, 2, C["gold_shade"])
        c.hline(hx + 7, oy + 3, 2, C["gold_shade"])
        # Half-lidded dark eyes with tiny white corner
        c.set(hx + 3, oy + 4, C["eye"])
        c.set(hx + 4, oy + 4, C["white"])
        c.set(hx + 7, oy + 4, C["eye"])
        c.set(hx + 8, oy + 4, C["white"])

    # --- Chubby Golden Torso ---
    c.rect(bx + 2, oy + 10, 10, 3, C["gold_main"])
    c.vline(bx + 11, oy + 10, 3, C["gold_shade"])
    c.hline(bx + 3, oy + 10, 7, C["gold_hi"])

    # --- Cozy Winter Scarf (snowy state) ---
    if scarf:
        c.hline(bx + 2, oy + 10, 10, C["scarf_red"])
        c.set(bx + 4, oy + 10, C["scarf_gold"])
        c.set(bx + 7, oy + 10, C["scarf_gold"])
        c.set(bx + 10, oy + 10, C["scarf_gold"])
        c.rect(bx + 11, oy + 11 + scarf_flutter, 2, 2, C["scarf_red"])
        c.set(bx + 12, oy + 12 + scarf_flutter, C["scarf_gold"])

    # --- Bright Orange-Coral Strawberry Shorts ---
    c.rect(bx + 2, oy + 12, 10, 3, C["shorts_main"])
    c.hline(bx + 3, oy + 12, 8, C["shorts_hi"])
    c.vline(bx + 11, oy + 12, 3, C["shorts_dark"])
    c.hline(bx + 2, oy + 14, 10, C["shorts_dark"])
    # Subtle strawberry seed accents
    c.set(bx + 4, oy + 13, C["shorts_seed"])
    c.set(bx + 9, oy + 13, C["shorts_seed"])

    # --- Little Chubby Sitting Yellow Feet ---
    c.rect(bx + 1, oy + 14, 3, 2, C["gold_main"])
    c.set(bx + 1, oy + 15, C["gold_shade"])
    c.rect(bx + 8, oy + 14, 3, 2, C["gold_main"])
    c.set(bx + 10, oy + 15, C["gold_shade"])

    # --- Optional Tiny Smartphone (iconic reference pose in default idle!) ---
    if holding_phone:
        c.rect(bx + 2, oy + 9, 3, 3, C["phone_body"])
        c.vline(bx + 2, oy + 9, 3, C["phone_dark"])
        if phone_glow:
            c.set(bx + 4, oy + 10, C["phone_glow"])
        # Cute chubby paw holding phone
        c.rect(bx + 5, oy + 10, 3, 2, C["gold_hi"])
        c.set(bx + 5, oy + 11, C["gold_main"])


# ---------------------------------------------------------------------------
# Weather Scene Generators (each returns 150 RGBA 32x32 frames)
# ---------------------------------------------------------------------------
def render_sunny_frame(f: int) -> Image.Image:
    c = Canvas()
    c.gradient_v((14, 38, 86, 255), (24, 68, 128, 255), 0, 28)
    # Warm sunny meadow ground
    c.hline(0, 28, WIDTH, C["grass_hi"])
    c.rect(0, 29, WIDTH, 3, C["grass_mid"])
    c.hline(0, 31, WIDTH, C["grass_dark"])

    # Drifting fluffy cloud wrapping seamlessly behind the sun (1 full pass in 150 frames)
    cx = wrap_pos(3, 1, f, WIDTH, direction=1)
    for dx, dy in [(0, 1), (1, 0), (2, 0), (3, 0), (4, 1), (1, 1), (2, 1), (3, 1)]:
        c.set((cx + dx) % WIDTH, 4 + dy, (204, 224, 248, 255))

    # Spinning sun in top-right (drawn in front of cloud)
    sx, sy = 26, 4
    c.hline(sx - 1, sy - 2, 3, C["sun_core"])
    c.rect(sx - 2, sy - 1, 5, 3, C["sun_core"])
    c.hline(sx - 1, sy + 2, 3, C["sun_core"])
    ray_phase = (f // 5) % 2
    if ray_phase == 0:
        for rx, ry in [(0, -3), (0, 3), (-3, 0), (3, 0), (-3, -2), (3, -2), (-3, 2), (3, 2)]:
            c.set(sx + rx, sy + ry, C["sun_ray"])
    else:
        for rx, ry in [(-1, -3), (1, 3), (-3, 1), (3, -1), (-2, -3), (2, -3), (-2, 3), (2, 3)]:
            c.set(sx + rx, sy + ry, C["sun_ray"])

    # Bobbing (period 30 = 5 cycles) + sunglasses glint (period 50 = 3 cycles)
    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    glint_step = f % 50
    glint_x = glint_step if glint_step <= 7 else -1
    sprout_sway = 1 if (f % 30) < 15 else 0

    draw_lumei(
        c, 1, 12 + bob_lumei,
        sunglasses=True, glint_x=glint_x, sprout_sway=sprout_sway,
    )
    draw_lulu(
        c, 17, 13 + bob_lulu,
        sunglasses=True, glint_x=glint_x,
    )

    # One-off Watermelon Eating Event (resolves completely before frame 150)
    mx, my = 12, 23 + bob_lumei
    if f < 35 or f >= 125:
        bite_stage = 0
    elif f < 55:
        bite_stage = 1 if (f % 4 < 2) else 0
    elif f < 85:
        bite_stage = 1
    elif f < 105:
        bite_stage = 2 if (f % 4 < 2) else 1
    else:
        bite_stage = 2

    c.hline(mx, my + 4, 7, C["melon_rind"])
    c.hline(mx + 1, my + 5, 5, C["melon_rind"])
    c.hline(mx + 1, my + 3, 5, C["melon_pith"])
    if bite_stage == 0:
        c.hline(mx + 1, my + 2, 5, C["melon_pink"])
        c.hline(mx + 2, my + 1, 3, C["melon_pink"])
        c.set(mx + 3, my, C["melon_pink"])
        c.set(mx + 2, my + 2, C["melon_seed"])
        c.set(mx + 4, my + 2, C["melon_seed"])
    elif bite_stage == 1:
        c.hline(mx + 1, my + 2, 5, C["melon_pink"])
        c.set(mx + 2, my + 1, C["melon_pink"])
        c.set(mx + 4, my + 2, C["melon_seed"])
    else:
        c.hline(mx + 2, my + 2, 3, C["melon_pink"])

    if 36 <= f <= 48:
        dt = f - 36
        c.set(mx + 1 - dt // 5, my - 1 - dt // 4, C["melon_pink"])
        c.set(mx + 5 + dt // 6, my - 1 - dt // 5, C["melon_seed"])
    elif 106 <= f <= 122:
        dt = f - 106
        hy = 11 - dt // 4
        c.set(14, hy, C["heart"])
        c.set(16, hy, C["heart"])
        c.hline(14, hy + 1, 3, C["heart"])
        c.set(15, hy + 2, C["heart"])

    return c.img


RAIN_DROPS = [
    (2, 1, True), (7, 14, False), (11, 5, True), (16, 22, False),
    (20, 9, True), (25, 18, False), (29, 3, True), (4, 26, False),
    (9, 19, True), (14, 11, False), (18, 28, True), (23, 6, False),
    (27, 24, True), (31, 13, False), (1, 16, True), (13, 29, False),
    (22, 1, True), (28, 10, False),
]


def render_rainy_frame(f: int) -> Image.Image:
    c = Canvas()
    c.gradient_v((10, 16, 32, 255), (16, 28, 48, 255), 0, 29)

    # Stormy cloud canopy at top
    cx = wrap_pos(0, 1, f, WIDTH, direction=1)
    c.rect(0, 0, WIDTH, 2, C["cloud_dark"])
    for seg in range(0, WIDTH, 8):
        px = (cx + seg) % WIDTH
        for dx in range(6):
            c.set((px + dx) % WIDTH, 2, C["cloud_mid"])
        for dx in range(1, 5):
            c.set((px + dx) % WIDTH, 3, C["cloud_dark"])

    # Wet ground & puddle ripples
    c.rect(0, 29, WIDTH, 3, (18, 36, 62, 255))
    c.hline(0, 29, WIDTH, (30, 56, 92, 255))

    rip = f % 30
    if rip < 10:
        c.hline(3, 30, 2, C["rain_bright"])
    elif rip < 20:
        c.set(2, 30, C["rain_dim"])
        c.set(5, 30, C["rain_dim"])
    rip2 = (f + 15) % 30
    if rip2 < 10:
        c.hline(26, 30, 2, C["rain_bright"])
    elif rip2 < 20:
        c.set(25, 30, C["rain_dim"])
        c.set(28, 30, C["rain_dim"])

    # Huddled closer under the shared blue umbrella
    bob = bob_offset(f, period=30, phase=0)
    blink_lumei = (f % 50) in (12, 13)
    blink_lulu = (f % 50) in (34, 35)
    sprout_sway = 1 if (f % 30) < 15 else 0

    draw_lumei(c, 3, 13 + bob, blink=blink_lumei, sprout_sway=sprout_sway)
    draw_lulu(c, 16, 14 + bob, blink=blink_lulu)

    # Blue umbrella arching cleanly above Lumei's sprout and Lulu's tangerine
    uy = 4 + bob
    c.vline(15, uy + 5, 16, C["umb_handle"])
    c.set(14, uy + 21, C["umb_handle"])
    c.set(15, uy - 1, C["umb_light"])
    c.hline(12, uy, 7, C["umb_light"])
    c.hline(9, uy + 1, 13, C["umb_blue"])
    c.hline(12, uy + 1, 4, C["umb_light"])
    c.hline(6, uy + 2, 19, C["umb_blue"])
    c.hline(4, uy + 3, 23, C["umb_blue"])
    c.hline(3, uy + 4, 25, C["umb_dark"])
    for rx in (7, 15, 23):
        c.set(rx, uy + 4, (16, 28, 48, 255))
    c.vline(11, uy + 1, 3, C["umb_light"])
    c.vline(19, uy + 1, 3, C["umb_dark"])

    # Falling slanted raindrops (exact modulo wrap: Ky=15, Kx=-5)
    for x0, y0, bright in RAIN_DROPS:
        rx = wrap_pos(x0, 5, f, WIDTH, direction=-1)
        ry = wrap_pos(y0, 15, f, HEIGHT, direction=1)
        if 3 <= rx <= 27 and ry >= uy + 3:
            continue
        col = C["rain_bright"] if bright else C["rain_dim"]
        c.set(rx, ry, col)
        if 4 <= rx <= 26 and uy <= ry <= uy + 2:
            c.set(rx, uy - 1, C["white"])
        else:
            c.set((rx + 1) % WIDTH, (ry - 1) % HEIGHT, C["rain_dim"])

    return c.img


SNOW_FLAKES = [
    (2, 2, 0.0, True), (7, 15, 1.1, False), (12, 7, 2.2, False), (17, 23, 0.7, True),
    (22, 4, 3.1, False), (27, 19, 1.9, False), (30, 11, 4.0, True), (5, 27, 2.5, False),
    (10, 19, 5.0, False), (15, 1, 1.4, False), (20, 14, 3.7, True), (25, 28, 0.3, False),
    (29, 6, 2.9, False), (1, 12, 4.5, False), (14, 26, 1.6, False), (24, 10, 5.4, False),
]


def render_snowy_frame(f: int) -> Image.Image:
    c = Canvas()
    c.gradient_v((8, 16, 36, 255), (16, 30, 58, 255), 0, 28)

    # Snowy ground mounds
    c.rect(0, 28, WIDTH, 4, C["snow_ground"])
    c.hline(0, 28, WIDTH, C["white"])
    c.hline(0, 30, WIDTH, C["snow_shadow"])
    c.hline(0, 31, WIDTH, C["snow_shadow"])
    c.hline(2, 27, 9, C["snow_ground"])
    c.hline(19, 27, 11, C["snow_ground"])

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    flutter = 1 if (f % 30) >= 15 else 0
    blink_lumei = (f % 50) in (10, 11)
    blink_lulu = (f % 50) in (36, 37)
    sprout_sway = 1 if (f % 30) < 15 else 0

    draw_lumei(
        c, 2, 12 + bob_lumei,
        blink=blink_lumei, scarf=True, scarf_flutter=flutter, sprout_sway=sprout_sway,
    )
    draw_lulu(
        c, 17, 13 + bob_lulu,
        blink=blink_lulu, scarf=True, scarf_flutter=1 - flutter,
    )

    # Cozy warm breath puffs (period 75 -> 2 exact cycles)
    bt = f % 75
    if 10 <= bt <= 22:
        step = (bt - 10) // 4
        c.set(13 + step, 19 - step // 2, C["snow_mid"])
        if step < 2:
            c.set(14 + step, 18 - step // 2, C["white"])
    bt2 = (f + 37) % 75
    if 10 <= bt2 <= 22:
        step = (bt2 - 10) // 4
        c.set(17 - step, 20 - step // 2, C["snow_mid"])

    # Falling snowflakes (Ky=3 exact wrap + 5-cycle sine sway)
    for x0, y0, phase, is_big in SNOW_FLAKES:
        sy = wrap_pos(y0, 3, f, HEIGHT, direction=1)
        sway = int(round(1.5 * wave_sin(f, cycles=5, phase=phase)))
        sx = (x0 + sway) % WIDTH
        if sy < 29:
            if is_big:
                c.set(sx, sy, C["snow_bright"])
                c.set((sx - 1) % WIDTH, sy, C["snow_mid"])
                c.set((sx + 1) % WIDTH, sy, C["snow_mid"])
            else:
                c.set(sx, sy, C["snow_bright"] if (x0 % 2 == 0) else C["snow_mid"])

    return c.img


WIND_LEAVES = [
    (2, 4, 0.0, "leaf_orange"), (9, 12, 1.3, "leaf_gold"),
    (16, 7, 2.4, "leaf_red"), (23, 18, 0.8, "leaf_orange"),
    (29, 9, 3.6, "leaf_sage"), (5, 22, 4.8, "leaf_gold"),
    (12, 26, 1.9, "leaf_red"), (20, 2, 5.2, "leaf_orange"),
    (26, 24, 2.9, "leaf_gold"), (14, 15, 4.1, "leaf_sage"),
    (1, 16, 0.5, "leaf_red"), (30, 14, 3.1, "leaf_orange"),
]


def render_windy_frame(f: int) -> Image.Image:
    c = Canvas()
    c.gradient_v((10, 24, 36, 255), (18, 42, 56, 255), 0, 28)

    c.hline(0, 28, WIDTH, C["grass_hi"])
    c.rect(0, 29, WIDTH, 3, C["grass_mid"])
    c.hline(0, 31, WIDTH, C["grass_dark"])

    # Horizontal gust wind streaks wrapping cleanly (Kx = 15)
    for row_y, offset, length in [(4, 0, 7), (10, 11, 9), (17, 21, 6), (24, 6, 8)]:
        wx = wrap_pos(offset, 15, f, WIDTH, direction=1)
        for dx in range(length):
            col = C["wind_streak"] if dx >= length - 3 else C["wind_dim"]
            c.set((wx + dx) % WIDTH, row_y, col)

    gust = (f % 30) < 18
    lean = 1 if gust else 0
    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=10)
    orange_jiggle = 1 if (f % 15) < 7 else 0

    draw_lumei(
        c, 1, 12 + bob_lumei,
        squint=True, lean_x=lean, sprout_sway=1,
    )
    draw_lulu(
        c, 17, 13 + bob_lulu,
        squint=True, lean_x=lean, orange_shift=orange_jiggle,
    )

    # Swirling autumn leaves (Kx=10, Ky=3, sine swirl cycles=5)
    spin = (f // 3) % 2
    for x0, y0, phase, col_key in WIND_LEAVES:
        lx = wrap_pos(x0, 10, f, WIDTH, direction=1)
        swirl_y = int(round(2.5 * wave_sin(f, cycles=5, phase=phase)))
        ly = (wrap_pos(y0, 3, f, HEIGHT, direction=1) + swirl_y) % HEIGHT
        col = C[col_key]
        c.set(lx, ly, col)
        if spin == 0:
            c.set((lx + 1) % WIDTH, ly, col)
        else:
            c.set((lx + 1) % WIDTH, (ly + 1) % HEIGHT, col)

    return c.img


def render_thunderstorm_frame(f: int) -> Image.Image:
    flash_1 = f in (32, 33, 36)
    flash_2 = f in (102, 103, 106)
    is_flashing = flash_1 or flash_2
    startled = (32 <= f <= 44) or (102 <= f <= 114)

    c = Canvas()
    if is_flashing:
        c.gradient_v((64, 78, 114, 255), (36, 48, 78, 255), 0, 29)
    else:
        c.gradient_v((6, 9, 20, 255), (14, 20, 38, 255), 0, 29)

    c.rect(0, 29, WIDTH, 3, (12, 18, 32, 255))

    # Storm clouds at top
    cx = wrap_pos(0, 1, f, WIDTH, direction=1)
    cloud_top = (72, 86, 120, 255) if is_flashing else (24, 30, 48, 255)
    cloud_bot = (110, 126, 166, 255) if is_flashing else C["cloud_mid"]
    c.rect(0, 0, WIDTH, 3, cloud_top)
    for seg in range(0, WIDTH, 8):
        px = (cx + seg) % WIDTH
        for dx in range(6):
            c.set((px + dx) % WIDTH, 3, cloud_bot)
        for dx in range(1, 5):
            c.set((px + dx) % WIDTH, 4, cloud_top)

    # Jagged lightning bolts
    if flash_1:
        bolt_pts = [(24, 4), (23, 5), (22, 6), (23, 7), (24, 8), (23, 9), (22, 10), (21, 11), (22, 12)]
        for bx, by in bolt_pts:
            c.set(bx - 1, by, C["bolt_glow"])
            c.set(bx + 1, by, C["bolt_glow"])
            c.set(bx, by, C["bolt_core"])
    elif flash_2:
        bolt_pts = [(7, 4), (8, 5), (9, 6), (8, 7), (7, 8), (8, 9), (9, 10), (8, 11)]
        for bx, by in bolt_pts:
            c.set(bx - 1, by, C["bolt_glow"])
            c.set(bx + 1, by, C["bolt_glow"])
            c.set(bx, by, C["bolt_core"])

    # Heavy slanted rain
    for x0, y0, bright in RAIN_DROPS:
        rx = wrap_pos(x0, 5, f, WIDTH, direction=-1)
        ry = wrap_pos(y0, 15, f, HEIGHT, direction=1)
        col = C["rain_bright"] if (bright or is_flashing) else C["rain_dim"]
        c.set(rx, ry, col)
        c.set((rx + 1) % WIDTH, (ry - 1) % HEIGHT, C["rain_dim"])

    shiver = (1 if (f % 2 == 0) else 0) if startled else 0
    duck = 1 if startled else bob_offset(f, period=30, phase=0)
    by = 13 + duck

    draw_lumei(
        c, 2 + shiver, by,
        blink=(not startled and (f % 50) in (14, 15)),
        startled=startled,
    )
    draw_lulu(
        c, 16 + shiver, by + 1,
        blink=(not startled and (f % 50) in (38, 39)),
        startled=startled,
    )

    # Cozy starry purple blanket draped over both bodies
    top_y = by + 9
    c.hline(3 + shiver, top_y, 25, C["blanket_hi"])
    c.rect(2 + shiver, top_y + 1, 27, max(1, 29 - (top_y + 1)), C["blanket_main"])
    c.vline(2 + shiver, top_y + 1, max(1, 29 - (top_y + 1)), C["blanket_dark"])
    c.vline(15 + shiver, top_y + 2, max(1, 28 - (top_y + 2)), C["blanket_dark"])
    c.vline(28 + shiver, top_y + 1, max(1, 29 - (top_y + 1)), C["blanket_dark"])
    c.hline(2 + shiver, 28, 27, C["blanket_dark"])
    for sx, sy in [(6, top_y + 2), (12, top_y + 4), (20, top_y + 2), (25, top_y + 4)]:
        if sy < 28:
            c.set(sx + shiver, sy, C["blanket_star"])

    return c.img


def render_default_frame(f: int) -> Image.Image:
    c = Canvas()
    c.gradient_v((7, 12, 28, 255), (14, 24, 48, 255), 0, 28)

    c.hline(0, 28, WIDTH, C["grass_hi"])
    c.rect(0, 29, WIDTH, 3, C["grass_mid"])
    c.hline(0, 31, WIDTH, C["grass_dark"])

    # Twinkling stars (periods 30 and 50 -> exact divisors of 150)
    stars = [
        (3, 3, 30, 0), (11, 2, 50, 10), (19, 4, 30, 15),
        (29, 8, 50, 25), (6, 7, 30, 7), (15, 7, 50, 35),
    ]
    for sx, sy, per, ph in stars:
        t = (f + ph) % per
        col = C["star_bright"] if t < per // 2 else C["star_dim"]
        c.set(sx, sy, col)

    # Crescent moon in top-right
    mx, my = 25, 2
    for dx, dy in [(1, 0), (2, 0), (0, 1), (1, 1), (0, 2), (1, 2), (1, 3), (2, 3)]:
        c.set(mx + dx, my + dy, C["moon"])

    # Wispy night cloud drifting seamlessly (1 exact pass in 150 frames)
    cx = wrap_pos(2, 1, f, WIDTH, direction=1)
    for dx, dy in [(0, 1), (1, 0), (2, 0), (3, 0), (4, 1), (1, 1), (2, 1), (3, 1)]:
        c.set((cx + dx) % WIDTH, 5 + dy, (42, 60, 96, 255))

    # Relaxed idle bobbing (period 30 -> 5 cycles) & natural blinking (period 50 -> 3 cycles)
    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    blink_lumei = (f % 50) in (12, 13)
    blink_lulu = (f % 50) in (34, 35)
    sprout_sway = 1 if (f % 30) < 15 else 0
    phone_glow = (f % 30) < 15

    # Lumei smiling happily on the left; Lulu chilling with his little phone on the right!
    draw_lumei(c, 1, 12 + bob_lumei, blink=blink_lumei, sprout_sway=sprout_sway)
    draw_lulu(
        c, 17, 13 + bob_lulu,
        blink=blink_lulu, holding_phone=True, phone_glow=phone_glow,
    )

    # Periodic floating heart between them (period 75 -> 2 exact cycles)
    ht = f % 75
    if 20 <= ht <= 44:
        rise = (ht - 20) // 6
        hy = 12 - rise
        c.set(14, hy, C["heart"])
        c.set(16, hy, C["heart"])
        c.hline(14, hy + 1, 3, C["heart"])
        c.set(15, hy + 2, C["heart"])

    return c.img


SCENE_RENDERERS: Dict[str, Callable[[int], Image.Image]] = {
    "sunny": render_sunny_frame,
    "rainy": render_rainy_frame,
    "snowy": render_snowy_frame,
    "windy": render_windy_frame,
    "thunderstorm": render_thunderstorm_frame,
    "default": render_default_frame,
}


# ---------------------------------------------------------------------------
# Custom Art Importer (Aseprite GIF / Sprite Sheet / PNG Frame Directory)
# ---------------------------------------------------------------------------
def load_custom_frames(state: str) -> Optional[List[Image.Image]]:
    """
    Check `assets/custom/` for user-supplied hand-drawn frames for `state`.
    Supports:
      1. `assets/custom/<state>.gif`
      2. `assets/custom/<state>_sheet.png` (horizontal strip of 32x32 tiles)
      3. `assets/custom/<state>/*.png`     (sorted individual 32x32 frames)
    Automatically normalizes frame count to exact NUM_FRAMES (150) for a
    seamless 15-second loop.
    """
    raw_frames: List[Image.Image] = []

    gif_path = CUSTOM_DIR / f"{state}.gif"
    sheet_path = CUSTOM_DIR / f"{state}_sheet.png"
    folder_path = CUSTOM_DIR / state

    if gif_path.exists():
        with Image.open(gif_path) as im:
            n = getattr(im, "n_frames", 1)
            for idx in range(n):
                im.seek(idx)
                raw_frames.append(im.convert("RGBA").resize((WIDTH, HEIGHT), Image.Resampling.NEAREST))
        print(f"  [{state}] Loaded {len(raw_frames)} custom frames from {gif_path.name}")
    elif sheet_path.exists():
        with Image.open(sheet_path) as sheet:
            sheet = sheet.convert("RGBA")
            tile_h = sheet.height
            tile_w = tile_h
            count = max(1, sheet.width // tile_w)
            for idx in range(count):
                tile = sheet.crop((idx * tile_w, 0, (idx + 1) * tile_w, tile_h))
                raw_frames.append(tile.resize((WIDTH, HEIGHT), Image.Resampling.NEAREST))
        print(f"  [{state}] Loaded {len(raw_frames)} custom frames from {sheet_path.name}")
    elif folder_path.is_dir():
        pngs = sorted(folder_path.glob("*.png"))
        if pngs:
            for p in pngs:
                with Image.open(p) as im:
                    raw_frames.append(im.convert("RGBA").resize((WIDTH, HEIGHT), Image.Resampling.NEAREST))
            print(f"  [{state}] Loaded {len(raw_frames)} custom frames from {folder_path.name}/")

    if not raw_frames:
        return None

    if len(raw_frames) == NUM_FRAMES:
        return raw_frames

    if NUM_FRAMES % len(raw_frames) == 0:
        reps = NUM_FRAMES // len(raw_frames)
        print(f"  [{state}] Repeating {len(raw_frames)}-frame cycle x{reps} -> {NUM_FRAMES} frames (15.0s)")
        return (raw_frames * reps)[:NUM_FRAMES]

    print(f"  [{state}] Resampling {len(raw_frames)} custom frames -> {NUM_FRAMES} frames (15.0s)")
    return [raw_frames[(i * len(raw_frames)) // NUM_FRAMES] for i in range(NUM_FRAMES)]


# ---------------------------------------------------------------------------
# Quantization, Encoding & Preview Generation
# ---------------------------------------------------------------------------
def build_shared_palette(frames: List[Image.Image]) -> Image.Image:
    """Build a single global palette across all frames so GIFs stay tiny & flicker-free."""
    colors = set()
    for im in frames:
        rgb = im.convert("RGB")
        for _, col in rgb.getcolors(maxcolors=WIDTH * HEIGHT):
            colors.add(col)

    palette_list = sorted(colors)
    if len(palette_list) <= 256:
        pal_img = Image.new("P", (1, 1))
        flat: List[int] = []
        for r, g, b in palette_list:
            flat.extend((r, g, b))
        flat.extend([0, 0, 0] * (256 - len(palette_list)))
        pal_img.putpalette(flat)
        return pal_img

    strip = Image.new("RGB", (WIDTH * min(len(frames), 30), HEIGHT))
    for idx in range(min(len(frames), 30)):
        strip.paste(frames[idx].convert("RGB"), (idx * WIDTH, 0))
    return strip.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)


def enforce_constant_frame_rate(frames: List[Image.Image]) -> List[Image.Image]:
    """
    Prevent Pillow's GIF/WebP encoders from merging identical consecutive frames
    into variable-duration frames (which would desync Pixlet's fixed-delay
    `render.Root(delay=100)` playback from the 15-second duration).
    """
    assert NUM_FRAMES % 2 == 0
    out: List[Image.Image] = []
    for idx, im in enumerate(frames):
        copy = im.copy()
        if idx % 2 == 1:
            r, g, b, a = copy.getpixel((0, 0))
            b_adj = b + 8 if b <= 247 else b - 8
            copy.putpixel((0, 0), (r, g, b_adj, a))
        out.append(copy)
    return out


def encode_animated_gif(frames: List[Image.Image]) -> bytes:
    """Encode 150 crisp pixel-art frames to a compact, infinite-loop GIF."""
    cfr_frames = enforce_constant_frame_rate(frames)
    pal_img = build_shared_palette(cfr_frames)
    p_frames = [
        im.convert("RGB").quantize(palette=pal_img, dither=Image.Dither.NONE)
        for im in cfr_frames
    ]
    buf = io.BytesIO()
    p_frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=p_frames[1:],
        duration=FRAME_DELAY_MS,
        loop=0,
        optimize=True,
        disposal=1,
    )
    return buf.getvalue()


def save_animated_webp(frames: List[Image.Image], path: Path) -> int:
    """Save 150 crisp constant-rate frames to lossless animated WebP (loop=0)."""
    cfr_frames = enforce_constant_frame_rate(frames)
    cfr_frames[0].save(
        path,
        format="WEBP",
        save_all=True,
        append_images=cfr_frames[1:],
        duration=FRAME_DELAY_MS,
        loop=0,
        lossless=True,
        method=4,
    )
    return path.stat().st_size


def verify_seamless_loop(state: str, renderer: Callable[[int], Image.Image]) -> None:
    """Verify renderer(NUM_FRAMES) matches renderer(0) bit-for-bit."""
    f0 = renderer(0)
    f_wrap = renderer(NUM_FRAMES)
    if f0.tobytes() != f_wrap.tobytes():
        raise AssertionError(
            f"Seamless loop violation in '{state}': renderer(0) != renderer({NUM_FRAMES})!"
        )


def build_contact_sheet(state_frames: Dict[str, List[Image.Image]], scale: int = 6) -> Path:
    """Create an upscaled visual inspection PNG showing key frames of all 6 states."""
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    sample_indices = [0, 33, 60, 102, 130]
    pad = 8
    label_h = 16
    cell_w = WIDTH * scale
    cell_h = HEIGHT * scale
    sheet_w = pad + len(sample_indices) * (cell_w + pad)
    sheet_h = pad + len(STATES) * (cell_h + label_h + pad)

    sheet = Image.new("RGB", (sheet_w, sheet_h), (18, 20, 28))
    draw = ImageDraw.Draw(sheet)

    for row, state in enumerate(STATES):
        y_top = pad + row * (cell_h + label_h + pad)
        for col, f_idx in enumerate(sample_indices):
            x_left = pad + col * (cell_w + pad)
            draw.text((x_left, y_top), f"{state} f={f_idx}", fill=(220, 228, 240))
            upscaled = state_frames[state][f_idx].convert("RGB").resize(
                (cell_w, cell_h), Image.Resampling.NEAREST
            )
            sheet.paste(upscaled, (x_left, y_top + label_h))

    out_path = PREVIEWS_DIR / "all_states_contact_sheet.png"
    sheet.save(out_path)
    return out_path


def inject_sprites_into_star(b64_map: Dict[str, str], star_path: Path) -> None:
    """Update the generated sprites block inside capybara_clock.star."""
    if not star_path.exists():
        print(f"Note: {star_path} does not exist yet; skipping Starlark injection.")
        return

    text = star_path.read_text(encoding="utf-8")
    if SPRITE_BEGIN_MARKER not in text or SPRITE_END_MARKER not in text:
        raise RuntimeError(
            f"Markers not found in {star_path}. Expected:\n"
            f"  {SPRITE_BEGIN_MARKER}\n  {SPRITE_END_MARKER}"
        )

    lines = [
        SPRITE_BEGIN_MARKER,
        f"SPRITE_FRAME_COUNT = {NUM_FRAMES}",
        f"SPRITE_DELAY_MS = {FRAME_DELAY_MS}",
        "SPRITES_B64 = {",
    ]
    for state in STATES:
        b64 = b64_map[state]
        lines.append(f'    "{state}": "{b64}",')
    lines.append("}")
    lines.append(SPRITE_END_MARKER)

    replacement = "\n".join(lines)
    pattern = re.compile(
        re.escape(SPRITE_BEGIN_MARKER) + r".*?" + re.escape(SPRITE_END_MARKER),
        re.DOTALL,
    )
    new_text = pattern.sub(replacement, text, count=1)
    star_path.write_text(new_text, encoding="utf-8")
    print(f"Injected {len(b64_map)} base64-encoded animated GIF sprites into {star_path.name}")


# ---------------------------------------------------------------------------
# Main Entrypoint
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate 15-second seamless 32x32 sprites for Capybara Clock."
    )
    parser.add_argument(
        "--no-inject",
        action="store_true",
        help="Generate assets without updating capybara_clock.star",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Also generate upscaled contact sheet PNG in assets/previews/",
    )
    args = parser.parse_args()

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)

    print(
        f"Generating {len(STATES)} weather sprites "
        f"({WIDTH}x{HEIGHT}, {NUM_FRAMES} frames @ {FRAME_DELAY_MS}ms = {TOTAL_DURATION_MS / 1000:.1f}s, loop=0)..."
    )

    b64_map: Dict[str, str] = {}
    all_frames: Dict[str, List[Image.Image]] = {}

    for state in STATES:
        custom = load_custom_frames(state)
        if custom is not None:
            frames = custom
        else:
            renderer = SCENE_RENDERERS[state]
            verify_seamless_loop(state, renderer)
            frames = [renderer(f) for f in range(NUM_FRAMES)]

        assert len(frames) == NUM_FRAMES, f"Expected {NUM_FRAMES} frames, got {len(frames)}"
        all_frames[state] = frames

        gif_bytes = encode_animated_gif(frames)
        gif_path = ASSETS_DIR / f"{state}.gif"
        gif_path.write_bytes(gif_bytes)

        webp_path = ASSETS_DIR / f"{state}.webp"
        webp_size = save_animated_webp(frames, webp_path)

        b64_str = base64.b64encode(gif_bytes).decode("ascii")
        b64_map[state] = b64_str
        print(
            f"  [OK] {state:13s} | GIF: {len(gif_bytes):6d} B | "
            f"WebP: {webp_size:6d} B | b64: {len(b64_str):6d} chars | seamless=verified"
        )

    if args.preview:
        sheet = build_contact_sheet(all_frames)
        print(f"Saved preview contact sheet -> {sheet}")

    if not args.no_inject:
        inject_sprites_into_star(b64_map, STAR_FILE)


if __name__ == "__main__":
    main()
