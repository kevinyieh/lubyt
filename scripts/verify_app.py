#!/usr/bin/env python3
"""
Starlark Syntax, Pixlet API, Sunset-Switching, and Seamless-Loop Verifier.

Verifies:
  1. Strict Starlark AST + token check (no implicit string concat, allowed Pixlet loads).
  2. All 28 official Open-Meteo WMO codes + wind mapping.
  3. Exact sunrise/sunset switching (`is_night_from_sun`) before sunrise, midday, and after sunset.
  4. Open-Meteo caching (`cache.get`/`cache.set`), zip geocoding, and minimal upper-left Time+Temp HUD.
  5. All 24 Day & Night embedded GIFs + on-disk `.gif`/`.webp` assets:
     64x32, exact 150 uniform frames @ 100ms = 15.0s, loop=0.
"""

from __future__ import annotations

import ast
import base64
import io
import json as py_json
import tokenize
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
STAR_FILE = ROOT_DIR / "capybara_clock.star"
ASSETS_DIR = ROOT_DIR / "assets"

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
TEMP_AWARE_WEATHERS = ("clear", "partly_cloudy")
EXPECTED_STATES = tuple(
    f"{w}_{tod}_{tier}" if w in TEMP_AWARE_WEATHERS else f"{w}_{tod}"
    for w in WEATHER_TYPES
    for tod in ("day", "night")
    for tier in (("warm", "cold") if w in TEMP_AWARE_WEATHERS else ("",))
)
EXPECTED_WIDTH = 64
EXPECTED_HEIGHT = 32
EXPECTED_FRAMES = 150
EXPECTED_DELAY_MS = 100


def check_starlark_ast(source: str) -> None:
    tree = ast.parse(source, filename=str(STAR_FILE))
    forbidden_nodes = (
        ast.Try,
        ast.While,
        ast.ClassDef,
        ast.Import,
        ast.ImportFrom,
        ast.JoinedStr,
        ast.With,
        ast.Yield,
        ast.AsyncFunctionDef,
        ast.Raise,
        ast.Set,
    )
    errors: List[str] = []

    for node in ast.walk(tree):
        if isinstance(node, forbidden_nodes):
            errors.append(f"Line {getattr(node, 'lineno', '?')}: Forbidden in Starlark: {type(node).__name__}")
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if isinstance(op, (ast.Is, ast.IsNot)):
                    errors.append(f"Line {node.lineno}: Use `== None` / `!= None` in Starlark.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "load":
            if not node.args or not isinstance(node.args[0], ast.Constant):
                errors.append(f"Line {node.lineno}: Invalid load() statement.")
            elif node.args[0].value not in ALLOWED_PIXLET_MODULES:
                errors.append(f"Line {node.lineno}: Disallowed Pixlet module: {node.args[0].value!r}")

    if errors:
        raise AssertionError("Starlark validation failed:\n  " + "\n  ".join(errors))

    prev_tok = None
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT):
            continue
        if prev_tok is not None and prev_tok.type == tokenize.STRING and tok.type == tokenize.STRING:
            raise AssertionError(f"Line {tok.start[0]}: Implicit string concatenation is invalid in Starlark.")
        prev_tok = tok

    print("[PASS] Strict Starlark AST, token, & Pixlet load() whitelist check")


class MockWidget:
    def __init__(self, kind: str, **kwargs: Any):
        self.kind = kind
        self.props = kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)


class MockModule:
    def __init__(self, name: str, handlers: Dict[str, Any]):
        self._name = name
        for k, v in handlers.items():
            setattr(self, k, v)


