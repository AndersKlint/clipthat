set -euo pipefail

target=$1
work=$2
jobs=$3
if [[ "$target" == windows-x64 ]]; then
    work=$(cygpath -u "$work")
fi
cd "$work"
work=$PWD
prefix="$work/prefix"
export PATH="$prefix/bin:$PATH"
export CC=gcc CXX=g++ AR=ar RANLIB=ranlib NM=nm STRIP=strip
export CFLAGS='-O2 -march=x86-64 -mtune=generic'
export CXXFLAGS="$CFLAGS"
export CPPFLAGS='' LDFLAGS=''
export PKG_CONFIG=pkg-config PKGCONFIG=pkg-config
export PKG_CONFIG_PATH=''
export PKG_CONFIG_LIBDIR="$prefix/lib/pkgconfig"
unset PKG_CONFIG_SYSROOT_DIR CONFIG_SITE MAKEFLAGS MFLAGS CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH LIBRARY_PATH
export LC_ALL=C TZ=UTC SOURCE_DATE_EPOCH=1792800000
unset BASH_ENV ENV CDPATH
mkdir -p "$prefix/bin" toolchain

run() {
    printf '%s\0' "$PWD" "$@" >> "$work/commands.bin"
    printf '\0' >> "$work/commands.bin"
    "$@"
}

capture() {
    local name=$1
    shift
    run "$@" > "$work/toolchain/$name.txt"
}

capture gcc gcc --version
capture gcc-target gcc -dumpmachine
capture g++ g++ --version
capture ld ld --version
capture ar ar --version
capture make make --version
capture meson meson --version
capture ninja ninja --version
capture pkg-config pkg-config --version
capture bash bash --version
capture kernel uname -a
capture compiler-path bash -c 'command -v gcc; command -v g++; command -v ld; command -v meson; command -v pkg-config'

exe=''
platform_flags=()
if [[ "$target" == windows-x64 ]]; then
    [[ "${MSYSTEM:-}" == UCRT64 ]] || { printf '%s\n' 'Run in an MSYS2 UCRT64 environment.' >&2; exit 1; }
    [[ "$(gcc -dumpmachine)" == x86_64-w64-mingw32 ]] || { printf '%s\n' 'UCRT64 x86_64 GCC is required.' >&2; exit 1; }
    exe=.exe
    export LDFLAGS='-static -static-libgcc -static-libstdc++'
    platform_flags=(--target-os=mingw32 --enable-w32threads --disable-pthreads)
    capture msys-packages pacman -Q
    capture libgcc-path gcc -print-file-name=libgcc.a
    capture libstdc++-path g++ -print-file-name=libstdc++.a
    for package in gcc crt headers; do
        run cp -R "${MINGW_PREFIX:?}/share/licenses/$package" "$work/notices/mingw-$package"
    done
    if [[ -d "$MINGW_PREFIX/share/licenses/winpthreads" ]]; then
        run cp -R "$MINGW_PREFIX/share/licenses/winpthreads" "$work/notices/mingw-winpthreads"
    fi
    capture runtime-archives bash -c 'for name in libgcc.a libgcc_eh.a libstdc++.a libmingw32.a libmingwex.a libwinpthread.a; do file=$(gcc -print-file-name="$name"); if [[ -f "$file" ]]; then sha256sum "$file"; fi; done'
else
    [[ "$(gcc -dumpmachine)" == x86_64*linux* ]] || { printf '%s\n' 'Native Linux x86_64 GCC is required.' >&2; exit 1; }
fi

cd "$work/src/nasm"
run bash ./configure --prefix="$prefix"
run make -j"$jobs" "nasm$exe"
run cp "nasm$exe" "$prefix/bin/nasm$exe"
capture nasm nasm -v

cd "$work/src/x264"
run bash ./configure --prefix="$prefix" --libdir="$prefix/lib" \
    --enable-static --disable-cli --disable-opencl --disable-bashcompletion \
    --enable-pic --bit-depth=8 --chroma-format=420
run make -j"$jobs"
run make install

cd "$work/src/dav1d"
run meson setup build --prefix="$prefix" --libdir=lib --buildtype=release \
    --default-library=static --wrap-mode=nodownload -Db_lto=false \
    -Denable_tools=false -Denable_examples=false -Denable_tests=false \
    -Denable_docs=false -Dtestdata_tests=false -Dxxhash_muxer=disabled
run meson compile -C build -j"$jobs"
run meson install -C build

cd "$work/src/ffmpeg"
run bash ./configure --prefix="$prefix" --libdir="$prefix/lib" \
    --cc=gcc --cxx=g++ --ar=ar --ranlib=ranlib --nm=nm --strip=strip \
    --arch=x86_64 --cpu=x86-64 --extra-cflags="$CFLAGS" --extra-ldflags="$LDFLAGS" \
    --pkg-config=pkg-config --pkg-config-flags=--static \
    --disable-autodetect --disable-everything --disable-network \
    --disable-shared --enable-static --disable-avdevice --disable-ffplay \
    --disable-doc --disable-debug --disable-sdl2 --enable-ffmpeg --enable-ffprobe \
    --enable-gpl --enable-version3 --enable-libx264 --enable-libdav1d \
    --enable-swscale --enable-swresample \
    --enable-decoder=libdav1d,vp9,h264,aac,opus,vorbis,webvtt \
    --enable-encoder=libx264,aac,webvtt \
    --enable-demuxer=mov,matroska,webvtt,aac,ogg,mpegts \
    --enable-muxer=matroska --enable-parser=av1,vp9,h264,aac,opus,vorbis \
    --enable-protocol=file,pipe --enable-filter=scale,aresample "${platform_flags[@]}"
run make -j"$jobs"
run make install

for name in ffmpeg ffprobe; do
    capture "$name-version" "$prefix/bin/$name$exe" -version
    if [[ "$target" == windows-x64 ]]; then
        capture "$name-linkage" objdump -p "$prefix/bin/$name$exe"
    else
        capture "$name-linkage" readelf -d "$prefix/bin/$name"
    fi
done
capture encoders "$prefix/bin/ffmpeg$exe" -hide_banner -encoders
capture decoders "$prefix/bin/ffmpeg$exe" -hide_banner -decoders
capture protocols "$prefix/bin/ffmpeg$exe" -hide_banner -protocols
capture buildconf "$prefix/bin/ffmpeg$exe" -hide_banner -buildconf

run mkdir -p "$work/sources/configuration/ffmpeg" "$work/sources/configuration/x264" "$work/sources/configuration/dav1d"
for name in config.h config_components.h ffbuild/config.mak ffbuild/config.log; do
    run cp "$work/src/ffmpeg/$name" "$work/sources/configuration/ffmpeg/$(basename "$name")"
done
for name in config.h config.mak config.log x264_config.h; do
    run cp "$work/src/x264/$name" "$work/sources/configuration/x264/$name"
done
run cp "$work/src/dav1d/build/meson-info/intro-buildoptions.json" "$work/sources/configuration/dav1d/buildoptions.json"
run cp "$work/src/dav1d/build/meson-logs/meson-log.txt" "$work/sources/configuration/dav1d/meson-log.txt"
