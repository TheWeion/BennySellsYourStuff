#!/usr/bin/env python3
"""Minify .gek scripts in place: strip comments, blank lines, trailing spaces.

Meant for *staged* build trees only - build.py and the release workflow run it
on their dist/CI staging copies, so the scripts under src/ keep their comments.

ObScript comment rule honoured: ';' starts a comment unless it sits inside a
double-quoted string literal (ObScript strings cannot escape quotes and never
span lines). Leading indentation is preserved; lines left empty are dropped.

Files are round-tripped as latin-1 so any single-byte encoding (ASCII, cp1252)
and the file's CRLF/LF style survive untouched in the kept content.

Usage:
    python tools/minify_gek.py <file-or-dir> [<file-or-dir> ...]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Split lines explicitly: latin-1 text can contain bytes like 0x85 (cp1252
# ellipsis) that str.splitlines would also treat as line breaks.
_LINE_BREAK = re.compile(r"\r\n|\r|\n")


def strip_comment(line: str) -> str:
    """Return the code portion of a line: everything before an unquoted ';'."""
    in_string = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_string = not in_string
        elif ch == ";" and not in_string:
            return line[:i]
    return line


def minify_text(text: str) -> str:
    eol = "\r\n" if "\r\n" in text else "\n"
    kept = [s for line in _LINE_BREAK.split(text) if (s := strip_comment(line).rstrip(" \t"))]
    return eol.join(kept) + eol if kept else ""


def minify_tree(root: Path) -> tuple[int, int]:
    """Minify root (a .gek file, or a dir walked for *.gek).

    Returns (files_changed, bytes_saved).
    """
    # rglob matches directories too - a folder named *.gek must not crash us.
    files = [root] if root.is_file() else sorted(p for p in root.rglob("*.gek") if p.is_file())
    changed = saved = 0
    for path in files:
        raw = path.read_bytes()
        out = minify_text(raw.decode("latin-1")).encode("latin-1")
        if out != raw:
            path.write_bytes(out)
            changed += 1
            saved += len(raw) - len(out)
    return changed, saved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Strip comments, blank lines and trailing spaces from staged .gek scripts."
    )
    parser.add_argument("paths", nargs="+", type=Path, help="Files or directories to minify in place.")
    args = parser.parse_args(argv)

    total_changed = total_saved = 0
    for path in args.paths:
        if not path.exists():
            sys.exit(f"No such path: {path}")
        changed, saved = minify_tree(path)
        total_changed += changed
        total_saved += saved
    print(f"Minified {total_changed} .gek file(s), {total_saved:,} bytes removed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
