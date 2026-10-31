# APASA hero asset layers

This pack separates the visual parts of the APASA hero so the scene can be animated in the browser.

## Files

- landscape-rwanda.png — wide hero background with terraced hills and sunrise; contains no text or tractor.
- tractor-3d.png — transparent 3D tractor cutout with tillage implement and soft contact shadow.
- foreground-crops.png — transparent crop-and-soil strip for a near-camera parallax layer.
- tractor-dust.png — transparent dust plume for a subtle drift/fade animation.
- rwanda-flag.svg — separate Rwanda flag artwork with blue, yellow, and green bands and a golden sun.
- animations.css — gentle motion examples, including a reduced-motion fallback.

The APASA wordmark, headline, description, and sign-in CTA should be real HTML text and a real button, not baked into an image. That keeps them sharp, accessible, responsive, and easy to translate.

## Suggested layer order

1. Landscape background
2. Large APASA wordmark as low-opacity HTML text
3. Dust plume
4. Tractor
5. Foreground crops
6. Centered heading and CTA, positioned above the tractor where they remain readable

Put the tractor image and rwanda-flag.svg inside a positioned scene wrapper. The flag can sit over the tractor cab as its own image element and use the .hero-scene__flag animation class. Adjust its coordinates and size to match the rendered tractor at your target viewport.

Example class mapping for animations.css:

- Background image: hero-scene__background
- APASA background word: hero-scene__wordmark
- Tractor image: hero-scene__tractor
- Foreground crop strip: hero-scene__crops
- Dust image: hero-scene__dust
- Flag image/wrapper: hero-scene__flag

Use restrained motion to avoid distracting visitors. The CSS includes a prefers-reduced-motion fallback.

## Public landing delivery

The original layered hero is preserved: landscape, APASA wordmark, dust, tractor,
flag and foreground crops. All raster layers now have local WebP encodings.
The original PNGs remain untouched as source assets and are not requested.

| Layer | Responsive widths | Encoded bytes |
| --- | --- | --- |
| Landscape | 640 / 960 / 1440 | 53,282 / 105,280 / 193,644 |
| Tractor | 640 / 960 / 1440 | 64,644 / 126,502 / 243,660 |
| Crops | 640 / 960 / 1440 | 34,950 / 67,040 / 134,194 |
| Dust | 960 | 70,620 |

All derivatives use Lanczos resampling and preserve the original aspect ratio and
transparency. WebP quality is 80 (landscape/tractor), 78 (crops) and 65 (dust),
with method 6. Use the original PNGs to regenerate. Matching responsive preload
and image srcset prevent duplicate landscape requests. Decorative layers decode
asynchronously, and artwork never blocks the real HTML headline and sign-in action.
The original animation stylesheet and reduced-motion fallback remain; the on-screen
pause control has been removed.
All URLs use Django static storage; no r2.dev or font CDN is required.
