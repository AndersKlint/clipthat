# Windows x64 portable release

## Running the portable application

Extract the entire ZIP and run `ClipThat/yt_section_downloader.exe`. Keep DLLs, `data/`, `tools/`, `licenses/`, and `release.json` together. Python, yt-dlp, FFmpeg, FFprobe, and Deno need no separate installation. This file ships as `README-WINDOWS.md`.

Use Windows x64 supporting Flutter, Deno, and the bundled components; verify Windows 10 22H2 or newer on a clean target machine. The Microsoft Visual C++ v14 x64 runtime is a prerequisite, not included or installed by this package. For missing `VCRUNTIME140.dll`, `VCRUNTIME140_1.dll`, or `MSVCP140.dll`, install the [official x64 redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).

## Building the release

Build natively on Windows x64 with:

- **Official CPython 3.13.17 x64**, not MSYS2 Python, a debug/free-threaded build, or another rebuilt distribution. Collected Python binaries are checked against python.org's matching archive.
- Git, **Flutter 3.47.2** for the current release, and Visual Studio's Desktop development with C++ workload and Windows SDK. Flutter and Git must be on build-time PATH.
- **MSYS2 UCRT64** with GCC, Meson, Ninja, pkgconf, binutils, Make, Perl, diffutils, coreutils, and Bash. Use `MSYSTEM=UCRT64`; WSL/cross-compilation is unsupported.

Install native build packages in the UCRT64 shell:

```sh
pacman -S --needed mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-meson mingw-w64-ucrt-x86_64-ninja mingw-w64-ucrt-x86_64-pkgconf mingw-w64-ucrt-x86_64-binutils make perl diffutils coreutils bash
```

Commit application/packaging changes first. The packager requires a clean tree before and after Flutter compilation, including tracked generated plugin files and `pubspec.lock`. Review and commit any generated changes before retrying. Keep output inside ignored `dist/` or outside the repository. Choose simple build/output paths without spaces or shell/make metacharacters.

From the repository root in **MSYS2 UCRT64**, invoke the official Windows interpreter (adjust its path):

```sh
"/c/Python313/python.exe" scripts/package_windows.py --output-dir dist/windows-x64
```

Alternatively use `make installer` with native GNU Make and `PYTHON` pointing to that interpreter in the same environment. No source-directory argument or separately hosted source input is required.

The packager runs `flutter build windows --release --target-platform windows-x64`, copies the complete release bundle, and invokes `prepare_release_tools.py` automatically. It builds FFmpeg/FFprobe 8.1.3 with x264/dav1d and a custom minimal yt-dlp 2026.10.21 standalone with official EJS/certifi; it stages official Deno 2.9.8 after automatic crate/native V8/Rust standard-library material collection. See [tool preparation](../tools/README.md) for locks, obligations, and provenance limitations.

Optional internal `--prepared-tools` reuses a validated native release stage. `--deno-materials` reuses a completed collector directory when preparing tools. Normal packaging requires neither. This packager has no development bypass.

Before assembling archives, packaging checks startup of all four tools and FFmpeg's GPL/libx264 configuration and native AAC/libx264 encoders. Outputs:

- `ClipThat-windows-x64.zip`: portable `ClipThat/` application, Flutter/plugin DLLs, data, tools, notices, tool manifest, `README-WINDOWS.md`, and `release.json`.
- `ClipThat-windows-x64-sources.zip`: `ClipThat-sources/application.zip` from the exact clean Git revision, automated tool sources/materials, recipes, notices, manifests, lock, and release provenance.
- `SHA256SUMS`: hashes of both ZIPs. CI publishes this as `SHA256SUMS-windows-x64`.

Publish all three together. Each ZIP must be **smaller than 2 GiB** or packaging fails. Existing outputs are refused. Staging is temporary and leaves the Flutter build tree intact; completed artifacts are copied out only after packaging checks succeed. There is no MSI/installer EXE, signing, or automatic runtime installation. Manifest flags and hashes are integrity/provenance checks, not legal certification.

## Manual release checks

1. Extract into a path containing spaces; launch without host yt-dlp, FFmpeg, FFprobe, Deno, or Python on PATH. Verify the Visual C++ prerequisite on a clean machine.
2. Check UI resizing, invalid links/time ranges, and output-directory selection. Queue two clips; confirm sequential processing, retry, cancellation, temporary/incomplete-output cleanup, and preservation of existing files.
3. Inspect precise MKV trimming, H.264/AAC, and English VTT when available. Missing/disabled captions and caption fallback should not fail an otherwise valid clip.
4. Try network/restricted-video and unwritable/full-destination failures. In a disposable bundle, rename a tool and refresh status; confirm actionable guidance without PATH or runtime-install fallback, restore it, and retry.
5. Check both ZIP hashes, notices, manifests, and source mapping; keep the matching source ZIP available beside the portable ZIP.

Native Windows packaging and these behavior checks remain required; Linux host compilation does not verify Windows. The current app version remains `0.5.0-beta+1`, with release tag `v0.5.0-beta`. See [release workflow instructions](../../README.md#github-release-workflows).
