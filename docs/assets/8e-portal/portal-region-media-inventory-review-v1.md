# Region media inventory review v1

Status: `review-pending` · local research only · no adopted media

The desktop `RIFTCOACH` folder now contains 12 dynamic WebM candidates and 15
JPEG stills. This report proposes names for the next normalization step; it
does not prove source ownership or redistribution permission.

## Dynamic candidates

All full-length files except Harrowing are 1920×1080, 25fps and 15.04s VP8
WebM. Harrowing is a 1280×720, 5s variant. Bandle City is the only file with
an Opus audio stream; the browser preview must use the muted WebM and the
audio-free H.264 sibling.

| Proposed region key | Current file | Technical read | Recommendation |
| --- | --- | --- | --- |
| `bandle-city` | `animated-bandlecity.webm` | 1920×1080, 15.04s, VP8 + Opus | Keep; strip audio for fallback; candidate |
| `bilgewater` | `animated-bilgewater.webm` | 1920×1080, 15.04s, VP8 | Keep; candidate |
| `demacia` | `animated-demacia.webm` | 1920×1080, 15.04s, VP8 | Keep; candidate; native seam needs review |
| `freljord` | `animated-freljord.webm` | 1920×1080, 15.04s, VP8 | Keep; candidate |
| `shadow-isles` | `animated-harrowing.webm` | 1280×720, 5s, VP8 | Use only if the short/low-resolution trade-off is accepted; otherwise static-only |
| `ionia` | `animated-ionia.webm` | 1920×1080, 15.04s, VP8 | Keep; candidate |
| `mount-targon` | `animated-mount-targon.webm` | 1920×1080, 15.04s, VP8 | Keep; candidate |
| `noxus` | `animated-noxus.webm` | 1920×1080, 15.04s, VP8 | Keep; candidate |
| `piltover` | `animated-piltover.webm` | 1920×1080, 15.04s, VP8 | Keep; candidate |
| `shurima` | `animated-shurima.webm` | 1920×1080, 15.04s, VP8 | Keep; candidate |
| `void` | `animated-void.webm` | 1920×1080, 15.04s, VP8 | Keep; candidate |
| `zaun` | `animated-zaun.webm` | 1920×1080, 15.04s, VP8 | Keep; candidate |

No dynamic candidate for Ixtal was found, matching the user's inventory note.
The sampled motion figures for all files are in the local audit output under
`tmp/wallpaper-inspect/audit/dynamic-audit.json`; they are engineering signals,
not visual sign-off.

## Provisional static picks

The recommendation favors a clear focal subject, enough negative space for
Account UI, and the highest useful source resolution. Anonymous filenames are
kept in this table until the user approves the mapping.

