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
