# LuckyRoll

High-contrast **256×256 DXT3 Arabic Corsair roll numbers** (`512×256` `BUST!`) paired with **33 distinctive, MODULATE2X-calibrated `256×512` Tarot Cards** built cleanly on retail Final Fantasy XI DATs for **Windower XIPivot**.

No more squinting at spinning Roman numerals or guessing whether a flash in Sortie was a `IV`, `V`, `VI`, `IX`, or `XI`.

![LuckyRoll in-game Samurai Roll spinning card ring](assets/ingame_samurai_ring.jpg)

<table>
  <tr>
    <td align="center">
      <img src="assets/ingame_lucky_2.jpg" alt="Samurai Roll Lucky 2 with Gold Star" width="420"/><br/>
      <sub><b>Lucky <code>2 ★</code></b> — Vivid emerald numeral + gold star badge</sub>
    </td>
    <td align="center">
      <img src="assets/ingame_unlucky_9.jpg" alt="Chaos or Fighter Unlucky 9" width="420"/><br/>
      <sub><b>Unlucky <code>9</code></b> — Bold crimson numeral with thick black outline</sub>
    </td>
  </tr>
</table>

---

## Features

- **Ultra-Readable Arabic Numerals (`256×256` DXT3 + `512×256` `BUST!`)**: Heavy sans-serif glyphs (`1`–`11` & `BUST!`) with outward Euclidean distance-transform pitch-black outlines and drop shadows so numbers pop cleanly against both dark Sortie arenas and bright snow zones.
- **Per-Roll Lucky / Unlucky Color Coding & Badges**:
  - **White**: Standard roll (`1`–`10`)
  - **Emerald Green + Gold Star (`★`)**: Roll-specific **Lucky** number (`2`, `3`, `4`, or `5`)
  - **Crimson Red (`×`)**: Roll-specific **Unlucky** number (`6`, `7`, `8`, `9`, or `10`)
  - **Radiant Gold + Royal Crown**: **11** (Jackpot), Wild Card `6`, and Cutting Cards `6`
  - **Gold-White + Star**: **Snake Eye** (`1`)
  - **Crimson `BUST!` Banner**: Wide `512×256` Bust indicator
- **33 Distinct Per-Roll Tarot Cards (`256×512` DXT3)**:
  - **Front (`d0`)**: Per-roll metallic border (`gold`, `silver`, `steel`, `copper`, `crimson`), top roll name banner (`SAMURAI`, `CHAOS`, `FIGHTER`, `BOLTER`, etc.), dark velvet center window behind the floating number, and a **Lucky / Unlucky cheat-sheet footer** (`★ Lucky | × Unlucky`).
  - **Back (`c0`)**: Five distinct tarot patterns & medallions (Sunburst Circle, Chevrons Shield, Arcane Rings Octagon, Stripes Hexagon, Lattice Diamond), job/roll crest (`WAR`, `SAM`, `DRK`, `SPD`, etc.), name ribbon, and **stat tag pill** (`DOUBLE ATK`, `STORE TP`, `ATTACK`, `MOVE SPD`, etc.).
- **Outward-Facing Spinning Ring (`wc`) + Forward Winning Card (`c1`–`c6`)**: The 6-card orbiting ring (`wc`) is re-oriented outward with corrected normals, un-mirrored full-card UVs, and aspect compensation so roll names, numbers (`1`–`6`), and Lucky/Unlucky cheat sheets face the camera while spinning, while the winning popped card (`c1`–`c6`) continues facing forward.
- **Full Texture Namespace Isolation (`cor_r01_`–`cor_r31_`)**: Retail Phantom Roll DATs all share colliding `cor_cd01*` internal texture names in FFXI's global texture cache. LuckyRoll isolates every Phantom Roll with unique internal prefixes so Busts, rapid rolls, or nearby Corsairs / Qultada never bleed cached textures across rolls.
- **All 44 Corsair Ability DATs Included**:
  - **31 Phantom Rolls** (`ROM/162`–`ROM/321`)
  - **6 Wild Card DATs** (`ROM/165/17.DAT`–`22.DAT`) — `1–4` White, `5 ★` Lucky, `6` Gold Crown (`WC` / `SP RESET`)
  - **6 Cutting Cards DATs** (`ROM/306/122.DAT`–`127.DAT`) — `1–4` White, `5 ★` Lucky, `6` Gold Crown (`CC` / `SP RECAST`)
  - **1 Snake Eye DAT** (`ROM/184/80.DAT`) — Gold-White `1 ★`

