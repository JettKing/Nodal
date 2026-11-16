#!/usr/bin/env python3
"""Remove generated root YAML files whose source is no longer present."""
from __future__ import annotations

import argparse
from pathlib import Path


def prune(root: Path, sources: set[str]) -> list[str]:
    removed: list[str] = []
    for path in sorted(root.glob("*.yaml")):
        if path.stem not in sources:
            path.unlink()
            removed.append(path.name)
    return removed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", required=True, help="Space-separated discovered source names")
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = parser.parse_args()
    removed = prune(args.root, set(args.sources.split()))
    if removed:
        print("Removed stale generated configs: " + " ".join(removed))
    else:
        print("No stale generated configs.")


if __name__ == "__main__":
    main()
