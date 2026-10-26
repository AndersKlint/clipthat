#!/bin/sh
set -eu

tools=/app/clipthat/tools
for directory in lib data tools licenses/tools; do
    test -d "/app/clipthat/$directory"
done
for notice in ClipThat-LICENSE.txt THIRD_PARTY_NOTICES.md tools/yt-dlp/upstream.json tools/ffmpeg/upstream.json tools/deno/upstream.json; do
    test -s "/app/clipthat/licenses/$notice"
done
test -s "$tools/manifest.json"
"$tools/yt-dlp" --ignore-config --no-update --version
"$tools/deno" --version
"$tools/ffprobe" -version
configuration=$("$tools/ffmpeg" -version 2>&1)
printf '%s\n' "$configuration"
case "$configuration" in *--enable-nonfree*) printf '%s\n' 'FFmpeg must not enable nonfree components.' >&2; exit 1;; esac
case "$configuration" in *--enable-gpl*) ;; *) printf '%s\n' 'FFmpeg must enable GPL components.' >&2; exit 1;; esac
case "$configuration" in *--enable-libx264*) ;; *) printf '%s\n' 'FFmpeg must enable libx264.' >&2; exit 1;; esac
encoders=$("$tools/ffmpeg" -hide_banner -encoders 2>&1)
printf '%s\n' "$encoders"
for encoder in libx264 aac; do
    printf '%s\n' "$encoders" | grep -Eq "^[[:space:]]*[VA][^[:space:]]*[[:space:]]+$encoder[[:space:]]" || {
        printf 'Missing FFmpeg encoder: %s\n' "$encoder" >&2
        exit 1
    }
done
