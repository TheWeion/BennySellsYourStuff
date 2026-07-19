#!/usr/bin/env python3
"""Build the local mod-manager zips into dist/.

Produces the same artifacts the release workflow publishes, but off your working
tree with no tag or push - mirroring the "Package" step in
.github/workflows/release.yml so a local build is what CI would cut:

    <name>-Main-v<ver>.zip    - everything under src/, KitInfo.ini stamped
    <name>-Config-v<ver>.zip  - just src/Config, for a settings-only update

The staged .gek scripts are minified (comments/blank lines/trailing spaces
stripped) via tools/minify_gek.py; the sources under src/ are untouched.

The <name> is the repo's root folder name (also the KitInfo mod folder).

Both zips are rooted so their contents drop straight into Data\\.

Uses only the Python standard library (shutil/zipfile) - no external `zip`
binary needed, so it runs the same from Git Bash, PowerShell or cmd.

Usage:
    python tools/build.py                      # version from git (KitInfo fallback)
    python tools/build.py --version 1.1.0-local
    python tools/build.py --print-version      # resolve + print, build nothing
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import minify_gek

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


def git_next_version() -> str | None:
    """Mirror the release workflow's version math (github-tag-action).

    Baseline = the highest stable vX.Y.Z tag anywhere in the repo. Releases
    are cut from SQUASH merges onto main, so develop's commits are never
    ancestors of the release tags: ancestry-bound lookups (`git describe`)
    under-count from develop, and commit ranges over-count (already-released
    commits re-appear). So content decides first: if src/ is identical to
    the baseline tag's, this tree IS that release - no bump. Otherwise bump
    by the strongest Conventional Commit in <tag>..HEAD: BREAKING CHANGE
    footer -> major (the action ignores the `type!:` shorthand - footer
    only), feat -> minor, fix -> patch. That range can include released
    commits (squash topology), so a preview of unreleased work may bump one
    step higher than the release CI eventually cuts - a naming overshoot on
    local previews only. Returns None when git/tags aren't available.
    """
    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(("git", *args), cwd=ROOT, capture_output=True, text=True)

    tags = git("tag", "--list")
    if tags.returncode != 0:
        return None

    stable = []
    for tag in tags.stdout.split():
        m = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", tag)
        if m:
            stable.append((tuple(int(g) for g in m.groups()), tag))
    if not stable:
        return None

    (major, minor, patch), tag = max(stable)

    # Same src/ as the released tag = this IS that release. No HEAD arg:
    # the build packages the WORKING TREE, so uncommitted src/ edits must
    # count as a difference too
    if git("diff", "--quiet", tag, "--", "src").returncode == 0:
        return f"{major}.{minor}.{patch}"

    log = git("log", f"{tag}..HEAD", "--pretty=%s%n%b")
    if log.returncode != 0:
        return None

    rank = 0  # 0 = no releasable commits, 1 = patch, 2 = minor, 3 = major
    for line in log.stdout.splitlines():
        if "BREAKING CHANGE" in line:
            rank = 3
            break
        if re.match(r"feat(\([^)]*\))?:", line):
            rank = max(rank, 2)
        elif re.match(r"fix(\([^)]*\))?:", line):
            rank = max(rank, 1)

    if rank == 3:
        return f"{major + 1}.0.0"
    if rank == 2:
        return f"{major}.{minor + 1}.0"
    if rank == 1:
        return f"{major}.{minor}.{patch + 1}"
    return f"{major}.{minor}.{patch}"


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
        help="Version to stamp/name with (default: derived from git tags + "
             "Conventional Commits, mirroring the release workflow; falls "
             "back to the Version in KitInfo.ini without git).",
    )
    parser.add_argument(
        "--print-version",
        action="store_true",
        help="Resolve and print the version, build nothing (used by CI).",
    )
    args = parser.parse_args(argv)

    kit_info = SRC / KIT_INFO_REL
    if not kit_info.is_file():
        sys.exit(f"KitInfo.ini not found at {kit_info}")

    version = args.version
    source = "--version"
    if not version:
        version = git_next_version()
        source = "git"
    if not version:
        version = read_version(kit_info)
        source = "KitInfo.ini fallback"

    if args.print_version:
        print(version)
        return 0

    print(f"Building {NAME} v{version} ({source})")

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
    changed, saved = minify_gek.minify_tree(main_stage)
    print(f"  Minified {changed} .gek scripts ({saved:,} bytes removed)")

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
