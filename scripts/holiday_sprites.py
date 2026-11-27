#!/usr/bin/env python3
"""
Special Holiday & Birthday 64x32 Animated Storyboards for Capybara Clock
(Lumei & Lulu — stylized high-res pixel art matching all 28 weather states).

11 Special Occasions (exact 150 frames @ 100ms = 15.0s, seamless loop=0):
  1. holiday_new_year       (Dec 31 18:00+ & Jan 1: Fireworks & Sparkler Toast)
  2. holiday_lunar_new_year (Lunar New Year: Red Lanterns & Lucky Hongbao)
  3. holiday_valentines     (Feb 14: Heart Box, Rose & Floating Hearts)
  4. birthday_lulu          (Feb 20: Lulu's Birthday Crown, Cake & Confetti!)
  5. holiday_st_patricks    (Mar 17: Rainbow, Shamrocks & Pot of Gold)
  6. holiday_easter         (Easter Sunday: Painted Egg Hunt & Hatching Chick)
  7. holiday_independence   (Jul 4: Red, White & Blue Fireworks Spectacular)
  8. birthday_lumei         (Oct 20: Lumei's Birthday Crown, Strawberry Cake & Gift!)
  9. holiday_halloween      (Oct 31: Witch Hat, Ghost Lulu & Candy Jack-o'-Lantern)
 10. holiday_thanksgiving   (4th Thu of Nov: Cozy Autumn Harvest & Pumpkin Pie)
 11. holiday_christmas      (Dec 24 18:00+ & Dec 25: Santa Hats, Tree & Present Pop)

All scenes preserve clear 20x12 upper-left HUD space (x=0..19, y=0..11).
"""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Tuple

from PIL import Image

HOLIDAY_STATES: Tuple[str, ...] = (
    "holiday_new_year",
    "holiday_lunar_new_year",
    "holiday_valentines",
    "birthday_lulu",
    "holiday_st_patricks",
    "holiday_easter",
    "holiday_independence",
    "birthday_lumei",
    "holiday_halloween",
    "holiday_thanksgiving",
    "holiday_christmas",
)

# Festive color additions (RGBA)
HC = {
    "red_bright": (244, 52, 66, 255),
    "red_deep": (176, 24, 38, 255),
    "red_dark": (118, 16, 26, 255),
    "gold_bright": (255, 232, 84, 255),
    "gold_mid": (246, 184, 34, 255),
    "gold_deep": (188, 124, 18, 255),
    "pink_hot": (255, 92, 152, 255),
    "pink_soft": (255, 174, 206, 255),
    "pink_deep": (204, 48, 108, 255),
    "cyan_bright": (92, 234, 255, 255),
    "blue_usa": (42, 114, 248, 255),
    "blue_hi": (124, 184, 255, 255),
    "violet_bright": (188, 112, 255, 255),
    "violet_dark": (78, 34, 126, 255),
    "emerald_hi": (98, 236, 124, 255),
    "emerald_main": (38, 184, 78, 255),
    "emerald_dark": (20, 116, 48, 255),
    "pine_hi": (44, 146, 72, 255),
    "pine_main": (24, 104, 48, 255),
    "pine_dark": (14, 68, 32, 255),
    "pumpkin_hi": (255, 166, 48, 255),
    "pumpkin_main": (238, 114, 22, 255),
    "pumpkin_dark": (174, 68, 14, 255),
    "ghost_white": (240, 246, 255, 255),
    "ghost_shade": (182, 198, 226, 255),
    "bat_dark": (22, 14, 34, 255),
    "bat_wing": (48, 32, 70, 255),
    "chick_hi": (255, 244, 128, 255),
    "chick_main": (255, 214, 52, 255),
    "egg_mint": (132, 238, 202, 255),
    "egg_lav": (198, 152, 255, 255),
    "egg_pink": (255, 148, 194, 255),
    "egg_gold": (255, 218, 88, 255),
    "iron_dark": (34, 38, 48, 255),
    "iron_mid": (64, 70, 86, 255),
    "iron_hi": (112, 120, 142, 255),
    "wood_hi": (178, 114, 58, 255),
    "wood_main": (136, 78, 36, 255),
    "wood_dark": (88, 46, 20, 255),
    "pie_pumpkin": (228, 112, 34, 255),
    "pie_hi": (248, 148, 56, 255),
    "smoke": (214, 226, 242, 175),
    "glow_warm": (255, 208, 92, 80),
    "glow_red": (255, 84, 56, 70),
    "glow_moon": (255, 236, 156, 48),
}


