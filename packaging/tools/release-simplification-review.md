# Focused release simplification review

**Research date: 2026-10-25. Decision input for the parent review; no binary-contract change is authorized here.**

## Recommendation

Simplify the collection policy before replacing controlled minimal builds with much larger dependency sets. Official yt-dlp is a technically suitable replacement for the custom freeze, but **its release tarball plus third-party notices are not a complete frozen-binary corresponding-source bundle**. BtbN is the best maintained cross-platform FFmpeg candidate examined, but its published recipes/download machinery are not themselves proof of an exact, durable source bundle for a historical binary. Gyan is a credible Windows supplier, with less source-collection automation demonstrated by the reviewed public material.

Recommended minimal viable architecture:

1. Keep one pinned preparation entry point, adjacent tools, hash checking, retained notices, matching sibling source archives, and native runtime/capability checks. Keep app/platform packaging and existing release asset layout.
2. Retain the small FFmpeg/x264/dav1d source build initially. It has an unusually tractable source boundary: three runtime projects plus a build-only assembler. Replacing it with a full vendor build can remove compilation while increasing source/license maintenance substantially.
3. Treat adopting official yt-dlp as a conditional simplification: accept upstream's GPLv3+ combined distribution, obtain the missing exact dependency/native source mapping once per version/platform, and retain that material. Then remove the custom freezer and interpreter-profile machinery rather than retaining two release architectures. Do not promote today's development staging to redistributable status by changing a flag.
4. Narrow Deno collection to evidence-backed distributed-component notices and license-specific source requirements. Comprehensive Cargo/dev/other-target/Rust/native source capture is an optional provenance policy. Keep the existing collector until its replacement scope is actually established; deleting the superset without a substitute attribution/source map would trade visible complexity for uncertainty.

This is an engineering recommendation, not legal certification. If the parent prefers minimum compilation over minimum dependency surface, a pinned official yt-dlp + pinned BtbN GPL static pair + official Deno is viable in principle, subject to the source-closure work below. It is not demonstrated here to be the lower-maintenance release solution.

## Repository baseline and hotspots

Reviewed `AGENTS.md`, `requirements.md`, root `README.md`, `packaging/tools/README.md`, all four tool locks, `downloader.spec`, `build-media.sh`, builder/collector/orchestrator code, and both release workflows. Initial `git status --short` was empty. Local facts below refer to the checked-out files on the research date.

| Area | Current responsibility and maintenance cost |
| --- | --- |
| Downloader | `scripts/build_downloader.py` and `downloader.spec` freeze yt-dlp 2026.10.21, EJS 0.8.0 and certifi 2026.10.19 using PyInstaller 6.22.0. Exclusions avoid mutagen/readline/curl and other dependencies. It inventories frozen native modules, maps Linux SDK recipes, validates Windows Python against official archives/SPDX, and compares embedded bytes. This is the clearest removable custom machinery if upstream source correspondence is obtained. |
| Interpreter environments | `downloader-lock.json` couples GNOME SDK 50 commit/manifest/CPython 3.13.16 and GNOME/freedesktop recipe revisions; Windows CPython 3.13.17 and its binary/source SPDX must move with the Windows workflow. Every SDK/interpreter refresh can require renewed mapping, even when yt-dlp behavior is unchanged. |
| Media | FFmpeg 8.1.3, pinned x264 commit `c24e06c2e184345ceb33eb20a15d1024d9fd3497`, dav1d 1.5.4, NASM 2.16.03. `build-media.sh` disables autodetection/networking, allows file/pipe, and builds native GCC on both targets. Configuration, recipes and matching source inputs are already retained. The costs are compiler environments, capability allowlists and OS imports, rather than a sprawling source graph. |
| Deno | Official 2.9.8 binary plus `collect_deno_materials.py`: full root Cargo graph, dev/other-target packages, recursive native gitlinks, Rust 1.95.0 sources and dependency graph, canonical texts and source-level notice scanning. The documented 1.41 GiB / 1,102 archives / 80,185 notice records is an existing observation, not remeasured here. Dirty V8 metadata and absence of an official complete link map remain explicit limitations. This is the largest policy-driven material/inode burden. |
| Integration | `prepare_release_tools.py` schema-2 validation specifically requires native media/downloader origins and builder evidence. Bundling and source assembly copy/hash large material trees. Upstream substitution therefore requires an intentional origin/evidence contract revision, not just new download URLs. |
| CI | Linux builds in the locked SDK; Windows installs MSYS2 UCRT64 plus official CPython and Flutter. Both have 240-minute build jobs and 180-minute packaging steps. Native packaging remains necessary even if tool compilation goes away. Existing docs report Windows/SDK-contained Flatpak verification incomplete; this review does not change that status. |

