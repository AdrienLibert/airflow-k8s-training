#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def list_tags(image_name: str) -> list[str]:
    result = subprocess.run(
        ["docker", "images", image_name, "--format", "{{.Tag}}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [
        tag
        for tag in (line.strip() for line in result.stdout.splitlines())
        if tag and tag != "<none>"
    ]


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
    parser = argparse.ArgumentParser(description="Compute next semver from Docker image tags")
    parser.add_argument("level", choices=["patch", "minor", "major"])
    parser.add_argument("--image-name", default="hello-world-tasks")
    args = parser.parse_args()

    tags = list_tags(args.image_name)
    next_tag = format_semver(bump(latest_semver(tags), args.level))
    print(next_tag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
