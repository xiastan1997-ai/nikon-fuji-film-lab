"""Inspect official .cube files directly from the preserved Fujifilm ZIP.

This is a numerical LUT check, not a Nikon RAW processing pipeline.
"""
from pathlib import Path
import hashlib
import json
import re
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'references/official/gfx-eterna-55-3d-lut-v110.zip'
REPORT = ROOT / 'reports/official-lut-inventory.json'
TARGETS = {'CC': 'CLASSIC-CHROME', 'NC': 'CLASSIC-Neg.', 'NN': 'NOSTALGIC-Neg.'}


def parse_cube(blob):
    header, rows, grid = {}, [], None
    for line in blob.decode('utf-8-sig').splitlines():
        value = line.strip()
        if not value:
            continue
        if value.startswith('#'):
            if ':' in value:
                k, v = value[1:].split(':', 1)
                header[k.strip()] = v.strip()
            continue
        if value.startswith('LUT_3D_SIZE'):
            grid = int(value.split()[1]); continue
        if value.startswith('DOMAIN_'):
            header[value.split()[0]] = [float(x) for x in value.split()[1:]]
            continue
        cols = value.split()
        if len(cols) == 3:
            rows.append([float(x) for x in cols])
        else:
            raise ValueError(f'Unexpected CUBE row {value!r}')
    if grid not in (33, 65) or len(rows) != grid**3:
        raise ValueError(f'Invalid grid: {grid}, {len(rows)} rows')
    array = np.asarray(rows, dtype=np.float32).reshape((grid, grid, grid, 3))
    if not np.isfinite(array).all():
        raise ValueError('Non-finite LUT entries')
    return header, array


def trilinear(lut, samples):
    """CUBE order: red varies fastest, then green, then blue."""
    p = np.clip(samples, 0, 1) * (lut.shape[0] - 1)
    lo = np.floor(p).astype(int)
    hi = np.minimum(lo + 1, lut.shape[0] - 1)
    f = p - lo
    result = np.zeros((len(samples), 3), dtype=np.float64)
    for b in (0, 1):
        for g in (0, 1):
            for r in (0, 1):
                weight = ((f[:, 2] if b else 1-f[:, 2]) *
                          (f[:, 1] if g else 1-f[:, 1]) *
                          (f[:, 0] if r else 1-f[:, 0]))
                result += weight[:, None] * lut[
                    np.where(b, hi[:, 2], lo[:, 2]),
                    np.where(g, hi[:, 1], lo[:, 1]),
                    np.where(r, hi[:, 0], lo[:, 0])]
    return result


def main():
    with zipfile.ZipFile(ARCHIVE) as archive:
        corrupt = archive.testzip()
        if corrupt:
            raise ValueError(f'Corrupt ZIP member: {corrupt}')
        selected = [n for n in archive.namelist()
                    if n.endswith('.cube') and '/F-Log2C/' in n and
                    ('CLASSIC-CHROME' in n or 'CLASSIC-Neg.' in n)]
        entries = {}
        for name in sorted(selected):
            blob = archive.read(name)
            header, array = parse_cube(blob)
            token = 'CC' if 'CLASSIC-CHROME' in name else 'NC'
            grid = array.shape[0]
            entries.setdefault(token, {})[grid] = {
                'name': name, 'sha256': hashlib.sha256(blob).hexdigest(),
                'header': header, 'shape': list(array.shape),
                'min': float(array.min()), 'max': float(array.max()),
                'array': array,
            }
        for token in ('CC', 'NC'):
            if set(entries[token]) != {33, 65}:
                raise ValueError(f'Missing expected F-Log2C grids for {token}')
        rng = np.random.default_rng(20261024)
        samples = rng.random((10000, 3))
        result = {'archive': str(ARCHIVE.relative_to(ROOT)),
                  'archive_sha256': hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
                  'archive_member_count': len(archive.namelist()),
                  'targets': {}, 'random_seed': 20261024,
                  'comparison_domain': 'uniform input code values [0,1]^3',
                  'interpolation': 'trilinear; red channel fastest in CUBE rows',
                  'note': '33-vs-65 disagreement is a sampling/interpolation diagnostic, not a Nikon visual accuracy score'}
        for token in TARGETS:
            if token not in entries:
                result['targets'][token] = {'official_LUT_in_archive': False}
                continue
            d = entries[token]
            a = trilinear(d[33]['array'], samples)
            b = trilinear(d[65]['array'], samples)
            delta = np.abs(a-b)
            result['targets'][token] = {
                'official_LUT_in_archive': True,
                'grids': {str(k): {j:v for j,v in d[k].items() if j != 'array'} for k in d},
                '33_vs_65_abs_difference': {
                    'mean_per_channel': delta.mean(axis=0).tolist(),
                    'p95_max_channel': float(np.quantile(delta.max(axis=1), .95)),
                    'max_channel': float(delta.max()),
                },
            }
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'targets': {k: {'present':v['official_LUT_in_archive'],
                                      'p95':v.get('33_vs_65_abs_difference',{}).get('p95_max_channel')}
                                    for k,v in result['targets'].items()}}, indent=2))


if __name__ == "__main__":
    main()
