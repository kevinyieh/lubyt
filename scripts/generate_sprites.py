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
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

from holiday_sprites import HOLIDAY_STATES, build_holiday_renderers

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

# Weather types whose activities depend strongly on temperature (< 55°F cold vs >= 55°F warm)
TEMP_AWARE_WEATHERS = ("clear", "partly_cloudy")


def _build_state_list() -> Tuple[str, ...]:
    out: List[str] = []
    for w in WEATHER_TYPES:
        for tod in ("day", "night"):
            if w in TEMP_AWARE_WEATHERS:
                out.append(f"{w}_{tod}_warm")
                out.append(f"{w}_{tod}_cold")
            else:
                out.append(f"{w}_{tod}")
    out.extend(HOLIDAY_STATES)
    return tuple(out)


STATES = _build_state_list()

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
    "bonnet_ruffle": (255, 244, 244, 255),
    "bonnet_pink": (246, 208, 214, 255),
    "bonnet_shade": (218, 168, 178, 255),
    "bonnet_dot": (228, 174, 186, 255),
    "ribbon": (248, 148, 174, 255),
    "romper_hi": (254, 218, 224, 255),
    "romper_main": (244, 176, 190, 255),
    "romper_shade": (208, 128, 148, 255),
    # Ice cream, boats, kite & fireflies (Batch 1 high-res props)
    "cone_tan": (214, 152, 78, 255),
    "cone_dark": (162, 106, 48, 255),
    "scoop_pink": (255, 142, 178, 255),
    "scoop_cream": (255, 244, 212, 255),
    "scoop_mint": (122, 236, 188, 255),
    "firefly": (255, 244, 128, 255),
    "candle_wax": (255, 250, 240, 255),
    "flame_hi": (255, 242, 112, 255),
    "flame_org": (255, 138, 32, 255),
    "kite_red": (246, 62, 78, 255),
    "kite_gold": (255, 216, 68, 255),
    "kite_string": (216, 226, 242, 255),
    "boat_white": (246, 250, 255, 255),
    "boat_shade": (176, 196, 222, 255),
    "boat_pink": (255, 164, 196, 255),
    "boat_pink_d": (214, 112, 152, 255),
    # Hot cocoa, campfire & warm winter buns (Cold variants)
    "mug_red": (224, 64, 72, 255),
    "mug_teal": (44, 178, 176, 255),
    "cocoa": (112, 58, 28, 255),
    "marshmallow": (255, 250, 244, 255),
    "log_wood": (122, 68, 34, 255),
    "log_dark": (78, 40, 18, 255),
    "fire_red": (244, 78, 34, 255),
    "fire_org": (255, 152, 36, 255),
    "fire_yel": (255, 238, 112, 255),
    "bun_hi": (255, 236, 188, 255),
    "bun_mid": (236, 192, 124, 255),
    "pie_crust": (218, 146, 62, 255),
    "pie_fill": (216, 56, 68, 255),
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


def draw_tangerine_hi(c: Canvas, tx: int, ty: int) -> None:
    """High-res plump 5x3 tangerine with bright highlight & green stem."""
    c.set(tx + 2, ty - 1, C["stem_green"])
    c.hline(tx + 1, ty, 3, C["orange_main"])
    c.set(tx + 1, ty, C["orange_hi"])
    c.hline(tx, ty + 1, 5, C["orange_main"])
    c.set(tx + 1, ty + 1, C["orange_hi"])
    c.hline(tx + 1, ty + 2, 3, C["orange_dark"])


def draw_loose_bonnet(c: Canvas, bx: int, by: int) -> None:
    """Lumei's detached pale-pink ruffled bonnet + halo + sprout flying in the wind!"""
    cx = bx + 5
    c.set(cx - 1, by - 3, C["sprout_hi"])
    c.set(cx + 1, by - 3, C["sprout_hi"])
    c.set(cx, by - 2, C["sprout_green"])
    c.hline(cx - 2, by - 1, 5, C["halo_cream"])
    c.set(cx, by - 1, C["orange_main"])
    c.hline(bx + 2, by, 7, C["bonnet_pink"])
    c.rect(bx + 1, by + 1, 9, 4, C["bonnet_pink"])
    c.set(bx + 3, by + 1, C["bonnet_dot"])
    c.set(bx + 7, by + 1, C["bonnet_dot"])
    c.hline(bx + 1, by + 4, 9, C["bonnet_ruffle"])
    c.set(bx + 1, by + 5, C["ribbon"])


def draw_ice_cream(c: Canvas, ix: int, iy: int, scoops: int = 1, scoop_col: RGBA = C["scoop_pink"]) -> None:
    """Crisp pixel ice cream cone (scoops=1 single, 3=giant triple scoop, 0=empty cone)."""
    # Waffle cone
    c.hline(ix, iy + 3, 3, C["cone_tan"])
    c.set(ix + 2, iy + 3, C["cone_dark"])
    c.hline(ix + 1, iy + 4, 2, C["cone_tan"])
    c.set(ix + 1, iy + 5, C["cone_dark"])
    if scoops >= 1:
        c.rect(ix, iy + 1, 3, 2, scoop_col)
        c.set(ix + 1, iy, scoop_col)
        c.set(ix, iy + 1, C["white"])
    if scoops >= 3:
        c.rect(ix, iy - 1, 3, 2, C["scoop_cream"])
        c.rect(ix, iy - 3, 3, 2, C["scoop_mint"])
        c.set(ix + 1, iy - 4, C["cherry"])


def draw_candle_cupcake(c: Canvas, cx: int, cy: int, f: int) -> None:
    """Night-picnic peace-offering frosted cupcake with flickering candle flame!"""
    c.hline(cx, cy + 4, 7, C["plate"])
    c.rect(cx + 1, cy + 2, 5, 2, C["cake_sponge"])
    c.hline(cx + 1, cy + 1, 5, C["cake_pink"])
    c.hline(cx + 2, cy, 3, C["cake_cream"])
    # Little candle + flickering flame + warm halo
    c.vline(cx + 3, cy - 2, 2, C["candle_wax"])
    flicker = 1 if (f % 4 < 2) else 0
    for dy in range(-4, 0):
        for dx in range(1, 6):
            c.set(cx + dx, cy + dy, C["lantern_glow"])
    c.set(cx + 3, cy - 3, C["flame_org"])
    c.set(cx + 3 + flicker - 1, cy - 4, C["flame_hi"])


def draw_paper_boat(c: Canvas, bx: int, by: int, pink: bool = False) -> None:
    """Cute pixel origami paper boat floating on a puddle."""
    hi = C["boat_pink"] if pink else C["boat_white"]
    lo = C["boat_pink_d"] if pink else C["boat_shade"]
    c.set(bx + 3, by, hi)
    c.hline(bx + 2, by + 1, 3, hi)
    c.hline(bx, by + 2, 7, hi)
    c.hline(bx + 1, by + 3, 5, lo)


def draw_kite(c: Canvas, kx: int, ky: int, f: int) -> None:
    """Bright diamond kite with fluttering ribbon tail."""
    c.set(kx + 2, ky, C["kite_red"])
    c.hline(kx + 1, ky + 1, 3, C["kite_red"])
    c.set(kx + 2, ky + 1, C["kite_gold"])
    c.hline(kx, ky + 2, 5, C["kite_gold"])
    c.set(kx + 2, ky + 2, C["kite_red"])
    c.hline(kx + 1, ky + 3, 3, C["kite_red"])
    c.set(kx + 2, ky + 4, C["kite_gold"])
    # Fluttering tail
    wob = 1 if (f % 6 < 3) else 0
    c.set(kx + 1, ky + 5, C["kite_string"])
    c.set(kx - 1, ky + 6 + wob, C["kite_red"])
    c.set(kx - 3, ky + 7 - wob, C["kite_gold"])


