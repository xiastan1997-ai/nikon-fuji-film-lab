"""Render synthetic scene-linear F-Gamut C color patches through official LUTs.

This proves only the numeric desktop LUT path. No Nikon image, sensor model,
camera JPEG equivalence, or NP3 is involved. The original CUBE stays private.
"""
from pathlib import Path
import json
import zipfile

import numpy as np
from PIL import Image, ImageDraw

from inspect_official_luts import parse_cube, trilinear

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'references/official/gfx-eterna-55-3d-lut-v110.zip'
OUT = ROOT / 'outputs/desktop/official-synthetic-swatch.png'
REPORT = ROOT / 'reports/official-synthetic-swatch.json'


def flog2c(linear):
    """Whitepaper p.11, scene-linear reflection to F-Log2C code values."""
    x = np.asarray(linear, dtype=np.float64)
    if np.any(x < 0):
        raise ValueError('Synthetic reflectance must be nonnegative')
    return np.where(x >= .000889,
                    .245281 * np.log10(5.555556 * x + .064829) + .384316,
                    8.799461 * x + .092864)


PATCHES = [
    ('black', (0, 0, 0)), ('gray 5%', (.05, .05, .05)),
    ('gray 18%', (.18, .18, .18)), ('gray 50%', (.5, .5, .5)),
    ('white', (1, 1, 1)), ('warm', (.42, .25, .16)),
    ('red', (.55, .05, .04)), ('orange', (.65, .25, .03)),
    ('yellow', (.6, .52, .04)), ('green', (.05, .45, .07)),
    ('cyan', (.04, .4, .44)), ('blue', (.04, .08, .55)),
    ('purple', (.3, .06, .45)), ('skin-like', (.55, .31, .19)),
]


def main():
    values = np.asarray([rgb for _, rgb in PATCHES], dtype=np.float64)
    encoded = flog2c(values)
    if np.any((encoded < 0) | (encoded > 1)):
        raise ValueError('F-Log2C test values escaped LUT domain')
    with zipfile.ZipFile(ARCHIVE) as z:
        names = z.namelist()
        targets = {}
        for label, needle in (('CC', 'CLASSIC-CHROME'), ('NC', 'CLASSIC-Neg.')):
            matches = [n for n in names if '/F-Log2C/' in n and needle in n
                       and n.endswith('.cube') and '65grid' in n.lower()]
            if len(matches) != 1:
                # Filename conventions can differ; select from parsed grid instead.
                matches = []
                for n in names:
                    if '/F-Log2C/' in n and needle in n and n.endswith('.cube'):
                        _, lut = parse_cube(z.read(n))
                        if lut.shape[0] == 65:
                            matches.append(n)
            if len(matches) != 1:
                raise ValueError(f'Expected one 65-grid LUT for {label}: {matches}')
            _, lut = parse_cube(z.read(matches[0]))
            targets[label] = {'name': matches[0], 'rgb': trilinear(lut, encoded)}

    width, patch_w, patch_h, gap, margin = 1220, 140, 82, 8, 16
    img = Image.new('RGB', (width, 3 * (2 * (patch_h + 24) + 18) + 62), '#202020')
    d = ImageDraw.Draw(img)
    d.text((margin, 10), 'SYNTHETIC F-Gamut C reflectance -> F-Log2C -> official Fuji LUT -> BT.709', fill='white')
    d.text((margin, 30), 'Numerical test only. Not a Nikon photo or a camera film simulation.', fill='#dddddd')
    rows = [('Input codes', encoded), ('Classic Chrome', targets['CC']['rgb']),
            ('Classic Negative', targets['NC']['rgb'])]
    for row_idx, (title, rgb) in enumerate(rows):
        y = 62 + row_idx * (2 * (patch_h + 24) + 18)
        d.text((margin, y + 24), title, fill='white')
        for j, (label, _) in enumerate(PATCHES):
            x = 165 + (j % 7) * (patch_w + gap)
            yy = y + (j // 7) * (patch_h + 24)
            color = tuple(np.rint(np.clip(rgb[j], 0, 1) * 255).astype(np.uint8).tolist())
            d.rectangle((x, yy, x + patch_w - 1, yy + patch_h - 1), fill=color)
            d.text((x + 3, yy + patch_h - 17), label, fill='white', stroke_width=1, stroke_fill='black')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT_str = str(OUT)
    img.save(OUT_str)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({'image': str(OUT.relative_to(ROOT)),
                                  'input_note': 'Synthetic scene-linear F-Gamut C channel values; not measured spectral colors',
                                  'encoding': 'F-Log2C whitepaper p.11',
                                  'output_note': 'BT.709 LUT values are directly mapped to PNG codes for inspection',
                                  'patches': {PATCHES[i][0]: {
                                      'scene_linear': PATCHES[i][1],
                                      'flog2c': encoded[i].tolist(),
                                      'CC': targets['CC']['rgb'][i].tolist(),
                                      'NC': targets['NC']['rgb'][i].tolist()}
                                      for i in range(len(PATCHES))}}, ensure_ascii=False, indent=2),
                      encoding='utf-8')
    print(OUT)


if __name__ == '__main__':
    main()
