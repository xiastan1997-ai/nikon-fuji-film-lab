"""Convert private Z6III NEFs with an installed Adobe DNG Converter 16+.

Call the official converter with lossless mosaic output. This script does not
ship Adobe software, rewrite originals, or claim camera color matching.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / 'data/originals/nikon/downloaded_raw_batch02'
DEFAULT_OUTPUT = ROOT / 'data/derived/dng_batch02'
REPORT = ROOT / 'reports/dng-conversion.json'


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def check_sensor_pixels(path):
    """Read the mosaic array, not DNG's embedded JPEG preview."""
    sys.path.insert(0, str(ROOT / '.vendor'))
    try:
        import rawpy
        import numpy as np
    except ImportError as exc:
        return {'status': 'rawpy_unavailable', 'detail': str(exc)}
    try:
        with rawpy.imread(str(path)) as raw:
            image = raw.raw_image_visible
            if image is None or image.size == 0:
                raise ValueError('No visible sensor mosaic')
            sample = np.asarray(image[::128, ::128], dtype=np.float64)
            return {'status': 'mosaic_read', 'shape': list(image.shape),
                    'dtype': str(image.dtype), 'sample_min': float(sample.min()),
                    'sample_max': float(sample.max()),
                    'sample_std': float(sample.std())}
    except Exception as exc:
        return {'status': 'mosaic_read_failed', 'detail': repr(exc)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--converter', type=Path, required=True,
                        help='Installed Adobe DNG Converter executable')
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--limit', type=int, default=None,
                        help='Convert only the first N files for a small pilot')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    if not args.converter.is_file():
        parser.error('Converter executable not found')
    files = sorted(args.input.glob('*.NEF'))
    if args.limit is not None:
        if args.limit < 1:
            parser.error('--limit must be positive')
        files = files[:args.limit]
    if not files:
        parser.error('No NEF files found')
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    for src in files:
        dest = args.output / (src.stem + '.dng')
        if dest.exists() and not args.force:
            status, exit_code, tail = 'existing_dng_checked', None, ''
        else:
            run = subprocess.run([str(args.converter), '-c', '-p0', '-d',
                                  str(args.output), str(src)],
                                 capture_output=True, text=True, errors='replace',
                                 timeout=600)
            exit_code = run.returncode
            tail = (run.stdout + '\n' + run.stderr)[-1000:]
            status = 'converted' if exit_code == 0 and dest.is_file() else 'conversion_failed'
        result = {'input': str(src.relative_to(ROOT)), 'input_sha256': sha256(src),
                  'output': str(dest.relative_to(ROOT)), 'status': status,
                  'exit_code': exit_code, 'converter_output_tail': tail}
        if dest.is_file():
            result.update({'output_bytes': dest.stat().st_size,
                           'output_sha256': sha256(dest),
                           'sensor_check': check_sensor_pixels(dest)})
        results.append(result)
        print(f'{src.name}: {status}; {result.get("sensor_check", {}).get("status", "no_dng")}')
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({'converter': str(args.converter), 'files': results},
                                 ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if not all(item.get('sensor_check', {}).get('status') == 'mosaic_read'
               for item in results):
        raise SystemExit('At least one DNG did not yield sensor pixels')


if __name__ == '__main__':
    main()
