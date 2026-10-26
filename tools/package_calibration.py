"""Package already-built diagnostic NP3s and verify hashes inside both ZIPs."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'outputs/calibration-z6iii-c201'


def pack(folder, target, manifest, extra):
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
        members = [item['file'] for item in manifest['files']] + ['manifest.json'] + extra
        for member in members:
            f = (folder / member).resolve()
            if not f.is_relative_to(folder.resolve()) or not f.is_file():
                raise ValueError(f'Invalid package member: {member}')
            z.write(f, f.relative_to(folder).as_posix())
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for item in manifest['files']:
            assert hashlib.sha256(z.read(item['file'])).hexdigest() == item['sha256']
    return {'file': str(target.relative_to(ROOT)), 'bytes': target.stat().st_size,
            'np3_files': len(manifest['files']),
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}


def main():
    manifest = json.loads((SOURCE / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('camera_import_tested') is not False:
        raise ValueError('Expected explicitly unverified diagnostic pack')
    shutil.copy2(ROOT / 'docs/10_机内诊断包.md', SOURCE / '使用说明.md')
    full = pack(SOURCE, SOURCE.with_suffix('.zip'), manifest, ['README.txt', '使用说明.md'])
    starter = ROOT / 'outputs/z6iii-first-import-test'
    selected = dict(manifest, files=manifest['files'][:2])
    (starter / 'NIKON/CUSTOMPC').mkdir(parents=True, exist_ok=True)
    for item in selected['files']:
        shutil.copy2(SOURCE / item['file'], starter / item['file'])
    (starter / 'manifest.json').write_text(json.dumps(selected, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copy2(ROOT / 'docs/首次导入测试说明.txt', starter / '先看这里.txt')
    small = pack(starter, starter.with_suffix('.zip'), selected, ['先看这里.txt'])
    print(json.dumps([full, small], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
