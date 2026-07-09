#!/usr/bin/env python3
"""Build the local mod-manager zips into dist/.

Produces the same artifacts the release workflow publishes, but off your working
tree with no tag or push - mirroring the "Package" step in
.github/workflows/release.yml so a local build is what CI would cut:

    <name>-Main-v<ver>.zip    - everything under src/, KitInfo.ini stamped
    <name>-Config-v<ver>.zip  - just src/Config, for a settings-only update

The <name> is the repo's root folder name (also the KitInfo mod folder).

Both zips are rooted so their contents drop straight into Data\\.

Uses only the Python standard library (shutil/zipfile) - no external `zip`
binary needed, so it runs the same from Git Bash, PowerShell or cmd.

Usage:
    python tools/build.py                      # version from KitInfo.ini
    python tools/build.py --version 1.1.0-local
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = ROOT.name  # the mod name is the repo's root folder name
SRC = ROOT / "src"
DIST = ROOT / "dist"
KIT_INFO_REL = f"Devkit/Mods/{NAME}/KitInfo.ini"


def read_version(kit_info: Path) -> str:
    for line in kit_info.read_text(encoding="utf-8").splitlines():
        if line.startswith("Version:"):
            return line[len("Version:"):].strip()
    sys.exit(f"No 'Version:' line in {kit_info} - pass --version explicitly.")


def stamp_version(kit_info: Path, version: str) -> None:
    """Rewrite the staged KitInfo.ini's Version line, keeping LF endings."""
    lines = kit_info.read_text(encoding="utf-8").splitlines()
    lines = [f"Version: {version}" if ln.startswith("Version:") else ln for ln in lines]
    kit_info.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def zip_rooted(stage: Path) -> Path:
    """Zip the contents of `stage` at the archive root; return the .zip path."""
    archive = shutil.make_archive(str(stage), "zip", root_dir=str(stage))
    return Path(archive)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build local mod-manager zips into dist/.")
    parser.add_argument(
        "--version",
        help="Version to stamp/name with (default: the Version in KitInfo.ini).",
    )
    args = parser.parse_args(argv)

    kit_info = SRC / KIT_INFO_REL
    if not kit_info.is_file():
        sys.exit(f"KitInfo.ini not found at {kit_info}")

    version = args.version or read_version(kit_info)
    print(f"Building {NAME} v{version}")

    main_stage = DIST / f"{NAME}-Main-v{version}"
    config_stage = DIST / f"{NAME}-Config-v{version}"
    for stage in (main_stage, config_stage):
        if stage.exists():
            shutil.rmtree(stage)
    DIST.mkdir(parents=True, exist_ok=True)

    # ---- Main artifact: the whole src/ tree, KitInfo stamped --------------
    shutil.copytree(SRC, main_stage)
    stamp_version(main_stage / KIT_INFO_REL, version)
    print(f"  Stamped KitInfo.ini -> Version: {version}")

    # ---- Config artifact: just src/Config --------------------------------
    (config_stage).mkdir(parents=True, exist_ok=True)
    shutil.copytree(SRC / "Config", config_stage / "Config")

    # ---- Zip both (rooted so contents land straight in Data\) -------------
    main_zip = zip_rooted(main_stage)
    config_zip = zip_rooted(config_stage)

    # Staging dirs were only scaffolding for the zips - leave dist/ tidy.
    shutil.rmtree(main_stage)
    shutil.rmtree(config_stage)

    print("Done. Artifacts in dist/:")
    for z in (main_zip, config_zip):
        print(f"  {z.name}  ({z.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
