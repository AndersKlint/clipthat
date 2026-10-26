import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';

import '../models/subtitle_track.dart';

class SubtitlePicker extends StatefulWidget {
  const SubtitlePicker({
    super.key,
    required this.tracks,
    required this.selected,
    required this.loading,
    required this.loaded,
    required this.error,
    required this.onLoad,
    required this.onRetry,
    required this.onChanged,
  });

  final List<SubtitleTrack> tracks;
  final List<SubtitleTrack> selected;
  final bool loading;
  final bool loaded;
  final String? error;
  final VoidCallback onLoad;
  final VoidCallback onRetry;
  final ValueChanged<List<SubtitleTrack>> onChanged;

  @override
  State<SubtitlePicker> createState() => _SubtitlePickerState();
}

class _SubtitlePickerState extends State<SubtitlePicker> {
  final _search = TextEditingController();
  final _focus = FocusNode();
  final _scroll = ScrollController();
  final _overlay = OverlayPortalController();
  bool _open = false;
  SubtitleTrack? _highlighted;

  List<SubtitleTrack> get _matches {
    final query = _search.text.trim().toLowerCase();
    return widget.tracks
        .where((track) =>
            !widget.selected.contains(track) &&
            (track.label.toLowerCase().contains(query) ||
                track.languageCode.toLowerCase().contains(query)))
        .toList();
  }

  @override
  void initState() {
    super.initState();
    _focus.addListener(_focusChanged);
  }

