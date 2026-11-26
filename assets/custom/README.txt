Custom Sprite Override Directory (Aseprite / PNG)
=================================================

Drop hand-drawn 32x32 pixel-art assets here to replace any procedurally
generated weather state while keeping the 15-second (150 frames @ 100ms)
seamless loop pipeline intact.

Supported layouts (per weather state: sunny, rainy, snowy, windy, thunderstorm, default):

1. Animated GIF exported from Aseprite:
     assets/custom/sunny.gif

2. Horizontal 32x32 sprite sheet (strip):
     assets/custom/sunny_sheet.png

3. Sorted directory of individual 32x32 PNG frames:
     assets/custom/sunny/frame_000.png
     assets/custom/sunny/frame_001.png
     ...

Tip for exact seamless looping:
  Export a frame count that evenly divides 150 (e.g., 10, 15, 25, 30, 50, 75, or 150
  frames at 100ms/frame). The generator will automatically tile your loop to 150 frames
  (15.0 seconds) and re-inject the base64 GIFs into capybara_clock.star when you run:

     python3 scripts/generate_sprites.py --preview