The current minimal downloader meaningfully reduces licensing/dependency scope; it is not solely duplicate upstream build automation. Conversely, all-source collection for permissive dependencies is not automatically a distribution obligation. These two sources of complexity should be evaluated separately.

## Official yt-dlp 2026.10.21

### Platform and EJS fit

The release was published **2026-10-21 21:54:37 UTC**, is marked immutable by the GitHub release API, and provides the required standalone assets [Y1]. API digests match this repository's development lock:

| Target | Asset | Bytes | SHA256 |
| --- | --- | ---: | --- |
| Linux x86_64 | `yt-dlp_linux` | 40,569,080 | `d8bd33fca9d5b23bd5b9952b3fca36db5c46331933fda9f598a3da14ce2c243f` |
| Windows x64 | `yt-dlp.exe` | 17,880,111 | `33121d192d706e62f684a06f80918e3f3a8ba52ac3a65213b6951c39c7d9f555` |

The versioned README identifies Linux glibc 2.17+ and Windows Win8+ for these artifacts; these are upstream tool floors, not certification of ClipThat!'s complete platform stack [Y2]. The similarly named Unix `yt-dlp` is a Python-dependent zipimport executable and cannot replace the standalone under the current contract. The `yt-dlp_linux.zip` and `yt-dlp_win.zip` alternatives are directory distributions; copying only their launcher loses dependencies [Y2].

**EJS is bundled; a JavaScript runtime is not supplied by that fact.** Upstream explicitly says official PyInstaller executables include yt-dlp-ejs, while YouTube challenge solving still requires a supported runtime. EJS 0.8.0 is pinned in the tag's requirements and Makefile [Y3, Y5, Y6]. Deno remains recommended, with minimum 2.3.0 in the EJS guide (page displayed last edit 2026-07-12, accessed 2026-10-25) [Y3]. Keep separately bundled Deno and explicit `--js-runtimes deno:<absolute-path>`, clear defaults, disable plugins/configuration/updates/remote components. No remote EJS fetch is necessary with the official binary [Y2–Y3].

### Exactly what upstream supplies, and what it does not establish

The API asset list contains binaries/directory ZIPs, `yt-dlp.tar.gz`, SHA256/SHA512 checksum files with detached signatures, and `_update_spec`; it does **not** list an all-dependencies source archive or SBOM/link-map asset [Y1]. GitHub also exposes generated repository source snapshots; these are distinct from the uploaded release tarball.

The uploaded **`yt-dlp.tar.gz` is 6,028,705 bytes**, SHA256 `5f1e419f76e49c996061511ef9eacce50d4aa4959c34480539562e9e1295708d` [Y1]. An in-memory HTTP download during this review independently matched that digest and inspected its member list. It contains yt-dlp Python sources, the Unix executable, Makefile, pyproject, devscripts, documentation/completions and upstream test material. It contains **neither `bundle/`, `.github/workflows/`, `THIRD_PARTY_LICENSES.txt`, nor a `yt_dlp_ejs/` source tree**. The tar recipe's explicit input list corroborates those omissions [Y6]. The Unix executable within the release can bundle generated EJS, but that does not make this tarball a source distribution of Python, mutagen, curl-impersonate or the other frozen dependencies.

