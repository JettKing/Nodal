#!/usr/bin/env python3
"""Discover valid subscription source files in the repository root."""
from __future__ import annotations

import argparse
import base64
import binascii
import re
from pathlib import Path

SUPPORTED_SCHEMES = (
    "vmess://",
    "vless://",
    "trojan://",
    "ss://",
    "ssr://",
    "hysteria://",
    "hysteria2://",
    "hy2://",
    "tuic://",
    "anytls://",
    "socks://",
    "socks5://",
    "http://",
    "wireguard://",
    "wg://",
)
SAFE_SOURCE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


def decode_source(path: Path) -> str:
    payload = b"".join(path.read_bytes().split())
    padding = b"=" * ((4 - len(payload) % 4) % 4)
    try:
        decoded = base64.b64decode(payload + padding, altchars=b"-_", validate=True)
    except binascii.Error as exc:
        raise ValueError(f"invalid Base64/Base64URL payload: {path}") from exc
    return decoded.decode("utf-8")


def is_valid_source(path: Path) -> bool:
    if (
        not path.is_file()
        or path.name.startswith(".")
        or path.suffix
        or not SAFE_SOURCE_NAME.fullmatch(path.name)
    ):
        return False
    try:
        text = decode_source(path)
    except (OSError, binascii.Error, UnicodeDecodeError, ValueError):
        return False
    return any(
        line.strip().lower().startswith(SUPPORTED_SCHEMES)
        for line in text.splitlines()
        if line.strip()
    )


def discover(root: Path) -> list[str]:
    return sorted(path.name for path in root.iterdir() if is_valid_source(path))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = parser.parse_args()
    sources = discover(args.root)
    if not sources:
        raise SystemExit("No valid subscription source files found.")
    print(" ".join(sources))


if __name__ == "__main__":
    main()