def build_pixlet_runtime(fake_http_responses: Dict[str, Dict[str, Any]], now_24h: str = "19:09") -> Dict[str, Any]:
    cache_store: Dict[str, str] = {}
    http_calls: List[str] = []

    def cache_get(key: str):
        return cache_store.get(key)

    def cache_set(key: str, value: str, ttl_seconds: int = 60):
        assert isinstance(key, str) and isinstance(value, str) and ttl_seconds > 0
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
            h, m = now_24h.split(":")
            h12 = str(int(h) % 12 or 12)
            return {"15:04": now_24h, "3:04": f"{h12}:{m}"}.get(layout, layout)

    modules = {
        "cache.star": {"cache": MockModule("cache", {"get": cache_get, "set": cache_set})},
        "encoding/base64.star": {"base64": MockModule("base64", {"decode": lambda s: base64.b64decode(s)})},
        "encoding/json.star": {"json": MockModule("json", {"decode": py_json.loads, "encode": py_json.dumps})},
        "http.star": {"http": MockModule("http", {"get": http_get})},
        "render.star": {
            "render": MockModule(
                "render",
                {
                    "Root": lambda **kw: MockWidget("Root", **kw),
                    "Stack": lambda **kw: MockWidget("Stack", **kw),
                    "Padding": lambda **kw: MockWidget("Padding", **kw),
                    "Column": lambda **kw: MockWidget("Column", **kw),
                    "Box": lambda **kw: MockWidget("Box", **kw),
                    "Text": lambda **kw: MockWidget("Text", **kw),
                    "Image": lambda **kw: MockWidget("Image", **kw),
                },
            )
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
            )
        },
        "time.star": {"time": MockModule("time", {"now": lambda: MockTimeObj()})},
    }

    env: Dict[str, Any] = {"_cache_store": cache_store, "_http_calls": http_calls}

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