def build_holiday_renderers(gs) -> Dict[str, Callable[[int], Image.Image]]:
    """
    Build all 11 holiday & birthday renderers using the shared Canvas, palette C,
    and stylized high-res character primitives from generate_sprites.py.
    """
    WIDTH = gs.WIDTH
    HEIGHT = gs.HEIGHT
    NUM_FRAMES = gs.NUM_FRAMES
    C = gs.C
    Canvas = gs.Canvas
    draw_lumei_hi = gs.draw_lumei_hi
    draw_lulu_hi = gs.draw_lulu_hi
    draw_tangerine_hi = gs.draw_tangerine_hi
    draw_heart = gs.draw_heart
    draw_exclaim = gs.draw_exclaim
    bob_offset = gs.bob_offset
    ease_in_out = gs.ease_in_out
    lerp_i = gs.lerp_i
    wave_sin = gs.wave_sin
    wrap_pos = gs.wrap_pos

    # -----------------------------------------------------------------------
    # Shared Festive Prop & Costume Primitives
    # -----------------------------------------------------------------------
    def draw_sparkle(c, sx: int, sy: int, col=None, big: bool = False) -> None:
        col = col or HC["gold_bright"]
        c.set(sx, sy, C["white"])
        if big:
            c.set(sx - 1, sy, col)
            c.set(sx + 1, sy, col)
            c.set(sx, sy - 1, col)
            c.set(sx, sy + 1, col)

    def draw_twinkle_stars(c, f: int, stars: List[Tuple[int, int, int]]) -> None:
        for sx, sy, phase in stars:
            if sx < 20 and sy < 12:
                continue
            bright = ((f + phase) % 15) < 8
            c.set(sx, sy, C["star_bright"] if bright else C["star_dim"])

    def draw_firework(c, cx: int, cy: int, prog: float, c_core, c_mid, c_tip) -> None:
        """Crisp expanding 8-ray pixel firework (prog in 0.0..1.0)."""
        if prog < 0.0 or prog >= 1.0:
            return
        if prog < 0.25:
            # Rising launch trail
            t = prog / 0.25
            ry = lerp_i(25, cy, t)
            c.set(cx, ry, C["white"])
            c.set(cx, ry + 1, c_core)
            c.set(cx, ry + 2, c_mid)
            return
        # Burst bloom (0.25..1.0)
        bt = (prog - 0.25) / 0.75
        rad = 1.0 + 6.5 * math.sin(bt * math.pi * 0.55)
        gravity = int(round(2.5 * bt * bt))
        if bt < 0.35:
            c.set(cx, cy, C["white"])
        dirs = [
            (1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0),
            (0.72, 0.72), (-0.72, 0.72), (0.72, -0.72), (-0.72, -0.72),
        ]
        for idx, (dx, dy) in enumerate(dirs):
            px = int(round(cx + dx * rad))
            py = int(round(cy + dy * rad)) + gravity
            if px < 20 and py < 12:
                continue
            if bt < 0.45:
                col = C["white"] if idx % 2 == 0 else c_core
            elif bt < 0.78:
                col = c_mid if (idx % 2 == 0) else c_core
            else:
                if (idx + int(bt * 10)) % 2 == 0:
                    continue
                col = c_tip
            c.set(px, py, col)
            if bt < 0.65:
                tx = int(round(cx + dx * rad * 0.55))
                ty = int(round(cy + dy * rad * 0.55)) + gravity // 2
                if not (tx < 20 and ty < 12):
                    c.set(tx, ty, c_mid)

    def draw_party_hat(c, cx: int, cy: int, col_main, col_stripe, col_pom) -> None:
        """Cute 5w x 5h striped cone party hat centered at cx, base at cy."""
        c.set(cx, cy - 4, col_pom)
        c.set(cx, cy - 3, col_main)
        c.hline(cx - 1, cy - 2, 3, col_stripe)
        c.hline(cx - 1, cy - 1, 3, col_main)
        c.hline(cx - 2, cy, 5, col_stripe)
        c.set(cx - 2, cy, col_main)
        c.set(cx + 2, cy, col_main)

    def draw_birthday_crown(c, cx: int, cy: int) -> None:
        """Sparkling 7w x 4h golden crown with jewel accents (base at cy)."""
        c.hline(cx - 3, cy, 7, HC["gold_deep"])
        c.hline(cx - 3, cy - 1, 7, HC["gold_mid"])
        c.set(cx - 3, cy - 2, HC["gold_bright"])
        c.set(cx - 3, cy - 3, HC["gold_bright"])
        c.set(cx, cy - 2, HC["gold_bright"])
        c.set(cx, cy - 3, C["white"])
        c.set(cx + 3, cy - 2, HC["gold_bright"])
        c.set(cx + 3, cy - 3, HC["gold_bright"])
        c.set(cx - 1, cy - 2, HC["gold_mid"])
        c.set(cx + 1, cy - 2, HC["gold_mid"])
        # Jewels
        c.set(cx, cy - 1, HC["pink_hot"])
        c.set(cx - 2, cy - 1, HC["cyan_bright"])
        c.set(cx + 2, cy - 1, HC["cyan_bright"])

    def draw_santa_hat(c, cx: int, cy: int) -> None:
        """Festive tilted red Santa hat with white fur brim & pom-pom (base at cy)."""
        c.hline(cx - 3, cy, 7, C["white"])
        c.hline(cx - 2, cy - 1, 5, HC["red_bright"])
        c.hline(cx - 1, cy - 2, 4, HC["red_bright"])
        c.hline(cx, cy - 3, 3, HC["red_deep"])
        c.set(cx + 2, cy - 2, HC["red_bright"])
        c.set(cx + 3, cy - 1, HC["red_deep"])
        c.set(cx + 4, cy - 1, C["white"])
        c.set(cx + 4, cy, C["white"])

    def draw_witch_hat(c, cx: int, cy: int) -> None:
        """Cute pointed Halloween witch hat with crisp violet edge highlight & gold buckle."""
        c.hline(cx - 4, cy, 9, HC["violet_dark"])
        c.hline(cx - 3, cy, 7, HC["bat_dark"])
        c.set(cx - 4, cy, HC["violet_bright"])
        c.set(cx + 4, cy, HC["violet_bright"])
        c.hline(cx - 3, cy - 1, 7, HC["violet_bright"])
        c.set(cx, cy - 1, HC["gold_bright"])
        c.hline(cx - 3, cy - 2, 7, HC["violet_dark"])
        c.hline(cx - 2, cy - 2, 5, HC["bat_dark"])
        c.hline(cx - 2, cy - 3, 5, HC["violet_dark"])
        c.hline(cx - 1, cy - 3, 3, HC["bat_dark"])
        c.hline(cx - 1, cy - 4, 3, HC["violet_bright"])
        c.set(cx, cy - 4, HC["violet_dark"])
        c.set(cx, cy - 5, HC["violet_bright"])
        c.set(cx + 1, cy - 6, HC["violet_bright"])

    def draw_leprechaun_hat(c, cx: int, cy: int) -> None:
        """Emerald St. Patrick's top hat with dark band & gleaming gold buckle."""
        c.hline(cx - 4, cy, 9, HC["emerald_dark"])
        c.hline(cx - 3, cy, 7, HC["emerald_main"])
        c.hline(cx - 2, cy - 1, 5, HC["iron_dark"])
        c.set(cx, cy - 1, HC["gold_bright"])
        c.rect(cx - 2, cy - 4, 5, 3, HC["emerald_main"])
        c.hline(cx - 2, cy - 4, 5, HC["emerald_hi"])
        c.vline(cx + 2, cy - 4, 3, HC["emerald_dark"])

    def draw_bunny_ears(c, cx: int, cy: int, twitch: int = 0) -> None:
        """Tall cute Easter bunny ears framed wide around Lulu's tangerine."""
        # Left ear
        c.rect(cx - 5, cy - 4, 2, 5, C["white"])
        c.vline(cx - 4, cy - 3, 3, HC["pink_soft"])
        # Right ear (optional playful tip fold when twitch == 1)
        if twitch:
            c.rect(cx + 3, cy - 3, 2, 4, C["white"])
            c.hline(cx + 4, cy - 3, 2, C["white"])
            c.vline(cx + 3, cy - 2, 2, HC["pink_soft"])
        else:
            c.rect(cx + 3, cy - 4, 2, 5, C["white"])
            c.vline(cx + 3, cy - 3, 3, HC["pink_soft"])

    def draw_bunting(c, x0: int, x1: int, y: int, f: int, colors) -> None:
        """Compact scalloped festive pennant flags (kept strictly right of HUD!)."""
        for x in range(x0, x1 + 1):
            sag = 1 if ((x - x0) % 10 in (4, 5)) else 0
            c.set(x, y + sag, C["white"])
        idx = 0
        for px in range(x0 + 1, x1 - 2, 5):
            sag = 1 if ((px - x0) % 10 in (4, 5)) else 0
            col = colors[(idx + (f // 30)) % len(colors)]
            c.hline(px, y + sag + 1, 3, col)
            c.set(px + 1, y + sag + 2, col)
            idx += 1

    def draw_balloon(c, bx: int, by: int, c_hi, c_main, c_dark, sway: int = 0) -> None:
        """Plump shiny 5x6 balloon with dangling string."""
        c.hline(bx + 1, by, 3, c_hi)
        c.rect(bx, by + 1, 5, 3, c_main)
        c.set(bx + 1, by + 1, C["white"])
        c.vline(bx + 4, by + 1, 3, c_dark)
        c.hline(bx + 1, by + 4, 3, c_dark)
        c.set(bx + 2, by + 5, c_dark)
        # Wavy string
        c.set(bx + 2, by + 6, C["kite_string"])
        c.set(bx + 2 + sway, by + 7, C["kite_string"])
        c.set(bx + 2, by + 8, C["kite_string"])
        c.set(bx + 2 - sway, by + 9, C["kite_string"])

    def draw_birthday_cake(c, cx: int, cy: int, f: int, *, pink: bool = False, lit: bool = True, smoke_step: int = 0) -> None:
        """Festive 9w x 6h two-tier birthday cake with 3 flickering candles!"""
        frost = HC["pink_soft"] if pink else C["cake_cream"]
        trim = HC["pink_hot"] if pink else HC["cyan_bright"]
        # Plate
        c.hline(cx, cy + 6, 9, C["plate"])
        # Bottom tier
        c.rect(cx + 1, cy + 3, 7, 3, C["cake_sponge"])
        c.hline(cx + 1, cy + 3, 7, frost)
        c.set(cx + 2, cy + 4, trim)
        c.set(cx + 4, cy + 4, HC["gold_bright"])
        c.set(cx + 6, cy + 4, trim)
        # Top tier
        c.rect(cx + 2, cy + 1, 5, 2, frost)
        c.hline(cx + 2, cy + 2, 5, trim)
        c.hline(cx + 2, cy + 1, 5, C["white"])
        # 3 striped candles
        for k, kx in enumerate((cx + 2, cx + 4, cx + 6)):
            c.vline(kx, cy - 1, 2, C["candle_wax"] if k == 1 else trim)
            if lit:
                flicker = 1 if ((f + k * 2) % 6 < 3) else 0
                for dy in range(-4, 0):
                    for dx in range(-1, 2):
                        c.set(kx + dx, cy + dy, HC["glow_warm"])
                c.set(kx, cy - 2, C["flame_org"])
                c.set(kx + (flicker if k == 0 else -flicker if k == 2 else 0), cy - 3, C["flame_hi"])
            elif 0 < smoke_step <= 8:
                sy = cy - 2 - (smoke_step // 2)
                sx = kx + (1 if (smoke_step + k) % 2 == 0 else 0)
                c.set(sx, sy, HC["smoke"])

    def draw_gift_box(c, gx: int, gy: int, c_box, c_dark, c_rib, *, lid_lift: int = 0) -> None:
        """Cute 7w x 6h wrapped gift box with bow & optional popping lid."""
        # Base box
        c.rect(gx, gy + 2, 7, 4, c_box)
        c.vline(gx + 6, gy + 2, 4, c_dark)
        c.hline(gx, gy + 5, 7, c_dark)
        c.vline(gx + 3, gy + 2, 4, c_rib)
        # Lid + bow
        ly = gy - lid_lift
        c.hline(gx - 1, ly + 1, 9, c_box)
        c.set(gx + 7, ly + 1, c_dark)
        c.set(gx + 3, ly + 1, c_rib)
        c.hline(gx + 1, ly, 2, c_rib)
        c.hline(gx + 4, ly, 2, c_rib)
        c.set(gx + 3, ly, C["white"])

    def draw_confetti(c, f: int, active: bool, x_min: int = 21) -> None:
        if not active:
            return
        cols = [HC["pink_hot"], HC["gold_bright"], HC["cyan_bright"], HC["emerald_hi"], HC["violet_bright"], HC["red_bright"]]
        seeds = [
            (23, 2, 0), (29, 7, 1), (35, 4, 2), (41, 10, 3), (47, 3, 4),
            (53, 8, 5), (59, 5, 0), (26, 13, 2), (38, 15, 4), (50, 12, 1),
            (61, 16, 3), (32, 19, 5), (45, 20, 0), (56, 22, 2),
        ]
        for x0, y0, ci in seeds:
            if x0 < x_min:
                continue
            cy = wrap_pos(y0, 3, f, HEIGHT, direction=1)
            sway = int(round(1.5 * wave_sin(f, cycles=5, phase=ci * 1.1)))
            cx = max(x_min, min(WIDTH - 1, x0 + sway))
            if cy < 29:
                c.set(cx, cy, cols[(ci + f // 15) % len(cols)])

    def draw_red_lantern(c, cx: int, cy: int, sway: int = 0) -> None:
        """Glowing red Lunar New Year silk lantern with gold caps & tassel."""
        lx = cx + sway
        # Warm halo
        for dy in range(-1, 7):
            for dx in range(-4, 5):
                if abs(dx) + abs(dy - 2) <= 5:
                    c.set(lx + dx, cy + dy, HC["glow_red"])
        # Cord & gold cap
        c.set(cx, cy - 1, HC["gold_mid"])
        c.hline(lx - 1, cy, 3, HC["gold_bright"])
        # Plump red lantern body
        c.hline(lx - 2, cy + 1, 5, HC["red_bright"])
        c.rect(lx - 2, cy + 2, 5, 2, HC["red_bright"])
        c.vline(lx, cy + 1, 3, HC["gold_mid"])
        c.set(lx - 1, cy + 2, C["flame_hi"])
        c.vline(lx + 2, cy + 1, 3, HC["red_deep"])
        # Gold bottom cap & swaying tassel
        c.hline(lx - 1, cy + 4, 3, HC["gold_bright"])
        c.set(lx + sway, cy + 5, HC["gold_mid"])
        c.set(lx + sway, cy + 6, HC["red_bright"])

    # -----------------------------------------------------------------------
    # 1. NEW YEAR'S EVE / DAY — Midnight Fireworks & Sparkler Toast!
    # -----------------------------------------------------------------------
    def render_holiday_new_year(f: int) -> Image.Image:
        c = Canvas()
        c.gradient_v((8, 10, 28, 255), (20, 24, 58, 255), 0, 28)
        draw_twinkle_stars(c, f, [(22, 2, 0), (28, 6, 4), (37, 3, 8), (45, 7, 11), (54, 2, 3), (60, 8, 9)])

        # Distant celebratory city skyline silhouette (y=21..27)
        buildings = [(0, 23, 8), (9, 21, 7), (17, 24, 6), (25, 22, 7), (35, 20, 6), (44, 23, 8), (54, 21, 10)]
        for bx, by, bw in buildings:
            c.rect(bx, by, bw, 28 - by, (14, 18, 42, 255))
            for wy in range(by + 1, 27, 2):
                for wx in range(bx + 1, bx + bw - 1, 2):
                    if (wx + wy) % 3 != 0:
                        c.set(wx, wy, (255, 220, 116, 175))

        # Snowy rooftop terrace floor (y=28..31)
        c.rect(0, 28, WIDTH, 4, (44, 52, 82, 255))
        c.hline(0, 28, WIDTH, (132, 152, 198, 255))

        # Synchronized fireworks (seamless within 0..149)
        if 18 <= f < 56:
            draw_firework(c, 33, 6, (f - 18) / 38.0, HC["gold_bright"], HC["pink_hot"], HC["violet_bright"])
        if 52 <= f < 90:
            draw_firework(c, 53, 6, (f - 52) / 38.0, HC["cyan_bright"], HC["gold_bright"], HC["blue_hi"])
        if 86 <= f < 134:
            p = (f - 86) / 48.0
            draw_firework(c, 29, 5, p, HC["gold_bright"], HC["red_bright"], HC["pink_soft"])
            draw_firework(c, 49, 6, max(0.0, (p - 0.12) / 0.88), HC["cyan_bright"], HC["violet_bright"], HC["gold_bright"])

        bob_l = bob_offset(f, period=30, phase=0)
        bob_u = bob_offset(f, period=30, phase=15)
        celebrate = (40 <= f < 52) or (74 <= f < 86) or (104 <= f < 130)
        jump_l = -2 if (celebrate and f % 6 < 3) else 0
        jump_u = -2 if (celebrate and (f + 3) % 6 < 3) else 0

        lx, ly = 19, 8 + bob_l + jump_l
        ux, uy = 42, 9 + bob_u + jump_u
        l_mood = "delighted" if celebrate else ("blink" if (f % 50) in (10, 11) else "happy")
        u_mood = "happy" if celebrate else ("blink" if (f % 50) in (35, 36) else "chill")

        draw_lumei_hi(c, lx, ly, mood=l_mood, sprout_sway=1 if (f % 30) < 15 else 0)
        draw_lulu_hi(c, ux, uy, mood=u_mood)

        # Party hats!
        draw_party_hat(c, lx + 8, ly, HC["pink_hot"], HC["gold_bright"], C["white"])
        draw_party_hat(c, ux + 9, uy - 1, HC["blue_usa"], HC["gold_bright"], HC["cyan_bright"])

        # Handheld crackling sparklers clinking toward center during finale!
        toast = 104 <= f < 128
        sp1_x = (lx + 15) if toast else (lx + 14)
        sp1_y = (ly + 9) if toast else (ly + 11)
        sp2_x = (ux - 1) if toast else (ux)
        sp2_y = (uy + 8) if toast else (uy + 10)
        c.vline(sp1_x, sp1_y, 5, C["plate"])
        c.vline(sp2_x, sp2_y, 5, C["plate"])
        draw_sparkle(c, sp1_x, sp1_y, HC["gold_bright"], big=(f % 6 < 3))
        draw_sparkle(c, sp2_x, sp2_y, HC["cyan_bright"] if (f % 6 < 3) else HC["gold_bright"], big=(f % 6 >= 3))

        if 106 <= f < 126:
            draw_heart(c, 37, 13 - (f - 106) // 5)
        draw_confetti(c, f, 96 <= f < 136)
        return c.img

    # -----------------------------------------------------------------------
    # 2. LUNAR NEW YEAR — Glowing Red Lanterns & Lucky Hongbao!
    # -----------------------------------------------------------------------
    def render_holiday_lunar_new_year(f: int) -> Image.Image:
        c = Canvas()
        # Rich midnight lacquer burgundy-charcoal sky so golden characters & glowing red lanterns pop!
        c.gradient_v((22, 6, 16, 255), (46, 12, 26, 255), 0, 28)

        # Festive crimson & gold pavilion eave trim across top-right (x=21..63)
        c.hline(21, 0, 43, HC["red_dark"])
        c.hline(21, 1, 43, HC["gold_mid"])
        for tx in range(22, 63, 4):
            c.set(tx, 0, HC["gold_bright"])

        # Dark slate courtyard stone terrace (contrasts orange shorts & red hongbao)
        c.rect(0, 28, WIDTH, 4, (28, 26, 40, 255))
        c.hline(0, 28, WIDTH, HC["gold_deep"])
        for sx in range(4, WIDTH, 10):
            c.vline(sx, 29, 3, (18, 16, 28, 255))

        # 3 swaying glowing red silk lanterns (clear of HUD!)
        sway_a = 1 if (f % 30) < 15 else 0
        sway_b = 1 - sway_a
        draw_red_lantern(c, 26, 3, sway_a)
        draw_red_lantern(c, 42, 2, sway_b)
        draw_red_lantern(c, 57, 3, sway_a)

        # Celebratory red & gold sky bursts during finale
        if 96 <= f < 136:
            draw_firework(c, 35, 9, (f - 96) / 40.0, HC["gold_bright"], HC["red_bright"], HC["gold_mid"])
            draw_firework(c, 51, 9, max(0.0, (f - 104) / 32.0), HC["gold_bright"], C["flame_hi"], HC["red_bright"])

        bob_l = bob_offset(f, period=30, phase=0)
        bob_u = bob_offset(f, period=30, phase=15)
        lx, ly = 19, 8 + bob_l
        ux, uy = 43, 9 + bob_u
        l_mood = "blink" if (f % 50) in (12, 13) else "happy"
        u_mood = "blink" if (f % 50) in (36, 37) else "chill"
        u_walk = 0
        show_hongbao = False
        hb_x, hb_y = 39, 20

        # Story: Lulu walks over with lucky red envelope -> hands to Lumei -> gold coins burst!
        if 28 <= f < 56:
            t = ease_in_out((f - 28) / 28.0)
            ux = lerp_i(43, 37, t)
            u_walk = 1 if (f % 6 < 3) else 2
            u_mood = "happy"
            show_hongbao = True
            hb_x, hb_y = ux - 3, 20 + bob_u
        elif 56 <= f < 96:
            ux = 37
            u_mood = "happy"
            l_mood = "delighted"
            show_hongbao = True
            t = min(1.0, (f - 56) / 14.0)
            hb_x = lerp_i(34, 31, t)
            hb_y = 19 - (1 if (f >= 70 and f % 6 < 3) else 0)
            if f >= 70:
                ly = 8 - (2 if (f % 8 < 4) else 0)
        elif 96 <= f < 132:
            ux = 37 if f < 118 else lerp_i(37, 43, ease_in_out((f - 118) / 14.0))
            u_walk = (1 if (f % 6 < 3) else 2) if f >= 118 else 0
            l_mood, u_mood = "delighted", "happy"
            ly = 8 - (2 if (f % 6 < 3) else 0)
            uy = 9 - (1 if ((f + 3) % 6 < 3) else 0)
            show_hongbao = f < 120
            hb_x, hb_y = 31, 18
        elif 132 <= f < 150:
            ux = 43

        draw_lumei_hi(c, lx, ly, mood=l_mood, sprout_sway=sway_a)
        draw_lulu_hi(c, ux, uy, mood=u_mood, walk_step=u_walk)

        # Lucky Red Envelope (Hongbao) with gold seal!
        if show_hongbao:
            c.rect(hb_x, hb_y, 5, 6, HC["red_bright"])
            c.vline(hb_x + 4, hb_y, 6, HC["red_deep"])
            c.hline(hb_x, hb_y + 1, 5, HC["gold_mid"])
            c.rect(hb_x + 2, hb_y + 2, 2, 2, HC["gold_bright"])
            c.set(hb_x + 2, hb_y + 2, C["white"])

        # Lucky gold coins & sparkles bursting from the hongbao!
        if 70 <= f < 116:
            dt = (f - 70) / 46.0
            for ci, (dx0, arc_h) in enumerate([(-4, 7), (0, 9), (4, 8), (8, 6)]):
                cx_c = int(round(33 + dx0 * (1.0 + dt)))
                cy_c = int(round(18 - arc_h * math.sin(min(1.0, dt * 1.4) * math.pi)))
                if not (cx_c < 20 and cy_c < 12):
                    c.rect(cx_c, cy_c, 2, 2, HC["gold_bright"])
                    c.set(cx_c, cy_c, C["white"] if (f + ci) % 4 < 2 else HC["gold_mid"])
        if 102 <= f < 126:
            draw_heart(c, 35, 11 - (f - 102) // 6)

        # Gentle drifting gold luck motes
        for x0, y0, ph in [(23, 14, 0), (32, 16, 2), (48, 13, 4), (59, 17, 1)]:
            gy = wrap_pos(y0, 2, f, HEIGHT, direction=1)
            if gy < 28:
                c.set(x0, gy, HC["gold_bright"] if ((f + ph) % 10 < 5) else HC["gold_mid"])
        return c.img

    # -----------------------------------------------------------------------
    # 3. VALENTINE'S DAY — Heart Chocolate Box, Rose & Floating Hearts!
    # -----------------------------------------------------------------------
    def render_holiday_valentines(f: int) -> Image.Image:
        c = Canvas()
        # Deep velvety midnight plum-indigo so Lumei's pink romper, gold faces & red hearts glow!
        c.gradient_v((20, 12, 42, 255), (52, 20, 64, 255), 0, 28)

        # Soft rosy sparkles in upper-right sky
        draw_twinkle_stars(c, f, [(24, 3, 0), (32, 6, 5), (44, 2, 9), (55, 5, 3), (60, 10, 12)])

        # Deep twilight meadow
        c.rect(0, 28, WIDTH, 4, (24, 54, 42, 255))
        c.hline(0, 28, WIDTH, (44, 92, 66, 255))
        for fx, fc in [(6, HC["pink_soft"]), (14, HC["red_bright"]), (28, HC["pink_hot"]), (52, HC["pink_soft"]), (60, HC["red_bright"])]:
            c.set(fx, 29, fc)

        bob_l = bob_offset(f, period=30, phase=0)
        bob_u = bob_offset(f, period=30, phase=15)
        lx, ly = 19, 8 + bob_l
        ux, uy = 43, 9 + bob_u
        l_mood = "blink" if (f % 50) in (10, 11) else "happy"
        u_mood = "blink" if (f % 50) in (36, 37) else "chill"
        l_walk, u_walk = 0, 0
        show_gift_heart = False

        if 26 <= f < 58:
            t = ease_in_out((f - 26) / 32.0)
            ux = lerp_i(43, 38, t)
            u_walk = 1 if (f % 6 < 3) else 2
            u_mood = "happy"
            show_gift_heart = f >= 40
        elif 58 <= f < 126:
            t_in = min(1.0, (f - 58) / 14.0)
            lx = lerp_i(19, 23, ease_in_out(t_in))
            ux = 38
            l_mood = "delighted"
            u_mood = "happy"
            show_gift_heart = True
            if 74 <= f < 118:
                ly = 8 - (1 if (f % 10 < 5) else 0)
                uy = 9 - (1 if ((f + 5) % 10 < 5) else 0)
        elif 126 <= f < 150:
            t = ease_in_out((f - 126) / 24.0)
            lx = lerp_i(23, 19, t)
            ux = lerp_i(38, 43, t)
            l_walk = 1 if (f % 6 < 3) else 2
            u_walk = 2 if (f % 6 < 3) else 1

        draw_lumei_hi(c, lx, ly, mood=l_mood, walk_step=l_walk, sprout_sway=1 if (f % 30) < 15 else 0)
        draw_lulu_hi(c, ux, uy, mood=u_mood, walk_step=u_walk)

        # Giant red heart gift box + rose held between them!
        if show_gift_heart:
            hx, hy = ux - 3, 18 + (0 if f >= 74 else 1)
            # 7x6 big pixel heart box
            c.hline(hx + 1, hy, 2, HC["red_bright"])
            c.hline(hx + 4, hy, 2, HC["red_bright"])
            c.rect(hx, hy + 1, 7, 2, HC["red_bright"])
            c.set(hx + 1, hy + 1, HC["pink_soft"])
            c.hline(hx + 1, hy + 3, 5, HC["red_bright"])
            c.hline(hx + 2, hy + 4, 3, HC["red_deep"])
            c.set(hx + 3, hy + 5, HC["red_deep"])
            # Gold ribbon bow on heart
            c.set(hx + 3, hy + 2, HC["gold_bright"])

        # Rising fountain of floating hearts!
        if 64 <= f < 134:
            for idx, (hx0, delay, speed) in enumerate([(34, 0, 4), (27, 10, 5), (44, 16, 4), (39, 26, 5), (31, 36, 4)]):
                age = f - 64 - delay
                if 0 <= age < 32:
                    hy = 16 - (age * speed) // 10
                    if hy >= 2 and not (hx0 < 20 and hy < 12):
                        draw_heart(c, hx0, hy)

        # Gentle drifting pink rose petals (exact 150-frame wrap)
        for x0, y0, ph in [(24, 5, 0), (37, 11, 2), (51, 3, 4), (60, 15, 1), (29, 20, 3)]:
            py = wrap_pos(y0, 2, f, HEIGHT, direction=1)
            px = (x0 + int(round(2 * wave_sin(f, cycles=3, phase=ph)))) % WIDTH
            if py < 28 and not (px < 20 and py < 12):
                c.set(px, py, HC["pink_soft"] if ph % 2 == 0 else HC["pink_hot"])
        return c.img

    # -----------------------------------------------------------------------
    # 4. LULU'S BIRTHDAY (Feb 20) — Crown, Glowing Cake & Confetti Blowout!
    # -----------------------------------------------------------------------
    def render_birthday_lulu(f: int) -> Image.Image:
        c = Canvas()
        # Rich deep midnight blue party room so golden crown, cake candles & avatars pop!
        c.gradient_v((14, 20, 52, 255), (28, 38, 84, 255), 0, 28)

        # Festive party bunting across very top-right (y=0..2, clear of HUD & crowns!)
        draw_bunting(c, 21, 63, 0, f, [HC["gold_bright"], C["orange_main"], HC["cyan_bright"], HC["pink_hot"], HC["emerald_hi"]])

        # Dark walnut party floor (crisp contrast against golden feet & orange shorts)
        c.rect(0, 28, WIDTH, 4, (58, 34, 24, 255))
        c.hline(0, 28, WIDTH, (94, 58, 38, 255))
        c.hline(0, 31, WIDTH, (36, 20, 14, 255))

        # Balanced floating birthday balloons (left below HUD + right edge!)
        b_bob = bob_offset(f, period=30, phase=0)
        b_sway = 1 if (f % 30) < 15 else 0
        draw_balloon(c, 4, 14 + b_bob, HC["cyan_bright"], HC["blue_usa"], (24, 68, 168, 255), b_sway)
        draw_balloon(c, 11, 16 - b_bob, HC["gold_bright"], HC["gold_mid"], HC["gold_deep"], 1 - b_sway)
        draw_balloon(c, 58, 11 + b_bob, C["orange_hi"], C["orange_main"], C["orange_dark"], b_sway)

        bob_l = bob_offset(f, period=30, phase=0)
        bob_u = bob_offset(f, period=30, phase=15)
        lx, ly = 19, 8 + bob_l
        ux, uy = 40, 10 + bob_u
        l_mood = "happy"
        u_mood = "chill"
        l_walk = 0
        cake_x, cake_y = 31, 21
        candles_lit = True
        smoke_step = 0
        confetti_on = False

        # Story:
        # 0..24:   Lumei starts on left carrying glowing cake; birthday king Lulu waits
        # 25..59:  Lumei marches closer presenting the glowing cake! Lulu lights up!
        # 60..84:  Lulu puffs cheeks & blows out all 3 candles (white breath + rising smoke!)
        # 85..129: CONFETTI EXPLOSION + birthday hops + hearts!
        # 130..149: Smooth reset to f=0
        if 0 <= f < 25:
            lx = 19
            cake_x = 30
        elif 25 <= f < 60:
            t = ease_in_out((f - 25) / 35.0)
            lx = lerp_i(19, 23, t)
            cake_x = lx + 11
            l_walk = 1 if (f % 6 < 3) else 2
            l_mood = "delighted"
            u_mood = "startled" if f < 42 else "happy"
        elif 60 <= f < 85:
            lx = 23
            cake_x = 34
            l_mood = "delighted"
            if f < 72:
                u_mood = "chomp"  # puffing cheeks to blow!
                candles_lit = True
            else:
                u_mood = "happy"
                candles_lit = False
                smoke_step = f - 72
        elif 85 <= f < 130:
            lx = 23
            cake_x = 34
            candles_lit = False
            confetti_on = True
            l_mood, u_mood = "delighted", "happy"
            ly = 8 - (2 if (f % 8 < 4) else 0)
            uy = 10 - (2 if ((f + 4) % 8 < 4) else 0)
        elif 130 <= f < 150:
            t = ease_in_out((f - 130) / 20.0)
            lx = lerp_i(23, 19, t)
            cake_x = lerp_i(34, 30, t)
            l_walk = 1 if (f % 6 < 3) else 2
            candles_lit = True
        else:
            lx = 19
            cake_x = 30

        # Wrapped birthday gifts on left & right!
        draw_gift_box(c, 5, 24, C["orange_main"], C["orange_dark"], HC["gold_bright"])
        draw_gift_box(c, 55, 24, HC["blue_usa"], (24, 62, 152, 255), HC["gold_bright"])

        draw_lumei_hi(c, lx, ly, mood=l_mood, walk_step=l_walk, sprout_sway=b_sway)
        draw_lulu_hi(c, ux, uy, mood=u_mood, has_tangerine=False)
        # Golden Birthday Crown perched cleanly on birthday-king Lulu's head!
        draw_birthday_crown(c, ux + 9, uy)

        # Birthday cake with flickering candles or blown-out smoke
        draw_birthday_cake(c, cake_x, cake_y, f, pink=False, lit=candles_lit, smoke_step=smoke_step)

        # Visible breath puff when Lulu blows out the candles (f=66..73)
        if 66 <= f <= 73:
            p_x = lerp_i(ux + 4, cake_x + 5, (f - 66) / 7.0)
            c.hline(p_x, 19, 3, C["white"])
            c.set(p_x - 1, 18, HC["smoke"])
            c.set(p_x - 1, 20, HC["smoke"])

        if 88 <= f < 124:
            draw_heart(c, 37, 11 - (f - 88) // 6)
        draw_confetti(c, f, confetti_on)
        return c.img

    # -----------------------------------------------------------------------
    # 5. ST. PATRICK'S DAY (Mar 17) — Rainbow, Leprechaun Hat & Pot of Gold!
    # -----------------------------------------------------------------------
    def render_holiday_st_patricks(f: int) -> Image.Image:
        c = Canvas()
        # Crisp saturated Irish blue sky so the rainbow, gold coins & pale bonnet pop!
        c.gradient_v((22, 66, 132, 255), (42, 108, 174, 255), 0, 27)

        # Vivid 6-band rainbow arcing from upper-mid (x=22) down into Pot of Gold (x=55)
        rb_cols = [HC["red_bright"], C["orange_main"], HC["gold_bright"], HC["emerald_hi"], HC["cyan_bright"], HC["violet_bright"]]
        shimmer = (f // 15) % 2
        for band_i, col in enumerate(rb_cols):
            r = 22 - band_i
            for deg in range(18, 128, 2):
                rad = math.radians(deg)
                rx = int(round(39 + r * math.cos(rad)))
                ry = int(round(26 - r * math.sin(rad)))
                if rx >= 21 and 0 <= ry < 27:
                    c.set(rx, ry, C["white"] if (shimmer == 1 and deg % 22 == 0 and band_i == 2) else col)

        # Deep lush emerald clover meadow
        c.rect(0, 27, WIDTH, 5, (20, 96, 44, 255))
        c.hline(0, 27, WIDTH, (42, 146, 68, 255))
        c.hline(0, 30, WIDTH, (12, 66, 30, 255))
        c.hline(0, 31, WIDTH, (12, 66, 30, 255))
        # Pixel four-leaf clovers
        for cx0, cy0 in [(6, 28), (15, 29), (29, 28), (46, 29)]:
            c.set(cx0, cy0 - 1, HC["emerald_hi"])
            c.set(cx0 - 1, cy0, HC["emerald_hi"])
            c.set(cx0 + 1, cy0, HC["emerald_hi"])
            c.set(cx0, cy0, HC["emerald_dark"])

        # Gleaming Black Iron Pot of Gold at right (x=53..61, y=22..28)
        px, py = 53, 22
        c.hline(px + 1, py + 1, 7, HC["gold_bright"])
        c.hline(px + 2, py, 5, HC["gold_mid"])
        c.set(px + 3, py - 1, HC["gold_bright"])
        c.set(px + 5, py, C["white"] if (f % 10 < 5) else HC["gold_bright"])
        c.hline(px, py + 2, 9, HC["iron_hi"])
        c.rect(px + 1, py + 3, 7, 3, HC["iron_dark"])
        c.vline(px + 2, py + 3, 2, HC["iron_mid"])
        c.hline(px + 2, py + 6, 5, HC["iron_dark"])

        bob_l = bob_offset(f, period=30, phase=0)
        bob_u = bob_offset(f, period=30, phase=15)
        lx, ly = 19, 8 + bob_l
        ux, uy = 35, 9 + bob_u
        l_mood = "blink" if (f % 50) in (10, 11) else "happy"
        u_mood = "blink" if (f % 50) in (34, 35) else "chill"
        u_walk = 0

        if 28 <= f < 58:
            t = ease_in_out((f - 28) / 30.0)
            ux = lerp_i(35, 39, t)
            u_walk = 1 if (f % 6 < 3) else 2
            u_mood = "happy"
        elif 58 <= f < 104:
            ux = 39
            u_mood = "happy"
            l_mood = "delighted"
            if f >= 74:
                ly = 8 - (2 if (f % 8 < 4) else 0)
        elif 104 <= f < 134:
            ux = 39
            l_mood, u_mood = "delighted", "happy"
            # Happy Irish jig hop!
            ly = 8 - (2 if (f % 6 < 3) else 0)
            uy = 9 - (2 if ((f + 3) % 6 < 3) else 0)
        elif 134 <= f < 150:
            t = ease_in_out((f - 134) / 16.0)
            ux = lerp_i(39, 35, t)
            u_walk = 1 if (f % 6 < 3) else 2

        draw_lumei_hi(c, lx, ly, mood=l_mood, sprout_sway=1 if (f % 30) < 15 else 0)
        draw_lulu_hi(c, ux, uy, mood=u_mood, has_tangerine=False, walk_step=u_walk)
        # Jaunty emerald leprechaun hat on Lulu!
        draw_leprechaun_hat(c, ux + 9, uy)

        # Arc of sparkling gold coins tossed from Pot of Gold to Lumei!
        if 60 <= f < 104:
            for ci, delay in enumerate([0, 8, 16, 24]):
                age = f - 60 - delay
                if 0 <= age <= 20:
                    ct = age / 20.0
                    cx_c = lerp_i(54, 28, ct)
                    cy_c = int(round(20 - 11 * math.sin(math.pi * ct)))
                    if not (cx_c < 20 and cy_c < 12):
                        c.rect(cx_c, cy_c, 2, 2, HC["gold_bright"])
                        c.set(cx_c, cy_c, C["white"] if (age % 4 < 2) else HC["gold_mid"])

        if 108 <= f < 130:
            draw_heart(c, 36, 10 - (f - 108) // 6)
        if f % 15 < 8:
            draw_sparkle(c, 57, 19, HC["gold_bright"], big=True)
        return c.img

    # -----------------------------------------------------------------------
    # 6. EASTER SUNDAY — Painted Egg Hunt & Hatching Golden Chick!
    # -----------------------------------------------------------------------
    def render_holiday_easter(f: int) -> Image.Image:
        c = Canvas()
        # Crisp saturated spring cerulean sky so white bunny ears, yellow chick & pale bonnet pop!
        c.gradient_v((28, 84, 166, 255), (56, 128, 204, 255), 0, 27)

        # Fluffy pastel spring clouds (clear of HUD!)
        for cx0, cy0 in [(28, 3), (50, 5)]:
            cx = 22 + (cx0 - 22 + (f * 42) // NUM_FRAMES) % 42
            c.hline(cx + 1, cy0, 5, C["white"])
            c.hline(cx, cy0 + 1, 7, C["cloud_white"])

        # Rich medium-deep spring meadow (lets pastel eggs & golden avatars pop!)
        c.rect(0, 27, WIDTH, 5, (32, 114, 52, 255))
        c.hline(0, 27, WIDTH, (58, 156, 74, 255))
        c.hline(0, 30, WIDTH, (20, 82, 36, 255))
        for fx, fc in [(6, HC["pink_soft"]), (13, HC["egg_gold"]), (26, HC["egg_lav"]), (59, HC["pink_hot"])]:
            c.set(fx, 28, fc)

        # Small painted polka-dot Easter eggs nestled in the grass
        def draw_mini_egg(ex: int, ey: int, col, dot) -> None:
            c.hline(ex + 1, ey, 2, col)
            c.rect(ex, ey + 1, 4, 3, col)
            c.set(ex + 1, ey + 2, dot)
            c.set(ex + 2, ey + 1, C["white"])

        draw_mini_egg(13, 25, HC["egg_mint"], HC["pink_hot"])
        draw_mini_egg(58, 25, HC["egg_lav"], HC["egg_gold"])

        # Cute woven Easter basket filled with pastel eggs on the left grass (below HUD!)
        c.hline(5, 22, 5, HC["wood_hi"])
        c.vline(4, 23, 2, HC["wood_hi"])
        c.vline(10, 23, 2, HC["wood_hi"])
        c.set(5, 23, HC["egg_pink"]); c.set(6, 23, HC["egg_pink"])
        c.set(7, 23, HC["egg_gold"]); c.set(8, 23, HC["egg_mint"]); c.set(9, 23, HC["egg_lav"])
        c.rect(4, 24, 7, 3, C["basket_main"])
        c.hline(4, 26, 7, C["basket_dark"])
        for bx in (5, 7, 9):
            c.set(bx, 25, C["basket_dark"])

        bob_l = bob_offset(f, period=30, phase=0)
        bob_u = bob_offset(f, period=30, phase=15)
        lx, ly = 19, 8 + bob_l
        ux, uy = 42, 9 + bob_u
        l_mood = "blink" if (f % 50) in (10, 11) else "happy"
        u_mood = "blink" if (f % 50) in (36, 37) else "chill"
        ear_twitch = 1 if (f % 30) in (12, 13, 14) else 0

        # Giant painted golden Easter egg center stage (x=34, y=22)!
        egg_wobble = 0
        egg_hatched = False
        chick_pos = None

        if 26 <= f < 58:
            egg_wobble = -1 if (f % 6 < 3) else 1
            l_mood = "startled" if f >= 44 else "happy"
            u_mood = "startled" if f >= 44 else "happy"
        elif 58 <= f < 130:
            egg_hatched = True
            l_mood = "delighted"
            u_mood = "happy"
            if f < 76:
                # Chick hops out of eggshell toward Lulu's head!
                t = ease_in_out((f - 58) / 18.0)
                cx_k = lerp_i(35, ux + 9, t)
                cy_k = int(round(20 - 15 * math.sin(t * math.pi * 0.65)))
                chick_pos = (cx_k, cy_k)
            elif f < 118:
                # Chick perches happily right beside Lulu's tangerine!
                hop = -1 if (f % 10 < 5) else 0
                chick_pos = (ux + 9, uy - 6 + hop)
                ly = 8 - (2 if (f % 8 < 4) else 0)
                uy = 9 - (1 if ((f + 4) % 8 < 4) else 0)
            else:
                t = ease_in_out((f - 118) / 12.0)
                cx_k = lerp_i(ux + 9, 35, t)
                cy_k = int(round(lerp_i(uy - 6, 22, t) - 5 * math.sin(math.pi * t)))
                chick_pos = (cx_k, cy_k)

        draw_lumei_hi(c, lx, ly, mood=l_mood, sprout_sway=1 if (f % 30) < 15 else 0)
        draw_lulu_hi(c, ux, uy, mood=u_mood)
        # Cute white Easter bunny ears on Lulu!
        draw_bunny_ears(c, ux + 9, uy, twitch=ear_twitch)

        # Center Giant Golden Egg (whole wobbling vs cracked bottom shell)
        ex, ey = 34 + egg_wobble, 22
        if not egg_hatched:
            c.hline(ex + 1, ey, 3, HC["egg_gold"])
            c.rect(ex, ey + 1, 5, 5, HC["egg_gold"])
            c.hline(ex + 1, ey + 6, 3, C["orange_main"])
            c.hline(ex, ey + 3, 5, HC["pink_hot"])
            c.set(ex + 1, ey + 1, C["white"])
            c.set(ex + 3, ey + 2, HC["egg_mint"])
            c.set(ex + 1, ey + 5, HC["egg_lav"])
            if 44 <= f < 58:
                # Crack zigzag!
                c.set(ex + 1, ey + 2, C["eye"])
                c.set(ex + 2, ey + 3, C["eye"])
                c.set(ex + 3, ey + 2, C["eye"])
                draw_exclaim(c, ex + 2, ey - 5)
        else:
            # Cracked bottom shell halves
            c.rect(ex, ey + 3, 5, 3, HC["egg_gold"])
            c.set(ex, ey + 2, HC["egg_gold"])
            c.set(ex + 2, ey + 2, HC["egg_gold"])
            c.set(ex + 4, ey + 2, HC["egg_gold"])
            c.hline(ex, ey + 4, 5, HC["pink_hot"])

        # Fluffy yellow baby chick!
        if chick_pos is not None:
            kx, ky = chick_pos
            c.rect(kx - 1, ky, 4, 3, HC["chick_main"])
            c.hline(kx, ky - 1, 2, HC["chick_hi"])
            c.set(kx, ky, C["eye"])
            c.set(kx - 2, ky + 1, C["orange_main"])  # tiny beak!
            if f % 6 < 3:
                c.set(kx + 2, ky, HC["chick_hi"])  # fluttering wing!

        if 80 <= f < 114:
            draw_heart(c, 36, 10 - (f - 80) // 6)
        return c.img

    # -----------------------------------------------------------------------
    # 7. INDEPENDENCE DAY (Jul 4) — Red, White & Blue Fireworks Spectacular!
    # -----------------------------------------------------------------------
    def render_holiday_independence(f: int) -> Image.Image:
        c = Canvas()
        c.gradient_v((8, 14, 44, 255), (20, 36, 82, 255), 0, 27)
        draw_twinkle_stars(c, f, [(23, 3, 0), (31, 7, 4), (43, 2, 8), (52, 6, 12), (61, 4, 6)])

        # Summer hill + patriotic blanket
        c.rect(0, 27, WIDTH, 5, (34, 96, 52, 255))
        c.hline(0, 27, WIDTH, (64, 146, 78, 255))
        for dx in range(42):
            bx = 19 + dx
            col = HC["red_bright"] if (dx % 6 < 2) else (C["white"] if (dx % 6 < 4) else HC["blue_usa"])
            c.hline(bx, 29, 1, col)
            c.hline(bx, 30, 1, col)

        # Synchronized Red, White & Blue Fireworks!
        if 16 <= f < 54:
            draw_firework(c, 29, 6, (f - 16) / 38.0, HC["red_bright"], C["white"], HC["pink_soft"])
        if 48 <= f < 86:
            draw_firework(c, 53, 6, (f - 48) / 38.0, HC["blue_hi"], C["white"], HC["cyan_bright"])
        if 82 <= f < 136:
            p = (f - 82) / 54.0
            draw_firework(c, 27, 6, p, HC["red_bright"], C["white"], HC["red_deep"])
            draw_firework(c, 41, 5, max(0.0, (p - 0.12) / 0.88), C["white"], HC["gold_bright"], HC["cyan_bright"])
            draw_firework(c, 55, 6, max(0.0, (p - 0.24) / 0.76), HC["blue_usa"], C["white"], HC["blue_hi"])

        bob_l = bob_offset(f, period=30, phase=0)
        bob_u = bob_offset(f, period=30, phase=15)
        cheer = (32 <= f < 48) or (64 <= f < 80) or (96 <= f < 130)
        lx, ly = 19, 8 + bob_l - (2 if (cheer and f % 6 < 3) else 0)
        ux, uy = 43, 9 + bob_u - (2 if (cheer and (f + 3) % 6 < 3) else 0)

        draw_lumei_hi(c, lx, ly, mood="delighted" if cheer else "happy", sprout_sway=1 if (f % 30) < 15 else 0)
        draw_lulu_hi(c, ux, uy, mood="happy" if cheer else "chill")

        # Waving mini US flag planted proudly in center grass!
        fx, fy = 36, 18
        c.vline(fx, fy, 11, C["plate"])
        wob = 1 if (f % 10 < 5) else 0
        # Blue canton
        c.rect(fx + 1, fy, 3, 2, HC["blue_usa"])
        c.set(fx + 2, fy, C["white"])
        # Red & white waving stripes
        c.hline(fx + 4, fy + wob, 3, HC["red_bright"])
        c.hline(fx + 4, fy + 1 + wob, 3, C["white"])
        c.hline(fx + 1, fy + 2, 3, HC["red_bright"])
        c.hline(fx + 4, fy + 2 + wob, 3, HC["red_bright"])
        c.hline(fx + 1, fy + 3, 3, C["white"])
        c.hline(fx + 4, fy + 3 + wob, 3, C["white"])

        # Sparklers during grand finale
        if cheer:
            draw_sparkle(c, lx + 14, ly + 10, HC["gold_bright"], big=(f % 4 < 2))
            draw_sparkle(c, ux, uy + 9, HC["cyan_bright"], big=(f % 4 >= 2))
        return c.img

    # -----------------------------------------------------------------------
    # 8. LUMEI'S BIRTHDAY (Oct 20) — Princess Crown, Strawberry Cake & Gift!
    # -----------------------------------------------------------------------
    def render_birthday_lumei(f: int) -> Image.Image:
        c = Canvas()
        # Deep royal starry violet-navy so Lumei's pink romper, golden crown & strawberry cake pop!
        c.gradient_v((18, 12, 44, 255), (40, 22, 74, 255), 0, 28)

        # Pastel princess bunting across very top-right (y=0..2, clear of HUD & crown!)
        draw_bunting(c, 21, 63, 0, f, [HC["pink_hot"], HC["gold_bright"], HC["egg_mint"], HC["pink_soft"], HC["egg_lav"]])

        # Deep plum party floor with soft lavender trim (contrasts baby-pink romper & gifts)
        c.rect(0, 28, WIDTH, 4, (44, 24, 64, 255))
        c.hline(0, 28, WIDTH, (94, 62, 128, 255))
        c.hline(0, 31, WIDTH, (28, 14, 42, 255))

        # Balanced pastel balloons (left below HUD + right edge!)
        b_bob = bob_offset(f, period=30, phase=0)
        b_sway = 1 if (f % 30) < 15 else 0
        draw_balloon(c, 4, 14 + b_bob, HC["pink_soft"], HC["pink_hot"], HC["pink_deep"], b_sway)
        draw_balloon(c, 11, 16 - b_bob, C["white"], HC["egg_mint"], HC["emerald_main"], 1 - b_sway)
        draw_balloon(c, 58, 11 + b_bob, HC["gold_bright"], HC["egg_lav"], HC["violet_dark"], b_sway)

        bob_l = bob_offset(f, period=30, phase=0)
        bob_u = bob_offset(f, period=30, phase=15)
        lx, ly = 19, 9 + bob_l
        ux, uy = 42, 9 + bob_u
        l_mood = "happy"
        u_mood = "happy"
        u_walk = 0
        cake_x, cake_y = 33, 21
        candles_lit = True
        smoke_step = 0
        lid_lift = 0
        confetti_on = False

        # Story:
        # 0..24:   Princess Lumei beams; Lulu prepares giant strawberry birthday cake
        # 25..59:  Lulu waddles over carrying the glowing strawberry cake!
        # 60..84:  Lumei makes a wish & blows out all 3 candles!
        # 85..129: Pink gift pops open in confetti & hearts! Both celebrate!
        # 130..149: Smooth seamless reset to f=0
        if 0 <= f < 25:
            ux = 42
            cake_x = 33
        elif 25 <= f < 60:
            t = ease_in_out((f - 25) / 35.0)
            ux = lerp_i(42, 39, t)
            cake_x = ux - 9
            u_walk = 1 if (f % 6 < 3) else 2
            l_mood = "startled" if f < 42 else "delighted"
        elif 60 <= f < 85:
            ux = 39
            cake_x = 30
            if f < 72:
                l_mood = "chomp"  # blowing out the candles!
                candles_lit = True
            else:
                l_mood = "delighted"
                candles_lit = False
                smoke_step = f - 72
        elif 85 <= f < 130:
            ux = 39
            cake_x = 30
            candles_lit = False
            confetti_on = True
            lid_lift = min(4, (f - 85) // 3) if f < 120 else max(0, 4 - (f - 120) // 2)
            l_mood, u_mood = "delighted", "happy"
            ly = 9 - (2 if (f % 8 < 4) else 0)
            uy = 9 - (2 if ((f + 4) % 8 < 4) else 0)
        elif 130 <= f < 150:
            t = ease_in_out((f - 130) / 20.0)
            ux = lerp_i(39, 42, t)
            cake_x = lerp_i(30, 33, t)
            u_walk = 1 if (f % 6 < 3) else 2
            candles_lit = True
        else:
            ux = 42
            cake_x = 33

        # Wrapped pink birthday presents on left & right!
        draw_gift_box(c, 5, 24, HC["egg_lav"], HC["violet_dark"], HC["pink_soft"])
        draw_gift_box(c, 55, 24, HC["pink_hot"], HC["pink_deep"], HC["gold_bright"], lid_lift=lid_lift)

        draw_lumei_hi(c, lx, ly, mood=l_mood, sprout_sway=b_sway)
        # Golden Princess Birthday Crown perched cleanly on Lumei's bonnet (well below bunting!)
        draw_birthday_crown(c, lx + 8, ly + 1)
        draw_lulu_hi(c, ux, uy, mood=u_mood, walk_step=u_walk)

        # Giant strawberry birthday cake!
        draw_birthday_cake(c, cake_x, cake_y, f, pink=True, lit=candles_lit, smoke_step=smoke_step)

        # Breath puff from Lumei toward candles (f=66..73)
        if 66 <= f <= 73:
            p_x = lerp_i(lx + 12, cake_x + 4, (f - 66) / 7.0)
            c.hline(p_x, 19, 3, C["white"])
            c.set(p_x + 3, 18, HC["smoke"])
            c.set(p_x + 3, 20, HC["smoke"])

        if 88 <= f < 124:
            draw_heart(c, 34, 11 - (f - 88) // 6)
            if f >= 94:
                draw_sparkle(c, 58, 18 - (f - 94) // 6, HC["gold_bright"], big=True)
        draw_confetti(c, f, confetti_on)
        return c.img

    # -----------------------------------------------------------------------
    # 9. HALLOWEEN (Oct 31) — Witch Lumei, Ghost Lulu & Candy Pumpkin!
    # -----------------------------------------------------------------------
    def render_holiday_halloween(f: int) -> Image.Image:
        c = Canvas()
        c.gradient_v((14, 6, 30, 255), (34, 14, 58, 255), 0, 27)

        # Glowing harvest full moon tucked cleanly in upper-right corner (x=54..61, y=1..8)
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                d2 = dx * dx + dy * dy
                if d2 <= 10:
                    c.set(57 + dx, 4 + dy, C["moon"])
                elif d2 <= 17:
                    c.set(57 + dx, 4 + dy, HC["glow_moon"])
        c.set(56, 3, HC["gold_mid"])
        c.set(58, 5, HC["gold_mid"])

        # Spooky wooden fence & silhouette pumpkin patch on left (below HUD!)
        c.hline(1, 22, 16, (30, 18, 44, 255))
        c.hline(1, 25, 16, (30, 18, 44, 255))
        for fx in (3, 9, 15):
            c.vline(fx, 19, 9, (30, 18, 44, 255))
        c.rect(5, 24, 4, 3, HC["pumpkin_main"])
        c.set(6, 23, C["stem_green"])

        # Two swooping pixel bats across upper-right sky (clear of HUD!)
        for bi, (bx0, by0, ph) in enumerate([(26, 4, 0), (44, 9, 2)]):
            bx = 22 + (bx0 - 22 + (f * 42) // NUM_FRAMES) % 42
            by = by0 + int(round(1.5 * wave_sin(f, cycles=5, phase=ph)))
            flap = 1 if ((f + bi * 3) % 6 < 3) else -1
            c.set(bx, by, HC["bat_dark"])
            c.set(bx - 1, by, HC["bat_wing"])
            c.set(bx + 1, by, HC["bat_wing"])
            c.set(bx - 2, by + flap, HC["bat_wing"])
            c.set(bx + 2, by + flap, HC["bat_wing"])

        # Spooky autumn grass patch
        c.rect(0, 27, WIDTH, 5, (42, 26, 56, 255))
        c.hline(0, 27, WIDTH, (74, 46, 94, 255))

        bob_l = bob_offset(f, period=30, phase=0)
        bob_u = bob_offset(f, period=30, phase=15)
        lx, ly = 19, 8 + bob_l
        ux, uy = 43, 9 + bob_u
        l_mood = "happy"
        u_mood = "chill"
        ghost_y = None
        candy_on = False

        # Story:
        # 0..29:   Witch Lumei & Ghost-sheet Lulu by the glowing jack-o'-lantern
        # 30..64:  BOO! Friendly tiny ghost pops out of pumpkin -> Ghost Lulu leaps startled!
        # 65..104: Friendly ghost showers colorful wrapped candies!
        # 105..134: Both happily munch candy with floating hearts!
        # 135..149: Ghost sinks smoothly back into pumpkin
        if 30 <= f < 65:
            t = min(1.0, (f - 30) / 14.0)
            ghost_y = lerp_i(21, 12, ease_in_out(t)) + bob_offset(f, period=10, phase=0)
            l_mood = "delighted"
            u_mood = "startled"
            if 34 <= f < 50:
                uy = 9 - int(round(4 * math.sin(((f - 34) / 16.0) * math.pi)))
        elif 65 <= f < 105:
            ghost_y = 12 + bob_offset(f, period=10, phase=0)
            candy_on = True
            l_mood = "delighted"
            u_mood = "happy"
        elif 105 <= f < 134:
            ghost_y = 12 + bob_offset(f, period=10, phase=0) if f < 120 else lerp_i(12, 21, ease_in_out((f - 120) / 14.0))
            l_mood = "chomp" if (f % 8 < 4) else "delighted"
            u_mood = "chomp" if ((f + 4) % 8 < 4) else "happy"
            ly = 8 - (1 if (f % 8 < 4) else 0)
            uy = 9 - (1 if ((f + 4) % 8 < 4) else 0)

        # Draw Lumei with cute Witch Hat!
        draw_lumei_hi(c, lx, ly, mood=l_mood, has_bonnet=True, sprout_sway=0)
        draw_witch_hat(c, lx + 8, ly + 1)

        # Draw Lulu in adorable White Ghost Sheet Costume (tangerine still on top!!)
        draw_lulu_hi(c, ux, uy, mood=u_mood, has_tangerine=True)
        # White draped ghost sheet over Lulu's torso & scalloped hem!
        c.rect(ux + 2, uy + 11, 14, 8, HC["ghost_white"])
        c.vline(ux + 15, uy + 11, 8, HC["ghost_shade"])
        c.hline(ux + 3, uy + 11, 12, C["white"])
        for sx in (ux + 3, ux + 7, ux + 11, ux + 14):
            c.set(sx, uy + 19, HC["ghost_white"])

        # Glowing Carved Jack-o'-Lantern center stage (x=34..40, y=22..28)
        px, py = 34, 22
        c.set(px + 3, py - 1, C["stem_green"])
        c.hline(px + 1, py, 5, HC["pumpkin_hi"])
        c.rect(px, py + 1, 7, 5, HC["pumpkin_main"])
        c.vline(px + 6, py + 1, 5, HC["pumpkin_dark"])
        c.hline(px + 1, py + 6, 5, HC["pumpkin_dark"])
        # Flickering carved eyes & grin
        glow = C["flame_hi"] if (f % 6 < 4) else HC["gold_mid"]
        c.set(px + 1, py + 2, glow)
        c.set(px + 5, py + 2, glow)
        c.hline(px + 1, py + 4, 5, glow)
        c.set(px + 3, py + 4, HC["pumpkin_dark"])  # cute jack-o'-lantern tooth!

        # Friendly little popping ghost!
        if ghost_y is not None:
            gx, gy = 35, ghost_y
            c.hline(gx + 1, gy, 3, C["white"])
            c.rect(gx, gy + 1, 5, 4, HC["ghost_white"])
            c.set(gx + 1, gy + 2, C["eye"])
            c.set(gx + 3, gy + 2, C["eye"])
            c.set(gx + 2, gy + 3, HC["pink_soft"])
            c.set(gx, gy + 5, HC["ghost_shade"])
            c.set(gx + 2, gy + 5, HC["ghost_white"])
            c.set(gx + 4, gy + 5, HC["ghost_shade"])
            if 32 <= f < 44:
                draw_exclaim(c, ux + 9, uy - 9)

        # Colorful wrapped Halloween candies raining down!
        if candy_on:
            candy_cols = [HC["pumpkin_hi"], HC["violet_bright"], HC["emerald_hi"], HC["pink_hot"]]
            for ci, (cx0, delay) in enumerate([(29, 0), (35, 6), (41, 12), (32, 18), (39, 24)]):
                age = f - 65 - delay
                if 0 <= age <= 24:
                    cy = lerp_i(14, 26, age / 24.0)
                    col = candy_cols[ci % len(candy_cols)]
                    c.set(cx0 - 1, cy, C["white"])
                    c.hline(cx0, cy, 2, col)
                    c.set(cx0 + 2, cy, C["white"])

        if 108 <= f < 130:
            draw_heart(c, 36, 9 - (f - 108) // 6)
        return c.img

    # -----------------------------------------------------------------------
    # 10. THANKSGIVING (4th Thu of Nov) — Autumn Harvest Feast & Roast Turkey!
    # -----------------------------------------------------------------------
    def render_holiday_thanksgiving(f: int) -> Image.Image:
        c = Canvas()
        # Deep crisp autumn twilight indigo-plum so golden avatars, orange pumpkins & roast turkey pop!
        c.gradient_v((16, 20, 48, 255), (38, 30, 68, 255), 0, 27)
        draw_twinkle_stars(c, f, [(23, 3, 0), (35, 5, 5), (49, 2, 10), (59, 6, 3)])

        # Subtle cool twilight horizon band (contrasts gold coats & bright orange leaves)
        c.hline(0, 25, WIDTH, (54, 42, 78, 255))
        c.hline(0, 26, WIDTH, (46, 36, 68, 255))

        # Deep pine-moss autumn orchard floor (crisp contrast against golden feet & pumpkins!)
        c.rect(0, 27, WIDTH, 5, (24, 46, 36, 255))
        c.hline(0, 27, WIDTH, (42, 74, 52, 255))
        c.hline(0, 31, WIDTH, (14, 30, 24, 255))
        # Plump autumn pumpkins on left & right ground edges (below HUD!)
        c.hline(5, 23, 5, HC["pumpkin_hi"])
        c.rect(4, 24, 7, 4, HC["pumpkin_main"])
        c.vline(10, 24, 4, HC["pumpkin_dark"])
        c.set(7, 22, C["stem_green"])
        c.rect(58, 25, 4, 3, HC["pumpkin_hi"])
        c.set(59, 24, C["stem_green"])

        bob_l = bob_offset(f, period=30, phase=0)
        bob_u = bob_offset(f, period=30, phase=15)
        lx, ly = 18, 8 + bob_l
        ux, uy = 46, 9 + bob_u
        l_mood = "blink" if (f % 50) in (10, 11) else "happy"
        u_mood = "blink" if (f % 50) in (36, 37) else "chill"
        l_walk, u_walk = 0, 0
        lulu_drumstick = False
        lumei_drumstick = False

        # Story:
        # 0..27:   Both admire the big steaming golden roast turkey on the silver platter!
        # 28..64:  Hungry Lulu leans in & grabs a crispy turkey drumstick for a big chomp!
        # 65..94:  Lumei spots him (giggles!) & Lulu shares the other drumstick with her!
        # 95..132: Both happily munch turkey drumsticks together with cozy floating hearts!
        # 133..149: Smooth seamless reset to f=0
        if 28 <= f < 65:
            t = min(1.0, (f - 28) / 18.0)
            ux = lerp_i(46, 45, ease_in_out(t))
            u_walk = (1 if (f % 6 < 3) else 2) if f < 46 else 0
            lulu_drumstick = f >= 44
            u_mood = "chomp" if (f >= 48 and f % 8 < 4) else "happy"
        elif 65 <= f < 95:
            ux = 45
            t = min(1.0, (f - 65) / 16.0)
            lx = lerp_i(18, 19, ease_in_out(t))
            l_walk = (1 if (f % 6 < 3) else 2) if f < 81 else 0
            lulu_drumstick = True
            lumei_drumstick = f >= 82
            l_mood = "startled" if f < 74 else "delighted"
            u_mood = "happy"
        elif 95 <= f < 133:
            lx, ux = 19, 45
            lulu_drumstick = True
            lumei_drumstick = True
            l_mood = "chomp" if (f % 10 < 5) else "delighted"
            u_mood = "chomp" if ((f + 5) % 10 < 5) else "happy"
            ly = 8 - (1 if (f % 10 < 5) else 0)
            uy = 9 - (1 if ((f + 5) % 10 < 5) else 0)
        elif 133 <= f < 150:
            t = ease_in_out((f - 133) / 17.0)
            lx = lerp_i(19, 18, t)
            ux = lerp_i(45, 46, t)
            l_walk = 1 if (f % 6 < 3) else 2
            u_walk = 2 if (f % 6 < 3) else 1

        draw_lumei_hi(c, lx, ly, mood=l_mood, scarf=True, scarf_flutter=1 if (f % 30) < 15 else 0, walk_step=l_walk)
        draw_lulu_hi(c, ux, uy, mood=u_mood, scarf=True, scarf_flutter=0 if (f % 30) < 15 else 1, walk_step=u_walk)

        # Cozy Wooden Harvest Feast Table + BIG Unmistakable Roast Turkey on Silver Platter!
        tx, ty = 33, 26
        c.hline(tx, ty, 13, HC["wood_hi"])
        c.hline(tx, ty + 1, 13, HC["wood_main"])
        c.vline(tx + 1, ty + 2, 3, HC["wood_dark"])
        c.vline(tx + 11, ty + 2, 3, HC["wood_dark"])

        # Silver platter + crisp green parsley garnish
        c.hline(tx + 1, ty - 1, 11, C["plate"])
        c.hline(tx + 2, ty - 1, 9, C["white"])
        c.set(tx + 1, ty - 2, HC["emerald_hi"])
        c.set(tx + 11, ty - 2, HC["emerald_hi"])

        # BIG Plump Asymmetric Golden-Brown Roast Turkey (classic Thanksgiving cartoon silhouette!)
        roast_outline = (86, 32, 10, 255)
        roast_dark = (128, 54, 18, 255)
        roast_main = (184, 92, 30, 255)
        roast_hi = (232, 146, 56, 255)
        roast_glint = (255, 218, 134, 255)

        # Plump rounded breast on left/center (tx+2..tx+10, ty-7..ty-2)
        c.hline(tx + 2, ty - 2, 9, roast_dark)
        c.hline(tx + 2, ty - 3, 9, roast_main)
        c.hline(tx + 2, ty - 4, 8, roast_main)
        c.hline(tx + 3, ty - 5, 7, roast_hi)
        c.hline(tx + 3, ty - 6, 5, roast_hi)
        c.hline(tx + 4, ty - 7, 3, roast_main)
        # Glossy butter-basted highlight on plump breast
        c.hline(tx + 4, ty - 6, 2, roast_glint)
        c.set(tx + 3, ty - 5, roast_glint)
        # Wing crease & dark roasted contour for 3D legibility
        c.hline(tx + 4, ty - 3, 4, roast_dark)
        c.set(tx + 5, ty - 4, roast_outline)
        c.set(tx + 2, ty - 2, roast_outline)
        c.set(tx + 10, ty - 2, roast_outline)

        # Iconic Curved Turkey Drumsticks with White Bone & Paper Frill sticking UP into the dark sky!
        if not lulu_drumstick:
            # Prominent right drumstick arching up-right cleanly against the dark sky!
            c.rect(tx + 8, ty - 5, 2, 2, roast_main)
            c.set(tx + 9, ty - 5, roast_hi)
            c.set(tx + 10, ty - 6, roast_hi)
            c.set(tx + 10, ty - 5, roast_dark)
            # Crisp white bone shaft + classic forked/frilled bone tip!
            c.set(tx + 11, ty - 7, C["white"])
            c.set(tx + 11, ty - 8, C["white"])
            c.set(tx + 12, ty - 8, C["white"])
            c.set(tx + 12, ty - 7, C["plate"])
        if not lumei_drumstick:
            # Second drumstick peeking up behind on upper-center-right (clearly silhouettes in dark sky!)
            c.set(tx + 7, ty - 6, roast_main)
            c.set(tx + 8, ty - 7, roast_hi)
            c.set(tx + 9, ty - 8, C["white"])
            c.set(tx + 9, ty - 9, C["white"])
            c.set(tx + 10, ty - 9, C["white"])

        # Rising hot turkey steam above the breast (period 15 -> exact loop)
        st = (f // 3) % 5
        c.set(tx + 4, ty - 8 - (st % 2), C["steam_dim"])
        if st < 3:
            c.set(tx + 6, ty - 9 - (st % 2), C["steam"])

        # Handheld Turkey Drumsticks (silhouetted cleanly against dark sky right beside their mouths!)
        if lulu_drumstick:
            dx, dy = ux - 3, uy + 8
            c.rect(dx + 1, dy, 3, 2, roast_main)
            c.set(dx + 1, dy, roast_hi)
            c.set(dx, dy + 1, C["white"])
            c.set(dx - 1, dy + 1, C["white"])
            c.set(dx - 1, dy, C["white"])
        if lumei_drumstick:
            dx, dy = lx + 14, ly + 9
            c.rect(dx, dy, 3, 2, roast_main)
            c.set(dx + 1, dy, roast_hi)
            c.set(dx + 3, dy + 1, C["white"])
            c.set(dx + 4, dy + 1, C["white"])
            c.set(dx + 4, dy, C["white"])

        if 98 <= f < 126:
            draw_heart(c, 38, 10 - (f - 98) // 6)

        # Gently falling autumn maple leaves (strictly clear of HUD!)
        leaves = [(23, 3, C["leaf_orange"]), (33, 9, C["leaf_red"]), (45, 2, C["leaf_gold"]), (55, 7, C["leaf_orange"]), (61, 14, C["leaf_red"])]
        for idx, (x0, y0, col) in enumerate(leaves):
            ly_f = wrap_pos(y0, 2, f, HEIGHT, direction=1)
            lx_f = (x0 + int(round(2 * wave_sin(f, cycles=3, phase=idx)))) % WIDTH
            if ly_f < 27 and not (lx_f < 20 and ly_f < 12):
                c.set(lx_f, ly_f, col)
                c.set((lx_f + 1) % WIDTH, ly_f, col)
        return c.img

    # -----------------------------------------------------------------------
    # 11. CHRISTMAS (Dec 24 18:00+ & Dec 25) — Santa Hats, Tree & Present Pop!
    # -----------------------------------------------------------------------
    def render_holiday_christmas(f: int) -> Image.Image:
        c = Canvas()
        c.gradient_v((10, 18, 44, 255), (24, 42, 82, 255), 0, 28)
        draw_twinkle_stars(c, f, [(23, 3, 0), (31, 6, 5), (41, 2, 10), (47, 7, 3)])

        # Moonlit blue-tinted winter snow floor (lets bright white snowman & gift box pop!)
        c.rect(0, 28, WIDTH, 4, (118, 152, 196, 255))
        c.hline(0, 28, WIDTH, (164, 198, 232, 255))
        c.hline(0, 31, WIDTH, (84, 114, 156, 255))

        # Twinkling Decorated Christmas Tree on right (x=50..62, y=6..28)
        tx = 56
        # Trunk
        c.rect(tx - 1, 25, 3, 4, HC["wood_dark"])
        # Layered pine boughs
        tiers = [
            (9, 1), (10, 3), (11, 5),
            (12, 3), (13, 5), (14, 7), (15, 9),
            (16, 5), (17, 7), (18, 9), (19, 11),
            (20, 7), (21, 9), (22, 11), (23, 13), (24, 13),
        ]
        for ty, tw in tiers:
            x0 = tx - tw // 2
            c.hline(x0, ty, tw, HC["pine_main"])
            c.hline(x0, ty, max(1, tw // 3), HC["pine_hi"])
            c.set(x0 + tw - 1, ty, HC["pine_dark"])
        # Gleaming golden star topper (y=6..8)
        star_bright = (f % 10) < 6
        c.set(tx, 6, C["white"] if star_bright else HC["gold_bright"])
        c.hline(tx - 1, 7, 3, HC["gold_bright"])
        c.set(tx, 8, HC["gold_mid"])
        # Blinking colored tree lights!
        lights = [
            (tx, 11, HC["red_bright"], 0),
            (tx - 2, 14, HC["gold_bright"], 1),
            (tx + 2, 15, HC["cyan_bright"], 0),
            (tx - 1, 18, HC["pink_hot"], 1),
            (tx + 3, 19, HC["red_bright"], 0),
            (tx - 4, 22, HC["gold_bright"], 1),
            (tx, 21, HC["cyan_bright"], 0),
            (tx + 4, 23, HC["pink_hot"], 1),
        ]
        blink_phase = (f // 15) % 2
        for lx_t, ly_t, lcol, group in lights:
            c.set(lx_t, ly_t, C["white"] if (group == blink_phase and f % 15 < 5) else (lcol if group == blink_phase else HC["pine_hi"]))

        bob_l = bob_offset(f, period=30, phase=0)
        bob_u = bob_offset(f, period=30, phase=15)
        lx, ly = 19, 8 + bob_l
        ux, uy = 35, 9 + bob_u

        # Cozy little smiling snowman on the left snow (strictly below HUD!)
        c.rect(5, 23, 7, 5, C["snow_bright"])
        c.hline(6, 22, 5, C["white"])
        c.rect(6, 18, 5, 4, C["white"])
        c.set(7, 19, C["eye"]); c.set(9, 19, C["eye"])
        c.hline(8, 20, 2, C["orange_main"])  # carrot nose!
        c.hline(6, 22, 5, HC["red_bright"])  # tiny red scarf!
        c.set(8, 24, C["eye"]); c.set(8, 26, C["eye"])
        l_mood = "blink" if (f % 50) in (10, 11) else "happy"
        u_mood = "blink" if (f % 50) in (36, 37) else "chill"
        gift_shake = 0
        lid_lift = 0
        candy_cane_y = None

        # Story:
        # 0..29:   Snow falls gently under the twinkling tree; red/gold present sits between them
        # 30..54:  Present wiggles & shakes excitedly!
        # 55..84:  POP! Lid flies up with golden sparkles & striped candy cane!
        # 85..129: Both jump for joy with hearts under the glowing tree!
        # 130..149: Lid settles gently back for seamless loop
        if 30 <= f < 55:
            gift_shake = -1 if (f % 4 < 2) else 1
            l_mood = "happy"
            u_mood = "happy"
        elif 55 <= f < 85:
            lid_lift = min(5, (f - 55) // 3)
            candy_cane_y = lerp_i(22, 15, min(1.0, (f - 55) / 14.0))
            l_mood, u_mood = "delighted", "happy"
            ly = 8 - (2 if (f % 6 < 3) else 0)
            uy = 9 - (2 if ((f + 3) % 6 < 3) else 0)
        elif 85 <= f < 130:
            lid_lift = 5
            candy_cane_y = 15 + bob_offset(f, period=15, phase=0)
            l_mood, u_mood = "delighted", "happy"
            ly = 8 - (1 if (f % 8 < 4) else 0)
            uy = 9 - (1 if ((f + 4) % 8 < 4) else 0)
        elif 130 <= f < 150:
            t = ease_in_out((f - 130) / 20.0)
            lid_lift = lerp_i(5, 0, t)

        draw_lumei_hi(c, lx, ly, mood=l_mood, scarf=True, scarf_flutter=1 if (f % 30) < 15 else 0)
        draw_santa_hat(c, lx + 8, ly + 1)
        draw_lulu_hi(c, ux, uy, mood=u_mood, scarf=True, scarf_flutter=0 if (f % 30) < 15 else 1, has_tangerine=False)
        draw_santa_hat(c, ux + 9, uy)

        # Red & Gold Present Box in foreground!
        draw_gift_box(c, 31 + gift_shake, 23, HC["red_bright"], HC["red_deep"], HC["gold_bright"], lid_lift=lid_lift)

        # Striped Candy Cane & sparkles popping out of the gift!
        if candy_cane_y is not None:
            ccx, ccy = 34, candy_cane_y
            c.vline(ccx, ccy + 1, 5, C["white"])
            c.set(ccx, ccy + 2, HC["red_bright"])
            c.set(ccx, ccy + 4, HC["red_bright"])
            c.set(ccx + 1, ccy, HC["red_bright"])
            c.set(ccx + 2, ccy + 1, C["white"])
            if 55 <= f < 85:
                draw_sparkle(c, 30, 15, HC["gold_bright"], big=(f % 4 < 2))
                draw_sparkle(c, 38, 16, C["white"], big=(f % 4 >= 2))

        if 86 <= f < 122:
            draw_heart(c, 34, 9 - (f - 86) // 6)

        # Gentle Christmas snowfall (clear of HUD!)
        flakes = [(22, 4, 0), (29, 12, 1), (37, 2, 2), (44, 15, 3), (51, 5, 4), (61, 11, 2), (25, 21, 1)]
        for x0, y0, ph in flakes:
            sy = wrap_pos(y0, 2, f, HEIGHT, direction=1)
            sx = (x0 + int(round(wave_sin(f, cycles=3, phase=ph)))) % WIDTH
            if sy < 28 and not (sx < 20 and sy < 12):
                c.set(sx, sy, C["snow_bright"] if ph % 2 == 0 else C["snow_mid"])
        return c.img

    return {
        "holiday_new_year": render_holiday_new_year,
        "holiday_lunar_new_year": render_holiday_lunar_new_year,
        "holiday_valentines": render_holiday_valentines,
        "birthday_lulu": render_birthday_lulu,
        "holiday_st_patricks": render_holiday_st_patricks,
        "holiday_easter": render_holiday_easter,
        "holiday_independence": render_holiday_independence,
        "birthday_lumei": render_birthday_lumei,
        "holiday_halloween": render_holiday_halloween,
        "holiday_thanksgiving": render_holiday_thanksgiving,
        "holiday_christmas": render_holiday_christmas,
    }
