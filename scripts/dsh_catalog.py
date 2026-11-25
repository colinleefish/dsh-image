#!/usr/bin/env python3
"""Published / skipped dsh-image catalog.

images.json is the machine record. IMAGES.md is the human directory
(newest semver first). Timed publishes never rebuild a version already
in published; failed builds go to skipped.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_JSON = ROOT / "images.json"
CATALOG_MD = ROOT / "IMAGES.md"
DEFAULT_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$")
TAG_PREFIX = "dsh-v"
REPO = "colinleefish/dsh-image"


class CatalogError(Exception):
    """Catalog or plan inputs cannot be used."""


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


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def empty_catalog() -> dict:
    return {"published": [], "skipped": []}


def load_catalog(path: Path | None = None) -> dict:
    path = path or CATALOG_JSON
    if not path.exists():
        return empty_catalog()
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise CatalogError(f"{path} must be an object")
    published = list(data.get("published") or [])
    skipped = list(data.get("skipped") or [])
    return {"published": published, "skipped": skipped}


def published_versions(catalog: dict) -> list[str]:
    return [str(row["version"]) for row in catalog.get("published") or [] if "version" in row]


def skipped_versions(catalog: dict) -> list[str]:
    return [str(row["version"]) for row in catalog.get("skipped") or [] if "version" in row]


def highest_published(catalog: dict) -> str:
    versions = published_versions(catalog)
    if not versions:
        raise CatalogError("published catalog is empty")
    return max(versions, key=version_key)


def sort_catalog(catalog: dict) -> dict:
    published = sorted(
        catalog.get("published") or [],
        key=lambda row: version_key(str(row["version"])),
        reverse=True,
    )
    skipped = sorted(
        catalog.get("skipped") or [],
        key=lambda row: version_key(str(row["version"])),
        reverse=True,
    )
    return {"published": published, "skipped": skipped}


def render_markdown(catalog: dict) -> str:
    catalog = sort_catalog(catalog)
    lines = [
        "# 已发布镜像",
        "",
        "镜像 tag 与 [`@deepseek-ai/dsh`](https://www.npmjs.com/package/@deepseek-ai/dsh) 的 npm 版本相同。**最新版本在最前面**。",
        "",
        "```bash",
        f"docker pull registry.cn-beijing.aliyuncs.com/{REPO}:<版本>",
        f"docker pull docker.io/{REPO}:<版本>",
        "```",
        "",
        "| 版本 | ACR digest | Docker Hub digest | 构建 commit | 发布于 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in catalog["published"]:
        version = row["version"]
        git = str(row.get("git") or "")
        short = git[:7] if git else ""
        git_cell = f"[`{short}`](https://github.com/{REPO}/commit/{git})" if git else ""
        lines.append(
            "| `{version}` | `{acr}` | `{dockerhub}` | {git} | {when} |".format(
                version=version,
                acr=row.get("acr") or "",
                dockerhub=row.get("dockerhub") or "",
                git=git_cell,
                when=row.get("published_at") or "",
            )
        )
    skipped = catalog["skipped"]
    lines.extend(["", "## 跳过", ""])
    if not skipped:
        lines.append("无。构建失败的版本会记在这里，定时任务不会再打。")
    else:
        lines.extend(
            [
                "这些版本构建失败，定时任务不会再打。从 `images.json` 删掉后，用 Actions 手动指定该版本才会再试。",
                "",
                "| 版本 | 原因 | 记录于 |",
                "| --- | --- | --- |",
            ]
        )
        for row in skipped:
            reason = str(row.get("reason") or "").replace("|", "\\|")
            lines.append(
                "| `{version}` | {reason} | {when} |".format(
                    version=row["version"],
                    reason=reason,
                    when=row.get("failed_at") or "",
                )
            )
    lines.append("")
    return "\n".join(lines)


def save_catalog(catalog: dict, json_path: Path | None = None, md_path: Path | None = None) -> dict:
    json_path = json_path or CATALOG_JSON
    md_path = md_path or CATALOG_MD
    catalog = sort_catalog(catalog)
    json_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
    md_path.write_text(render_markdown(catalog))
    return catalog


def upsert_published(
    catalog: dict,
    *,
    version: str,
    git: str,
    dockerhub: str,
    acr: str,
    published_at: str | None = None,
) -> dict:
    skipped = [row for row in catalog.get("skipped") or [] if str(row.get("version")) != version]
    published = [row for row in catalog.get("published") or [] if str(row.get("version")) != version]
    published.append(
        {
            "version": version,
            "git": git,
            "dockerhub": dockerhub,
            "acr": acr,
            "published_at": published_at or utc_now(),
        }
    )
    return save_catalog({"published": published, "skipped": skipped})


def upsert_skipped(catalog: dict, *, version: str, reason: str, failed_at: str | None = None) -> dict:
    if any(str(row.get("version")) == version for row in catalog.get("published") or []):
        raise CatalogError(f"{version} is already published; not adding to skipped")
    skipped = [row for row in catalog.get("skipped") or [] if str(row.get("version")) != version]
    skipped.append(
        {
            "version": version,
            "reason": reason.replace("\n", " ").strip() or "build failed",
            "failed_at": failed_at or utc_now(),
        }
    )
    return save_catalog({"published": list(catalog.get("published") or []), "skipped": skipped})


def strip_upstream(name: str, pattern: re.Pattern[str] = DEFAULT_PATTERN) -> str | None:
    raw = name.strip()
    if not raw.startswith(TAG_PREFIX):
        return None
    version = raw[len(TAG_PREFIX) :]
    if pattern.fullmatch(version):
        return version
    return None


def read_upstream(path: Path, pattern: re.Pattern[str] = DEFAULT_PATTERN) -> set[str]:
    versions: set[str] = set()
    for line in path.read_text().splitlines():
        version = strip_upstream(line, pattern)
        if version is not None:
            versions.add(version)
    return versions


def plan(
    *,
    upstream: set[str],
    catalog: dict,
    main_pin: str,
    force: str = "",
    force_rebuild: bool = False,
    pattern: re.Pattern[str] = DEFAULT_PATTERN,
) -> dict[str, str]:
    """Pick at most one version to publish.

    Scheduled runs publish the lowest upstream version that is newer than
    the highest published image, is not skipped, and is not already published.
    """
    if pattern.fullmatch(main_pin) is None:
        raise CatalogError(f"main pin is not a dsh version: {main_pin}")
    if not upstream:
        raise CatalogError("upstream tag list is empty")
    for version in published_versions(catalog) + skipped_versions(catalog) + [main_pin]:
        if pattern.fullmatch(version) is None:
            raise CatalogError(f"not a dsh version: {version}")

    published = set(published_versions(catalog))
    skipped = set(skipped_versions(catalog))
    floor = highest_published(catalog) if published else main_pin

    if force:
        if pattern.fullmatch(force) is None:
            raise CatalogError(f"not a dsh version: {force}")
        if force not in upstream:
            raise CatalogError(f"upstream has no tag {TAG_PREFIX}{force}")
        if force in published and not force_rebuild:
            return _none(force, f"{force} is already published")
        bump = version_key(force) > version_key(main_pin)
        action = "rebuild" if force in published else "publish"
        return {
            "action": action,
            "version": force,
            "bump_pin": "true" if bump else "false",
            "reason": f"{action} {force}",
        }

    newer = [
        version
        for version in upstream
        if version_key(version) > version_key(floor)
        and version not in published
        and version not in skipped
    ]
    if not newer:
        return _none("", f"no upstream version newer than {floor}")
    target = min(newer, key=version_key)
    bump = version_key(target) > version_key(main_pin)
    return {
        "action": "publish",
        "version": target,
        "bump_pin": "true" if bump else "false",
        "reason": f"publish {target} (newer than {floor})",
    }


def _none(version: str, reason: str) -> dict[str, str]:
    return {
        "action": "none",
        "version": version,
        "bump_pin": "false",
        "reason": reason.replace("\n", " "),
    }


def _write_github_output(path: str, values: dict[str, str]) -> None:
    with Path(path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def _cmd_plan(args: argparse.Namespace) -> int:
    pattern = re.compile(args.pattern)
    catalog = load_catalog(Path(args.catalog) if args.catalog else CATALOG_JSON)
    chosen = plan(
        upstream=read_upstream(Path(args.upstream_file), pattern),
        catalog=catalog,
        main_pin=args.main_version,
        force=args.force,
        force_rebuild=args.force_rebuild == "true",
        pattern=pattern,
    )
    chosen["dry_run"] = "true" if args.dry_run == "true" else "false"
    print(
        "action={action} version={version} bump_pin={bump_pin} dry_run={dry_run}".format(
            **chosen
        )
    )
    print(chosen["reason"])
    if args.github_output:
        _write_github_output(args.github_output, chosen)
    return 0


def _cmd_record(args: argparse.Namespace) -> int:
    catalog = load_catalog()
    upsert_published(
        catalog,
        version=args.version,
        git=args.git,
        dockerhub=args.dockerhub,
        acr=args.acr,
        published_at=args.published_at or None,
    )
    print(f"recorded {args.version}")
    return 0


def _cmd_skip(args: argparse.Namespace) -> int:
    catalog = load_catalog()
    upsert_skipped(catalog, version=args.version, reason=args.reason)
    print(f"skipped {args.version}")
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    save_catalog(load_catalog())
    print(f"wrote {CATALOG_MD}")
    return 0


def _cmd_assert_pin(args: argparse.Namespace) -> int:
    highest = highest_published(load_catalog())
    if highest != args.version:
        print(
            f"catalog highest {highest} does not match pin {args.version}",
            file=sys.stderr,
        )
        return 1
    print(f"catalog highest ok: {highest}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    plan_p = sub.add_parser("plan")
    plan_p.add_argument("--upstream-file", required=True)
    plan_p.add_argument("--main-version", required=True)
    plan_p.add_argument("--catalog", default="")
    plan_p.add_argument("--force", default="")
    plan_p.add_argument("--force-rebuild", default="false")
    plan_p.add_argument("--pattern", default=DEFAULT_PATTERN.pattern)
    plan_p.add_argument("--dry-run", default="false")
    plan_p.add_argument("--github-output", default="")
    plan_p.set_defaults(func=_cmd_plan)

    rec = sub.add_parser("record")
    rec.add_argument("--version", required=True)
    rec.add_argument("--git", required=True)
    rec.add_argument("--dockerhub", required=True)
    rec.add_argument("--acr", required=True)
    rec.add_argument("--published-at", default="")
    rec.set_defaults(func=_cmd_record)

    sk = sub.add_parser("skip")
    sk.add_argument("--version", required=True)
    sk.add_argument("--reason", required=True)
    sk.set_defaults(func=_cmd_skip)

    rend = sub.add_parser("render")
    rend.set_defaults(func=_cmd_render)

    pin = sub.add_parser("assert-pin")
    pin.add_argument("version")
    pin.set_defaults(func=_cmd_assert_pin)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (CatalogError, json.JSONDecodeError, OSError, re.error, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
