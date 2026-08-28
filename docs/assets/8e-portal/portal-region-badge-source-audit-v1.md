# Region badge source audit v1

Status: `reference-only` · not adopted

## Findings

The older official Legends of Runeterra support article includes image
attachments for detailed faction crests: Demacia, Freljord, Ionia, Noxus,
Piltover & Zaun, Shadow Isles, Bilgewater, Targon, Shurima and Bandle City.
The article itself is a reliable provenance reference, but the legacy
`article_attachments` URLs now redirect to the current Riot Support landing
page when fetched directly. They cannot currently serve as a stable runtime
asset source.

The currently used small card icons are the 13 transparent Riot Universe crest
PNGs. They are a separate, sharper and more predictable asset family. The
detailed 3D attachments should be used only as visual reference or as a
selected-region hero after a stable downloadable source, dimensions and usage
boundary are confirmed.

## Referenced official attachments

| Region | Legacy attachment filename | Current status |
| --- | --- | --- |
| Demacia | `Demacia_Crest.jpg` | reference URL redirects |
| Freljord | `Freljord_Crest.jpg` | reference URL redirects |
| Ionia | `Ionia_Crest.jpg` | reference URL redirects |
| Noxus | `Noxus_Crest.jpg` | reference URL redirects |
| Piltover & Zaun | `P_an_Z_Crest.jpg` | reference URL redirects |
| Shadow Isles | `Shadow_Crest.jpg` | reference URL redirects |
| Bilgewater | `Bilge_Crest.jpg` | reference URL redirects |
| Targon | `Targon_ver_53FINAL.png` | reference URL redirects |
| Shurima | `Board_RegionShurima_Icon_withoutbackground.png` | reference URL redirects |
| Bandle City | `Bandle_City_Player_Icon.png` | reference URL redirects |

The source article is [Riot's LoR region guide](https://support-legendsofruneterra.riotgames.com/hc/ja/articles/360035541954-%E3%83%AB%E3%83%BC%E3%83%B3%E3%83%86%E3%83%A9%E3%81%AE%E5%9C%B0%E5%9F%9F). The small Universe crest family is documented on the [Riot Universe regions page](https://universe.leagueoflegends.com/en_US/regions/) and the [Riot Developer Portal LoR asset guide](https://developer.riotgames.com/docs/lor).

## Decision

Do not replace the current crest selector with these legacy files. If the
user supplies higher-resolution copies, inspect each file, record its hash and
permission boundary, and consider the detailed emblem only for the
selected-region hero/transition—not as an unverified bulk replacement.

## Void gap candidate

The legacy support article has no usable Void detailed attachment. A generated
replacement was therefore explored from the existing official Universe Void
crest as a shape reference:

- `C:/Users/33502/Desktop/RIFTCOACH/badge-void-generated-v3-balanced.png`
- SHA-256: `ed928e5b28c1c0073f9160db2e29370885a760e505618e2d57652585d74f01ad`
- 1254×1254 RGBA; original, non-Riot asset; research-only

The balanced version keeps a deep obsidian/indigo body while retaining a
recognisable muted-violet Void accent. It is not yet used in the selector or
runtime; the user must first confirm that its texture and brightness match the
other supplied emblems.

The user later supplied a stronger Image2 web candidate:

- `C:/Users/33502/Desktop/RIFTCOACH/badge-void-image2-v1.png`
- SHA-256: `0b7eee4adb3983615fc74e28b55012cfd847995674a03558678f78a6d07cb559`
- 1254×1254 RGB with a dark opaque background; visual quality is closer to the
  supplied 3D emblems, but it is not a transparent badge yet.
- A restrained sibling,
  `C:/Users/33502/Desktop/RIFTCOACH/badge-void-image2-v2-muted.png`, keeps the
  same composition with slightly lower highlight/saturation; SHA-256
  `29f4d96b37717dee218155c4d93f07b1c705f71b4965719a5647767fbb6294bf`.

These Image2 files are user-generated candidates, not Riot assets. Prefer the
Image2 v1/v2 direction for the selected-region hero if the user accepts the
opaque background; create a separate transparent cutout only after that visual
choice is approved.
