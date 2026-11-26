# Weather-Reactive Capybara Clock (Tidbyt / Pixlet)

A custom **64×32 Tidbyt LED matrix app** written in **Pixlet Starlark** featuring an ultra-minimal upper-left clock + temperature corner HUD over **28 full-screen high-resolution 15-second seamlessly looping animations** of **Lumei** (pale pink dotted ruffled bonnet + twin-leaf sprout + baby-pink romper) and **Lulu** (plump tangerine on his head + sleepy half-lidded eyes + strawberry shorts) reacting to live local weather, sunrise/sunset, and temperature.

---

## Features

- **Ultra-Minimal Upper-Left Corner HUD (20×12 px):** Displays **only** the current time (`HH:MM`) and temperature (`42°`, no F/C suffix) in crisp `tom-thumb` over a subtle translucent backing — leaving the entire **64×32 px** screen for the high-res characters and weather scenes.
- **Automatic Sunrise / Sunset & Temperature-Aware Switching:** Fetches today's local `daily.sunrise`, `daily.sunset`, and auto-detected IANA `timezone` from Open-Meteo. Switches every weather condition between **Day** and **Night** at sunrise/sunset, and automatically adapts temperature-sensitive activities (`clear` and `partly_cloudy`) at **55°F (12.8°C)** so they drink hot cocoa and warm up by a campfire when it's chilly instead of eating ice cream!
- **Complete Open-Meteo WMO Weather Coverage (28 Full-Screen 64×32 High-Res Storyboards):**
  | Weather | Open-Meteo Trigger | Day Storyboard | Night Storyboard |
  | :--- | :--- | :--- | :--- |
  | `clear` (Warm ≥ 55°F) | WMO `0, 1` | **Ice Cream Meltdown:** Lulu's ice cream melts → Lumei pops off-screen & returns with a fresh double-scoop cone | **Telescope Stargazing:** Brass telescope, crescent moon & twin shooting stars — Lumei & Lulu take turns making wishes |
  | `clear` (Cold < 55°F) | WMO `0, 1` | **Shared Hot Chocolate:** Lumei sips their shared mug dry (clearly empty cup!) → sad Lulu → Lumei brings back a fresh overflowing whipped-cream cocoa | **Campfire & Telescope:** Cozy crackling campfire with knit scarves alongside stargazing |
  | `partly_cloudy` (Warm / Cold) | WMO `2` | **Checkered Picnic Heist:** Lumei gobbles the snacks → sad Lulu (`💧`) → Lumei returns with a giant strawberry cake (warm) or steaming berry pie in knit scarves (cold) | **Moonlit Picnic:** Starry lantern picnic with candle cupcake (warm) or steaming winter pie & scarves (cold) |
  | `overcast` | WMO `3` | **Sleepy Blanket Snooze:** Cozy clouds put Lulu to sleep (`Zzz`) → Lumei wakes him → warm cuddle | **Close-Up Tucked in Bed:** High-fidelity zoomed-in bedroom scene — snooze bubble pop, blanket tug & sleepy cuddle |
  | `fog` | WMO `45, 48` | **Misty Hide-and-Seek:** Lulu wanders into thick fog → Lumei searches (`?`) → happy reunion | **Lantern Mist Search:** Lumei swings a glowing warm lantern through moonlit fog to find Lulu |
  | `drizzle` | WMO `51–55` | **Puddle Splash Ambush:** Cheerful Lumei puddle-splashes phone-holding Lulu → Lulu splashes right back | **Gentle Umbrella Escort:** Moonlight drizzle with Lulu walking Lumei home under a shared umbrella |
  | `freezing_rain` | WMO `56–57, 66–67` | **Ice Rink Wipeout:** Overconfident Lulu slides off-screen on gleaming ice → Lumei glides to rescue him | **Moonlit Tandem Ice Glide:** Lulu catches slipping Lumei & they glide smoothly together across the ice |
  | `rain` | WMO `61–65` | **Umbrella Tug-of-War:** Phone-glued Lulu drifts off hogging the blue umbrella → soaked spicy Lumei yanks it back | **Paper Boat Race:** Rainy night puddle with miniature paper boats bobbing under a shared umbrella |
  | `rain_showers` | WMO `80–82` | **Sun-Shower Rainbow:** Passing shower clears into bright sun & a **vivid 6-color Rainbow** | **Midnight Moonbow:** Night cloudburst clears into crescent moon & a shimmering **Moonbow** |
  | `snow` | WMO `71–77, 85–86` | **Escalating Snowball Fight:** Knit scarves, flying snowballs, Lulu's giant snowball & snowy head-cap | **Close-Up Frosty Window:** Zoomed-in high-fidelity window — Lumei & Lulu breathe frost and draw a glowing pink heart on the glass |
  | `thunderstorm` | WMO `95` | **Park Shelter Leap:** Overconfident Lulu stands outside the wooden park gazebo in the pouring rain until lightning sends him leaping safely under the dry roof! | **Close-Up Starry Blanket:** Zoomed-in bedroom storm — lightning flashes outside and Lulu ducks completely under the covers leaving only his tangerine poking out! |
  | `thunderstorm_hail` | WMO `96, 99` | **Silver Shield Scramble:** Bouncing hailstones bonk Lulu → sturdy silver shield huddle with ricochet sparks | **Night Shield Scramble:** Pitch-dark midnight hailstorm & ricocheting sparks under the shared silver shield |
  | `windy` | Wind ≥ `25 km/h` (dry) | **Runaway Kite & Gust Rescue:** Breezy gusts blow Lulu & kite off-screen → Lumei sprints to drag him back | **Midnight Bonnet Rescue:** Gust blows Lumei's bonnet off → heroic Lulu leaps to catch it & return it |
