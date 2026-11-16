#!/usr/bin/env python3
"""Merge Hysteria2 and VLESS links into a generated Mihomo configuration."""

from __future__ import annotations

import argparse
import base64
import binascii
import urllib.parse
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_SCHEMES = {"hysteria2", "vless"}
TRUE_VALUES = {"1", "true", "yes", "on"}


def first(query: dict[str, list[str]], *keys: str) -> str | None:
    for key in keys:
        values = query.get(key)
        if values and values[0] != "":
            return values[0]
    return None


def truthy(value: str | None) -> bool:
    return value is not None and value.lower() in TRUE_VALUES


def parse_link(line: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line or "://" not in line:
        return None
    parsed = urllib.parse.urlsplit(line)
    scheme = parsed.scheme.lower()
    if scheme not in SUPPORTED_SCHEMES:
        return None

    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    username = parsed.username
    host = parsed.hostname
    port = parsed.port

    # Some providers wrap VLESS's `uuid:host:port` payload in URL-safe
    # Base64 after vless://. Decode only the authority; query options remain
    # outside the Base64 payload.
    if scheme == "vless" and (not host or not port):
        encoded = parsed.netloc.split("@", 1)[-1]
        encoded += "=" * ((4 - len(encoded) % 4) % 4)
        try:
            decoded = base64.urlsafe_b64decode(encoded).decode("utf-8")
            if "@" in decoded:
                username, authority = decoded.rsplit("@", 1)
                host, port_text = authority.rsplit(":", 1)
            else:
                decoded_parts = decoded.rsplit(":", 2)
                if len(decoded_parts) != 3:
                    return None
                username, host, port_text = decoded_parts
            if username and host and port_text:
                port = int(port_text)
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return None

    if not host or not port:
        return None

    name = urllib.parse.unquote(parsed.fragment) or first(query, "remarks")
    name = name or f"{scheme}-{host}-{port}"
    name = name.strip()

    node: dict[str, Any] = {
        "name": name,
        "type": scheme,
        "server": host,
        "port": port,
        "udp": True,
    }

    if username:
        node["password" if scheme == "hysteria2" else "uuid"] = urllib.parse.unquote(username)

    if scheme == "hysteria2":
        sni = first(query, "sni", "peer")
        if sni:
            node["sni"] = sni
        if truthy(first(query, "insecure")):
            node["skip-cert-verify"] = True
        mport = first(query, "mport", "ports")
        if mport:
            node["ports"] = mport
        obfs = first(query, "obfs")
        if obfs:
            node["obfs"] = obfs
        obfs_password = first(query, "obfs-password", "obfs_password")
        if obfs_password:
            node["obfs-password"] = obfs_password
        alpn = first(query, "alpn")
        if alpn:
            node["alpn"] = [part for part in alpn.split(",") if part]
        return node

    # VLESS links use Xray-style query names. Mihomo uses the same concepts
    # but stores transport-specific settings below ws-opts/grpc-opts/http-opts.
    node["tls"] = truthy(first(query, "security", "tls")) or first(query, "security") in {"tls", "reality"}
    servername = first(query, "sni", "peer", "servername")
    if servername:
        node["servername"] = servername
    if truthy(first(query, "allowInsecure", "allow-insecure", "insecure")):
        node["skip-cert-verify"] = True
    flow = first(query, "flow")
    if not flow and first(query, "xtls") in {"vision", "xtls-rprx-vision"}:
        flow = "xtls-rprx-vision"
    if flow and flow in {"xtls-rprx-vision"}:
        node["flow"] = flow
    fingerprint = first(query, "fingerprint", "fp")
    if fingerprint:
        node["client-fingerprint"] = fingerprint

    public_key = first(query, "pbk", "publicKey")
    short_id = first(query, "sid", "shortId")
    spider_x = first(query, "spx", "spiderX")
    if public_key or short_id or spider_x or first(query, "security") == "reality":
        reality: dict[str, Any] = {}
        if public_key:
            reality["public-key"] = public_key
        if short_id:
            reality["short-id"] = short_id
        if spider_x:
            reality["spider-x"] = spider_x
        node["reality-opts"] = reality

    network = (first(query, "type", "network") or "tcp").lower()
    if network == "ws":
        ws: dict[str, Any] = {}
        path = first(query, "path")
        host = first(query, "host")
        if path:
            ws["path"] = path
        if host:
            ws["headers"] = {"Host": host}
        if ws:
            node["ws-opts"] = ws
    elif network == "grpc":
        service_name = first(query, "serviceName", "serviceName")
        if service_name:
            node["grpc-opts"] = {"grpc-service-name": service_name}
    elif network in {"h2", "http"}:
        http: dict[str, Any] = {}
        path = first(query, "path")
        host = first(query, "host")
        if path:
            http["path"] = [path]
        if host:
            http["headers"] = {"Host": [host]}
        if http:
            node["http-opts"] = http
    return node


def decode_source(path: Path) -> list[dict[str, Any]]:
    try:
        decoded = base64.b64decode(path.read_bytes().strip(), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"invalid Base64/UTF-8 source: {path}: {exc}") from exc
    nodes = []
    for line in decoded.splitlines():
        node = parse_link(line)
        if node:
            nodes.append(node)
    return nodes


def unique_name(name: str, used: set[str]) -> str:
    if name not in used:
        return name
    index = 2
    while f"{name} {index}" in used:
        index += 1
    return f"{name} {index}"


def node_key(item: dict[str, Any]) -> tuple[Any, ...]:
    """Identify a node without collapsing distinct accounts on one endpoint."""
    return (
        item.get("type"),
        item.get("server"),
        item.get("port"),
        item.get("uuid"),
        item.get("password"),
        item.get("sni") or item.get("servername"),
        item.get("ports"),
    )


def merge(source: Path, config: Path) -> tuple[int, int]:
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"generated config root must be a mapping: {config}")
    proxies = data.setdefault("proxies", [])
    groups = data.setdefault("proxy-groups", [])
    if not isinstance(proxies, list) or not isinstance(groups, list):
        raise ValueError(f"generated config has invalid proxies/proxy-groups: {config}")

    used_names = {item.get("name") for item in proxies if isinstance(item, dict) and item.get("name")}
    existing_keys = {
        node_key(item)
        for item in proxies
        if isinstance(item, dict)
    }
    added: list[dict[str, Any]] = []
    for node in decode_source(source):
        key = node_key(node)
        if key in existing_keys:
            continue
        node["name"] = unique_name(node["name"], used_names)
        used_names.add(node["name"])
        existing_keys.add(key)
        added.append(node)
    proxies.extend(added)

    added_names = [node["name"] for node in added]
    if added_names:
        preferred = ["🚀 节点选择", "♻️ 自动选择"]
        target_groups = [
            group for group in groups
            if isinstance(group, dict) and group.get("name") in preferred
        ]
        if not target_groups:
            target_groups = [group for group in groups if isinstance(group, dict) and group.get("type") == "select"][:1]
        for group in target_groups:
            refs = group.setdefault("proxies", [])
            if not isinstance(refs, list):
                raise ValueError(f"proxy group has invalid proxies list: {group.get('name')}")
            for name in added_names:
                if name not in refs:
                    refs.append(name)

    config.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    return len(added), len(proxies)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    added, total = merge(args.source, args.config)
    print(f"Merged {added} Hysteria2/VLESS nodes into {args.config}; total proxies={total}")


if __name__ == "__main__":
    main()
