# Task runner for local tooling.
#
# Install `just` once (https://github.com/casey/just):
#     winget install --id Casey.Just    # or: scoop install just / cargo install just
# Then, from the repo root:
#     just              # list recipes
#     just build        # stage src/ -> dist/*.zip (local release artifacts)
#     just bbcode       # README.md -> dist/README-nexus.bbcode (for Nexus)
#     just dist         # build + bbcode in one go
#
# Recipe bodies run under sh (Git Bash on Windows), so keep them POSIX. The
# build/convert logic itself lives in the tools/*.py scripts.
set shell := ["sh", "-cu"]

# Show the recipe list (default when you run bare `just`).
default:
    @just --list

# Build the local mod-manager zips into dist/ (mirrors the release workflow).
build version="":
    python tools/build.py {{ if version == "" { "" } else { "--version " + version } }}

# Convert README.md to Nexus BBCode -> dist/README-nexus.bbcode.
bbcode source="README.md":
    python tools/md2bbcode.py "{{source}}"

# Everything a release drop needs: zips + the Nexus description.
dist: build bbcode

# Remove all local build output.
clean:
    rm -rf dist && mkdir -p dist

# Install the Python tooling dependencies (markdown-it-py).
setup:
    python -m pip install -r tools/requirements.txt
