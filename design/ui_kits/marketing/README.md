# opencode — marketing site UI kit

A click-through recreation of the three audited marketing surfaces: `/` (home), `/zen`, and `/enterprise`. The nav switches between them; the install snippet, FAQ, and contact form all respond to clicks.

## Files

| File | Role |
|---|---|
| `index.html` | Loads React + Babel, mounts the kit, hosts page-switching state. |
| `Atoms.jsx` | `Button`, `Hairline`, `SectionLabel`, `BracketBullet`, `TextField`, `TextArea`, `Wordmark`. |
| `PrimaryNav.jsx` | Top nav with ASCII wordmark + link cluster + Download CTA. |
| `HeroTUI.jsx` | The single dark surface — ASCII wordmark + prompt row + keybinding hints. |
| `InstallBlock.jsx` | Install-method tab strip + copy-able snippet. |
| `FeatureList.jsx` | `[+]` / `[-]` / `[x]` bracket-bullet feature rows. |
| `FAQList.jsx` | `+` / `−` toggle FAQ. |
| `ChartTile.jsx` | Sparse-line / dotted SVG plot for the home stat block. |
| `TestimonialRow.jsx` | `/zen` peer-quote row. |
| `Footer.jsx` | 5-up link grid + copyright. |
| `Pages.jsx` | `HomePage`, `ZenPage`, `EnterprisePage` compositions. |

## How to use

Open `index.html`. The kit assumes `colors_and_type.css` lives at the project root (two levels up).

Every component reads tokens via CSS custom properties — there is no JS theme object. To restyle, edit `colors_and_type.css`.

## Known gaps

- No mobile drawer for the nav (only collapsing rules in CSS). The audit did not document the exact mobile pattern.
- `/go` page not included — not in the audited surfaces.
- Form validation states (error / success per-field) not implemented; the submit path swaps the whole form for a confirmation block.
