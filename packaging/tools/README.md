# Bundled tool preparation

Requires Python 3.10+ and network access at packaging time. Only the Python standard
library is used. No tool is downloaded by the application. The resulting layout is:

```text
<Flutter bundle>/
  yt_section_downloader[.exe]
  tools/
    yt-dlp[.exe]
    ffmpeg[.exe]
    ffprobe[.exe]
    deno[.exe]
    manifest.json
  licenses/tools/
    lock.json
    BUNDLING.md
    <component>/...
  tool-sources/
    sources.json
    <prepared source archives, notices and compliance notes>
```

The runtime must resolve these four tools relative to the application executable.
It must explicitly give yt-dlp the bundled FFmpeg directory and Deno executable,
disable user configuration and automatic updates, and never fall back to PATH or
fetch EJS remotely. Official standalone yt-dlp assets include Python and EJS.
The extensionless `yt-dlp` upstream asset is not standalone and is not used.

## Commands

```sh
python3 scripts/bundle_tools.py --help
python3 scripts/bundle_tools.py --platform linux-x64 --destination build/linux/x64/release/bundle --sources-dir release-sources/linux-x64
python3 scripts/bundle_tools.py --platform windows-x64 --destination build/windows/x64/runner/Release --sources-dir release-sources/windows-x64
python3 scripts/bundle_tools.py --platform linux-x64 --destination build/linux/x64/release/bundle --development
```

The destination must already exist. Existing `tools/`, `licenses/tools/`, or
`tool-sources/` are refused, including symlinks. Use a freshly built/copied bundle
for each invocation. Downloads and staging are temporary; there is no shared
cache. Downloads are SHA256-checked before processing. Archive paths, file types,
duplicate names, entry counts, expanded sizes and selected executable locations
are checked; archives are never extracted wholesale. Linux binaries receive 0755
permissions. Staging may target either platform from either host without running
the downloaded binaries. This does not change their native runtime requirements.

Release is the default. `--development` allows absent source inputs and always
marks the tool manifest `development: true, redistributable: false`. Such bundles
are for local development only, with potentially incomplete dependency notices.
The Windows release command has no development bypass.

## Locked upstream provenance

`lock.json` pins the exact release URLs and SHA256 digests returned by upstream
GitHub release APIs on 2026-10-24. Notice hashes were computed from the listed
upstream tag URLs. This is HTTPS/upstream-digest verification, not independent
maintainer-signature verification. No floating `latest` download URLs are used.

| Component | Pin | Distribution |
| --- | --- | --- |
| yt-dlp | 2026.10.21 | Official PyInstaller standalone x64, Python + EJS included |
| FFmpeg + FFprobe | n8.1.3-9-g29e619e767 | BtbN `autobuild-2026-09-30-13-08`, static `gpl`, release branch 8.1 |
| Deno | 2.9.8 | Official x86_64 GNU/Linux or Windows MSVC ZIP |

The FFmpeg `gpl` variant includes libx264; AAC is FFmpeg's native encoder, not
non-redistributable fdk-aac. The Windows packager checks the actual encoder list
and build configuration. Shared cross-host staging does not execute binaries.
BtbN documents Linux glibc >= 2.28, kernel >= 4.18, and Windows 10 22H2 as its
minimum supported baseline. Other bundled components may impose further limits.
BtbN retains monthly final builds for two years; archive these exact assets for
release reproducibility before their removal. There is no unverified mirror or
silent upgrade fallback. Source references in the lock are useful starting points,
not complete source-distribution claims.

## Required corresponding source inputs

Automating complete source recovery for these prebuilt distributions is not
implemented. Release packaging therefore **requires user-prepared exact matching
source archives and compliance notes**. A URL to FFmpeg or yt-dlp core alone is
insufficient. Prepare a separate directory for each target, containing
`sources.json` and all referenced files. Files must be nonempty regular files
inside that directory, without symlink paths. SHA256 is checked before staging
and again after copying. Archives must be recognizable ZIP or tar archives; they
are copied intact, not unpacked or treated as verified source content.

