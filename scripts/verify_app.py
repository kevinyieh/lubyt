#!/usr/bin/env python3
"""
Starlark Syntax, Pixlet API, and Seamless-Loop Verifier for Capybara Clock.

Because `pixlet` may not be installed in every local environment, this script:
  1. Parses `capybara_clock.star` with Python's AST and verifies strict Starlark
     compatibility (no try/except, while, class, f-strings, Python-only syntax,
     and only whitelisted Pixlet built-in `load()` modules).
  2. Executes `capybara_clock.star` inside a faithful Pixlet Starlark runtime mock
     to test `get_schema()`, `main(config)` across all 6 weather states, WMO code
     mapping, caching (`cache.get`/`cache.set`), and Zip geocoding.
  3. Decodes every embedded base64 GIF inside `capybara_clock.star` and verifies:
     - Dimensions == 32x32
     - Frame count == 150
     - Frame duration == 100 ms (total 15,000 ms = 15.0s)
     - Loop == 0 (infinite)
     - Corresponding `assets/<state>.gif` and `assets/<state>.webp` match
  4. Renders a simulated 64x32 Tidbyt composite preview PNG in `assets/previews/`
     so you can inspect the full left-clock + right-capybara layout visually.
"""

from __future__ import annotations

import ast
import base64
import io
import json as py_json
import tokenize
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, ImageDraw

ROOT_DIR = Path(__file__).resolve().parent.parent
STAR_FILE = ROOT_DIR / "capybara_clock.star"
ASSETS_DIR = ROOT_DIR / "assets"
PREVIEWS_DIR = ASSETS_DIR / "previews"

ALLOWED_PIXLET_MODULES = {
    "cache.star",
    "encoding/base64.star",
    "encoding/json.star",
    "http.star",
    "humanize.star",
    "math.star",
    "render.star",
    "schema.star",
    "time.star",
}

EXPECTED_STATES = ("sunny", "rainy", "snowy", "windy", "thunderstorm", "default")
EXPECTED_FRAMES = 150
EXPECTED_DELAY_MS = 100


# ---------------------------------------------------------------------------
# 1. Strict Starlark AST & Module Linter
# ---------------------------------------------------------------------------
def check_starlark_ast(source: str) -> None:
    tree = ast.parse(source, filename=str(STAR_FILE))
    forbidden_nodes = (
        ast.Try,
        ast.While,
        ast.ClassDef,
        ast.Import,
        ast.ImportFrom,
        ast.JoinedStr,  # f-strings are not valid Starlark
        ast.With,
        ast.Yield,
        ast.AsyncFunctionDef,
        ast.Raise,
        ast.Set,
    )
    errors: List[str] = []

    for node in ast.walk(tree):
        if isinstance(node, forbidden_nodes):
            errors.append(
                f"Line {getattr(node, 'lineno', '?')}: Forbidden in Starlark: {type(node).__name__}"
            )
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if isinstance(op, (ast.Is, ast.IsNot)):
                    errors.append(
                        f"Line {node.lineno}: Use `== None` / `!= None` instead of `is` / `is not` in Starlark."
                    )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "load":
            if not node.args or not isinstance(node.args[0], ast.Constant):
                errors.append(f"Line {node.lineno}: Invalid load() statement.")
            else:
                mod = node.args[0].value
                if mod not in ALLOWED_PIXLET_MODULES:
                    errors.append(f"Line {node.lineno}: Disallowed Pixlet module: {mod!r}")

    if errors:
        raise AssertionError("Starlark validation failed:\n  " + "\n  ".join(errors))

    # Also check for Python-style implicit adjacent string literal concatenation
    # (disallowed in starlark-go: `got string literal, want ')'`).
    prev_tok = None
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT):
            continue
        if prev_tok is not None and prev_tok.type == tokenize.STRING and tok.type == tokenize.STRING:
            raise AssertionError(
                f"Line {tok.start[0]}: Implicit adjacent string literal concatenation is not valid Starlark."
            )
        prev_tok = tok

    print("[PASS] Strict Starlark AST, token, & Pixlet load() whitelist check")


