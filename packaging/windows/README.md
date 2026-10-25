# Windows x64 portable package

## Running the portable application

Extract the entire ZIP and run `ClipThat/yt_section_downloader.exe`. Keep DLLs, `data/`, `tools/`, notices, and accompanying metadata together. Python, yt-dlp, FFmpeg, FFprobe, and Deno need no separate installation. This file ships as `README-WINDOWS.md`.

Use Windows x64 supporting Flutter, Deno, and the bundled components; verify Windows 10 22H2 or newer on a clean target machine. The Microsoft Visual C++ v14 x64 runtime is a prerequisite, not installed by this package. For missing `VCRUNTIME140.dll`, `VCRUNTIME140_1.dll`, or `MSVCP140.dll`, install the [official x64 redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).

Tools are bundled upstream binaries: official stable yt-dlp with Python/EJS, official compatible stable Deno for JavaScript challenges, and BtbN GPL static stable-branch FFmpeg/FFprobe with libx264 and native AAC. The app never downloads or updates tools at runtime or falls back to PATH. Rebuild and install a new package to refresh tools; installed packages do not update tools by themselves.

## Building the package

Build natively on Windows x64 with ordinary **Python 3.x**, **Flutter stable**, Git, native GNU Make, Visual Studio's Desktop development with C++ workload, and Windows SDK. No MSYS2 or exact interpreter version is required.

From the repository root:

```sh
make windows-installer
```

`make windows-zip` is an alias; `make installer` / `make installers` selects this package on Windows. `make build` performs only Flutter's native build; `make run` builds, stages prebuilt tools, and launches the application.

Each installer build resolves the latest stable official yt-dlp and selects compatible stable Deno and stable-branch FFmpeg binaries. Selected versions and download details are recorded, not version locks. Packaging does not compile or freeze tools, crawl Deno sources, or require manually supplied source archives or repository variables. See [tool packaging](../tools/README.md) for upstream selection and license obligations.

Validate startup of all four tools and libx264/native AAC encoding support before considering packaging complete. The outputs are `dist/windows-x64/ClipThat-windows-x64.zip` and `SHA256SUMS-windows-x64`. The ZIP includes the complete portable app, tools, upstream notices, and available source access records. No sibling tool source ZIP is produced.

This is a portable ZIP, without an MSI/installer EXE, signing, or automatic Visual C++ runtime installation. Upstream source links and notices are not legal certification or a guarantee that GPL/MPL/other obligations have been fully discharged.

## Manual checks

1. Verify the ZIP checksum. Extract into a path containing spaces; launch without host yt-dlp, FFmpeg, FFprobe, Deno, or Python on PATH. Verify the Visual C++ prerequisite on a clean machine.
2. Check UI resizing, invalid links/time ranges, and output-directory selection. Queue two clips; confirm sequential processing, retry, cancellation, temporary/incomplete-output cleanup, and preservation of existing files.
3. Inspect precise MKV trimming, H.264/AAC, and English VTT when available. Missing/disabled captions and caption fallback should not fail an otherwise valid clip.
4. Try network/restricted-video and unwritable/full-destination failures. In a disposable bundle, rename a tool and refresh status; confirm actionable repair guidance, restore it, and retry.
5. Check selected tool versions, notices, and available source access records against the bundled binaries.

Native Windows packaging and these behavior checks remain required; Linux builds do not verify Windows. The manual `workflow_dispatch` workflow uploads the ZIP and checksums as Actions artifacts without requiring a tag or publishing a GitHub release. See [workflow instructions](../../README.md#github-release-workflows).