The **tagged repository** separately supplies `LICENSE` (Unlicense), `THIRD_PARTY_LICENSES.txt`, build workflows, PyInstaller bundling code, Docker inputs, and hash-pinned Python requirement files [Y2, Y4–Y7]. Retain that snapshot as well as the uploaded tarball if using the official executable. The build workflow uses Python **3.14** for the Linux matrix and **3.10** for Windows x64; these differ from ClipThat!'s custom interpreter pins [Y7]. A requirement's source/wheel hashes help recover packages, but do not alone map every embedded native library or exact interpreter patch to source.

The tagged README explicitly classifies the **combined PyInstaller executable as GPLv3+**, although the core is Unlicense [Y2]. The third-party aggregation says source is available from the original projects and offers help from `maintainers@yt-dlp.org` if it cannot be obtained [Y4]. That is useful escalation evidence, not a ready-made downstream corresponding-source archive or an automatic transfer of ClipThat!'s distribution responsibilities.

The notice file covers these component groups (it is a cross-platform aggregation, **not a per-platform/version link map**) [Y4]:

- Python/PSF; Microsoft Distributable Code on Windows; bzip2; libffi; OpenSSL 1.x and 3.x notices; SQLite; liblzma; mpdecimal; zlib; Expat; ncurses; GNU Readline; libstdc++/libgcc with GCC runtime exception; libuuid; libintl; libidn2 including Unicode data; libunistring.
- curl-impersonate/curl, BoringSSL, nghttp2/ngtcp2/nghttp3, zstd/brotli, curl_cffi, Tornado/httpx/cffi/pycparser.
- mutagen (GPL-2.0-or-later), PyCryptodome, certifi (MPL-2.0), requests, charset-normalizer, idna, urllib3, SecretStorage/cryptography/Jeepney, websockets, Meriyah (ISC), Astring (MIT).

Readline is marked Linux-only; native GPL/LGPL components and mutagen explain why treating this as merely Unlicense + certifi is incorrect. Preserve full upstream notice texts and required copyright/NOTICE material, plus a GPLv3 license copy; the core `LICENSE` alone is insufficient. Do not infer exact OpenSSL versions or shipped libraries solely from generic notice headings.

**Conclusion:** official release assets make a custom freeze unnecessary for functionality and eliminate responsibility for producing that executable. They do not eliminate dependency-source/licensing work. Before replacing it, establish exact Python/native/curl component versions and patches per platform, obtain GPL/LGPL corresponding sources and build/install scripts, retain certifi's covered source and other applicable materials, and resolve any mapping gaps with upstream. A small source manifest driven by upstream requirements is preferable to recreating the entire upstream CI system. Exact bit reproduction is a separate goal.

## Maintained FFmpeg alternatives

### BtbN: preferred vendor candidate, conditional on source closure

BtbN documents daily successful builds for Windows and Linux x64, static `gpl` and `lgpl` variants and shared counterparts, plus release-branch addins [F1]. Its currently documented Linux baseline is glibc 2.28 / Linux 4.18; Windows minimum supported is Windows 10 22H2 with UCRT requirements. These baseline docs were read on 2026-10-25 and may change.

Select **`gpl`, static**, not `lgpl` (omits libx264), not `nonfree` (adds fdk-aac), and avoid shared builds' DLL/library staging complexity. Native AAC needs no fdk-aac [F1]. At the repository's already pinned recipe commit **`6c9aec5fc9a72ec3abedd1fa84db141fa18cf52b`**, GPL defaults set `--enable-gpl --enable-version3`, x264 enables `--enable-libx264` at commit `0480cb05fa188d37ae87e8f4fd8f1aea3711f7ee`, and dav1d enables `--enable-libdav1d` at commit `9711965b60bb692ae24004659acf61f5c7d9ed61` [F2–F4]. These are not the current custom build's dependency revisions.