Use this schema, repeating the component entry for `ffmpeg` and `deno`, with
their exact versions and target asset hashes from `lock.json`:

```json
{
  "schema": 1,
  "platform": "windows-x64",
  "components": {
    "yt-dlp": {
      "version": "2026.10.21",
      "binary_sha256": "COPY_EXACT_TARGET_ASSET_SHA256_FROM_LOCK",
      "attestation": "exact-corresponding-sources-including-dependencies-and-build-scripts",
      "archives": [
        {"path": "yt-dlp/corresponding-source.tar.xz", "sha256": "COMPUTED_SHA256"}
      ],
      "notices": [
        {"path": "yt-dlp/COMPLETE-NOTICES.txt", "sha256": "COMPUTED_SHA256"}
      ],
      "compliance_notes": {"path": "yt-dlp/COMPLIANCE.md", "sha256": "COMPUTED_SHA256"}
    }
  }
}
```

The uppercase values are placeholders, not usable checksums. Multiple archives
and notice files are supported per component. Paths must be portable relative
paths using `/`. Do not name an input `sources.json`, which is reserved for the
copied manifest. Compute each file hash, for example:

```sh
python3 -c "import hashlib,pathlib; print(hashlib.file_digest(pathlib.Path('archive.tar.xz').open('rb'),'sha256').hexdigest())"
```

That convenience command requires Python 3.11+. With Python 3.10 use
`hashlib.sha256(pathlib.Path('archive.tar.xz').read_bytes()).hexdigest()` instead.

For every component, the preparer must supply:

* The preferred form for modification of the **exact shipped binary**, including
  all relevant bundled/linked dependencies, local changes, generated-code inputs,
  patches, configuration, and scripts controlling compilation and installation.
* A dependency inventory with exact versions/commits and source-to-binary mapping,
  plus original copyright, attribution, license, and NOTICE texts required by each
  dependency. Include full applicable GPL texts, not just license identifiers.
* Compliance notes identifying the binary URL and SHA256, upstream build revision,
  dependency revisions, build recipes/options/toolchain and preparation method;
  explain the mapping from every archive to the binaries and attest completeness.

In particular:

* **FFmpeg/FFprobe:** include the exact FFmpeg revision and all linked library
  sources, including x264 and every other enabled GPL/LGPL/permissive dependency
  with redistribution obligations. Include the matching BtbN build scripts at
  `6c9aec5fc9a72ec3abedd1fa84db141fa18cf52b`, dependency revisions, patches,
  configuration, generated inputs and build/install instructions. The build-script
  repository alone does not contain all fetched dependency sources. Do not
  substitute a newer FFmpeg release tarball or a generic x264 download link.
* **Standalone yt-dlp:** the combined PyInstaller executable is GPLv3+, despite
  the core being Unlicense. Include exact bundled Python, EJS (and its bundled
  astring/meriyah), PyInstaller/bootloader, Python packages and native dependencies
  and their applicable sources/notices, plus the actual standalone build recipe.
  Use the upstream release workflow and build metadata to establish versions;
  the core source archive does not establish these versions by itself.
* **Deno:** provide the exact release source/dependency inventory and complete
  license/notice texts for V8, Rust crates and other included components. Deno's
  top-level MIT license alone is not a complete third-party notice collection.
  Include sources required by those dependency licenses. This tooling requires a
  source archive for Deno too, to keep each binary's provenance explicit.

The script verifies declarations, target/version/binary binding, file presence,
archive format and hashes; it **cannot prove legal or source completeness**. The
explicit attestation records the preparer's responsibility, not an automated
compliance certification. If matching source cannot be obtained, do not produce
a release with these binaries. Obtain complete sources or deliberately change
the locked build and provide matching sources for that build.

