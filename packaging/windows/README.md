# Windows x64 portable ZIP and Inno Setup installer

## Installing and uninstalling

Verify `ClipThat-windows-x64-setup.exe` against `SHA256SUMS-windows-x64`, then run it on native x64 Windows. Setup installs per-user to `%LOCALAPPDATA%\Programs\ClipThat!` without administrator privileges. It creates a Start Menu shortcut, offers an optional desktop shortcut, and offers to launch the app after installation. Both Windows assets are unsigned.

Close the app before upgrading, then run the new Setup for the same user and installation directory. Uninstall through Windows Settings > Apps. Store output clips outside the application directory. Setup includes the same application, bundled tools, licenses, and data as the portable ZIP; it does not install the Visual C++ runtime or update tools at runtime.

## Running the portable application

Verify `ClipThat-windows-x64.zip` against `SHA256SUMS-windows-x64`, extract the entire ZIP and run `ClipThat/yt_section_downloader.exe`. Keep DLLs, `data/`, `tools/`, notices, and accompanying metadata together. Python, yt-dlp, FFmpeg, FFprobe, and Deno need no separate installation. This file ships as `README-WINDOWS.md`. To upgrade, close the app and extract the new ZIP into a fresh directory. To remove it, close the app and delete its extracted directory; keep output clips separately.

Use Windows x64 supporting Flutter, Deno, and the bundled components; verify Windows 10 22H2 or newer on a clean target machine. The Microsoft Visual C++ v14 x64 runtime is a prerequisite, not installed by this package. For missing `VCRUNTIME140.dll`, `VCRUNTIME140_1.dll`, or `MSVCP140.dll`, install the [official x64 redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).

Tools are bundled upstream binaries: official stable yt-dlp with Python/EJS, official compatible stable Deno for JavaScript challenges, and BtbN GPL static stable-branch FFmpeg/FFprobe with libx264 and native AAC. The app never downloads or updates tools at runtime or falls back to PATH. Rebuild and install a new package to refresh tools; installed packages do not update tools by themselves.

## Building the package

Build natively on Windows x64 with ordinary **Python 3.x**, **Flutter stable**, Git, native GNU Make, Visual Studio's Desktop development with C++ workload, Windows SDK, and **Inno Setup 6.3+**. Install Inno Setup from [upstream](https://jrsoftware.org/isinfo.php) or with `choco install innosetup --yes`. Packaging discovers `ISCC.exe` on PATH or in the standard `Inno Setup 6` directory under `ProgramFiles(x86)` / `ProgramFiles`; there is no extra compiler override. No MSYS2 or exact interpreter version is required.

From the repository root:

```sh
make windows-installer
```

`make windows-zip` is an alias; both commands always produce **both** the ZIP and setup EXE by invoking `python scripts/package_windows.py`. `make installer` / `make installers` selects this dual-output packaging on Windows. `make build` performs only Flutter's native build; `make run` builds, stages prebuilt tools, and launches the application.

The Inno Setup definition is `packaging/windows/clipthat.iss`. Setup uses `GetFileVersion` on the built `yt_section_downloader.exe` for its version; it does not parse release tags or `pubspec.yaml`.

Each installer build resolves the latest stable official yt-dlp and selects compatible stable Deno and stable-branch FFmpeg binaries. Selected versions and download details are recorded, not version locks. Packaging does not compile or freeze tools, crawl Deno sources, or require manually supplied source archives or repository variables. See [tool packaging](../tools/README.md) for upstream selection and license obligations.

Validate startup of all four tools and libx264/native AAC encoding support before considering packaging complete. The outputs are `dist/windows-x64/ClipThat-windows-x64.zip`, `ClipThat-windows-x64-setup.exe`, and `SHA256SUMS-windows-x64` listing both binaries. Both assets include the complete app, tools, upstream notices, and available source access records. No sibling tool source ZIP is produced.

Both assets include `licenses/ClipThat-LICENSE.txt` (MIT for ClipThat!'s own code) and `licenses/THIRD_PARTY_NOTICES.md`; bundled components retain their own terms. There is no MSI, signing, or automatic Visual C++ runtime installation.

Before public distribution, obtain complete matching supplier source/build materials for official standalone yt-dlp and BtbN FFmpeg: no verified complete, durable, exact-matching corresponding-source download bundle has been found. Remaining Deno native/Cargo notices and MPL source applicability also need resolution. Generic recipes or core archives are insufficient. Required sources may be separate accessible downloads; users need not download them to install. Current tooling generates no complete source bundle. See [licensing gaps and remedy](../tools/README.md#licenses-and-source-access).

## Manual checks

1. Verify both binary checksums. Extract the ZIP into a path containing spaces; launch without host yt-dlp, FFmpeg, FFprobe, Deno, or Python on PATH. Verify the separate Visual C++ prerequisite on a clean machine for both distributions.
2. Install Setup as a standard user on native x64 Windows. Check the per-user location, Start Menu shortcut, optional desktop shortcut, and optional launch. Close the app, upgrade with a new package, and verify startup and all four tools. Uninstall through Windows Settings; check removal of application files/shortcuts and preservation of output clips stored outside the application directory.
3. Check UI resizing, invalid links/time ranges, and output-directory selection. Queue two clips; confirm sequential processing, retry, cancellation, temporary/incomplete-output cleanup, and preservation of existing files.
4. Inspect precise MKV trimming, H.264/AAC, and English VTT when available. Missing/disabled captions and caption fallback should not fail an otherwise valid clip.
5. Try network/restricted-video and unwritable/full-destination failures. In a disposable bundle, rename a tool and refresh status; confirm actionable repair guidance, restore it, and retry.
6. Check selected tool versions, notices, and available source access records against the bundled binaries.

Native Windows packaging and these behavior checks remain required; Linux builds do not verify Windows. The workflow ensures Inno Setup is available using Chocolatey and retains the ZIP, setup EXE, and platform checksums as Actions artifacts. Manual `workflow_dispatch` requires no tag and does not publish a release. Pushing a `v*` tag triggers Windows and Linux builds; successful platforms independently publish their distinct assets to the same nondraft, nonprerelease GitHub Release. A failed platform may leave partial assets until retry. See [workflow instructions](../../README.md#github-release-workflows).
