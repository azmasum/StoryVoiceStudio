"""Create the portable ZIP from the PyInstaller output folder."""
import shutil
import pathlib


def main() -> None:
    dist = pathlib.Path("dist")
    src = dist / "StoryVoiceStudio"
    if not src.exists():
        raise SystemExit("dist/StoryVoiceStudio not found - run PyInstaller first")
    zip_path = dist / "StoryVoiceStudio-Portable.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip",
                        root_dir=dist, base_dir="StoryVoiceStudio")
    print(f"Created {zip_path}")


if __name__ == "__main__":
    main()