---

## Previews

### Custom Tarot Cards (Front & Back)
![LuckyRoll Tarot Card Fronts and Backs](assets/preview_cards.png)

### Post-DXT3 Numerals & Badges
![LuckyRoll Numerals Preview](assets/preview_numbers.png)

---

## Installation (Windower 4 + XIPivot)

1. Download this repository (or clone it / grab the release zip) and place the `LuckyRoll` folder inside your Windower XIPivot `DATs` directory:
   ```text
   Windower4/addons/XIPivot/data/DATs/LuckyRoll/
   ```
   Confirm the ROM directory sits directly underneath:
   ```text
   Windower4/addons/XIPivot/data/DATs/LuckyRoll/ROM/162/...
   ```
2. Add `LuckyRoll` **first** in `<overlays>` in `Windower4/addons/XIPivot/data/settings.xml` (ahead of global HD packs such as `NextHD` so LuckyRoll overrides their roll DATs cleanly):
   ```xml
   <overlays>LuckyRoll,NextHD,...</overlays>
   ```
3. In-game, reload XIPivot (`//lua reload xipivot`) and zone or relog to clear any previously cached effect DATs.

---

## Included DAT Reference (44 DATs)

<details>
<summary>Expand full table of all 31 Phantom Rolls + Wild Card, Cutting Cards & Snake Eye</summary>

