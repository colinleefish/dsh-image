#!/usr/bin/env python3
"""Pick one dsh-image sync action.

main only moves forward. Older missing tags are built from a detached commit.
A missing git tag or GitHub Release is retried even when the pin already matches.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$")
TAG_PREFIX = "dsh-v"
COOLDOWN = timedelta(hours=12)


class SyncError(Exception):
    """The inputs cannot produce a plan."""


@dataclass(frozen=True)
class Plan:
    action: str
    version: str = ""
    commit_mode: str = "none"
    create_tag: bool = False
    dispatch_publish: bool = False
    reason: str = ""

    def as_output(self) -> dict[str, str]:
        return {
            "action": self.action,
            "version": self.version,
            "commit_mode": self.commit_mode,
            "create_tag": "true" if self.create_tag else "false",
            "dispatch_publish": "true" if self.dispatch_publish else "false",
            "reason": self.reason.replace("\n", " "),
        }


def version_key(version: str) -> tuple:
    """Semver key. A release sorts after prereleases of the same core version."""
    main, sep, pre = version.partition("-")
    numbers = tuple(int(part) for part in main.split("."))
    if not sep:
        return (numbers, 1, ())
    idents: list[tuple[int, int | str]] = []
    for part in pre.split("."):
        if part.isdigit():
            idents.append((0, int(part)))
        else:
            idents.append((1, part))
    return (numbers, 0, tuple(idents))


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def strip_version(name: str, pattern: re.Pattern[str]) -> str | None:
    version = name[len(TAG_PREFIX) :] if name.startswith(TAG_PREFIX) else name
    if name.startswith(TAG_PREFIX) and pattern.fullmatch(version):
        return version
    if pattern.fullmatch(name):
        return name
    return None


def read_versions(path: str, pattern: re.Pattern[str]) -> set[str]:
    versions: set[str] = set()
    for line in Path(path).read_text().splitlines():
        name = line.strip()
        if not name:
            continue
        version = strip_version(name, pattern)
        if version is not None:
            versions.add(version)
    return versions


def index_runs(
    runs: list[dict], pattern: re.Pattern[str] = DEFAULT_PATTERN
) -> tuple[dict[str, datetime], set[str]]:
    """Return the latest failure time per version, and versions with a run still going."""
    newest: dict[str, tuple[datetime, dict]] = {}
    for run in runs:
        branch = str(run.get("headBranch") or "")
        if not branch.startswith(TAG_PREFIX):
            continue
        version = branch[len(TAG_PREFIX) :]
        if pattern.fullmatch(version) is None:
            continue
        created = parse_time(str(run["createdAt"]))
        previous = newest.get(version)
        if previous is None or created > previous[0]:
            newest[version] = (created, run)

    failures: dict[str, datetime] = {}
    inflight: set[str] = set()
    for version, (created, run) in newest.items():
        status = str(run.get("status") or "")
        if not status and run.get("conclusion"):
            status = "completed"
        if status != "completed":
            inflight.add(version)
            continue
        if run.get("conclusion") == "failure":
            failures[version] = created
    return failures, inflight


def _frontier(main: str, ours: set[str]) -> str:
    best = main
    for version in ours:
        if version_key(version) > version_key(best):
            best = version
    return best


def _can_dispatch(
    version: str,
    *,
    failures: dict[str, datetime],
    inflight: set[str],
    now: datetime,
    cooldown: timedelta,
    ignore_cooldown: bool,
) -> bool:
    if version in inflight:
        return False
    if ignore_cooldown:
        return True
    failed_at = failures.get(version)
    if failed_at is None:
        return True
    return now - failed_at >= cooldown


def _finish(
    version: str,
    *,
    upstream: set[str],
    ours: set[str],
    released: set[str],
    failures: dict[str, datetime],
    inflight: set[str],
    now: datetime,
    cooldown: timedelta,
    ignore_cooldown: bool,
    action: str,
) -> Plan | None:
    needs_tag = version in upstream and version not in ours
    needs_release = version not in released and (version in ours or needs_tag)
    if not needs_tag and not needs_release:
        return None
    dispatch = needs_release and _can_dispatch(
        version,
        failures=failures,
        inflight=inflight,
        now=now,
        cooldown=cooldown,
        ignore_cooldown=ignore_cooldown,
    )
    if needs_release and not dispatch and not needs_tag:
        return None
    if needs_tag and not needs_release:
        reason = f"tag dsh-v{version} is missing"
    elif needs_tag and dispatch:
        reason = f"tag and image for {version} are missing"
    elif dispatch:
        reason = f"tag dsh-v{version} has no published image"
    else:
        reason = f"tag dsh-v{version} is missing; image publish is waiting"
        dispatch = False
    return Plan(
        action=action,
        version=version,
        commit_mode="none",
        create_tag=needs_tag,
        dispatch_publish=dispatch,
        reason=reason,
    )


def plan(
    *,
    upstream: set[str],
    ours: set[str],
    released: set[str],
    main: str,
    runs: list[dict] | None = None,
    force: str = "",
    now: datetime | None = None,
    cooldown: timedelta = COOLDOWN,
    pattern: re.Pattern[str] = DEFAULT_PATTERN,
) -> Plan:
    """Choose the single action for this run.

    1. Advance main to the lowest upstream version above the frontier.
    2. Move main forward when its pin is behind the frontier.
    3. Finish the main pin when its tag or release is missing.
    4. Republish the highest other tag that has no release.
    5. Backfill the highest older missing tag off main.
    """
    if not upstream:
        raise SyncError("upstream tag list is empty")
    if pattern.fullmatch(main) is None:
        raise SyncError(f"main pin is not a dsh version: {main}")
    for version in ours | released | upstream:
        if pattern.fullmatch(version) is None:
            raise SyncError(f"not a dsh version: {version}")

    moment = now or datetime.now(timezone.utc)
    failures, inflight = index_runs(runs or [], pattern)
    frontier = _frontier(main, ours)

    if force:
        if pattern.fullmatch(force) is None:
            raise SyncError(f"not a dsh version: {force}")
        if force not in upstream:
            raise SyncError(f"upstream has no tag dsh-v{force}")
        return _plan_force(
            force,
            main=main,
            upstream=upstream,
            ours=ours,
            released=released,
            failures=failures,
            inflight=inflight,
            now=moment,
            cooldown=cooldown,
        )

    newer = sorted(
        (version for version in upstream if version_key(version) > version_key(frontier)),
        key=version_key,
    )
    if newer:
        version = newer[0]
        return Plan(
            action="advance",
            version=version,
            commit_mode="main",
            create_tag=True,
            dispatch_publish=True,
            reason=f"advance main from {main} to {version}",
        )

    if version_key(main) < version_key(frontier):
        dispatch = frontier not in released and _can_dispatch(
            frontier,
            failures=failures,
            inflight=inflight,
            now=moment,
            cooldown=cooldown,
            ignore_cooldown=False,
        )
        return Plan(
            action="repair-main",
            version=frontier,
            commit_mode="main",
            create_tag=False,
            dispatch_publish=dispatch,
            reason=f"move main pin forward from {main} to {frontier}",
        )

    current = _finish(
        main,
        upstream=upstream,
        ours=ours,
        released=released,
        failures=failures,
        inflight=inflight,
        now=moment,
        cooldown=cooldown,
        ignore_cooldown=False,
        action="finish-current",
    )
    if current is not None:
        return current

    retries = sorted(
        (version for version in ours if version not in released and version != main),
        key=version_key,
        reverse=True,
    )
    for version in retries:
        chosen = _finish(
            version,
            upstream=upstream,
            ours=ours,
            released=released,
            failures=failures,
            inflight=inflight,
            now=moment,
            cooldown=cooldown,
            ignore_cooldown=False,
            action="retry-publish",
        )
        if chosen is not None:
            return chosen

    missing = sorted(
        (
            version
            for version in upstream
            if version not in ours and version_key(version) < version_key(frontier)
        ),
        key=version_key,
        reverse=True,
    )
    if missing:
        version = missing[0]
        return Plan(
            action="backfill",
            version=version,
            commit_mode="detached",
            create_tag=True,
            dispatch_publish=True,
            reason=f"backfill {version} off main",
        )

    if retries:
        return Plan(action="none", reason="image republish is in cooldown")
    return Plan(action="none", reason="every upstream tag is tagged and published")


def _plan_force(
    version: str,
    *,
    main: str,
    upstream: set[str],
    ours: set[str],
    released: set[str],
    failures: dict[str, datetime],
    inflight: set[str],
    now: datetime,
    cooldown: timedelta,
) -> Plan:
    if version in inflight:
        return Plan(action="none", version=version, reason=f"publish for {version} is already running")

    if version_key(version) > version_key(main):
        return Plan(
            action="advance",
            version=version,
            commit_mode="main",
            create_tag=version not in ours,
            dispatch_publish=version not in released,
            reason=f"force-advance main from {main} to {version}",
        )

    if version_key(version) == version_key(main):
        chosen = _finish(
            version,
            upstream=upstream,
            ours=ours,
            released=released,
            failures=failures,
            inflight=inflight,
            now=now,
            cooldown=cooldown,
            ignore_cooldown=True,
            action="finish-current",
        )
        if chosen is not None:
            return chosen
        return Plan(action="none", version=version, reason=f"{version} is already tagged and published")

    if version not in ours:
        return Plan(
            action="backfill",
            version=version,
            commit_mode="detached",
            create_tag=True,
            dispatch_publish=True,
            reason=f"force-backfill {version} off main",
        )
    chosen = _finish(
        version,
        upstream=upstream,
        ours=ours,
        released=released,
        failures=failures,
        inflight=inflight,
        now=now,
        cooldown=cooldown,
        ignore_cooldown=True,
        action="retry-publish",
    )
    if chosen is not None:
        return chosen
    return Plan(action="none", version=version, reason=f"{version} is already tagged and published")


def _write_github_output(path: str, values: dict[str, str]) -> None:
    with Path(path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-file", required=True)
    parser.add_argument("--ours-file", required=True)
    parser.add_argument("--releases-file", required=True)
    parser.add_argument("--runs-json", required=True)
    parser.add_argument("--main-version", required=True)
    parser.add_argument("--force", default="")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN.pattern)
    parser.add_argument("--now", default="")
    parser.add_argument("--cooldown-hours", type=float, default=12)
    parser.add_argument("--dry-run", default="false")
    parser.add_argument("--github-output", default="")
    args = parser.parse_args(argv)

    try:
        pattern = re.compile(args.pattern)
    except re.error as exc:
        print(f"invalid TAG_SUFFIX_PATTERN: {exc}", file=sys.stderr)
        return 1

    try:
        runs = json.loads(Path(args.runs_json).read_text() or "[]")
        moment = parse_time(args.now) if args.now else datetime.now(timezone.utc)
        chosen = plan(
            upstream=read_versions(args.upstream_file, pattern),
            ours=read_versions(args.ours_file, pattern),
            released=read_versions(args.releases_file, pattern),
            main=args.main_version,
            runs=runs,
            force=args.force,
            now=moment,
            cooldown=timedelta(hours=args.cooldown_hours),
            pattern=pattern,
        )
    except (SyncError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    output = chosen.as_output()
    output["dry_run"] = "true" if args.dry_run == "true" else "false"
    print(
        "action={action} version={version} commit_mode={commit_mode} "
        "create_tag={create_tag} dispatch_publish={dispatch_publish}".format(**output)
    )
    print(output["reason"])
    if args.github_output:
        _write_github_output(args.github_output, output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
