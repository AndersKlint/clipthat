.DEFAULT_GOAL := help

ifeq ($(OS),Windows_NT)
PYTHON ?= python
HOST_PLATFORM := windows
HOST_PACKAGE := windows-zip
else
PYTHON ?= python3
HOST_PLATFORM := linux
HOST_PACKAGE := flatpak
endif

FLUTTER ?= flutter
FLUTTER_SDK ?= $(shell "$(PYTHON)" scripts/dev_run.py --flutter "$(FLUTTER)" --print-flutter-sdk)
SOURCES_DIR ?= release-sources/$(HOST_PLATFORM)-x64
ifeq ($(OS),Windows_NT)
OUTPUT_DIR ?= dist/windows-x64
else
OUTPUT_DIR ?= build/flatpak
endif

.PHONY: help run build installer installers flatpak flatpak-dev windows-zip flatpak-setup

help:
	@"$(PYTHON)" -c "print('ClipThat! developer commands\n\n  make run            Build and launch native Linux/Windows x64 with cached development tools\n  make build          Native host release build (Flutter only)\n  make installer      Host package: Linux Flatpak or Windows portable ZIP\n  make installers     Alias for installer\n  make flatpak        Linux release Flatpak; matching sources required\n  make flatpak-dev    Non-redistributable development Flatpak\n  make windows-zip    Windows portable ZIP, source ZIP and SHA256SUMS (Windows only)\n  make flatpak-setup  Explicitly install user GNOME Platform + SDK 50 from Flathub\n\nVariables: PYTHON, FLUTTER, FLUTTER_SDK, SOURCES_DIR, OUTPUT_DIR\nDefaults: Python python3 on Linux / python on Windows; Flutter on PATH;\nFlutter SDK detected from resolved executable; sources release-sources/<host>-x64;\noutput build/flatpak on Linux / dist/windows-x64 on Windows.')"

run:
	"$(PYTHON)" scripts/dev_run.py --flutter "$(FLUTTER)"

build:
	"$(FLUTTER)" build $(HOST_PLATFORM) --release --target-platform $(HOST_PLATFORM)-x64

installer installers: $(HOST_PACKAGE)

flatpak:
	"$(PYTHON)" scripts/package_flatpak.py --flutter-sdk "$(FLUTTER_SDK)" --sources-dir "$(SOURCES_DIR)" --output-dir "$(OUTPUT_DIR)"

flatpak-dev:
	"$(PYTHON)" scripts/package_flatpak.py --flutter-sdk "$(FLUTTER_SDK)" --development --output-dir "$(OUTPUT_DIR)"

windows-zip:
	"$(PYTHON)" scripts/package_windows.py --sources-dir "$(SOURCES_DIR)" --output-dir "$(OUTPUT_DIR)"

flatpak-setup:
	flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
	flatpak install --user flathub org.gnome.Platform//50 org.gnome.Sdk//50
