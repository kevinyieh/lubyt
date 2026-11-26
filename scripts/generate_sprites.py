#!/usr/bin/env python3
"""
Procedural Pixel-Art Sprite Generator & Custom Frame Importer
for the Tidbyt Weather-Reactive Capybara Clock (Lumei & Lulu).

Generates 24 full-screen 64x32 animated GIF & WebP storyboards —
a distinct DAY and NIGHT version for EVERY Open-Meteo weather condition:
  1. clear             (day: Watermelon Heist | night: Telescope Stargazing & Shooting Stars!)
  2. partly_cloudy     (day & night: Checkered Picnic — Lumei eats all the food, makes Lulu
                        sad, rushes off-screen & returns with a giant frosted cake!)
  3. overcast          (day & night: Sleepy Overcast Zzz & Cozy Wake-Up)
  4. fog               (day & night: Lost in the Fog — off-screen hide & seek + night lantern!)
  5. drizzle           (day & night: Puddle-Splash Shenanigans)
  6. freezing_rain     (day & night: Slippery Ice Wipeout — off-screen belly slide!)
  7. rain              (day & night: Umbrella Tug-of-War)
  8. rain_showers      (day: Cloudburst & Vivid Rainbow | night: Night Shower & Silvery Moonbow!)
  9. snow              (day & night: Escalating Snowball Fight — off-screen chase!)
 10. thunderstorm      (day & night: Overconfident Lulu Leaps Under the Blanket)
 11. thunderstorm_hail (day & night: Bouncing Hailstone Shield Scramble)
 12. windy             (day & night: Mega Gust Blows Lulu Off-Screen & Lumei Rescues Him!)

Loop Timing & Seamlessness Contract:
  - Canvas:       64 x 32 px (with top-left x=0..19, y=0..11 clear for minimal Time+Temp HUD)
  - Frame count:  150 frames @ 100 ms = 15.0 seconds, loop=0
  - Bit-for-bit seamless verified: renderer(0) == renderer(150) for every single state.
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
# Core Animation Timing & Full-Screen Canvas Constants
# ---------------------------------------------------------------------------
WIDTH = 64
HEIGHT = 32
NUM_FRAMES = 150
FRAME_DELAY_MS = 100  # 150 * 100 ms = 15,000 ms (15.0s at 10 FPS)
TOTAL_DURATION_MS = NUM_FRAMES * FRAME_DELAY_MS

WEATHER_TYPES = (
    "clear",
    "partly_cloudy",
    "overcast",
    "fog",
    "drizzle",
    "freezing_rain",
    "rain",
    "rain_showers",
    "snow",
    "thunderstorm",
    "thunderstorm_hail",
    "windy",
)

STATES = tuple(f"{w}_{tod}" for w in WEATHER_TYPES for tod in ("day", "night"))

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
CUSTOM_DIR = ASSETS_DIR / "custom"
PREVIEWS_DIR = ASSETS_DIR / "previews"
STAR_FILE = ROOT_DIR / "capybara_clock.star"

SPRITE_BEGIN_MARKER = "# --- BEGIN GENERATED SPRITES (DO NOT EDIT MANUALLY) ---"
SPRITE_END_MARKER = "# --- END GENERATED SPRITES ---"

RGBA = Tuple[int, int, int, int]

# ---------------------------------------------------------------------------
# Palette (tuned for vibrant LED contrast across both Day & Night skies)
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
    "tear_blue": (110, 206, 255, 255),
    "gloom_blue": (72, 134, 212, 255),
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
    # Sun, moon, clouds, lantern & fog
    "sun_core": (255, 224, 64, 255),
    "sun_ray": (255, 158, 28, 255),
    "moon": (255, 238, 158, 255),
    "star_bright": (255, 248, 208, 255),
    "star_dim": (138, 162, 204, 255),
    "wish_gold": (255, 224, 102, 255),
    "lantern_core": (255, 236, 136, 255),
    "lantern_glow": (255, 186, 62, 100),
    "lantern_frame": (118, 74, 42, 255),
    "scope_brass": (236, 184, 52, 255),
    "scope_hi": (255, 226, 118, 255),
    "scope_dark": (132, 92, 34, 255),
    "tripod": (84, 96, 122, 255),
    "cloud_white": (228, 238, 250, 255),
    "cloud_light": (176, 198, 222, 255),
    "cloud_gray": (118, 132, 154, 255),
    "cloud_mid": (66, 80, 106, 255),
    "cloud_dark": (34, 44, 66, 255),
    "cloud_night": (24, 32, 54, 255),
    "fog_day_hi": (214, 226, 236, 155),
    "fog_day_mid": (172, 190, 206, 130),
    "fog_night_hi": (122, 146, 174, 140),
    "fog_night_mid": (82, 104, 132, 120),
    # Picnic & snacks
    "picnic_red": (228, 62, 74, 255),
    "picnic_white": (248, 242, 236, 255),
    "basket_main": (196, 136, 72, 255),
    "basket_dark": (138, 86, 38, 255),
    "plate": (224, 232, 242, 255),
    "cake_sponge": (252, 214, 142, 255),
    "cake_cream": (255, 246, 248, 255),
    "cake_pink": (255, 132, 168, 255),
    "cherry": (236, 36, 56, 255),
    # Sunglasses & watermelon
    "shades_frame": (20, 24, 38, 255),
    "shades_lens": (42, 58, 96, 255),
    "shades_glint": (190, 232, 255, 255),
    "melon_rind": (44, 192, 82, 255),
    "melon_pith": (235, 248, 235, 255),
    "melon_pink": (255, 72, 104, 255),
    "melon_seed": (32, 22, 26, 255),
    # Rain, umbrella, puddle, ice, hail
    "umb_blue": (46, 120, 242, 255),
    "umb_light": (118, 178, 255, 255),
    "umb_dark": (24, 72, 172, 255),
    "umb_handle": (162, 104, 58, 255),
    "shield_hi": (212, 232, 252, 255),
    "shield_mid": (132, 164, 202, 255),
    "shield_dark": (78, 106, 144, 255),
    "rain_bright": (146, 208, 255, 255),
    "rain_dim": (68, 134, 216, 255),
    "ice_hi": (222, 248, 255, 255),
    "ice_mid": (138, 216, 246, 255),
    "ice_dark": (74, 156, 204, 255),
    "hail_core": (248, 252, 255, 255),
    "hail_rim": (152, 216, 255, 255),
    # Snow & scarves
    "snow_bright": (242, 248, 255, 255),
    "snow_mid": (176, 212, 244, 255),
    "snow_ground": (214, 232, 248, 255),
    "snow_shadow": (142, 176, 214, 255),
    "snow_night_ground": (156, 184, 216, 255),
    "snow_night_shadow": (98, 128, 166, 255),
    "scarf_red": (236, 56, 68, 255),
    "scarf_gold": (255, 208, 72, 255),
    "scarf_teal": (44, 204, 196, 255),
    "scarf_mint": (186, 248, 242, 255),
    # Windy
    "wind_streak": (132, 204, 224, 255),
    "wind_dim": (68, 120, 146, 255),
    "leaf_orange": (250, 122, 34, 255),
    "leaf_gold": (252, 204, 44, 255),
    "leaf_red": (234, 66, 66, 255),
    "leaf_sage": (132, 206, 68, 255),
    # Thunderstorm & blanket
    "bolt_core": (255, 255, 230, 255),
    "bolt_glow": (255, 224, 72, 255),
    "blanket_main": (124, 72, 216, 255),
    "blanket_hi": (168, 126, 246, 255),
    "blanket_dark": (78, 42, 148, 255),
    "blanket_star": (255, 224, 118, 255),
    # Ground & accents
    "grass_day_hi": (84, 158, 86, 255),
    "grass_day_mid": (52, 114, 66, 255),
    "grass_day_dark": (32, 76, 48, 255),
    "grass_night_hi": (36, 74, 58, 255),
    "grass_night_mid": (24, 52, 42, 255),
    "grass_night_dark": (14, 34, 30, 255),
    "puddle_day": (58, 124, 192, 255),
    "puddle_night": (30, 66, 116, 255),
    "puddle_hi": (134, 202, 252, 255),
    "heart": (255, 108, 148, 255),
    "zzz": (176, 214, 255, 255),
}

RAINBOW_DAY = [
    (255, 68, 78, 255), (255, 158, 44, 255), (255, 232, 74, 255),
    (74, 214, 108, 255), (76, 168, 255, 255), (168, 108, 255, 255),
]
# Subtle silvery-pastel moonbow for night showers!
RAINBOW_NIGHT = [
    (168, 122, 168, 255), (146, 164, 214, 255), (156, 212, 238, 255),
    (196, 232, 248, 255), (138, 178, 224, 255), (118, 136, 192, 255),
]


# ---------------------------------------------------------------------------
# Low-level Pixel Drawing Helpers
# ---------------------------------------------------------------------------
class Canvas:
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

    def gradient_v(self, top: RGBA, bottom: RGBA, y0: int = 0, y1: int = HEIGHT, bands: int = 4) -> None:
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
    assert NUM_FRAMES % period == 0
    return 1 if ((frame + phase) % period) >= period // 2 else 0


def wrap_pos(start: int, cycles: int, frame: int, size: int = WIDTH, direction: int = 1) -> int:
    delta = (cycles * size * frame) // NUM_FRAMES
    return (start + direction * delta) % size


def lerp_i(a: float, b: float, t: float) -> int:
    t_c = max(0.0, min(1.0, t))
    return int(round(a + (b - a) * t_c))


def ease_in_out(t: float) -> float:
    t_c = max(0.0, min(1.0, t))
    return 0.5 - 0.5 * math.cos(math.pi * t_c)


# ---------------------------------------------------------------------------
# Scenic, Day/Night Sky, & Prop Helpers
# ---------------------------------------------------------------------------
def draw_meadow(c: Canvas, is_night: bool) -> None:
    if is_night:
        c.hline(0, 28, WIDTH, C["grass_night_hi"])
        c.rect(0, 29, WIDTH, 3, C["grass_night_mid"])
        c.hline(0, 31, WIDTH, C["grass_night_dark"])
    else:
        c.hline(0, 28, WIDTH, C["grass_day_hi"])
        c.rect(0, 29, WIDTH, 3, C["grass_day_mid"])
        c.hline(0, 31, WIDTH, C["grass_day_dark"])


def draw_sun(c: Canvas, sx: int, sy: int, f: int) -> None:
    c.hline(sx - 1, sy - 2, 3, C["sun_core"])
    c.rect(sx - 2, sy - 1, 5, 3, C["sun_core"])
    c.hline(sx - 1, sy + 2, 3, C["sun_core"])
    if (f // 5) % 2 == 0:
        for rx, ry in [(0, -4), (0, 4), (-4, 0), (4, 0), (-3, -3), (3, -3), (-3, 3), (3, 3)]:
            c.set(sx + rx, sy + ry, C["sun_ray"])
    else:
        for rx, ry in [(-1, -4), (1, 4), (-4, 1), (4, -1), (-3, -2), (3, -2), (-2, 3), (2, 3)]:
            c.set(sx + rx, sy + ry, C["sun_ray"])


def draw_moon(c: Canvas, mx: int = 56, my: int = 3) -> None:
    for dx, dy in [(1, 0), (2, 0), (0, 1), (1, 1), (0, 2), (1, 2), (1, 3), (2, 3)]:
        c.set(mx + dx, my + dy, C["moon"])


def draw_stars(c: Canvas, f: int, dense: bool = False) -> None:
    stars = [
        (25, 3, 30, 0), (34, 2, 50, 10), (42, 5, 30, 15), (49, 8, 50, 25),
        (29, 9, 30, 7), (61, 10, 50, 35), (39, 9, 50, 5),
    ]
    if dense:
        stars += [
            (22, 6, 50, 18), (46, 2, 30, 12), (52, 4, 30, 22), (31, 5, 50, 40),
            (59, 14, 30, 3), (24, 13, 50, 30), (44, 12, 30, 26),
        ]
    for sx, sy, per, ph in stars:
        c.set(sx, sy, C["star_bright"] if ((f + ph) % per) < per // 2 else C["star_dim"])


def draw_lantern(c: Canvas, lx: int, ly: int, f: int) -> None:
    """Cozy warm glowing pixel lantern for nighttime scenes."""
    glow_r = 2 if (f % 30) < 15 else 1
    for dy in range(-glow_r, glow_r + 2):
        for dx in range(-glow_r, glow_r + 2):
            c.set(lx + dx, ly + dy, C["lantern_glow"])
    c.hline(lx, ly - 1, 2, C["lantern_frame"])
    c.rect(lx, ly, 2, 2, C["lantern_core"])
    c.hline(lx, ly + 2, 2, C["lantern_frame"])


def draw_fluffy_cloud(c: Canvas, x: int, y: int, col: RGBA, shade: RGBA, wrap: bool = True) -> None:
    pts_hi = [(2, 0), (3, 0), (4, 0), (5, 0), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1)]
    pts_lo = [(0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (7, 2), (8, 2)]
    for dx, dy in pts_hi:
        c.set((x + dx) % WIDTH if wrap else (x + dx), y + dy, col)
    for dx, dy in pts_lo:
        c.set((x + dx) % WIDTH if wrap else (x + dx), y + dy, shade)


def draw_storm_canopy(c: Canvas, f: int, top_col: RGBA, bot_col: RGBA) -> None:
    cx = wrap_pos(0, 1, f, WIDTH, direction=1)
    c.rect(0, 0, WIDTH, 3, top_col)
    for seg in range(0, WIDTH, 8):
        px = (cx + seg) % WIDTH
        for dx in range(6):
            c.set((px + dx) % WIDTH, 3, bot_col)
        for dx in range(1, 5):
            c.set((px + dx) % WIDTH, 4, top_col)


def draw_heart(c: Canvas, cx: int, cy: int) -> None:
    c.set(cx - 1, cy, C["heart"])
    c.set(cx + 1, cy, C["heart"])
    c.hline(cx - 1, cy + 1, 3, C["heart"])
    c.set(cx, cy + 2, C["heart"])


def draw_anger_steam(c: Canvas, cx: int, cy: int, tick: int) -> None:
    c.set(cx, cy, C["anger_red"])
    c.set(cx + 2, cy, C["anger_red"])
    c.set(cx + 1, cy + 1, C["anger_red"])
    rise = tick % 4
    c.set(cx - 2, cy - 1 - rise // 2, C["steam"])
    c.set(cx + 3, cy - 1 - ((rise + 2) % 4) // 2, C["steam_dim"])


def draw_sad_gloom(c: Canvas, cx: int, cy: int, tick: int) -> None:
    """Adorable little sad blue gloom lines + falling teardrop."""
    c.vline(cx, cy, 3, C["gloom_blue"])
    c.vline(cx + 2, cy + 1, 3, C["gloom_blue"])
    drop_y = cy + 2 + (tick % 4)
    c.set(cx - 2, drop_y, C["tear_blue"])


def draw_exclaim(c: Canvas, cx: int, cy: int) -> None:
    c.vline(cx, cy, 3, C["exclaim"])
    c.set(cx, cy + 4, C["exclaim"])


def draw_question(c: Canvas, cx: int, cy: int) -> None:
    c.hline(cx - 1, cy, 3, C["exclaim"])
    c.set(cx + 1, cy + 1, C["exclaim"])
    c.set(cx, cy + 2, C["exclaim"])
    c.set(cx, cy + 4, C["exclaim"])


def draw_zzz(c: Canvas, cx: int, cy: int) -> None:
    c.hline(cx, cy, 3, C["zzz"])
    c.set(cx + 1, cy + 1, C["zzz"])
    c.hline(cx, cy + 2, 3, C["zzz"])


def draw_tangerine(c: Canvas, tx: int, ty: int) -> None:
    c.set(tx + 1, ty - 1, C["stem_green"])
    c.hline(tx, ty, 3, C["orange_main"])
    c.set(tx, ty, C["orange_hi"])
    c.hline(tx, ty + 1, 3, C["orange_main"])
    c.set(tx + 2, ty + 1, C["orange_dark"])


def draw_watermelon(c: Canvas, mx: int, my: int, bite_stage: int = 0) -> None:
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


def draw_picnic_blanket(c: Canvas, x0: int = 16, width: int = 44) -> None:
    """Classic red-and-white checkered picnic blanket laid over the grass."""
    for dy in range(3):
        for dx in range(width):
            col = C["picnic_red"] if ((dx // 2 + dy) % 2 == 0) else C["picnic_white"]
            c.set(x0 + dx, 27 + dy, col)


def draw_picnic_snacks(c: Canvas, px: int, py: int, stage: int) -> None:
    """
    Picnic plate + woven basket:
      stage 0 = full snack pile (sandwich + berries + pastry)
      stage 1 = half eaten
      stage 2 = completely empty plate!
    """
    # Plate
    c.hline(px, py + 3, 7, C["plate"])
    if stage == 0:
        # Stacked snacks (yellow pastry, pink cupcake, red berry)
        c.rect(px + 1, py + 1, 5, 2, C["cake_sponge"])
        c.hline(px + 1, py + 1, 5, C["cake_cream"])
        c.set(px + 2, py, C["cherry"])
        c.set(px + 4, py, C["melon_pink"])
        c.set(px + 5, py + 2, C["orange_main"])
    elif stage == 1:
        c.rect(px + 2, py + 2, 3, 1, C["cake_sponge"])
        c.set(px + 3, py + 1, C["cake_cream"])
    # stage 2: empty plate (only crumbs!)
    elif stage == 2:
        c.set(px + 2, py + 2, C["cake_sponge"])


def draw_giant_cake(c: Canvas, cx: int, cy: int) -> None:
    """Big frosted strawberry peace-offering cake with bright cherry on top!"""
    c.hline(cx, cy + 4, 7, C["plate"])
    c.rect(cx + 1, cy + 2, 5, 2, C["cake_sponge"])
    c.hline(cx + 1, cy + 2, 5, C["cake_pink"])
    c.hline(cx + 1, cy + 1, 5, C["cake_cream"])
    c.set(cx + 3, cy, C["cherry"])
    c.set(cx + 2, cy + 1, C["white"])


def draw_telescope(c: Canvas, tx: int, ty: int, tilt: int = 0) -> None:
    """Cute brass stargazing telescope on tripod angled up-right toward the stars."""
    # Tripod legs
    c.vline(tx + 2, ty + 3, 5, C["tripod"])
    c.set(tx + 1, ty + 6, C["tripod"])
    c.set(tx, ty + 7, C["tripod"])
    c.set(tx + 3, ty + 6, C["tripod"])
    c.set(tx + 4, ty + 7, C["tripod"])
    # Brass tube angled up-right
    c.set(tx, ty + 3 + tilt, C["scope_dark"])
    c.rect(tx + 1, ty + 2 + tilt, 2, 2, C["scope_brass"])
    c.rect(tx + 3, ty + 1, 2, 2, C["scope_brass"])
    c.set(tx + 3, ty + 1, C["scope_hi"])
    c.rect(tx + 5, ty, 2, 2, C["scope_hi"])
    c.set(tx + 6, ty, C["white"])  # lens glint


def draw_umbrella(c: Canvas, cx: int, uy: int, handle_h: int = 16) -> None:
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


def draw_hail_shield(c: Canvas, cx: int, uy: int) -> None:
    c.hline(cx - 8, uy, 17, C["shield_hi"])
    c.hline(cx - 10, uy + 1, 21, C["shield_mid"])
    c.hline(cx - 7, uy + 1, 8, C["shield_hi"])
    c.hline(cx - 11, uy + 2, 23, C["shield_mid"])
    c.hline(cx - 11, uy + 3, 23, C["shield_dark"])


# ---------------------------------------------------------------------------
# Character Primitives: Expressive Lumei & Lulu
# ---------------------------------------------------------------------------
def draw_lumei(
    c: Canvas,
    ox: int,
    oy: int,
    *,
    mood: str = "happy",  # "happy", "blink", "spicy", "startled", "squint", "delighted", "chomp", "guilty"
    sunglasses: bool = False,
    glint_x: int = -1,
    scarf: bool = False,
    scarf_flutter: int = 0,
    lean_x: int = 0,
    sprout_sway: int = 0,
    walk_step: int = 0,
    snow_on_bonnet: bool = False,
) -> None:
    hx = ox + lean_x
    bx = ox

    # V-shaped twin-leaf sprout + tiny orange nub + cream halo ring
    cx = hx + 5
    c.set(cx - 1 + sprout_sway, oy - 3, C["sprout_hi"])
    c.set(cx + 1 + sprout_sway, oy - 3, C["sprout_hi"])
    c.set(cx + sprout_sway, oy - 2, C["sprout_green"])
    c.hline(cx - 2, oy - 1, 5, C["halo_cream"])
    c.set(cx, oy - 1, C["orange_main"])
    c.set(cx - 2, oy - 1, C["halo_shade"])
    c.set(cx + 2, oy - 1, C["halo_shade"])
    c.hline(cx - 1, oy, 3, C["orange_dark"])

    # Pale blush-pink bonnet dome
    c.hline(hx + 2, oy, 7, C["bonnet_pink"])
    c.hline(hx + 4, oy, 3, C["orange_dark"])
    c.rect(hx + 1, oy + 1, 9, 4, C["bonnet_pink"])
    c.rect(hx, oy + 3, 3, 5, C["bonnet_pink"])
    c.set(hx + 3, oy + 1, C["bonnet_dot"])
    c.set(hx + 7, oy + 1, C["bonnet_dot"])
    c.set(hx + 1, oy + 5, C["bonnet_dot"])
    for rx, ry in [(3, 2), (5, 2), (7, 2), (9, 2), (2, 3), (1, 4), (1, 6), (0, 7), (10, 3)]:
        c.set(hx + rx, oy + ry, C["bonnet_ruffle"])
    c.rect(hx + 1, oy + 2, 2, 2, C["gold_main"])
    c.set(hx + 1, oy + 3, C["gold_dark"])

    if snow_on_bonnet:
        c.hline(hx + 2, oy, 6, C["white"])
        c.hline(hx + 3, oy + 1, 4, C["snow_bright"])

    # Round golden butter-yellow face
    c.hline(hx + 4, oy + 3, 6, C["gold_hi"])
    c.rect(hx + 3, oy + 4, 8, 5, C["gold_main"])
    c.hline(hx + 3, oy + 8, 8, C["gold_shade"])
    c.hline(hx + 4, oy + 9, 6, C["gold_shade"])
    c.vline(hx + 2, oy + 5, 3, C["gold_main"])
    c.set(hx + 2, oy + 7, C["gold_shade"])

    cheek_col = C["cheek_angry"] if mood in ("spicy", "guilty") else C["cheek_peach"]
    c.hline(hx + 4, oy + 7, 2, cheek_col)
    c.set(hx + 10, oy + 7, cheek_col)

    # Eyes
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
        c.set(hx + 4, oy + 4, C["mouth_line"])
        c.set(hx + 5, oy + 5, C["eye"])
        c.set(hx + 4, oy + 5, C["eye"])
        c.set(hx + 9, oy + 4, C["mouth_line"])
        c.set(hx + 8, oy + 5, C["eye"])
        c.set(hx + 9, oy + 5, C["eye"])
    elif mood == "delighted":
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
    elif mood in ("startled", "guilty"):
        c.rect(hx + 4, oy + 5, 2, 2, C["white"])
        c.set(hx + 5, oy + 6, C["eye"])
        c.rect(hx + 8, oy + 5, 2, 2, C["white"])
        c.set(hx + 9, oy + 6, C["eye"])
        if mood == "guilty":
            c.set(hx + 10, oy + 3, C["tear_blue"])  # tiny guilty sweat drop!
    else:
        c.rect(hx + 4, oy + 5, 2, 2, C["eye"])
        c.set(hx + 4, oy + 5, C["white"])
        c.set(hx + 4, oy + 6, C["white"])
        c.rect(hx + 8, oy + 5, 2, 2, C["eye"])
        c.set(hx + 8, oy + 5, C["white"])

    # Mouth
    if mood == "spicy":
        c.hline(hx + 6, oy + 8, 3, C["smile_dark"])
        c.set(hx + 7, oy + 7, C["smile_dark"])
    elif mood == "chomp":
        c.rect(hx + 6, oy + 7, 3, 2, C["smile_dark"])
        c.set(hx + 7, oy + 8, C["smile_tongue"])
    elif mood in ("startled", "guilty"):
        c.set(hx + 7, oy + 8, C["smile_dark"])
    else:
        c.hline(hx + 6, oy + 7, 2, C["smile_dark"])
        c.set(hx + 7, oy + 8, C["smile_tongue"])

    # Puffy baby-pink bloomer romper
    c.hline(bx + 3, oy + 10, 7, C["romper_hi"])
    c.rect(bx + 2, oy + 11, 9, 2, C["romper_main"])
    c.vline(bx + 2, oy + 11, 2, C["romper_shade"])
    c.rect(bx + 2, oy + 13, 9, 3, C["romper_main"])
    c.hline(bx + 3, oy + 13, 7, C["romper_hi"])
    c.vline(bx + 2, oy + 13, 3, C["romper_shade"])
    c.hline(bx + 2, oy + 15, 9, C["romper_shade"])
    c.hline(bx + 3, oy + 15, 3, C["bonnet_ruffle"])
    c.hline(bx + 7, oy + 15, 3, C["bonnet_ruffle"])

    paw_y = oy + 10 if mood == "spicy" else oy + 11
    c.rect(bx + 6, paw_y, 4, 2, C["gold_main"])
    c.set(bx + 7, paw_y, C["gold_hi"])
    c.set(bx + 8, paw_y + 1, C["gold_shade"])

    if scarf:
        c.hline(bx + 2, oy + 10, 9, C["scarf_teal"])
        c.set(bx + 4, oy + 10, C["scarf_mint"])
        c.set(bx + 7, oy + 10, C["scarf_mint"])
        c.rect(bx, oy + 11 + scarf_flutter, 2, 2, C["scarf_teal"])
        c.set(bx, oy + 12 + scarf_flutter, C["scarf_mint"])

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
    mood: str = "chill",  # "chill", "blink", "startled", "squint", "happy", "chomp", "dizzy", "sleep", "sad"
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
    hx = ox + lean_x
    bx = ox

    if has_tangerine:
        draw_tangerine(c, hx + 5 + orange_shift, oy - 2)

    c.rect(hx + 2, oy + 1, 2, 2, C["gold_main"])
    c.set(hx + 2, oy + 2, C["gold_dark"])
    c.rect(hx + 10, oy + 1, 2, 2, C["gold_main"])
    c.set(hx + 11, oy + 2, C["gold_dark"])

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
    elif mood == "sad":
        # Droopy little sad frown!
        c.hline(hx + 5, oy + 7, 2, C["mouth_line"])
        c.set(hx + 4, oy + 8, C["mouth_line"])
        c.set(hx + 7, oy + 8, C["mouth_line"])
    elif mood == "sleep":
        c.set(hx + 5, oy + 8, C["smile_dark"])
    elif mood == "happy":
        c.hline(hx + 5, oy + 8, 2, C["mouth_line"])
        c.set(hx + 4, oy + 7, C["mouth_line"])
        c.set(hx + 7, oy + 7, C["mouth_line"])
    else:
        c.hline(hx + 5, oy + 8, 2, C["mouth_line"])

    # Eyes
    if sunglasses:
        c.hline(hx + 2, oy + 3, 9, C["shades_frame"])
        c.rect(hx + 2, oy + 3, 4, 2, C["shades_lens"])
        c.rect(hx + 7, oy + 3, 4, 2, C["shades_lens"])
        c.set(hx + 6, oy + 3, C["shades_frame"])
        if 0 <= glint_x <= 7:
            gx = hx + 2 + glint_x
            if hx + 2 <= gx <= hx + 5 or hx + 7 <= gx <= hx + 10:
                c.set(gx, oy + 3, C["shades_glint"])
    elif mood == "sad":
        # Droopy sad puppy eyes + tiny blue tear!
        c.set(hx + 4, oy + 3, C["gold_dark"])
        c.set(hx + 3, oy + 4, C["eye"])
        c.set(hx + 4, oy + 4, C["tear_blue"])
        c.set(hx + 7, oy + 3, C["gold_dark"])
        c.set(hx + 8, oy + 4, C["eye"])
        c.set(hx + 7, oy + 4, C["tear_blue"])
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
    elif mood in ("sleep", "blink"):
        c.hline(hx + 3, oy + 4, 2, C["mouth_line"])
        c.hline(hx + 7, oy + 4, 2, C["mouth_line"])
    elif mood == "squint":
        c.hline(hx + 3, oy + 4, 2, C["eye"])
        c.hline(hx + 7, oy + 4, 2, C["eye"])
    elif mood == "startled":
        c.rect(hx + 3, oy + 3, 2, 2, C["white"])
        c.set(hx + 3, oy + 4, C["eye"])
        c.rect(hx + 7, oy + 3, 2, 2, C["white"])
        c.set(hx + 7, oy + 4, C["eye"])
    else:
        c.hline(hx + 3, oy + 3, 2, C["gold_shade"])
        c.hline(hx + 7, oy + 3, 2, C["gold_shade"])
        c.set(hx + 3, oy + 4, C["eye"])
        c.set(hx + 4, oy + 4, C["white"])
        c.set(hx + 7, oy + 4, C["eye"])
        c.set(hx + 8, oy + 4, C["white"])

    # Torso
    c.rect(bx + 2, oy + 10, 10, 3, C["gold_main"])
    c.vline(bx + 11, oy + 10, 3, C["gold_shade"])
    c.hline(bx + 3, oy + 10, 7, C["gold_hi"])

    if scarf:
        c.hline(bx + 2, oy + 10, 10, C["scarf_red"])
        c.set(bx + 4, oy + 10, C["scarf_gold"])
        c.set(bx + 7, oy + 10, C["scarf_gold"])
        c.set(bx + 10, oy + 10, C["scarf_gold"])
        c.rect(bx + 11, oy + 11 + scarf_flutter, 2, 2, C["scarf_red"])
        c.set(bx + 12, oy + 12 + scarf_flutter, C["scarf_gold"])

    c.rect(bx + 2, oy + 12, 10, 3, C["shorts_main"])
    c.hline(bx + 3, oy + 12, 8, C["shorts_hi"])
    c.vline(bx + 11, oy + 12, 3, C["shorts_dark"])
    c.hline(bx + 2, oy + 14, 10, C["shorts_dark"])
    c.set(bx + 4, oy + 13, C["shorts_seed"])
    c.set(bx + 9, oy + 13, C["shorts_seed"])

    l_dy = -1 if walk_step == 1 else 0
    r_dy = -1 if walk_step == 2 else 0
    c.rect(bx + 1, oy + 14 + l_dy, 3, 2, C["gold_main"])
    c.set(bx + 1, oy + 15 + l_dy, C["gold_shade"])
    c.rect(bx + 8, oy + 14 + r_dy, 3, 2, C["gold_main"])
    c.set(bx + 10, oy + 15 + r_dy, C["gold_shade"])

    if holding_phone:
        c.rect(bx + 2, oy + 9, 3, 3, C["phone_body"])
        c.vline(bx + 2, oy + 9, 3, C["phone_dark"])
        if phone_glow:
            c.set(bx + 4, oy + 10, C["phone_glow"])
        c.rect(bx + 5, oy + 10, 3, 2, C["gold_hi"])
        c.set(bx + 5, oy + 11, C["gold_main"])


# ---------------------------------------------------------------------------
# Deterministic 64x32 Particle Seeds
# ---------------------------------------------------------------------------
RAIN_DROPS_64 = [
    (2, 1, True), (7, 14, False), (12, 5, True), (17, 22, False), (22, 9, True),
    (27, 18, False), (32, 3, True), (37, 15, False), (42, 7, True), (47, 24, False),
    (52, 11, True), (57, 20, False), (62, 4, True), (5, 26, False), (10, 19, True),
    (15, 11, False), (20, 28, True), (25, 6, False), (30, 23, True), (35, 12, False),
    (40, 27, True), (45, 2, False), (50, 17, True), (55, 29, False), (60, 13, True),
    (1, 16, False), (29, 10, True), (49, 25, False),
]

DRIZZLE_DROPS_64 = [
    (6, 3, False), (14, 15, True), (23, 8, False), (31, 21, True), (39, 5, False),
    (46, 17, True), (54, 10, False), (61, 23, True), (19, 26, False), (35, 13, True),
    (51, 2, False), (10, 20, True), (43, 27, False), (27, 1, True),
]

SNOW_FLAKES_64 = [
    (2, 2, 0.0, True), (7, 15, 1.1, False), (12, 7, 2.2, False), (17, 23, 0.7, True),
    (22, 4, 3.1, False), (27, 19, 1.9, False), (32, 11, 4.0, True), (37, 26, 2.5, False),
    (42, 6, 1.4, False), (47, 18, 5.0, False), (52, 1, 3.7, True), (57, 14, 0.3, False),
    (62, 24, 2.9, False), (5, 27, 4.5, False), (15, 12, 1.6, True), (25, 28, 5.4, False),
    (35, 17, 2.1, False), (45, 9, 3.3, True), (55, 22, 0.9, False), (60, 5, 4.8, False),
    (10, 19, 2.6, False), (30, 3, 1.2, False), (50, 13, 3.9, False), (20, 14, 0.4, False),
]

WIND_LEAVES_64 = [
    (2, 4, 0.0, "leaf_orange"), (10, 12, 1.3, "leaf_gold"), (18, 7, 2.4, "leaf_red"),
    (26, 18, 0.8, "leaf_orange"), (34, 9, 3.6, "leaf_sage"), (42, 21, 4.8, "leaf_gold"),
    (50, 6, 1.9, "leaf_red"), (58, 16, 5.2, "leaf_orange"), (6, 22, 2.9, "leaf_gold"),
    (14, 26, 4.1, "leaf_sage"), (22, 2, 0.5, "leaf_red"), (30, 24, 3.1, "leaf_orange"),
    (38, 14, 1.7, "leaf_gold"), (46, 25, 4.4, "leaf_sage"), (54, 11, 2.1, "leaf_red"),
    (62, 20, 0.9, "leaf_orange"), (16, 15, 3.8, "leaf_gold"), (44, 3, 1.1, "leaf_orange"),
]

HAIL_STONES_64 = [
    (6, 2), (16, 14), (26, 6), (36, 20), (46, 10), (56, 24),
    (11, 22), (21, 8), (31, 18), (41, 4), (51, 16), (61, 12),
]


# ---------------------------------------------------------------------------
# 1A. CLEAR DAY: Watermelon Heist + Off-Screen Peace Offering!
# ---------------------------------------------------------------------------
def render_clear_day(f: int) -> Image.Image:
    c = Canvas()
    c.gradient_v((24, 78, 154, 255), (56, 132, 204, 255), 0, 28)
    draw_meadow(c, is_night=False)

    draw_sun(c, 55, 6, f)
    cx = wrap_pos(28, 1, f, WIDTH, direction=1)
    draw_fluffy_cloud(c, cx, 4, C["cloud_white"], C["cloud_light"])

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    glint_step = f % 50
    glint_x = glint_step if glint_step <= 7 else -1
    sprout_sway = 1 if (f % 30) < 15 else 0

    lumei_x, lumei_y = 20, 12 + bob_lumei
    lulu_x, lulu_y = 44, 13 + bob_lulu
    lumei_mood, lulu_mood = "happy", "chill"
    lumei_shades, lulu_shades = True, True
    lumei_walk, lulu_walk = 0, 0
    melon_x, melon_y = 33, 23
    melon_stage = 0
    show_melon = True

    if 24 <= f < 56:
        lulu_shades = False
        if f < 34:
            lulu_x = lerp_i(44, 38, ease_in_out((f - 24) / 10))
            lulu_walk = 1 if (f % 4 < 2) else 2
        else:
            lulu_x = 38
        if 34 <= f < 44:
            lulu_mood = "chomp" if (f % 4 < 2) else "happy"
            melon_stage = 1
        elif 44 <= f < 56:
            lulu_mood = "chomp" if (f % 4 < 2) else "happy"
            melon_stage = 3
            dt = f - 44
            c.set(35 - dt // 4, 21 - dt // 3, C["melon_pink"])
            c.set(38 + dt // 5, 20 - dt // 4, C["melon_seed"])
    elif 56 <= f < 84:
        lumei_shades, lulu_shades = False, False
        melon_stage = 3
        lumei_mood = "spicy"
        lumei_x = lerp_i(20, 25, ease_in_out((f - 56) / 10))
        lumei_y = 12 - (2 if (f % 6 < 3) else 0)
        lulu_x = lerp_i(38, 44, ease_in_out((f - 56) / 10))
        lulu_mood = "startled" if f < 68 else "chill"
    elif 84 <= f < 120:
        lumei_shades, lulu_shades = False, False
        lumei_x = 25 if f < 104 else lerp_i(25, 20, ease_in_out((f - 104) / 16))
        lumei_mood = "spicy" if f < 106 else "startled"
        lulu_walk = 1 if (f % 4 < 2) else 2
        if f < 98:
            lulu_x = lerp_i(44, 68, ease_in_out((f - 84) / 14))
            melon_stage = 3
        elif f < 104:
            lulu_x = 68
            show_melon = False
        else:
            lulu_x = lerp_i(68, 44, ease_in_out((f - 104) / 16))
            lulu_mood = "happy"
            melon_x = lulu_x - 5
            melon_y = 19 + (f % 2)
            melon_stage = 0
    elif 120 <= f < 138:
        lumei_shades, lulu_shades = False, False
        lumei_mood, lulu_mood = "delighted", "happy"
        lumei_y = 12 - (1 if (f % 6 < 3) else 0)
        melon_x = lerp_i(39, 33, ease_in_out((f - 120) / 8))
        melon_y = lerp_i(19, 23, ease_in_out((f - 120) / 8))
        melon_stage = 0

    draw_lumei(c, lumei_x, lumei_y, mood=lumei_mood, sunglasses=lumei_shades, glint_x=glint_x, sprout_sway=sprout_sway, walk_step=lumei_walk)
    draw_lulu(c, lulu_x, lulu_y, mood=lulu_mood, sunglasses=lulu_shades, glint_x=glint_x, walk_step=lulu_walk)
    if show_melon:
        draw_watermelon(c, melon_x, melon_y, bite_stage=melon_stage)
    if 58 <= f < 98:
        draw_anger_steam(c, lumei_x + 5, lumei_y - 4, f)
    elif 120 <= f < 136:
        draw_heart(c, 36, 12 - (f - 120) // 4)
    return c.img


# ---------------------------------------------------------------------------
# 1B. CLEAR NIGHT: Cozy Telescope Stargazing & Twin Shooting Stars!
# ---------------------------------------------------------------------------
def render_clear_night(f: int) -> Image.Image:
    c = Canvas()
    c.gradient_v((4, 8, 22, 255), (10, 18, 42, 255), 0, 28)
    draw_meadow(c, is_night=True)
    draw_stars(c, f, dense=True)
    draw_moon(c, 56, 3)

    # Shooting star #1 (f=24..38) and Shooting star #2 (f=76..90)
    for start_f, x_start, y_start in [(24, 24, 2), (76, 30, 3)]:
        if start_f <= f <= start_f + 14:
            dt = f - start_f
            ssx = x_start + dt * 2
            ssy = y_start + dt // 2
            c.set(ssx, ssy, C["white"])
            c.set(ssx - 1, ssy, C["wish_gold"])
            c.set(ssx - 2, ssy - 1, C["star_bright"])
            c.set(ssx - 3, ssy - 1, C["star_dim"])

    # Cozy dark-blue/purple stargazing mat on the meadow
    c.hline(17, 28, 42, C["blanket_main"])
    c.hline(16, 29, 44, C["blanket_dark"])
    for sx in (21, 33, 45, 53):
        c.set(sx, 28, C["blanket_star"])

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    sprout_sway = 1 if (f % 30) < 15 else 0

    # Lumei on left, Lulu peering through the brass telescope on right!
    lumei_x, lumei_y = 20, 12 + bob_lumei
    lulu_x, lulu_y = 39, 13 + bob_lulu
    scope_x, scope_y = 52, 20
    scope_tilt = 0
    lumei_mood = "blink" if (f % 50) in (12, 13) else "happy"
    lulu_mood = "blink" if (f % 50) in (34, 35) else "chill"
    lumei_walk, lulu_walk = 0, 0
    orange_pop = 0

    if 24 <= f < 52:
        # Shooting star #1! Lumei hops excitedly pointing up & nudges Lulu!
        lumei_mood = "delighted"
        lumei_y = 12 - (2 if (f % 8 < 4) else 0)
        if f >= 34:
            lumei_x = lerp_i(20, 29, ease_in_out((f - 34) / 14))
            lumei_walk = 1 if (f % 4 < 2) else 2
            if f >= 42:
                # Playful bump wobbles the telescope & pops Lulu's tangerine slightly!
                lulu_mood = "startled"
                orange_pop = -1 if (f % 4 < 2) else 0
                scope_tilt = 1 if (f % 4 < 2) else 0
    elif 52 <= f < 96:
        # Lulu steps aside sweetly so Lumei can peer through the telescope -> Shooting star #2!
        lulu_x = lerp_i(39, 28, ease_in_out((f - 52) / 14)) if f < 66 else 28
        lumei_x = lerp_i(29, 41, ease_in_out((f - 52) / 14)) if f < 66 else 41
        lumei_walk = (1 if (f % 4 < 2) else 2) if f < 66 else 0
        lulu_walk = (2 if (f % 4 < 2) else 1) if f < 66 else 0
        lumei_mood = "delighted" if f >= 74 else "happy"
        lulu_mood = "happy" if f >= 74 else "chill"
        if 80 <= f < 96:
            # Wish sparkles & twin hearts rise into the starry sky!
            rise = (f - 80) // 4
            draw_heart(c, 39, 11 - rise)
            c.set(46, 9 - rise, C["wish_gold"])
            c.set(33, 10 - rise, C["wish_gold"])
    elif 96 <= f < 130:
        # Cozy stargazing cuddle side-by-side, then smoothly return to home spots
        if f < 114:
            lulu_x, lumei_x = 28, 41
            lumei_mood, lulu_mood = "delighted", "happy"
            draw_heart(c, 38, 12 - (f - 96) // 6)
        else:
            t = ease_in_out((f - 114) / 16)
            lumei_x = lerp_i(41, 20, t)
            lulu_x = lerp_i(28, 39, t)
            lumei_walk = 1 if (f % 4 < 2) else 2
            lulu_walk = 2 if (f % 4 < 2) else 1
            lumei_mood, lulu_mood = "happy", "happy"

    draw_telescope(c, scope_x, scope_y, tilt=scope_tilt)
    draw_lumei(c, lumei_x, lumei_y, mood=lumei_mood, sprout_sway=sprout_sway, walk_step=lumei_walk)
    draw_lulu(c, lulu_x, lulu_y + orange_pop, mood=lulu_mood, walk_step=lulu_walk)
    return c.img


# ---------------------------------------------------------------------------
# 2. PARTLY CLOUDY (Day & Night): Checkered Picnic — Lumei Eats All the Food!
# ---------------------------------------------------------------------------
def render_partly_cloudy(f: int, is_night: bool) -> Image.Image:
    c = Canvas()
    if is_night:
        c.gradient_v((6, 12, 30, 255), (14, 24, 52, 255), 0, 28)
        draw_stars(c, f, dense=False)
        draw_moon(c, 55, 3)
        c_hi, c_lo = C["cloud_mid"], C["cloud_dark"]
    else:
        c.gradient_v((26, 76, 146, 255), (62, 126, 194, 255), 0, 28)
        draw_sun(c, 54, 6, f)
        c_hi, c_lo = C["cloud_white"], C["cloud_light"]

    # Fluffy partly-cloudy drifting clouds (1 exact wrap over 64px)
    c1 = wrap_pos(22, 1, f, WIDTH, direction=1)
    c2 = wrap_pos(46, 1, f, WIDTH, direction=1)
    draw_fluffy_cloud(c, c1, 3, c_hi, c_lo)
    draw_fluffy_cloud(c, c2, 6, c_hi, c_lo)

    draw_meadow(c, is_night=is_night)
    draw_picnic_blanket(c, x0=18, width=42)

    # Cozy picnic lantern on the blanket corner at night!
    if is_night:
        draw_lantern(c, 56, 24, f)

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    sprout_sway = 1 if (f % 30) < 15 else 0

    lumei_x, lumei_y = 20, 12 + bob_lumei
    lulu_x, lulu_y = 44, 13 + bob_lulu
    lumei_mood = "blink" if (f % 50) in (12, 13) else "happy"
    lulu_mood = "blink" if (f % 50) in (34, 35) else "chill"
    lumei_walk = 0
    snack_stage = 0
    show_cake = False
    cake_x, cake_y = 33, 23
    lulu_phone = False

    if 22 <= f < 56:
        # While chill Lulu looks at his phone, hungry Lumei scoots over & EATS ALL THE FOOD!
        lulu_phone = True
        if f < 32:
            lumei_x = lerp_i(20, 26, ease_in_out((f - 22) / 10))
            lumei_walk = 1 if (f % 4 < 2) else 2
        else:
            lumei_x = 26
        if 32 <= f < 44:
            lumei_mood = "chomp" if (f % 4 < 2) else "delighted"
            snack_stage = 1
        elif 44 <= f < 56:
            lumei_mood = "chomp" if (f % 4 < 2) else "delighted"
            snack_stage = 2  # Plate totally empty!!
            dt = f - 44
            c.set(34 + dt // 5, 22 - dt // 4, C["cake_sponge"])
            c.set(32 - dt // 5, 21 - dt // 4, C["cake_pink"])
    elif 56 <= f < 84:
        # Lulu puts phone away, sees empty plate -> SAD LULU (droopy eyes + blue tear gloom)!
        # Lumei freezes in guilty shock!
        snack_stage = 2
        lumei_x = 26
        lulu_mood = "sad"
        lulu_y = 14  # sad slump
        lumei_mood = "guilty"
        draw_sad_gloom(c, lulu_x + 11, lulu_y - 3, f)
    elif 84 <= f < 120:
        # Sweet Lumei sprints OFF-SCREEN left/right -> rushes back with a GIANT FROSTED CAKE!
        snack_stage = 2
        lulu_mood = "sad" if f < 110 else "startled"
        lulu_y = 14 if f < 110 else 13
        if f < 108:
            draw_sad_gloom(c, lulu_x + 11, lulu_y - 3, f)
        lumei_walk = 1 if (f % 4 < 2) else 2
        if f < 98:
            # Sprints completely OFF-SCREEN left (x = -14)!
            lumei_x = lerp_i(26, -14, ease_in_out((f - 84) / 14))
            lumei_mood = "guilty"
        elif f < 104:
            lumei_x = -14
        else:
            # Rushes back in from the left carrying a giant frosted strawberry cake!
            lumei_x = lerp_i(-14, 24, ease_in_out((f - 104) / 16))
            lumei_mood = "happy"
            show_cake = True
            cake_x = lumei_x + 9
            cake_y = 19 + (f % 2)
    elif 120 <= f < 138:
        # Lumei places the giant cake in front of Lulu -> Lulu cheers right up with hearts!
        snack_stage = 2
        show_cake = True
        lumei_x = lerp_i(24, 20, ease_in_out((f - 120) / 12))
        cake_x = lerp_i(33, 33, 1.0)
        cake_y = lerp_i(19, 23, ease_in_out((f - 120) / 8))
        lumei_mood, lulu_mood = "delighted", "happy"
        lulu_y = 13 - (1 if (f % 6 < 3) else 0)
        draw_heart(c, 36, 11 - (f - 120) // 4)
        if f >= 126:
            draw_heart(c, 30, 12 - (f - 126) // 4)
    # f=138..149: Picnic snacks cleanly restored -> matches f=0!

    draw_lumei(c, lumei_x, lumei_y, mood=lumei_mood, sprout_sway=sprout_sway, walk_step=lumei_walk)
    draw_lulu(c, lulu_x, lulu_y, mood=lulu_mood, holding_phone=lulu_phone, phone_glow=(f % 8 < 4))
    if show_cake:
        draw_giant_cake(c, cake_x, cake_y)
    else:
        draw_picnic_snacks(c, 33, 24, stage=snack_stage)
    return c.img


# ---------------------------------------------------------------------------
# 3. OVERCAST (Day & Night): Sleepy Overcast Zzz & Cozy Wake-Up Cuddle!
# ---------------------------------------------------------------------------
def render_overcast(f: int, is_night: bool) -> Image.Image:
    c = Canvas()
    if is_night:
        c.gradient_v((14, 18, 30, 255), (24, 30, 48, 255), 0, 28)
        c_top, c_hi, c_lo = C["cloud_night"], C["cloud_dark"], C["cloud_night"]
    else:
        c.gradient_v((64, 78, 98, 255), (96, 112, 134, 255), 0, 28)
        c_top, c_hi, c_lo = C["cloud_gray"], C["cloud_light"], C["cloud_gray"]

    draw_meadow(c, is_night=is_night)

    c1 = wrap_pos(0, 1, f, WIDTH, direction=1)
    c2 = wrap_pos(16, 1, f, WIDTH, direction=1)
    c3 = wrap_pos(34, 1, f, WIDTH, direction=1)
    c4 = wrap_pos(50, 1, f, WIDTH, direction=1)
    c.rect(0, 0, WIDTH, 4, c_top)
    for cx in (c1, c2, c3, c4):
        draw_fluffy_cloud(c, cx, 2, c_hi, c_lo)
        draw_fluffy_cloud(c, (cx + 8) % WIDTH, 5, c_lo, c_top)

    if is_night:
        draw_lantern(c, 58, 25, f)

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    sprout_sway = 1 if (f % 30) < 15 else 0

    lumei_x, lumei_y = 20, 12 + bob_lumei
    lulu_x, lulu_y = 44, 13 + bob_lulu
    lumei_mood, lulu_mood = "happy", "sleep"
    lumei_walk = 0

    if 6 <= f < 46:
        lulu_mood = "sleep"
        lumei_mood = "happy" if f < 30 else "squint"
        zt = (f - 6) % 20
        draw_zzz(c, lulu_x + 11, 8 - zt // 5)
    elif 46 <= f < 78:
        lumei_mood = "spicy"
        if f < 62:
            lumei_x = lerp_i(20, 33, ease_in_out((f - 46) / 16))
            lumei_walk = 1 if (f % 4 < 2) else 2
            lulu_mood = "sleep"
        else:
            lumei_x = 33
            lumei_y = 12 - (1 if (f % 4 < 2) else 0)
            lulu_mood = "startled"
            draw_exclaim(c, lulu_x + 6, lulu_y - 6)
    elif 78 <= f < 118:
        lumei_x = 33
        lulu_x = lerp_i(44, 40, ease_in_out((f - 78) / 10)) if f < 108 else lerp_i(40, 44, ease_in_out((f - 108) / 10))
        lumei_mood, lulu_mood = "delighted", "happy"
        if 86 <= f < 112:
            draw_heart(c, 38, 11 - (f - 86) // 6)
    elif 118 <= f < 136:
        lumei_x = lerp_i(33, 20, ease_in_out((f - 118) / 18))
        lumei_walk = 1 if (f % 4 < 2) else 2
        lumei_mood = "happy"
        lulu_mood = "chill" if f < 128 else "sleep"

    draw_lumei(c, lumei_x, lumei_y, mood=lumei_mood, sprout_sway=sprout_sway, walk_step=lumei_walk)
    draw_lulu(c, lulu_x, lulu_y, mood=lulu_mood)
    if 48 <= f < 74:
        draw_anger_steam(c, lumei_x + 4, lumei_y - 4, f)
    return c.img


# ---------------------------------------------------------------------------
# 4. FOG (Day & Night): Lost in the Fog — Off-Screen Hide & Seek!
# ---------------------------------------------------------------------------
def render_fog(f: int, is_night: bool) -> Image.Image:
    c = Canvas()
    if is_night:
        c.gradient_v((16, 24, 38, 255), (34, 46, 66, 255), 0, 28)
        draw_moon(c, 55, 3)
        fog_hi, fog_mid = C["fog_night_hi"], C["fog_night_mid"]
    else:
        c.gradient_v((72, 88, 106, 255), (112, 130, 148, 255), 0, 28)
        fog_hi, fog_mid = C["fog_day_hi"], C["fog_day_mid"]

    draw_meadow(c, is_night=is_night)

    m_bg = wrap_pos(0, 1, f, WIDTH, direction=1)
    for seg in range(0, WIDTH, 16):
        mx = (m_bg + seg) % WIDTH
        for dx in range(12):
            c.set((mx + dx) % WIDTH, 11, fog_mid)
            c.set((mx + dx) % WIDTH, 12, fog_mid)

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    sprout_sway = 1 if (f % 30) < 15 else 0

    lumei_x, lumei_y = 20, 12 + bob_lumei
    lulu_x, lulu_y = 44, 13 + bob_lulu
    lumei_mood, lulu_mood = "happy", "chill"
    lumei_walk, lulu_walk = 0, 0

    if 20 <= f < 46:
        lulu_x = lerp_i(44, 68, ease_in_out((f - 20) / 24))
        lulu_walk = 1 if (f % 4 < 2) else 2
        lumei_mood = "startled" if f >= 34 else "happy"
    elif 46 <= f < 84:
        lulu_x = 68
        lumei_mood = "squint"
        lumei_walk = 1 if (f % 6 < 3) else 2
        if f < 64:
            lumei_x = lerp_i(20, 40, ease_in_out((f - 46) / 18))
            draw_question(c, lumei_x + 5, lumei_y - 7)
        else:
            lumei_x = lerp_i(40, 24, ease_in_out((f - 64) / 18))
            draw_question(c, lumei_x + 5, lumei_y - 7)
    elif 84 <= f < 118:
        lumei_x = 24
        if f < 102:
            lulu_x = lerp_i(68, 36, ease_in_out((f - 84) / 18))
            lulu_walk = 1 if (f % 4 < 2) else 2
            lumei_mood = "startled" if f < 96 else "delighted"
            if f < 96:
                draw_exclaim(c, lumei_x + 5, lumei_y - 7)
        else:
            lulu_x = 36
            lumei_mood, lulu_mood = "delighted", "happy"
            draw_heart(c, 34, 11 - (f - 102) // 4)
    elif 118 <= f < 138:
        lumei_x = lerp_i(24, 20, ease_in_out((f - 118) / 18))
        lulu_x = lerp_i(36, 44, ease_in_out((f - 118) / 18))
        lumei_walk = 1 if (f % 4 < 2) else 2
        lulu_walk = 2 if (f % 4 < 2) else 1

    draw_lumei(c, lumei_x, lumei_y, mood=lumei_mood, sprout_sway=sprout_sway, walk_step=lumei_walk)
    if is_night:
        draw_lantern(c, lumei_x + 11, lumei_y + 10, f)  # Lumei carries a warm glowing lantern in night fog!
    draw_lulu(c, lulu_x, lulu_y, mood=lulu_mood, walk_step=lulu_walk)

    m_fg1 = wrap_pos(4, 2, f, WIDTH, direction=1)
    m_fg2 = wrap_pos(32, 3, f, WIDTH, direction=-1)
    for offset, y_row, col in [(m_fg1, 18, fog_mid), (m_fg1 + 26, 22, fog_hi), (m_fg2, 25, fog_hi)]:
        for seg in (0, 32):
            bx = (offset + seg) % WIDTH
            for dx in range(18):
                c.set((bx + dx) % WIDTH, y_row, col)
                if 2 <= dx <= 15:
                    c.set((bx + dx) % WIDTH, y_row + 1, col)
    return c.img


# ---------------------------------------------------------------------------
# 5. DRIZZLE (Day & Night): Puddle-Splash Shenanigans!
# ---------------------------------------------------------------------------
def render_drizzle(f: int, is_night: bool) -> Image.Image:
    c = Canvas()
    if is_night:
        c.gradient_v((10, 18, 34, 255), (18, 30, 52, 255), 0, 28)
        draw_storm_canopy(c, f, C["cloud_night"], C["cloud_dark"])
        puddle_col = C["puddle_night"]
    else:
        c.gradient_v((44, 68, 98, 255), (72, 102, 134, 255), 0, 28)
        draw_storm_canopy(c, f, C["cloud_gray"], C["cloud_light"])
        puddle_col = C["puddle_day"]

    draw_meadow(c, is_night=is_night)
    c.hline(28, 28, 16, puddle_col)
    c.hline(26, 29, 20, puddle_col)
    c.hline(30, 29, 8, C["puddle_hi"])

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    sprout_sway = 1 if (f % 30) < 15 else 0

    lumei_x, lumei_y = 20, 12 + bob_lumei
    lulu_x, lulu_y = 44, 13 + bob_lulu
    lumei_mood, lulu_mood = "happy", "chill"
    lumei_walk, lulu_walk = 0, 0
    lulu_phone = True

    if 22 <= f < 56:
        if f < 36:
            lumei_x = lerp_i(20, 29, ease_in_out((f - 22) / 14))
            lumei_walk = 1 if (f % 4 < 2) else 2
        else:
            lumei_x = 29
            lumei_y = 12 - int(round(4 * abs(math.sin(math.pi * (f - 36) / 10))))
            lumei_mood = "delighted"
            if (f - 36) % 10 in (0, 1, 9):
                for sx, sy in [(38, 24), (41, 21), (43, 23), (26, 25)]:
                    c.set(sx, sy, C["rain_bright"])
            if f >= 46:
                lulu_mood, lulu_phone = "startled", False
    elif 56 <= f < 96:
        lumei_x, lulu_phone = 26, False
        if f < 68:
            lulu_x = lerp_i(44, 35, ease_in_out((f - 56) / 12))
            lulu_walk = 1 if (f % 4 < 2) else 2
        else:
            lulu_x = 35
            lulu_y = 13 - int(round(4 * abs(math.sin(math.pi * (f - 68) / 10))))
            lulu_mood = "happy"
            lumei_mood = "startled" if f < 78 else "delighted"
            if (f - 68) % 10 in (0, 1, 9):
                for sx, sy in [(31, 23), (29, 20), (42, 24), (33, 21)]:
                    c.set(sx, sy, C["rain_bright"])
    elif 96 <= f < 130:
        lumei_x = lerp_i(26, 20, ease_in_out((f - 108) / 20)) if f >= 108 else 26
        lulu_x = lerp_i(35, 44, ease_in_out((f - 108) / 20)) if f >= 108 else 35
        lumei_walk = (1 if (f % 4 < 2) else 2) if f >= 108 else 0
        lulu_walk = (2 if (f % 4 < 2) else 1) if f >= 108 else 0
        lumei_mood, lulu_mood = "delighted", "happy"
        lulu_phone = f >= 126
        if f < 112:
            draw_heart(c, 36, 11 - (f - 96) // 4)

    draw_lumei(c, lumei_x, lumei_y, mood=lumei_mood, sprout_sway=sprout_sway, walk_step=lumei_walk)
    draw_lulu(c, lulu_x, lulu_y, mood=lulu_mood, holding_phone=lulu_phone, phone_glow=(f % 10 < 5), walk_step=lulu_walk)

    for x0, y0, bright in DRIZZLE_DROPS_64:
        rx = wrap_pos(x0, 2, f, WIDTH, direction=-1)
        ry = wrap_pos(y0, 10, f, HEIGHT, direction=1)
        c.set(rx, ry, C["rain_bright"] if bright else C["rain_dim"])
    return c.img


# ---------------------------------------------------------------------------
# 6. FREEZING RAIN (Day & Night): Slippery Ice Wipeout Off-Screen!
# ---------------------------------------------------------------------------
def render_freezing_rain(f: int, is_night: bool) -> Image.Image:
    c = Canvas()
    if is_night:
        c.gradient_v((8, 16, 36, 255), (14, 30, 58, 255), 0, 28)
        draw_moon(c, 55, 3)
    else:
        c.gradient_v((42, 74, 112, 255), (76, 118, 158, 255), 0, 28)

    c.hline(0, 28, WIDTH, C["ice_hi"])
    c.rect(0, 29, WIDTH, 2, C["ice_mid"])
    c.hline(0, 31, WIDTH, C["ice_dark"])
    gx = wrap_pos(4, 2, f, WIDTH, direction=1)
    for off in (0, 22, 44):
        c.hline((gx + off) % WIDTH, 28, 4, C["white"])

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    sprout_sway = 1 if (f % 30) < 15 else 0

    lumei_x, lumei_y = 20, 12 + bob_lumei
    lulu_x, lulu_y = 44, 13 + bob_lulu
    lumei_mood, lulu_mood = "happy", "chill"
    lulu_has_tang = True
    loose_tang: Optional[Tuple[int, int]] = None

    if 22 <= f < 52:
        t = ease_in_out((f - 22) / 28)
        lulu_x = lerp_i(44, 70, t)
        lulu_y = 13 + (1 if f >= 30 else 0)
        lulu_mood = "startled" if f < 36 else "dizzy"
        lulu_has_tang = f < 30
        if not lulu_has_tang:
            loose_tang = (lulu_x + 2, 11 - (f % 3))
        lumei_mood = "startled"
        if f < 40:
            draw_exclaim(c, lulu_x + 6, lulu_y - 6)
    elif 52 <= f < 74:
        lulu_x, lulu_has_tang = 70, False
        lumei_x = lerp_i(20, 68, ease_in_out((f - 52) / 20))
        lumei_mood = "spicy"
    elif 74 <= f < 118:
        t = ease_in_out((f - 74) / 40)
        lumei_x = lerp_i(66, 20, t)
        lulu_x = lerp_i(82, 44, t)
        lumei_mood = "spicy" if f < 104 else "happy"
        lulu_mood = "dizzy" if f < 108 else "chill"
        lulu_has_tang = f >= 106
        if not lulu_has_tang:
            rt = ease_in_out(max(0.0, (f - 88) / 18))
            loose_tang = (lerp_i(66, 49, rt), lerp_i(25, 11, rt))
    elif 118 <= f < 136:
        lumei_mood, lulu_mood = "delighted", "happy"
        draw_heart(c, 36, 11 - (f - 118) // 5)

    draw_lumei(c, lumei_x, lumei_y, mood=lumei_mood, scarf=True, sprout_sway=sprout_sway)
    draw_lulu(c, lulu_x, lulu_y, mood=lulu_mood, scarf=True, has_tangerine=lulu_has_tang)
    if loose_tang is not None:
        draw_tangerine(c, loose_tang[0], loose_tang[1])

    for x0, y0, bright in RAIN_DROPS_64:
        rx = wrap_pos(x0, 5, f, WIDTH, direction=-1)
        ry = wrap_pos(y0, 15, f, HEIGHT, direction=1)
        c.set(rx, ry, C["ice_hi"] if bright else C["ice_mid"])
        c.set((rx + 1) % WIDTH, (ry - 1) % HEIGHT, C["ice_dark"])
    return c.img


# ---------------------------------------------------------------------------
# 7. RAIN (Day & Night): Umbrella Tug-of-War!
# ---------------------------------------------------------------------------
def render_rain(f: int, is_night: bool) -> Image.Image:
    c = Canvas()
    if is_night:
        c.gradient_v((6, 12, 26, 255), (12, 22, 42, 255), 0, 29)
        draw_storm_canopy(c, f, C["cloud_night"], C["cloud_dark"])
        c.rect(0, 29, WIDTH, 3, (12, 24, 46, 255))
        c.hline(0, 29, WIDTH, (22, 42, 74, 255))
    else:
        c.gradient_v((34, 54, 84, 255), (54, 80, 114, 255), 0, 29)
        draw_storm_canopy(c, f, C["cloud_mid"], C["cloud_gray"])
        c.rect(0, 29, WIDTH, 3, (28, 52, 82, 255))
        c.hline(0, 29, WIDTH, (44, 76, 114, 255))

    for rx, ph in [(8, 0), (32, 10), (54, 20)]:
        rip = (f + ph) % 30
        if rip < 10:
            c.hline(rx, 30, 2, C["rain_bright"])
        elif rip < 20:
            c.set(rx - 1, 30, C["rain_dim"])
            c.set(rx + 2, 30, C["rain_dim"])

    bob = bob_offset(f, period=30, phase=0)
    sprout_sway = 1 if (f % 30) < 15 else 0
    lumei_x, lumei_y = 21, 13 + bob
    lulu_x, lulu_y = 36, 14 + bob
    umb_cx, umb_y = 34, 4 + bob
    lumei_mood = "blink" if (f % 50) in (12, 13) else "happy"
    lulu_mood = "blink" if (f % 50) in (34, 35) else "chill"
    lulu_phone, lumei_walk = False, 0

    if 24 <= f < 56:
        lulu_phone = True
        t = ease_in_out((f - 24) / 22)
        lulu_x = lerp_i(36, 46, t)
        umb_cx = lerp_i(34, 48, t)
        if f >= 42:
            lumei_mood = "startled"
            if f % 4 < 2:
                c.set(lumei_x + 4, lumei_y - 3, C["rain_bright"])
                c.set(lumei_x + 7, lumei_y - 2, C["white"])
    elif 56 <= f < 88:
        lumei_mood = "spicy"
        if f < 70:
            lumei_x = lerp_i(21, 33, ease_in_out((f - 56) / 14))
            lumei_walk = 1 if (f % 4 < 2) else 2
            lulu_x, umb_cx, lulu_phone = 46, 48, True
        else:
            lumei_x = lerp_i(33, 21, ease_in_out((f - 70) / 16))
            lumei_walk = 1 if (f % 4 < 2) else 2
            umb_cx = lerp_i(48, 28, ease_in_out((f - 70) / 12))
            lulu_x = lerp_i(46, 39, ease_in_out((f - 74) / 14))
            lulu_mood = "startled"
    elif 88 <= f < 126:
        umb_cx = lerp_i(28, 34, ease_in_out((f - 88) / 14))
        lulu_x = lerp_i(39, 34, ease_in_out((f - 88) / 14)) if f < 112 else lerp_i(34, 36, ease_in_out((f - 112) / 14))
        lumei_mood = "delighted" if f >= 96 else "happy"
        lulu_mood = "happy"

    draw_lumei(c, lumei_x, lumei_y, mood=lumei_mood, sprout_sway=sprout_sway, walk_step=lumei_walk)
    draw_lulu(c, lulu_x, lulu_y, mood=lulu_mood, holding_phone=lulu_phone, phone_glow=(f % 6 < 3))
    draw_umbrella(c, umb_cx, umb_y, handle_h=16)

    if 56 <= f < 82:
        draw_anger_steam(c, lumei_x + 4, lumei_y - 4, f)
    elif 98 <= f < 120:
        draw_heart(c, 33, 12 - (f - 98) // 6)

    for x0, y0, bright in RAIN_DROPS_64:
        rx = wrap_pos(x0, 5, f, WIDTH, direction=-1)
        ry = wrap_pos(y0, 15, f, HEIGHT, direction=1)
        if (umb_cx - 12) <= rx <= (umb_cx + 12) and ry >= umb_y + 3:
            continue
        c.set(rx, ry, C["rain_bright"] if bright else C["rain_dim"])
        if (umb_cx - 11) <= rx <= (umb_cx + 11) and umb_y <= ry <= umb_y + 2:
            c.set(rx, umb_y - 1, C["white"])
        else:
            c.set((rx + 1) % WIDTH, (ry - 1) % HEIGHT, C["rain_dim"])
    return c.img


# ---------------------------------------------------------------------------
# 8. RAIN SHOWERS (Day & Night): Cloudburst Dash & Rainbow / Moonbow!
# ---------------------------------------------------------------------------
def render_rain_showers(f: int, is_night: bool) -> Image.Image:
    shower_active = 15 <= f <= 68
    rainbow_active = 74 <= f <= 138

    c = Canvas()
    if is_night:
        if shower_active:
            c.gradient_v((6, 10, 22, 255), (12, 20, 38, 255), 0, 28)
        else:
            c.gradient_v((6, 12, 30, 255), (14, 24, 52, 255), 0, 28)
    else:
        if shower_active:
            c.gradient_v((28, 46, 74, 255), (44, 68, 102, 255), 0, 28)
        else:
            c.gradient_v((26, 76, 146, 255), (58, 124, 192, 255), 0, 28)

    draw_meadow(c, is_night=(is_night or shower_active))

    if rainbow_active:
        bow_cols = RAINBOW_NIGHT if is_night else RAINBOW_DAY
        rcx, rcy = 43, 27
        for idx, rcol in enumerate(bow_cols):
            rad = 20 - idx
            for x in range(22, WIDTH):
                dx = x - rcx
                rem = rad * rad - dx * dx
                if rem >= 0:
                    y = int(round(rcy - math.sqrt(rem)))
                    if 1 <= y < 28:
                        c.set(x, y, rcol)
        if is_night:
            draw_stars(c, f, dense=False)
            draw_moon(c, 57, 3)
        else:
            draw_sun(c, 57, 5, f)
    elif shower_active:
        draw_storm_canopy(c, f, C["cloud_night"] if is_night else C["cloud_dark"], C["cloud_dark"] if is_night else C["cloud_mid"])
    else:
        if is_night:
            draw_stars(c, f, dense=False)
            draw_moon(c, 57, 3)
        else:
            draw_sun(c, 57, 5, f)

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    sprout_sway = 1 if (f % 30) < 15 else 0

    lumei_x, lumei_y = 20, 12 + bob_lumei
    lulu_x, lulu_y = 44, 13 + bob_lulu
    lumei_mood, lulu_mood = "happy", "chill"
    lumei_walk, lulu_walk = 0, 0

    if 15 <= f < 46:
        lumei_mood, lulu_mood = "startled", "startled"
        if f < 24:
            draw_exclaim(c, lumei_x + 5, lumei_y - 6)
            draw_exclaim(c, lulu_x + 6, lulu_y - 6)
        else:
            t = ease_in_out((f - 24) / 22)
            lumei_x = lerp_i(20, 68, t)
            lulu_x = lerp_i(44, 82, t)
            lumei_walk = 1 if (f % 4 < 2) else 2
            lulu_walk = 2 if (f % 4 < 2) else 1
    elif 46 <= f < 74:
        lumei_x, lulu_x = 70, 82
    elif 74 <= f < 104:
        t = ease_in_out((f - 74) / 28)
        lumei_x = lerp_i(68, 20, t)
        lulu_x = lerp_i(82, 44, t)
        lumei_mood, lulu_mood = "delighted", "happy"
        lumei_walk = 1 if (f % 4 < 2) else 2
        lulu_walk = 2 if (f % 4 < 2) else 1
    elif 104 <= f < 136:
        lumei_mood, lulu_mood = "delighted", "happy"
        lumei_y = 12 - (2 if (f % 8 < 4) else 0)
        lulu_y = 13 - (2 if ((f + 4) % 8 < 4) else 0)
        draw_heart(c, 36, 11 - (f - 104) // 8)

    draw_lumei(c, lumei_x, lumei_y, mood=lumei_mood, sprout_sway=sprout_sway, walk_step=lumei_walk)
    draw_lulu(c, lulu_x, lulu_y, mood=lulu_mood, walk_step=lulu_walk)

    if shower_active:
        for x0, y0, bright in RAIN_DROPS_64:
            rx = wrap_pos(x0, 6, f, WIDTH, direction=-1)
            ry = wrap_pos(y0, 18, f, HEIGHT, direction=1)
            c.set(rx, ry, C["rain_bright"] if bright else C["rain_dim"])
            c.set((rx + 1) % WIDTH, (ry - 1) % HEIGHT, C["rain_dim"])
    return c.img


# ---------------------------------------------------------------------------
# 9. SNOW (Day & Night): Escalating Snowball Fight & Off-Screen Chase!
# ---------------------------------------------------------------------------
def render_snow(f: int, is_night: bool) -> Image.Image:
    c = Canvas()
    if is_night:
        c.gradient_v((6, 12, 30, 255), (14, 26, 52, 255), 0, 28)
        draw_stars(c, f, dense=False)
        draw_moon(c, 55, 3)
        sg, ss = C["snow_night_ground"], C["snow_night_shadow"]
    else:
        c.gradient_v((52, 86, 128, 255), (96, 134, 174, 255), 0, 28)
        sg, ss = C["snow_ground"], C["snow_shadow"]

    c.rect(0, 28, WIDTH, 4, sg)
    c.hline(0, 28, WIDTH, C["snow_bright"])
    c.hline(0, 30, WIDTH, ss)
    c.hline(0, 31, WIDTH, ss)
    c.hline(6, 27, 16, sg)
    c.hline(38, 27, 18, sg)

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    flutter = 1 if (f % 30) >= 15 else 0
    sprout_sway = 1 if (f % 30) < 15 else 0

    lumei_x, lumei_y = 20, 12 + bob_lumei
    lulu_x, lulu_y = 44, 13 + bob_lulu
    lumei_mood = "blink" if (f % 50) in (10, 11) else "happy"
    lulu_mood = "blink" if (f % 50) in (36, 37) else "chill"
    lulu_walk = 0
    lumei_snow, lulu_snow = False, False

    if 22 <= f < 46:
        lulu_mood = "happy"
        if f < 30:
            lulu_y = 14
        elif f < 44:
            t = (f - 30) / 14.0
            sb_x = lerp_i(44, 25, t)
            sb_y = int(round(18 - 7 * math.sin(math.pi * t)))
            c.rect(sb_x, sb_y, 2, 2, C["white"])
            c.set(sb_x + 1, sb_y + 1, C["snow_mid"])
        else:
            lumei_snow, lumei_mood = True, "startled"
            for dx, dy in [(-2, -1), (2, -2), (-1, 2), (3, 1)]:
                c.set(25 + dx, 12 + dy, C["white"])
    elif 46 <= f < 66:
        lumei_snow = f < 52
        lumei_mood = "spicy"
        lumei_y = 12 - (1 if (f % 4 < 2) else 0)
        lulu_mood = "startled" if f >= 56 else "happy"
        if f >= 54:
            c.rect(30, 20, 4, 4, C["white"])
            c.hline(31, 20, 2, C["snow_bright"])
            c.hline(30, 23, 4, C["snow_mid"])
    elif 66 <= f < 102:
        lumei_mood = "spicy" if f < 84 else "delighted"
        lulu_mood = "startled"
        lulu_walk = 1 if (f % 4 < 2) else 2
        if f < 84:
            lulu_x = lerp_i(44, 62, ease_in_out((f - 66) / 18))
            t = (f - 66) / 18.0
            sb_x = lerp_i(31, 62, t)
            sb_y = int(round(19 - 9 * math.sin(math.pi * t)))
            c.rect(sb_x, sb_y, 4, 4, C["white"])
            c.hline(sb_x, sb_y + 3, 4, C["snow_mid"])
        else:
            lulu_x = lerp_i(62, 44, ease_in_out((f - 84) / 18))
            lulu_snow = True
            if f < 90:
                for dx, dy in [(-3, -2), (4, -3), (-2, 3), (5, 2), (1, -4)]:
                    c.set(min(62, lulu_x + 5 + dx), 14 + dy, C["white"])
    elif 102 <= f < 128:
        lulu_snow = f < 116
        lumei_mood, lulu_mood = "delighted", "happy"
        lumei_y = 12 - (2 if (f % 8 < 4) else 0)
        lulu_y = 13 - (1 if ((f + 4) % 8 < 4) else 0)

    draw_lumei(c, lumei_x, lumei_y, mood=lumei_mood, scarf=True, scarf_flutter=flutter, sprout_sway=sprout_sway, snow_on_bonnet=lumei_snow)
    draw_lulu(c, lulu_x, lulu_y, mood=lulu_mood, scarf=True, scarf_flutter=1 - flutter, walk_step=lulu_walk, snow_on_head=lulu_snow)
    if 48 <= f < 66:
        draw_anger_steam(c, lumei_x + 4, lumei_y - 4, f)
    elif 104 <= f < 122:
        draw_heart(c, 36, 12 - (f - 104) // 5)

    for x0, y0, phase, is_big in SNOW_FLAKES_64:
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
# 10. THUNDERSTORM (Day & Night): Overconfident Lulu Leaps Under Blanket!
# ---------------------------------------------------------------------------
def render_thunderstorm(f: int, is_night: bool) -> Image.Image:
    flash_1 = f in (30, 31, 34)
    flash_2 = f in (80, 81, 84)
    is_flashing = flash_1 or flash_2
    shiver_1 = 30 <= f <= 44
    shiver_2 = 80 <= f <= 94

    c = Canvas()
    if is_flashing:
        c.gradient_v((86, 98, 134, 255), (50, 62, 96, 255), 0, 29)
    elif is_night:
        c.gradient_v((5, 7, 16, 255), (12, 16, 32, 255), 0, 29)
    else:
        c.gradient_v((36, 40, 62, 255), (56, 62, 88, 255), 0, 29)

    c.rect(0, 29, WIDTH, 3, (12, 18, 32, 255) if is_night else (28, 36, 52, 255))
    cloud_top = (92, 106, 142, 255) if is_flashing else (C["cloud_night"] if is_night else C["cloud_dark"])
    cloud_bot = (132, 148, 186, 255) if is_flashing else (C["cloud_dark"] if is_night else C["cloud_mid"])
    draw_storm_canopy(c, f, cloud_top, cloud_bot)

    if flash_1:
        for bx, by in [(50, 4), (49, 5), (48, 6), (49, 7), (50, 8), (49, 9), (48, 10), (47, 11), (48, 12)]:
            c.set(bx - 1, by, C["bolt_glow"])
            c.set(bx + 1, by, C["bolt_glow"])
            c.set(bx, by, C["bolt_core"])
    elif flash_2:
        for bx, by in [(29, 4), (30, 5), (31, 6), (30, 7), (29, 8), (30, 9), (31, 10), (30, 11)]:
            c.set(bx - 1, by, C["bolt_glow"])
            c.set(bx + 1, by, C["bolt_glow"])
            c.set(bx, by, C["bolt_core"])

    for x0, y0, bright in RAIN_DROPS_64:
        rx = wrap_pos(x0, 5, f, WIDTH, direction=-1)
        ry = wrap_pos(y0, 15, f, HEIGHT, direction=1)
        c.set(rx, ry, C["rain_bright"] if (bright or is_flashing) else C["rain_dim"])
        c.set((rx + 1) % WIDTH, (ry - 1) % HEIGHT, C["rain_dim"])

    bob = bob_offset(f, period=30, phase=0)
    shiver = (1 if (f % 2 == 0) else 0) if (shiver_1 or shiver_2) else 0

    lumei_x, lumei_y = 20 + shiver, 13 + (1 if (shiver_1 or shiver_2) else bob)
    lumei_mood = "startled" if (shiver_1 or shiver_2) else ("blink" if (f % 50) in (14, 15) else "happy")

    lulu_x, lulu_y = 45, 13 + bob
    lulu_mood = "chill"
    lulu_under = False
    blanket_w = 15
    orange_pop = 0

    if 30 <= f < 46:
        lulu_mood = "startled"
        t = (f - 30) / 16.0
        lulu_x = lerp_i(45, 33, ease_in_out(t))
        lulu_y = 13 - int(round(6 * math.sin(math.pi * t)))
        orange_pop = -2 if f < 38 else 0
        lulu_under = f >= 40
        blanket_w = lerp_i(15, 29, ease_in_out(max(0.0, (f - 36) / 8)))
    elif 46 <= f < 104:
        lulu_under = True
        blanket_w = 29
        lulu_x = 33 + shiver
        lulu_y = 14 + (1 if shiver_2 else bob)
        lulu_mood = "startled" if shiver_2 else "squint"
        if 56 <= f < 74:
            lumei_mood = "delighted"
            draw_heart(c, 32, 11 - (f - 56) // 6)
    elif 104 <= f < 130:
        t = ease_in_out((f - 104) / 24)
        lulu_x = lerp_i(33, 45, t)
        blanket_w = lerp_i(29, 15, t)
        lulu_under = f < 114
        lulu_mood = "chill"
        lumei_mood = "delighted" if f < 122 else "happy"

    draw_lumei(c, lumei_x, lumei_y, mood=lumei_mood)
    draw_lulu(c, lulu_x, lulu_y + orange_pop, mood=lulu_mood)

    top_y = lumei_y + 9
    bx0 = 19 + shiver
    c.hline(bx0 + 1, top_y, max(4, blanket_w - 2), C["blanket_hi"])
    c.rect(bx0, top_y + 1, blanket_w, max(1, 29 - (top_y + 1)), C["blanket_main"])
    c.vline(bx0, top_y + 1, max(1, 29 - (top_y + 1)), C["blanket_dark"])
    c.vline(bx0 + blanket_w - 1, top_y + 1, max(1, 29 - (top_y + 1)), C["blanket_dark"])
    c.hline(bx0, 28, blanket_w, C["blanket_dark"])
    for sx, sy in [(bx0 + 4, top_y + 2), (bx0 + 10, top_y + 4), (bx0 + 18, top_y + 2), (bx0 + 24, top_y + 4)]:
        if sx < bx0 + blanket_w - 1 and sy < 28:
            c.set(sx, sy, C["blanket_star"])

    if not lulu_under:
        draw_lulu(c, lulu_x, lulu_y + orange_pop, mood=lulu_mood)
    return c.img


# ---------------------------------------------------------------------------
# 11. THUNDERSTORM + HAIL (Day & Night): Bouncing Hailstone Shield Scramble!
# ---------------------------------------------------------------------------
def render_thunderstorm_hail(f: int, is_night: bool) -> Image.Image:
    flash = f in (42, 43, 106, 107)
    c = Canvas()
    if flash:
        c.gradient_v((86, 98, 134, 255), (50, 62, 96, 255), 0, 29)
    elif is_night:
        c.gradient_v((6, 10, 22, 255), (14, 22, 42, 255), 0, 29)
    else:
        c.gradient_v((36, 52, 72, 255), (56, 78, 102, 255), 0, 29)

    c.rect(0, 29, WIDTH, 3, (14, 22, 38, 255) if is_night else (34, 48, 68, 255))
    c.hline(0, 29, WIDTH, (42, 60, 88, 255) if is_night else (68, 92, 120, 255))
    draw_storm_canopy(
        c, f,
        (92, 106, 142, 255) if flash else (C["cloud_night"] if is_night else C["cloud_dark"]),
        (132, 148, 186, 255) if flash else (C["cloud_dark"] if is_night else C["cloud_mid"]),
    )

    if flash:
        bx_start = 52 if f < 60 else 28
        for i in range(8):
            bx = bx_start + (1 if i % 2 else -1)
            by = 4 + i
            c.set(bx - 1, by, C["bolt_glow"])
            c.set(bx + 1, by, C["bolt_glow"])
            c.set(bx, by, C["bolt_core"])

    bob = bob_offset(f, period=30, phase=0)
    lumei_x, lumei_y = 21, 13 + bob
    lulu_x, lulu_y = 36, 14 + bob
    shield_cx, shield_y = 34, 6 + bob
    shield_up = True
    lumei_mood, lulu_mood = "squint", "chill"
    orange_pop = 0

    if 24 <= f < 46:
        shield_up = f >= 38
        lulu_x = lerp_i(36, 45, ease_in_out((f - 24) / 10)) if f < 34 else lerp_i(45, 36, ease_in_out((f - 34) / 10))
        if 32 <= f < 40:
            lulu_mood, orange_pop = "startled", -2
            draw_exclaim(c, lulu_x + 6, lulu_y - 7)
        lumei_mood = "spicy"
    elif 46 <= f < 118:
        shield_up = True
        lumei_x, lulu_x, shield_cx = 22, 35, 34
        lumei_mood = "startled" if flash else "happy"
        lulu_mood = "startled" if flash else "squint"
        if 70 <= f < 94:
            lumei_mood, lulu_mood = "delighted", "happy"
            draw_heart(c, 34, 13 - (f - 70) // 6)

    draw_lumei(c, lumei_x, lumei_y, mood=lumei_mood)
    draw_lulu(c, lulu_x, lulu_y + orange_pop, mood=lulu_mood)
    if shield_up:
        draw_hail_shield(c, shield_cx, shield_y)

    for x0, y0 in HAIL_STONES_64:
        hx = wrap_pos(x0, 4, f, WIDTH, direction=-1)
        hy = wrap_pos(y0, 15, f, HEIGHT, direction=1)
        if shield_up and (shield_cx - 11) <= hx <= (shield_cx + 11) and hy >= shield_y + 2:
            if hy <= shield_y + 6:
                c.set(hx, shield_y - 2, C["white"])
                c.set((hx + 2) % WIDTH, shield_y - 1, C["hail_rim"])
            continue
        c.rect(hx, hy, 2, 2, C["hail_core"])
        c.set(hx + 1, hy + 1, C["hail_rim"])
        if hy >= 27:
            c.set((hx - 1) % WIDTH, 26, C["white"])
            c.set((hx + 2) % WIDTH, 26, C["hail_rim"])
    return c.img


# ---------------------------------------------------------------------------
# 12. WINDY (Day & Night): Mega Gust Blows Lulu OFF-SCREEN & Lumei Rescues Him!
# ---------------------------------------------------------------------------
def render_windy(f: int, is_night: bool) -> Image.Image:
    c = Canvas()
    if is_night:
        c.gradient_v((6, 14, 28, 255), (12, 26, 44, 255), 0, 28)
        draw_stars(c, f, dense=False)
        draw_moon(c, 55, 3)
    else:
        c.gradient_v((26, 72, 114, 255), (56, 118, 152, 255), 0, 28)
        draw_sun(c, 55, 5, f)

    draw_meadow(c, is_night=is_night)

    gust_heavy = 22 <= f <= 74
    for row_y, offset, length in [(4, 0, 11), (10, 18, 13), (17, 34, 10), (24, 10, 12)]:
        wx = wrap_pos(offset, 15, f, WIDTH, direction=1)
        extra = 4 if gust_heavy else 0
        for dx in range(length + extra):
            col = C["wind_streak"] if dx >= length - 3 else C["wind_dim"]
            c.set((wx + dx) % WIDTH, row_y, col)

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=10)

    lumei_x, lumei_y = 20, 12 + bob_lumei
    lulu_x, lulu_y = 44, 13 + bob_lulu
    lumei_mood, lulu_mood = "squint", "squint"
    lumei_lean, lulu_lean = 1, 1
    lumei_walk, lulu_walk = 0, 0
    lulu_has_tang = True
    loose_tang: Optional[Tuple[int, int]] = None
    orange_jiggle = 1 if (f % 15) < 7 else 0

    if 24 <= f < 46:
        lulu_has_tang = False
        t = ease_in_out((f - 24) / 22)
        lulu_x = lerp_i(44, 68, t)
        lulu_y = 13 - int(round(6 * math.sin(math.pi * t)))
        lulu_mood = "startled" if f < 34 else "dizzy"
        lulu_walk = 1 if (f % 4 < 2) else 2
        tx = lerp_i(49, 70, ease_in_out((f - 24) / 14))
        ty = 11 - int(round(4 * math.sin(math.pi * min(1.0, (f - 24) / 14))))
        loose_tang = (tx, ty)
        lumei_mood = "startled"
        lumei_x = lerp_i(20, 26, ease_in_out((f - 24) / 22))
    elif 46 <= f < 64:
        lulu_x, lulu_has_tang = 70, False
        if f < 52:
            lumei_x, lumei_mood = 26, "startled"
            draw_exclaim(c, lumei_x + 5, lumei_y - 6)
        else:
            lumei_x = lerp_i(26, 68, ease_in_out((f - 52) / 12))
            lumei_mood = "spicy"
            lumei_walk = 1 if (f % 4 < 2) else 2
    elif 64 <= f < 76:
        lumei_x, lulu_x, lulu_has_tang = 70, 70, False
    elif 76 <= f < 114:
        t = ease_in_out((f - 76) / 36)
        lumei_x = lerp_i(66, 20, t)
        lulu_x = lerp_i(82, 44, t)
        lumei_mood = "spicy"
        lulu_mood = "dizzy" if f < 104 else "chill"
        lumei_lean, lulu_lean = 0, 0
        lumei_walk = 1 if (f % 4 < 2) else 2
        lulu_walk = 2 if (f % 4 < 2) else 1
        lulu_has_tang = f >= 106
        if not lulu_has_tang:
            rt = ease_in_out(max(0.0, (f - 86) / 20))
            loose_tang = (lerp_i(66, 49, rt), lerp_i(25, 11, rt) - int(round(3 * math.sin(math.pi * rt))))
    elif 114 <= f < 134:
        lumei_mood = "spicy"
        lulu_mood = "blink" if f < 122 else "chill"
        lumei_lean, lulu_lean = 0, 0
        draw_anger_steam(c, lumei_x + 5, lumei_y - 4, f)

    draw_lumei(c, lumei_x, lumei_y, mood=lumei_mood, lean_x=lumei_lean, sprout_sway=1, walk_step=lumei_walk)
    draw_lulu(c, lulu_x, lulu_y, mood=lulu_mood, lean_x=lulu_lean, orange_shift=orange_jiggle, has_tangerine=lulu_has_tang, walk_step=lulu_walk)
    if loose_tang is not None:
        draw_tangerine(c, loose_tang[0], loose_tang[1])

    spin = (f // 3) % 2
    for x0, y0, phase, col_key in WIND_LEAVES_64:
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
# 24-State Renderer Registry (12 Weather Types x Day & Night)
# ---------------------------------------------------------------------------
SCENE_RENDERERS: Dict[str, Callable[[int], Image.Image]] = {
    "clear_day": render_clear_day,
    "clear_night": render_clear_night,
    "partly_cloudy_day": lambda f: render_partly_cloudy(f, is_night=False),
    "partly_cloudy_night": lambda f: render_partly_cloudy(f, is_night=True),
    "overcast_day": lambda f: render_overcast(f, is_night=False),
    "overcast_night": lambda f: render_overcast(f, is_night=True),
    "fog_day": lambda f: render_fog(f, is_night=False),
    "fog_night": lambda f: render_fog(f, is_night=True),
    "drizzle_day": lambda f: render_drizzle(f, is_night=False),
    "drizzle_night": lambda f: render_drizzle(f, is_night=True),
    "freezing_rain_day": lambda f: render_freezing_rain(f, is_night=False),
    "freezing_rain_night": lambda f: render_freezing_rain(f, is_night=True),
    "rain_day": lambda f: render_rain(f, is_night=False),
    "rain_night": lambda f: render_rain(f, is_night=True),
    "rain_showers_day": lambda f: render_rain_showers(f, is_night=False),
    "rain_showers_night": lambda f: render_rain_showers(f, is_night=True),
    "snow_day": lambda f: render_snow(f, is_night=False),
    "snow_night": lambda f: render_snow(f, is_night=True),
    "thunderstorm_day": lambda f: render_thunderstorm(f, is_night=False),
    "thunderstorm_night": lambda f: render_thunderstorm(f, is_night=True),
    "thunderstorm_hail_day": lambda f: render_thunderstorm_hail(f, is_night=False),
    "thunderstorm_hail_night": lambda f: render_thunderstorm_hail(f, is_night=True),
    "windy_day": lambda f: render_windy(f, is_night=False),
    "windy_night": lambda f: render_windy(f, is_night=True),
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
    elif sheet_path.exists():
        with Image.open(sheet_path) as sheet:
            sheet = sheet.convert("RGBA")
            count = max(1, sheet.width // WIDTH)
            for idx in range(count):
                tile = sheet.crop((idx * WIDTH, 0, (idx + 1) * WIDTH, sheet.height))
                raw_frames.append(tile.resize((WIDTH, HEIGHT), Image.Resampling.NEAREST))
    elif folder_path.is_dir():
        pngs = sorted(folder_path.glob("*.png"))
        for p in pngs:
            with Image.open(p) as im:
                raw_frames.append(im.convert("RGBA").resize((WIDTH, HEIGHT), Image.Resampling.NEAREST))

    if not raw_frames:
        return None
    if len(raw_frames) == NUM_FRAMES:
        return raw_frames
    if NUM_FRAMES % len(raw_frames) == 0:
        return (raw_frames * (NUM_FRAMES // len(raw_frames)))[:NUM_FRAMES]
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

    strip = Image.new("RGB", (WIDTH * min(len(frames), 25), HEIGHT))
    for idx in range(min(len(frames), 25)):
        strip.paste(frames[idx].convert("RGB"), (idx * WIDTH, 0))
    return strip.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)


def enforce_constant_frame_rate(frames: List[Image.Image]) -> List[Image.Image]:
    assert NUM_FRAMES % 2 == 0
    out: List[Image.Image] = []
    for idx, im in enumerate(frames):
        copy = im.copy()
        if idx % 2 == 1:
            r, g, b, a = copy.getpixel((WIDTH - 1, HEIGHT - 1))
            b_adj = b + 8 if b <= 247 else b - 8
            copy.putpixel((WIDTH - 1, HEIGHT - 1), (r, g, b_adj, a))
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


def build_contact_sheet(state_frames: Dict[str, List[Image.Image]], scale: int = 3) -> Path:
    """Side-by-side Day vs Night storyboard sheet for all 12 weather types."""
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    sample_indices = [0, 62, 116]
    pad = 6
    label_h = 14
    cell_w = WIDTH * scale
    cell_h = HEIGHT * scale
    cols = len(sample_indices) * 2  # 3 day frames + 3 night frames per row
    sheet_w = pad + cols * (cell_w + pad)
    sheet_h = pad + len(WEATHER_TYPES) * (cell_h + label_h + pad)

    sheet = Image.new("RGB", (sheet_w, sheet_h), (14, 16, 24))
    draw = ImageDraw.Draw(sheet)

    for row, wtype in enumerate(WEATHER_TYPES):
        y_top = pad + row * (cell_h + label_h + pad)
        col = 0
        for tod in ("day", "night"):
            st = f"{wtype}_{tod}"
            for f_idx in sample_indices:
                x_left = pad + col * (cell_w + pad)
                draw.text((x_left, y_top), f"{st} f={f_idx}", fill=(220, 228, 240))
                upscaled = state_frames[st][f_idx].convert("RGB").resize(
                    (cell_w, cell_h), Image.Resampling.NEAREST
                )
                sheet.paste(upscaled, (x_left, y_top + label_h))
                col += 1

    out_path = PREVIEWS_DIR / "all_states_contact_sheet.png"
    sheet.save(out_path)
    return out_path


def inject_sprites_into_star(b64_map: Dict[str, str], star_path: Path) -> None:
    if not star_path.exists():
        print(f"Note: {star_path} does not exist yet; skipping Starlark injection.")
        return

    text = star_path.read_text(encoding="utf-8")
    if SPRITE_BEGIN_MARKER not in text or SPRITE_END_MARKER not in text:
        raise RuntimeError(f"Markers not found in {star_path}.")

    lines = [
        SPRITE_BEGIN_MARKER,
        f"SPRITE_WIDTH = {WIDTH}",
        f"SPRITE_HEIGHT = {HEIGHT}",
        f"SPRITE_FRAME_COUNT = {NUM_FRAMES}",
        f"SPRITE_DELAY_MS = {FRAME_DELAY_MS}",
        "SPRITES_B64 = {",
    ]
    for state in STATES:
        lines.append(f'    "{state}": "{b64_map[state]}",')
    lines.append("}")
    lines.append(SPRITE_END_MARKER)

    replacement = "\n".join(lines)
    pattern = re.compile(
        re.escape(SPRITE_BEGIN_MARKER) + r".*?" + re.escape(SPRITE_END_MARKER),
        re.DOTALL,
    )
    star_path.write_text(pattern.sub(replacement, text, count=1), encoding="utf-8")
    print(f"Injected {len(b64_map)} base64-encoded {WIDTH}x{HEIGHT} animated GIFs into {star_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate 24 day/night 15-second seamless 64x32 sprites for Capybara Clock."
    )
    parser.add_argument("--no-inject", action="store_true")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)

    # Remove old non-day/night asset filenames if present
    valid_names = {f"{s}{ext}" for s in STATES for ext in (".gif", ".webp")}
    for existing in list(ASSETS_DIR.glob("*.gif")) + list(ASSETS_DIR.glob("*.webp")):
        if existing.name not in valid_names:
            existing.unlink()

    print(
        f"Generating {len(STATES)} day/night weather sprites "
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
        b64_map[state] = base64.b64encode(gif_bytes).decode("ascii")
        print(
            f"  [OK] {state:23s} | GIF: {len(gif_bytes):6d} B | "
            f"WebP: {webp_size:6d} B | seamless=verified"
        )

    if args.preview:
        sheet = build_contact_sheet(all_frames)
        print(f"Saved preview contact sheet -> {sheet}")

    if not args.no_inject:
        inject_sprites_into_star(b64_map, STAR_FILE)


if __name__ == "__main__":
    main()