def main() -> None:
    source = STAR_FILE.read_text(encoding="utf-8")
    check_starlark_ast(source)

    fake_http = {
        "https://api.open-meteo.com/v1/forecast": {
            "current": {"temperature_2m": 45.4, "weather_code": 2, "wind_speed_10m": 12.0, "is_day": 0},
            "daily": {
                "time": ["2026-11-26"],
                "sunrise": ["2026-11-26T06:55"],
                "sunset": ["2026-11-26T16:30"],
            },
        },
        "https://geocoding-api.open-meteo.com/v1/search": {
            "results": [{"latitude": 40.672, "longitude": -73.986, "timezone": "America/New_York"}]
        },
    }

    env = build_pixlet_runtime(fake_http, now_24h="19:09")
    exec(compile(source, str(STAR_FILE), "exec"), env)

    schema_obj = env["get_schema"]()
    field_ids = [f.props["id"] for f in schema_obj.props["fields"]]
    for req in ("location", "latitude", "longitude", "zip_code", "timezone", "use_24h", "temp_unit", "debug_weather", "debug_time_of_day", "debug_temp"):
        assert req in field_ids, f"Missing schema field: {req}"
    print(f"[PASS] get_schema() verified ({len(field_ids)} fields including debug_time_of_day & debug_temp)")

    # Verify all 28 official Open-Meteo WMO codes
    mapper = env["map_wmo_to_weather"]
    wmo_expected = {
        0: "clear", 1: "clear", 2: "partly_cloudy", 3: "overcast",
        45: "fog", 48: "fog",
        51: "drizzle", 53: "drizzle", 55: "drizzle",
        56: "freezing_rain", 57: "freezing_rain",
        61: "rain", 63: "rain", 65: "rain",
        66: "freezing_rain", 67: "freezing_rain",
        71: "snow", 73: "snow", 75: "snow", 77: "snow",
        80: "rain_showers", 81: "rain_showers", 82: "rain_showers",
        85: "snow", 86: "snow",
        95: "thunderstorm", 96: "thunderstorm_hail", 99: "thunderstorm_hail",
    }
    for code, expected in wmo_expected.items():
        assert mapper(code, 8.0) == expected, f"WMO {code}: got {mapper(code, 8.0)}"
    assert mapper(2, 30.0) == "windy"
    assert mapper(63, 35.0) == "rain"
    print(f"[PASS] All {len(wmo_expected)} official Open-Meteo WMO codes + wind verified")

    # Verify sunset/sunrise Day/Night switching
    is_night_fn = env["is_night_from_sun"]
    wx_sun = {"sunrise": "06:55", "sunset": "16:30", "is_day": 1}
    assert is_night_fn("06:54", wx_sun) is True, "Before sunrise must be night"
    assert is_night_fn("06:55", wx_sun) is False, "At sunrise must be day"
    assert is_night_fn("12:00", wx_sun) is False, "Midday must be day"
    assert is_night_fn("16:29", wx_sun) is False, "1 min before sunset must be day"
    assert is_night_fn("16:30", wx_sun) is True, "At sunset must switch to night"
    assert is_night_fn("23:15", wx_sun) is True, "Late evening must be night"
    print("[PASS] Daily sunrise/sunset Day-Night switching verified (06:55 -> 16:30)")

    # Verify caching + HUD + automatic night selection at 19:09 (> 16:30 sunset)
    cfg = MockConfig({"zip_code": "11215", "temp_unit": "F", "use_24h": False})
    root1 = env["main"](cfg)
    assert len(env["_http_calls"]) == 2
    root2 = env["main"](cfg)
    assert len(env["_http_calls"]) == 2, "Expected cache hit on second render!"
    assert root1.props["delay"] == EXPECTED_DELAY_MS and root2.props["show_full_animation"] is True

    stack_children = root1.props["child"].props["children"]
    # 45.4°F < 55°F and 19:09 > 16:30 sunset -> must select partly_cloudy_night_cold!
    assert stack_children[0].props["src"] == (ASSETS_DIR / "partly_cloudy_night_cold.gif").read_bytes()
    hud_texts = stack_children[1].props["child"].props["child"].props["children"]
    assert [t.props["content"] for t in hud_texts] == ["7:09", "45°"]
    # Check warm vs cold threshold in both F and C
    is_cold_fn = env["is_cold_temp"]
    assert is_cold_fn({"temp": 42.0}, "F") is True
    assert is_cold_fn({"temp": 68.0}, "F") is False
    assert is_cold_fn({"temp": 8.0}, "C") is True   # 46.4°F
    assert is_cold_fn({"temp": 20.0}, "C") is False # 68.0°F
    print("[PASS] Caching, auto sunset + cold/warm temp selection (F & C), & minimal HUD verified")

    # Verify all 28 GIFs + WebPs
    sprites_b64: Dict[str, str] = env["SPRITES_B64"]
    assert tuple(sprites_b64.keys()) == EXPECTED_STATES

    for state in EXPECTED_STATES:
        root = env["main"](MockConfig({"debug_weather": state}))
        gif_bytes = root.props["child"].props["children"][0].props["src"]
        with Image.open(io.BytesIO(gif_bytes)) as gif_im:
            assert gif_im.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT)
            assert gif_im.n_frames == EXPECTED_FRAMES
            assert gif_im.info.get("loop") == 0
            durs = []
            for i in range(gif_im.n_frames):
                gif_im.seek(i)
                durs.append(gif_im.info.get("duration", 0))
            assert all(d == EXPECTED_DELAY_MS for d in durs)

        assert (ASSETS_DIR / f"{state}.gif").read_bytes() == gif_bytes
        with Image.open(ASSETS_DIR / f"{state}.webp") as webp_im:
            assert webp_im.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT)
            assert webp_im.n_frames == EXPECTED_FRAMES
            assert webp_im.info.get("loop") == 0
            wdurs = []
            for i in range(webp_im.n_frames):
                webp_im.seek(i)
                webp_im.load()
                wdurs.append(webp_im.info.get("duration", 0))
            assert all(d == EXPECTED_DELAY_MS for d in wdurs)

    print(
        f"[PASS] All {len(EXPECTED_STATES)} Day/Night & Warm/Cold GIFs & WebPs verified: "
        f"{EXPECTED_WIDTH}x{EXPECTED_HEIGHT}, {EXPECTED_FRAMES} frames @ {EXPECTED_DELAY_MS}ms = 15.0s, loop=0"
    )


if __name__ == "__main__":
    main()