- **Free Open-Meteo API:** Zero API keys required, with 12-minute caching (`cache.get`/`cache.set` + `http.get(..., ttl_seconds=720)`) to avoid rate limits.
- **Mathematically Seamless 15-Second Loops:**
  - All idle bobbing/blinking oscillators use periods dividing `150` (`30`, `50`, `75` frames).
  - All particles (rain, snow, leaves, clouds, wind gusts) wrap via exact modulo arithmetic across the 64×32 canvas so `frame(150) == frame(0)` identically.
  - All rendered WebPs stay strictly under Tidbyt's 128 KB limit (`150` frames @ `100 ms` = `15,000 ms`, `loop=0`).
- **Modular Sprite Pipeline:** Easily swap in hand-drawn Aseprite or PNG frames later via `assets/custom/`.

---

## Repository Structure

```text
capybara-clock/
├── capybara_clock.star            # Self-contained Pixlet Starlark applet (28 embedded GIFs)
├── scripts/
│   ├── generate_sprites.py        # High-res Pillow sprite generator, custom art importer & .star injector
│   └── verify_app.py              # Starlark syntax/API validator & seamless loop verifier (all 28 states)
├── assets/
│   ├── <state>.{gif,webp}         # 28 states: 64x32, 150 frames @ 100ms, loop=0
│   ├── custom/                    # Drop hand-drawn Aseprite GIFs / PNGs here
│   └── previews/                  # Upscaled contact sheets & showcase strips
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

Use the **Debug Weather Override**, **Debug Time of Day**, and **Debug Temperature Tier** dropdowns in the browser UI to instantly preview all 28 scenes.

### 3. CLI Rendering (`pixlet render`)

Render a 15-second animated WebP directly from the command line:

```bash
# Default (Brooklyn, NY, live weather)
pixlet render capybara_clock.star -o preview.webp

# Override location, units, 24h clock, and force a specific weather / time / temp state
pixlet render capybara_clock.star \
  latitude=40.6782 \
  longitude=-73.9442 \
  timezone=America/New_York \
  use_24h=false \
  temp_unit=F \
  debug_weather=clear \
  debug_time_of_day=day \
  debug_temp=cold \
  -o preview_cocoa.webp