The existing development lock names the **2026-09-30 13:08** pair, version **`n8.1.3-9-g29e619e767`**:

- `ffmpeg-n8.1.3-9-g29e619e767-linux64-gpl-8.1.tar.xz`, SHA256 `97ce978979194b5cf7e06a5e68020dbdaa7a4f3294c5452b6a1bc347100dbb79`.
- `ffmpeg-n8.1.3-9-g29e619e767-win64-gpl-8.1.zip`, SHA256 `7b801cdd3a1a0bb54ae6f572187e68b4ed54f52086cfee133fab2180bfb429fa`.

Those are local lock facts, not newly downloaded/verified vendor binaries in this review. Do not describe them as exactly FFmpeg 8.1.3: the version includes nine later commits. For a future selection, pin a dated retained release, full FFmpeg commit and recipe commit, archive bytes/hash, dependency revisions, patches, and configuration. Do not use `latest` URLs. The vendor retains only 14 daily builds and month-end builds for two years, so keep required sources and artifacts independently [F1].

**Source-fetching feasibility:** public `scripts.d/` provides per-package repositories/revisions, configuration and patch operations; `download.sh` invokes their download functions into a compressed cache, with a hash of the download recipe used as a cache identity [F3–F6]. This is a strong automation starting point. It is not an upstream digest of source content and not, by itself, evidence that a particular binary used that cache. The workflow uploads a download-cache Actions artifact, while release publication attaches binary archives/checksums; the inspected static packaging copies binaries, docs/manpages/presets and a GPL license rather than an all-library source bundle [F7–F8].

An automated collector can archive the exact vendor recipe tree/patches, resolve enabled package inputs to immutable commits/checksums, fetch source archives/git submodules, retain required notices, and publish them alongside the binaries. It must include **all linked dependencies that fall within corresponding-source scope**, not only x264/dav1d. Vendor GPL builds deliberately include a broad library set, so reusing their binaries may need a larger collector than the present three-project build. Public recipes reduce reverse engineering, but exact historical binary-to-image/dependency mapping remains unverified here. Do not reconstruct it from today's master scripts.

Capability expectation is strong from recipes, not execution evidence: verify the chosen pair's native `aac`, `libx264`, `libdav1d`, WebVTT/Matroska and required demuxers, configuration free of `--enable-nonfree`, and runtime imports on both platforms before adoption. Stock binaries also enable more protocols/features than the current file/pipe-only build. That would need explicit parent approval as a tool-contract change.

### Gyan: maintained Windows alternative, not a cross-platform simplifier

The supplier page on 2026-10-25 lists **release 9.0.2 (2026-09-19)** and latest git build **2026-10-22, `bf0e831606`**; Windows 10+, x64, GPLv3 static builds and a full shared variant are documented [G1]. This establishes active maintenance, not compatibility of a specific downloaded package.

Gyan essentials includes libx264 and internal components (including native AAC), but **libdav1d is in full only**. For the stated dav1d requirement, select full static, not essentials. No nonfree build is needed; the supplier explicitly excludes `--enable-nonfree` for custom builds [G1]. Full brings many more libraries than ClipThat! needs.

Version/checksum text endpoints and dated package URLs support automated binary acquisition. The page links matching FFmpeg commits, says package README files contain full internal/external configuration and external library versions, and provides public support contacts. However, this review did **not** establish a public version-matched, all-dependency source/patch/build-script bundle or public complete build-recipe repository from those links. A core FFmpeg commit plus library version list does not close that gap. Ask the supplier for matching materials before choosing it for redistributable packaging. Lack of evidence here is not a finding that the supplier violates a license.

Using Gyan on Windows and a different Linux provider doubles supplier-specific source and configuration handling. Prefer BtbN for both platforms if the parent chooses prebuilts and can establish exact source correspondence. No additional vendor is needed to decide this focused question.

