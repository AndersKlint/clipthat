# Windows x64 portable release

## Running the portable application

Extract the entire portable ZIP and run `ClipThat/yt_section_downloader.exe`.
Keep its DLLs, `data/`, `tools/`, and `licenses/` together. Python, yt-dlp,
FFmpeg, FFprobe, and Deno do not need separate installation.

Use Windows 10 22H2 or newer, x64. The Microsoft Visual C++ v14 x64 runtime
(the runtime used by Visual Studio 2015 and later) is an OS prerequisite;
it is not installed or included by this portable package. If Windows reports
missing `VCRUNTIME140.dll`, `VCRUNTIME140_1.dll`, or `MSVCP140.dll`, install the
supported x64 redistributable from Microsoft's official instructions:
https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist

This file is included as `README-WINDOWS.md` in the portable application ZIP.

## Building the release

Run on Windows x64 with 64-bit Python 3.10+, Git, and Flutter's Windows desktop
toolchain (Visual Studio C++ desktop workload and Windows SDK). There is no
cross-compilation path. Flutter and Git must be on PATH at build time; the
application uses the packaged tools exclusively at runtime.

Prepare the matching source inputs described in `packaging/tools/README.md`,
then commit application and packaging changes. Release packaging refuses dirty
or untracked repository files so `application.zip` corresponds to the build's
Git revision. `release-sources/` and `dist/` are ignored for local preparation.
Keep a custom output directory outside the repository or Git-ignored too.

The post-build clean-tree check also covers tracked generated plugin registrants
and `generated_plugins.cmake`. If Flutter refreshes these or `pubspec.lock`,
review and commit those changes, then rerun packaging. They are not silently
excluded from the source-to-binary check. Ordinary build output and Windows
Flutter ephemeral files are already ignored.

On Windows, `shutil.which("flutter")` normally resolves `flutter.bat`. Python
supports launching that batch file with an argument list and `shell=False`;
Windows may invoke its command interpreter internally. Flutter receives only
fixed build/version arguments, not source or output paths from CLI inputs.

From the repository root, in PowerShell:

```powershell
python scripts/package_windows.py --help
python scripts/package_windows.py --sources-dir release-sources/windows-x64 --output-dir dist/windows-x64
```

The script validates source inputs before building, invokes
`flutter build windows --release --target-platform windows-x64`, copies the
complete `build/windows/x64/runner/Release` tree, bundles verified tools, checks
tool startup, FFmpeg GPL/libx264 configuration and native AAC/libx264 encoders,
and creates:

* `ClipThat-windows-x64.zip`: complete portable application in `ClipThat/`,
  including Flutter DLLs, plugins, data, offline tools, licenses, tool manifest
  `README-WINDOWS.md`, and `release.json` build provenance.
* `ClipThat-windows-x64-sources.zip`: `ClipThat-sources/application.zip` from the
  exact clean Git revision, prepared tool source archives, notices, compliance
  notes, source manifest, pinned lock, and matching build provenance.
* `SHA256SUMS`: hashes of both ZIPs.

The executable remains `yt_section_downloader.exe`. Publish both ZIPs and
`SHA256SUMS` together. Existing output files are refused; use a new output
directory for another release. The Flutter build tree is not modified by tool
staging. Artifacts are assembled in a temporary directory and published only
after every packaging step succeeds. No installers, signing, or MSVC runtime
redistributable installation are performed. Verify the Flutter/MSVC runtime
prerequisites on a clean supported Windows machine before publishing.

Manual release checks:

1. Extract the portable ZIP in a path containing spaces. Start the executable
   without yt-dlp, FFmpeg, FFprobe, Deno, or Python on PATH.
2. Queue two YouTube clips and confirm sequential processing, cancellation and
   temporary-file cleanup. Confirm invalid links/time ranges give useful errors.
3. Inspect resulting MKV files for precise trimming, H.264/AAC, and English VTT
   captions when available. Missing captions should only warn.
4. Rename a bundled executable and confirm actionable failure without PATH or
   network installation fallback. Restore it and retry.
5. Check both ZIP hashes, inspect license/notice files and source mapping, and
   verify the matching source distribution is available beside the portable ZIP.
