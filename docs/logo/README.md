# likingInitiative logo

Hex sticker for the project and the `likingInitiative` R / Python packages:
a cartoon orange over a dislike-to-like slider, on the app palette
(cream `#fdf3e0`, orange `#E78A00`, navy `#0b3c74`).

## Files

| File | Use |
|---|---|
| `likingInitiative-hex.svg` | Master. Hexagon only, transparent background, text outlined (no font needed). |
| `likingInitiative-hex-{1200,600,240}.png` | Hexagon renders for READMEs, slides, pkgdown. The R package repository (`liking-initiative/likingInitiative-r`) would carry the 240 px copy as `man/figures/logo.png`. |
| `likingInitiative-avatar.svg` | Square-framed version for profile pictures (hex fits inside a circular crop). |
| `likingInitiative-avatar-{1024,500}.png` | GitHub organization / profile avatar. Upload the 1024 one; GitHub asks for at least 500 × 500 and under 1 MB. |

## Regenerating

The text is converted to paths with `build_logo.py`, which needs
`fonttools` and `Nunito-ExtraBold.ttf` (Google Fonts, OFL) next to it:

```bash
python build_logo.py                       # writes the two SVGs
rsvg-convert -w 1200 -b none likingInitiative-hex.svg    -o likingInitiative-hex-1200.png
rsvg-convert -w 1024 -h 1024 -b none likingInitiative-avatar.svg -o likingInitiative-avatar-1024.png
```

The editable design canvas (with the earlier explorations) lives at
https://claude.ai/code/artifact/fe18f8f4-a0eb-4809-9c99-0b065aba0005.