# Or use a Zip Code instead of lat/lon
pixlet render capybara_clock.star zip_code=11215 debug_weather=snow debug_time_of_day=night -o preview_snow_night.webp
```

### 4. Push Manually to Your Tidbyt

```bash
pixlet push \
  --api-token "$TIDBYT_API_KEY" \
  --installation-id "capybaraclock" \
  "$TIDBYT_DEVICE_ID" \
  preview.webp
```

---

## Regenerating or Swapping Custom Sprites (Aseprite / PNG)

Requires Python 3.9+ and `Pillow` (`pip install pillow`):

```bash
# Regenerate all 28 weather states, update preview contact sheet, and inject base64 into capybara_clock.star
python3 scripts/generate_sprites.py --preview

# Run Starlark static verification & seamless loop tests
python3 scripts/verify_app.py
```

### Swapping in Hand-Drawn Art

To replace any state (e.g., `clear_day_warm`, `clear_day_cold`, `snow_night`, `thunderstorm_night`, etc.) with your own Aseprite or PNG art:

1. Export a 64×32 animation into `assets/custom/` using any of these formats:
   - `assets/custom/<state>.gif` (animated GIF from Aseprite)
   - `assets/custom/<state>_sheet.png` (horizontal strip of 64×32 tiles)
   - `assets/custom/<state>/frame_000.png ...` (sorted folder of 64×32 PNG frames)
2. Tip: choose a frame count that evenly divides `150` (e.g., `10`, `15`, `25`, `30`, `50`, `75`, or `150` frames at 100 ms/frame) for an exact 15-second loop.
3. Run `python3 scripts/generate_sprites.py --preview` — the script automatically imports your custom art, normalizes it to 150 frames @ 100 ms, and updates `capybara_clock.star`.

---

## Automated Deployment

### Option 1: Local Mac 1-Minute Background Updater (`launchd` — Exact Clock)

For a clock that stays exact to the minute (firing at `:02` past every minute via macOS `launchd`), run the interactive installer once:

```bash
./scripts/setup_mac_updater.sh
```

- Stores your `TIDBYT_DEVICE_ID` and `TIDBYT_API_KEY` locally in `~/.config/capybara-clock/env` (`chmod 600`, outside Git).
- Installs `~/Library/LaunchAgents/com.capybaraclock.updater.plist` and immediately pushes to your Tidbyt.
- Check status/logs: `./scripts/setup_mac_updater.sh --status`
- Push immediately: `./scripts/setup_mac_updater.sh --run-now`
- Stop & uninstall: `./scripts/setup_mac_updater.sh --uninstall`

### Option 2: 24/7 Free Cloud Clock (Public GitHub Repo + `cron-job.org`)

Because GitHub's built-in `schedule:` cron is heavily delayed, you can trigger `.github/workflows/push.yml` every **1 minute** for free via [cron-job.org](https://cron-job.org) (requires the repository to be **public** for unlimited free GitHub Actions minutes; your Tidbyt secrets remain encrypted in GitHub Secrets):

1. Create a **Fine-Grained Personal Access Token** on GitHub (**Settings → Developer settings → Personal access tokens → Fine-grained tokens**):
   - **Repository access:** Only select repositories → `kevinyieh/lubyt`
   - **Repository permissions:** `Actions` → **Read and write** (nothing else!)
2. On [cron-job.org](https://cron-job.org), create a new Cronjob:
   - **URL:** `https://api.github.com/repos/kevinyieh/lubyt/actions/workflows/push.yml/dispatches`
   - **Execution schedule:** Every `1` minute
   - **Advanced → Request method:** `POST`
   - **Advanced → Request body:** `{"ref":"main"}`
   - **Advanced → Headers:**
     - `Authorization`: `Bearer <YOUR_FINE_GRAINED_TOKEN>`
     - `Accept`: `application/vnd.github+json`
     - `X-GitHub-Api-Version`: `2022-11-28`
     - `User-Agent`: `capybara-clock-cron`

The workflow uses sparse checkout (`capybara_clock.star` only) + a cached `pixlet` binary so each 1-minute push completes in ~6–10 seconds.

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