| Region | Proposed static pick | Alternate / note |
| --- | --- | --- |
| Bandle City | **none yet** | `runeterra-bandlecity-03.jpg` is only 926×1080; imagegen restoration was rejected for crunchy AI texture. Prefer a true high-resolution source or a still extracted from the dynamic candidate after review. |
| Bilgewater | `ef261f0073747a41a230b54f96aa22de45e6b40d-1920x900.jpg` | User-confirmed Bilgewater candidate; broad horizontal composition, check Account crop before adoption. |
| Demacia | `5b80fe8ddd3d935c3f258f3e145b8aed4b7460bf-1920x887.jpg` | Bright hall/monument; `demacia.jpg` is a city alternate with lower width. |
| Freljord | `freljord.jpg` | 1577×1080 but visually coherent with the dynamic scene; search for a larger source later. |
| Ionia | `72ad1322d9a8b12047f23f9f7d344de6735e54fc-1920x1079.jpg` | White organic temple with colored flora; strong 16:9 fit. |
| Ixtal | **none in the current folder** | The user explicitly excluded Ixtal from the collected dynamic/static set; keep the region pending instead of borrowing another region's still. |
| Mount Targon | `mount-targon.jpg` | 1920×946 celestial spire; good focal silhouette. |
| Noxus | `6310fe5db818f80b84ee784a746cc28ee1273e6b-1920x1080.jpg` | City skyline with clear 16:9 framing; `fb300ca74eea40f058e348f4e376293f38b8b68d-1920x962.jpg` is an alternate interior/forge scene. |
| Piltover | `6c77423961def6e3a82d9a36545782f1a06386e0-4681x2114.jpg` | Highest-resolution still; visible “PILTOVER EXPLORATION” provenance mark must be checked before use. |
| Shurima | `shurima.jpg` | 1920×995 desert/temple scene; good match to dynamic palette. |
| Shadow Isles | `94e4bf2e1b30ba553b4fc0f93e94983837082210-2503x1080.jpg` | Primary: official Universe faction splash hash, strong misty-ruins silhouette. `ab3c2d4effe32c931570596363361436d64a2b19-1920x726.jpg` is the user-confirmed alternate. |
| The Void | `7107e5dbca7887931748e7ae0924e6eda17ef6f4-1920x1064.jpg` | Purple vortex; preserve as a restrained Account background, not a glowing overlay. |
| Zaun | `3b6df4047902ac8960f128d24b9f7c62051cb77f-1920x1057.jpg` | Green industrial city; strongest match to Zaun dynamic. |

`fb300...jpg`, `demacia.jpg` and `runeterra-bandlecity-03.jpg` remain as
alternates/rejected evidence rather than being deleted.

## File-by-file correction ledger

| Current file | Region assignment | Role |
| --- | --- | --- |
| `3b6df4047902ac8960f128d24b9f7c62051cb77f-1920x1057.jpg` | Zaun | primary candidate |
| `5b80fe8ddd3d935c3f258f3e145b8aed4b7460bf-1920x887.jpg` | Demacia | primary candidate |
| `6310fe5db818f80b84ee784a746cc28ee1273e6b-1920x1080.jpg` | Noxus | primary candidate |
| `6c77423961def6e3a82d9a36545782f1a06386e0-4681x2114.jpg` | Piltover | primary candidate |
| `7107e5dbca7887931748e7ae0924e6eda17ef6f4-1920x1064.jpg` | The Void | primary candidate |
| `72ad1322d9a8b12047f23f9f7d344de6735e54fc-1920x1079.jpg` | Ionia | primary candidate |
| `94e4bf2e1b30ba553b4fc0f93e94983837082210-2503x1080.jpg` | Shadow Isles | primary candidate |
| `ab3c2d4effe32c931570596363361436d64a2b19-1920x726.jpg` | Shadow Isles | alternate candidate (user-confirmed) |
| `ef261f0073747a41a230b54f96aa22de45e6b40d-1920x900.jpg` | Bilgewater | primary candidate (user-confirmed) |
| `fb300ca74eea40f058e348f4e376293f38b8b68d-1920x962.jpg` | Noxus | alternate candidate |
| `demacia.jpg` | Demacia | alternate candidate |
| `freljord.jpg` | Freljord | primary candidate |
| `mount-targon.jpg` | Mount Targon | primary candidate |
| `runeterra-bandlecity-03.jpg` | Bandle City | rejected for Account use until a higher-resolution source is found |
| `shurima.jpg` | Shurima | primary candidate |

## Next normalization step after approval

1. Keep the original files untouched and create a side-by-side manifest with
   `dynamic/<region>.webm`, `dynamic/<region>.mp4`, `dynamic/<region>.webp`
   and `account/<region>.jpg` names.
2. Verify every proposed static mapping at the actual Account crop and record
   source hash, dimensions, and rights status.
3. Convert dynamic files to audio-free H.264 fallbacks where needed; retain
   WebM for browsers that decode it.
4. Only after the user approves the mapping and every source/rights/format/
   mobile/reduced-motion/loop gate passes may any candidate enter the adopted
   media manifest. Until then `production_media = 0`.
