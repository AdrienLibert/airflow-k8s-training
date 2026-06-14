#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def list_tags(registry: str, repository: str) -> list[str]:
    url = f"http://{registry}/v2/{repository}/tags/list"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []
        raise
    tags = payload.get("tags")
    return tags if tags else []


def parse_semver(tag: str) -> tuple[int, int, int] | None:
    match = SEMVER.match(tag)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def latest_semver(tags: list[str]) -> tuple[int, int, int]:
    versions = [parsed for tag in tags if (parsed := parse_semver(tag))]
    return max(versions) if versions else (0, 0, 0)


def bump(version: tuple[int, int, int], level: str) -> tuple[int, int, int]:
    major, minor, patch = version
    if level == "patch":
        return major, minor, patch + 1
    if level == "minor":
        return major, minor + 1, 0
    if level == "major":
        return major + 1, 0, 0
    raise ValueError(f"unsupported bump level: {level}")


def format_semver(version: tuple[int, int, int]) -> str:
    return f"{version[0]}.{version[1]}.{version[2]}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute next semver from registry tags")
    parser.add_argument("level", choices=["patch", "minor", "major"])
    parser.add_argument("--registry", default="localhost:5000")
    parser.add_argument("--image-name", default="hello-world-tasks")
    args = parser.parse_args()

    tags = list_tags(args.registry, args.image_name)
    current = latest_semver(tags)
    if current == (0, 0, 0) and not tags:
        current = (0, 0, 0)
    next_tag = format_semver(bump(current, args.level))
    print(next_tag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
