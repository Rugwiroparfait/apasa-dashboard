# APASA UI

Tailwind CSS v4 is compiled into `evidence/static/evidence/ui.css`. The actual
shadcn/ui **New York** Button, Card, Dialog and Popover components live in `components/ui`
(MIT license included). The neutral shadcn theme is customized with APASA's existing
forest-green primary, gold focus/caution and light-neutral background tokens.

The authenticated assistant is a small React island using those components.
Its floating launcher is fixed at the bottom-left. Radix handles popover placement,
Escape, focus return and outside-click dismissal. The existing Django-rendered
conversation/form is moved into the popover so signed evidence, CSRF, user history,
provider and quota handling remain unchanged. Opening the popover never calls AI.

Django buttons, cards and native inputs use the same component recipes through
Tailwind `@apply` in `styles.css`; the app does not require React for ordinary pages
or forms. Bespoke CSS is retained for the original hero artwork and evidence SVGs.

Build after changing templates, utility classes or frontend components:

```sh
npm ci
npm run build
```

Commit the lockfile and generated `ui.css`/`ui.js` with source changes. Python-only
Docker/Render deployments already copy these local static assets and need no Node
runtime or CDN. `components.json` records the shadcn configuration.

Component source: https://ui.shadcn.com/r/styles/new-york-v4/{button,card,popover}.json

The original hero can be re-encoded using `python scripts/optimize-hero.py` in a
Python environment with Pillow. This changes encoding/size only, not composition.

Landing motion is implemented in `accounts/static/accounts/landing.js`: a passive
scroll listener schedules one animation frame for tractor travel, while an
IntersectionObserver reveals sections/cards once with an 80ms stagger. Card
appearance and hover/focus motion use compiled Tailwind styles. Content remains
visible without JavaScript; reduced-motion preferences show all content immediately
and disable travel. Scenery controls are intentionally omitted; the tractor still
responds to scrolling and system reduced-motion preferences.

Evidence charts use the same shadcn Dialog. Django serializes the existing chart
facts with `json_script`; the client uses each server-computed bar percentage and
original unit/scale without recalculating values. Desktop dialogs show up to 15
rows; compact viewports page through rows on that same scale. Exact values and
sources occupy a separate scrollable view; the graph pane itself does not scroll.
Native charts/tables remain available when JavaScript is unavailable. District
filters are one GET toolbar; province/district changes clear their dependent
selections before submitting to the existing route.
