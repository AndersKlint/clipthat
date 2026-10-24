import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "packaging/tools/deno-materials-lock.json"
LEGAL_NAME = re.compile(r"licen[cs]|copying|copyright|notice|unlicense|patents|authors", re.I)
LEGAL_TEXT = re.compile(rb"copyright|SPDX-License-Identifier|permission is hereby granted|redistribution and use", re.I)
REVISION = re.compile(r"[0-9a-f]{40}")


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def checked_url(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f"Expected credential-free HTTPS URL: {url}")
    return url


def archive_url(repository, revision):
    checked_url(repository)
    if not REVISION.fullmatch(revision):
        raise ValueError(f"Expected immutable Git revision: {revision}")
    parsed = urllib.parse.urlsplit(repository)
    path = parsed.path.removesuffix(".git").rstrip("/")
    if parsed.hostname == "github.com" and len(path.strip("/").split("/")) == 2:
        return f"https://codeload.github.com{path}/tar.gz/{revision}"
    if parsed.hostname.endswith(".googlesource.com"):
        return f"https://{parsed.hostname}{path}/+archive/{revision}.tar.gz"
    raise ValueError(f"No reproducible HTTPS archive endpoint for {repository}")


class Collector:
    def __init__(self, destination, lock, binary):
        self.destination = destination
        self.lock = lock
        self.limits = lock["limits"]
        self.downloaded = 0
        self.expanded = 0
        self.notice_bytes = 0
        self.repositories = {}
        self.crates = {}
        self.licenses = {}
        self.supplements = {}
        cache = destination / "download-cache.json"
        self.download_cache = json.loads(cache.read_text()) if cache.exists() else {}
        self.binary_notices = binary["notices"]
        self.manifest = {
            "schema": 1,
            "component": "deno",
            "version": lock["version"],
            "binaries": binary["assets"],
            "scope": lock["scope"],
            "collection_complete": False,
            "declared_graph_collected": False,
            "materials_complete": False,
            "notice_collection": "Unabridged legal files and source files containing copyright, SPDX, or license grants; each notice is attributed to its component, source archive, and archive member. This inventory is evidence, not an inference that filename scanning proves licensing completeness.",
            "archives": [],
            "notices": [],
            "components": [],
            "gaps": [],
            "provenance_limitations": lock["provenance_limitations"],
            "errors": [],
            "collector_lock_sha256": sha256(LOCK),
        }

    def checkpoint(self):
        write_json(self.destination / "materials.json", self.manifest)

    def fetch(self, url, relative, expected=None, limit=None):
        checked_url(url)
        target = self.destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            cached = self.download_cache.get(relative)
            if (target.is_symlink() or not cached or cached["url"] != url or
                    target.stat().st_size != cached["bytes"] or sha256(target) != cached["sha256"] or
                    (expected is not None and cached["sha256"] != expected)):
                raise ValueError(f"Existing download does not match provenance: {target}")
            return dict(cached)
        limit = min(limit or self.limits["archive_bytes"],
                    self.limits["download_bytes"] - self.downloaded)
        temporary = target.with_name(target.name + ".partial")
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "ClipThat-Deno-materials/1"})
                with urllib.request.urlopen(request, timeout=90) as response, temporary.open("xb") as output:
                    checked_url(response.url)
                    length = response.headers.get("Content-Length")
                    if length is not None and (int(length) < 0 or int(length) > limit):
                        raise ValueError(f"Download exceeds remaining size budget: {url}")
                    size = 0
                    while block := response.read(1024 * 1024):
                        size += len(block)
                        self.downloaded += len(block)
                        if size > limit or self.downloaded > self.limits["download_bytes"]:
                            raise ValueError(f"Download exceeds size budget: {url}")
                        output.write(block)
                    if not size or (length is not None and size != int(length)):
                        raise ValueError(f"Empty or truncated response: {url}")
                    resolved = response.url
                actual = sha256(temporary)
                if expected is not None and actual != expected:
                    raise ValueError(f"SHA256 mismatch for {url}: expected {expected}, got {actual}")
                temporary.rename(target)
                record = {
                    "path": relative, "url": url, "resolved_url": resolved,
                    "sha256": actual, "bytes": size,
                    "integrity": "pinned-sha256" if expected else "observed-sha256-over-https",
                }
                self.download_cache[relative] = record
                write_json(self.destination / "download-cache.json", self.download_cache)
                return dict(record)
            except PermissionError:
                raise
            except (urllib.error.URLError, TimeoutError) as error:
                if attempt == 2:
                    raise ValueError(f"Download failed: {url}: {error}") from error
                time.sleep(2 ** attempt)
            finally:
                temporary.unlink(missing_ok=True)

    def scan(self, record, component):
        selected = []
        metadata = {}
        expanded = 0
        seen = set()
        with tarfile.open(self.destination / record["path"], "r|*") as archive:
            for count, member in enumerate(archive, 1):
                path = PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts or "\\" in member.name:
                    raise ValueError(f"Unsafe archive member: {member.name}")
                if member.name in seen:
                    raise ValueError(f"Duplicate archive member: {member.name}")
                seen.add(member.name)
                expanded += member.size
                self.expanded += member.size
                if (count > self.limits["archive_entries"] or member.size < 0 or
                        expanded > self.limits["expanded_archive_bytes"] or
                        self.expanded > self.limits["expanded_total_bytes"]):
                    raise ValueError(f"Archive exceeds scan budget: {record['path']}")
                if not member.isfile():
                    continue
                if member.size > self.limits["member_bytes"]:
                    self.manifest["gaps"].append(f"Unscanned oversized file: {record['path']}:{member.name}")
                    continue
                with archive.extractfile(member) as stream:
                    data = stream.read()
                if len(data) != member.size:
                    raise ValueError(f"Truncated archive member: {member.name}")
                name = path.name
                if name in {"Cargo.lock", "Cargo.toml", ".cargo_vcs_info.json", "rust-toolchain.toml", ".gitmodules"}:
                    metadata[member.name] = data
                named = bool(LEGAL_NAME.search(name))
                if not named and (b"\0" in data or not LEGAL_TEXT.search(data)):
                    continue
                self.notice_bytes += len(data)
                if self.notice_bytes > self.limits["notice_bytes"]:
                    raise ValueError("Collected notice files exceed output size budget")
                identity = hashlib.sha256((record["path"] + ":" + member.name).encode()).hexdigest()
                relative = f"notices/{identity}.txt"
                target = self.destination / relative
                target.write_bytes(data)
                notice = {
                    "path": relative, "sha256": hashlib.sha256(data).hexdigest(),
                    "component": component, "archive": record["path"],
                    "member": member.name, "kind": "legal-file" if named else "attributed-source",
                }
                self.manifest["notices"].append(notice)
                selected.append(notice)
        record["notice_count"] = len(selected)
        record["legal_file_count"] = sum(n["kind"] == "legal-file" for n in selected)
        record["license_file_count"] = sum(bool(re.search(r"licen[cs]|copying|unlicense", PurePosixPath(n["member"]).name, re.I)) for n in selected)
        return metadata

    def source(self, name, version, url, expected=None, **provenance):
        identity = hashlib.sha256((name + version + url).encode()).hexdigest()[:20]
        suffix = ".tar.xz" if url.endswith(".tar.xz") else ".crate" if url.endswith(".crate") else ".tar.gz"
        relative = f"sources/{identity}{suffix}"
        reused = relative in self.download_cache
        record = self.fetch(url, relative, expected)
        record.update({"component": name, "version": version, **provenance})
        self.manifest["archives"].append(record)
        if not reused:
            print(f"Collected {name} {version} ({record['bytes']} bytes)", flush=True)
        metadata = self.scan(record, name)
        if len(self.manifest["archives"]) % 25 == 0:
            print(f"Scanned {len(self.manifest['archives'])} source archives", flush=True)
            self.checkpoint()
        return record, metadata

    def git(self, repository, revision, parent):
        key = (repository, revision)
        if key in self.repositories:
            self.repositories[key]["required_by"].append(parent)
            return self.repositories[key]
        if len(self.repositories) >= self.limits["repositories"]:
            raise ValueError("Recursive repository count exceeds budget")
        url = archive_url(repository, revision)
        record, metadata = self.source(repository, revision, url, repository=repository,
                                       revision=revision, required_by=[parent],
                                       revision_integrity="parent-gitlink-or-checksum-verified-crate-VCS-metadata")
        self.repositories[key] = record
        if not record["license_file_count"]:
            inherited = self.lock["inherited_repository_licenses"].get(repository)
            if not inherited:
                raise ValueError(f"Native repository has no license files or declared inherited license: {repository}@{revision}")
            record["inherited_license_materials"] = [self.license_text(identifier) for identifier in inherited]
        modules = [data for path, data in metadata.items()
                   if path.count("/") <= (1 if "codeload.github.com" in url else 0)
                   and PurePosixPath(path).name == ".gitmodules"]
        links = self.gitlinks(repository, revision)
        mapping = {}
        if modules:
            config = configparser.ConfigParser(interpolation=None, strict=True)
            config.read_string(modules[0].decode("utf-8"))
            mapping = {config[s]["path"]: config[s]["url"] for s in config.sections()}
        for path, commit in links:
            if path not in mapping:
                raise ValueError(f"Gitlink lacks repository URL: {repository}@{revision}:{path}")
            child = mapping[path]
            if child.startswith("../") or child.startswith("./"):
                child = urllib.parse.urljoin(repository.rstrip("/") + "/", child)
            self.git(child, commit, {"repository": repository, "revision": revision, "path": path})
        record["gitlinks_complete"] = True
        self.checkpoint()
        return record

    def gitlinks(self, repository, revision):
        entries = self.git_tree(repository, revision)
        return [(path, header.split()[2]) for header, path in entries if header.startswith("160000 ")]

    def git_tree(self, repository, revision):
        identity = hashlib.sha256((repository + revision).encode()).hexdigest()
        relative = f"sources/git-tree-{identity}.json"
        target = self.destination / relative
        cached = self.download_cache.get(relative)
        if cached:
            if (target.is_symlink() or target.stat().st_size != cached["bytes"] or
                    sha256(target) != cached["sha256"]):
                raise ValueError(f"Cached Git tree changed: {target}")
            data = json.loads(target.read_bytes())
            if data["repository"] != repository or data["revision"] != revision:
                raise ValueError(f"Cached Git tree revision mismatch: {target}")
            self.manifest.setdefault("provenance", []).append(dict(cached))
            return data["entries"]
        environment = {**{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
                       "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                       "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_COUNT": "0"}
        with tempfile.TemporaryDirectory(prefix="deno-git-", dir=self.destination) as temporary:
            def run(*arguments):
                result = subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull,
                                         "-c", "protocol.file.allow=never", *arguments],
                                        cwd=temporary, env=environment, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        timeout=180, check=False)
                if result.returncode:
                    if b"permission denied" in result.stderr.lower():
                        raise PermissionError(13, "Git permission denied", temporary)
                    raise ValueError(f"Git failed for {repository}: {result.stderr.decode(errors='replace')}")
                return result.stdout
            run("init", "--bare", "--quiet")
            run("fetch", "--quiet", "--depth=1", "--filter=blob:none", "--no-tags", repository, revision)
            if run("rev-parse", "FETCH_HEAD").decode().strip() != revision:
                raise ValueError(f"Git revision mismatch: {repository}")
            entries = run("ls-tree", "-rz", "FETCH_HEAD").split(b"\0")
            tree = []
            for entry in entries:
                if entry:
                    header, path = entry.split(b"\t", 1)
                    tree.append((header.decode("ascii"), path.decode("utf-8")))
            write_json(target, {"repository": repository, "revision": revision, "entries": tree})
            record = {
                "path": relative, "repository": repository, "revision": revision,
                "sha256": sha256(target), "bytes": target.stat().st_size,
                "method": "git fetch --depth=1 --filter=blob:none; git ls-tree -rz FETCH_HEAD",
            }
            self.manifest.setdefault("provenance", []).append(record)
            self.download_cache[relative] = record
            write_json(self.destination / "download-cache.json", self.download_cache)
            return tree

    def supplemental_notices(self, repository, revision, component):
        key = (repository, revision)
        if key in self.supplements:
            return self.supplements[key]
        original = revision
        try:
            tree = self.git_tree(repository, revision)
        except ValueError as error:
            if not any(text in str(error).lower() for text in ("not our ref", "couldn't find remote ref", "unadvertised object")):
                raise
            environment = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
            environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0"})
            result = subprocess.run(["git", "-c", "credential.helper=", "ls-remote", repository, "HEAD"],
                                    env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=120, check=False)
            if b"permission denied" in result.stderr.lower():
                raise PermissionError(13, "Git permission denied", str(self.destination))
            revision = result.stdout.decode().split()[0] if result.returncode == 0 and result.stdout else ""
            if not REVISION.fullmatch(revision):
                raise ValueError(f"Cannot resolve supplemental license repository: {repository}")
            tree = self.git_tree(repository, revision)
            self.manifest["provenance_limitations"].append(
                f"{component}: published crate commit {original} is unavailable in {repository}; canonical declared license text and repository legal files at {revision} supplement the checksum-verified crate. This supplemental revision is not claimed as the crate source.")
        records = []
        parsed = urllib.parse.urlsplit(repository)
        for header, path in tree:
            if not header.startswith("100") or not LEGAL_NAME.search(PurePosixPath(path).name):
                continue
            url = f"https://raw.githubusercontent.com{parsed.path.removesuffix('.git')}/{revision}/{urllib.parse.quote(path)}"
            identity = hashlib.sha256(url.encode()).hexdigest()
            notice = self.fetch(url, f"notices/supplemental-{identity}.txt", limit=self.limits["member_bytes"])
            notice.update({"kind": "supplemental-repository-legal-file", "repository": repository,
                           "revision": revision, "member": path, "component": component,
                           "crate_revision": original})
            self.manifest["notices"].append(notice)
            records.append(notice)
        if not records:
            self.manifest["provenance_limitations"].append(f"{component}: no named legal files in supplemental repository {repository}@{revision}; canonical license text and attributed crate source are retained.")
        self.supplements[key] = records
        return records

    def license_text(self, identifier, exception=False):
        key = (identifier, exception)
        if key in self.licenses:
            return self.licenses[key]
        if not re.fullmatch(r"[A-Za-z0-9.+-]+", identifier):
            raise ValueError(f"Unsupported SPDX identifier: {identifier}")
        spdx = self.lock["spdx"]
        directory = "exceptions" if exception else "details"
        url = f"https://raw.githubusercontent.com/spdx/license-list-data/{spdx['revision']}/json/{directory}/{identifier}.json"
        record = self.fetch(url, f"sources/spdx-{identifier}.json", limit=4 * 1024 * 1024)
        data = json.loads((self.destination / record["path"]).read_bytes())
        id_field = "licenseExceptionId" if exception else "licenseId"
        text_field = "licenseExceptionText" if exception else "licenseText"
        if data[id_field] != identifier or not data[text_field].strip():
            raise ValueError(f"Missing canonical SPDX text: {identifier}")
        self.manifest.setdefault("provenance", []).append(record)
        relative = f"notices/SPDX-{identifier}.txt"
        target = self.destination / relative
        target.write_text(data[text_field] + "\n", encoding="utf-8")
        notice = {"path": relative, "sha256": sha256(target), "license": identifier,
                  "kind": "canonical-license", "source": record["path"]}
        self.manifest["notices"].append(notice)
        self.licenses[key] = notice
        return notice

    def license_materials(self, entry, manifest, record, prefix, vcs):
        expression = entry["license"]
        if not expression:
            license_file = entry["license_file"]
            if not license_file:
                raise ValueError(f"No declared license or license-file for {entry['name']}@{entry['version']}")
            with tarfile.open(self.destination / record["path"]) as archive:
                member = archive.getmember(prefix + license_file)
                if not member.isfile() or member.size > self.limits["member_bytes"]:
                    raise ValueError(f"Missing or oversized declared license-file: {entry['name']}:{license_file}")
                data = archive.extractfile(member).read()
            if not data.strip():
                raise ValueError(f"Empty declared license-file: {entry['name']}:{license_file}")
            relative = f"notices/license-file-{hashlib.sha256(data).hexdigest()}.txt"
            (self.destination / relative).write_bytes(data)
            notice = {"path": relative, "sha256": hashlib.sha256(data).hexdigest(),
                      "component": entry["name"], "archive": record["path"],
                      "member": prefix + license_file, "kind": "declared-license-file"}
            self.manifest["notices"].append(notice)
            entry["license_materials"] = [notice]
            return
        expression = expression.replace("/", " OR ")
        tokens = re.findall(r"[A-Za-z0-9.+-]+|[()]", expression)
        if re.sub(r"\s+", "", expression) != "".join(tokens):
            raise ValueError(f"Unsupported license expression: {expression}")
        position = 0

        def primary():
            nonlocal position
            if position >= len(tokens):
                raise ValueError(f"Incomplete license expression: {expression}")
            token = tokens[position]
            position += 1
            if token == "(":
                alternatives = disjunction()
                if position >= len(tokens) or tokens[position] != ")":
                    raise ValueError(f"Unbalanced license expression: {expression}")
                position += 1
                return alternatives
            if token in {"AND", "OR", "WITH", ")"}:
                raise ValueError(f"Unsupported license expression: {expression}")
            if token == "MPL-2.0+":
                token = "MPL-2.0"
            if position < len(tokens) and tokens[position] == "WITH":
                position += 1
                if position >= len(tokens) or tokens[position] in {"AND", "OR", "WITH", "(", ")"}:
                    raise ValueError(f"Missing SPDX exception: {expression}")
                token += " WITH " + tokens[position]
                position += 1
            return [{token}]

        def conjunction():
            nonlocal position
            alternatives = primary()
            while position < len(tokens) and tokens[position] == "AND":
                position += 1
                right = primary()
                alternatives = [left | other for left in alternatives for other in right]
            return alternatives

        def disjunction():
            nonlocal position
            alternatives = conjunction()
            while position < len(tokens) and tokens[position] == "OR":
                position += 1
                alternatives += conjunction()
            return alternatives

        alternatives = disjunction()
        if position != len(tokens):
            raise ValueError(f"Unsupported license expression: {expression}")
        allowed = [option for option in alternatives
                   if not any(re.match(r"(?:A?GPL|LGPL)-", item) for item in option)]
        if not allowed:
            raise ValueError(f"Unexpected GPL-family source obligations require explicit closure: {entry['name']} {expression}")
        chosen = min(allowed, key=lambda option: (len(option), sorted(option)))
        entry["selected_licenses"] = sorted(chosen)
        entry["license_materials"] = []
        for identifier in sorted(chosen):
            parts = identifier.split(" WITH ")
            entry["license_materials"].append(self.license_text(parts[0]))
            if len(parts) == 2:
                entry["license_materials"].append(self.license_text(parts[1], exception=True))
        if "MPL-2.0" in chosen:
            entry["source_obligation"] = {"license": "MPL-2.0", "archive": record["path"],
                                          "sha256": record["sha256"], "source_url": record["url"]}
        if not record["license_file_count"] and entry["name"] != "v8":
            repository = manifest["package"].get("repository", "").rstrip("/")
            if vcs and repository.startswith("https://github.com/"):
                parsed = urllib.parse.urlsplit(repository)
                repository = f"https://github.com/{'/'.join(parsed.path.strip('/').split('/')[:2])}"
                entry["supplemental_notices"] = self.supplemental_notices(repository, vcs["git"]["sha1"], entry["name"])
            if vcs and vcs["git"].get("dirty"):
                self.manifest["provenance_limitations"].append(f"{entry['name']}@{entry['version']} crate VCS metadata records a dirty checkout; the published crate SHA256 is retained.")

    def cargo(self, packages, source_record, lock_member):
        for package in packages:
            name, version = package["name"], package["version"]
            entry = {"name": name, "version": version, "source": package.get("source", "workspace"),
                     "lock_archive": source_record["path"], "lock_member": lock_member}
            self.manifest["components"].append(entry)
            origin = package.get("source", "")
            if not origin:
                entry["archive"] = source_record["path"]
                continue
            if origin.startswith("git+"):
                parsed = urllib.parse.urlsplit(origin[4:])
                repository = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
                record = self.git(repository, parsed.fragment, f"Cargo.lock:{name}@{version}")
                entry["archive"] = record["path"]
                continue
            if origin != "registry+https://github.com/rust-lang/crates.io-index":
                raise ValueError(f"Unsupported Cargo source: {origin}")
            if not re.fullmatch(r"[A-Za-z0-9_-]+", name) or not re.fullmatch(r"[A-Za-z0-9.+_-]+", version):
                raise ValueError(f"Unsafe Cargo package identity: {name}@{version}")
            checksum = package["checksum"]
            key = (name, version, checksum)
            if key in self.crates:
                entry.update(self.crates[key])
                continue
            record, metadata = self.source(name, version,
                f"https://static.crates.io/crates/{name}/{name}-{version}.crate", checksum,
                checksum_provenance=source_record["path"] + ":" + lock_member)
            entry["archive"] = record["path"]
            prefix = f"{name}-{version}/"
            manifest = tomllib.loads(metadata[prefix + "Cargo.toml"].decode())
            entry["license"] = manifest["package"].get("license")
            entry["license_file"] = manifest["package"].get("license-file")
            entry["authors"] = manifest["package"].get("authors", [])
            entry["repository"] = manifest["package"].get("repository")
            vcs_data = metadata.get(prefix + ".cargo_vcs_info.json")
            vcs = json.loads(vcs_data) if vcs_data else None
            self.license_materials(entry, manifest, record, prefix, vcs)
            if name == "v8":
                expected = self.lock["v8"]
                if (version != expected["version"] or checksum != expected["crate_sha256"] or
                        vcs["git"]["sha1"] != expected["revision"]):
                    raise ValueError("v8 crate does not match supplemental native-source lock")
                entry["vcs"] = vcs
                self.git(expected["repository"], expected["revision"], f"Cargo.lock:v8@{version}")
            self.crates[key] = {k: value for k, value in entry.items()
                                if k not in {"name", "version", "source", "lock_archive", "lock_member"}}

    def collect(self):
        source = self.lock["source"]
        record, metadata = self.source("deno", self.lock["version"], source["url"], source["sha256"])
        for notice in self.binary_notices:
            matches = [n for n in self.manifest["notices"]
                       if n["archive"] == record["path"] and n["member"] == "deno/" + notice["name"]]
            if len(matches) != 1 or matches[0]["sha256"] != notice["sha256"]:
                raise ValueError(f"Release source does not preserve locked Deno notice: {notice['name']}")
        cargo_lock = tomllib.loads(metadata["deno/Cargo.lock"].decode())
        toolchain = tomllib.loads(metadata["deno/rust-toolchain.toml"].decode())
        if toolchain["toolchain"]["channel"] != self.lock["rust"]["version"]:
            raise ValueError("Release Rust toolchain differs from materials lock")
        self.manifest["workspace_package_count"] = len(cargo_lock["package"])
        self.cargo(cargo_lock["package"], record, "deno/Cargo.lock")
        rust = self.lock["rust"]
        rust_source = rust["source"]
        rust_record, rust_metadata = self.source("rust-std-source", rust["version"], rust_source["url"], rust_source["sha256"])
        std_locks = [(path, data) for path, data in rust_metadata.items() if path.endswith("/library/Cargo.lock")]
        if len(std_locks) != 1:
            raise ValueError("Rust source must contain exactly one library/Cargo.lock")
        std_path, std_lock = std_locks[0]
        self.cargo(tomllib.loads(std_lock.decode())["package"], rust_record, std_path)
        channel_record = self.fetch(rust["channel_url"], "sources/rust-channel.toml", limit=2 * 1024 * 1024)
        self.manifest.setdefault("provenance", []).append(channel_record)
        channel = tomllib.loads((self.destination / channel_record["path"]).read_text())
        published_source = channel["pkg"]["rust-src"]["target"]["*"]
        if (published_source["xz_url"] != rust_source["url"] or
                published_source["xz_hash"] != rust_source["sha256"]):
            raise ValueError("Published Rust channel differs from pinned rust-src archive")
        self.manifest["declared_graph_collected"] = True
        self.manifest["collection_complete"] = not self.manifest["gaps"]
        self.manifest["downloaded_bytes"] = self.downloaded
        self.manifest["materials_complete"] = not self.manifest["gaps"]
        self.manifest["counts"] = {"cargo_packages": len(self.manifest["components"]),
                                    "unique_registry_crates": len(self.crates),
                                    "native_repository_snapshots": len(self.repositories),
                                    "supplemental_repository_snapshots": len(self.supplements),
                                    "supplemental_repositories": len({repository for repository, _ in self.supplements}),
                                    "archives": len(self.manifest["archives"]),
                                    "notices": len(self.manifest["notices"])}
        self.checkpoint()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--resume", action="store_true", help="Verify and reuse downloads in an existing collector destination")
    parser.add_argument("--max-download-mib", type=int, help="Lower the total HTTPS download budget (default: 4096 MiB)")
    arguments = parser.parse_args()
    lock = json.loads(LOCK.read_text())
    if arguments.max_download_mib is not None:
        budget = arguments.max_download_mib * 1024 * 1024
        if not 0 < budget <= lock["limits"]["download_bytes"]:
            parser.error("--max-download-mib must be between 1 and 4096")
        lock["limits"]["download_bytes"] = budget
    binary = json.loads((ROOT / "packaging/tools/lock.json").read_text())["components"]["deno"]
    if lock["schema"] != 1 or binary["version"] != lock["version"]:
        parser.error("Deno materials lock and binary lock disagree")
    destination = arguments.destination.absolute()
    collector = None
    try:
        if destination.is_symlink() or (destination.exists() and not arguments.resume):
            raise ValueError(f"Destination must not already exist: {destination}")
        if arguments.resume and not (destination / "download-cache.json").is_file():
            raise ValueError("--resume requires an existing collector download-cache.json")
        destination.mkdir(parents=True, exist_ok=arguments.resume)
        (destination / "sources").mkdir(exist_ok=arguments.resume)
        (destination / "notices").mkdir(exist_ok=arguments.resume)
        collector = Collector(destination, lock, binary)
        collector.manifest["limits"] = lock["limits"]
        collector.checkpoint()
        collector.collect()
    except PermissionError as error:
        print(f"Permission denied at {error.filename}. Whitelist that directory using: nano ~/.config/firejail/strict-dev.profile", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError, subprocess.SubprocessError) as error:
        if collector:
            collector.manifest["errors"].append(str(error))
            collector.checkpoint()
        print(f"Deno material collection failed: {error}", file=sys.stderr)
        return 1
    if collector.manifest["gaps"]:
        print("Required materials are missing:", file=sys.stderr)
        for gap in collector.manifest["gaps"]:
            print(f"- {gap}", file=sys.stderr)
        return 1
    print(f"Deno materials ready: {destination / 'materials.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