| # | Roll / Ability | Lucky | Unlucky | Crest | Stat Tag | DAT Path |
|---:|---|---:|---:|---|---|---|
| 1 | Fighter's Roll | 5 | 9 | `WAR` | `DOUBLE ATK` | `ROM/163/90.DAT` |
| 2 | Monk's Roll | 3 | 7 | `MNK` | `SUBTLE BLOW` | `ROM/162/50.DAT` |
| 3 | Healer's Roll | 3 | 7 | `WHM` | `CURE POT` | `ROM/164/45.DAT` |
| 4 | Wizard's Roll | 5 | 9 | `BLM` | `MAGIC ATK` | `ROM/164/46.DAT` |
| 5 | Warlock's Roll | 4 | 8 | `RDM` | `MAGIC ACC` | `ROM/164/47.DAT` |
| 6 | Rogue's Roll | 5 | 9 | `THF` | `CRIT RATE` | `ROM/164/48.DAT` |
| 7 | Gallant's Roll | 3 | 7 | `PLD` | `DEFENSE` | `ROM/164/49.DAT` |
| 8 | Chaos Roll | 4 | 8 | `DRK` | `ATTACK` | `ROM/164/50.DAT` |
| 9 | Beast Roll | 4 | 8 | `BST` | `PET ATK` | `ROM/164/51.DAT` |
| 10 | Choral Roll | 2 | 6 | `BRD` | `SPELL INT` | `ROM/164/52.DAT` |
| 11 | Hunter's Roll | 4 | 8 | `RNG` | `ACCURACY` | `ROM/164/53.DAT` |
| 12 | Samurai Roll | 2 | 6 | `SAM` | `STORE TP` | `ROM/164/54.DAT` |
| 13 | Ninja Roll | 4 | 8 | `NIN` | `EVASION` | `ROM/164/55.DAT` |
| 14 | Drachen Roll | 4 | 8 | `DRG` | `PET ACC` | `ROM/164/56.DAT` |
| 15 | Evoker's Roll | 5 | 9 | `SMN` | `REFRESH` | `ROM/164/57.DAT` |
| 16 | Magus's Roll | 2 | 6 | `BLU` | `MAGIC DEF` | `ROM/164/58.DAT` |
| 17 | Corsair's Roll | 5 | 9 | `COR` | `EXP / CP` | `ROM/164/59.DAT` |
| 18 | Puppet Roll | 3 | 7 | `PUP` | `PET MACC` | `ROM/164/60.DAT` |
| 19 | Dancer's Roll | 3 | 7 | `DNC` | `REGEN` | `ROM/164/61.DAT` |
| 20 | Scholar's Roll | 2 | 6 | `SCH` | `CONS MP` | `ROM/198/107.DAT` |
| 21 | Bolter's Roll | 3 | 9 | `SPD` | `MOVE SPD` | `ROM/246/101.DAT` |
| 22 | Caster's Roll | 2 | 7 | `FC` | `FAST CAST` | `ROM/246/102.DAT` |
| 23 | Courser's Roll | 3 | 9 | `SNP` | `SNAPSHOT` | `ROM/256/87.DAT` |
| 24 | Blitzer's Roll | 4 | 9 | `HST` | `HASTE` | `ROM/256/88.DAT` |
| 25 | Tactician's Roll | 5 | 8 | `TP` | `REGAIN` | `ROM/261/40.DAT` |
| 26 | Allies' Roll | 3 | 10 | `SC` | `SC DMG` | `ROM/262/28.DAT` |
| 27 | Miser's Roll | 5 | 7 | `STP` | `SAVE TP` | `ROM/265/25.DAT` |
| 28 | Companion's Roll | 2 | 10 | `PET` | `PET REGEN` | `ROM/265/32.DAT` |
| 29 | Avenger's Roll | 4 | 8 | `CTR` | `COUNTER` | `ROM/265/33.DAT` |
| 30 | Naturalist's Roll | 3 | 7 | `GEO` | `ENH DUR` | `ROM/321/72.DAT` |
| 31 | Runeist's Roll | 4 | 8 | `RUN` | `MAGIC EVA` | `ROM/321/73.DAT` |
| 32–37 | Wild Card (6 DATs) | 5 | 6 (`MAX`) | `WC` | `SP RESET` | `ROM/165/17.DAT` – `22.DAT` |
| 38–43 | Cutting Cards (6 DATs) | 5 | 6 (`MAX`) | `CC` | `SP RECAST` | `ROM/306/122.DAT` – `127.DAT` |
| 44 | Snake Eye | 1 (`★`) | — | — | — | `ROM/184/80.DAT` |

</details>

---

## Optional: Customizing & Rebuilding from Retail DATs

You do **not** need Python or this script to use LuckyRoll — the ready-to-drop `LuckyRoll/` folder works out of the box.

The generator at [`tools/build_luckyroll.py`](tools/build_luckyroll.py) is included for players and modders who want to:
- Customize number or card colors (for example, **colorblind-friendly palettes**) by editing `PALETTES` / `CARD_THEMES`.
- Swap typography via `--font <path-to-ttf>`.
- Regenerate clean DATs against a retail FFXI install or future FFXI client patch.
- Audit every patched section, DXT3 texture, card mesh, and texture namespace (`--verify`).

**Requirements**: Python 3.9+, `pillow`, `numpy`, and a clean retail FFXI installation containing `ROM/`.

```powershell
# Rebuild all 44 DATs and regenerate preview sheets
python tools/build_luckyroll.py

# Verify an existing LuckyRoll build against retail DATs
python tools/build_luckyroll.py --verify

# Custom FFXI path + export a clean XIPivot zip
python tools/build_luckyroll.py --ffxi-root "D:\Games\FINAL FANTASY XI" --zip LuckyRoll_XIPivot.zip
```

---

## Known Retail FFXI Behavior

- **Bust (`12+`) Card Quirk**: Square Enix's server hardcodes animation ID `98` (`ROM/163/90.DAT`, Fighter's Roll) whenever *any* Phantom Roll Busts (`12+`), so you will briefly see the `FIGHTER` card right before the `BUST!` popup regardless of which roll was active. Because LuckyRoll isolates every roll's internal texture namespace (`cor_r01_`–`cor_r31_`), that Fighter's Bust animation will never corrupt your actual active roll textures afterward.
