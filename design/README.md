# OpenCode Design System

> "The marketing page is a man page."

OpenCode is an open-source, terminal-native AI coding agent. The marketing site (`opencode.ai`) and the in-product TUI share a single typographic identity: **every word on every surface sits in Berkeley Mono.** No sans-serif, no display face, no italics, no decorative ornament. The page reads like a `whatis` listing rendered at modern resolution.

The system's strength is restraint. There is exactly one font, one weight family, two corner radii (4 px and 0 px), two surface tones (cream and near-black), and a single iconography vocabulary: ASCII bracket markers — `[+]`, `[-]`, `[x]`, `+`, `−`. The Apple HIG semantic ramp ships with the system but is **reserved for the in-product TUI**; marketing chrome stays strictly monochrome.

The company is **Anomaly**; the product is **opencode**. Surfaces audited: `/` (home), `/zen`, `/enterprise`.

---

## Sources

This system was built from a written design audit (no codebase or Figma was attached). Where the audit was specific about hex values, sizes, and component anatomy, those are reproduced verbatim. Where it left gaps (hover states, validation styling, in-product TUI beyond the hero mockup, `/go` page), the corresponding sections here are stubs.

If you have the original `opencode` repo or Figma, please attach it via the **Import** menu and we'll lift the real assets (font files, ASCII wordmark glyph data, install snippet markup) instead of approximating them.

---

## Index

| File / Folder | Purpose |
|---|---|
| `README.md` | This file — brand context, content & visual fundamentals, iconography. |
| `SKILL.md` | Cross-compatible skill manifest so this system can be invoked from Claude Code. |
| `colors_and_type.css` | All design tokens as CSS custom properties + semantic element styles. |
| `fonts/` | Webfont files. Currently JetBrains Mono (Berkeley Mono substitute — see below). |
| `assets/` | Logos, ASCII wordmark text, any raster assets. |
| `preview/` | Small HTML cards that populate the Design System tab. |
| `ui_kits/marketing/` | High-fidelity recreation of the `opencode.ai` marketing site. |

---

## Brand at a glance

- **Name:** opencode (lowercase) — the product. Anomaly is the legal entity behind it.
- **Tagline:** "The open source AI coding agent."
- **Surface:** terminal-first. The hero of the marketing page is a TUI screenshot, not a product shot of a GUI.
- **Tone:** dry, technical, generous with whitespace. Reads like documentation that happens to be marketing.

---

## Content fundamentals

**Voice.** Plainspoken, technical, declarative. No exclamation points, no marketing superlatives ("revolutionary," "game-changing"), no second-person sales copy ("you'll love how…"). The hero headline is a single noun phrase: *The open source AI coding agent.* Feature rows are even drier — verb-first labels followed by a one-line definition.

**Examples (drawn from the audited surfaces):**

| Surface | Copy | What's happening |
|---|---|---|
| Hero | `The open source AI coding agent` | Declarative, lowercase product name, no embellishment. |
| Install | `curl -fsSL https://opencode.ai/install \| bash` | Literal shell command as primary CTA. |
| Feature row | `[+] LSP enabled    Automatically loads the right LSPs for the IDE` | ASCII bracket bullet, bold label, single-line definition. |
| FAQ row | `+ How is opencode different from other agents?` | Plain text question, leading `+` glyph for collapsed state. |
| Footer | `©2026 Anomaly` | Year and entity, nothing else. |

**Casing.** Product name is *always* lowercase: `opencode`, never `OpenCode` or `OPENCODE` outside the ASCII block-pixel wordmark. Section labels use sentence case ("What is opencode?", "Built for privacy first"). Buttons use sentence case ("Get started with Zen", "Read docs →").

**Pronoun stance.** Neither "I" nor an aggressive "you." Copy describes the product in third person or imperative ("Build", "Send", "Read docs"). The brand is talking *about* the tool, not *at* the reader.

**Emoji.** None. Anywhere. ASCII bracket markers do every job emoji might otherwise do.

**Vibe.** A printed code listing. A man page. A README that someone took the time to typeset.

---

## Visual foundations

**Palette.**
The chrome palette is two tones: warm cream `#fdfcfc` (canvas) and warm near-black `#201d1d` (ink). A four-tier neutral gray ladder (`charcoal → body → mute → stone → ash`) covers everything between. The full Apple HIG accent ramp ships with the system (`#007aff` blue, `#ff3b30` red, `#ff9f0a` orange, `#30d158` green plus pressed depths) **but only the in-product TUI mockup ever uses them.** Marketing surfaces are monochrome.

**Typography.**
Berkeley Mono at every size, every weight (400 / 500 / 700), every role. Hierarchy is built from size + weight on a single face. No italic alternative is documented; the system does not use italics. Line-height is 1.5 across body and headlines; buttons get a deliberately tall 2.0 so labels feel calm inside the 4 px radius rectangle.

**Spacing.**
8 px base with 1/2/4 px finer steps. The dominant cue is `--spacing-section` = **96 px** between major content blocks — sections are 96 px apart on desktop, 64 px on tablet, 48 px on mobile. Inside a section, content rows sit at 16 px vertical with no horizontal padding; bullets are ASCII bracket prefixes, not indents.

