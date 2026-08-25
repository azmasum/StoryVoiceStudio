"""Build the portable ZIP and the one-click Setup.exe (7z SFX).

Outputs into dist/:
  - StoryVoiceStudio-Portable.zip   (unzip anywhere, run Install.bat)
  - StoryVoiceStudio-Setup.exe      (double-click -> installs)

Both contain the app plus the installer scripts; the optional
voice-clone pack is excluded from the payload (the installer can
fetch it on demand).
"""
import pathlib
import shutil
import subprocess

DIST = pathlib.Path("dist")
SRC = DIST / "StoryVoiceStudio"
STAGE_ROOT = DIST / "_zip_staging"
STAGE = STAGE_ROOT / "StoryVoiceStudio"
ZIP_PATH = DIST / "StoryVoiceStudio-Portable.zip"
SETUP_PATH = DIST / "StoryVoiceStudio-Setup.exe"

EXCLUDE_DIRS = {"clone_libs", "_runtime"}
INSTALLER_FILES = ("Install.bat", "install.ps1", "Uninstall.bat")
SEVENZIP_CANDIDATES = (
    r"C:\Program Files\7-Zip\7z.exe",
    r"C:\Program Files (x86)\7-Zip\7z.exe",
)
SFX_MODULE = pathlib.Path(__file__).parent / "tools" / "7zSD.sfx"


def find_7z() -> str | None:
    for cand in SEVENZIP_CANDIDATES:
        if pathlib.Path(cand).exists():
            return cand
    return None


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
    if not SRC.exists():
        raise SystemExit("dist/StoryVoiceStudio not found - run PyInstaller first")

    # --- stage payload -----------------------------------------------------
    if STAGE_ROOT.exists():
        shutil.rmtree(STAGE_ROOT)
    STAGE.mkdir(parents=True)
    copy_tree(SRC, STAGE)
    inst_src = pathlib.Path(__file__).parent / "portable_installer"
    for name in INSTALLER_FILES:
        shutil.copy2(inst_src / name, STAGE / name)

    # --- portable zip -------------------------------------------------------
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    shutil.make_archive(str(ZIP_PATH.with_suffix("")), "zip",
                        root_dir=STAGE_ROOT, base_dir="StoryVoiceStudio")
    print(f"Created {ZIP_PATH}")

    # --- one-click setup.exe -------------------------------------------------
    sevenzip = find_7z()
    sfx_config = STAGE_ROOT / "sfx_config.txt"
    sfx_config.write_text(
        ';!@Install@!UTF-8!\r\n'
        'Title="StoryVoice Studio"\r\n'
        'BeginPrompt="Install StoryVoice Studio on this PC?"\r\n'
        'RunProgram="StoryVoiceStudio\\\\Install.bat"\r\n'
        'ExtractTitle="StoryVoice Studio"\r\n'
        'ExtractDialogText="Preparing installation files..."\r\n'
        ';!@InstallEnd@!\r\n',
        encoding="utf-8-sig",
    )
    archive = STAGE_ROOT / "payload.7z"
    if SETUP_PATH.exists():
        SETUP_PATH.unlink()

    if not sevenzip:
        print("7-Zip not found - skipped Setup.exe (zip only).")
        shutil.rmtree(STAGE_ROOT)
        return

    subprocess.check_call([sevenzip, "a", str(archive), str(STAGE),
                           "-mx=9", "-bso0", "-bsp0"])
    if SFX_MODULE.exists():
        with open(SETUP_PATH, "wb") as out:
            out.write(SFX_MODULE.read_bytes())
            out.write(sfx_config.read_bytes())
            with open(archive, "rb") as arc:
                shutil.copyfileobj(arc, out)
        size_mb = SETUP_PATH.stat().st_size // (1024 * 1024)
        print(f"Created {SETUP_PATH} ({size_mb} MB)")
    else:
        print("7zSD.sfx module missing - skipped Setup.exe.")
    shutil.rmtree(STAGE_ROOT)


if __name__ == "__main__":
    main()
