"""Experimental Nikon DNG -> official Fuji CC/NC LUT desktop previews.

This is a deliberately provisional color input adaptation, not a validated
cross-camera film simulation. It uses LibRaw camera WB and linear sRGB output,
which may clip colors and has an uncalibrated scene-exposure scale.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import zipfile

import numpy as np
from PIL import Image, ImageDraw

from inspect_official_luts import parse_cube, trilinear
from render_official_swatch import flog2c

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'references/official/gfx-eterna-55-3d-lut-v110.zip'


def rgb_to_xyz(primaries, white=(.31270, .32900)):
    p = np.array([[x / y, 1., (1 - x - y) / y] for x, y in primaries]).T
    wx, wy = white
    white_xyz = np.array([wx / wy, 1., (1 - wx - wy) / wy])
    return p @ np.diag(np.linalg.solve(p, white_xyz))


def save_labelled(rgb, path, title):
    arr = np.rint(np.clip(rgb, 0, 1) * 255).astype(np.uint8)
    image = Image.fromarray(arr, 'RGB')
    banner = Image.new('RGB', (image.width, image.height + 40), '#202020')
    banner.paste(image, (0, 40))
    ImageDraw.Draw(banner).text((12, 12), title, fill='white')
    banner.save(path, quality=92, subsampling=0)


def srgb_oetf(linear):
    x = np.clip(linear, 0, 1)
    return np.where(x <= .0031308, 12.92 * x,
                    1.055 * np.power(x, 1 / 2.4) - .055)


def exposure_from_embedded_jpeg(developed, jpeg_path):
    """Match display-luminance medians, not a physical exposure calibration."""
    if not jpeg_path.is_file():
        raise FileNotFoundError(jpeg_path)
    h, w = developed.shape[:2]
    with Image.open(jpeg_path) as im:
        jpg = np.asarray(im.convert('RGB').resize((w, h), Image.Resampling.BILINEAR))[::8, ::8]
    raw = developed[::8, ::8].astype(np.float64) / 65535
    weights = np.array([.2126, .7152, .0722])
    target = float(np.median((jpg / 255) @ weights))
    low, high = -4., 4.
    for _ in range(24):
        mid = (low + high) / 2
        candidate = float(np.median(srgb_oetf(raw * 2 ** mid) @ weights))
        if candidate < target:
            low = mid
        else:
            high = mid
    stops = (low + high) / 2
    return stops, {'anchor_jpeg': str(jpeg_path), 'target_display_luma_median': target,
                   'rawpy_display_luma_median_at_gain1': float(np.median(srgb_oetf(raw) @ weights)),
                   'method': 'match whole-image median display luminance; heuristic, not color or scene-linear calibration'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('dng', type=Path)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--exposure-stops', type=float)
    group.add_argument('--anchor-jpeg', type=Path,
                       help='Same NEF embedded camera JPEG for heuristic median-brightness alignment')
    args = parser.parse_args()
    if not args.dng.is_file() or (args.exposure_stops is not None and not np.isfinite(args.exposure_stops)):
        parser.error('Valid DNG and finite exposure are required')
    sys.path.insert(0, str(ROOT / '.vendor'))
    import rawpy
    with rawpy.imread(str(args.dng)) as raw:
        developed = raw.postprocess(
            half_size=True, use_camera_wb=True, no_auto_bright=True,
            gamma=(1, 1), output_bps=16, output_color=rawpy.ColorSpace.sRGB,
            user_flip=0, bright=1.0)
    shape = developed.shape
    if args.anchor_jpeg:
        exposure_stops, anchor_info = exposure_from_embedded_jpeg(developed, args.anchor_jpeg)
    else:
        exposure_stops, anchor_info = (args.exposure_stops or 0.0), None
    base = developed.reshape(-1, 3)
    m_s = rgb_to_xyz(((.64, .33), (.30, .60), (.15, .06)))
    m_f = rgb_to_xyz(((.73470, .26530), (.02630, .97370), (.11730, -.02240)))
    matrix = np.linalg.solve(m_f, m_s)
    if not np.allclose(matrix @ np.ones(3), np.ones(3), atol=1e-6):
        raise ValueError('Neutral axis failed color-matrix check')
    with zipfile.ZipFile(ARCHIVE) as z:
        cubes = {}
        for token, needle in (('CC', 'CLASSIC-CHROME'), ('NC', 'CLASSIC-Neg.')):
            found = []
            for name in z.namelist():
                if name.endswith('.cube') and '/F-Log2C/' in name and needle in name:
                    blob = z.read(name)
                    _, arr = parse_cube(blob)
                    if arr.shape[0] == 65:
                        found.append((name, hashlib.sha256(blob).hexdigest(), arr))
            if len(found) != 1:
                raise ValueError(f'Expected one 65-grid {token} LUT, got {len(found)}')
            cubes[token] = found[0]
    out_dir = ROOT / 'outputs/desktop/experimental-dng-previews'
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {token: np.empty(shape, dtype=np.uint8) for token in cubes}
    baseline = np.empty(shape, dtype=np.uint8)
    negative = over_domain = clipped_srgb = baseline_clip = count = 0
    lut_clip = {token: 0 for token in cubes}
    gain = float(2 ** exposure_stops)
    for start in range(0, len(base), 50000):
        chunk = base[start:start + 50000].astype(np.float64) / 65535
        clipped_srgb += int(np.count_nonzero(np.any((base[start:start + 50000] == 0) |
                                                      (base[start:start + 50000] == 65535), axis=1)))
        display_linear = np.clip(chunk * gain, 0, 1)
        baseline_clip += int(np.count_nonzero(np.any(chunk * gain >= 1, axis=1)))
        srgb = srgb_oetf(display_linear)
        baseline.reshape(-1, 3)[start:start + len(chunk)] = np.rint(np.clip(srgb, 0, 1) * 255).astype(np.uint8)
        f_linear = (chunk @ matrix.T) * gain
        negative += int(np.count_nonzero(np.any(f_linear < 0, axis=1)))
        encoded = flog2c(np.maximum(f_linear, 0))
        over_domain += int(np.count_nonzero(np.any(encoded > 1, axis=1)))
        encoded = np.clip(encoded, 0, 1)
        for token, (_, _, cube) in cubes.items():
            rendered = trilinear(cube, encoded)
            lut_clip[token] += int(np.count_nonzero(np.any((rendered <= 0) |
                                                           (rendered >= 1), axis=1)))
            result[token].reshape(-1, 3)[start:start + len(chunk)] = np.rint(
                np.clip(rendered, 0, 1) * 255).astype(np.uint8)
        count += len(chunk)
    files = {}
    prefix = 'anchor' if args.anchor_jpeg else 'exp'
    tag = f'{prefix}_{exposure_stops:+.2f}'.replace('+', 'p').replace('-', 'm').replace('.', '_')
    p = out_dir / f'{args.dng.stem}_{tag}_rawpy_linear_srgb.jpg'
    save_labelled(baseline / 255, p, 'EXPERIMENTAL: LibRaw linear sRGB -> sRGB display')
    files['baseline'] = str(p.relative_to(ROOT))
    for token, arr in result.items():
        p = out_dir / f'{args.dng.stem}_{tag}_{token}_experimental.jpg'
        save_labelled(arr / 255, p, f'EXPERIMENTAL: Z6III DNG -> sRGB -> F-Gamut C -> official {token} LUT')
        files[token] = str(p.relative_to(ROOT))
    report = {'dng': str(args.dng), 'shape': list(shape), 'half_size': True,
              'rawpy_version': rawpy.__version__, 'libraw_version': rawpy.libraw_version,
              'camera_wb': True, 'no_auto_bright': True, 'exposure_stops': exposure_stops,
              'anchor': anchor_info,
              'matrix_linear_srgb_to_f_gamut_c': matrix.tolist(),
              'sRGB_boundary_pixel_fraction': clipped_srgb / count,
              'exposure_scaled_srgb_clipped_pixel_fraction': baseline_clip / count,
              'negative_f_gamut_pixel_fraction': negative / count,
              'over_lut_domain_pixel_fraction': over_domain / count,
              'lut_output_boundary_pixel_fraction': {k: v / count for k, v in lut_clip.items()},
              'official_lut_sha256': {k: v[1] for k, v in cubes.items()},
              'files': files,
              'limitation': 'Exploratory only: linear sRGB may clip gamut; exposure scale and camera color are not calibrated; output is not NP3 or Fuji camera JPEG.'}
    path = ROOT / 'reports' / f'{args.dng.stem}_{tag}_experimental-preview.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'files': files, 'pixel_count': count,
                      'exposure_stops': exposure_stops,
                      'exposure_scaled_srgb_clipped_pixel_fraction': baseline_clip / count,
                      'negative_f_gamut_pixel_fraction': negative / count,
                      'over_lut_domain_pixel_fraction': over_domain / count},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
