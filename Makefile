.DEFAULT_GOAL := help

ifeq ($(OS),Windows_NT)
PYTHON ?= python
HOST_PLATFORM := windows
HOST_PACKAGE := windows-zip
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
FLUTTER_SDK ?= $(shell "$(PYTHON)" scripts/dev_run.py --flutter "$(FLUTTER)" --print-flutter-sdk)
ifeq ($(OS),Windows_NT)
OUTPUT_DIR ?= dist/windows-x64
else
OUTPUT_DIR ?= build/flatpak
endif

.PHONY: help run build installer installers flatpak flatpak-installer windows-installer windows-zip flatpak-setup

help:
	@"$(PYTHON)" -c "print('ClipThat! developer commands\n\n  make run                Build and launch with bundled upstream tools\n  make build              Native host Flutter release build\n  make installer          Native installer with upstream tools and checksums\n  make installers         Alias for installer\n  make flatpak-installer  Linux Flatpak built inside GNOME SDK 50\n  make flatpak            Alias for flatpak-installer\n  make windows-installer  Windows portable ZIP\n  make windows-zip        Alias for windows-installer\n  make flatpak-setup      Install current GNOME Platform + SDK 50 from Flathub\n\nVariables: PYTHON, FLUTTER, FLUTTER_SDK, OUTPUT_DIR\nDefaults: Python python3 on Linux / python on Windows; Flutter on PATH;\nFlutter SDK detected from resolved executable;\noutput build/flatpak on Linux / dist/windows-x64 on Windows.')"

run:
	"$(PYTHON)" scripts/dev_run.py --flutter "$(FLUTTER)"

build:
	"$(FLUTTER)" build $(HOST_PLATFORM) --release $(HOST_TARGET_FLAGS)

installer installers: $(HOST_PACKAGE)

flatpak flatpak-installer:
	"$(PYTHON)" scripts/package_flatpak.py --flutter-sdk "$(FLUTTER_SDK)" --output-dir "$(OUTPUT_DIR)"

windows-zip windows-installer:
	"$(PYTHON)" scripts/package_windows.py --output-dir "$(OUTPUT_DIR)"

flatpak-setup:
	flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
	flatpak install --user --noninteractive -y --arch=x86_64 flathub org.gnome.Platform//50 org.gnome.Sdk//50
