# Bandle City static Account image restoration candidate

Status: `research-only` · `rejected` · not adopted

## Inputs and output

- Original: `C:/Users/33502/Desktop/RIFTCOACH/runeterra-bandlecity-03.jpg`
- Original SHA-256: `bce45259ab92683a5c6e8cd69fe3f7e859b976dbbe76ba8afd27062b263ef2b1`
- Original dimensions: 926×1080 JPEG (`yuvj444p`); this is why the image becomes visibly soft when used as a large Account background.
- Restoration candidate: `C:/Users/33502/Desktop/RIFTCOACH/runeterra-bandlecity-03-restored-v1.png`
- Candidate SHA-256: `a3c8dcd985d2507db35516ac17c73a4efe79d5a29bd9e93924b703fe597ac2eb`
- Candidate dimensions: 1161×1354 PNG

## Method

The built-in image generation editor was used once with the JPEG as the edit target. The prompt explicitly locked the portrait framing,
central tree, embedded Bandle City emblem, foliage, light direction and painterly identity, and asked only for detail reconstruction and
compression cleanup. The original JPEG was not overwritten.

## Review boundary

The candidate is sharper than the JPEG, but manual review rejects it as a final asset: the reconstruction is too crunchy/high-frequency,
the bark highlights read as AI-invented texture, and the emblem/brushwork no longer sits at the same quality level as the other saved
region stills. It remains only as a comparison artifact. A true higher-resolution Riot source or a different native still is required;
do not spend more generation attempts on this prompt or promote it by increasing sharpness.
