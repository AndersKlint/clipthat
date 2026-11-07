# ClipThat!

## App contract

- Target Flutter desktop on Windows x64 (portable ZIP) and Linux x64 (Flatpak) only. Preserve the `yt_section_downloader` package and executable identity.
- Branding: short name `ClipThat!`, full title `ClipThat! – Paste a Link. Grab Your Clip.`, studio Dr. Jetski Studios, website https://drjetski.com. Keep `!` in display names; use `com.drjetski.clipthat` for the native application ID.
- Support YouTube downloads only.
- Process clips sequentially using full sources cached by YouTube video ID and requested quality. Desired quality defaults to Best available, with resolution caps; queued quality is immutable through retries. Precisely encode lossy H.264/AAC MKV at source resolution with only selected eligible VTT subtitle tracks. Keep manual and automatic selections distinct; use no all-language fallback. Missing captions warn rather than failing the clip. For quality choices, cache lifecycle, clearing, and job-temp fallback, read `requirements.md#download-behavior-and-limits`.
- Persist only the last output-directory preference, from Browse or typed edits, and restore it on launch or use platform defaults. Keep queue, theme, quality, and subtitle state memory-only; completed source cache is disposable storage separate from preferences. Restored Flatpak portal paths may require Browse reselection; retain portal-based access without blanket filesystem grants.
- Render subtitle switches label-left/switch-right: Download subs defaults on and gates all subtitle downloads; `Include auto generated subs (experimental)` sits below it, defaults off, and is disabled when Download subs is off. Its tooltip warns automatic subtitles, especially uncommon languages, can often fail. Experimental off filters dropdown/chips and effective queued tracks to manual only; on includes original automatic and translated tracks. Retain hidden automatic selections across toggles. Download subs off hides/disables the picker and queues empty tracks while retaining selections and experimental state in memory; on restores them.
- Use a searchable multi-select chip field with a floating anchored popup on focus, not inline expansion. Highlight the active row with a neutral background and normal text, not red. Freely select individual manual, original automatic, and translated tracks; list per-video manual/original options first and keep translated labels such as `Swedish (auto translated)`. Allow unlimited selections; show a short possible-HTTP-429 warning above five. Original-English manual captions may default when available. Queue only immutable effective track selections, empty with subtitles off, with no automatic boolean; later edits leave jobs and retries unchanged. Keep selection state session-only.
- Discover subtitles once per current video on field focus/submit, never per search keystroke, with no metadata-discovery sleep; metadata failure offers UI retry or subtitles off. Pace subtitle downloads/request extraction by five seconds without promising rate-limit prevention. On HTTP 429, stop further subtitle requests for that job and finish with available valid tracks and a compact warning. See `requirements.md#download-behavior-and-limits` for the download contract and `requirements.md#manual-release-checks` for manual checks.
- Use neutral near-white field focus in dark mode and near-black in light mode; retain red validation errors and brand-colored buttons.
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
- For tool staging or packaging changes, read `packaging/tools/README.md`, `THIRD_PARTY_NOTICES.md`, and the platform packaging scripts. Use upstream prebuilts without custom tool builds/freezing or version locks.
- Scope MIT to ClipThat!'s own code; keep third-party terms and CC0-1.0 metadata separate. Package `licenses/ClipThat-LICENSE.txt`, `licenses/THIRD_PARTY_NOTICES.md`, upstream notices, and source links; do not claim complete corresponding source or waived redistribution obligations.
- Use ordinary Python 3.x and Flutter stable with native Windows tooling; build Linux Flutter inside GNOME SDK 50 for runtime ABI compatibility, without SDK commit/interpreter pins. Keep prerequisite installation explicit through `make flatpak-setup`.
- Retain binary packages and platform checksums as Actions artifacts. Manual workflows require no tag and do not publish releases; pushed `v*` tags trigger both platforms to publish successful packages to one nondraft, nonprerelease GitHub Release. Use separate publish jobs with job-scoped `contents: write`, `softprops/action-gh-release@v2`, and shared publishing concurrency. Allow partial assets until a failed platform is retried; require no tag/pubspec matching, automatic version parsing, or generated notes. See `README.md#github-release-workflows` for details.

## Workflow

- Delegate implementation to general agents with explicit file ownership, then review the combined changes for major issues and complete a Linux release build. Fix build failures and report which platforms were actually built.
- Do not add, modify, or run tests. Leave manual behavior checks to the user; provide checks for affected UI, queue behavior, output media, and failure handling. Skip builds for docs-only changes.
- On any sandbox permission problem, stop immediately and ask the user to whitelist the affected directory via `nano ~/.config/firejail/strict-dev.profile`; never edit that file yourself.