# ---------------------------------------------------------------------------
# 2. Faithful Pixlet Runtime Mock
# ---------------------------------------------------------------------------
class MockWidget:
    def __init__(self, kind: str, **kwargs: Any):
        self.kind = kind
        self.props = kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self) -> str:
        return f"<{self.kind} {list(self.props.keys())}>"


class MockModule:
    def __init__(self, name: str, handlers: Dict[str, Any]):
        self._name = name
        for k, v in handlers.items():
            setattr(self, k, v)


def build_pixlet_runtime(fake_http_responses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    cache_store: Dict[str, str] = {}
    http_calls: List[str] = []

    def cache_get(key: str):
        return cache_store.get(key)

    def cache_set(key: str, value: str, ttl_seconds: int = 60):
        assert isinstance(key, str) and isinstance(value, str), "cache key/value must be strings"
        assert ttl_seconds > 0
        cache_store[key] = value

    class MockHttpResp:
        def __init__(self, status_code: int, payload: Any):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    def http_get(url: str, ttl_seconds: int = 0):
        http_calls.append(url)
        for prefix, payload in fake_http_responses.items():
            if url.startswith(prefix):
                return MockHttpResp(200, payload)
        return MockHttpResp(404, {})

    class MockTimeObj:
        def in_location(self, tz: str):
            assert isinstance(tz, str) and len(tz) > 0
            return self

        def format(self, layout: str) -> str:
            mapping = {
                "Mon": "Wed",
                "15:04": "19:09",
                "3:04": "7:09",
                "PM": "PM",
            }
            return mapping.get(layout, layout)

    modules = {
        "cache.star": {
            "cache": MockModule("cache", {"get": cache_get, "set": cache_set}),
        },
        "encoding/base64.star": {
            "base64": MockModule("base64", {"decode": lambda s: base64.b64decode(s)}),
        },
        "encoding/json.star": {
            "json": MockModule("json", {"decode": py_json.loads, "encode": py_json.dumps}),
        },
        "http.star": {
            "http": MockModule("http", {"get": http_get}),
        },
        "render.star": {
            "render": MockModule(
                "render",
                {
                    "Root": lambda **kw: MockWidget("Root", **kw),
                    "Row": lambda **kw: MockWidget("Row", **kw),
                    "Column": lambda **kw: MockWidget("Column", **kw),
                    "Box": lambda **kw: MockWidget("Box", **kw),
                    "Text": lambda **kw: MockWidget("Text", **kw),
                    "Image": lambda **kw: MockWidget("Image", **kw),
                },
            ),
        },
        "schema.star": {
            "schema": MockModule(
                "schema",
                {
                    "Schema": lambda **kw: MockWidget("Schema", **kw),
                    "Location": lambda **kw: MockWidget("Location", **kw),
                    "Text": lambda **kw: MockWidget("Text", **kw),
                    "Toggle": lambda **kw: MockWidget("Toggle", **kw),
                    "Dropdown": lambda **kw: MockWidget("Dropdown", **kw),
                    "Option": lambda **kw: MockWidget("Option", **kw),
                },
            ),
        },
        "time.star": {
            "time": MockModule("time", {"now": lambda: MockTimeObj()}),
        },
    }

    env: Dict[str, Any] = {
        "_cache_store": cache_store,
        "_http_calls": http_calls,
    }

    def starlark_load(module_path: str, *names: str, **aliases: str):
        mod = modules[module_path]
        for n in names:
            env[n] = mod[n]
        for alias, orig in aliases.items():
            env[alias] = mod[orig]

    env["load"] = starlark_load
    return env


class MockConfig:
    def __init__(self, values: Dict[str, Any]):
        self._values = values

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    def str(self, key: str, default: str = "") -> str:
        val = self._values.get(key)
        return str(val) if val is not None else default

    def bool(self, key: str, default: bool = False) -> bool:
        val = self._values.get(key)
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1", "yes")


# ---------------------------------------------------------------------------
# 3. Verification Suite
# ---------------------------------------------------------------------------
def main() -> None:
    source = STAR_FILE.read_text(encoding="utf-8")
    check_starlark_ast(source)

    fake_http = {
        "https://api.open-meteo.com/v1/forecast": {
            "current": {
                "temperature_2m": 45.4,
                "weather_code": 61,  # Slight rain
                "wind_speed_10m": 12.0,
                "is_day": 1,
            }
        },
        "https://geocoding-api.open-meteo.com/v1/search": {
            "results": [
                {
                    "latitude": 40.672,
                    "longitude": -73.986,
                    "timezone": "America/New_York",
                }
            ]
        },
    }

    env = build_pixlet_runtime(fake_http)
    exec(compile(source, str(STAR_FILE), "exec"), env)

    # Verify get_schema()
    schema_obj = env["get_schema"]()
    field_ids = [f.props["id"] for f in schema_obj.props["fields"]]
    for required_id in ("location", "latitude", "longitude", "zip_code", "timezone", "use_24h", "temp_unit", "debug_weather"):
        assert required_id in field_ids, f"Missing schema field: {required_id}"
    print(f"[PASS] get_schema() verified ({len(field_ids)} fields: {', '.join(field_ids)})")

    # Verify WMO weather mapping across all states
    mapper = env["map_wmo_to_weather"]
    assert mapper(0, 5.0, 1) == ("sunny", "SUNNY")
    assert mapper(0, 5.0, 0) == ("default", "CLEAR")
    assert mapper(3, 10.0, 1) == ("default", "CLOUDY")
    assert mapper(45, 4.0, 1) == ("default", "FOGGY")
    assert mapper(2, 30.0, 1) == ("windy", "WINDY")
    assert mapper(63, 35.0, 1) == ("rainy", "RAINY")
    assert mapper(75, 10.0, 1) == ("snowy", "SNOWY")
    assert mapper(95, 40.0, 1) == ("thunderstorm", "STORM")
    print("[PASS] WMO weather code + wind + day/night mapping verified")

    # Verify caching (first call hits HTTP, second hits cache.get with zero extra HTTP calls)
    cfg = MockConfig({"zip_code": "11215", "temp_unit": "F", "use_24h": False})
    root1 = env["main"](cfg)
    calls_after_first = len(env["_http_calls"])
    assert calls_after_first == 2, f"Expected 2 HTTP calls (geocode + forecast), got {calls_after_first}"
    root2 = env["main"](cfg)
    assert len(env["_http_calls"]) == calls_after_first, "Expected cache hit on second render!"
    assert root1.props["delay"] == EXPECTED_DELAY_MS
    assert root1.props["show_full_animation"] is True
    assert root2.props["max_age"] == 300
    print("[PASS] Open-Meteo caching (cache.get/cache.set) & zip geocoding verified")

    # Verify all 6 embedded base64 GIFs + assets/*.gif + assets/*.webp
    sprites_b64: Dict[str, str] = env["SPRITES_B64"]
    assert tuple(sprites_b64.keys()) == EXPECTED_STATES, f"Unexpected sprite keys: {sprites_b64.keys()}"

    for state in EXPECTED_STATES:
        # Execute main() with debug override for each state
        root = env["main"](MockConfig({"debug_weather": state, "temp_unit": "F"}))
        row_children = root.props["child"].props["children"]
        assert len(row_children) == 3  # left(31) + divider(1) + right(32) = 64
        total_w = sum(child.props["width"] for child in row_children)
        assert total_w == 64, f"Expected 64px width, got {total_w}"

        # Decode base64 GIF passed to render.Image
        img_widget = row_children[2].props["child"]
        gif_bytes = img_widget.props["src"]
        with Image.open(io.BytesIO(gif_bytes)) as gif_im:
            assert gif_im.size == (32, 32), f"{state} GIF size != 32x32"
            assert gif_im.n_frames == EXPECTED_FRAMES, f"{state} GIF frames={gif_im.n_frames} != {EXPECTED_FRAMES}"
            assert gif_im.info.get("loop") == 0, f"{state} GIF loop != 0"
            gif_durs = []
            for f_i in range(gif_im.n_frames):
                gif_im.seek(f_i)
                gif_durs.append(gif_im.info.get("duration", 0))
            assert all(d == EXPECTED_DELAY_MS for d in gif_durs), f"{state} GIF non-uniform durations: {set(gif_durs)}"
            assert sum(gif_durs) == EXPECTED_FRAMES * EXPECTED_DELAY_MS

        # Check matching disk assets (.gif and .webp)
        gif_path = ASSETS_DIR / f"{state}.gif"
        webp_path = ASSETS_DIR / f"{state}.webp"
        assert gif_path.read_bytes() == gif_bytes, f"{state}.gif on disk out of sync with .star!"
        with Image.open(webp_path) as webp_im:
            assert webp_im.size == (32, 32)
            assert webp_im.n_frames == EXPECTED_FRAMES, f"{state} WebP frames={webp_im.n_frames} != {EXPECTED_FRAMES}"
            assert webp_im.info.get("loop") == 0
            webp_durs = []
            for f_i in range(webp_im.n_frames):
                webp_im.seek(f_i)
                webp_im.load()
                webp_durs.append(webp_im.info.get("duration", 0))
            assert all(d == EXPECTED_DELAY_MS for d in webp_durs), f"{state} WebP durations: {set(webp_durs)}"
            assert sum(webp_durs) == EXPECTED_FRAMES * EXPECTED_DELAY_MS

    print(
        f"[PASS] All 6 embedded GIFs & WebPs verified: 32x32, {EXPECTED_FRAMES} frames @ "
        f"{EXPECTED_DELAY_MS}ms = {EXPECTED_FRAMES * EXPECTED_DELAY_MS / 1000:.1f}s, loop=0"
    )

    # Generate a quick 64x32 simulated Tidbyt display preview (all 6 states stacked)
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    scale = 6
    pad = 10
    card_w, card_h = 64 * scale, 32 * scale
    cols = 2
    rows = 3
    sheet = Image.new("RGB", (pad + cols * (card_w + pad), pad + rows * (card_h + pad)), (12, 14, 20))

    themes = env["WEATHER_THEMES"]
    sample_temps = {
        "sunny": "74°F",
        "rainy": "58°F",
        "snowy": "28°F",
        "windy": "52°F",
        "thunderstorm": "66°F",
        "default": "45°F",
    }

    for idx, state in enumerate(EXPECTED_STATES):
        r, c_idx = divmod(idx, cols)
        theme = themes[state]
        frame_idx = 33 if state == "thunderstorm" else 0
        with Image.open(ASSETS_DIR / f"{state}.gif") as im:
            im.seek(frame_idx)
            right_rgb = im.convert("RGB")

        # Compose 64x32 mock screen
        bg_hex = theme["bg"].lstrip("#")
        bg_rgb = tuple(int(bg_hex[i:i + 2], 16) for i in (0, 2, 4))
        div_hex = theme["divider"].lstrip("#")
        div_rgb = tuple(int(div_hex[i:i + 2], 16) for i in (0, 2, 4))

        mock_64x32 = Image.new("RGB", (64, 32), bg_rgb)
        mock_64x32.paste(right_rgb, (32, 0))
        for y in range(32):
            mock_64x32.putpixel((31, y), div_rgb)

        upscaled = mock_64x32.resize((card_w, card_h), Image.Resampling.NEAREST)
        draw = ImageDraw.Draw(upscaled)
        # Approximate Tidbyt left-half typography preview
        draw.text((22, 16), "WED PM", fill=theme["day"])
        draw.text((14, 58), "7:09", fill=theme["time"])
        draw.text((24, 114), sample_temps[state], fill=theme["temp"])
        draw.text((22, 152), theme["default_label"], fill=theme["label"])

        sheet.paste(upscaled, (pad + c_idx * (card_w + pad), pad + r * (card_h + pad)))

    preview_path = PREVIEWS_DIR / "tidbyt_64x32_mockup.png"
    sheet.save(preview_path)
    print(f"[PASS] Saved 64x32 Tidbyt layout mockup -> {preview_path}")


if __name__ == "__main__":
    main()