  void _focusChanged() {
    if (SchedulerBinding.instance.schedulerPhase ==
        SchedulerPhase.persistentCallbacks) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _focusChanged();
      });
      return;
    }
    _setOpen(_focus.hasFocus);
    if (_focus.hasFocus) widget.onLoad();
  }

  void _setOpen(bool open) {
    setState(() => _open = open);
    _syncOverlay();
  }

  void _syncOverlay() {
    if (SchedulerBinding.instance.schedulerPhase ==
        SchedulerPhase.persistentCallbacks) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _syncOverlay();
      });
      return;
    }
    final shouldShow =
        _open && _focus.hasFocus && widget.loaded && widget.tracks.isNotEmpty;
    if (shouldShow == _overlay.isShowing) return;
    if (shouldShow) {
      _overlay.show();
    } else {
      _overlay.hide();
    }
  }

  @override
  void didUpdateWidget(covariant SubtitlePicker oldWidget) {
    super.didUpdateWidget(oldWidget);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _syncOverlay();
    });
  }

  int _highlightIndex(List<SubtitleTrack> matches) {
    final highlighted = _highlighted;
    final index = highlighted == null ? -1 : matches.indexOf(highlighted);
    return index < 0 ? 0 : index;
  }

  void _highlight(SubtitleTrack track, {bool scroll = false}) {
    setState(() => _highlighted = track);
    if (!scroll) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_scroll.hasClients) return;
      final index = _matches.indexOf(track);
      if (index < 0) return;
      final position = _scroll.position;
      final top = index * 64.0;
      final bottom = top + 64;
      final offset = top < position.pixels
          ? top
          : bottom > position.pixels + position.viewportDimension
              ? bottom - position.viewportDimension
              : position.pixels;
      _scroll.jumpTo(offset.clamp(0.0, position.maxScrollExtent));
    });
  }

  void _add(SubtitleTrack track) {
    widget.onChanged([...widget.selected, track]);
    _search.clear();
    setState(() {
      _highlighted = null;
      _open = true;
    });
    _focus.requestFocus();
    _syncOverlay();
  }

  KeyEventResult _key(FocusNode node, KeyEvent event) {
    if (event is! KeyDownEvent && event is! KeyRepeatEvent) {
      return KeyEventResult.ignored;
    }
    if (event.logicalKey == LogicalKeyboardKey.escape) {
      _setOpen(false);
      return KeyEventResult.handled;
    }
    final matches = _matches;
    if (event.logicalKey == LogicalKeyboardKey.arrowDown ||
        event.logicalKey == LogicalKeyboardKey.arrowUp) {
      final direction =
          event.logicalKey == LogicalKeyboardKey.arrowDown ? 1 : -1;
      final next = _open ? _highlightIndex(matches) + direction : 0;
      _setOpen(true);
      if (matches.isNotEmpty) {
        _highlight(matches[next.clamp(0, matches.length - 1)], scroll: true);
      }
      return KeyEventResult.handled;
    }
    if (_open && event.logicalKey == LogicalKeyboardKey.enter) {
      if (matches.isNotEmpty) {
        _add(matches[_highlightIndex(matches)]);
      }
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  @override
  void dispose() {
    _focus.removeListener(_focusChanged);
    _search.dispose();
    _focus.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return TextFieldTapRegion(
      onTapOutside: (_) {
        _setOpen(false);
        _focus.unfocus();
      },
      child: Focus(
        onFocusChange: (hasFocus) {
          if (!hasFocus && _open) _setOpen(false);
        },
        child: Material(
          color: theme.colorScheme.surface,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (widget.selected.isNotEmpty)
                Wrap(spacing: 6, runSpacing: 4, children: [
                  for (final track in widget.selected)
                    InputChip(
                      label: Text(track.label),
                      onDeleted: () => widget.onChanged(
                        widget.selected.where((item) => item != track).toList(),
                      ),
                      deleteButtonTooltipMessage: 'Remove ${track.label}',
                    ),
                ]),
              if (widget.selected.isNotEmpty) const SizedBox(height: 8),
              OverlayPortal.overlayChildLayoutBuilder(
                controller: _overlay,
                overlayChildBuilder: _buildPopup,
                child: Focus(
                  onKeyEvent: _key,
                  child: TextField(
                    controller: _search,
                    focusNode: _focus,
                    onTap: () {
                      _setOpen(true);
                      widget.onLoad();
                    },
                    onChanged: (_) {
                      _highlighted = null;
                      _setOpen(true);
                      if (_scroll.hasClients) _scroll.jumpTo(0);
                    },
                    decoration: const InputDecoration(
                      labelText: 'Subtitle languages',
                      hintText: 'Search by language or code',
                    ),
                  ),
                ),
              ),
              if (widget.loading) const LinearProgressIndicator(),
              const SizedBox(height: 8),
              if (widget.error != null) ...[
                Text(widget.error!,
                    style: TextStyle(color: theme.colorScheme.error)),
                TextButton(
                    onPressed: widget.onRetry,
                    child: const Text('Retry languages')),
              ] else if (widget.loaded && widget.tracks.isEmpty)
                const Text(
                    'No subtitles available. You can still create this clip.')
              else if (!widget.loaded && !widget.loading)
                const Text(
                    'Enter a valid YouTube URL, then focus here to load languages.'),
              if (widget.selected.length > 5)
                const Text(
                    'YouTube may rate-limit many languages. Subtitle requests are paced 5 seconds apart.'),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPopup(BuildContext context, OverlayChildLayoutInfo layout) {
    final transform = layout.childPaintTransform;
    if (transform.determinant() == 0) return const SizedBox.shrink();
    final field = MatrixUtils.transformRect(
      transform,
      Offset.zero & layout.childSize,
    );
    final media = MediaQuery.of(context);
    final bounds = media.padding.deflateRect(
      media.viewInsets.deflateRect(Offset.zero & layout.overlaySize),
    );
    if (!bounds.overlaps(field)) return const SizedBox.shrink();
    final below = (bounds.bottom - field.bottom).clamp(0.0, bounds.height);
    final above = (field.top - bounds.top).clamp(0.0, bounds.height);
    final opensUp = below < 180 && above > below;
    final height = (opensUp ? above : below).clamp(0.0, 280.0);
    final width = field.width.clamp(0.0, bounds.width);
    final left = field.left.clamp(bounds.left, bounds.right - width);
    final matches = _matches;
    final theme = Theme.of(context);
    return Positioned(
      left: left,
      top: opensUp ? null : field.bottom,
      bottom: opensUp ? layout.overlaySize.height - field.top : null,
      width: width,
      child: TextFieldTapRegion(
        child: ExcludeFocus(
          child: Material(
            elevation: 6,
            color: theme.colorScheme.surface,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
              side: BorderSide(color: theme.colorScheme.outlineVariant),
            ),
            clipBehavior: Clip.antiAlias,
            child: ConstrainedBox(
              constraints: BoxConstraints(maxHeight: height),
              child: matches.isEmpty
                  ? const SingleChildScrollView(
                      child: Padding(
                        padding: EdgeInsets.all(12),
                        child: Text('No matching unselected languages.'),
                      ),
                    )
                  : ListView.builder(
                      controller: _scroll,
                      padding: EdgeInsets.zero,
                      shrinkWrap: true,
                      itemExtent: 64,
                      itemCount: matches.length,
                      itemBuilder: (context, index) {
                        final track = matches[index];
                        return MouseRegion(
                          onEnter: (_) => _highlight(track),
                          child: ListTile(
                            key: ValueKey(track),
                            title: Text(track.label),
                            textColor: theme.colorScheme.onSurface,
                            selectedColor: theme.colorScheme.onSurface,
                            selectedTileColor:
                                theme.colorScheme.surfaceContainerHighest,
                            selected: index == _highlightIndex(matches),
                            onTap: () => _add(track),
                          ),
                        );
                      },
                    ),
            ),
          ),
        ),
      ),
    );
  }
}
