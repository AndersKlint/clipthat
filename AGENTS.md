# ClipThat!

## App contract

- Target Flutter desktop on Windows x64 (portable ZIP) and Linux x64 (Flatpak) only. Preserve the `yt_section_downloader` package and executable identity.
- Branding: short name `ClipThat!`, full title `ClipThat! – Paste a Link. Grab Your Clip.`, studio Dr. Jetski Studios, website https://drjetski.com. Keep `!` in display names; use `com.drjetski.clipthat` for the native application ID.
- Support YouTube downloads only.
- Process clips sequentially: download the full source at up to 1080p into system temp, then precisely encode an H.264/AAC MKV with English VTT captions when available. Missing captions are a warning, not a failed clip.
- Keep queue state and output-directory selection in memory; no persistence.
- Bundle official upstream prebuilt yt-dlp (including Python/EJS), official compatible stable Deno for JavaScript challenges, and maintained BtbN GPL static stable-branch FFmpeg/FFprobe with libx264/native AAC beside the executable. Resolve latest stable yt-dlp every installer build; record selected versions rather than locking them. Refresh tools by rebuilding packages; no runtime tool downloads, updates, remote EJS, or PATH fallback.

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
- For tool staging or packaging changes, read `packaging/tools/README.md` and the platform packaging scripts. Use upstream prebuilts without custom tool builds/freezing, version locks, Deno source crawling, development/redistributable flags, or tool source archive outputs. Include upstream notices and source access records where available; actual license obligations remain, and records are not legal certification or a guarantee of compliance. Preserve `packaging/tools/*review.md` as historical findings.
- Use ordinary Python 3.x and Flutter stable with native Windows tooling; build Linux Flutter inside GNOME SDK 50 for runtime ABI compatibility, without SDK commit/interpreter pins. Keep prerequisite installation explicit through `make flatpak-setup`. Manual workflows upload binary packages and checksums as Actions artifacts without tag requirements or release publication.

## Workflow

- Delegate implementation to general agents with explicit file ownership, then review the combined changes for major issues and complete a Linux release build. Fix build failures and report which platforms were actually built.
- Do not add, modify, or run tests. Leave manual behavior checks to the user; provide checks for affected UI, queue behavior, output media, and failure handling. Skip builds for docs-only changes.
- On any sandbox permission problem, stop immediately and ask the user to whitelist the affected directory via `nano ~/.config/firejail/strict-dev.profile`; never edit that file yourself.