## Obligations versus optional provenance

The authoritative distinction is the license text, especially GPLv3 §§1, 4–6 [L1], not whether a build ran locally:

| Material/activity | Release relevance |
| --- | --- |
| Matching preferred-form sources, applied patches, necessary build/install control scripts and dependency sources within the corresponding-source definition | Required for the chosen GPL distribution route; unchanged vendor binaries still carry obligations. Include linked x264/dav1d and other included code as applicable. |
| Equivalent source access beside download, with clear directions and retained availability | GPLv3 §6(d) permits network source on another server but leaves the distributor responsible for availability. Keeping sibling source archives is a simple operational choice. A generic upstream homepage or email sentence is not equivalent evidence of complete accessible corresponding source. |
| Full GPL texts and component attribution/NOTICE/license preservation | Retain applicable notices in runtime distribution and sources; upstream's combined GPL label does not erase underlying notices. |
| MPL-covered source, including certifi and covered Deno dependency files | Provide the applicable source/access and notices under that license; this is distinct from collecting every permissively licensed dependency's source. |
| Sources for unmodified general-purpose compilers/tools and qualifying System Libraries | GPLv3 §1 has exclusions. Do not require an entire OS/compiler source archive solely because it participated in the build. Static runtime exceptions and individual component terms still require evaluation. |
| Complete Cargo lock graph including unused/dev/other-target crates, whole Rust source ecosystem, every source comment scanned as a notice, build-only NASM source archive | Broader provenance policy; not automatically required merely because present in an upstream workspace/build environment. Required attribution still needs evidence-backed coverage. |
| Cryptographic pins, signatures, inventories, exact compiler/image versions and byte comparisons | Useful integrity/source-correspondence evidence. Neither license certification nor a universal requirement for bit-reproducible output. |

FFmpeg's legal page explains optional GPL components and exact source/configuration concerns, but its checklist specifically targets **LGPL library linking** [L2]. Its advice to omit GPL/libx264 cannot be copied as a requirement for this app's intended GPL executable distribution. ClipThat! launches separate tools with process arguments; retaining independent executable boundaries is sensible. GPLv3 §5 recognizes aggregates, but process separation alone is not a blanket legal determination about every integration [L1].

## Parent decision and remaining uncertainties

**Best immediate simplification target:** the broad provenance policy and interpreter/freeze mapping burden. **Best reason to retain a custom component:** a deliberately small FFmpeg dependency/configuration boundary. Do not assume replacing both builders simultaneously yields the least overall work.

Before approving a switch, resolve:

1. **yt-dlp correspondence:** exact official Python patch/native/curl build inputs, patches and source coverage for Linux x64 and Windows x64; determine which generic third-party notices actually apply to each binary. The source tarball omission is verified; completeness of an alternative assembled source set is not.
2. **BtbN correspondence:** tie the selected binary to its exact builder revision/image, enabled library revisions and patches, and archive accessible source materials before vendor retention expires. Current recipes/CI cache availability do not settle old-build mapping.
3. **Gyan materials:** obtain supplier confirmation and accessible matching dependency sources/recipes/patches if it remains a candidate. Public page evidence alone was insufficient.
4. **Deno scope:** establish distributed-component attribution/source coverage before narrowing collection. The existing all-graph inventory cannot be equated with an exact official-binary link map.
5. **Operational fit:** parent-directed native startup/Flatpak runtime compatibility, no host-tool fallback, bundled EJS with remote fetching disabled, full-source YouTube download, sequential queue/cancellation/cleanup, precise H.264/AAC MKV with available English VTT, caption warning/fallback, and actionable failures. Media/capability checks need actual selected binaries; none were executed here.

No tests or builds were added or run. Research used read-only HTTP and in-memory archive inspection; no `gh`, account configuration, publication, tags or commits were used. Only this review document was created.

## Primary sources

All URLs accessed 2026-10-25. Tagged/commit links anchor claims; master/vendor pages are dated observations rather than permanent version facts.

