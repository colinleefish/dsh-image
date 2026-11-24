#!/usr/bin/env python3
"""Unit tests for scripts/plan_dsh_sync.py."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "plan_dsh_sync", ROOT / "scripts" / "plan_dsh_sync.py"
)
assert SPEC is not None and SPEC.loader is not None
plan_dsh_sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plan_dsh_sync)

plan = plan_dsh_sync.plan
version_key = plan_dsh_sync.version_key
SyncError = plan_dsh_sync.SyncError


UPSTREAM = {
    "0.2.3-alpha.2",
    "0.2.3-alpha.1",
    "0.2.2-rc.5",
    "0.2.2-rc.4",
    "0.2.2-rc.3",
    "0.2.2-rc.2",
    "0.2.2-rc.1",
    "0.2.2-alpha.3",
    "0.2.2-alpha.2",
    "0.2.1-rc.5",
    "0.1.7-rc.2",
}
OURS = {
    "0.2.3-alpha.2",
    "0.2.3-alpha.1",
    "0.2.2-rc.5",
    "0.2.2-rc.4",
    "0.2.2-rc.3",
    "0.2.2-rc.2",
}
RELEASED = OURS - {"0.2.3-alpha.1"}


def at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class VersionOrderTest(unittest.TestCase):
    def test_prerelease_order(self) -> None:
        ordered = [
            "0.1.7-rc.2",
            "0.2.1-rc.5",
            "0.2.2-alpha.2",
            "0.2.2-alpha.3",
            "0.2.2-rc.1",
            "0.2.2-rc.2",
            "0.2.2-rc.10",
            "0.2.2",
            "0.2.3-alpha.1",
            "0.2.3-alpha.2",
        ]
        self.assertEqual(ordered, sorted(ordered, key=version_key))


class CurrentRepoTest(unittest.TestCase):
    def test_repairs_main_up_to_highest_tag(self) -> None:
        chosen = plan(
            upstream=UPSTREAM,
            ours=OURS,
            released=RELEASED,
            main="0.2.2-rc.2",
        )
        self.assertEqual("repair-main", chosen.action)
        self.assertEqual("0.2.3-alpha.2", chosen.version)
        self.assertEqual("main", chosen.commit_mode)
        self.assertFalse(chosen.create_tag)
        self.assertFalse(chosen.dispatch_publish)

    def test_retries_unpublished_alpha_after_main_is_current(self) -> None:
        failed = at("2026-11-22T06:39:57Z")
        chosen = plan(
            upstream=UPSTREAM,
            ours=OURS,
            released=RELEASED,
            main="0.2.3-alpha.2",
            runs=[
                {
                    "headBranch": "dsh-v0.2.3-alpha.1",
                    "conclusion": "failure",
                    "status": "completed",
                    "createdAt": failed.isoformat(),
                }
            ],
            now=failed + timedelta(hours=12),
        )
        self.assertEqual("retry-publish", chosen.action)
        self.assertEqual("0.2.3-alpha.1", chosen.version)
        self.assertEqual("none", chosen.commit_mode)
        self.assertFalse(chosen.create_tag)
        self.assertTrue(chosen.dispatch_publish)

    def test_cooldown_lets_backfill_proceed(self) -> None:
        failed = at("2026-11-22T06:39:57Z")
        chosen = plan(
            upstream=UPSTREAM,
            ours=OURS,
            released=RELEASED,
            main="0.2.3-alpha.2",
            runs=[
                {
                    "headBranch": "dsh-v0.2.3-alpha.1",
                    "conclusion": "failure",
                    "status": "completed",
                    "createdAt": failed.isoformat(),
                }
            ],
            now=failed + timedelta(hours=12) - timedelta(seconds=1),
        )
        self.assertEqual("backfill", chosen.action)
        self.assertEqual("0.2.2-rc.1", chosen.version)
        self.assertEqual("detached", chosen.commit_mode)
        self.assertTrue(chosen.create_tag)
        self.assertTrue(chosen.dispatch_publish)


class AdvanceTest(unittest.TestCase):
    def test_takes_the_lowest_newer_version(self) -> None:
        chosen = plan(
            upstream=UPSTREAM | {"0.2.3-alpha.3", "0.2.3-alpha.4"},
            ours=OURS,
            released=RELEASED,
            main="0.2.3-alpha.2",
        )
        self.assertEqual("advance", chosen.action)
        self.assertEqual("0.2.3-alpha.3", chosen.version)
        self.assertEqual("main", chosen.commit_mode)
        self.assertTrue(chosen.create_tag)
        self.assertTrue(chosen.dispatch_publish)


class FinishCurrentTest(unittest.TestCase):
    def test_tags_when_pin_matches_but_tag_push_was_lost(self) -> None:
        chosen = plan(
            upstream={"0.2.2-rc.2", "0.2.2-rc.1"},
            ours=set(),
            released=set(),
            main="0.2.2-rc.2",
        )
        self.assertEqual("finish-current", chosen.action)
        self.assertEqual("0.2.2-rc.2", chosen.version)
        self.assertEqual("none", chosen.commit_mode)
        self.assertTrue(chosen.create_tag)
        self.assertTrue(chosen.dispatch_publish)

    def test_nothing_left(self) -> None:
        chosen = plan(
            upstream={"0.2.2-rc.2"},
            ours={"0.2.2-rc.2"},
            released={"0.2.2-rc.2"},
            main="0.2.2-rc.2",
        )
        self.assertEqual("none", chosen.action)


class ForceTest(unittest.TestCase):
    def test_force_older_version_stays_off_main(self) -> None:
        chosen = plan(
            upstream=UPSTREAM,
            ours=OURS,
            released=RELEASED,
            main="0.2.3-alpha.2",
            force="0.2.2-rc.1",
        )
        self.assertEqual("backfill", chosen.action)
        self.assertEqual("detached", chosen.commit_mode)

    def test_force_newer_version_moves_main(self) -> None:
        chosen = plan(
            upstream=UPSTREAM | {"0.2.3-alpha.4"},
            ours=OURS,
            released=RELEASED,
            main="0.2.3-alpha.2",
            force="0.2.3-alpha.4",
        )
        self.assertEqual("advance", chosen.action)
        self.assertEqual("0.2.3-alpha.4", chosen.version)

    def test_force_unknown_version_errors(self) -> None:
        with self.assertRaises(SyncError):
            plan(
                upstream=UPSTREAM,
                ours=OURS,
                released=RELEASED,
                main="0.2.3-alpha.2",
                force="9.9.9",
            )

    def test_force_retries_even_inside_cooldown(self) -> None:
        failed = at("2026-11-22T06:39:57Z")
        chosen = plan(
            upstream=UPSTREAM,
            ours=OURS,
            released=RELEASED,
            main="0.2.3-alpha.2",
            force="0.2.3-alpha.1",
            runs=[
                {
                    "headBranch": "dsh-v0.2.3-alpha.1",
                    "conclusion": "failure",
                    "status": "completed",
                    "createdAt": failed.isoformat(),
                }
            ],
            now=failed + timedelta(minutes=5),
        )
        self.assertEqual("retry-publish", chosen.action)
        self.assertTrue(chosen.dispatch_publish)


class RunIndexTest(unittest.TestCase):
    def test_newer_success_clears_an_older_failure(self) -> None:
        chosen = plan(
            upstream=UPSTREAM,
            ours=OURS,
            released=RELEASED | {"0.2.3-alpha.1"},
            main="0.2.3-alpha.2",
            runs=[
                {
                    "headBranch": "dsh-v0.2.3-alpha.1",
                    "conclusion": "failure",
                    "status": "completed",
                    "createdAt": "2026-11-22T06:39:57Z",
                },
                {
                    "headBranch": "dsh-v0.2.3-alpha.1",
                    "conclusion": "success",
                    "status": "completed",
                    "createdAt": "2026-11-22T08:00:00Z",
                },
            ],
            now=at("2026-11-22T09:00:00Z"),
        )
        self.assertEqual("backfill", chosen.action)

    def test_inflight_publish_does_not_block_backfill(self) -> None:
        chosen = plan(
            upstream=UPSTREAM,
            ours=OURS,
            released=RELEASED,
            main="0.2.3-alpha.2",
            runs=[
                {
                    "headBranch": "dsh-v0.2.3-alpha.1",
                    "conclusion": "",
                    "status": "in_progress",
                    "createdAt": "2026-11-23T00:00:00Z",
                }
            ],
            now=at("2026-11-23T00:10:00Z"),
        )
        self.assertEqual("backfill", chosen.action)
        self.assertEqual("0.2.2-rc.1", chosen.version)


class CliTest(unittest.TestCase):
    def test_strips_dsh_prefix_and_ignores_other_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "upstream.txt").write_text(
                "dsh-v0.2.2-rc.2\ndsh-v0.2.2-rc.1\nimage-v0.2.2-rc.1-r4\n"
            )
            (directory / "ours.txt").write_text("dsh-v0.2.2-rc.2\n")
            (directory / "releases.txt").write_text("dsh-v0.2.2-rc.2\n")
            (directory / "runs.json").write_text("[]")
            output = directory / "github.out"
            code = plan_dsh_sync.main(
                [
                    "--upstream-file",
                    str(directory / "upstream.txt"),
                    "--ours-file",
                    str(directory / "ours.txt"),
                    "--releases-file",
                    str(directory / "releases.txt"),
                    "--runs-json",
                    str(directory / "runs.json"),
                    "--main-version",
                    "0.2.2-rc.2",
                    "--github-output",
                    str(output),
                    "--dry-run",
                    "true",
                ]
            )
            self.assertEqual(0, code)
            text = output.read_text()
            self.assertIn("action=backfill", text)
            self.assertIn("version=0.2.2-rc.1", text)
            self.assertIn("dry_run=true", text)

    def test_empty_upstream_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for name in ("upstream.txt", "ours.txt", "releases.txt"):
                (directory / name).write_text("")
            (directory / "runs.json").write_text(json.dumps([]))
            code = plan_dsh_sync.main(
                [
                    "--upstream-file",
                    str(directory / "upstream.txt"),
                    "--ours-file",
                    str(directory / "ours.txt"),
                    "--releases-file",
                    str(directory / "releases.txt"),
                    "--runs-json",
                    str(directory / "runs.json"),
                    "--main-version",
                    "0.2.2-rc.2",
                ]
            )
            self.assertEqual(1, code)


if __name__ == "__main__":
    unittest.main()