The bundler includes the archives alongside the bundle under `tool-sources/`,
copies prepared notices and compliance notes into `licenses/tools/<component>/`,
and records the copied source manifest's hash in `tools/manifest.json`. Ship the
entire corresponding source distribution with the binaries through the same
release location; retain it for each published binary release. The Windows
packager moves `tool-sources/` into the sibling source ZIP and names that ZIP in
`release.json`. Never publish the portable ZIP without its matching source ZIP.

## CI source archives

Release CI uses Flutter **3.47.2** and Python **3.13**. Source preparation is
manual: first populate and review separate `release-sources/windows-x64/` and
`release-sources/linux-x64/` directories using the schema above. Each manifest
must declare exactly `yt-dlp`, `ffmpeg`, and `deno`, bind their versions and
target-specific binary hashes to `lock.json`, and include the exact attestation,
nonempty archive and notice lists, and compliance notes. Include every referenced
file with its declared hash. Do not substitute generic upstream source tarballs
for complete corresponding sources of the shipped standalone builds.

Package each prepared directory's **contents**, not the enclosing directory,
into a ZIP or tar archive. For example, from the repository root with Python 3.13:

```sh
python -c "import shutil; shutil.make_archive('windows-tool-sources', 'zip', root_dir='release-sources/windows-x64')"
python -c "import shutil; shutil.make_archive('linux-tool-sources', 'gztar', root_dir='release-sources/linux-x64')"
python -c "import hashlib,pathlib; print(hashlib.file_digest(pathlib.Path('windows-tool-sources.zip').open('rb'), 'sha256').hexdigest())"
python -c "import hashlib,pathlib; print(hashlib.file_digest(pathlib.Path('linux-tool-sources.tar.gz').open('rb'), 'sha256').hexdigest())"
```

The outer archives must have this layout (with the actual paths declared in each
target's manifest):

```text
sources.json
yt-dlp/corresponding-source.tar.xz
yt-dlp/COMPLETE-NOTICES.txt
yt-dlp/COMPLIANCE.md
ffmpeg/...
deno/...
```

Use regular files and directories, without symlinks or paths escaping the package.
The hashes in `sources.json` cover the individual referenced files; the digest
configured in GitHub covers the entire outer ZIP/tar download. Recompute both
levels as appropriate whenever inputs change, including when tool pins change.

Host each complete outer archive at a **public HTTPS URL**. In the repository's
**Settings > Secrets and variables > Actions > Variables**, configure:

| Repository variable | Prepared input |
| --- | --- |
| `WINDOWS_TOOL_SOURCES_URL` | Windows x64 outer archive's public HTTPS URL |
| `WINDOWS_TOOL_SOURCES_SHA256` | SHA256 of that complete archive |
| `LINUX_TOOL_SOURCES_URL` | Linux x64 outer archive's public HTTPS URL |
| `LINUX_TOOL_SOURCES_SHA256` | SHA256 of that complete archive |

Use repository variables, not secrets or embedded/base64 source material. Keep
the hosted archives available for reproducibility. Each native workflow fails
if its required variables are missing, the download or hash fails, or extracted
inputs do not satisfy the release source schema. CI never uses `--development`.
Validation cannot establish source completeness: **do not publish until the
complete source-to-binary mapping has been reviewed**.

The Windows workflow publishes the portable ZIP, matching source ZIP, and
`SHA256SUMS-windows-x64`. The Linux workflow publishes the Flatpak, exact tagged
application-source archive `ClipThat-linux-x64-app-source.tar.gz`, and
`SHA256SUMS-linux-x64`; prepared tool sources and notices remain inside the
Flatpak. Both upload Actions artifacts and assets to the same GitHub release.
Actions retention is finite; release assets are the permanent distribution
location until explicitly removed. See [release workflow setup](../../README.md#github-release-workflows)
for token write permissions, version/tag validation, and trigger instructions.
