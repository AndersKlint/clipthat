# Bundled tool preparation

The application uses adjacent `tools/yt-dlp`, `ffmpeg`, `ffprobe`, and `deno` (`.exe` on Windows). It passes bundled FFmpeg/Deno paths explicitly, disables user configuration, plugins, remote EJS, and updates, and never downloads tools at runtime or falls back to PATH.

## Automatic release pipeline

`scripts/prepare_release_tools.py` builds native release tools and collects Deno materials. `scripts/package_flatpak.py` and `scripts/package_windows.py` invoke it automatically; `make installer` selects the host packager without source inputs.

| Release component | Inputs and method |
| --- | --- |
| FFmpeg + FFprobe **8.1.3** | `media-lock.json`, `scripts/build_media_tools.py`, and `build-media.sh`; native GCC build with static x264 revision `c24e06c2e184345ceb33eb20a15d1024d9fd3497` and dav1d **1.5.4**, using source-built NASM **2.16.03** at build time only |
| yt-dlp **2026.10.21** | `downloader-lock.json`, `scripts/build_downloader.py`, and `downloader.spec`; custom minimal PyInstaller **6.22.0** standalone with Python, unchanged official **yt-dlp-ejs 0.8.0**, and **certifi 2026.10.19** |
| Deno **2.9.8** | Official x64 binary pinned in `lock.json`; `deno-materials-lock.json` and `scripts/collect_deno_materials.py` collect matching declared source/dependency and license materials |

`lock.json` separates release builders/collector from development-only upstream yt-dlp and BtbN media assets. Downloads use pinned HTTPS URLs and SHA256 checks; Git snapshots are commit-verified and hashed after creation. This records provenance, not independent maintainer-signature verification.

Media builds disable autodetection and networking, enable only local `file`/`pipe` protocols, and retain H.264/AAC/VTT encoding plus the decoders needed for the supported YouTube workflow, including AV1 through dav1d. The recipe enables GPLv3 and libx264, not nonfree fdk-aac. Build output checks cover encoders, decoders, protocols, and native runtime imports. Source archives, recipes, configuration, command logs, toolchain versions, and notices are retained.

The downloader freezes a locked minimal package set rather than redistributing the upstream combined standalone. EJS data is checked against yt-dlp's solver version/hashes; certifi CA data and editable source are retained. Python modules and native libraries are inventoried and mapped to official Windows Python inputs or the locked Linux SDK manifest and recipes. Unknown collected libraries or an unmapped SDK profile fail preparation.

### Native environments

- **Linux x64:** run preparation with `/usr/bin/python3` **inside GNOME SDK 50**. `downloader-lock.json` pins the SDK commit, manifest hash, interpreter, and GNOME/freedesktop recipe revisions. The current profile uses **CPython 3.13.16**. `make flatpak-setup` reads the commit from that lock and installs/pins it; a floating SDK update is not a substitute. GCC/G++, Make, Meson, Ninja, pkg-config, binutils, Bash, Perl, and Git must be available. The Flatpak packager builds both app and tools in this environment.
- **Windows x64:** official **CPython 3.13.17 x64**, launched from **MSYS2 UCRT64**, with UCRT64 GCC, Meson, Ninja, pkgconf, binutils, Make, Perl, diffutils, coreutils, Bash, and Git. The builder verifies collected Python binaries against the official archive. Flutter also requires Visual Studio's desktop C++ workload and Windows SDK. See [Windows instructions](../windows/README.md).

