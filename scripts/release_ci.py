import argparse
import os
from pathlib import Path
import re
import subprocess

from bundle_tools import ROOT


def git(*arguments):
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, shell=False, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60,
    ).stdout.strip()


def validate_tag(tag):
    version_pattern = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    if not re.fullmatch("v" + version_pattern, tag):
        raise ValueError("Release tag must be v<version>, for example v0.5.0-beta")
    version = tag[1:]
    versions = re.findall(r"^version:\s*([^\s#]+)\s*(?:#.*)?$",
                          (ROOT / "pubspec.yaml").read_text(encoding="utf-8"), re.MULTILINE)
    if len(versions) != 1 or versions[0].split("+", 1)[0] != version:
        raise ValueError(f"Tag {tag} must exactly match pubspec.yaml version without +build")
    try:
        revision = git("rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")
    except subprocess.CalledProcessError as error:
        raise ValueError(f"Tag {tag} does not exist locally; fetch the existing release tag") from error
    if revision != git("rev-parse", "HEAD"):
        raise ValueError(f"Tag {tag} must target the checked-out HEAD")
    outputs = {"tag": tag, "version": version, "prerelease": str("-" in version).lower()}
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as stream:
            for key, value in outputs.items():
                stream.write(f"{key}={value}\n")
    print(f"Validated existing release tag {tag}")


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    tag = commands.add_parser("validate-tag")
    tag.add_argument("--tag", required=True)
    args = parser.parse_args()
    try:
        validate_tag(args.tag)
    except PermissionError as error:
        parser.exit(1, f"Permission denied: {error.filename}. Whitelist its directory via nano ~/.config/firejail/strict-dev.profile\n")
    except subprocess.CalledProcessError as error:
        parser.exit(1, f"Git command failed: {error.stderr or error}\n")
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"Release preparation failed: {error}\n")


if __name__ == "__main__":
    main()