**Backgrounds.**
Flat cream. Period. No gradients, no atmospheric blurs, no textures, no repeating patterns, no full-bleed photography. The single exception is the hero TUI mockup — one full-bleed dark `#201d1d` rectangle per landing page — which functions as the visual anchor of the whole site.

**Animation & easing.**
Not documented in the source audit, and the surfaces do not appear to lean on motion. Treat animation as a quiet "if used, instant or short crossfade" — never bounces, never spring physics. Stay closer to a static page than a SaaS hero.

**Hover states.**
Explicitly **not documented** per system policy. Each component spec covers Default and Active/Pressed only. If you must introduce a hover, mirror Active at lower magnitude (e.g. CTA goes from `#201d1d` → `#0f0000` on press; a hover might land halfway). Do not introduce opacity dims or scale wobbles.

**Press states.**
Primary CTA: background darkens to `#0f0000` (ink-deep). No scale change, no shadow change.

**Borders.**
1 px hairline `rgba(15,0,0,0.12)` is the *only* divider in the system — warm-tinted to match the cream's undertone. A `hairline-strong` `#646262` exists for the install-method tab strip and stronger inline rules. Everything else is borderless.

**Shadows.**
**None.** There are no drop shadows anywhere. Nothing lifts, nothing floats. The only "elevation" is the dark TUI surface, and that elevates via *color*, not light.

**Transparency / blur.**
None documented. The hairline color is the only translucent value in the system (`rgba(15,0,0,0.12)`).

**Corner radii.**
Two values:
- `--rounded-none` = **0 px** — every container (sections, hero TUI, primary nav, footer, list rows).
- `--rounded-sm` = **4 px** — every interactive element (primary CTA, secondary CTA, text inputs, install snippet, badges, prompt rows).
- `--rounded-full` = 9999 px — *only* the testimonial avatar circles.

**Cards.**
Cards are borderless. A "card" in this system is just a `padding`-bearing text block on cream, optionally separated from its neighbor by a 1 px hairline rule. No raised surfaces, no rounded corners, no shadow.

**Imagery color vibe.**
N/A. There is no photography, no illustration, no raster art beyond the favicon and OG share image. Every visual element is type or inline SVG (and SVG is used sparingly, only for the abstract sparse-line charts inside the home page's stat block).

**Layout rules.**
Single 960 px reading column for body; the hero TUI mockup widens to ~1100 px. `/enterprise` is the only two-column layout (≈360 px text + ≈480 px form). Footer is a 5-up link grid that collapses to 2-up at tablet, 1-up at mobile.

---

## Iconography

The brand's iconography is **ASCII bracket markers, rendered as text inside Berkeley Mono.** There is no icon font, no SVG sprite, no Lucide/Heroicons CDN dependency. The icon set is exactly:

| Glyph | Role |
|---|---|
| `[+]` | Feature added / capability enabled bullet |
| `[-]` | Feature removed / not-applicable bullet |
| `[x]` | Selected / completed marker |
| `+` | Collapsed FAQ row leading glyph |
| `−` | Expanded FAQ row leading glyph |
| `→` | Inline link affordance (`Read docs →`) |
| `▼` | Footer language dropdown |
| `\|` | TUI prompt row leading vertical pipe |

All of these are normal Unicode characters set in Berkeley Mono. They are part of the text content, not separate icon elements. **Do not** replace them with SVG icons; the brackets *are* the icons.

**In-product TUI** uses additional monospaced glyphs for keybinding hints — `tab`, `ctrl-p`, `kbd`, `A+`, `⊕`, `↻`, `K`, `Z` — again as plain text characters in Berkeley Mono.

**The wordmark.** The opencode wordmark is itself ASCII — a 5-row block-pixel rendering of `OPENCODE` composed entirely of `█` (U+2588) and surrounding monospaced cells. It appears in the primary nav and as the centerpiece of the hero TUI mockup. The wordmark is *never* rendered as a vector logo. See `assets/wordmark.txt`.

**Emoji.** Not used.

**No third-party icon CDN is referenced** because the system genuinely has no SVG icons. If a future component truly cannot be expressed in bracket glyphs, prefer adding another Unicode character before reaching for a CDN.

---

## Substitutions flagged

- **Berkeley Mono** is a paid commercial font. We ship **JetBrains Mono** (weights 400 / 500 / 700) as the closest open-source substitute, loaded from Google Fonts via `colors_and_type.css`. The system's documented fallback stack (`IBM Plex Mono → ui-monospace → SFMono-Regular → Menlo → Monaco → Consolas → Liberation Mono → Courier New`) is preserved verbatim after JetBrains Mono. **If you can provide Berkeley Mono `.woff2` files, drop them in `fonts/` and update `colors_and_type.css`.**
- The audit notes that mobile screenshots were not captured; responsive collapsing here follows the audit's synthesis (hamburger drawer at 768 px, single-column at 640 px). Recheck against the live site before shipping.

---

## Caveats & known gaps

- **Hover states** — not documented by system policy.
- **Form validation** — success/error inline styling not present in the audited surfaces.
- **Full in-product TUI** — only the hero mockup is documented; the actual `opencode` terminal interface (panels, status bar, full keybinding map) is not in scope.
- **`/go` page** — Go SDK marketing page not extracted; likely shares chrome plus code-sample blocks.
