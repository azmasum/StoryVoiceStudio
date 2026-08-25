"""Create the portable ZIP from the PyInstaller output folder."""
import shutil
import pathlib


EXCLUDE_DIRS = {"clone_libs"}  # optional voice-clone pack (large)


def copy_tree(src: pathlib.Path, dst: pathlib.Path) -> None:
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def main() -> None:
    dist = pathlib.Path("dist")
    src = dist / "StoryVoiceStudio"
    if not src.exists():
        raise SystemExit("dist/StoryVoiceStudio not found - run PyInstaller first")
    staging = dist / "_zip_staging" / "StoryVoiceStudio"
    if staging.exists():
        shutil.rmtree(staging.parent)
    staging.mkdir(parents=True)
    copy_tree(src, staging)
    zip_path = dist / "StoryVoiceStudio-Portable.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip",
                        root_dir=staging.parent, base_dir="StoryVoiceStudio")
    shutil.rmtree(staging.parent)
    print(f"Created {zip_path} (voice-clone pack excluded)")


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
