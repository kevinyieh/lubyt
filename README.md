# Weather-Reactive Capybara Clock (Tidbyt / Pixlet)

A custom **64×32 Tidbyt LED matrix app** written in **Pixlet Starlark** featuring a crisp clock + live local weather panel on the left half and 15-second seamlessly looping pixel-art animations of **Lulu** (tiny orange on his head + strawberry shorts) and **Lumei** (pink bonnet/romper + tiny sprout on her head) reacting to the weather on the right half.

---

## Features

- **Left Half (32×32 px):** Clean static clock displaying day of the week (e.g., `WED PM` or `WED`), current time (`HH:MM` in 12h or 24h format), live temperature (`°F` or `°C`), and a color-themed weather label (`SUNNY`, `RAINY`, `SNOWY`, `WINDY`, `STORM`, `CLEAR`, `CLOUDY`, `FOGGY`).
- **Right Half (32×32 px):** Dynamically selected 15-second seamless loop (`150 frames @ 100 ms = 15.0s`, `loop=0`) of Lulu & Lumei across 6 distinct weather scenes:
  | State | WMO Codes / Trigger | Scene & Props |
  | :--- | :--- | :--- |
  | `sunny` | `0, 1` (daytime) | Cool sunglasses with lens glint, spinning pixel sun, and a two-bite watermelon cycle |
  | `rainy` | `51–57, 61–67, 80–82` | Huddled under a blue umbrella with slanted raindrops & puddle ripples |
  | `snowy` | `71–77, 85–86` | Cozy striped knit scarves, breath puffs, and gently swaying snowflakes |
  | `windy` | Wind ≥ `25 km/h` (dry) | Leaning into wind gusts with swirling autumn pixel leaves |
  | `thunderstorm` | `95, 96, 99` | Huddled under a starry purple blanket with two lightning-strike flashes |
  | `default` | `2, 3, 45, 48` or clear night | Starry twilight sky, drifting wispy cloud, relaxed bobbing, and floating hearts |
- **Free Open-Meteo API:** Zero API keys required, with 12-minute caching (`cache.get`/`cache.set` + `http.get(..., ttl_seconds=720)`) to avoid rate limits.
- **Mathematically Seamless 15-Second Loops:**
  - All idle bobbing/blinking oscillators use periods dividing `150` (`30`, `50`, `75` frames).
  - All particles (rain, snow, leaves, clouds, wind gusts) wrap via exact modulo arithmetic across the 32×32 canvas so `frame(150) == frame(0)` identically.
  - All one-off events (watermelon bites, lightning strikes) resolve back to the resting state well before frame 150.
- **Modular Sprite Pipeline:** Easily swap in hand-drawn Aseprite or PNG frames later via `assets/custom/`.

---

## Repository Structure

```text
capybara-clock/
├── capybara_clock.star            # Self-contained Pixlet Starlark applet
├── scripts/
│   ├── generate_sprites.py        # Pillow sprite generator, custom art importer & .star injector
│   └── verify_app.py              # Starlark syntax/API validator & seamless loop verifier
├── assets/
│   ├── sunny.{gif,webp}           # 32x32, 150 frames @ 100ms, loop=0
│   ├── rainy.{gif,webp}
│   ├── snowy.{gif,webp}
│   ├── windy.{gif,webp}
│   ├── thunderstorm.{gif,webp}
│   ├── default.{gif,webp}
│   ├── custom/                    # Drop hand-drawn Aseprite GIFs / PNGs here
│   └── previews/                  # Upscaled contact sheets for visual inspection
├── .github/
│   └── workflows/
│       └── push.yml               # 5-minute cron render + push to Tidbyt
└── README.md
```

---

## Local Setup & Testing

### 1. Install Pixlet

Pixlet is not pre-installed by default on macOS. Install it via Homebrew:

```bash
brew install tidbyt/tidbyt/pixlet
pixlet version
```

