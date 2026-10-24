# ClipThat!

## App contract

- Target Flutter desktop on Windows x64 (portable ZIP) and Linux x64 (Flatpak) only. Preserve the `yt_section_downloader` package and executable identity.
- Branding: short name `ClipThat!`, full title `ClipThat! – Paste a Link. Grab Your Clip.`, studio Dr. Jetski Studios, website https://drjetski.com. Keep `!` in display names; use `com.drjetski.clipthat` for the native application ID.
- Support YouTube downloads only.
- Process clips sequentially: download the full source at up to 1080p into system temp, then precisely encode an H.264/AAC MKV with English VTT captions when available. Missing captions are a warning, not a failed clip.
- Keep queue state and output-directory selection in memory; no persistence.
- Bundle pinned standalone `yt-dlp`, `ffmpeg`, `ffprobe`, and Deno beside the executable; release yt-dlp is a custom minimal standalone with official EJS. Require libx264 and AAC encoding support. No runtime tool downloads, updates, remote EJS, or PATH fallback.

## Implementation

- Keep rendering in widgets, shared colors/typography in the theme, and queue/process logic in controllers and services. Prefer small private widgets, composition, immutable data, and `const` constructors.
- Use minimal concrete abstractions; avoid speculative infrastructure and backward compatibility.
- Launch external processes directly with argument lists and shell execution disabled. Validate URLs and time ranges; treat user text and paths as data.
- Handle start failures, nonzero exits, malformed output, and filesystem errors explicitly with actionable UI feedback. Drain process streams and release process resources.
- Give each job its own temporary directory and clean it on success, failure, and cancellation. Remove incomplete output without deleting existing user files.
- Write self-documenting code. Comments may only be one-line technical explanations of non-obvious WHY; no WHAT comments, docstrings, or code summaries.

## Documentation

- When changing the download/tool contract, runtime dependencies, or packaging, read and update `requirements.md`.
- When changing setup, supported platforms, or developer commands, read and update `README.md`.
- For tool staging or release changes, follow `packaging/tools/README.md` and the platform packaging scripts: automated native tool builds and Deno material collection, matching source distributions and notices. Distinguish provenance collection from license-specific source obligations; manifest validation is not legal certification. Development bundles are not redistributable.

## Workflow

- Delegate implementation to general agents with explicit file ownership, then review the combined changes for major issues and complete a Linux release build. Fix build failures and report which platforms were actually built.
- Do not add, modify, or run tests. Leave manual behavior checks to the user; provide checks for affected UI, queue behavior, output media, and failure handling. Skip builds for docs-only changes.
- On any sandbox permission problem, stop immediately and ask the user to whitelist the affected directory via `nano ~/.config/firejail/strict-dev.profile`; never edit that file yourself.
