.DEFAULT_GOAL := help

ifeq ($(OS),Windows_NT)
PYTHON ?= python
HOST_PLATFORM := windows
HOST_PACKAGE := windows-installer
else
PYTHON ?= python3
HOST_PLATFORM := linux
HOST_TARGET_FLAGS := --target-platform linux-x64
HOST_PACKAGE := flatpak
endif

ifeq ($(OS),Windows_NT)
FLUTTER ?= flutter.bat
else
FLUTTER ?= flutter
endif
ifeq ($(OS),Windows_NT)
OUTPUT_DIR ?= dist/windows-x64
else
OUTPUT_DIR ?= build/flatpak
endif

.PHONY: help run build installer installers flatpak flatpak-installer windows-installer windows-zip flatpak-setup

help:
	@"$(PYTHON)" -c "print('ClipThat! developer commands\n\n  make run                Build and launch with bundled upstream tools\n  make build              Native host Flutter release build\n  make installer          Native package(s) with upstream tools and checksums\n  make installers         Alias for installer\n  make flatpak-installer  Linux Flatpak built inside GNOME SDK 50\n  make flatpak            Alias for flatpak-installer\n  make windows-installer  Windows portable ZIP + Inno Setup EXE (requires Inno Setup 6.3+)\n  make windows-zip        Alias for windows-installer; produces both assets\n  make flatpak-setup      Install current GNOME Platform + SDK 50 from Flathub\n\nVariables: PYTHON, FLUTTER, OUTPUT_DIR\nDefaults: Python python3 on Linux / python on Windows; Flutter on PATH for native builds;\nFlatpak fetches stable Flutter; output build/flatpak on Linux / dist/windows-x64 on Windows.')"

run:
	"$(PYTHON)" scripts/dev_run.py --flutter "$(FLUTTER)"

build:
	"$(FLUTTER)" build $(HOST_PLATFORM) --release $(HOST_TARGET_FLAGS)

installer installers: $(HOST_PACKAGE)

flatpak flatpak-installer:
	@set -eu; \
	test "$$(uname -sm)" = 'Linux x86_64' || { printf '%s\n' 'Flatpak packaging requires Linux x86_64.' >&2; exit 1; }; \
	mkdir -p -- "$(OUTPUT_DIR)"; \
	output=$$(realpath -- "$(OUTPUT_DIR)"); \
	case "$$output/" in "$(CURDIR)/build/"*) ;; "$(CURDIR)/"*) printf '%s\n' 'OUTPUT_DIR must be inside build/ or outside the source tree.' >&2; exit 1;; esac; \
	for name in ClipThat-linux-x64.flatpak SHA256SUMS-linux-x64; do \
		if test -e "$$output/$$name" || test -L "$$output/$$name"; then printf 'Output already exists: %s\n' "$$output/$$name" >&2; exit 1; fi; \
	done; \
	work=$$(mktemp -d "$$output/.clipthat-flatpak-XXXXXXXX"); \
	published=0; complete=0; \
	trap 'if test "$$published" = 1 && test "$$complete" = 0; then rm -f -- "$$output/ClipThat-linux-x64.flatpak"; fi; rm -rf -- "$$work"' EXIT; \
	trap 'exit 130' INT; trap 'exit 143' TERM; \
	cp packaging/linux/com.drjetski.clipthat.json "$$work/"; \
	ln -s -- "$(CURDIR)" "$$work/source"; \
	mkdir "$$work/prepared"; \
	"$(PYTHON)" scripts/bundle_tools.py --platform linux-x64 --destination "$$work/prepared"; \
	flatpak-builder --arch=x86_64 --disable-rofiles-fuse \
		--state-dir="$$work/builder-state" --repo="$$output/repo" \
		"$$work/app" "$$work/com.drjetski.clipthat.json"; \
	timeout 120 flatpak build --runtime --unshare=network --env=HOME=/tmp \
		--env=TMPDIR=/tmp --env=TEMP=/tmp --env=TMP=/tmp "$$work/app" \
		sh -s < packaging/linux/check-runtime-tools.sh; \
	flatpak build-bundle --arch=x86_64 --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo \
		"$$output/repo" "$$work/ClipThat-linux-x64.flatpak" com.drjetski.clipthat stable; \
	test "$$(stat -c %s "$$work/ClipThat-linux-x64.flatpak")" -lt 2147483648; \
	(cd "$$work" && sha256sum ClipThat-linux-x64.flatpak > SHA256SUMS-linux-x64); \
	ln -- "$$work/ClipThat-linux-x64.flatpak" "$$output/ClipThat-linux-x64.flatpak"; published=1; \
	ln -- "$$work/SHA256SUMS-linux-x64" "$$output/SHA256SUMS-linux-x64"; complete=1; \
	printf 'Flatpak bundle: %s/ClipThat-linux-x64.flatpak\n' "$$output"

windows-zip windows-installer:
	"$(PYTHON)" scripts/package_windows.py --output-dir "$(OUTPUT_DIR)"

flatpak-setup:
	flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
	flatpak install --user --noninteractive -y --arch=x86_64 flathub org.gnome.Platform//50 org.gnome.Sdk//50 org.freedesktop.Sdk.Extension.llvm21//25.08