For Linux/WSL, download the latest release binary from [github.com/tidbyt/pixlet/releases](https://github.com/tidbyt/pixlet/releases) (and install `libwebp-dev`).

### 2. Interactive Live Preview (`pixlet serve`)

Run the local Pixlet web preview server (opens a live simulator + interactive schema controls at `http://localhost:8080`):

```bash
pixlet serve capybara_clock.star
```

Use the **Debug Weather Override** dropdown in the browser UI to instantly preview `Sunny`, `Rainy`, `Snowy`, `Windy`, `Thunderstorm`, and `Default`.

### 3. CLI Rendering (`pixlet render`)

Render a 15-second animated WebP directly from the command line:

```bash
# Default (Brooklyn, NY, live weather)
pixlet render capybara_clock.star -o preview.webp

# Override location, units, 24h clock, and force a specific weather state
pixlet render capybara_clock.star \
  latitude=40.6782 \
  longitude=-73.9442 \
  timezone=America/New_York \
  use_24h=false \
  temp_unit=F \
  debug_weather=rainy \
  -o preview_rainy.webp

# Or use a Zip Code instead of lat/lon
pixlet render capybara_clock.star zip_code=11215 debug_weather=snowy -o preview_snowy.webp
```

### 4. Push Manually to Your Tidbyt

```bash
pixlet push \
  --api-token "$TIDBYT_API_KEY" \
  --installation-id "capybara-clock" \
  "$TIDBYT_DEVICE_ID" \
  preview.webp
```

---

## Regenerating or Swapping Custom Sprites (Aseprite / PNG)

Requires Python 3.9+ and `Pillow` (`pip install pillow`):

```bash
# Regenerate all 6 weather states, update preview contact sheet, and inject base64 into capybara_clock.star
python3 scripts/generate_sprites.py --preview

# Run Starlark static verification & seamless loop tests
python3 scripts/verify_app.py
```

### Swapping in Hand-Drawn Art

To replace any state (`sunny`, `rainy`, `snowy`, `windy`, `thunderstorm`, `default`) with your own Aseprite or PNG art:

1. Export a 32×32 animation into `assets/custom/` using any of these formats:
   - `assets/custom/<state>.gif` (animated GIF from Aseprite)
   - `assets/custom/<state>_sheet.png` (horizontal strip of 32×32 tiles)
   - `assets/custom/<state>/frame_000.png ...` (sorted folder of 32×32 PNG frames)
2. Tip: choose a frame count that evenly divides `150` (e.g., `10`, `15`, `25`, `30`, `50`, `75`, or `150` frames at 100 ms/frame) for an exact 15-second loop.
3. Run `python3 scripts/generate_sprites.py --preview` — the script automatically imports your custom art, normalizes it to 150 frames @ 100 ms, and updates `capybara_clock.star`.

---

## Automated Deployment (GitHub Actions)

`.github/workflows/push.yml` renders and pushes `capybara_clock.star` to your Tidbyt every 5 minutes (and supports manual `workflow_dispatch` runs with an optional weather override).

### Required Repository Secrets
Add these under **Settings → Secrets and variables → Actions → Secrets**:
- `TIDBYT_DEVICE_ID` — Your Tidbyt device ID (from the Tidbyt mobile app or `pixlet devices`)
- `TIDBYT_API_KEY` — Your Tidbyt API key (from the Tidbyt mobile app under device settings)

### Optional Repository Variables
Add these under **Settings → Secrets and variables → Actions → Variables** to customize your location & display format:
- `CAPYBARA_LATITUDE` (e.g., `40.6782`)
- `CAPYBARA_LONGITUDE` (e.g., `-73.9442`)
- `CAPYBARA_ZIP_CODE` (e.g., `11215`, alternative to lat/lon)
- `CAPYBARA_TIMEZONE` (e.g., `America/New_York`)
- `CAPYBARA_USE_24H` (`true` or `false`)
- `CAPYBARA_TEMP_UNIT` (`F` or `C`)