def draw_cocoa_mug(c: Canvas, mx: int, my: int, f: int, *, giant: bool = False, marshmallows: int = 2, mug_col: RGBA = C["mug_red"]) -> None:
    """Steaming hot cocoa mug with optional fluffy white marshmallows."""
    if giant:
        c.rect(mx, my + 1, 6, 4, mug_col)
        c.vline(mx + 6, my + 2, 2, mug_col)  # handle
        c.hline(mx + 1, my + 1, 4, C["cocoa"])
        # Big whipped cream mound + marshmallows
        c.hline(mx + 1, my, 4, C["marshmallow"])
        c.hline(mx + 2, my - 1, 2, C["white"])
        c.set(mx + 3, my - 2, C["cherry"])
    else:
        c.rect(mx, my + 1, 4, 3, mug_col)
        c.set(mx + 4, my + 2, mug_col)
        c.hline(mx + 1, my + 1, 2, C["cocoa"])
        if marshmallows >= 1:
            c.set(mx + 1, my, C["marshmallow"])
        if marshmallows >= 2:
            c.set(mx + 2, my, C["white"])
    # Rising gentle steam wisp (period 15 -> 10 exact cycles)
    st = (f // 3) % 5
    c.set(mx + (2 if giant else 1), my - 2 - (st % 2), C["steam_dim"])
    if st < 3:
        c.set(mx + (3 if giant else 2), my - 3 - (st % 2), C["steam"])


def draw_campfire(c: Canvas, fx: int, fy: int, f: int) -> None:
    """Crackling warm pixel campfire with animated flames & embers (period 10)."""
    # Warm glow halo on grass & air
    for dy in range(-3, 4):
        for dx in range(-4, 9):
            if abs(dx - 2) + abs(dy) <= 6:
                c.set(fx + dx, fy + dy, C["lantern_glow"])
    # Crossed wooden logs
    c.hline(fx, fy + 2, 6, C["log_wood"])
    c.hline(fx + 1, fy + 3, 4, C["log_dark"])
    # Flickering layered pixel flames (period 10 divides 150)
    ph = (f // 2) % 5
    c.rect(fx + 1, fy, 4, 2, C["fire_red"])
    c.hline(fx + 1, fy + 1, 4, C["fire_org"])
    c.hline(fx + 2, fy, 2, C["fire_yel"])
    tip_x = fx + 2 + (1 if ph in (1, 3) else 0)
    c.set(tip_x, fy - 1, C["fire_org"])
    c.set(tip_x, fy - 2, C["fire_yel"])
    # Rising glowing ember
    ember_y = fy - 3 - ph
    c.set(fx + 1 + (ph % 3), ember_y, C["fire_org"] if ph < 3 else C["fire_yel"])


def draw_steaming_buns(c: Canvas, px: int, py: int, f: int, stage: int) -> None:
    """Warm wooden steamer basket piled with hot fluffy buns (Cold Picnic)."""
    c.rect(px, py + 2, 7, 2, C["basket_main"])
    c.hline(px, py + 3, 7, C["basket_dark"])
    if stage == 0:
        c.hline(px + 1, py + 1, 5, C["bun_mid"])
        c.hline(px + 1, py, 2, C["bun_hi"])
        c.hline(px + 4, py, 2, C["bun_hi"])
        c.set(px + 3, py - 1, C["white"])
    elif stage == 1:
        c.hline(px + 2, py + 1, 3, C["bun_hi"])
    # Rising warm steam while buns are present
    if stage < 2:
        st = (f // 3) % 5
        c.set(px + 2, py - 2 - (st % 2), C["steam_dim"])
        c.set(px + 4, py - 1 - ((st + 1) % 2), C["steam"])


def draw_warm_pie(c: Canvas, cx: int, cy: int, f: int) -> None:
    """Steaming golden berry pie peace offering (Cold Picnic)."""
    c.hline(cx, cy + 4, 7, C["plate"])
    c.rect(cx + 1, cy + 2, 5, 2, C["pie_crust"])
    c.hline(cx + 1, cy + 1, 5, C["pie_fill"])
    c.set(cx + 2, cy + 1, C["pie_crust"])
    c.set(cx + 4, cy + 1, C["pie_crust"])
    st = (f // 3) % 5
    c.set(cx + 2, cy - 1 - (st % 2), C["steam"])
    c.set(cx + 4, cy - 2 - ((st + 1) % 2), C["steam_dim"])


def draw_lumei_hi(
    c: Canvas,
    ox: int,
    oy: int,
    *,
    mood: str = "happy",  # "happy", "blink", "spicy", "startled", "squint", "delighted", "chomp", "guilty"
    sunglasses: bool = False,
    glint_x: int = -1,
    has_bonnet: bool = True,
    scarf: bool = False,
    scarf_flutter: int = 0,
    snow_on_bonnet: bool = False,
    lean_x: int = 0,
    sprout_sway: int = 0,
    walk_step: int = 0,
) -> None:
    """
    High-res Lumei (~16w x 25h, from sprout oy-4 to feet oy+21).
    Supports detached bonnet (for windy_night bonnet rescue!).
    """
    hx = ox + lean_x
    bx = ox

    if has_bonnet:
        # Slimmer, sleeker bonnet & compact twin-leaf sprout + cream halo ring
        cx = hx + 7
        c.set(cx - 2 + sprout_sway, oy - 2, C["sprout_hi"])
        c.set(cx - 1 + sprout_sway, oy - 2, C["sprout_hi"])
        c.set(cx + 1 + sprout_sway, oy - 2, C["sprout_hi"])
        c.set(cx + 2 + sprout_sway, oy - 2, C["sprout_hi"])
        c.set(cx + sprout_sway, oy - 1, C["sprout_green"])
        # Cream halo ring + tiny orange nub seated tightly on bonnet crown
        c.hline(cx - 2, oy, 5, C["halo_cream"])
        c.set(cx - 2, oy, C["halo_shade"])
        c.set(cx + 2, oy, C["halo_shade"])
        c.set(cx, oy, C["orange_main"])
        c.hline(cx - 1, oy + 1, 3, C["orange_dark"])

        # Sleeker pale blush-pink dotted bonnet hugging her head closely
        c.hline(hx + 3, oy + 1, 9, C["bonnet_pink"])
        c.hline(cx - 1, oy + 1, 3, C["orange_dark"])
        c.rect(hx + 2, oy + 2, 11, 3, C["bonnet_pink"])
        c.rect(hx + 1, oy + 4, 3, 7, C["bonnet_pink"])
        c.vline(hx + 1, oy + 5, 5, C["bonnet_shade"])
        for dx, dy in [(4, 1), (9, 1), (3, 3), (11, 3), (2, 7)]:
            c.set(hx + dx, oy + dy, C["bonnet_dot"])
        c.set(hx + 1, oy + 6, C["ribbon"])
        c.set(hx + 2, oy + 6, C["ribbon"])
        c.set(hx + 1, oy + 7, C["ribbon"])
        # Crisp tight scalloped white lace ruffle framing her forehead & cheek
        for dx, dy in [
            (4, 3), (6, 3), (8, 3), (10, 3), (12, 3),
            (3, 4), (13, 4), (2, 5), (2, 7), (2, 9), (2, 11),
        ]:
            c.set(hx + dx, oy + dy, C["bonnet_ruffle"])
        # Cute golden ear poking out cleanly on left edge
        c.rect(hx + 1, oy + 3, 3, 3, C["gold_main"])
        c.set(hx + 1, oy + 3, C["gold_hi"])
        c.set(hx + 2, oy + 4, C["gold_dark"])
        if snow_on_bonnet:
            c.hline(hx + 3, oy + 1, 9, C["white"])
            c.hline(hx + 4, oy + 2, 7, C["snow_bright"])
    else:
        # Bare golden head & two adorable round golden ears when bonnet blows off!
        c.rect(hx + 2, oy + 2, 3, 3, C["gold_main"])
        c.set(hx + 2, oy + 2, C["gold_hi"])
        c.set(hx + 3, oy + 3, C["gold_dark"])
        c.rect(hx + 10, oy + 2, 3, 3, C["gold_main"])
        c.set(hx + 11, oy + 2, C["gold_hi"])
        c.set(hx + 11, oy + 3, C["gold_dark"])
        c.hline(hx + 4, oy + 2, 7, C["gold_hi"])

    # Round golden butter-yellow face
    c.hline(hx + 5, oy + 3, 7, C["gold_hi"])
    c.hline(hx + 4, oy + 4, 9, C["gold_hi"])
    c.rect(hx + 3, oy + 5, 11, 6, C["gold_main"])
    c.hline(hx + 3, oy + 11, 11, C["gold_shade"])
    c.hline(hx + 4, oy + 12, 9, C["gold_shade"])
    c.vline(hx + 14, oy + 7, 3, C["gold_main"])
    c.set(hx + 14, oy + 10, C["gold_shade"])

    # Rosy cheeks
    cheek = C["cheek_angry"] if mood in ("spicy", "guilty") else C["cheek_peach"]
    c.rect(hx + 4, oy + 9, 3, 2, cheek)
    c.rect(hx + 12, oy + 9, 2, 2, cheek)

    # Big Expressive Chibi Eyes
    if sunglasses:
        c.hline(hx + 4, oy + 6, 10, C["shades_frame"])
        c.rect(hx + 4, oy + 6, 4, 3, C["shades_lens"])
        c.rect(hx + 10, oy + 6, 4, 3, C["shades_lens"])
        c.hline(hx + 8, oy + 6, 2, C["shades_frame"])
        if 0 <= glint_x <= 9:
            gx = hx + 4 + glint_x
            if hx + 4 <= gx <= hx + 7 or hx + 10 <= gx <= hx + 13:
                c.set(gx, oy + 6, C["shades_glint"])
                c.set(gx, oy + 7, C["shades_glint"])
    elif mood == "spicy":
        c.hline(hx + 5, oy + 5, 2, C["mouth_line"])
        c.set(hx + 7, oy + 6, C["mouth_line"])
        c.rect(hx + 5, oy + 6, 3, 2, C["eye"])
        c.set(hx + 5, oy + 6, C["white"])
        c.hline(hx + 11, oy + 5, 2, C["mouth_line"])
        c.set(hx + 10, oy + 6, C["mouth_line"])
        c.rect(hx + 10, oy + 6, 3, 2, C["eye"])
        c.set(hx + 10, oy + 6, C["white"])
    elif mood == "delighted":
        c.set(hx + 5, oy + 7, C["eye"])
        c.set(hx + 6, oy + 6, C["eye"])
        c.set(hx + 7, oy + 7, C["eye"])
        c.set(hx + 10, oy + 7, C["eye"])
        c.set(hx + 11, oy + 6, C["eye"])
        c.set(hx + 12, oy + 7, C["eye"])
    elif mood == "squint":
        c.hline(hx + 5, oy + 7, 3, C["eye"])
        c.hline(hx + 10, oy + 7, 3, C["eye"])
    elif mood == "blink":
        c.hline(hx + 5, oy + 8, 3, C["eye"])
        c.hline(hx + 10, oy + 8, 3, C["eye"])
    elif mood in ("startled", "guilty"):
        c.rect(hx + 5, oy + 6, 3, 3, C["white"])
        c.rect(hx + 6, oy + 7, 2, 2, C["eye"])
        c.rect(hx + 10, oy + 6, 3, 3, C["white"])
        c.rect(hx + 11, oy + 7, 2, 2, C["eye"])
        if mood == "guilty":
            c.vline(hx + 14, oy + 4, 2, C["tear_blue"])
    else:
        c.rect(hx + 5, oy + 6, 3, 3, C["white"])
        c.rect(hx + 6, oy + 6, 2, 3, C["eye"])
        c.set(hx + 6, oy + 6, C["white"])
        c.rect(hx + 11, oy + 6, 2, 3, C["eye"])
        c.set(hx + 11, oy + 6, C["white"])
        c.set(hx + 11, oy + 7, C["white"])

    # Mouth
    if mood == "spicy":
        c.hline(hx + 8, oy + 10, 3, C["smile_dark"])
        c.set(hx + 9, oy + 9, C["smile_dark"])
    elif mood == "chomp":
        c.rect(hx + 8, oy + 9, 4, 3, C["smile_dark"])
        c.hline(hx + 9, oy + 11, 2, C["smile_tongue"])
    elif mood in ("startled", "guilty"):
        c.rect(hx + 8, oy + 10, 2, 2, C["smile_dark"])
    else:
        c.hline(hx + 8, oy + 9, 4, C["smile_dark"])
        c.hline(hx + 9, oy + 9, 2, C["white"])
        c.hline(hx + 8, oy + 10, 3, C["smile_dark"])
        c.hline(hx + 9, oy + 11, 2, C["smile_tongue"])

    # Puffy Baby-Pink Bloomer Romper
    c.hline(bx + 4, oy + 13, 9, C["romper_hi"])
    c.set(bx + 8, oy + 13, C["romper_shade"])
    c.rect(bx + 3, oy + 14, 10, 2, C["romper_main"])
    c.vline(bx + 3, oy + 14, 2, C["romper_shade"])
    c.rect(bx + 2, oy + 16, 12, 3, C["romper_main"])
    c.hline(bx + 3, oy + 16, 10, C["romper_hi"])
    c.vline(bx + 2, oy + 16, 3, C["romper_shade"])
    c.hline(bx + 3, oy + 19, 10, C["romper_shade"])
    c.hline(bx + 4, oy + 19, 3, C["bonnet_ruffle"])
    c.hline(bx + 9, oy + 19, 3, C["bonnet_ruffle"])

    # Clasped golden paws
    paw_y = oy + 13 if mood == "spicy" else oy + 14
    c.rect(bx + 7, paw_y, 5, 2, C["gold_main"])
    c.hline(bx + 8, paw_y, 3, C["gold_hi"])
    c.set(bx + 9, paw_y + 1, C["gold_shade"])

    # Cozy winter knit scarf (teal & mint stripes!)
    if scarf:
        c.rect(bx + 3, oy + 13, 10, 2, C["scarf_teal"])
        for sx in (5, 9):
            c.vline(bx + sx, oy + 13, 2, C["scarf_mint"])
        c.rect(bx, oy + 14 + scarf_flutter, 3, 3, C["scarf_teal"])
        c.hline(bx, oy + 15 + scarf_flutter, 3, C["scarf_mint"])

    # Standing / walking yellow feet
    l_dy = -1 if walk_step == 1 else 0
    r_dy = -1 if walk_step == 2 else 0
    c.rect(bx + 4, oy + 20 + l_dy, 3, 2, C["gold_main"])
    c.hline(bx + 4, oy + 21 + l_dy, 3, C["gold_shade"])
    c.rect(bx + 9, oy + 20 + r_dy, 3, 2, C["gold_main"])
    c.hline(bx + 9, oy + 21 + r_dy, 3, C["gold_shade"])


def draw_lulu_hi(
    c: Canvas,
    ox: int,
    oy: int,
    *,
    mood: str = "chill",  # "chill", "blink", "startled", "squint", "happy", "chomp", "dizzy", "sleep", "sad", "determined"
    sunglasses: bool = False,
    glint_x: int = -1,
    has_tangerine: bool = True,
    orange_shift: int = 0,
    scarf: bool = False,
    scarf_flutter: int = 0,
    snow_on_head: bool = False,
    lean_x: int = 0,
    holding_phone: bool = False,
    phone_glow: bool = False,
    walk_step: int = 0,
) -> None:
    """High-res Lulu (~18w x 24h, from tangerine oy-4 to sitting feet oy+20)."""
    hx = ox + lean_x
    bx = ox

    if has_tangerine:
        draw_tangerine_hi(c, hx + 7 + orange_shift, oy - 3)

    # Small round golden ears
    c.rect(hx + 2, oy + 1, 3, 3, C["gold_main"])
    c.set(hx + 2, oy + 1, C["gold_hi"])
    c.set(hx + 3, oy + 2, C["gold_dark"])
    c.rect(hx + 13, oy + 1, 3, 3, C["gold_main"])
    c.set(hx + 14, oy + 1, C["gold_hi"])
    c.set(hx + 14, oy + 2, C["gold_dark"])

    # Pear-shaped chubby golden head
    c.hline(hx + 5, oy, 8, C["gold_hi"])
    c.hline(hx + 4, oy + 1, 10, C["gold_hi"])
    c.rect(hx + 3, oy + 2, 12, 4, C["gold_main"])
    c.vline(hx + 14, oy + 2, 4, C["gold_shade"])
    c.rect(hx + 1, oy + 6, 16, 5, C["gold_main"])
    c.vline(hx + 16, oy + 6, 5, C["gold_shade"])
    c.hline(hx + 2, oy + 11, 14, C["gold_shade"])
    c.hline(hx + 3, oy + 12, 12, C["gold_shade"])
    if snow_on_head:
        c.hline(hx + 4, oy, 10, C["white"])
        c.hline(hx + 5, oy + 1, 8, C["snow_bright"])

    # Rounded peach-orange lower snout/muzzle glow
    c.hline(hx + 4, oy + 6, 9, C["snout_hi"])
    c.hline(hx + 2, oy + 7, 13, C["snout_hi"])
    c.rect(hx + 2, oy + 8, 13, 3, C["snout_main"])
    c.hline(hx + 3, oy + 11, 11, C["snout_shade"])
    c.hline(hx + 5, oy + 12, 7, C["snout_shade"])
    c.hline(hx + 5, oy + 7, 6, C["snout_hi"])

    # Eyes
    if sunglasses:
        c.hline(hx + 3, oy + 4, 11, C["shades_frame"])
        c.rect(hx + 3, oy + 4, 5, 3, C["shades_lens"])
        c.rect(hx + 9, oy + 4, 5, 3, C["shades_lens"])
        c.set(hx + 8, oy + 4, C["shades_frame"])
        if 0 <= glint_x <= 10:
            gx = hx + 3 + glint_x
            if hx + 3 <= gx <= hx + 7 or hx + 9 <= gx <= hx + 13:
                c.set(gx, oy + 4, C["shades_glint"])
                c.set(gx, oy + 5, C["shades_glint"])
    elif mood == "sad":
        c.hline(hx + 4, oy + 4, 3, C["gold_shade"])
        c.set(hx + 4, oy + 5, C["gold_dark"])
        c.rect(hx + 4, oy + 5, 3, 2, C["white"])
        c.set(hx + 5, oy + 5, C["eye"])
        c.set(hx + 4, oy + 6, C["tear_blue"])
        c.set(hx + 4, oy + 7, C["tear_blue"])
        c.hline(hx + 10, oy + 4, 3, C["gold_shade"])
        c.set(hx + 12, oy + 5, C["gold_dark"])
        c.rect(hx + 10, oy + 5, 3, 2, C["white"])
        c.set(hx + 11, oy + 5, C["eye"])
        c.set(hx + 12, oy + 6, C["tear_blue"])
        c.set(hx + 12, oy + 7, C["tear_blue"])
    elif mood == "determined":
        c.hline(hx + 4, oy + 4, 2, C["mouth_line"])
        c.set(hx + 6, oy + 5, C["mouth_line"])
        c.rect(hx + 4, oy + 5, 3, 2, C["eye"])
        c.set(hx + 4, oy + 5, C["white"])
        c.hline(hx + 11, oy + 4, 2, C["mouth_line"])
        c.set(hx + 10, oy + 5, C["mouth_line"])
        c.rect(hx + 10, oy + 5, 3, 2, C["eye"])
        c.set(hx + 12, oy + 5, C["white"])
    elif mood == "startled":
        c.rect(hx + 4, oy + 4, 3, 3, C["white"])
        c.rect(hx + 5, oy + 5, 2, 2, C["eye"])
        c.rect(hx + 10, oy + 4, 3, 3, C["white"])
        c.rect(hx + 10, oy + 5, 2, 2, C["eye"])
    elif mood == "dizzy":
        c.set(hx + 4, oy + 4, C["eye"])
        c.set(hx + 5, oy + 5, C["eye"])
        c.set(hx + 6, oy + 6, C["eye"])
        c.set(hx + 12, oy + 4, C["eye"])
        c.set(hx + 11, oy + 5, C["eye"])
        c.set(hx + 10, oy + 6, C["eye"])
    elif mood == "happy":
        c.set(hx + 4, oy + 6, C["eye"])
        c.set(hx + 5, oy + 5, C["eye"])
        c.set(hx + 6, oy + 6, C["eye"])
        c.set(hx + 10, oy + 6, C["eye"])
        c.set(hx + 11, oy + 5, C["eye"])
        c.set(hx + 12, oy + 6, C["eye"])
    elif mood in ("sleep", "blink"):
        c.hline(hx + 4, oy + 5, 3, C["mouth_line"])
        c.hline(hx + 10, oy + 5, 3, C["mouth_line"])
    elif mood == "squint":
        c.hline(hx + 4, oy + 5, 3, C["eye"])
        c.hline(hx + 10, oy + 5, 3, C["eye"])
    else:
        # Iconic heavy half-lidded sleepy eyes!
        c.hline(hx + 4, oy + 4, 3, C["gold_shade"])
        c.hline(hx + 10, oy + 4, 3, C["gold_shade"])
        c.set(hx + 4, oy + 5, C["eye"])
        c.set(hx + 5, oy + 5, C["eye"])
        c.set(hx + 6, oy + 5, C["white"])
        c.set(hx + 4, oy + 6, C["white"])
        c.set(hx + 5, oy + 6, C["eye"])
        c.set(hx + 6, oy + 6, C["white"])
        c.set(hx + 10, oy + 5, C["eye"])
        c.set(hx + 11, oy + 5, C["eye"])
        c.set(hx + 12, oy + 5, C["white"])
        c.set(hx + 10, oy + 6, C["white"])
        c.set(hx + 11, oy + 6, C["eye"])
        c.set(hx + 12, oy + 6, C["white"])

    # Mouth
    if mood == "sad":
        c.hline(hx + 7, oy + 10, 3, C["mouth_line"])
        c.set(hx + 6, oy + 11, C["mouth_line"])
        c.set(hx + 10, oy + 11, C["mouth_line"])
    elif mood == "startled":
        c.rect(hx + 7, oy + 9, 3, 2, C["smile_dark"])
    elif mood == "chomp":
        c.rect(hx + 7, oy + 9, 3, 3, C["smile_dark"])
        c.set(hx + 8, oy + 11, C["smile_tongue"])
    elif mood == "happy":
        c.hline(hx + 7, oy + 10, 3, C["mouth_line"])
        c.set(hx + 6, oy + 9, C["mouth_line"])
        c.set(hx + 10, oy + 9, C["mouth_line"])
    elif mood == "sleep":
        c.rect(hx + 8, oy + 10, 2, 1, C["smile_dark"])
    else:
        c.hline(hx + 7, oy + 10, 3, C["mouth_line"])
        c.set(hx + 6, oy + 11, C["mouth_line"])

    # Torso
    c.rect(bx + 3, oy + 13, 12, 4, C["gold_main"])
    c.vline(bx + 14, oy + 13, 4, C["gold_shade"])
    c.hline(bx + 4, oy + 13, 9, C["gold_hi"])

    # Cozy winter knit scarf (red & gold stripes!)
    if scarf:
        c.rect(bx + 3, oy + 13, 12, 2, C["scarf_red"])
        for sx in (5, 9, 13):
            c.vline(bx + sx, oy + 13, 2, C["scarf_gold"])
        c.rect(bx + 15, oy + 14 + scarf_flutter, 3, 3, C["scarf_red"])
        c.hline(bx + 15, oy + 15 + scarf_flutter, 3, C["scarf_gold"])

    # Bright orange-coral strawberry shorts
    c.rect(bx + 2, oy + 16, 14, 4, C["shorts_main"])
    c.hline(bx + 3, oy + 16, 12, C["shorts_hi"])
    c.vline(bx + 15, oy + 16, 4, C["shorts_dark"])
    c.hline(bx + 2, oy + 19, 14, C["shorts_dark"])
    for sx, sy in [(5, 17), (12, 17), (8, 18)]:
        c.set(bx + sx, oy + sy, C["shorts_seed"])

    # Plump sitting / walking yellow feet
    l_dy = -1 if walk_step == 1 else 0
    r_dy = -1 if walk_step == 2 else 0
    c.rect(bx + 1, oy + 17 + l_dy, 4, 3, C["gold_main"])
    c.hline(bx + 2, oy + 17 + l_dy, 2, C["gold_hi"])
    c.hline(bx + 1, oy + 19 + l_dy, 4, C["gold_shade"])
    c.rect(bx + 10, oy + 17 + r_dy, 4, 3, C["gold_main"])
    c.hline(bx + 11, oy + 17 + r_dy, 2, C["gold_hi"])
    c.hline(bx + 10, oy + 19 + r_dy, 4, C["gold_shade"])

    if holding_phone:
        c.rect(bx + 2, oy + 11, 4, 4, C["phone_body"])
        c.vline(bx + 2, oy + 11, 4, C["phone_dark"])
        if phone_glow:
            c.set(bx + 5, oy + 12, C["phone_glow"])
            c.set(bx + 5, oy + 13, C["phone_glow"])
        c.rect(bx + 6, oy + 13, 4, 2, C["gold_hi"])


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
# 1A. CLEAR DAY (High-Res Batch 1): Ice Cream Meltdown & Triple-Scoop Dash!
# ---------------------------------------------------------------------------
def render_clear_day(f: int) -> Image.Image:
    c = Canvas()
    c.gradient_v((24, 78, 154, 255), (56, 132, 204, 255), 0, 28)
    draw_meadow(c, is_night=False)

    draw_sun(c, 57, 5, f)
    cx = wrap_pos(24, 1, f, WIDTH, direction=1)
    draw_fluffy_cloud(c, cx, 2, C["cloud_white"], C["cloud_light"])

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    glint_step = f % 50
    glint_x = glint_step if glint_step <= 9 else -1
    sprout_sway = 1 if (f % 30) < 15 else 0

    lumei_x, lumei_y = 20, 8 + bob_lumei
    lulu_x, lulu_y = 42, 9 + bob_lulu
    lumei_mood, lulu_mood = "happy", "chill"
    lumei_shades, lulu_shades = True, True
    lumei_walk = 0
    lulu_phone = False
    lumei_cone = 1
    lulu_cone = 1
    splat = False
    triple_cone_pos: Optional[Tuple[int, int]] = None

    if 22 <= f < 52:
        # Chill Lulu gets distracted by his phone -> scoop drips & PLOPS onto the grass!
        lulu_phone = True
        lulu_shades = False
        if f < 38:
            lulu_cone = 1
            if f >= 30:
                # Melting drip falling!
                drip_y = lerp_i(23, 28, (f - 30) / 8)
                c.set(41, drip_y, C["scoop_cream"])
        else:
            lulu_cone = 0
            splat = True
            if f < 46:
                c.set(40, 26, C["scoop_cream"])
                c.set(43, 26, C["scoop_cream"])
    elif 52 <= f < 76:
        # Lulu notices the melted splat -> SAD CRYING LULU! Lumei removes shades in sympathy.
        lumei_shades, lulu_shades = False, False
        lulu_cone = 0
        splat = True
        lulu_mood = "sad"
        lulu_y = 10
        lumei_mood = "startled" if f < 64 else "happy"
        draw_sad_gloom(c, lulu_x + 15, lulu_y - 2, f)
    elif 76 <= f < 116:
        # Sweet Lumei gives Lulu her cone, then sprints OFF-SCREEN right for a GIANT TRIPLE-SCOOP!
        lumei_shades, lulu_shades = False, False
        splat = f < 104
        if f < 86:
            lumei_x = lerp_i(20, 30, ease_in_out((f - 76) / 10))
            lumei_walk = 1 if (f % 4 < 2) else 2
            lulu_mood = "sad" if f < 82 else "startled"
            lulu_cone = 0 if f < 82 else 1
            lumei_cone = 1 if f < 82 else 0
        elif f < 98:
            # Sprints completely OFF-SCREEN right (x -> 68)!
            lumei_x = lerp_i(30, 68, ease_in_out((f - 86) / 12))
            lumei_walk = 1 if (f % 4 < 2) else 2
            lumei_cone = 0
            lulu_cone = 1
            lulu_mood = "happy"
        elif f < 102:
            lumei_x = 68
            lumei_cone = 0
            lulu_cone = 1
            lulu_mood = "happy"
        else:
            # Rushes back in from the right carrying a GIANT TRIPLE-SCOOP cone!
            lumei_x = lerp_i(68, 20, ease_in_out((f - 102) / 14))
            lumei_walk = 1 if (f % 4 < 2) else 2
            lumei_mood, lulu_mood = "delighted", "happy"
            lumei_cone = 0
            lulu_cone = 1
            triple_cone_pos = (lumei_x + 12, 18 + (f % 2))
    elif 116 <= f < 138:
        # Both share the giant triple-scoop cone with ^ ^ eyes & floating hearts!
        lumei_shades, lulu_shades = False, False
        lumei_mood, lulu_mood = "delighted", "happy"
        lumei_y = 8 - (1 if (f % 6 < 3) else 0)
        lumei_cone, lulu_cone = 0, 1
        triple_cone_pos = (36, 20)
        draw_heart(c, 38, 8 - (f - 116) // 5)
        if f >= 124:
            draw_heart(c, 32, 9 - (f - 124) // 5)
    # f=138..149: Back to cool sunglasses & fresh cones -> exact match to f=0!

    if splat:
        c.hline(38, 28, 6, C["scoop_cream"])
        c.hline(39, 27, 4, C["scoop_cream"])

    draw_lumei_hi(
        c, lumei_x, lumei_y, mood=lumei_mood, sunglasses=lumei_shades,
        glint_x=glint_x, sprout_sway=sprout_sway, walk_step=lumei_walk,
    )
    draw_lulu_hi(
        c, lulu_x, lulu_y, mood=lulu_mood, sunglasses=lulu_shades,
        glint_x=glint_x, holding_phone=lulu_phone, phone_glow=(f % 8 < 4),
    )
    if lumei_cone > 0:
        draw_ice_cream(c, lumei_x + 13, lumei_y + 11, scoops=lumei_cone, scoop_col=C["scoop_pink"])
    if lulu_cone > 0 and not lulu_phone:
        draw_ice_cream(c, lulu_x - 1, lulu_y + 11, scoops=lulu_cone, scoop_col=C["scoop_cream"])
    if triple_cone_pos is not None:
        draw_ice_cream(c, triple_cone_pos[0], triple_cone_pos[1], scoops=3, scoop_col=C["scoop_pink"])
    return c.img


def draw_shared_cocoa_cup(
    c: Canvas,
    mx: int,
    my: int,
    f: int,
    *,
    fill: str = "full",  # "full", "empty", "deluxe"
    tilted: bool = False,
) -> None:
    """
    Large, unmistakable shared hot-chocolate mug (~8w x 7h) so viewers immediately
    see rich dark cocoa vs. an obviously EMPTY pale ceramic cup!
    """
    if tilted:
        # Tipped up while Lumei/Lulu drinks!
        c.rect(mx, my + 1, 6, 4, C["mug_red"])
        c.hline(mx + 1, my + 4, 4, C["shorts_dark"])
        c.vline(mx + 6, my + 2, 2, C["mug_red"])
        c.hline(mx + 1, my, 4, C["white"])
        return

    # Big chunky red mug body with rim & handle
    c.hline(mx, my, 7, C["white"])                # crisp white ceramic top rim
    c.rect(mx, my + 1, 7, 5, C["mug_red"])
    c.hline(mx + 1, my + 5, 5, C["shorts_dark"])  # bottom shading
    c.vline(mx + 7, my + 2, 3, C["mug_red"])      # D-handle
    c.set(mx + 6, my + 2, C["mug_red"])
    c.set(mx + 6, my + 4, C["mug_red"])

    if fill == "empty":
        # Clearly EMPTY pale gray-white hollow interior — NO cocoa, NO steam!
        c.hline(mx + 1, my, 5, (156, 168, 184, 255))
        c.hline(mx + 2, my + 1, 3, (124, 136, 152, 255))
    elif fill == "full":
        # Rich dark hot chocolate + 2 tiny white marshmallows + rising steam!
        c.hline(mx + 1, my, 5, C["cocoa"])
        c.hline(mx + 1, my + 1, 5, C["cocoa"])
        c.set(mx + 2, my, C["marshmallow"])
        c.set(mx + 4, my, C["white"])
        st = (f // 3) % 5
        c.set(mx + 2, my - 2 - (st % 2), C["steam"])
        c.set(mx + 4, my - 3 - ((st + 1) % 2), C["steam_dim"])
    elif fill == "deluxe":
        # Overflowing hot chocolate topped with tall whipped cream + marshmallows + steam!
        c.hline(mx + 1, my, 5, C["cocoa"])
        c.hline(mx + 1, my - 1, 5, C["marshmallow"])
        c.hline(mx + 2, my - 2, 3, C["white"])
        c.set(mx + 3, my - 3, C["cherry"])
        st = (f // 3) % 5
        c.set(mx + 1, my - 3 - (st % 2), C["steam"])
        c.set(mx + 5, my - 4 - ((st + 1) % 2), C["steam_dim"])


# ---------------------------------------------------------------------------
# 1A-COLD. CLEAR DAY COLD (< 55°F): Sharing One Big Cup of Hot Chocolate!
# ---------------------------------------------------------------------------
def render_clear_day_cold(f: int) -> Image.Image:
    c = Canvas()
    c.gradient_v((32, 74, 134, 255), (76, 126, 184, 255), 0, 28)
    c.hline(0, 28, WIDTH, (142, 186, 168, 255))
    c.rect(0, 29, WIDTH, 3, (56, 102, 86, 255))
    c.hline(0, 31, WIDTH, (34, 68, 56, 255))

    draw_sun(c, 57, 5, f)
    cx = wrap_pos(24, 1, f, WIDTH, direction=1)
    draw_fluffy_cloud(c, cx, 2, C["cloud_white"], C["cloud_light"])

    # Little wooden stump table right between them holding the shared mug!
    c.rect(35, 25, 9, 4, C["basket_main"])
    c.hline(34, 25, 11, C["bun_mid"])
    c.hline(35, 28, 9, C["basket_dark"])

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    flutter = 1 if (f % 30) >= 15 else 0
    sprout_sway = 1 if (f % 30) < 15 else 0

    lumei_x, lumei_y = 18, 8 + bob_lumei
    lulu_x, lulu_y = 45, 9 + bob_lulu
    lumei_mood = "blink" if (f % 50) in (12, 13) else "happy"
    lulu_mood = "blink" if (f % 50) in (34, 35) else "chill"
    lumei_walk = 0

    mug_x, mug_y = 36, 19
    mug_fill = "full"
    mug_tilted = False
    show_mug = True

    if 22 <= f < 56:
        # Lumei scoots up, lifts the shared hot chocolate mug, and DRINKS IT COMPLETELY DRY!
        if f < 32:
            lumei_x = lerp_i(18, 24, ease_in_out((f - 22) / 10))
            lumei_walk = 1 if (f % 4 < 2) else 2
        elif f < 48:
            lumei_x = 24
            lumei_mood = "delighted" if (f % 6 < 3) else "chomp"
            mug_x, mug_y = 32, 15 + (1 if (f % 4 < 2) else 0)
            mug_tilted = True
        else:
            # Sets the clearly EMPTY cup back on the stump!
            lumei_x = 24
            lumei_mood = "delighted"
            mug_x, mug_y = 36, 19
            mug_fill = "empty"
    elif 56 <= f < 82:
        # Lulu peeks into the EMPTY mug -> SAD CRYING LULU! Guilty Lumei freezes!
        lumei_x = 24
        mug_x, mug_y = 36, 19
        mug_fill = "empty"
        lulu_mood = "sad"
        lulu_y = 10
        lumei_mood = "guilty"
        draw_sad_gloom(c, lulu_x + 15, lulu_y - 2, f)
    elif 82 <= f < 118:
        # Sweet Lumei grabs the empty mug, sprints OFF-SCREEN left, & returns with an OVERFLOWING DELUXE MUG!
        lulu_mood = "sad" if f < 108 else "startled"
        lulu_y = 10 if f < 108 else 9
        if f < 106:
            draw_sad_gloom(c, lulu_x + 15, lulu_y - 2, f)
        lumei_walk = 1 if (f % 4 < 2) else 2
        if f < 96:
            lumei_x = lerp_i(24, -18, ease_in_out((f - 82) / 14))
            lumei_mood = "guilty"
            mug_x, mug_y = lumei_x + 12, 18
            mug_fill = "empty"
        elif f < 102:
            lumei_x = -18
            show_mug = False
        else:
            lumei_x = lerp_i(-18, 22, ease_in_out((f - 102) / 16))
            lumei_mood = "happy"
            mug_x, mug_y = lumei_x + 12, 17 + (f % 2)
            mug_fill = "deluxe"
    elif 118 <= f < 138:
        # Lulu lifts the deluxe cocoa mug and takes a happy warm sip -> twin hearts!
        lumei_x = lerp_i(22, 18, ease_in_out((f - 118) / 10))
        lumei_mood, lulu_mood = "delighted", "happy"
        if f < 130:
            mug_x, mug_y = 41, 16 + (1 if (f % 4 < 2) else 0)
            mug_fill = "deluxe"
            mug_tilted = (f % 8 >= 4)
        else:
            mug_x, mug_y = 36, 19
            mug_fill = "deluxe"
        draw_heart(c, 39, 8 - (f - 118) // 4)
        if f >= 124:
            draw_heart(c, 33, 9 - (f - 124) // 4)

    draw_lumei_hi(
        c, lumei_x, lumei_y, mood=lumei_mood,
        scarf=True, scarf_flutter=flutter, sprout_sway=sprout_sway, walk_step=lumei_walk,
    )
    draw_lulu_hi(
        c, lulu_x, lulu_y, mood=lulu_mood,
        scarf=True, scarf_flutter=1 - flutter,
    )
    if show_mug:
        draw_shared_cocoa_cup(c, mug_x, mug_y, f, fill=mug_fill, tilted=mug_tilted)
    return c.img


# ---------------------------------------------------------------------------
# 1B. CLEAR NIGHT (Warm & Cold): Telescope Stargazing (+ Crackling Campfire when Cold!)
# ---------------------------------------------------------------------------
def render_clear_night(f: int, is_cold: bool = False) -> Image.Image:
    c = Canvas()
    c.gradient_v((4, 8, 22, 255), (10, 18, 42, 255), 0, 28)
    draw_meadow(c, is_night=True)
    draw_stars(c, f, dense=True)
    draw_moon(c, 57, 2)

    # Twin shooting stars streaking across the starry sky!
    for start_f, x_start, y_start in [(24, 24, 2), (76, 30, 2)]:
        if start_f <= f <= start_f + 14:
            dt = f - start_f
            ssx = x_start + dt * 2
            ssy = y_start + dt // 2
            c.set(ssx, ssy, C["white"])
            c.set(ssx - 1, ssy, C["wish_gold"])
            c.set(ssx - 2, ssy - 1, C["star_bright"])
            c.set(ssx - 3, ssy - 1, C["star_dim"])

    # Starry stargazing mat on the grass
    c.hline(16, 28, 46, C["blanket_main"])
    c.hline(15, 29, 48, C["blanket_dark"])
    for sx in (20, 32, 46, 56):
        c.set(sx, 28, C["blanket_star"])

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    flutter = 1 if (f % 30) >= 15 else 0
    sprout_sway = 1 if (f % 30) < 15 else 0

    lumei_x, lumei_y = 19, 8 + bob_lumei
    lulu_x, lulu_y = 37, 9 + bob_lulu
    scope_x, scope_y = 55, 20
    scope_tilt = 0
    lumei_mood = "blink" if (f % 50) in (12, 13) else "happy"
    lulu_mood = "blink" if (f % 50) in (34, 35) else "chill"
    lumei_walk, lulu_walk = 0, 0
    orange_pop = 0

    if 24 <= f < 52:
        lumei_mood = "delighted"
        lumei_y = 8 - (2 if (f % 8 < 4) else 0)
        if f >= 34:
            lumei_x = lerp_i(19, 27, ease_in_out((f - 34) / 14))
            lumei_walk = 1 if (f % 4 < 2) else 2
            if f >= 42:
                lulu_mood = "startled"
                orange_pop = -1 if (f % 4 < 2) else 0
                scope_tilt = 1 if (f % 4 < 2) else 0
    elif 52 <= f < 98:
        lulu_x = lerp_i(37, 21, ease_in_out((f - 52) / 14)) if f < 66 else 21
        lumei_x = lerp_i(27, 40, ease_in_out((f - 52) / 14)) if f < 66 else 40
        lumei_walk = (1 if (f % 4 < 2) else 2) if f < 66 else 0
        lulu_walk = (2 if (f % 4 < 2) else 1) if f < 66 else 0
        lumei_mood = "delighted" if f >= 74 else "happy"
        lulu_mood = "happy" if f >= 74 else "chill"
        if 80 <= f < 98:
            rise = (f - 80) // 4
            draw_heart(c, 39, 8 - rise)
            c.set(48, 6 - rise, C["wish_gold"])
            c.set(31, 7 - rise, C["wish_gold"])
    elif 98 <= f < 132:
        if f < 116:
            lulu_x, lumei_x = 21, 40
            lumei_mood, lulu_mood = "delighted", "happy"
            draw_heart(c, 38, 8 - (f - 98) // 6)
        else:
            t = ease_in_out((f - 116) / 16)
            lumei_x = lerp_i(40, 19, t)
            lulu_x = lerp_i(21, 37, t)
            lumei_walk = 1 if (f % 4 < 2) else 2
            lulu_walk = 2 if (f % 4 < 2) else 1
            lumei_mood, lulu_mood = "happy", "happy"

    draw_telescope(c, scope_x, scope_y, tilt=scope_tilt)
    draw_lumei_hi(
        c, lumei_x, lumei_y, mood=lumei_mood,
        scarf=is_cold, scarf_flutter=flutter, sprout_sway=sprout_sway, walk_step=lumei_walk,
    )
    draw_lulu_hi(
        c, lulu_x, lulu_y + orange_pop, mood=lulu_mood,
        scarf=is_cold, scarf_flutter=1 - flutter, walk_step=lulu_walk,
    )
    if is_cold:
        # Crackling warm campfire beside them in the cold night!
        draw_campfire(c, 7, 26, f)
    return c.img


# ---------------------------------------------------------------------------
# 2. PARTLY CLOUDY (Warm & Cold x Day & Night): Picnic Heist!
#    Warm -> Checkered Picnic + Giant Cake / Candle Cupcake
#    Cold -> Scarved Steaming-Bun Picnic + Giant Steaming Warm Pie!
# ---------------------------------------------------------------------------
def render_partly_cloudy(f: int, is_night: bool, is_cold: bool = False) -> Image.Image:
    c = Canvas()
    if is_night:
        c.gradient_v((6, 12, 30, 255), (14, 24, 52, 255), 0, 28)
        draw_stars(c, f, dense=False)
        draw_moon(c, 57, 2)
        c_hi, c_lo = C["cloud_mid"], C["cloud_dark"]
    else:
        if is_cold:
            c.gradient_v((38, 76, 130, 255), (84, 128, 178, 255), 0, 28)
        else:
            c.gradient_v((26, 76, 146, 255), (62, 126, 194, 255), 0, 28)
        draw_sun(c, 57, 5, f)
        c_hi, c_lo = C["cloud_white"], C["cloud_light"]

    c1 = wrap_pos(22, 1, f, WIDTH, direction=1)
    c2 = wrap_pos(46, 1, f, WIDTH, direction=1)
    draw_fluffy_cloud(c, c1, 2, c_hi, c_lo)
    draw_fluffy_cloud(c, c2, 5, c_hi, c_lo)

    draw_meadow(c, is_night=is_night)
    draw_picnic_blanket(c, x0=16, width=46)

    if is_night:
        draw_lantern(c, 59, 24, f)
        if not is_cold:
            for fx0, fy0, ph in [(24, 14, 0.0), (40, 11, 2.1), (54, 16, 4.2)]:
                fx = (fx0 + int(round(3 * wave_sin(f, cycles=3, phase=ph)))) % WIDTH
                fy = fy0 + int(round(2 * wave_sin(f, cycles=5, phase=ph)))
                if ((f + int(ph * 10)) % 30) < 18:
                    c.set(fx, fy, C["firefly"])

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    flutter = 1 if (f % 30) >= 15 else 0
    sprout_sway = 1 if (f % 30) < 15 else 0

    lumei_x, lumei_y = 20, 8 + bob_lumei
    lulu_x, lulu_y = 43, 9 + bob_lulu
    lumei_mood = "blink" if (f % 50) in (12, 13) else "happy"
    lulu_mood = "blink" if (f % 50) in (34, 35) else "chill"
    lumei_walk = 0
    snack_stage = 0
    show_treat = False
    treat_x, treat_y = 36, 23
    lulu_phone = False

    if 22 <= f < 56:
        if is_night:
            lulu_mood = "sleep"
            draw_zzz(c, lulu_x + 15, 6 - (f % 16) // 4)
        else:
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
            snack_stage = 2
            dt = f - 44
            c.set(38 + dt // 5, 22 - dt // 4, C["bun_hi"] if is_cold else C["cake_sponge"])
            c.set(35 - dt // 5, 21 - dt // 4, C["steam"] if is_cold else C["cake_pink"])
    elif 56 <= f < 84:
        snack_stage = 2
        lumei_x = 26
        lulu_mood = "sad"
        lulu_y = 10
        lumei_mood = "guilty"
        draw_sad_gloom(c, lulu_x + 15, lulu_y - 2, f)
    elif 84 <= f < 120:
        snack_stage = 2
        lulu_mood = "sad" if f < 110 else "startled"
        lulu_y = 10 if f < 110 else 9
        if f < 108:
            draw_sad_gloom(c, lulu_x + 15, lulu_y - 2, f)
        lumei_walk = 1 if (f % 4 < 2) else 2
        if f < 98:
            lumei_x = lerp_i(26, -18, ease_in_out((f - 84) / 14))
            lumei_mood = "guilty"
        elif f < 104:
            lumei_x = -18
        else:
            lumei_x = lerp_i(-18, 24, ease_in_out((f - 104) / 16))
            lumei_mood = "happy"
            show_treat = True
            treat_x = lumei_x + 12
            treat_y = 19 + (f % 2)
    elif 120 <= f < 138:
        snack_stage = 2
        show_treat = True
        lumei_x = lerp_i(24, 20, ease_in_out((f - 120) / 12))
        treat_x = 36
        treat_y = lerp_i(19, 23, ease_in_out((f - 120) / 8))
        lumei_mood, lulu_mood = "delighted", "happy"
        lulu_y = 9 - (1 if (f % 6 < 3) else 0)
        draw_heart(c, 39, 8 - (f - 120) // 4)
        if f >= 126:
            draw_heart(c, 33, 9 - (f - 126) // 4)

    draw_lumei_hi(
        c, lumei_x, lumei_y, mood=lumei_mood,
        scarf=is_cold, scarf_flutter=flutter, sprout_sway=sprout_sway, walk_step=lumei_walk,
    )
    draw_lulu_hi(
        c, lulu_x, lulu_y, mood=lulu_mood,
        scarf=is_cold, scarf_flutter=1 - flutter, holding_phone=lulu_phone, phone_glow=(f % 8 < 4),
    )
    if show_treat:
        if is_cold:
            draw_warm_pie(c, treat_x, treat_y, f)
        elif is_night:
            draw_candle_cupcake(c, treat_x, treat_y, f)
        else:
            draw_giant_cake(c, treat_x, treat_y)
    else:
        if is_cold:
            draw_steaming_buns(c, 36, 24, f, stage=snack_stage)
        else:
            draw_picnic_snacks(c, 36, 24, stage=snack_stage)
    return c.img


# ---------------------------------------------------------------------------
# 3. OVERCAST (High-Res Batch 2):
#    Day   -> High-Res Cloud-Gazing Nap & Wake-Up Cuddle
#    Night -> HIGH-FIDELITY CLOSE-UP Tucked in Bed Sleeping Together!!
# ---------------------------------------------------------------------------
def draw_closeup_sleeping_bed(f: int) -> Image.Image:
    """
    High-fidelity zoomed-in close-up of Lumei & Lulu tucked snugly under a
    quilted blanket on fluffy pillows in their cozy bedroom on an overcast night!
    """
    c = Canvas()
    # Warm dark cozy bedroom wall
    c.gradient_v((18, 16, 30, 255), (28, 24, 44, 255), 0, 22)

    # Bedroom window in upper-right (x=44..61, y=2..12) showing drifting dark overcast clouds!
    c.rect(44, 2, 18, 10, (12, 18, 34, 255))
    wx = wrap_pos(0, 1, f, 18, direction=1)
    for dx in range(7):
        c.set(44 + (wx + dx) % 18, 5, C["cloud_dark"])
        c.set(44 + (wx + dx + 8) % 18, 8, C["cloud_mid"])
    # Wooden window frame & crossbars
    c.hline(43, 1, 20, C["basket_dark"])
    c.hline(43, 12, 20, C["basket_dark"])
    c.vline(43, 1, 12, C["basket_dark"])
    c.vline(62, 1, 12, C["basket_dark"])
    c.vline(52, 2, 10, C["basket_dark"])
    c.hline(44, 6, 18, C["basket_dark"])

    # Wooden headboard & fluffy white pillows behind their zoomed-in heads!
    c.rect(14, 13, 48, 9, (68, 44, 34, 255))
    c.hline(14, 13, 48, (96, 64, 48, 255))
    # Left pillow (under Lumei) & Right pillow (under Lulu)
    c.rect(16, 14, 21, 9, (226, 232, 244, 255))
    c.hline(17, 14, 19, C["white"])
    c.rect(39, 14, 22, 9, (226, 232, 244, 255))
    c.hline(40, 14, 20, C["white"])

    # Gentle breathing rhythm (period 30 -> 5 exact cycles)
    breath = bob_offset(f, period=30, phase=0)
    lulu_breath = bob_offset(f, period=30, phase=15)

    # Story beats inside the 15-second seamless close-up:
    # 0..44:  Peaceful sleeping, Lulu's snooze bubble inflates!
    # 45..64: Bubble POPS! Lulu snores & rolls slightly right, tugging the blanket down 1px on Lumei
    # 65..96: Lumei cracks sleepy-spicy eyes open, tugs blanket back up & snuggles into Lulu's cheek!
    # 97..134: Both smile happily in their sleep with rising floating hearts!
    # 135..149: Settle seamlessly back to f=0!
    lumei_x = 18
    lulu_x = 40
    lumei_eye = "sleep"
    lulu_eye = "sleep"
    bubble_size = 0
    blanket_y = 22 + breath
    lumei_blanket_drop = 0

    if 10 <= f < 46:
        bubble_size = 1 if f < 24 else (2 if f < 38 else 3)
    elif 46 <= f < 66:
        # POP! Lulu rolls slightly right, tugging Lumei's blanket slightly!
        if f < 52:
            for dx, dy in [(-2, -1), (2, -1), (0, 2), (-1, -2)]:
                c.set(47 + dx, 18 + dy, C["white"])
        lulu_x = lerp_i(40, 42, ease_in_out(min(1.0, (f - 46) / 10)))
        lumei_blanket_drop = 2
    elif 66 <= f < 98:
        # Lumei cracks adorable sleepy-spicy eyes open, yanks blanket back & snuggles right up to Lulu!
        lumei_eye = "spicy" if f < 82 else "happy"
        lumei_blanket_drop = 2 if f < 78 else 0
        lumei_x = lerp_i(18, 23, ease_in_out(max(0.0, (f - 76) / 16)))
        lulu_x = lerp_i(42, 39, ease_in_out(max(0.0, (f - 76) / 16)))
        lulu_eye = "happy" if f >= 86 else "sleep"
    elif 98 <= f < 134:
        # Snuggled together smiling happily in their sleep -> floating hearts!
        t_ret = ease_in_out(max(0.0, (f - 118) / 16))
        lumei_x = lerp_i(23, 18, t_ret)
        lulu_x = lerp_i(39, 40, t_ret)
        lumei_eye = "happy" if f < 126 else "sleep"
        lulu_eye = "happy" if f < 126 else "sleep"
        if f < 120:
            draw_heart(c, 37, 11 - (f - 98) // 5)
            if f >= 106:
                draw_heart(c, 31, 10 - (f - 106) // 5)

    # --- ZOOMED-IN CLOSE-UP LUMEI HEAD (~18w x 17h) ---
    lx, ly = lumei_x, 8 + breath
    # Sprout + cream halo + sleek blush bonnet
    c.set(lx + 6, ly - 2, C["sprout_hi"])
    c.set(lx + 7, ly - 2, C["sprout_hi"])
    c.set(lx + 9, ly - 2, C["sprout_hi"])
    c.set(lx + 10, ly - 2, C["sprout_hi"])
    c.set(lx + 8, ly - 1, C["sprout_green"])
    c.hline(lx + 6, ly, 5, C["halo_cream"])
    c.set(lx + 8, ly, C["orange_main"])
    c.hline(lx + 3, ly + 1, 11, C["bonnet_pink"])
    c.rect(lx + 2, ly + 2, 13, 4, C["bonnet_pink"])
    c.rect(lx + 1, ly + 4, 4, 10, C["bonnet_pink"])
    c.set(lx + 5, ly + 1, C["bonnet_dot"])
    c.set(lx + 11, ly + 1, C["bonnet_dot"])
    for dx, dy in [(4, 3), (6, 3), (8, 3), (10, 3), (12, 3), (3, 4), (13, 4), (2, 6), (2, 8), (2, 10)]:
        c.set(lx + dx, ly + dy, C["bonnet_ruffle"])
    c.rect(lx + 1, ly + 4, 3, 3, C["gold_main"])
    c.set(lx + 2, ly + 5, C["gold_dark"])
    # Large high-fidelity golden face!
    c.hline(lx + 5, ly + 4, 9, C["gold_hi"])
    c.rect(lx + 4, ly + 5, 11, 9, C["gold_main"])
    c.vline(lx + 15, ly + 7, 6, C["gold_main"])
    c.hline(lx + 4, ly + 13, 11, C["gold_shade"])
    # Rosy cheeks
    c.rect(lx + 5, ly + 10, 3, 2, C["cheek_angry"] if lumei_eye == "spicy" else C["cheek_peach"])
    c.rect(lx + 13, ly + 10, 2, 2, C["cheek_angry"] if lumei_eye == "spicy" else C["cheek_peach"])
    # Expressive close-up eyes
    if lumei_eye == "spicy":
        c.hline(lx + 6, ly + 6, 3, C["mouth_line"])
        c.rect(lx + 6, ly + 7, 3, 2, C["eye"])
        c.set(lx + 6, ly + 7, C["white"])
        c.hline(lx + 11, ly + 6, 3, C["mouth_line"])
        c.rect(lx + 11, ly + 7, 3, 2, C["eye"])
        c.set(lx + 11, ly + 7, C["white"])
        c.hline(lx + 9, ly + 11, 3, C["smile_dark"])
    elif lumei_eye == "happy":
        c.set(lx + 6, ly + 8, C["eye"]); c.set(lx + 7, ly + 7, C["eye"]); c.set(lx + 8, ly + 8, C["eye"])
        c.set(lx + 11, ly + 8, C["eye"]); c.set(lx + 12, ly + 7, C["eye"]); c.set(lx + 13, ly + 8, C["eye"])
        c.hline(lx + 9, ly + 10, 3, C["smile_dark"]); c.set(lx + 10, ly + 11, C["smile_tongue"])
    else:
        # Peaceful curved sleeping lashes!
        c.set(lx + 6, ly + 8, C["mouth_line"]); c.hline(lx + 7, ly + 9, 2, C["mouth_line"])
        c.hline(lx + 11, ly + 9, 2, C["mouth_line"]); c.set(lx + 13, ly + 8, C["mouth_line"])
        c.hline(lx + 9, ly + 11, 2, C["mouth_line"])

    # --- ZOOMED-IN CLOSE-UP LULU HEAD (~20w x 17h) ---
    ux, uy = lulu_x, 8 + lulu_breath
    draw_tangerine_hi(c, ux + 7, uy - 2)
    c.rect(ux + 2, uy + 2, 3, 3, C["gold_main"]); c.set(ux + 3, uy + 3, C["gold_dark"])
    c.rect(ux + 15, uy + 2, 3, 3, C["gold_main"]); c.set(ux + 16, uy + 3, C["gold_dark"])
    c.hline(ux + 5, uy + 1, 10, C["gold_hi"])
    c.rect(ux + 3, uy + 2, 14, 5, C["gold_main"])
    c.rect(ux + 1, uy + 7, 18, 7, C["gold_main"])
    c.vline(ux + 18, uy + 7, 7, C["gold_shade"])
    # Big plush peach-orange muzzle
    c.hline(ux + 4, uy + 7, 11, C["snout_hi"])
    c.rect(ux + 2, uy + 8, 15, 5, C["snout_main"])
    c.hline(ux + 4, uy + 8, 11, C["snout_hi"])
    c.hline(ux + 3, uy + 13, 13, C["snout_shade"])
    if lulu_eye == "happy":
        c.set(ux + 4, uy + 6, C["eye"]); c.set(ux + 5, uy + 5, C["eye"]); c.set(ux + 6, uy + 6, C["eye"])
        c.set(ux + 12, uy + 6, C["eye"]); c.set(ux + 13, uy + 5, C["eye"]); c.set(ux + 14, uy + 6, C["eye"])
        c.hline(ux + 8, uy + 11, 3, C["mouth_line"])
        c.set(ux + 7, uy + 10, C["mouth_line"]); c.set(ux + 11, uy + 10, C["mouth_line"])
    else:
        c.hline(ux + 4, uy + 6, 3, C["mouth_line"])
        c.hline(ux + 12, uy + 6, 3, C["mouth_line"])
        c.rect(ux + 8, uy + 11, 2, 1, C["smile_dark"])

    # Growing translucent cartoon snooze bubble from Lulu!
    if bubble_size == 1:
        c.rect(ux + 7, uy + 10, 2, 2, C["rain_bright"])
    elif bubble_size == 2:
        c.rect(ux + 6, uy + 9, 3, 3, C["rain_bright"])
        c.set(ux + 6, uy + 9, C["white"])
    elif bubble_size == 3:
        c.rect(ux + 5, uy + 8, 4, 4, C["rain_bright"])
        c.set(ux + 6, uy + 9, C["white"])
        c.set(ux + 5, uy + 8, C["snow_mid"])

    # --- COZY QUILTED BLANKET PULLED UP TO THEIR CHINS (y=22..31) ---
    for x in range(13, WIDTH):
        by = blanket_y + (lumei_blanket_drop if x < 38 else 0)
        c.set(x, by, C["bonnet_ruffle"])
        c.set(x, by + 1, C["blanket_hi"])
        for y in range(by + 2, HEIGHT):
            col = C["blanket_main"] if ((x // 5 + y // 4) % 2 == 0) else C["blanket_dark"]
            c.set(x, y, col)
    # Cute golden quilted stars on blanket
    for sx, sy in [(20, 26), (31, 28), (45, 26), (55, 28)]:
        c.set(sx, sy, C["blanket_star"])

    # Little floating Zzzs while sleeping (f=6..44)
    if 6 <= f < 44:
        zt = (f - 6) % 19
        draw_zzz(c, 58, 12 - zt // 5)
    return c.img


def render_overcast(f: int, is_night: bool) -> Image.Image:
    if is_night:
        return draw_closeup_sleeping_bed(f)

    # DAY: High-Res Cloud-Gazing Nap & Spicy Wake-Up Cuddle!
    c = Canvas()
    c.gradient_v((64, 78, 98, 255), (96, 112, 134, 255), 0, 28)
    draw_meadow(c, is_night=False)

    c1 = wrap_pos(0, 1, f, WIDTH, direction=1)
    c2 = wrap_pos(16, 1, f, WIDTH, direction=1)
    c3 = wrap_pos(34, 1, f, WIDTH, direction=1)
    c4 = wrap_pos(50, 1, f, WIDTH, direction=1)
    c.rect(0, 0, WIDTH, 4, C["cloud_gray"])
    for cx in (c1, c2, c3, c4):
        draw_fluffy_cloud(c, cx, 2, C["cloud_light"], C["cloud_gray"])
        draw_fluffy_cloud(c, (cx + 8) % WIDTH, 5, C["cloud_gray"], C["cloud_mid"])

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    sprout_sway = 1 if (f % 30) < 15 else 0

    lumei_x, lumei_y = 20, 8 + bob_lumei
    lulu_x, lulu_y = 43, 9 + bob_lulu
    lumei_mood, lulu_mood = "happy", "sleep"
    lumei_walk = 0

    if 6 <= f < 46:
        lulu_mood = "sleep"
        lumei_mood = "happy" if f < 30 else "squint"
        zt = (f - 6) % 20
        draw_zzz(c, lulu_x + 15, 5 - zt // 5)
    elif 46 <= f < 78:
        lumei_mood = "spicy"
        if f < 62:
            lumei_x = lerp_i(20, 31, ease_in_out((f - 46) / 16))
            lumei_walk = 1 if (f % 4 < 2) else 2
            lulu_mood = "sleep"
        else:
            lumei_x = 31
            lumei_y = 8 - (1 if (f % 4 < 2) else 0)
            lulu_mood = "startled"
            draw_exclaim(c, lulu_x + 8, lulu_y - 6)
    elif 78 <= f < 118:
        lumei_x = 31
        lulu_x = lerp_i(43, 39, ease_in_out((f - 78) / 10)) if f < 108 else lerp_i(39, 43, ease_in_out((f - 108) / 10))
        lumei_mood, lulu_mood = "delighted", "happy"
        if 86 <= f < 112:
            draw_heart(c, 39, 7 - (f - 86) // 6)
    elif 118 <= f < 136:
        lumei_x = lerp_i(31, 20, ease_in_out((f - 118) / 18))
        lumei_walk = 1 if (f % 4 < 2) else 2
        lumei_mood = "happy"
        lulu_mood = "chill" if f < 128 else "sleep"

    draw_lumei_hi(c, lumei_x, lumei_y, mood=lumei_mood, sprout_sway=sprout_sway, walk_step=lumei_walk)
    draw_lulu_hi(c, lulu_x, lulu_y, mood=lulu_mood)
    if 48 <= f < 74:
        draw_anger_steam(c, lumei_x + 6, lumei_y - 3, f)
    return c.img


# ---------------------------------------------------------------------------
# 4. FOG (High-Res Batch 2): Lost in the Fog — Off-Screen Hide & Seek (+ Night Lantern!)
# ---------------------------------------------------------------------------
def render_fog(f: int, is_night: bool) -> Image.Image:
    c = Canvas()
    if is_night:
        c.gradient_v((14, 22, 36, 255), (30, 42, 62, 255), 0, 28)
        draw_moon(c, 57, 2)
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

    lumei_x, lumei_y = 20, 8 + bob_lumei
    lulu_x, lulu_y = 43, 9 + bob_lulu
    lumei_mood, lulu_mood = "happy", "chill"
    lumei_walk, lulu_walk = 0, 0

    if 20 <= f < 46:
        lulu_x = lerp_i(43, 70, ease_in_out((f - 20) / 24))
        lulu_walk = 1 if (f % 4 < 2) else 2
        lumei_mood = "startled" if f >= 34 else "happy"
    elif 46 <= f < 84:
        lulu_x = 70
        lumei_mood = "squint"
        lumei_walk = 1 if (f % 6 < 3) else 2
        if f < 64:
            lumei_x = lerp_i(20, 38, ease_in_out((f - 46) / 18))
            draw_question(c, lumei_x + 7, lumei_y - 5)
        else:
            lumei_x = lerp_i(38, 22, ease_in_out((f - 64) / 18))
            draw_question(c, lumei_x + 7, lumei_y - 5)
    elif 84 <= f < 118:
        lumei_x = 22
        if f < 102:
            lulu_x = lerp_i(70, 37, ease_in_out((f - 84) / 18))
            lulu_walk = 1 if (f % 4 < 2) else 2
            lumei_mood = "startled" if f < 96 else "delighted"
            if f < 96:
                draw_exclaim(c, lumei_x + 7, lumei_y - 5)
        else:
            lulu_x = 37
            lumei_mood, lulu_mood = "delighted", "happy"
            draw_heart(c, 37, 8 - (f - 102) // 4)
    elif 118 <= f < 138:
        lumei_x = lerp_i(22, 20, ease_in_out((f - 118) / 18))
        lulu_x = lerp_i(37, 43, ease_in_out((f - 118) / 18))
        lumei_walk = 1 if (f % 4 < 2) else 2
        lulu_walk = 2 if (f % 4 < 2) else 1

    draw_lumei_hi(c, lumei_x, lumei_y, mood=lumei_mood, sprout_sway=sprout_sway, walk_step=lumei_walk)
    if is_night:
        draw_lantern(c, lumei_x + 14, lumei_y + 13, f)
    draw_lulu_hi(c, lulu_x, lulu_y, mood=lulu_mood, walk_step=lulu_walk)

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
# 5. DRIZZLE (High-Res Batch 2):
#    Day   -> Puddle-Jumping Splash Duel
#    Night -> Moonlit Puddle Reflections & Umbrella Escort!
# ---------------------------------------------------------------------------
def render_drizzle(f: int, is_night: bool) -> Image.Image:
    c = Canvas()
    if is_night:
        c.gradient_v((10, 18, 34, 255), (18, 30, 52, 255), 0, 28)
        draw_storm_canopy(c, f, C["cloud_night"], C["cloud_dark"])
        puddle_col = C["puddle_night"]
        draw_meadow(c, is_night=True)
        draw_lantern(c, 59, 24, f)
    else:
        c.gradient_v((44, 68, 98, 255), (72, 102, 134, 255), 0, 28)
        draw_storm_canopy(c, f, C["cloud_gray"], C["cloud_light"])
        puddle_col = C["puddle_day"]
        draw_meadow(c, is_night=False)

    c.hline(26, 28, 20, puddle_col)
    c.hline(24, 29, 24, puddle_col)
    c.hline(30, 29, 9, C["puddle_hi"])

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    sprout_sway = 1 if (f % 30) < 15 else 0

    if not is_night:
        # DAY: High-Res Puddle-Jumping Splash Duel!
        lumei_x, lumei_y = 19, 8 + bob_lumei
        lulu_x, lulu_y = 43, 9 + bob_lulu
        lumei_mood, lulu_mood = "happy", "chill"
        lumei_walk, lulu_walk = 0, 0
        lulu_phone = True

        if 22 <= f < 56:
            if f < 36:
                lumei_x = lerp_i(19, 27, ease_in_out((f - 22) / 14))
                lumei_walk = 1 if (f % 4 < 2) else 2
            else:
                lumei_x = 27
                lumei_y = 8 - int(round(4 * abs(math.sin(math.pi * (f - 36) / 10))))
                lumei_mood = "delighted"
                if (f - 36) % 10 in (0, 1, 9):
                    for sx, sy in [(40, 24), (42, 21), (44, 23), (24, 25)]:
                        c.set(sx, sy, C["rain_bright"])
                if f >= 46:
                    lulu_mood, lulu_phone = "startled", False
        elif 56 <= f < 96:
            lumei_x, lulu_phone = 24, False
            if f < 68:
                lulu_x = lerp_i(43, 35, ease_in_out((f - 56) / 12))
                lulu_walk = 1 if (f % 4 < 2) else 2
            else:
                lulu_x = 35
                lulu_y = 9 - int(round(4 * abs(math.sin(math.pi * (f - 68) / 10))))
                lulu_mood = "happy"
                lumei_mood = "startled" if f < 78 else "delighted"
                if (f - 68) % 10 in (0, 1, 9):
                    for sx, sy in [(32, 23), (30, 20), (45, 24), (34, 21)]:
                        c.set(sx, sy, C["rain_bright"])
        elif 96 <= f < 130:
            lumei_x = lerp_i(24, 19, ease_in_out((f - 108) / 20)) if f >= 108 else 24
            lulu_x = lerp_i(35, 43, ease_in_out((f - 108) / 20)) if f >= 108 else 35
            lumei_walk = (1 if (f % 4 < 2) else 2) if f >= 108 else 0
            lulu_walk = (2 if (f % 4 < 2) else 1) if f >= 108 else 0
            lumei_mood, lulu_mood = "delighted", "happy"
            lulu_phone = f >= 126
            if f < 112:
                draw_heart(c, 37, 8 - (f - 96) // 4)

        draw_lumei_hi(c, lumei_x, lumei_y, mood=lumei_mood, sprout_sway=sprout_sway, walk_step=lumei_walk)
        draw_lulu_hi(c, lulu_x, lulu_y, mood=lulu_mood, holding_phone=lulu_phone, phone_glow=(f % 10 < 5), walk_step=lulu_walk)
    else:
        # NIGHT: Lumei skips playfully across puddles while sweet Lulu escorts her with an umbrella!
        wave = math.sin(2.0 * math.pi * f / NUM_FRAMES)
        lumei_x = int(round(26 + 8 * wave))
        lulu_x = lumei_x + 15
        skip = 1 if (f % 10 < 5) else 0
        lumei_y = 8 - skip
        lulu_y = 9 + bob_lulu
        walk_s = 1 if (f % 6 < 3) else 2
        draw_lumei_hi(c, lumei_x, lumei_y, mood="delighted", sprout_sway=sprout_sway, walk_step=walk_s)
        draw_lulu_hi(c, lulu_x, lulu_y, mood="happy", walk_step=walk_s)
        draw_umbrella(c, lumei_x + 10, 1 + bob_lulu, handle_h=17)
        if skip == 0 and (f % 10 == 5):
            c.set(lumei_x + 4, 27, C["puddle_hi"])
            c.set(lumei_x + 11, 27, C["puddle_hi"])
        if (f % 50) < 18:
            draw_heart(c, lumei_x + 14, 7 - (f % 50) // 5)

    for x0, y0, bright in DRIZZLE_DROPS_64:
        rx = wrap_pos(x0, 2, f, WIDTH, direction=-1)
        ry = wrap_pos(y0, 10, f, HEIGHT, direction=1)
        c.set(rx, ry, C["rain_bright"] if bright else C["rain_dim"])
    return c.img


# ---------------------------------------------------------------------------
# 8. RAIN SHOWERS (High-Res Batch 2): Cloudburst Off-Screen Dash & Rainbow / Moonbow!
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
            rad = 21 - idx
            for x in range(21, WIDTH):
                dx = x - rcx
                rem = rad * rad - dx * dx
                if rem >= 0:
                    y = int(round(rcy - math.sqrt(rem)))
                    if 1 <= y < 28:
                        c.set(x, y, rcol)
        if is_night:
            draw_stars(c, f, dense=False)
            draw_moon(c, 57, 2)
        else:
            draw_sun(c, 57, 5, f)
    elif shower_active:
        draw_storm_canopy(c, f, C["cloud_night"] if is_night else C["cloud_dark"], C["cloud_dark"] if is_night else C["cloud_mid"])
    else:
        if is_night:
            draw_stars(c, f, dense=False)
            draw_moon(c, 57, 2)
        else:
            draw_sun(c, 57, 5, f)

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    sprout_sway = 1 if (f % 30) < 15 else 0

    lumei_x, lumei_y = 20, 8 + bob_lumei
    lulu_x, lulu_y = 43, 9 + bob_lulu
    lumei_mood, lulu_mood = "happy", "chill"
    lumei_walk, lulu_walk = 0, 0

    if 15 <= f < 46:
        lumei_mood, lulu_mood = "startled", "startled"
        if f < 24:
            draw_exclaim(c, lumei_x + 7, lumei_y - 5)
            draw_exclaim(c, lulu_x + 8, lulu_y - 6)
        else:
            t = ease_in_out((f - 24) / 22)
            lumei_x = lerp_i(20, 70, t)
            lulu_x = lerp_i(43, 86, t)
            lumei_walk = 1 if (f % 4 < 2) else 2
            lulu_walk = 2 if (f % 4 < 2) else 1
    elif 46 <= f < 74:
        lumei_x, lulu_x = 72, 86
    elif 74 <= f < 104:
        t = ease_in_out((f - 74) / 28)
        lumei_x = lerp_i(70, 20, t)
        lulu_x = lerp_i(86, 43, t)
        lumei_mood, lulu_mood = "delighted", "happy"
        lumei_walk = 1 if (f % 4 < 2) else 2
        lulu_walk = 2 if (f % 4 < 2) else 1
    elif 104 <= f < 136:
        lumei_mood, lulu_mood = "delighted", "happy"
        lumei_y = 8 - (2 if (f % 8 < 4) else 0)
        lulu_y = 9 - (2 if ((f + 4) % 8 < 4) else 0)
        draw_heart(c, 38, 7 - (f - 104) // 8)

    draw_lumei_hi(c, lumei_x, lumei_y, mood=lumei_mood, sprout_sway=sprout_sway, walk_step=lumei_walk)
    draw_lulu_hi(c, lulu_x, lulu_y, mood=lulu_mood, walk_step=lulu_walk)

    if shower_active:
        for x0, y0, bright in RAIN_DROPS_64:
            rx = wrap_pos(x0, 6, f, WIDTH, direction=-1)
            ry = wrap_pos(y0, 18, f, HEIGHT, direction=1)
            c.set(rx, ry, C["rain_bright"] if bright else C["rain_dim"])
            c.set((rx + 1) % WIDTH, (ry - 1) % HEIGHT, C["rain_dim"])
    return c.img


# ---------------------------------------------------------------------------
# 6. FREEZING RAIN (High-Res Batch 3):
#    Day   -> Slippery Ice Wipeout Off-Screen & Rescue
#    Night -> Moonlit Tandem Ice Glide & Spin!
# ---------------------------------------------------------------------------
def render_freezing_rain(f: int, is_night: bool) -> Image.Image:
    c = Canvas()
    if is_night:
        c.gradient_v((8, 16, 36, 255), (14, 30, 58, 255), 0, 28)
        draw_stars(c, f, dense=False)
        draw_moon(c, 57, 2)
    else:
        c.gradient_v((42, 74, 112, 255), (76, 118, 158, 255), 0, 28)

    # Gleaming frozen ice rink ground
    c.hline(0, 28, WIDTH, C["ice_hi"])
    c.rect(0, 29, WIDTH, 2, C["ice_mid"])
    c.hline(0, 31, WIDTH, C["ice_dark"])
    gx = wrap_pos(4, 2, f, WIDTH, direction=1)
    for off in (0, 22, 44):
        c.hline((gx + off) % WIDTH, 28, 4, C["white"])

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    flutter = 1 if (f % 30) >= 15 else 0
    sprout_sway = 1 if (f % 30) < 15 else 0

    if not is_night:
        # DAY: Overconfident Lulu slips & slides OFF-SCREEN right -> Lumei rescues him!
        lumei_x, lumei_y = 20, 8 + bob_lumei
        lulu_x, lulu_y = 43, 9 + bob_lulu
        lumei_mood, lulu_mood = "happy", "chill"
        lulu_has_tang = True
        loose_tang: Optional[Tuple[int, int]] = None

        if 22 <= f < 52:
            t = ease_in_out((f - 22) / 28)
            lulu_x = lerp_i(43, 72, t)
            lulu_y = 9 + (1 if f >= 30 else 0)
            lulu_mood = "startled" if f < 36 else "dizzy"
            lulu_has_tang = f < 30
            if not lulu_has_tang:
                loose_tang = (lulu_x + 4, 6 - (f % 3))
            lumei_mood = "startled"
            if f < 40:
                draw_exclaim(c, lulu_x + 8, lulu_y - 6)
            # Ice spray sparks under Lulu's sliding feet!
            if f % 4 < 2:
                c.set(lulu_x - 1, 27, C["white"])
                c.set(lulu_x - 3, 26, C["ice_hi"])
        elif 52 <= f < 70:
            lulu_x, lulu_has_tang = 70, False
            lumei_x = lerp_i(20, 62, ease_in_out((f - 52) / 17))
            lumei_mood = "spicy"
        elif 70 <= f < 118:
            t = ease_in_out((f - 70) / 44)
            lumei_x = lerp_i(62, 20, t)
            lulu_x = lerp_i(78, 43, t)
            lumei_mood = "spicy" if f < 104 else "happy"
            lulu_mood = "dizzy" if f < 108 else "chill"
            lulu_has_tang = f >= 106
            if not lulu_has_tang:
                rt = ease_in_out(max(0.0, (f - 88) / 18))
                loose_tang = (lerp_i(66, 50, rt), lerp_i(24, 6, rt))
        elif 118 <= f < 136:
            lumei_mood, lulu_mood = "delighted", "happy"
            draw_heart(c, 39, 7 - (f - 118) // 5)

        draw_lumei_hi(c, lumei_x, lumei_y, mood=lumei_mood, scarf=True, scarf_flutter=flutter, sprout_sway=sprout_sway)
        draw_lulu_hi(c, lulu_x, lulu_y, mood=lulu_mood, scarf=True, scarf_flutter=1 - flutter, has_tangerine=lulu_has_tang)
        if loose_tang is not None:
            draw_tangerine_hi(c, loose_tang[0], loose_tang[1])
    else:
        # NIGHT: Moonlit Tandem Ice Glide — Lulu catches slipping Lumei & they glide together!
        glide = math.sin(2.0 * math.pi * f / NUM_FRAMES)
        cx_pair = int(round(41 + 6 * glide))
        lumei_x = cx_pair - 15
        lulu_x = cx_pair
        slip_moment = (20 <= f < 38) or (95 <= f < 113)
        lumei_mood = "startled" if slip_moment else "delighted"
        lulu_mood = "determined" if slip_moment else "happy"
        lumei_y = 8 - (1 if slip_moment else bob_lumei)
        lulu_y = 9 + bob_lulu
        draw_lumei_hi(c, lumei_x, lumei_y, mood=lumei_mood, scarf=True, scarf_flutter=flutter, sprout_sway=sprout_sway)
        draw_lulu_hi(c, lulu_x, lulu_y, mood=lulu_mood, scarf=True, scarf_flutter=1 - flutter)
        # Ice skating sparkles under their feet!
        if f % 6 < 3:
            c.set(lumei_x + 3, 27, C["white"])
            c.set(lulu_x + 14, 27, C["ice_hi"])
        if (f % 50) < 18:
            draw_heart(c, cx_pair - 1, 7 - (f % 50) // 5)

    for x0, y0, bright in RAIN_DROPS_64:
        rx = wrap_pos(x0, 5, f, WIDTH, direction=-1)
        ry = wrap_pos(y0, 15, f, HEIGHT, direction=1)
        c.set(rx, ry, C["ice_hi"] if bright else C["ice_mid"])
        c.set((rx + 1) % WIDTH, (ry - 1) % HEIGHT, C["ice_dark"])
    return c.img


# ---------------------------------------------------------------------------
# 7. RAIN (High-Res Batch 1): Day Umbrella Tug-of-War | Night Paper Boat Race!
# ---------------------------------------------------------------------------
def render_rain(f: int, is_night: bool) -> Image.Image:
    c = Canvas()
    if is_night:
        c.gradient_v((6, 12, 26, 255), (12, 22, 42, 255), 0, 29)
        draw_storm_canopy(c, f, C["cloud_night"], C["cloud_dark"])
        c.rect(0, 28, WIDTH, 4, (14, 28, 52, 255))
        c.hline(0, 28, WIDTH, (28, 54, 92, 255))
        # Warm glowing lantern reflecting on the rain puddle!
        draw_lantern(c, 59, 24, f)
    else:
        c.gradient_v((34, 54, 84, 255), (54, 80, 114, 255), 0, 29)
        draw_storm_canopy(c, f, C["cloud_mid"], C["cloud_gray"])
        c.rect(0, 29, WIDTH, 3, (28, 52, 82, 255))
        c.hline(0, 29, WIDTH, (44, 76, 114, 255))

    for rx, ph in [(8, 0), (32, 10), (52, 20)]:
        rip = (f + ph) % 30
        if rip < 10:
            c.hline(rx, 30, 2, C["rain_bright"])
        elif rip < 20:
            c.set(rx - 1, 30, C["rain_dim"])
            c.set(rx + 2, 30, C["rain_dim"])

    bob = bob_offset(f, period=30, phase=0)
    sprout_sway = 1 if (f % 30) < 15 else 0

    if not is_night:
        # DAY: High-Res Umbrella Tug-of-War!
        lumei_x, lumei_y = 20, 9 + bob
        lulu_x, lulu_y = 37, 10 + bob
        umb_cx, umb_y = 36, 1 + bob
        lumei_mood = "blink" if (f % 50) in (12, 13) else "happy"
        lulu_mood = "blink" if (f % 50) in (34, 35) else "chill"
        lulu_phone, lumei_walk = False, 0
        orange_pop = 0

        if 24 <= f < 56:
            lulu_phone = True
            t = ease_in_out((f - 24) / 22)
            lulu_x = lerp_i(37, 45, t)
            umb_cx = lerp_i(36, 48, t)
            if f >= 42:
                lumei_mood = "startled"
                if f % 4 < 2:
                    c.set(lumei_x + 6, lumei_y - 3, C["rain_bright"])
                    c.set(lumei_x + 10, lumei_y - 2, C["white"])
        elif 56 <= f < 88:
            lumei_mood = "spicy"
            if f < 70:
                lumei_x = lerp_i(20, 28, ease_in_out((f - 56) / 14))
                lumei_walk = 1 if (f % 4 < 2) else 2
                lulu_x, umb_cx, lulu_phone = 45, 48, True
            else:
                lumei_x = lerp_i(28, 20, ease_in_out((f - 70) / 16))
                lumei_walk = 1 if (f % 4 < 2) else 2
                umb_cx = lerp_i(48, 30, ease_in_out((f - 70) / 12))
                lulu_x = lerp_i(45, 39, ease_in_out((f - 74) / 14))
                lulu_mood = "startled"
                orange_pop = -1 if f < 80 else 0
        elif 88 <= f < 126:
            umb_cx = lerp_i(30, 36, ease_in_out((f - 88) / 14))
            lulu_x = lerp_i(39, 36, ease_in_out((f - 88) / 14)) if f < 112 else lerp_i(36, 37, ease_in_out((f - 112) / 14))
            lumei_mood = "delighted" if f >= 96 else "happy"
            lulu_mood = "happy"

        draw_lumei_hi(c, lumei_x, lumei_y, mood=lumei_mood, sprout_sway=sprout_sway, walk_step=lumei_walk)
        draw_lulu_hi(c, lulu_x, lulu_y + orange_pop, mood=lulu_mood, holding_phone=lulu_phone, phone_glow=(f % 6 < 3))
        draw_umbrella(c, umb_cx, umb_y, handle_h=17)

        if 56 <= f < 82:
            draw_anger_steam(c, lumei_x + 6, lumei_y - 4, f)
        elif 98 <= f < 120:
            draw_heart(c, 36, 7 - (f - 98) // 6)
    else:
        # NIGHT: Cozy Rainy-Night Paper Boat Race under the blue umbrella!
        lumei_x, lumei_y = 18, 9 + bob
        lulu_x, lulu_y = 34, 10 + bob
        umb_cx, umb_y = 33, 1 + bob
        lumei_mood = "blink" if (f % 50) in (12, 13) else "happy"
        lulu_mood = "blink" if (f % 50) in (34, 35) else "chill"
        white_boat_x: Optional[int] = None
        pink_boat_x: Optional[int] = None

        if 20 <= f < 66:
            # Lulu sets a white paper boat sailing across the puddle & OFF-SCREEN right!
            lulu_mood = "happy"
            lumei_mood = "delighted" if f >= 34 else "happy"
            white_boat_x = lerp_i(44, 68, (f - 20) / 44)
        elif 66 <= f < 112:
            # Excited Lumei launches a pink paper boat racing after his!
            lumei_mood = "delighted"
            lulu_mood = "happy"
            lumei_y = 9 - (1 if (f % 8 < 4) else 0)
            pink_boat_x = lerp_i(34, 68, (f - 66) / 44)
        elif 112 <= f < 136:
            # Cozy huddle under the umbrella with floating hearts!
            lumei_mood, lulu_mood = "delighted", "happy"
            draw_heart(c, 33, 7 - (f - 112) // 6)

        draw_lumei_hi(c, lumei_x, lumei_y, mood=lumei_mood, sprout_sway=sprout_sway)
        draw_lulu_hi(c, lulu_x, lulu_y, mood=lulu_mood)
        draw_umbrella(c, umb_cx, umb_y, handle_h=17)

        if white_boat_x is not None:
            draw_paper_boat(c, white_boat_x, 27 + (1 if (f % 6 < 3) else 0), pink=False)
        if pink_boat_x is not None:
            draw_paper_boat(c, pink_boat_x, 27 + (1 if ((f + 3) % 6 < 3) else 0), pink=True)

    # Slanted raindrops clipped neatly off the umbrella dome
    for x0, y0, bright in RAIN_DROPS_64:
        rx = wrap_pos(x0, 5, f, WIDTH, direction=-1)
        ry = wrap_pos(y0, 15, f, HEIGHT, direction=1)
        if (umb_cx - 13) <= rx <= (umb_cx + 13) and ry >= umb_y + 3:
            continue
        c.set(rx, ry, C["rain_bright"] if bright else C["rain_dim"])
        if (umb_cx - 11) <= rx <= (umb_cx + 11) and umb_y <= ry <= umb_y + 2:
            c.set(rx, umb_y - 1, C["white"])
        else:
            c.set((rx + 1) % WIDTH, (ry - 1) % HEIGHT, C["rain_dim"])
    return c.img





# ---------------------------------------------------------------------------
# 9. SNOW (High-Res Batch 3):
#    Day   -> High-Res Escalating Snowball Fight & Off-Screen Chase!
#    Night -> HIGH-FIDELITY CLOSE-UP: Frosty Window Snow-Watching!
# ---------------------------------------------------------------------------
def draw_closeup_snow_window(f: int) -> Image.Image:
    """
    High-fidelity zoomed-in close-up of Lumei & Lulu bundled in scarves pressing
    against a frosty wooden cabin window watching snowflakes fall on a snowy night,
    breathing frost onto the glass and drawing a cute heart!
    """
    c = Canvas()
    # Snowy midnight night sky visible outside the window
    c.gradient_v((6, 14, 34, 255), (14, 28, 58, 255), 0, 32)
    draw_stars(c, f, dense=False)
    draw_moon(c, 55, 3)

    # Gently falling snowflakes outside the window (exact periodic wrap!)
    for x0, y0, phase, is_big in SNOW_FLAKES_64:
        sy = wrap_pos(y0, 3, f, HEIGHT, direction=1)
        sx = (x0 + int(round(1.5 * wave_sin(f, cycles=5, phase=phase)))) % WIDTH
        if is_big:
            c.set(sx, sy, C["white"])
            c.set((sx - 1) % WIDTH, sy, C["snow_mid"])
            c.set((sx + 1) % WIDTH, sy, C["snow_mid"])
        else:
            c.set(sx, sy, C["snow_bright"])

    # Warm wooden cabin window sill & frame borders
    c.rect(0, 28, WIDTH, 4, (92, 58, 36, 255))
    c.hline(0, 28, WIDTH, (132, 88, 56, 255))
    c.vline(62, 0, 28, (92, 58, 36, 255))
    c.vline(63, 0, 28, (64, 38, 24, 255))
    # Subtle snow drift piled along the outer bottom windowsill
    c.hline(14, 27, 48, C["snow_bright"])
    c.hline(16, 26, 12, C["white"])
    c.hline(48, 26, 12, C["white"])

    breath = bob_offset(f, period=30, phase=0)
    lulu_breath = bob_offset(f, period=30, phase=15)

    # Story beats inside the 15s close-up:
    # 0..34:   Watching snow fall in cozy wonder
    # 35..64:  Warm breath frost patch forms on glass; Lumei draws a glowing pink heart on the frost!
    # 65..114: Both smile happily cheek-to-cheek as a sparkling crystal snowflake lands on the glass!
    # 115..149: Frost & heart fade gently back to clear glass -> exact match to f=0!
    lumei_x = 18
    lulu_x = 40
    lumei_eye = "happy"
    lulu_eye = "chill"

    if 35 <= f < 66:
        lumei_eye = "delighted"
        lulu_eye = "happy" if f >= 50 else "chill"
    elif 66 <= f < 118:
        t_in = ease_in_out(min(1.0, (f - 66) / 14))
        t_out = ease_in_out(max(0.0, (f - 102) / 16))
        shift = t_in * (1.0 - t_out)
        lumei_x = lerp_i(18, 22, shift)
        lulu_x = lerp_i(40, 38, shift)
        lumei_eye = "delighted"
        lulu_eye = "happy"

    # --- ZOOMED-IN LUMEI (bundled in teal/mint knit scarf!) ---
    lx, ly = lumei_x, 9 + breath
    c.set(lx + 6, ly - 2, C["sprout_hi"]); c.set(lx + 7, ly - 2, C["sprout_hi"])
    c.set(lx + 9, ly - 2, C["sprout_hi"]); c.set(lx + 10, ly - 2, C["sprout_hi"])
    c.set(lx + 8, ly - 1, C["sprout_green"])
    c.hline(lx + 6, ly, 5, C["halo_cream"]); c.set(lx + 8, ly, C["orange_main"])
    c.hline(lx + 3, ly + 1, 11, C["bonnet_pink"])
    c.rect(lx + 2, ly + 2, 13, 4, C["bonnet_pink"])
    c.rect(lx + 1, ly + 4, 4, 10, C["bonnet_pink"])
    c.set(lx + 5, ly + 1, C["bonnet_dot"]); c.set(lx + 11, ly + 1, C["bonnet_dot"])
    for dx, dy in [(4, 3), (6, 3), (8, 3), (10, 3), (12, 3), (3, 4), (13, 4), (2, 6), (2, 8), (2, 10)]:
        c.set(lx + dx, ly + dy, C["bonnet_ruffle"])
    c.rect(lx + 1, ly + 4, 3, 3, C["gold_main"]); c.set(lx + 2, ly + 5, C["gold_dark"])
    c.hline(lx + 5, ly + 4, 9, C["gold_hi"])
    c.rect(lx + 4, ly + 5, 11, 9, C["gold_main"])
    c.vline(lx + 15, ly + 7, 6, C["gold_main"])
    c.hline(lx + 4, ly + 13, 11, C["gold_shade"])
    c.rect(lx + 5, ly + 10, 3, 2, C["cheek_peach"])
    c.rect(lx + 13, ly + 10, 2, 2, C["cheek_peach"])
    if lumei_eye == "delighted":
        c.set(lx + 6, ly + 8, C["eye"]); c.set(lx + 7, ly + 7, C["eye"]); c.set(lx + 8, ly + 8, C["eye"])
        c.set(lx + 11, ly + 8, C["eye"]); c.set(lx + 12, ly + 7, C["eye"]); c.set(lx + 13, ly + 8, C["eye"])
    else:
        c.rect(lx + 6, ly + 6, 3, 3, C["white"]); c.rect(lx + 7, ly + 6, 2, 3, C["eye"]); c.set(lx + 7, ly + 6, C["white"])
        c.rect(lx + 12, ly + 6, 2, 3, C["eye"]); c.set(lx + 12, ly + 6, C["white"])
    c.hline(lx + 9, ly + 10, 3, C["smile_dark"]); c.set(lx + 10, ly + 11, C["smile_tongue"])
    # Thick cozy teal/mint scarf bundled up to her chin!
    c.rect(lx + 3, ly + 14, 12, 4, C["scarf_teal"])
    for sx in (5, 9, 13):
        c.vline(lx + sx, ly + 14, 4, C["scarf_mint"])

    # --- ZOOMED-IN LULU (bundled in red/gold knit scarf!) ---
    ux, uy = lulu_x, 9 + lulu_breath
    draw_tangerine_hi(c, ux + 7, uy - 2)
    c.rect(ux + 2, uy + 2, 3, 3, C["gold_main"]); c.set(ux + 3, uy + 3, C["gold_dark"])
    c.rect(ux + 15, uy + 2, 3, 3, C["gold_main"]); c.set(ux + 16, uy + 3, C["gold_dark"])
    c.hline(ux + 5, uy + 1, 10, C["gold_hi"])
    c.rect(ux + 3, uy + 2, 14, 5, C["gold_main"])
    c.rect(ux + 1, uy + 7, 18, 7, C["gold_main"])
    c.vline(ux + 18, uy + 7, 7, C["gold_shade"])
    c.hline(ux + 4, uy + 7, 11, C["snout_hi"])
    c.rect(ux + 2, uy + 8, 15, 5, C["snout_main"])
    c.hline(ux + 4, uy + 8, 11, C["snout_hi"])
    c.hline(ux + 3, uy + 13, 13, C["snout_shade"])
    if lulu_eye == "happy":
        c.set(ux + 4, uy + 6, C["eye"]); c.set(ux + 5, uy + 5, C["eye"]); c.set(ux + 6, uy + 6, C["eye"])
        c.set(ux + 12, uy + 6, C["eye"]); c.set(ux + 13, uy + 5, C["eye"]); c.set(ux + 14, uy + 6, C["eye"])
        c.hline(ux + 8, uy + 11, 3, C["mouth_line"])
        c.set(ux + 7, uy + 10, C["mouth_line"]); c.set(ux + 11, uy + 10, C["mouth_line"])
    else:
        c.hline(ux + 4, uy + 5, 3, C["gold_shade"]); c.hline(ux + 12, uy + 5, 3, C["gold_shade"])
        c.set(ux + 4, uy + 6, C["eye"]); c.set(ux + 5, uy + 6, C["eye"]); c.set(ux + 6, uy + 6, C["white"])
        c.set(ux + 12, uy + 6, C["eye"]); c.set(ux + 13, uy + 6, C["eye"]); c.set(ux + 14, uy + 6, C["white"])
        c.hline(ux + 8, uy + 11, 3, C["mouth_line"])
    # Thick red & gold scarf bundled up to his chin!
    c.rect(ux + 2, uy + 14, 15, 4, C["scarf_red"])
    for sx in (4, 8, 12, 15):
        c.vline(ux + sx, uy + 14, 4, C["scarf_gold"])

    # Breath frost patch + hand-drawn glowing heart on the glass (f=36..126)
    if 36 <= f < 126:
        for dy in range(5):
            for dx in range(7):
                c.set(34 + dx, 8 + dy, (206, 228, 248, 72))
        if f >= 46:
            draw_heart(c, 37, 9)
    # Sparkling crystal snowflake landing on glass (f=72..112)
    if 72 <= f < 112:
        c.set(27, 4, C["white"])
        c.set(26, 4, C["snow_mid"]); c.set(28, 4, C["snow_mid"])
        c.set(27, 3, C["snow_mid"]); c.set(27, 5, C["snow_mid"])
    return c.img


def render_snow(f: int, is_night: bool) -> Image.Image:
    if is_night:
        return draw_closeup_snow_window(f)

    # DAY: High-Res Escalating Snowball Fight & Off-Screen Chase!
    c = Canvas()
    c.gradient_v((52, 86, 128, 255), (96, 134, 174, 255), 0, 28)

    c.rect(0, 28, WIDTH, 4, C["snow_ground"])
    c.hline(0, 28, WIDTH, C["snow_bright"])
    c.hline(0, 30, WIDTH, C["snow_shadow"])
    c.hline(0, 31, WIDTH, C["snow_shadow"])
    c.hline(6, 27, 16, C["snow_ground"])
    c.hline(38, 27, 18, C["snow_ground"])

    bob_lumei = bob_offset(f, period=30, phase=0)
    bob_lulu = bob_offset(f, period=30, phase=15)
    flutter = 1 if (f % 30) >= 15 else 0
    sprout_sway = 1 if (f % 30) < 15 else 0

    lumei_x, lumei_y = 20, 8 + bob_lumei
    lulu_x, lulu_y = 43, 9 + bob_lulu
    lumei_mood = "blink" if (f % 50) in (10, 11) else "happy"
    lulu_mood = "blink" if (f % 50) in (36, 37) else "chill"
    lulu_walk = 0
    lumei_snow, lulu_snow = False, False

    if 22 <= f < 46:
        lulu_mood = "happy"
        if f < 30:
            lulu_y = 10
        elif f < 44:
            t = (f - 30) / 14.0
            sb_x = lerp_i(43, 27, t)
            sb_y = int(round(16 - 7 * math.sin(math.pi * t)))
            c.rect(sb_x, sb_y, 3, 3, C["white"])
            c.hline(sb_x, sb_y + 2, 3, C["snow_mid"])
        else:
            lumei_snow, lumei_mood = True, "startled"
            for dx, dy in [(-2, -1), (2, -2), (-1, 2), (3, 1)]:
                c.set(27 + dx, 10 + dy, C["white"])
    elif 46 <= f < 66:
        lumei_snow = f < 52
        lumei_mood = "spicy"
        lumei_y = 8 - (1 if (f % 4 < 2) else 0)
        lulu_mood = "startled" if f >= 56 else "happy"
        if f >= 54:
            c.rect(32, 19, 5, 5, C["white"])
            c.hline(33, 19, 3, C["snow_bright"])
            c.hline(32, 23, 5, C["snow_mid"])
    elif 66 <= f < 102:
        lumei_mood = "spicy" if f < 84 else "delighted"
        lulu_mood = "startled"
        lulu_walk = 1 if (f % 4 < 2) else 2
        if f < 84:
            lulu_x = lerp_i(43, 62, ease_in_out((f - 66) / 18))
            t = (f - 66) / 18.0
            sb_x = lerp_i(33, 61, t)
            sb_y = int(round(18 - 10 * math.sin(math.pi * t)))
            c.rect(sb_x, sb_y, 5, 5, C["white"])
            c.hline(sb_x, sb_y + 4, 5, C["snow_mid"])
        else:
            lulu_x = lerp_i(62, 43, ease_in_out((f - 84) / 18))
            lulu_snow = True
            if f < 90:
                for dx, dy in [(-3, -2), (4, -3), (-2, 3), (5, 2), (1, -4)]:
                    c.set(min(62, lulu_x + 7 + dx), 11 + dy, C["white"])
    elif 102 <= f < 128:
        lulu_snow = f < 116
        lumei_mood, lulu_mood = "delighted", "happy"
        lumei_y = 8 - (2 if (f % 8 < 4) else 0)
        lulu_y = 9 - (1 if ((f + 4) % 8 < 4) else 0)

    draw_lumei_hi(c, lumei_x, lumei_y, mood=lumei_mood, scarf=True, scarf_flutter=flutter, sprout_sway=sprout_sway, snow_on_bonnet=lumei_snow)
    draw_lulu_hi(c, lulu_x, lulu_y, mood=lulu_mood, scarf=True, scarf_flutter=1 - flutter, walk_step=lulu_walk, snow_on_head=lulu_snow)
    if 48 <= f < 66:
        draw_anger_steam(c, lumei_x + 6, lumei_y - 3, f)
    elif 104 <= f < 122:
        draw_heart(c, 38, 8 - (f - 104) // 5)

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
# 10. THUNDERSTORM (High-Res Batch 3):
#     Day   -> High-Res Overconfident Lulu Leaps Under the Blanket!
#     Night -> HIGH-FIDELITY CLOSE-UP: Peeking Over the Blanket in Lightning!
# ---------------------------------------------------------------------------
def draw_closeup_storm_blanket(f: int) -> Image.Image:
    """
    High-fidelity zoomed-in close-up of Lumei & Lulu peeking over their starry
    purple blanket during a midnight thunderstorm! Lightning flashes illuminate
    their huge startled eyes — Lulu ducks completely under leaving ONLY his
    tangerine sticking up, and sweet Lumei comforts him with hearts!
    """
    flash_1 = f in (30, 31, 34)
    flash_2 = f in (78, 79, 82)
    is_flashing = flash_1 or flash_2
    shiver = (1 if (f % 2 == 0) else 0) if ((30 <= f <= 44) or (78 <= f <= 92)) else 0

    c = Canvas()
    if is_flashing:
        c.gradient_v((72, 84, 122, 255), (42, 54, 88, 255), 0, 22)
    else:
        c.gradient_v((10, 12, 24, 255), (18, 20, 38, 255), 0, 22)

    # Stormy bedroom window in upper-right showing pounding rain & lightning bolts!
    c.rect(44, 2, 18, 12, (98, 114, 158, 255) if is_flashing else (6, 10, 22, 255))
    if flash_1 or flash_2:
        bx0 = 53 if flash_1 else 49
        for i in range(9):
            bx = bx0 + (1 if i % 2 else -1)
            by = 2 + i
            c.set(bx - 1, by, C["bolt_glow"])
            c.set(bx + 1, by, C["bolt_glow"])
            c.set(bx, by, C["bolt_core"])
    # Diagonal rain inside window pane
    for rx0, ry0 in [(46, 3), (51, 7), (56, 4), (59, 9), (48, 11)]:
        rx = 44 + (rx0 - 44 - (3 * 18 * f) // NUM_FRAMES) % 18
        ry = 2 + (ry0 - 2 + (12 * 12 * f) // NUM_FRAMES) % 12
        c.set(rx, ry, C["rain_bright"] if is_flashing else C["rain_dim"])
    c.hline(43, 1, 20, C["basket_dark"]); c.hline(43, 14, 20, C["basket_dark"])
    c.vline(43, 1, 14, C["basket_dark"]); c.vline(62, 1, 14, C["basket_dark"])
    c.vline(52, 2, 12, C["basket_dark"]); c.hline(44, 7, 18, C["basket_dark"])

    # Story beats (150 frames, seamless):
    # 0..29:   Both peek cautiously over the starry blanket rim
    # 30..44:  LIGHTNING #1! Both eyes go HUGE! Lulu ducks COMPLETELY under the covers (tangerine sticks out!)
    # 45..104: Lumei giggles & comforts the shivering blanket lump with hearts (Lightning #2 at f=78!)
    # 105..134: Lulu slowly peeks his wide eyes back up -> relieved smiles!
    # 135..149: Settle back to f=0!
    breath = bob_offset(f, period=30, phase=0)
    lumei_y = 9 + breath + (1 if is_flashing else 0)
    lulu_y = 9 + breath
    lumei_eye = "squint"
    lulu_eye = "chill"

    if 30 <= f < 46:
        lumei_eye = "startled"
        lulu_eye = "startled"
        lulu_y = lerp_i(9, 20, ease_in_out((f - 30) / 14))
    elif 46 <= f < 104:
        # Lulu completely hidden under covers — ONLY his tangerine & blanket bump show!
        lulu_y = 20 + (1 if (78 <= f <= 92) else 0)
        lumei_eye = "startled" if (78 <= f <= 92) else "delighted"
        lulu_eye = "startled"
    elif 104 <= f < 134:
        lulu_y = lerp_i(20, 9, ease_in_out((f - 104) / 22))
        lumei_eye = "delighted" if f < 124 else "squint"
        lulu_eye = "startled" if f < 118 else "happy"

    # --- ZOOMED-IN LUMEI PEEKING OVER BLANKET ---
    lx, ly = 18 + shiver, lumei_y
    c.set(lx + 6, ly - 2, C["sprout_hi"]); c.set(lx + 7, ly - 2, C["sprout_hi"])
    c.set(lx + 9, ly - 2, C["sprout_hi"]); c.set(lx + 10, ly - 2, C["sprout_hi"])
    c.set(lx + 8, ly - 1, C["sprout_green"])
    c.hline(lx + 6, ly, 5, C["halo_cream"]); c.set(lx + 8, ly, C["orange_main"])
    c.hline(lx + 3, ly + 1, 11, C["bonnet_pink"])
    c.rect(lx + 2, ly + 2, 13, 4, C["bonnet_pink"])
    c.rect(lx + 1, ly + 4, 4, 10, C["bonnet_pink"])
    for dx, dy in [(4, 3), (6, 3), (8, 3), (10, 3), (12, 3), (3, 4), (13, 4), (2, 6), (2, 8)]:
        c.set(lx + dx, ly + dy, C["bonnet_ruffle"])
    c.rect(lx + 1, ly + 4, 3, 3, C["gold_main"]); c.set(lx + 2, ly + 5, C["gold_dark"])
    c.hline(lx + 5, ly + 4, 9, C["gold_hi"])
    c.rect(lx + 4, ly + 5, 11, 9, C["gold_main"])
    c.vline(lx + 15, ly + 7, 6, C["gold_main"])
    c.rect(lx + 5, ly + 10, 3, 2, C["cheek_peach"])
    c.rect(lx + 13, ly + 10, 2, 2, C["cheek_peach"])
    if lumei_eye == "startled":
        c.rect(lx + 6, ly + 6, 3, 3, C["white"]); c.rect(lx + 7, ly + 7, 2, 2, C["eye"])
        c.rect(lx + 11, ly + 6, 3, 3, C["white"]); c.rect(lx + 12, ly + 7, 2, 2, C["eye"])
        c.rect(lx + 9, ly + 10, 2, 2, C["smile_dark"])
    elif lumei_eye == "delighted":
        c.set(lx + 6, ly + 8, C["eye"]); c.set(lx + 7, ly + 7, C["eye"]); c.set(lx + 8, ly + 8, C["eye"])
        c.set(lx + 11, ly + 8, C["eye"]); c.set(lx + 12, ly + 7, C["eye"]); c.set(lx + 13, ly + 8, C["eye"])
        c.hline(lx + 9, ly + 10, 3, C["smile_dark"]); c.set(lx + 10, ly + 11, C["smile_tongue"])
    else:
        c.rect(lx + 6, ly + 6, 3, 3, C["white"]); c.rect(lx + 7, ly + 6, 2, 3, C["eye"]); c.set(lx + 7, ly + 6, C["white"])
        c.rect(lx + 12, ly + 6, 2, 3, C["eye"]); c.set(lx + 12, ly + 6, C["white"])
        c.hline(lx + 9, ly + 11, 2, C["smile_dark"])

    # --- ZOOMED-IN LULU PEEKING OR DUCKED UNDER BLANKET ---
    ux, uy = 40 + shiver, lulu_y
    draw_tangerine_hi(c, ux + 7, uy - 2)
    c.rect(ux + 2, uy + 2, 3, 3, C["gold_main"]); c.set(ux + 3, uy + 3, C["gold_dark"])
    c.rect(ux + 15, uy + 2, 3, 3, C["gold_main"]); c.set(ux + 16, uy + 3, C["gold_dark"])
    c.hline(ux + 5, uy + 1, 10, C["gold_hi"])
    c.rect(ux + 3, uy + 2, 14, 5, C["gold_main"])
    c.rect(ux + 1, uy + 7, 18, 7, C["gold_main"])
    c.hline(ux + 4, uy + 7, 11, C["snout_hi"])
    c.rect(ux + 2, uy + 8, 15, 5, C["snout_main"])
    if lulu_eye == "startled":
        c.rect(ux + 4, uy + 5, 3, 3, C["white"]); c.rect(ux + 5, uy + 6, 2, 2, C["eye"])
        c.rect(ux + 12, uy + 5, 3, 3, C["white"]); c.rect(ux + 12, uy + 6, 2, 2, C["eye"])
    elif lulu_eye == "happy":
        c.set(ux + 4, uy + 6, C["eye"]); c.set(ux + 5, uy + 5, C["eye"]); c.set(ux + 6, uy + 6, C["eye"])
        c.set(ux + 12, uy + 6, C["eye"]); c.set(ux + 13, uy + 5, C["eye"]); c.set(ux + 14, uy + 6, C["eye"])
    else:
        c.hline(ux + 4, uy + 5, 3, C["gold_shade"]); c.hline(ux + 12, uy + 5, 3, C["gold_shade"])
        c.set(ux + 4, uy + 6, C["eye"]); c.set(ux + 5, uy + 6, C["eye"]); c.set(ux + 6, uy + 6, C["white"])
        c.set(ux + 12, uy + 6, C["eye"]); c.set(ux + 13, uy + 6, C["eye"]); c.set(ux + 14, uy + 6, C["white"])

    # --- FOREGROUND STARRY PURPLE BLANKET PULLED RIGHT UP TO THEIR EYES (y=20..31) ---
    for x in range(13, WIDTH):
        # Slight blanket mound over ducked Lulu!
        mound = -1 if (42 <= x <= 58 and lulu_y >= 18) else 0
        by = 20 + breath + mound
        c.set(x, by, C["bonnet_ruffle"])
        c.set(x, by + 1, C["blanket_hi"])
        for y in range(by + 2, HEIGHT):
            col = C["blanket_main"] if ((x // 5 + y // 4) % 2 == 0) else C["blanket_dark"]
            c.set(x, y, col)
    for sx, sy in [(20, 25), (32, 28), (46, 25), (56, 28)]:
        c.set(sx, sy, C["blanket_star"])

    # Re-draw Lulu's plump tangerine poking hilariously above the blanket mound when ducked!
    if lulu_y >= 18:
        draw_tangerine_hi(c, 47 + shiver, 17 + breath)

    if 30 <= f < 38:
        draw_exclaim(c, 49, 2)
    elif 56 <= f < 74:
        draw_heart(c, 39, 10 - (f - 56) // 5)
    elif 94 <= f < 112:
        draw_heart(c, 39, 10 - (f - 94) // 5)
    return c.img


def render_thunderstorm(f: int, is_night: bool) -> Image.Image:
    if is_night:
        return draw_closeup_storm_blanket(f)

    # DAY: Outdoor Wooden Park Shelter — Overconfident Lulu Leaps Under the Roof!
    flash_1 = f in (30, 31, 34)
    flash_2 = f in (82, 83, 86)
    is_flashing = flash_1 or flash_2
    shiver_1 = 30 <= f <= 42
    shiver_2 = 82 <= f <= 94

    c = Canvas()
    if is_flashing:
        c.gradient_v((102, 114, 152, 255), (62, 76, 112, 255), 0, 29)
    else:
        c.gradient_v((34, 46, 68, 255), (56, 72, 98, 255), 0, 29)

    # Wet stormy park grass ground + puddles on right
    c.hline(0, 28, WIDTH, (42, 74, 58, 255))
    c.rect(0, 29, WIDTH, 3, (26, 46, 44, 255))
    # Rain puddle outside the shelter on the right
    c.hline(50, 29, 12, (82, 134, 178, 255))
    if f % 10 < 5:
        c.set(53, 28, C["rain_bright"])
        c.set(59, 28, C["rain_bright"])

    cloud_top = (104, 118, 156, 255) if is_flashing else C["cloud_dark"]
    cloud_bot = (146, 162, 198, 255) if is_flashing else C["cloud_mid"]
    draw_storm_canopy(c, f, cloud_top, cloud_bot)

    # Blazing outdoor lightning bolts striking outside on the right
    if flash_1:
        for bx, by in [(61, 2), (60, 3), (59, 4), (60, 5), (61, 6), (60, 7), (59, 8), (60, 9), (61, 10), (60, 11)]:
            c.set(bx - 1, by, C["bolt_glow"])
            c.set(bx + 1, by, C["bolt_glow"])
            c.set(bx, by, C["bolt_core"])
    elif flash_2:
        for bx, by in [(56, 3), (57, 4), (58, 5), (57, 6), (56, 7), (57, 8), (58, 9), (57, 10), (56, 11)]:
            c.set(bx - 1, by, C["bolt_glow"])
            c.set(bx + 1, by, C["bolt_glow"])
            c.set(bx, by, C["bolt_core"])

    # Cozy Wooden Park Shelter / Gazebo (x=21..51 — clear of 20x12 upper-left HUD!)
    wood_hi = (176, 114, 68, 255)
    wood_mid = (132, 78, 44, 255)
    wood_dark = (84, 46, 26, 255)
    roof_hi = (196, 108, 66, 255)
    roof_mid = (154, 72, 42, 255)
    roof_dark = (96, 42, 24, 255)

    # Back wall posts, railing & dry wooden shelter deck (drawn behind characters)
    c.rect(22, 8, 2, 20, wood_mid)
    c.vline(22, 8, 20, wood_hi)
    c.rect(48, 8, 2, 20, wood_mid)
    c.vline(49, 8, 20, wood_dark)
    # Cozy park shelter back wooden bench rail
    c.hline(24, 21, 24, wood_hi)
    c.hline(24, 22, 24, wood_dark)
    c.hline(24, 25, 24, wood_mid)
    # Dry wooden shelter floor
    c.hline(21, 28, 30, wood_hi)
    c.hline(21, 29, 30, wood_dark)

    bob = bob_offset(f, period=30, phase=0)
    shiver = (1 if (f % 2 == 0) else 0) if (shiver_1 or shiver_2) else 0

    lumei_x, lumei_y = 22 + shiver, 9 + (1 if (shiver_1 or shiver_2) else bob)
    lumei_mood = "startled" if (shiver_1 or shiver_2) else ("blink" if (f % 50) in (14, 15) else "happy")

    lulu_x, lulu_y = 48, 10 + bob
    lulu_mood = "chill"
    orange_pop = 0

    if 30 <= f < 46:
        lulu_mood = "startled"
        t = (f - 30) / 16.0
        lulu_x = lerp_i(48, 34, ease_in_out(t))
        lulu_y = 10 - int(round(3 * math.sin(math.pi * t)))
        orange_pop = -2 if f < 38 else 0
        if f < 38:
            draw_exclaim(c, lulu_x + 7, lulu_y - 4)
    elif 46 <= f < 106:
        lulu_x = 34 + shiver
        lulu_y = 10 + (1 if shiver_2 else bob)
        lulu_mood = "startled" if shiver_2 else "squint"
        if 56 <= f < 76:
            lumei_mood, lulu_mood = "delighted", "happy"
            draw_heart(c, 35, 9 - (f - 56) // 7)
    elif 106 <= f < 132:
        t = ease_in_out((f - 106) / 24)
        lulu_x = lerp_i(34, 48, t)
        lulu_mood = "chill"
        lumei_mood = "delighted" if f < 122 else "happy"

    draw_lumei_hi(c, lumei_x, lumei_y, mood=lumei_mood)
    draw_lulu_hi(c, lulu_x, lulu_y + orange_pop, mood=lulu_mood)

    # Sloped wooden shelter roof drawn OVER posts so characters stand neatly under the eaves
    c.hline(25, 4, 23, roof_hi)
    c.hline(23, 5, 27, roof_mid)
    c.hline(25, 5, 21, roof_hi)
    c.hline(21, 6, 31, roof_mid)
    c.hline(21, 7, 31, roof_dark)
    # Little rain-drip droplets off the roof edge
    if f % 6 < 3:
        c.set(21, 8, C["rain_bright"])
        c.set(51, 8, C["rain_bright"])

    # Heavy pouring rain — blocked cleanly by the shelter roof (x=21..51, y>=6)!
    for x0, y0, bright in RAIN_DROPS_64:
        rx = wrap_pos(x0, 5, f, WIDTH, direction=-1)
        ry = wrap_pos(y0, 15, f, HEIGHT, direction=1)
        if 21 <= rx <= 51 and ry >= 6:
            if ry <= 8:
                # Rain splash sparks bouncing off the top of the shelter roof!
                c.set(rx, 4 if 25 <= rx <= 47 else 5, C["white"])
            continue
        c.set(rx, ry, C["rain_bright"] if (bright or is_flashing) else C["rain_dim"])
        c.set((rx + 1) % WIDTH, (ry - 1) % HEIGHT, C["rain_dim"])

    return c.img


# ---------------------------------------------------------------------------
# 11. THUNDERSTORM + HAIL (High-Res Batch 3): Bouncing Hailstone Shield Scramble!
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
    lumei_x, lumei_y = 22, 9 + bob
    lulu_x, lulu_y = 39, 10 + bob
    shield_cx, shield_y = 38, 2 + bob
    shield_up = True
    lumei_mood, lulu_mood = "squint", "chill"
    orange_pop = 0

    if 24 <= f < 46:
        shield_up = f >= 38
        lulu_x = lerp_i(39, 47, ease_in_out((f - 24) / 10)) if f < 34 else lerp_i(47, 39, ease_in_out((f - 34) / 10))
        if 32 <= f < 40:
            lulu_mood, orange_pop = "startled", -2
            draw_exclaim(c, lulu_x + 8, lulu_y - 6)
        lumei_mood = "spicy"
    elif 46 <= f < 118:
        shield_up = True
        lumei_x, lulu_x, shield_cx = 23, 38, 38
        lumei_mood = "startled" if flash else "happy"
        lulu_mood = "startled" if flash else "squint"
        if 70 <= f < 94:
            lumei_mood, lulu_mood = "delighted", "happy"
            draw_heart(c, 38, 7 - (f - 70) // 6)

    draw_lumei_hi(c, lumei_x, lumei_y, mood=lumei_mood)
    draw_lulu_hi(c, lulu_x, lulu_y + orange_pop, mood=lulu_mood)
    if shield_up:
        # Wide sturdy silver shield covering both high-res characters!
        c.hline(shield_cx - 12, shield_y, 25, C["shield_hi"])
        c.hline(shield_cx - 14, shield_y + 1, 29, C["shield_mid"])
        c.hline(shield_cx - 10, shield_y + 1, 12, C["shield_hi"])
        c.hline(shield_cx - 15, shield_y + 2, 31, C["shield_mid"])
        c.hline(shield_cx - 15, shield_y + 3, 31, C["shield_dark"])

    for x0, y0 in HAIL_STONES_64:
        hx = wrap_pos(x0, 4, f, WIDTH, direction=-1)
        hy = wrap_pos(y0, 15, f, HEIGHT, direction=1)
        if shield_up and (shield_cx - 15) <= hx <= (shield_cx + 15) and hy >= shield_y + 2:
            if hy <= shield_y + 6:
                c.set(hx, shield_y - 1, C["white"])
                c.set((hx + 2) % WIDTH, shield_y, C["hail_rim"])
            continue
        c.rect(hx, hy, 2, 2, C["hail_core"])
        c.set(hx + 1, hy + 1, C["hail_rim"])
        if hy >= 27:
            c.set((hx - 1) % WIDTH, 26, C["white"])
            c.set((hx + 2) % WIDTH, 26, C["hail_rim"])
    return c.img


# ---------------------------------------------------------------------------
# 12. WINDY (High-Res Batch 1): Day Kite & Gust Rescue | Night Bonnet Hero Lulu!
# ---------------------------------------------------------------------------
def render_windy(f: int, is_night: bool) -> Image.Image:
    c = Canvas()
    if is_night:
        c.gradient_v((6, 14, 28, 255), (12, 26, 44, 255), 0, 28)
        draw_stars(c, f, dense=False)
        draw_moon(c, 57, 2)
    else:
        c.gradient_v((26, 72, 114, 255), (56, 118, 152, 255), 0, 28)
        draw_sun(c, 57, 5, f)

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
    orange_jiggle = 1 if (f % 15) < 7 else 0

    if not is_night:
        # DAY: Runaway Kite & Mega Gust Blows Lulu OFF-SCREEN -> Lumei Rescues Him!
        lumei_x, lumei_y = 20, 8 + bob_lumei
        lulu_x, lulu_y = 43, 9 + bob_lulu
        lumei_mood, lulu_mood = "squint", "squint"
        lumei_lean, lulu_lean = 1, 1
        lumei_walk, lulu_walk = 0, 0
        lulu_has_tang = True
        loose_tang: Optional[Tuple[int, int]] = None
        kite_pos: Optional[Tuple[int, int]] = (36 + (1 if (f % 6 < 3) else 0), 2 + (1 if (f % 10 < 5) else 0))
        kite_attached = True

        if 24 <= f < 46:
            # Kite snaps & whips off-screen right; Lulu & tangerine blow OFF-SCREEN right!
            kite_attached = False
            kt = min(1.0, (f - 24) / 12)
            kite_pos = (lerp_i(37, 70, kt), lerp_i(3, -4, kt))
            lulu_has_tang = False
            t = ease_in_out((f - 24) / 22)
            lulu_x = lerp_i(43, 70, t)
            lulu_y = 9 - int(round(5 * math.sin(math.pi * t)))
            lulu_mood = "startled" if f < 34 else "dizzy"
            lulu_walk = 1 if (f % 4 < 2) else 2
            tx = lerp_i(50, 72, ease_in_out((f - 24) / 14))
            ty = 6 - int(round(4 * math.sin(math.pi * min(1.0, (f - 24) / 14))))
            loose_tang = (tx, ty)
            lumei_mood = "startled"
            lumei_x = lerp_i(20, 26, ease_in_out((f - 24) / 22))
        elif 46 <= f < 64:
            kite_pos = None
            lulu_x, lulu_has_tang = 72, False
            if f < 52:
                lumei_x, lumei_mood = 26, "startled"
                draw_exclaim(c, lumei_x + 7, lumei_y - 6)
            else:
                lumei_x = lerp_i(26, 70, ease_in_out((f - 52) / 12))
                lumei_mood = "spicy"
                lumei_walk = 1 if (f % 4 < 2) else 2
        elif 64 <= f < 76:
            # Empty windswept stage beat!
            kite_pos = None
            lumei_x, lulu_x, lulu_has_tang = 72, 72, False
        elif 76 <= f < 116:
            kite_pos = None
            t = ease_in_out((f - 76) / 38)
            lumei_x = lerp_i(68, 20, t)
            lulu_x = lerp_i(86, 43, t)
            lumei_mood = "spicy"
            lulu_mood = "dizzy" if f < 106 else "chill"
            lumei_lean, lulu_lean = 0, 0
            lumei_walk = 1 if (f % 4 < 2) else 2
            lulu_walk = 2 if (f % 4 < 2) else 1
            lulu_has_tang = f >= 108
            if not lulu_has_tang:
                rt = ease_in_out(max(0.0, (f - 88) / 20))
                loose_tang = (lerp_i(68, 50, rt), lerp_i(24, 6, rt) - int(round(3 * math.sin(math.pi * rt))))
        elif 116 <= f < 136:
            kite_pos = None if f < 130 else (36, 2)
            kite_attached = f >= 130
            lumei_mood = "spicy"
            lulu_mood = "blink" if f < 124 else "chill"
            lumei_lean, lulu_lean = 0, 0
            draw_anger_steam(c, lumei_x + 7, lumei_y - 4, f)

        if kite_pos is not None:
            if kite_attached:
                # Diagonal kite string from Lulu's paw up to kite
                for i in range(1, 14):
                    sx = lerp_i(lulu_x + 3, kite_pos[0] + 2, i / 14.0)
                    sy = lerp_i(lulu_y + 13, kite_pos[1] + 4, i / 14.0)
                    c.set(sx, sy, C["kite_string"])
            draw_kite(c, kite_pos[0], kite_pos[1], f)

        draw_lumei_hi(c, lumei_x, lumei_y, mood=lumei_mood, lean_x=lumei_lean, sprout_sway=1, walk_step=lumei_walk)
        draw_lulu_hi(c, lulu_x, lulu_y, mood=lulu_mood, lean_x=lulu_lean, orange_shift=orange_jiggle, has_tangerine=lulu_has_tang, walk_step=lulu_walk)
        if loose_tang is not None:
            draw_tangerine_hi(c, loose_tang[0], loose_tang[1])
    else:
        # NIGHT: Heroic Lulu Chases Lumei's Blown-Off Pink Bonnet OFF-SCREEN & Saves It!
        lumei_x, lumei_y = 20, 8 + bob_lumei
        lulu_x, lulu_y = 43, 9 + bob_lulu
        lumei_mood, lulu_mood = "squint", "squint"
        lumei_lean, lulu_lean = 1, 1
        lulu_walk = 0
        lumei_has_bonnet = True
        bonnet_pos: Optional[Tuple[int, int]] = None

        if 22 <= f < 46:
            # WHOOSH! Lumei's pink ruffled bonnet lifts off & tumbles OFF-SCREEN right!
            lumei_has_bonnet = False
            lumei_mood = "startled"
            t = ease_in_out((f - 22) / 22)
            bx = lerp_i(22, 70, t)
            by = 8 - int(round(5 * math.sin(math.pi * t)))
            bonnet_pos = (bx, by)
            if f < 36:
                draw_exclaim(c, lumei_x + 7, lumei_y - 5)
            lulu_mood = "startled" if f < 38 else "determined"
        elif 46 <= f < 72:
            # Usually-lazy Lulu turns HERO and sprints OFF-SCREEN right to catch it!
            lumei_has_bonnet = False
            lumei_mood = "startled"
            lulu_mood = "determined"
            lulu_walk = 1 if (f % 4 < 2) else 2
            if f < 64:
                lulu_x = lerp_i(43, 70, ease_in_out((f - 46) / 18))
            else:
                lulu_x = 70
        elif 72 <= f < 114:
            # Triumphant Lulu marches back from right holding Lumei's pink bonnet aloft & plops it on!
            lulu_mood = "happy"
            lulu_lean, lumei_lean = 0, 0
            if f < 98:
                lumei_has_bonnet = False
                lumei_mood = "startled" if f < 88 else "delighted"
                lulu_x = lerp_i(70, 34, ease_in_out((f - 72) / 26))
                lulu_walk = 1 if (f % 4 < 2) else 2
                bonnet_pos = (lulu_x - 4, 10 + (f % 2))
            elif f < 108:
                # Plops bonnet gently back onto Lumei's head!
                lumei_has_bonnet = f >= 104
                lumei_mood = "delighted"
                lulu_x = 34
                if not lumei_has_bonnet:
                    bonnet_pos = (lerp_i(30, 21, (f - 98) / 6), lerp_i(10, 7, (f - 98) / 6))
            else:
                lumei_has_bonnet = True
                lumei_mood = "delighted"
                lulu_x = 34
        elif 114 <= f < 136:
            # Delighted Lumei beams with twin hearts while proud Lulu strolls back to his spot!
            lumei_has_bonnet = True
            lumei_mood, lulu_mood = "delighted", "happy"
            lumei_lean, lulu_lean = 0, 0
            lulu_x = lerp_i(34, 43, ease_in_out((f - 118) / 16)) if f >= 118 else 34
            lulu_walk = (1 if (f % 4 < 2) else 2) if f >= 118 else 0
            draw_heart(c, 36, 7 - (f - 114) // 5)
            if f >= 120:
                draw_heart(c, 29, 8 - (f - 120) // 5)

        draw_lumei_hi(c, lumei_x, lumei_y, mood=lumei_mood, has_bonnet=lumei_has_bonnet, lean_x=lumei_lean, sprout_sway=1)
        draw_lulu_hi(c, lulu_x, lulu_y, mood=lulu_mood, lean_x=lulu_lean, orange_shift=orange_jiggle, walk_step=lulu_walk)
        if bonnet_pos is not None:
            draw_loose_bonnet(c, bonnet_pos[0], bonnet_pos[1])

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
# 28-State Renderer Registry (12 Weather Types x Day/Night + Warm/Cold)
# ---------------------------------------------------------------------------
SCENE_RENDERERS: Dict[str, Callable[[int], Image.Image]] = {
    "clear_day_warm": render_clear_day,
    "clear_day_cold": render_clear_day_cold,
    "clear_night_warm": lambda f: render_clear_night(f, is_cold=False),
    "clear_night_cold": lambda f: render_clear_night(f, is_cold=True),
    "partly_cloudy_day_warm": lambda f: render_partly_cloudy(f, is_night=False, is_cold=False),
    "partly_cloudy_day_cold": lambda f: render_partly_cloudy(f, is_night=False, is_cold=True),
    "partly_cloudy_night_warm": lambda f: render_partly_cloudy(f, is_night=True, is_cold=False),
    "partly_cloudy_night_cold": lambda f: render_partly_cloudy(f, is_night=True, is_cold=True),
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
SCENE_RENDERERS.update(build_holiday_renderers(sys.modules[__name__]))


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
    """Compact storyboard sheet across all 28 states (3 key beats each)."""
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    sample_indices = [0, 62, 120]
    pad = 6
    label_h = 14
    cell_w = WIDTH * scale
    cell_h = HEIGHT * scale
    cols = len(sample_indices) * 2
    rows = (len(STATES) + 1) // 2
    sheet_w = pad + cols * (cell_w + pad)
    sheet_h = pad + rows * (cell_h + label_h + pad)

    sheet = Image.new("RGB", (sheet_w, sheet_h), (14, 16, 24))
    draw = ImageDraw.Draw(sheet)

    for idx, st in enumerate(STATES):
        row = idx // 2
        half = idx % 2
        y_top = pad + row * (cell_h + label_h + pad)
        for j, f_idx in enumerate(sample_indices):
            col = half * len(sample_indices) + j
            x_left = pad + col * (cell_w + pad)
            draw.text((x_left, y_top), f"{st} f={f_idx}", fill=(220, 228, 240))
            upscaled = state_frames[st][f_idx].convert("RGB").resize(
                (cell_w, cell_h), Image.Resampling.NEAREST
            )
            sheet.paste(upscaled, (x_left, y_top + label_h))

    out_path = PREVIEWS_DIR / "all_states_contact_sheet.png"
    sheet.save(out_path)
    return out_path


def build_holiday_review_sheet(state_frames: Dict[str, List[Image.Image]], scale: int = 4) -> Path:
    """High-res 4-beat storyboard sheet across all 11 holiday & birthday states."""
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    sample_indices = [0, 44, 76, 112]
    pad = 8
    label_h = 16
    cell_w = WIDTH * scale
    cell_h = HEIGHT * scale
    cols = len(sample_indices)
    rows = len(HOLIDAY_STATES)
    sheet_w = pad + cols * (cell_w + pad)
    sheet_h = pad + rows * (cell_h + label_h + pad)

    sheet = Image.new("RGB", (sheet_w, sheet_h), (12, 14, 22))
    draw = ImageDraw.Draw(sheet)

    for r_idx, st in enumerate(HOLIDAY_STATES):
        y_top = pad + r_idx * (cell_h + label_h + pad)
        for c_idx, f_idx in enumerate(sample_indices):
            x_left = pad + c_idx * (cell_w + pad)
            draw.text((x_left, y_top), f"{st} (f={f_idx})", fill=(232, 238, 248))
            upscaled = state_frames[st][f_idx].convert("RGB").resize(
                (cell_w, cell_h), Image.Resampling.NEAREST
            )
            sheet.paste(upscaled, (x_left, y_top + label_h))
            # Subtle 20x12 upper-left HUD safe-zone guide box
            draw.rectangle(
                [x_left, y_top + label_h, x_left + 20 * scale - 1, y_top + label_h + 12 * scale - 1],
                outline=(120, 140, 180),
                width=1,
            )

    out_path = PREVIEWS_DIR / "holidays_and_birthdays_review.png"
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
        hsheet = build_holiday_review_sheet(all_frames)
        print(f"Saved holiday & birthday review sheet -> {hsheet}")

    if not args.no_inject:
        inject_sprites_into_star(b64_map, STAR_FILE)


if __name__ == "__main__":
    main()