Windows Python tracks the latest official 3.13 patch with matching binaries and SPDX: [3.13.17](https://www.python.org/downloads/release/python-31317/) (2026-10-21), listed in the [official Windows catalog](https://www.python.org/downloads/windows/). The lock hashes the full `python-3.13.17-amd64.zip` archive (not the embeddable ZIP), Windows installer SPDX, and source-tarball SPDX from [python.org](https://www.python.org/ftp/python/3.13.17/). The builder verifies their SHA256 values, collects sources using SPDX checksums, and checks frozen native binaries against that archive. Keep the workflow interpreter pin and lock synchronized. Linux retains its independently locked SDK Python 3.13.16 profile.

Use fresh native work paths without whitespace or shell/make metacharacters. No cross-compilation path is supported for release preparation.

### Internal reusable staging

Normal release commands are in [the root README](../../README.md#release-packaging). For separate preparation inside the appropriate native environment:

```sh
python scripts/prepare_release_tools.py --platform windows-x64 --destination C:/clipthat-work/prepared
python scripts/bundle_tools.py --platform windows-x64 --destination build/windows/x64/runner/Release --prepared-tools C:/clipthat-work/prepared
```

The same orchestrator accepts `--platform linux-x64` **inside the locked SDK**. `--destination` for preparation must be absent; direct bundling requires an existing Flutter bundle without `tools/`, `licenses/tools/`, or `tool-sources/`. `--prepared-tools` is an internal reusable stage accepted by the bundler and Windows packager. It validates platform, all builder-lock fingerprints, payload inventory/hashes, executable set, and evidence. The Flatpak packager always prepares tools inside its SDK build; it does not accept this option.

Deno collection can be reused independently on either platform, with **Python 3.11+** and Git:

```sh
python3 scripts/collect_deno_materials.py --destination build/deno-materials
python3 scripts/collect_deno_materials.py --destination build/deno-materials --resume
```

Use `--resume` only for an existing collector destination; cached downloads are verified. The orchestrator, bundler, and both platform packagers accept `--deno-materials` to reuse a completed collection matching current locks. It cannot be combined with development mode, or with `--prepared-tools` in the bundler. Collection gaps/errors, incomplete status, or changed files fail release validation.

## Materials and source obligations

The Deno collector covers the release source's entire root Cargo lock graph, including dev/unused/other-target packages; crate checksums and license declarations; native rusty_v8/V8 sources and recursive gitlinks; Rust **1.95.0** standard-library sources and its Cargo lock dependencies; attributed legal files/source notices; supplemental repository notices; and pinned canonical SPDX texts. It records license alternatives and MPL source mappings. The result is a **provenance superset**, not an exact link map of the official binary.

Observed completed collection: about **1.41 GiB uncompressed**, **1,102 archives**, and **80,185 manifest notice records**, with roughly **81k filesystem notice files**. Record counts and filesystem counts differ; budget space and inodes for both retained material and copied notice trees. Package sizes are measured separately, and packagers fail if a binary/source asset is **2 GiB or larger**.

Apply obligations by license and distributed component:

- **Media:** ship corresponding sources for the GPL FFmpeg/x264 build and linked dav1d, with matching configuration and build/install recipes. NASM sources are retained as build provenance; NASM itself is not shipped as a runtime tool. General-purpose build tools and qualifying system libraries are treated separately under the applicable license provisions.
- **Custom yt-dlp:** the core is Unlicense; official EJS includes Unlicense/MIT/ISC material. PyInstaller's bootloader exception permits freezing applications without automatically imposing the upstream combined standalone's GPLv3 classification. Preserve the exception and component notices. Certifi's MPL-2.0 source obligations are covered by its retained matching source, including `cacert.pem`. Python/native dependency notices and sources, and build-time package sources, are collected with the build map.
- **Deno:** preserve applicable third-party attribution, license, and NOTICE material and provide source where a component's license requires it, such as MPL-covered files. **MIT dependencies do not generally require source distribution merely because they use MIT.** Collecting all declared crate/native/Rust material is a provenance policy broader than those legal obligations.

The official Deno binaries lack a complete published link map. The v8 crate records a dirty checkout; its published checksum identifies the crate, while the recorded revision/gitlinks anchor supplemental native materials. These limitations remain in `materials.json`. Collection flags and manifest validation describe mechanical coverage/integrity, **not legal certification, a generic all-source attestation, or proof of bit-for-bit rebuild equivalence**. Review the recorded source-to-binary mapping, notices, and license-specific obligations before distribution.

### Prepared layout and release outputs

```text
<prepared stage>/
  tools/{yt-dlp,ffmpeg,ffprobe,deno}[.exe]
  tools/manifest.json
  licenses/tools/{yt-dlp,ffmpeg,deno}/...
  tool-sources/manifest.json
  tool-sources/yt-dlp/{build.json,sources/,inputs/,recipe/,notices/,...}
  tool-sources/ffmpeg/{build.json,sources/,notices/,...}
  tool-sources/deno/{materials.json,sources/,notices/,...}
  tool-sources/integration/...
```

The release tool manifest uses schema 2, records native-build or official-asset origins, lock fingerprints, and a hashed payload inventory. Packaging moves `tool-sources/` into the sibling source archive, retains runtime notices, and updates the runtime manifest's source-distribution pointer.

| Native packager | Local output |
| --- | --- |
| Linux | `ClipThat-linux-x64.flatpak`, `ClipThat-linux-x64-sources.tar.gz`, retained `repo/` |
| Windows | `ClipThat-windows-x64.zip`, `ClipThat-windows-x64-sources.zip`, `SHA256SUMS` |

Source archives contain `ClipThat-sources/`, the exact Git application archive (`application.tar` on Linux, `application.zip` on Windows), `tool-sources/`, and `release.json` provenance. CI supplies `SHA256SUMS-linux-x64` and names Windows checksums `SHA256SUMS-windows-x64`. Publish each complete platform set together and retain matching sources at the release location. See [release workflows](../../README.md#github-release-workflows) for existing-tag validation and token permissions. CI builds and collects inputs automatically without user-provided source URL/hash variables.

## Fast development bundling

```sh
python3 scripts/bundle_tools.py --platform linux-x64 --destination build/linux/x64/release/bundle --development
```

Development mode stages locked upstream prebuilt standalone yt-dlp, BtbN GPL FFmpeg/FFprobe, and official Deno, with limited notices and a schema-1 manifest marked `development: true, redistributable: false`. It avoids native release builds/material collection and is **non-redistributable**. Direct staging can target either platform without executing those binaries; that does not verify native compatibility. `make run` caches this development path by platform, lock hash, and bundler hash; the cache formula and development manifest schema are unchanged. Release preparation uses separate schema-2 manifests and never upgrades a development bundle into a release.