- **[Y1]** [yt-dlp 2026.10.21 release API and asset digests](https://api.github.com/repos/yt-dlp/yt-dlp/releases/tags/2026.10.21); [release page](https://github.com/yt-dlp/yt-dlp/releases/tag/2026.10.21); [uploaded source tarball](https://github.com/yt-dlp/yt-dlp/releases/download/2026.10.21/yt-dlp.tar.gz).
- **[Y2]** [Versioned README: artifacts, licensing, dependencies and CLI controls](https://github.com/yt-dlp/yt-dlp/blob/2026.10.21/README.md).
- **[Y3]** [Official EJS setup guide: bundled scripts versus separate runtime](https://github.com/yt-dlp/yt-dlp/wiki/EJS).
- **[Y4]** [Versioned third-party license aggregation and source contact statement](https://github.com/yt-dlp/yt-dlp/blob/2026.10.21/THIRD_PARTY_LICENSES.txt).
- **[Y5]** [Versioned, hash-pinned default package requirements](https://github.com/yt-dlp/yt-dlp/blob/2026.10.21/bundle/requirements/default.txt).
- **[Y6]** [Versioned Makefile: source tar member list and EJS 0.8.0 inputs](https://github.com/yt-dlp/yt-dlp/blob/2026.10.21/Makefile).
- **[Y7]** [Versioned upstream build workflow](https://github.com/yt-dlp/yt-dlp/blob/2026.10.21/.github/workflows/build.yml).
- **[F1]** [BtbN maintained variants, baselines and retention policy](https://github.com/BtbN/FFmpeg-Builds/blob/master/README.md).
- **[F2]** [Pinned GPL defaults](https://github.com/BtbN/FFmpeg-Builds/blob/6c9aec5fc9a72ec3abedd1fa84db141fa18cf52b/variants/defaults-gpl.sh).
- **[F3]** [Pinned x264 recipe](https://github.com/BtbN/FFmpeg-Builds/blob/6c9aec5fc9a72ec3abedd1fa84db141fa18cf52b/scripts.d/50-x264.sh).
- **[F4]** [Pinned dav1d recipe](https://github.com/BtbN/FFmpeg-Builds/blob/6c9aec5fc9a72ec3abedd1fa84db141fa18cf52b/scripts.d/50-dav1d.sh).
- **[F5]** [Pinned dependency download/cache machinery](https://github.com/BtbN/FFmpeg-Builds/blob/6c9aec5fc9a72ec3abedd1fa84db141fa18cf52b/download.sh); [default Git downloader](https://github.com/BtbN/FFmpeg-Builds/blob/6c9aec5fc9a72ec3abedd1fa84db141fa18cf52b/util/dl_functions.sh).
- **[F6]** [Pinned full package recipe directory](https://github.com/BtbN/FFmpeg-Builds/tree/6c9aec5fc9a72ec3abedd1fa84db141fa18cf52b/scripts.d).
- **[F7]** [Maintained BtbN workflow: cache artifact and release publication](https://github.com/BtbN/FFmpeg-Builds/blob/master/.github/workflows/build.yml).
- **[F8]** [Pinned binary build/package script](https://github.com/BtbN/FFmpeg-Builds/blob/6c9aec5fc9a72ec3abedd1fa84db141fa18cf52b/build.sh); [static Linux package contents](https://github.com/BtbN/FFmpeg-Builds/blob/6c9aec5fc9a72ec3abedd1fa84db141fa18cf52b/variants/linux-install-static.sh).
- **[G1]** [Gyan supplier downloads, library matrix, configuration/version notes and API](https://www.gyan.dev/ffmpeg/builds/).
- **[L1]** [GNU GPL version 3, especially §§1, 4, 5 and 6](https://www.gnu.org/licenses/gpl-3.0.html).
- **[L2]** [FFmpeg license/legal guidance](https://ffmpeg.org/legal.html).
