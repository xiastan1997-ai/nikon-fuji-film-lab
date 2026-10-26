"""Check public source staging; optionally require validated camera profiles."""
from pathlib import Path
import argparse
import json
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--require-profiles', action='store_true',
                    help='Fail unless CC/NC reference, Nikon input, and camera NP3 gates pass')
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[1]
result = subprocess.run(['git', '-C', str(ROOT), 'ls-files'], capture_output=True, text=True, check=True)
tracked = [line.strip().replace('\\', '/') for line in result.stdout.splitlines() if line.strip()]
forbidden = ('data/originals/', 'data/derived/', 'references/official/', 'references/community/', '.vendor/', 'outputs/')
violations = [path for path in tracked if path.startswith(forbidden)]
required = ['README.md', 'LICENSE', '.gitignore', 'reports/public-status.md',
            'tools/inspect_official_luts.py',
            'third_party/nikon-flexible-color-picture-control/LICENSE',
            'third_party/nikon-flexible-color-picture-control/PROVENANCE.md']
missing = [path for path in required if path not in tracked]
private_local_paths = []
for path in tracked:
    try:
        staged = subprocess.run(['git', '-C', str(ROOT), 'show', f':{path}'],
                                capture_output=True, check=True)
        body = staged.stdout.decode('utf-8')
    except (UnicodeError, OSError, subprocess.CalledProcessError):
        continue
    if re.search(r'C:[\\/]Users[\\/][^\\/]+[\\/]|D:[\\/](?:CODEX|夸克)', body,
                 re.IGNORECASE):
        private_local_paths.append(path)
experiment = json.loads((ROOT/'experiments/experiments.json').read_text(encoding='utf-8'))
stage = {item['id']: item['status'] for item in experiment['experiments']}
release_ready = (stage.get('E01') == 'passed' and stage.get('E02') == 'passed'
                 and stage.get('E03') == 'camera_validated'
                 and set(experiment['profile_status']) == set(experiment['target_simulations'])
                 and all(status == 'camera_validated'
                         for status in experiment['profile_status'].values()))
print(json.dumps({'tracked_files':len(tracked), 'private_path_violations':violations,
                  'private_local_paths':private_local_paths,
                  'missing_public_files':missing, 'v1_profiles_release_ready':release_ready},
                 ensure_ascii=False, indent=2))
if violations or missing or private_local_paths or (args.require_profiles and not release_ready):
    raise SystemExit(1)
