"""Read-only environment inspection; writes only this project's report."""
from pathlib import Path
import datetime
import importlib.util
import json
import platform
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
report = {
    "checked_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
    "python_executable": sys.executable,
    "python_version": sys.version,
    "platform": platform.platform(),
    "modules": {name: importlib.util.find_spec(name) is not None for name in ("numpy", "PIL", "scipy", "colour", "rawpy")},
    "commands_on_path": {name: shutil.which(name) for name in ("node", "python", "git", "ffmpeg", "java", "ghidraRun", "uv", "rea")},
    "nx_studio_common_paths": {p: Path(p).is_file() for p in (
        "C:/Program Files/Nikon/NXStudio/NXStudio.exe",
        "C:/Program Files/Nikon/NX Studio/NXStudio.exe")},
    "limitations": ["PATH checks are not full installation searches", "No network probes or installations", "No camera connection or image rendering tested"]
}
target = ROOT / "reports" / "environment.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
