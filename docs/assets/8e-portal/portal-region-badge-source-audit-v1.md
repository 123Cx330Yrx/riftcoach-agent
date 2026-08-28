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
