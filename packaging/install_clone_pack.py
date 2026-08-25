"""Install the optional voice-clone pack (OpenVoice v2 tone transfer).

Usage:
    python packaging/install_clone_pack.py [--source] [--dist PATH]

- --source      install into <repo>/clone_libs for source-mode runs
- --dist PATH   install into <PATH>/clone_libs next to a built EXE

Both flags may be combined.  Model checkpoints always go to the app
data dir (paths.clone_models_dir()).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

HF_BASE = "https://huggingface.co/myshell-ai/OpenVoiceV2/resolve/main/converter"
FILES = ("checkpoint.pth", "config.json")
TORCH_INDEX = "https://download.pytorch.org/whl/cpu"


def pip_target(target: Path, packages: list[str]) -> None:
    target.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pip", "install", "--target", str(target),
           "--upgrade", "--no-warn-script-location", *packages]
    print("+", " ".join(cmd))
    subprocess.check_call(cmd)


def fetch(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"= exists  {dest.name} ({dest.stat().st_size // 1024} KB)")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"+ download {url}")

    def hook(blocks: int, bs: int, total: int) -> None:
        done = min(blocks * bs, total)
        pct = f"{done * 100 // total}%" if total > 0 else "?"
        print(f"\r  {pct} ({done // (1024 * 1024)} MB)", end="", flush=True)

    urllib.request.urlretrieve(url, tmp, reporthook=hook)
    print()
    tmp.rename(dest)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", action="store_true")
    ap.add_argument("--dist", type=Path, default=None)
    args = ap.parse_args()
    if not args.source and not args.dist:
        args.source = True

    roots: list[Path] = []
    if args.source:
        roots.append(REPO / "clone_libs")
    if args.dist:
        roots.append(args.dist / "clone_libs")

    for root in roots:
        pip_target(root, ["torch", "librosa"])

    from app.config.paths import clone_models_dir, data_dir
    models = clone_models_dir()
    for name in FILES:
        fetch(f"{HF_BASE}/{name}", models / name)

    # A --dist install targets the frozen app, whose data dir lives in
    # %LOCALAPPDATA% - mirror the checkpoints there too.
    if args.dist:
        frozen_models = (data_dir() if not getattr(sys, "frozen", False)
                         else clone_models_dir())
        # compute the LOCALAPPDATA location the EXE will use
        import os
        base = Path(os.environ["LOCALAPPDATA"]) / "StoryVoiceStudio" / "models" / "openvoice"
        base.mkdir(parents=True, exist_ok=True)
        for name in FILES:
            target = base / name
            if not target.exists():
                import shutil
                shutil.copy2(models / name, target)
                print(f"  copied -> {target}")

    print("\nVoice-clone pack installed:")
    for root in roots:
        print(f"  libs     : {root}")
    print(f"  models   : {models}")
    print("Restart the app; the Voice Clone box should show 'ready'.")


if __name__ == "__main__":
    main()
