---
name: opencode-design
description: Use this skill to generate well-branded interfaces and assets for opencode (by Anomaly), either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping.
user-invocable: true
---

Read the `README.md` file within this skill, and explore the other available files.

If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. If working on production code, you can copy assets and read the rules here to become an expert in designing with this brand.

If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.

## Quick rules

- **One font.** Every text role uses the mono stack defined in `colors_and_type.css` (Berkeley Mono → JetBrains Mono fallback). No sans-serif, no display face, no italics.
- **Two surfaces.** Cream `#fdfcfc` is the only body background. The dark surface `#201d1d` exists for **one** TUI mockup per landing page — never for body content.
- **One iconography.** ASCII bracket markers: `[+]`, `[-]`, `[x]`, `+`, `−`, `→`, `▼`, `|`. No SVG icons. No emoji.
- **Two radii.** `0px` for every container; `4px` for every interactive element; `9999px` only for testimonial avatars.
- **No shadows. No gradients. No textures.** Elevation comes from color (the dark TUI surface), not from light.
- **Section rhythm:** 96 px between major content blocks. The only divider is a 1 px hairline `rgba(15,0,0,0.12)`.
- **Apple HIG accent ramp** (`#007aff`, `#ff3b30`, `#ff9f0a`, `#30d158` + pressed depths) is shipped in tokens but **reserved for the in-product TUI**. Marketing chrome stays monochrome.
- **Product name** is always lowercase: `opencode`. The block-pixel ASCII wordmark renders the letters uppercase by stylization, never by spelling.

## Files in this skill

| Path | Purpose |
|---|---|
| `README.md` | Brand context, content & visual fundamentals, iconography. |
| `colors_and_type.css` | All tokens + semantic element styles as CSS custom properties. |
| `fonts/` | Webfont substitute (JetBrains Mono via Google Fonts import). |
| `assets/wordmark.txt` | Block-pixel ASCII wordmark — copy as plain text into a `<pre>`. |
| `preview/` | Small per-token preview cards. |
| `ui_kits/marketing/` | High-fidelity React recreation of the marketing site (home / zen / enterprise). |
