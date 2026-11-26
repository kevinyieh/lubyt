#!/usr/bin/env python3
"""
Procedural Pixel-Art Sprite Generator & Custom Frame Importer
for the Tidbyt Weather-Reactive Capybara Clock (Lumei & Lulu).

Stage Dimensions:
  - 40 x 32 px animated right-hand stage (paired with compact 23px HUD + 1px divider = 64x32)
  - 150 frames @ 100 ms = 15.0 seconds, loop=0 (mathematically seamless)

Character Personalities (inspired by Lumei & Lulu / 噜噜与噜妹):
  - Lumei (Left): Expressive, sweet, energetic, and adorably "spicy" (生气的噜妹)
    when Lulu messes up or ignores her — complete with rosy flare, steam puffs,
    and quick forgiveness when he makes it up to her.
  - Lulu (Right): Chill, lazy, unbothered, glued to his phone or snacks,
    overconfident ("I got this"), goofy, and secretly sweet underneath.

15-Second Personality Storyboards (all wrap cleanly back to frame 0):
  - windy:        Mega gust blows Lulu's tangerine & Lulu right OFF-SCREEN; Lumei
                  rushes off-screen to rescue him, then marches back dragging him in!
  - sunny:        Greedy Lulu gobbles the whole watermelon -> spicy Lumei scolds him
                  with steam puffs -> Lulu leaves off-screen & returns with a giant fresh slice!
  - rainy:        Phone-glued Lulu drifts off with the umbrella -> soaked Lumei gets
                  spicy & yanks it back -> Lulu sheepishly shares it & hearts float up!
  - snowy:        Playful Lulu pelts Lumei with a snowball -> Lumei packs a GIANT
                  snowball & chases Lulu to the screen edge -> happy snowy truce!
  - thunderstorm: Overconfident Lulu sits outside the blanket -> huge lightning bolt
                  sends him leaping head-first under the blanket next to Lumei!
  - default:      Starry night reference-photo gag: Lulu glued to his phone -> spicy
                  Lumei marches over & snatches it -> sweet nuzzle + twin hearts!
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
# Core Animation Timing & Stage Constants (15-second seamless loop)
# ---------------------------------------------------------------------------
WIDTH = 40
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
    # Lulu's warm peach-orange snout/cheeks & mouth
    "snout_main": (242, 148, 58, 255),
    "snout_hi": (252, 184, 102, 255),
    "snout_shade": (214, 114, 38, 255),
    "mouth_line": (136, 68, 28, 255),
    # Lumei's rosy blush, angry blush & happy smile
    "cheek_peach": (246, 146, 116, 255),
    "cheek_angry": (255, 64, 76, 255),
    "smile_dark": (110, 36, 44, 255),
    "smile_tongue": (224, 102, 112, 255),
    "anger_red": (255, 58, 68, 255),
    "steam": (244, 248, 255, 255),
    "steam_dim": (184, 200, 224, 255),
    "exclaim": (255, 224, 64, 255),
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
    # Eyes, phone & basics
    "eye": (24, 16, 14, 255),
    "white": (255, 255, 255, 255),
    "phone_body": (68, 74, 88, 255),
    "phone_dark": (40, 44, 54, 255),
    "phone_glow": (166, 222, 255, 255),
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
    "wind_streak": (122, 194, 214, 255),
    "wind_dim": (62, 114, 136, 255),
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
# Low-level Pixel Drawing Helpers (bounds-safe so off-screen exits work cleanly!)
# ---------------------------------------------------------------------------
class Canvas:
    """Bounds-safe 40x32 RGBA pixel canvas (silently clips off-screen sprites)."""

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
# Seamless Loop Math & Interpolation Helpers
# ---------------------------------------------------------------------------
def wave_sin(frame: int, cycles: int, phase: float = 0.0) -> float:
    return math.sin(2.0 * math.pi * cycles * frame / NUM_FRAMES + phase)


def bob_offset(frame: int, period: int = 30, phase: int = 0) -> int:
    assert NUM_FRAMES % period == 0, f"Period {period} must divide {NUM_FRAMES}"
    return 1 if ((frame + phase) % period) >= period // 2 else 0


def wrap_pos(start: int, cycles: int, frame: int, size: int = WIDTH, direction: int = 1) -> int:
    """Exact toroidal position: wrap_pos(..., frame=150) == wrap_pos(..., frame=0)."""
    delta = (cycles * size * frame) // NUM_FRAMES
    return (start + direction * delta) % size


def lerp_i(a: float, b: float, t: float) -> int:
    """Clamped linear interpolation returning nearest integer pixel coordinate."""
    t_c = max(0.0, min(1.0, t))
    return int(round(a + (b - a) * t_c))


def ease_in_out(t: float) -> float:
    t_c = max(0.0, min(1.0, t))
    return 0.5 - 0.5 * math.cos(math.pi * t_c)


# ---------------------------------------------------------------------------
# Expressive Emote & Prop Helpers
# ---------------------------------------------------------------------------
def draw_heart(c: Canvas, cx: int, cy: int) -> None:
    c.set(cx - 1, cy, C["heart"])
    c.set(cx + 1, cy, C["heart"])
    c.hline(cx - 1, cy + 1, 3, C["heart"])
    c.set(cx, cy + 2, C["heart"])


def draw_anger_steam(c: Canvas, cx: int, cy: int, tick: int) -> None:
    """Adorable spicy Lumei anger puff + tiny comic vein!"""
    # Little red anger cross/vein
    c.set(cx, cy, C["anger_red"])
    c.set(cx + 2, cy, C["anger_red"])
    c.set(cx + 1, cy + 1, C["anger_red"])
    # Rising white steam puffs
    rise = tick % 4
    c.set(cx - 2, cy - 1 - rise // 2, C["steam"])
    c.set(cx + 3, cy - 1 - ((rise + 2) % 4) // 2, C["steam_dim"])


def draw_exclaim(c: Canvas, cx: int, cy: int) -> None:
    c.vline(cx, cy, 3, C["exclaim"])
    c.set(cx, cy + 4, C["exclaim"])


def draw_tangerine(c: Canvas, tx: int, ty: int) -> None:
    """Standalone plump tangerine (can sit on Lulu's head OR pop off in the wind!)."""
    c.set(tx + 1, ty - 1, C["stem_green"])
    c.hline(tx, ty, 3, C["orange_main"])
    c.set(tx, ty, C["orange_hi"])
    c.hline(tx, ty + 1, 3, C["orange_main"])
    c.set(tx + 2, ty + 1, C["orange_dark"])


def draw_watermelon(c: Canvas, mx: int, my: int, bite_stage: int = 0) -> None:
    """Watermelon slice: stage 0=full, 1=1 bite, 2=almost gone, 3=tiny rind."""
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
    elif bite_stage == 2:
        c.hline(mx + 2, my + 2, 3, C["melon_pink"])


def draw_umbrella(c: Canvas, cx: int, uy: int, handle_h: int = 16) -> None:
    """Shared blue umbrella centered horizontally at `cx`."""
    c.vline(cx, uy + 5, handle_h, C["umb_handle"])
    c.set(cx - 1, uy + 5 + handle_h, C["umb_handle"])
    c.set(cx, uy - 1, C["umb_light"])
    c.hline(cx - 3, uy, 7, C["umb_light"])
    c.hline(cx - 6, uy + 1, 13, C["umb_blue"])
    c.hline(cx - 3, uy + 1, 4, C["umb_light"])
    c.hline(cx - 9, uy + 2, 19, C["umb_blue"])
    c.hline(cx - 11, uy + 3, 23, C["umb_blue"])
    c.hline(cx - 12, uy + 4, 25, C["umb_dark"])
    for rx in (cx - 8, cx, cx + 8):
        c.set(rx, uy + 4, (16, 28, 48, 255))
    c.vline(cx - 4, uy + 1, 3, C["umb_light"])
    c.vline(cx + 4, uy + 1, 3, C["umb_dark"])


# ---------------------------------------------------------------------------
# Character Primitives: Expressive Lumei & Chill Lulu
# ---------------------------------------------------------------------------
def draw_lumei(
    c: Canvas,
    ox: int,
    oy: int,
    *,
    mood: str = "happy",  # "happy", "blink", "spicy", "startled", "squint", "delighted"
    sunglasses: bool = False,
    glint_x: int = -1,
    scarf: bool = False,
    scarf_flutter: int = 0,
    lean_x: int = 0,
    sprout_sway: int = 0,
    walk_step: int = 0,
    holding_phone: bool = False,
    snow_on_bonnet: bool = False,
) -> None:
    """
    Draw Lumei (~12w x 18h from sprout to feet).
    Supports walking steps, spicy/angry expressions, surprised gasps, and delighted eyes.
    """
    hx = ox + lean_x
    bx = ox

    # --- V-shaped green twin-leaf sprout + tiny orange nub + cream halo ring ---
    cx = hx + 5
    c.set(cx - 1 + sprout_sway, oy - 3, C["sprout_hi"])
    c.set(cx + 1 + sprout_sway, oy - 3, C["sprout_hi"])
    c.set(cx + sprout_sway, oy - 2, C["sprout_green"])
    c.hline(cx - 2, oy - 1, 5, C["halo_cream"])
    c.set(cx, oy - 1, C["orange_main"])
    c.set(cx - 2, oy - 1, C["halo_shade"])
    c.set(cx + 2, oy - 1, C["halo_shade"])
    c.hline(cx - 1, oy, 3, C["orange_dark"])

    # --- Pale Blush-Pink Bonnet Dome ---
    c.hline(hx + 2, oy, 7, C["bonnet_pink"])
    c.hline(hx + 4, oy, 3, C["orange_dark"])
    c.rect(hx + 1, oy + 1, 9, 4, C["bonnet_pink"])
    c.rect(hx, oy + 3, 3, 5, C["bonnet_pink"])
    c.set(hx + 3, oy + 1, C["bonnet_dot"])
    c.set(hx + 7, oy + 1, C["bonnet_dot"])
    c.set(hx + 1, oy + 5, C["bonnet_dot"])
    # Scalloped lace ruffle
    for rx, ry in [(3, 2), (5, 2), (7, 2), (9, 2), (2, 3), (1, 4), (1, 6), (0, 7), (10, 3)]:
        c.set(hx + rx, oy + ry, C["bonnet_ruffle"])
    # Little golden ear on bonnet side
    c.rect(hx + 1, oy + 2, 2, 2, C["gold_main"])
    c.set(hx + 1, oy + 3, C["gold_dark"])

    if snow_on_bonnet:
        c.hline(hx + 2, oy, 6, C["white"])
        c.hline(hx + 3, oy + 1, 4, C["snow_bright"])

    # --- Round Golden Butter-Yellow Face ---
    c.hline(hx + 4, oy + 3, 6, C["gold_hi"])
    c.rect(hx + 3, oy + 4, 8, 5, C["gold_main"])
    c.hline(hx + 3, oy + 8, 8, C["gold_shade"])
    c.hline(hx + 4, oy + 9, 6, C["gold_shade"])
    c.vline(hx + 2, oy + 5, 3, C["gold_main"])
    c.set(hx + 2, oy + 7, C["gold_shade"])

    # Cheeks (flare bright red in spicy mode!)
    cheek_col = C["cheek_angry"] if mood == "spicy" else C["cheek_peach"]
    c.hline(hx + 4, oy + 7, 2, cheek_col)
    c.set(hx + 10, oy + 7, cheek_col)

    # --- Eyes & Expressions ---
    if sunglasses:
        c.hline(hx + 3, oy + 5, 8, C["shades_frame"])
        c.rect(hx + 3, oy + 5, 3, 2, C["shades_lens"])
        c.rect(hx + 7, oy + 5, 3, 2, C["shades_lens"])
        c.set(hx + 6, oy + 5, C["shades_frame"])
        if 0 <= glint_x <= 6:
            gx = hx + 3 + glint_x
            if hx + 3 <= gx <= hx + 5 or hx + 7 <= gx <= hx + 9:
                c.set(gx, oy + 5, C["shades_glint"])
    elif mood == "spicy":
        # Fierce adorable angled eyebrows + narrow eyes!
        c.set(hx + 4, oy + 4, C["mouth_line"])
        c.set(hx + 5, oy + 5, C["eye"])
        c.set(hx + 4, oy + 5, C["eye"])
        c.set(hx + 9, oy + 4, C["mouth_line"])
        c.set(hx + 8, oy + 5, C["eye"])
        c.set(hx + 9, oy + 5, C["eye"])
    elif mood == "delighted":
        # Joyful ^ ^ arched eyes!
        c.set(hx + 4, oy + 5, C["eye"])
        c.set(hx + 5, oy + 4, C["eye"])
        c.set(hx + 6, oy + 5, C["eye"])
        c.set(hx + 8, oy + 5, C["eye"])
        c.set(hx + 9, oy + 4, C["eye"])
        c.set(hx + 10, oy + 5, C["eye"])
    elif mood == "squint":
        c.hline(hx + 4, oy + 5, 2, C["eye"])
        c.hline(hx + 8, oy + 5, 2, C["eye"])
    elif mood == "blink":
        c.hline(hx + 4, oy + 6, 2, C["eye"])
        c.hline(hx + 8, oy + 6, 2, C["eye"])
    elif mood == "startled":
        c.rect(hx + 4, oy + 5, 2, 2, C["white"])
        c.set(hx + 5, oy + 6, C["eye"])
        c.rect(hx + 8, oy + 5, 2, 2, C["white"])
        c.set(hx + 9, oy + 6, C["eye"])
    else:
        c.rect(hx + 4, oy + 5, 2, 2, C["eye"])
        c.set(hx + 4, oy + 5, C["white"])
        c.set(hx + 4, oy + 6, C["white"])
        c.rect(hx + 8, oy + 5, 2, 2, C["eye"])
        c.set(hx + 8, oy + 5, C["white"])

    # --- Mouth ---
    if mood == "spicy":
        # Pouty inverted frown / huffy "o"
        c.hline(hx + 6, oy + 8, 3, C["smile_dark"])
        c.set(hx + 7, oy + 7, C["smile_dark"])
    elif mood == "startled":
        c.set(hx + 7, oy + 8, C["smile_dark"])
    else:
        c.hline(hx + 6, oy + 7, 2, C["smile_dark"])
        c.set(hx + 7, oy + 8, C["smile_tongue"])

    # --- Puffy Baby-Pink Bloomer Romper ---
    c.hline(bx + 3, oy + 10, 7, C["romper_hi"])
    c.rect(bx + 2, oy + 11, 9, 2, C["romper_main"])
    c.vline(bx + 2, oy + 11, 2, C["romper_shade"])
    c.rect(bx + 2, oy + 13, 9, 3, C["romper_main"])
    c.hline(bx + 3, oy + 13, 7, C["romper_hi"])
    c.vline(bx + 2, oy + 13, 3, C["romper_shade"])
    c.hline(bx + 2, oy + 15, 9, C["romper_shade"])
    c.hline(bx + 3, oy + 15, 3, C["bonnet_ruffle"])
    c.hline(bx + 7, oy + 15, 3, C["bonnet_ruffle"])

    # Paws (raised slightly if spicy or holding confiscated phone!)
    paw_y = oy + 10 if mood == "spicy" else oy + 11
    c.rect(bx + 6, paw_y, 4, 2, C["gold_main"])
    c.set(bx + 7, paw_y, C["gold_hi"])
    c.set(bx + 8, paw_y + 1, C["gold_shade"])

    if holding_phone:
        c.rect(bx + 9, oy + 9, 3, 3, C["phone_body"])
        c.vline(bx + 9, oy + 9, 3, C["phone_dark"])

    # --- Cozy Winter Scarf ---
    if scarf:
        c.hline(bx + 2, oy + 10, 9, C["scarf_teal"])
        c.set(bx + 4, oy + 10, C["scarf_mint"])
        c.set(bx + 7, oy + 10, C["scarf_mint"])
        c.rect(bx, oy + 11 + scarf_flutter, 2, 2, C["scarf_teal"])
        c.set(bx, oy + 12 + scarf_flutter, C["scarf_mint"])

    # --- Tiny Yellow Feet (animated walk cycle!) ---
    left_dy = -1 if walk_step == 1 else 0
    right_dy = -1 if walk_step == 2 else 0
    c.hline(bx + 3, oy + 16 + left_dy, 3, C["gold_main"])
    c.set(bx + 3, oy + 16 + left_dy, C["gold_shade"])
    c.hline(bx + 7, oy + 16 + right_dy, 3, C["gold_main"])
    c.set(bx + 7, oy + 16 + right_dy, C["gold_shade"])


def draw_lulu(
    c: Canvas,
    ox: int,
    oy: int,
    *,
    mood: str = "chill",  # "chill", "blink", "startled", "squint", "happy", "chomp", "dizzy"
    sunglasses: bool = False,
    glint_x: int = -1,
    scarf: bool = False,
    scarf_flutter: int = 0,
    lean_x: int = 0,
    orange_shift: int = 0,
    has_tangerine: bool = True,
    holding_phone: bool = False,
    phone_glow: bool = False,
    walk_step: int = 0,
    snow_on_head: bool = False,
) -> None:
    """
    Draw Lulu (~13w x 17h from tangerine to feet).
    Supports walking/tumble steps, phone scrolling, chomping, startled jump, and dizzy face.
    """
    hx = ox + lean_x
    bx = ox

    # --- Plump Tangerine with Tiny Green Stem ---
    if has_tangerine:
        draw_tangerine(c, hx + 5 + orange_shift, oy - 2)

    # --- Small Round Golden Ears ---
    c.rect(hx + 2, oy + 1, 2, 2, C["gold_main"])
    c.set(hx + 2, oy + 2, C["gold_dark"])
    c.rect(hx + 10, oy + 1, 2, 2, C["gold_main"])
    c.set(hx + 11, oy + 2, C["gold_dark"])

    # --- Pear-Shaped Chubby Golden Head ---
    c.hline(hx + 4, oy, 6, C["gold_hi"])
    c.hline(hx + 3, oy + 1, 8, C["gold_hi"])
    c.rect(hx + 2, oy + 2, 10, 3, C["gold_main"])
    c.vline(hx + 11, oy + 2, 3, C["gold_shade"])
    c.rect(hx + 1, oy + 5, 12, 4, C["gold_main"])
    c.vline(hx + 12, oy + 5, 4, C["gold_shade"])
    c.hline(hx + 2, oy + 9, 10, C["gold_shade"])

    if snow_on_head:
        c.hline(hx + 3, oy, 7, C["white"])
        c.hline(hx + 4, oy + 1, 5, C["snow_bright"])

    # Rounded warm peach-orange lower muzzle glow
    c.hline(hx + 3, oy + 5, 6, C["snout_hi"])
    c.hline(hx + 2, oy + 6, 8, C["snout_hi"])
    c.hline(hx + 2, oy + 7, 8, C["snout_main"])
    c.hline(hx + 3, oy + 8, 6, C["snout_main"])
    c.hline(hx + 4, oy + 9, 4, C["snout_shade"])

    # Mouth
    if mood == "chomp":
        c.rect(hx + 4, oy + 7, 3, 2, C["smile_dark"])
        c.set(hx + 5, oy + 8, C["smile_tongue"])
    elif mood == "startled":
        c.rect(hx + 5, oy + 7, 2, 2, C["smile_dark"])
    elif mood == "happy":
        c.hline(hx + 5, oy + 8, 2, C["mouth_line"])
        c.set(hx + 4, oy + 7, C["mouth_line"])
        c.set(hx + 7, oy + 7, C["mouth_line"])
    else:
        c.hline(hx + 5, oy + 8, 2, C["mouth_line"])

    # --- Eyes ---
    if sunglasses:
        c.hline(hx + 2, oy + 3, 9, C["shades_frame"])
        c.rect(hx + 2, oy + 3, 4, 2, C["shades_lens"])
        c.rect(hx + 7, oy + 3, 4, 2, C["shades_lens"])
        c.set(hx + 6, oy + 3, C["shades_frame"])
        if 0 <= glint_x <= 7:
            gx = hx + 2 + glint_x
            if hx + 2 <= gx <= hx + 5 or hx + 7 <= gx <= hx + 10:
                c.set(gx, oy + 3, C["shades_glint"])
    elif mood == "dizzy":
        c.set(hx + 3, oy + 3, C["eye"])
        c.set(hx + 4, oy + 4, C["eye"])
        c.set(hx + 7, oy + 4, C["eye"])
        c.set(hx + 8, oy + 3, C["eye"])
    elif mood == "happy":
        c.set(hx + 3, oy + 4, C["eye"])
        c.set(hx + 4, oy + 3, C["eye"])
        c.set(hx + 7, oy + 3, C["eye"])
        c.set(hx + 8, oy + 4, C["eye"])
    elif mood == "squint":
        c.hline(hx + 3, oy + 4, 2, C["eye"])
        c.hline(hx + 7, oy + 4, 2, C["eye"])
    elif mood == "blink":
        c.hline(hx + 3, oy + 4, 2, C["mouth_line"])
        c.hline(hx + 7, oy + 4, 2, C["mouth_line"])
    elif mood == "startled":
        c.rect(hx + 3, oy + 3, 2, 2, C["white"])
        c.set(hx + 3, oy + 4, C["eye"])
        c.rect(hx + 7, oy + 3, 2, 2, C["white"])
        c.set(hx + 7, oy + 4, C["eye"])
    else:
        # Iconic sleepy half-lidded eyes
        c.hline(hx + 3, oy + 3, 2, C["gold_shade"])
        c.hline(hx + 7, oy + 3, 2, C["gold_shade"])
        c.set(hx + 3, oy + 4, C["eye"])
        c.set(hx + 4, oy + 4, C["white"])
        c.set(hx + 7, oy + 4, C["eye"])
        c.set(hx + 8, oy + 4, C["white"])

    # --- Chubby Golden Torso ---
    c.rect(bx + 2, oy + 10, 10, 3, C["gold_main"])
    c.vline(bx + 11, oy + 10, 3, C["gold_shade"])
    c.hline(bx + 3, oy + 10, 7, C["gold_hi"])

    # --- Cozy Winter Scarf ---
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
    c.set(bx + 4, oy + 13, C["shorts_seed"])
    c.set(bx + 9, oy + 13, C["shorts_seed"])

    # --- Sitting / Walking Yellow Feet ---
    l_dy = -1 if walk_step == 1 else 0
    r_dy = -1 if walk_step == 2 else 0
    c.rect(bx + 1, oy + 14 + l_dy, 3, 2, C["gold_main"])
    c.set(bx + 1, oy + 15 + l_dy, C["gold_shade"])
    c.rect(bx + 8, oy + 14 + r_dy, 3, 2, C["gold_main"])
    c.set(bx + 10, oy + 15 + r_dy, C["gold_shade"])

    # --- Tiny Smartphone ---
    if holding_phone:
        c.rect(bx + 2, oy + 9, 3, 3, C["phone_body"])
        c.vline(bx + 2, oy + 9, 3, C["phone_dark"])
        if phone_glow:
            c.set(bx + 4, oy + 10, C["phone_glow"])
        c.rect(bx + 5, oy + 10, 3, 2, C["gold_hi"])
        c.set(bx + 5, oy + 11, C["gold_main"])


# ---------------------------------------------------------------------------
# 1. SUNNY: "Lulu Gobbles the Watermelon -> Spicy Lumei -> Off-Screen Peace Offering!"
# ---------------------------------------------------------------------------
def render_sunny_frame(f: int) -> Image.Image:
    c = Canvas()
    c.gradient_v((14, 38, 86, 255), (24, 68, 128, 255), 0, 28)
    c.hline(0, 28, WIDTH, C["grass_hi"])
    c.rect(0, 29, WIDTH, 3, C["grass_mid"])
    c.hline(0, 31, WIDTH, C["grass_dark"])

    # Seamless drifting cloud (1 full pass over 40px)
    cx = wrap_pos(3, 1, f, WIDTH, direction=1)
    for dx, dy in [(0, 1), (1, 0), (2, 0), (3, 0), (4, 1), (1, 1), (2, 1), (3, 1)]:
        c.set((cx + dx) % WIDTH, 4 + dy, (204, 224, 248, 255))

    # Spinning sun in top-right (period 10 -> 15 exact cycles)
    sx, sy = 34, 4
    c.hline(sx - 1, sy - 2, 3, C["sun_core"])
    c.rect(sx - 2, sy - 1, 5, 3, C["sun_core"])
    c.hline(sx - 1, sy + 2, 3, C["sun_core"])
    if (f // 5) % 2 == 0:
        for rx, ry in [(0, -3), (0, 3), (-3, 0), (3, 0), (-3, -2), (3, -2), (-3, 2), (3, 2)]:
            c.set(sx + rx, sy + ry, C["sun_ray"])
    else:
        for rx, ry in [(-1, -3), (1, 3), (-3, 1), (3, -1), (-2, -3), (2, -3), (-2, 3), (2, 3)]:
            c.set(sx + rx, sy + ry, C["sun_ray"])

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    glint_step = f % 50
    glint_x = glint_step if glint_step <= 7 else -1
    sprout_sway = 1 if (f % 30) < 15 else 0

    # Base home coordinates on 40px stage
    lumei_x, lumei_y = 3, 12 + bob_lumei
    lulu_x, lulu_y = 24, 13 + bob_lulu
    lumei_mood = "happy"
    lulu_mood = "chill"
    lumei_shades = True
    lulu_shades = True
    lumei_walk = 0
    lulu_walk = 0
    melon_x, melon_y = 16, 23
    melon_stage = 0
    show_melon = True

    if 24 <= f < 56:
        # Sneaky greedy Lulu slides over & gobbles the whole watermelon!
        lulu_shades = False
        if f < 34:
            lulu_x = lerp_i(24, 20, ease_in_out((f - 24) / 10))
            lulu_walk = 1 if (f % 4 < 2) else 2
        else:
            lulu_x = 20
        if 34 <= f < 44:
            lulu_mood = "chomp" if (f % 4 < 2) else "happy"
            melon_stage = 1
        elif 44 <= f < 56:
            lulu_mood = "chomp" if (f % 4 < 2) else "happy"
            melon_stage = 3  # eaten down to the green rind!
            # Flying watermelon crumbs
            dt = f - 44
            c.set(18 - dt // 4, 21 - dt // 3, C["melon_pink"])
            c.set(21 + dt // 5, 20 - dt // 4, C["melon_seed"])
    elif 56 <= f < 86:
        # SPICY LUMEI spots the empty rind and stomps indignantly!
        lumei_shades = False
        lulu_shades = False
        melon_stage = 3
        lumei_mood = "spicy"
        lumei_x = lerp_i(3, 7, ease_in_out((f - 56) / 10))
        lumei_y = 12 - (2 if (f % 6 < 3) else 0)  # angry hop stomp!
        lulu_x = lerp_i(20, 24, ease_in_out((f - 56) / 10))
        lulu_mood = "startled" if f < 68 else "chill"
    elif 86 <= f < 118:
        # Lulu casually walks OFF-SCREEN right and returns carrying a fresh watermelon!
        lumei_shades = False
        lulu_shades = False
        lumei_x = 7 if f < 104 else lerp_i(7, 3, ease_in_out((f - 104) / 14))
        lumei_mood = "spicy" if f < 106 else "startled"
        lulu_walk = 1 if (f % 4 < 2) else 2
        if f < 100:
            # Exits completely off the right edge (x = 42)
            lulu_x = lerp_i(24, 42, ease_in_out((f - 86) / 14))
            melon_stage = 3
        elif f < 104:
            # Briefly off-screen!
            lulu_x = 42
            show_melon = False
        else:
            # Marches back in from the right carrying a giant fresh watermelon!
            lulu_x = lerp_i(42, 24, ease_in_out((f - 104) / 14))
            lulu_mood = "happy"
            melon_x = lulu_x - 5
            melon_y = 19 + (f % 2)
            melon_stage = 0
    elif 118 <= f < 136:
        # Peace offering delivered -> Lumei instantly melts into hearts!
        lumei_shades = False
        lulu_shades = False
        lumei_mood = "delighted"
        lulu_mood = "happy"
        lumei_y = 12 - (1 if (f % 6 < 3) else 0)
        melon_x = lerp_i(19, 16, ease_in_out((f - 118) / 8))
        melon_y = lerp_i(19, 23, ease_in_out((f - 118) / 8))
        melon_stage = 0
    # f=136..149: Cool sunglasses back on, relaxing with fresh watermelon -> matches f=0!

    draw_lumei(
        c, lumei_x, lumei_y,
        mood=lumei_mood, sunglasses=lumei_shades, glint_x=glint_x,
        sprout_sway=sprout_sway, walk_step=lumei_walk,
    )
    draw_lulu(
        c, lulu_x, lulu_y,
        mood=lulu_mood, sunglasses=lulu_shades, glint_x=glint_x,
        walk_step=lulu_walk,
    )

    if show_melon:
        draw_watermelon(c, melon_x, melon_y, bite_stage=melon_stage)

    # Emote overlays
    if 58 <= f < 98:
        draw_anger_steam(c, lumei_x + 5, lumei_y - 4, f)
    elif 118 <= f < 134:
        rise = (f - 118) // 4
        draw_heart(c, 19, 12 - rise)

    return c.img


# ---------------------------------------------------------------------------
# 2. RAINY: "Lulu Hogs the Umbrella -> Spicy Lumei Yanks It Back!"
# ---------------------------------------------------------------------------
RAIN_DROPS_40 = [
    (2, 1, True), (7, 14, False), (11, 5, True), (16, 22, False),
    (20, 9, True), (25, 18, False), (29, 3, True), (34, 15, False),
    (38, 7, True), (4, 26, False), (9, 19, True), (14, 11, False),
    (18, 28, True), (23, 6, False), (27, 24, True), (32, 12, False),
    (36, 25, True), (1, 16, False), (13, 29, True), (22, 1, False),
    (31, 20, True), (39, 10, False),
]


def render_rainy_frame(f: int) -> Image.Image:
    c = Canvas()
    c.gradient_v((10, 16, 32, 255), (16, 28, 48, 255), 0, 29)

    # Drifting rain clouds (1 exact wrap over 40px)
    cx = wrap_pos(0, 1, f, WIDTH, direction=1)
    c.rect(0, 0, WIDTH, 2, C["cloud_dark"])
    for seg in range(0, WIDTH, 8):
        px = (cx + seg) % WIDTH
        for dx in range(6):
            c.set((px + dx) % WIDTH, 2, C["cloud_mid"])
        for dx in range(1, 5):
            c.set((px + dx) % WIDTH, 3, C["cloud_dark"])

    # Wet ground & animated puddle ripples (period 30 -> 5 cycles)
    c.rect(0, 29, WIDTH, 3, (18, 36, 62, 255))
    c.hline(0, 29, WIDTH, (30, 56, 92, 255))
    for rx, ph in [(4, 0), (20, 10), (35, 20)]:
        rip = (f + ph) % 30
        if rip < 10:
            c.hline(rx, 30, 2, C["rain_bright"])
        elif rip < 20:
            c.set(rx - 1, 30, C["rain_dim"])
            c.set(rx + 2, 30, C["rain_dim"])

    bob = bob_offset(f, period=30, phase=0)
    sprout_sway = 1 if (f % 30) < 15 else 0
    lumei_x, lumei_y = 6, 13 + bob
    lulu_x, lulu_y = 21, 14 + bob
    umb_cx = 19
    umb_y = 4 + bob
    lumei_mood = "blink" if (f % 50) in (12, 13) else "happy"
    lulu_mood = "blink" if (f % 50) in (34, 35) else "chill"
    lulu_phone = False
    lumei_walk = 0

    if 24 <= f < 56:
        # Oblivious Lulu pulls out his phone and drifts right with the umbrella!
        lulu_phone = True
        t = ease_in_out((f - 24) / 22)
        lulu_x = lerp_i(21, 26, t)
        umb_cx = lerp_i(19, 28, t)
        if f >= 42:
            lumei_mood = "startled"
            # Raindrop splashing right on Lumei's bonnet!
            if f % 4 < 2:
                c.set(lumei_x + 4, lumei_y - 3, C["rain_bright"])
                c.set(lumei_x + 7, lumei_y - 2, C["white"])
    elif 56 <= f < 86:
        # Soaked SPICY LUMEI marches over & yanks the umbrella back!
        lumei_mood = "spicy"
        if f < 68:
            lumei_x = lerp_i(6, 13, ease_in_out((f - 56) / 12))
            lumei_walk = 1 if (f % 4 < 2) else 2
            lulu_x = 26
            umb_cx = 28
            lulu_phone = True
        else:
            # YANK! Umbrella snaps back over Lumei; Lulu drops phone in surprise!
            lumei_x = lerp_i(13, 6, ease_in_out((f - 68) / 16))
            lumei_walk = 1 if (f % 4 < 2) else 2
            umb_cx = lerp_i(28, 13, ease_in_out((f - 68) / 12))
            lulu_x = lerp_i(26, 22, ease_in_out((f - 72) / 14))
            lulu_mood = "startled"
    elif 86 <= f < 126:
        # Sheepish Lulu scoots closer & shares the umbrella warmly -> hearts!
        umb_cx = lerp_i(13, 19, ease_in_out((f - 86) / 14))
        lulu_x = lerp_i(22, 19, ease_in_out((f - 86) / 14)) if f < 112 else lerp_i(19, 21, ease_in_out((f - 112) / 14))
        lumei_mood = "delighted" if f >= 96 else "happy"
        lulu_mood = "happy"
    # f=126..149: Cozy shared umbrella idle -> matches f=0!

    draw_lumei(
        c, lumei_x, lumei_y,
        mood=lumei_mood, sprout_sway=sprout_sway, walk_step=lumei_walk,
    )
    draw_lulu(
        c, lulu_x, lulu_y,
        mood=lulu_mood, holding_phone=lulu_phone, phone_glow=(f % 6 < 3),
    )
    draw_umbrella(c, umb_cx, umb_y, handle_h=16)

    if 56 <= f < 82:
        draw_anger_steam(c, lumei_x + 4, lumei_y - 4, f)
    elif 98 <= f < 120:
        draw_heart(c, 18, 12 - (f - 98) // 6)

    # Falling slanted raindrops (Ky=15, Kx=-5 exact modulo wrap over 40x32)
    for x0, y0, bright in RAIN_DROPS_40:
        rx = wrap_pos(x0, 5, f, WIDTH, direction=-1)
        ry = wrap_pos(y0, 15, f, HEIGHT, direction=1)
        if (umb_cx - 12) <= rx <= (umb_cx + 12) and ry >= umb_y + 3:
            continue
        col = C["rain_bright"] if bright else C["rain_dim"]
        c.set(rx, ry, col)
        if (umb_cx - 11) <= rx <= (umb_cx + 11) and umb_y <= ry <= umb_y + 2:
            c.set(rx, umb_y - 1, C["white"])
        else:
            c.set((rx + 1) % WIDTH, (ry - 1) % HEIGHT, C["rain_dim"])

    return c.img


# ---------------------------------------------------------------------------
# 3. SNOWY: "Playful Lulu Starts a Snowball Fight -> Giant Revenge Snowball!"
# ---------------------------------------------------------------------------
SNOW_FLAKES_40 = [
    (2, 2, 0.0, True), (7, 15, 1.1, False), (12, 7, 2.2, False), (17, 23, 0.7, True),
    (22, 4, 3.1, False), (27, 19, 1.9, False), (32, 11, 4.0, True), (37, 26, 2.5, False),
    (5, 27, 1.4, False), (10, 19, 5.0, False), (15, 1, 3.7, True), (20, 14, 0.3, False),
    (25, 28, 2.9, False), (30, 6, 4.5, False), (35, 17, 1.6, True), (39, 9, 5.4, False),
    (1, 12, 2.1, False), (14, 26, 3.3, False), (24, 10, 0.9, False), (34, 2, 4.8, False),
]


def render_snowy_frame(f: int) -> Image.Image:
    c = Canvas()
    c.gradient_v((8, 16, 36, 255), (16, 30, 58, 255), 0, 28)

    # Snowy hills
    c.rect(0, 28, WIDTH, 4, C["snow_ground"])
    c.hline(0, 28, WIDTH, C["white"])
    c.hline(0, 30, WIDTH, C["snow_shadow"])
    c.hline(0, 31, WIDTH, C["snow_shadow"])
    c.hline(2, 27, 11, C["snow_ground"])
    c.hline(24, 27, 13, C["snow_ground"])

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    flutter = 1 if (f % 30) >= 15 else 0
    sprout_sway = 1 if (f % 30) < 15 else 0

    lumei_x, lumei_y = 3, 12 + bob_lumei
    lulu_x, lulu_y = 24, 13 + bob_lulu
    lumei_mood = "blink" if (f % 50) in (10, 11) else "happy"
    lulu_mood = "blink" if (f % 50) in (36, 37) else "chill"
    lulu_walk = 0
    lumei_snow = False
    lulu_snow = False

    if 24 <= f < 46:
        # Mischievous Lulu packs & throws a snowball at Lumei!
        lulu_mood = "happy"
        if f < 32:
            # Lulu dips down to pack snowball
            lulu_y = 14
        elif f < 44:
            t = (f - 32) / 12.0
            sb_x = lerp_i(24, 9, t)
            sb_y = int(round(18 - 6 * math.sin(math.pi * t)))
            c.rect(sb_x, sb_y, 2, 2, C["white"])
            c.set(sb_x + 1, sb_y + 1, C["snow_mid"])
        else:
            # SPLAT on Lumei's bonnet!
            lumei_snow = True
            lumei_mood = "startled"
            for dx, dy in [(-2, -1), (2, -2), (-1, 2), (3, 1)]:
                c.set(8 + dx, 12 + dy, C["white"])
    elif 46 <= f < 66:
        # Lumei gets SPICY, shakes off snow, and rolls a GIANT snowball!
        lumei_snow = f < 52
        lumei_mood = "spicy"
        lumei_y = 12 - (1 if (f % 4 < 2) else 0)
        lulu_mood = "startled" if f >= 56 else "happy"
        if f >= 54:
            # Growing giant snowball in front of Lumei!
            c.rect(12, 20, 4, 4, C["white"])
            c.hline(13, 20, 2, C["snow_bright"])
            c.hline(12, 23, 4, C["snow_mid"])
    elif 66 <= f < 98:
        # Giant snowball flies -> Lulu tries to waddle OFF-SCREEN right & gets BONKED!
        lumei_mood = "spicy" if f < 80 else "delighted"
        lulu_mood = "startled"
        lulu_walk = 1 if (f % 4 < 2) else 2
        if f < 82:
            # Lulu flees right toward/past the edge while giant snowball arcs over!
            lulu_x = lerp_i(24, 33, ease_in_out((f - 66) / 16))
            t = (f - 66) / 16.0
            sb_x = lerp_i(13, 33, t)
            sb_y = int(round(19 - 8 * math.sin(math.pi * t)))
            c.rect(sb_x, sb_y, 4, 4, C["white"])
            c.hline(sb_x, sb_y + 3, 4, C["snow_mid"])
        else:
            # POOF! Giant snow explosion on Lulu, who waddles back covered in snow!
            lulu_x = lerp_i(33, 24, ease_in_out((f - 82) / 16))
            lulu_snow = True
            if f < 88:
                for dx, dy in [(-3, -2), (4, -3), (-2, 3), (5, 2), (1, -4)]:
                    c.set(lulu_x + 5 + dx, 14 + dy, C["white"])
    elif 98 <= f < 126:
        # Both laugh and hop together in snowy truce!
        lulu_snow = f < 114
        lumei_mood = "delighted"
        lulu_mood = "happy"
        lumei_y = 12 - (2 if (f % 8 < 4) else 0)
        lulu_y = 13 - (1 if ((f + 4) % 8 < 4) else 0)
    # f=126..149: Calm snowy bobbing -> matches f=0!

    draw_lumei(
        c, lumei_x, lumei_y,
        mood=lumei_mood, scarf=True, scarf_flutter=flutter,
        sprout_sway=sprout_sway, snow_on_bonnet=lumei_snow,
    )
    draw_lulu(
        c, lulu_x, lulu_y,
        mood=lulu_mood, scarf=True, scarf_flutter=1 - flutter,
        walk_step=lulu_walk, snow_on_head=lulu_snow,
    )

    if 48 <= f < 66:
        draw_anger_steam(c, lumei_x + 4, lumei_y - 4, f)
    elif 100 <= f < 120:
        draw_heart(c, 19, 12 - (f - 100) // 5)

    # Gentle falling snowflakes (Ky=3 exact wrap + 5-cycle sine sway)
    for x0, y0, phase, is_big in SNOW_FLAKES_40:
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


# ---------------------------------------------------------------------------
# 4. WINDY: "MEGA GUST Blows Lulu OFF-SCREEN -> Lumei Rescues Him!"
# ---------------------------------------------------------------------------
WIND_LEAVES_40 = [
    (2, 4, 0.0, "leaf_orange"), (9, 12, 1.3, "leaf_gold"),
    (16, 7, 2.4, "leaf_red"), (23, 18, 0.8, "leaf_orange"),
    (30, 9, 3.6, "leaf_sage"), (37, 21, 4.8, "leaf_gold"),
    (5, 22, 1.9, "leaf_red"), (12, 26, 5.2, "leaf_orange"),
    (20, 2, 2.9, "leaf_gold"), (26, 24, 4.1, "leaf_sage"),
    (34, 15, 0.5, "leaf_red"), (1, 16, 3.1, "leaf_orange"),
    (14, 14, 1.7, "leaf_gold"), (38, 6, 4.4, "leaf_sage"),
]


def render_windy_frame(f: int) -> Image.Image:
    c = Canvas()
    c.gradient_v((10, 24, 36, 255), (18, 42, 56, 255), 0, 28)

    c.hline(0, 28, WIDTH, C["grass_hi"])
    c.rect(0, 29, WIDTH, 3, C["grass_mid"])
    c.hline(0, 31, WIDTH, C["grass_dark"])

    # Fast horizontal gust streaks wrapping seamlessly (Kx=15 over 40px)
    gust_heavy = 22 <= f <= 74
    for row_y, offset, length in [(4, 0, 9), (10, 14, 11), (17, 26, 8), (24, 7, 10)]:
        wx = wrap_pos(offset, 15, f, WIDTH, direction=1)
        extra = 3 if gust_heavy else 0
        for dx in range(length + extra):
            col = C["wind_streak"] if dx >= length - 3 else C["wind_dim"]
            c.set((wx + dx) % WIDTH, row_y, col)

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=10)

    lumei_x, lumei_y = 3, 12 + bob_lumei
    lulu_x, lulu_y = 24, 13 + bob_lulu
    lumei_mood = "squint"
    lulu_mood = "squint"
    lumei_lean = 1
    lulu_lean = 1
    lumei_walk = 0
    lulu_walk = 0
    lulu_has_tang = True
    loose_tang: Optional[Tuple[int, int]] = None
    orange_jiggle = 1 if (f % 15) < 7 else 0

    if 24 <= f < 46:
        # MEGA GUST! Lulu's tangerine pops off & Lulu blows completely OFF-SCREEN right!
        lulu_has_tang = False
        t = ease_in_out((f - 24) / 22)
        lulu_x = lerp_i(24, 44, t)  # flies completely past x=40!
        lulu_y = 13 - int(round(5 * math.sin(math.pi * t)))
        lulu_mood = "startled" if f < 34 else "dizzy"
        lulu_walk = 1 if (f % 4 < 2) else 2
        # Tangerine zips off ahead of him
        tx = lerp_i(29, 46, ease_in_out((f - 24) / 14))
        ty = 11 - int(round(4 * math.sin(math.pi * min(1.0, (f - 24) / 14))))
        loose_tang = (tx, ty)
        lumei_mood = "startled"
        lumei_x = lerp_i(3, 6, ease_in_out((f - 24) / 22))
    elif 46 <= f < 64:
        # Lumei gasps ("!") then sprints OFF-SCREEN right to rescue him!
        lulu_x = 46  # off-screen
        lulu_has_tang = False
        if f < 52:
            lumei_x = 6
            lumei_mood = "startled"
            draw_exclaim(c, lumei_x + 5, lumei_y - 6)
        else:
            t = ease_in_out((f - 52) / 12)
            lumei_x = lerp_i(6, 44, t)  # sprints completely off-screen right!
            lumei_mood = "spicy"
            lumei_walk = 1 if (f % 4 < 2) else 2
    elif 64 <= f < 76:
        # Comedic beat: EMPTY STAGE while leaves & wind whip across!
        lumei_x = 46
        lulu_x = 46
        lulu_has_tang = False
    elif 76 <= f < 114:
        # Heroic return! Spicy Lumei marches back from right dragging dizzy Lulu!
        t = ease_in_out((f - 76) / 36)
        lumei_x = lerp_i(42, 3, t)
        lulu_x = lerp_i(56, 24, t)
        lumei_mood = "spicy"
        lulu_mood = "dizzy" if f < 104 else "chill"
        lumei_lean = 0
        lulu_lean = 0
        lumei_walk = 1 if (f % 4 < 2) else 2
        lulu_walk = 2 if (f % 4 < 2) else 1
        lulu_has_tang = f >= 106
        if not lulu_has_tang:
            # Rolling tangerine bounces back right behind Lulu!
            rt = ease_in_out(max(0.0, (f - 86) / 20))
            loose_tang = (lerp_i(44, 29, rt), lerp_i(25, 11, rt) - int(round(3 * math.sin(math.pi * rt))))
    elif 114 <= f < 134:
        # Lumei huffs with a cute angry puff; dizzy Lulu blinks unbothered with tangerine restored!
        lumei_mood = "spicy"
        lulu_mood = "blink" if f < 122 else "chill"
        lumei_lean = 0
        lulu_lean = 0
        draw_anger_steam(c, lumei_x + 5, lumei_y - 4, f)
    # f=134..149: Both settle back into leaning into the wind -> exact match to f=0!

    draw_lumei(
        c, lumei_x, lumei_y,
        mood=lumei_mood, lean_x=lumei_lean, sprout_sway=1, walk_step=lumei_walk,
    )
    draw_lulu(
        c, lulu_x, lulu_y,
        mood=lulu_mood, lean_x=lulu_lean, orange_shift=orange_jiggle,
        has_tangerine=lulu_has_tang, walk_step=lulu_walk,
    )
    if loose_tang is not None:
        draw_tangerine(c, loose_tang[0], loose_tang[1])

    # Swirling autumn leaves (Kx=10, Ky=3, sine swirl cycles=5 -> exact seamless wrap!)
    spin = (f // 3) % 2
    for x0, y0, phase, col_key in WIND_LEAVES_40:
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


# ---------------------------------------------------------------------------
# 5. THUNDERSTORM: "Overconfident Lulu Gets Spooked & Dives Under Blanket!"
# ---------------------------------------------------------------------------
def render_thunderstorm_frame(f: int) -> Image.Image:
    flash_1 = f in (30, 31, 34)
    flash_2 = f in (80, 81, 84)
    is_flashing = flash_1 or flash_2
    shiver_1 = 30 <= f <= 44
    shiver_2 = 80 <= f <= 94

    c = Canvas()
    if is_flashing:
        c.gradient_v((64, 78, 114, 255), (36, 48, 78, 255), 0, 29)
    else:
        c.gradient_v((6, 9, 20, 255), (14, 20, 38, 255), 0, 29)

    c.rect(0, 29, WIDTH, 3, (12, 18, 32, 255))

    # Rumbling storm clouds (1 exact pass over 40px)
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

    # Jagged lightning strikes
    if flash_1:
        for bx, by in [(31, 4), (30, 5), (29, 6), (30, 7), (31, 8), (30, 9), (29, 10), (28, 11), (29, 12)]:
            c.set(bx - 1, by, C["bolt_glow"])
            c.set(bx + 1, by, C["bolt_glow"])
            c.set(bx, by, C["bolt_core"])
    elif flash_2:
        for bx, by in [(9, 4), (10, 5), (11, 6), (10, 7), (9, 8), (10, 9), (11, 10), (10, 11)]:
            c.set(bx - 1, by, C["bolt_glow"])
            c.set(bx + 1, by, C["bolt_glow"])
            c.set(bx, by, C["bolt_core"])

    # Heavy slanted rain (Ky=15, Kx=-5 exact modulo wrap)
    for x0, y0, bright in RAIN_DROPS_40:
        rx = wrap_pos(x0, 5, f, WIDTH, direction=-1)
        ry = wrap_pos(y0, 15, f, HEIGHT, direction=1)
        col = C["rain_bright"] if (bright or is_flashing) else C["rain_dim"]
        c.set(rx, ry, col)
        c.set((rx + 1) % WIDTH, (ry - 1) % HEIGHT, C["rain_dim"])

    bob = bob_offset(f, period=30, phase=0)
    shiver = (1 if (f % 2 == 0) else 0) if (shiver_1 or shiver_2) else 0

    # Lumei stays tucked on the left; overconfident Lulu starts OUTSIDE blanket on the right!
    lumei_x, lumei_y = 4 + shiver, 13 + (1 if (shiver_1 or shiver_2) else bob)
    lumei_mood = "startled" if (shiver_1 or shiver_2) else ("blink" if (f % 50) in (14, 15) else "happy")

    lulu_x, lulu_y = 25, 13 + bob
    lulu_mood = "chill"
    lulu_under_blanket = False
    blanket_w = 15  # starts draped over Lumei only; expands to 28 when Lulu dives in!
    orange_pop = 0

    if 30 <= f < 46:
        # CRACK!! Lulu leaps sky-high in terror and dives straight under the blanket!
        lulu_mood = "startled"
        t = (f - 30) / 16.0
        lulu_x = lerp_i(25, 17, ease_in_out(t))
        lulu_y = 13 - int(round(5 * math.sin(math.pi * t)))
        orange_pop = -2 if f < 38 else 0
        lulu_under_blanket = f >= 40
        blanket_w = lerp_i(15, 28, ease_in_out(max(0.0, (f - 36) / 8)))
    elif 46 <= f < 104:
        # Both huddled tightly under the starry purple blanket!
        lulu_under_blanket = True
        blanket_w = 28
        lulu_x = 17 + shiver
        lulu_y = 14 + (1 if shiver_2 else bob)
        lulu_mood = "startled" if shiver_2 else "squint"
        if 56 <= f < 74:
            # Lumei comforts Lulu with a sweet heart!
            lumei_mood = "delighted"
            draw_heart(c, 16, 11 - (f - 56) // 6)
    elif 104 <= f < 130:
        # Lulu slowly scoots back outside trying to act "totally brave & unbothered" again!
        t = ease_in_out((f - 104) / 24)
        lulu_x = lerp_i(17, 25, t)
        blanket_w = lerp_i(28, 15, t)
        lulu_under_blanket = f < 114
        lulu_mood = "chill"
        lumei_mood = "delighted" if f < 122 else "happy"
    # f=130..149: Resting pose matching f=0!

    draw_lumei(c, lumei_x, lumei_y, mood=lumei_mood)
    draw_lulu(
        c, lulu_x, lulu_y + orange_pop,
        mood=lulu_mood,
        has_tangerine=True,
    )

    # Cozy starry purple blanket (drapes over Lumei, expands to cover Lulu too!)
    top_y = lumei_y + 9
    bx0 = 3 + shiver
    c.hline(bx0 + 1, top_y, max(4, blanket_w - 2), C["blanket_hi"])
    c.rect(bx0, top_y + 1, blanket_w, max(1, 29 - (top_y + 1)), C["blanket_main"])
    c.vline(bx0, top_y + 1, max(1, 29 - (top_y + 1)), C["blanket_dark"])
    c.vline(bx0 + blanket_w - 1, top_y + 1, max(1, 29 - (top_y + 1)), C["blanket_dark"])
    c.hline(bx0, 28, blanket_w, C["blanket_dark"])
    for sx, sy in [(bx0 + 4, top_y + 2), (bx0 + 10, top_y + 4), (bx0 + 18, top_y + 2), (bx0 + 23, top_y + 4)]:
        if sx < bx0 + blanket_w - 1 and sy < 28:
            c.set(sx, sy, C["blanket_star"])

    # If Lulu isn't under the blanket, re-draw him on top of the right edge cleanly
    if not lulu_under_blanket:
        draw_lulu(c, lulu_x, lulu_y + orange_pop, mood=lulu_mood)

    return c.img


# ---------------------------------------------------------------------------
# 6. DEFAULT: "Starry Night Phone-Snatch Gag (Exact Reference Photo Dynamic!)"
# ---------------------------------------------------------------------------
def render_default_frame(f: int) -> Image.Image:
    c = Canvas()
    c.gradient_v((7, 12, 28, 255), (14, 24, 48, 255), 0, 28)

    c.hline(0, 28, WIDTH, C["grass_hi"])
    c.rect(0, 29, WIDTH, 3, C["grass_mid"])
    c.hline(0, 31, WIDTH, C["grass_dark"])

    # Twinkling stars (periods 30 and 50 -> exact divisors of 150)
    stars = [
        (3, 3, 30, 0), (11, 2, 50, 10), (19, 4, 30, 15),
        (27, 3, 50, 25), (37, 8, 30, 7), (15, 7, 50, 35), (6, 8, 30, 20),
    ]
    for sx, sy, per, ph in stars:
        col = C["star_bright"] if ((f + ph) % per) < per // 2 else C["star_dim"]
        c.set(sx, sy, col)

    # Crescent moon in top-right
    mx, my = 33, 2
    for dx, dy in [(1, 0), (2, 0), (0, 1), (1, 1), (0, 2), (1, 2), (1, 3), (2, 3)]:
        c.set(mx + dx, my + dy, C["moon"])

    # Drifting wispy night cloud (1 exact pass over 40px)
    cx = wrap_pos(2, 1, f, WIDTH, direction=1)
    for dx, dy in [(0, 1), (1, 0), (2, 0), (3, 0), (4, 1), (1, 1), (2, 1), (3, 1)]:
        c.set((cx + dx) % WIDTH, 5 + dy, (42, 60, 96, 255))

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    sprout_sway = 1 if (f % 30) < 15 else 0
    phone_glow = (f % 10) < 5

    lumei_x, lumei_y = 3, 12 + bob_lumei
    lulu_x, lulu_y = 24, 13 + bob_lulu
    lumei_mood = "blink" if (f % 50) in (12, 13) else "happy"
    lulu_mood = "blink" if (f % 50) in (34, 35) else "chill"
    lulu_phone = True
    lumei_phone = False
    lumei_walk = 0

    if 24 <= f < 50:
        # Lumei hops enthusiastically trying to get phone-glued Lulu's attention!
        lumei_y = 12 - (2 if (f % 8 < 4) else 0)
        lumei_mood = "happy"
    elif 50 <= f < 82:
        # SPICY LUMEI marches over and SNATCHES Lulu's phone away!
        lumei_mood = "spicy"
        if f < 66:
            lumei_x = lerp_i(3, 14, ease_in_out((f - 50) / 16))
            lumei_walk = 1 if (f % 4 < 2) else 2
        else:
            # Snatched!!
            lumei_x = 14
            lulu_phone = False
            lumei_phone = True
            lulu_mood = "startled"
            if f < 74:
                draw_exclaim(c, lulu_x + 6, lulu_y - 6)
    elif 82 <= f < 114:
        # Lulu breaks into a sweet smile & leans over to nuzzle Lumei -> twin hearts!
        lulu_phone = False
        lumei_phone = True
        lumei_x = 14
        lulu_x = lerp_i(24, 21, ease_in_out((f - 82) / 10)) if f < 104 else lerp_i(21, 24, ease_in_out((f - 104) / 10))
        lumei_mood = "delighted"
        lulu_mood = "happy"
        if 88 <= f < 112:
            rise = (f - 88) // 6
            draw_heart(c, 19, 11 - rise)
            if f >= 94:
                draw_heart(c, 14, 10 - (f - 94) // 6)
    elif 114 <= f < 134:
        # Lumei hands the phone back and skips happily back to her left spot!
        lulu_phone = True
        lumei_phone = False
        lumei_x = lerp_i(14, 3, ease_in_out((f - 114) / 18))
        lumei_y = 12 - (1 if (f % 6 < 3) else 0)
        lumei_walk = 1 if (f % 4 < 2) else 2
        lumei_mood = "happy"
        lulu_mood = "happy" if f < 126 else "chill"
    # f=134..149: Back to starry-night cozy idle -> matches f=0!

    draw_lumei(
        c, lumei_x, lumei_y,
        mood=lumei_mood, sprout_sway=sprout_sway,
        walk_step=lumei_walk, holding_phone=lumei_phone,
    )
    draw_lulu(
        c, lulu_x, lulu_y,
        mood=lulu_mood, holding_phone=lulu_phone, phone_glow=phone_glow,
    )

    if 50 <= f < 72:
        draw_anger_steam(c, lumei_x + 4, lumei_y - 4, f)

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
            tile_w = WIDTH
            tile_h = sheet.height
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
    """Ensure Pillow emits exact 150 uniform 100ms frames (never collapses holds)."""
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
    f0 = renderer(0)
    f_wrap = renderer(NUM_FRAMES)
    if f0.tobytes() != f_wrap.tobytes():
        raise AssertionError(
            f"Seamless loop violation in '{state}': renderer(0) != renderer({NUM_FRAMES})!"
        )


def build_contact_sheet(state_frames: Dict[str, List[Image.Image]], scale: int = 5) -> Path:
    """Create an upscaled storyboard strip showing key beats of all 6 states."""
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    sample_indices = [0, 34, 60, 70, 96, 120]
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
        f"SPRITE_WIDTH = {WIDTH}",
        f"SPRITE_HEIGHT = {HEIGHT}",
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
    print(f"Injected {len(b64_map)} base64-encoded {WIDTH}x{HEIGHT} animated GIFs into {star_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate 15-second seamless 40x32 sprites for Capybara Clock."
    )
    parser.add_argument("--no-inject", action="store_true")
    parser.add_argument("--preview", action="store_true")
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

        assert len(frames) == NUM_FRAMES
        all_frames[state] = frames

        gif_bytes = encode_animated_gif(frames)
        (ASSETS_DIR / f"{state}.gif").write_bytes(gif_bytes)

        webp_size = save_animated_webp(frames, ASSETS_DIR / f"{state}.webp")
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
