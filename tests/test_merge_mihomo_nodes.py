import base64
import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml


SCRIPT = Path(__file__).parents[1] / "scripts" / "merge_mihomo_nodes.py"
SPEC = importlib.util.spec_from_file_location("merge_mihomo_nodes", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

DISCOVER_SCRIPT = Path(__file__).parents[1] / "scripts" / "discover_sources.py"
DISCOVER_SPEC = importlib.util.spec_from_file_location("discover_sources", DISCOVER_SCRIPT)
DISCOVER = importlib.util.module_from_spec(DISCOVER_SPEC)
assert DISCOVER_SPEC.loader is not None
DISCOVER_SPEC.loader.exec_module(DISCOVER)

PRUNE_SCRIPT = Path(__file__).parents[1] / "scripts" / "prune_generated_configs.py"
PRUNE_SPEC = importlib.util.spec_from_file_location("prune_generated_configs", PRUNE_SCRIPT)
PRUNE = importlib.util.module_from_spec(PRUNE_SPEC)
assert PRUNE_SPEC.loader is not None
PRUNE_SPEC.loader.exec_module(PRUNE)


class ParseLinkTests(unittest.TestCase):
    def test_hysteria2_query_options_are_mapped(self):
        node = MODULE.parse_link(
            "hysteria2://pass@example.com:443?"
            "sni=edge.example.com&insecure=1&obfs=salamander&"
            "obfs-password=secret&alpn=h3,h2#Tokyo"
        )
        self.assertEqual(node["name"], "Tokyo")
        self.assertEqual(node["type"], "hysteria2")
        self.assertTrue(node["skip-cert-verify"])
        self.assertEqual(node["alpn"], ["h3", "h2"])

    def test_vless_websocket_and_reality_options_are_mapped(self):
        node = MODULE.parse_link(
            "vless://uuid@example.com:443?security=reality&pbk=key&sid=id&"
            "type=ws&path=%2Fproxy&host=cdn.example.com#VLESS"
        )
        self.assertEqual(node["uuid"], "uuid")
        self.assertTrue(node["tls"])
        self.assertEqual(node["reality-opts"]["public-key"], "key")
        self.assertEqual(node["ws-opts"]["headers"]["Host"], "cdn.example.com")

    def test_malformed_port_is_skipped(self):
        self.assertIsNone(MODULE.parse_link("vless://uuid@example.com:not-a-port#bad"))


class MergeTests(unittest.TestCase):
    def test_wrapped_base64_and_duplicate_names(self):
        links = "\n".join(
            [
                "vless://one@example.com:443#same",
                "vless://two@example.com:443#same",
            ]
        ).encode()
        wrapped = base64.encodebytes(links)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            config = root / "config.yaml"
            source.write_bytes(wrapped)
            config.write_text(
                yaml.safe_dump(
                    {
                        "proxies": [],
                        "proxy-groups": [
                            {"name": "🚀 节点选择", "type": "select", "proxies": []}
                        ],
                        "rules": ["MATCH,🚀 节点选择"],
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            added, total = MODULE.merge(source, config)
            data = yaml.safe_load(config.read_text(encoding="utf-8"))
        self.assertEqual((added, total), (2, 2))
        self.assertEqual([p["name"] for p in data["proxies"]], ["same", "same 2"])
        self.assertIn("same 2", data["proxy-groups"][0]["proxies"])


class DiscoverSourceTests(unittest.TestCase):
    def test_discovers_new_root_source_and_ignores_invalid_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = base64.b64encode(b"vless://uuid@example.com:443#new\n")
            (root / "NEW001").write_bytes(payload)
            (root / "README").write_text("not a subscription", encoding="utf-8")
            (root / "with space").write_bytes(payload)
            (root / "existing.yaml").write_bytes(payload)
            (root / ".hidden").write_bytes(payload)
            (root / "scripts").mkdir()
            self.assertEqual(DISCOVER.discover(root), ["NEW001"])


class PruneGeneratedConfigTests(unittest.TestCase):
    def test_removes_only_yaml_without_a_current_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "KEEP.yaml").write_text("keep", encoding="utf-8")
            (root / "STALE.yaml").write_text("stale", encoding="utf-8")
            (root / "notes.txt").write_text("keep", encoding="utf-8")
            removed = PRUNE.prune(root, {"KEEP"})
            self.assertEqual(removed, ["STALE.yaml"])
            self.assertTrue((root / "KEEP.yaml").exists())
            self.assertTrue((root / "notes.txt").exists())


if __name__ == "__main__":
    unittest.main()
