#!/usr/bin/env python3
"""Tests for scripts/dsh_catalog.py."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("dsh_catalog", ROOT / "scripts" / "dsh_catalog.py")
assert SPEC is not None and SPEC.loader is not None
dsh_catalog = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dsh_catalog)

UPSTREAM = {
    "0.2.3-alpha.2",
    "0.2.3-alpha.1",
    "0.2.2-rc.5",
    "0.2.2-rc.4",
    "0.2.2-rc.3",
    "0.2.2-rc.2",
    "0.2.2-rc.1",
    "0.2.2-alpha.3",
    "0.2.1-rc.5",
}


def catalog_with(*published: str, skipped: tuple[str, ...] = ()) -> dict:
    return {
        "published": [{"version": version, "git": "abc", "dockerhub": "h", "acr": "a"} for version in published],
        "skipped": [{"version": version, "reason": "fail"} for version in skipped],
    }


class VersionOrderTest(unittest.TestCase):
    def test_newest_first(self) -> None:
        ordered = [
            "0.2.3-alpha.2",
            "0.2.3-alpha.1",
            "0.2.2-rc.5",
            "0.2.2-rc.2",
            "0.2.2-rc.1",
            "0.2.2-alpha.3",
            "0.2.1-rc.5",
        ]
        self.assertEqual(ordered, sorted(ordered, key=dsh_catalog.version_key, reverse=True))


class PlanTest(unittest.TestCase):
    def test_picks_lowest_newer_than_catalog(self) -> None:
        chosen = dsh_catalog.plan(
            upstream=UPSTREAM | {"0.2.3-alpha.3", "0.2.3-alpha.4"},
            catalog=catalog_with("0.2.3-alpha.2", "0.2.2-rc.5"),
            main_pin="0.2.3-alpha.2",
        )
        self.assertEqual("publish", chosen["action"])
        self.assertEqual("0.2.3-alpha.3", chosen["version"])
        self.assertEqual("true", chosen["bump_pin"])

    def test_skipped_does_not_block_later_version(self) -> None:
        chosen = dsh_catalog.plan(
            upstream=UPSTREAM | {"0.2.3-alpha.3", "0.2.3-alpha.4"},
            catalog=catalog_with("0.2.3-alpha.2", skipped=("0.2.3-alpha.3",)),
            main_pin="0.2.3-alpha.2",
        )
        self.assertEqual("0.2.3-alpha.4", chosen["version"])

    def test_does_not_backfill_older_missing_versions(self) -> None:
        chosen = dsh_catalog.plan(
            upstream=UPSTREAM,
            catalog=catalog_with("0.2.3-alpha.2"),
            main_pin="0.2.2-alpha.3",
        )
        self.assertEqual("none", chosen["action"])

    def test_already_published_is_not_rebuilt(self) -> None:
        chosen = dsh_catalog.plan(
            upstream=UPSTREAM,
            catalog=catalog_with("0.2.3-alpha.2"),
            main_pin="0.2.3-alpha.2",
            force="0.2.3-alpha.2",
        )
        self.assertEqual("none", chosen["action"])

    def test_force_rebuild_published(self) -> None:
        chosen = dsh_catalog.plan(
            upstream=UPSTREAM,
            catalog=catalog_with("0.2.3-alpha.2"),
            main_pin="0.2.3-alpha.2",
            force="0.2.3-alpha.2",
            force_rebuild=True,
        )
        self.assertEqual("rebuild", chosen["action"])
        self.assertEqual("false", chosen["bump_pin"])

    def test_force_older_unpublished_does_not_move_pin(self) -> None:
        chosen = dsh_catalog.plan(
            upstream=UPSTREAM,
            catalog=catalog_with("0.2.3-alpha.2"),
            main_pin="0.2.3-alpha.2",
            force="0.2.3-alpha.1",
        )
        self.assertEqual("publish", chosen["action"])
        self.assertEqual("false", chosen["bump_pin"])

    def test_force_unknown_version_errors(self) -> None:
        with self.assertRaises(dsh_catalog.CatalogError):
            dsh_catalog.plan(
                upstream=UPSTREAM,
                catalog=catalog_with("0.2.3-alpha.2"),
                main_pin="0.2.3-alpha.2",
                force="9.9.9",
            )


class CatalogWriteTest(unittest.TestCase):
    def test_record_sorts_newest_first_and_clears_skip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            json_path = directory / "images.json"
            md_path = directory / "IMAGES.md"
            dsh_catalog.CATALOG_JSON = json_path
            dsh_catalog.CATALOG_MD = md_path
            catalog = {
                "published": [
                    {
                        "version": "0.2.2-rc.5",
                        "git": "a",
                        "dockerhub": "h1",
                        "acr": "a1",
                        "published_at": "2026-11-19T13:20:16Z",
                    }
                ],
                "skipped": [{"version": "0.2.3-alpha.2", "reason": "fail", "failed_at": "x"}],
            }
            json_path.write_text(json.dumps(catalog))
            dsh_catalog.upsert_published(
                dsh_catalog.load_catalog(json_path),
                version="0.2.3-alpha.2",
                git="b" * 40,
                dockerhub="h2",
                acr="a2",
                published_at="2026-11-22T19:34:37Z",
            )
            saved = json.loads(json_path.read_text())
            self.assertEqual(
                ["0.2.3-alpha.2", "0.2.2-rc.5"],
                [row["version"] for row in saved["published"]],
            )
            self.assertEqual([], saved["skipped"])
            text = md_path.read_text()
            self.assertLess(text.index("0.2.3-alpha.2"), text.index("0.2.2-rc.5"))
            self.assertIn("无。", text)

    def test_skip_rejected_for_published_version(self) -> None:
        catalog = catalog_with("0.2.3-alpha.2")
        with self.assertRaises(dsh_catalog.CatalogError):
            dsh_catalog.upsert_skipped(catalog, version="0.2.3-alpha.2", reason="nope")


if __name__ == "__main__":
    unittest.main()
