import 'dart:async';

import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';

import '../app_brand.dart';
import '../controllers/clip_controller.dart';
import '../models/clip_job.dart';
import '../models/clip_request.dart';
import '../widgets/clip_queue.dart';
import '../widgets/tool_status_banner.dart';
import '../widgets/workspace_panel.dart';

class ClipWorkspace extends StatefulWidget {
  const ClipWorkspace(
      {super.key, required this.themeMode, required this.onThemeChanged});

  final ThemeMode themeMode;
  final ValueChanged<ThemeMode> onThemeChanged;

  @override
  State<ClipWorkspace> createState() => _ClipWorkspaceState();
}

class _ClipWorkspaceState extends State<ClipWorkspace> {
  final _controller = ClipController();
  final _url = TextEditingController();
  final _start = TextEditingController();
  final _end = TextEditingController();
  final _output = TextEditingController();
  final Map<TextEditingController, String> _lastInput = {};
  bool _includeSubtitles = true;
  bool _includeAutomaticTranslations = false;
  bool _pickingDirectory = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _output.text = _controller.outputDirectory;
    unawaited(_restoreOutputDirectory());
    unawaited(_controller.checkTools());
  }

  Future<void> _restoreOutputDirectory() async {
    await _controller.restoreOutputDirectory();
    if (!mounted) return;
    if (_output.text != _controller.outputDirectory) {
      setState(() => _output.text = _controller.outputDirectory);
    }
  }

  void _outputChanged(String value) {
    _controller.editOutputDirectory(value);
    _inputChanged(value);
  }

  void _inputChanged(String value) {
    setState(() => _error = null);
  }

  void _linkInputChanged(TextEditingController input, String value) {
    final previous = _lastInput[input] ?? '';
    _lastInput[input] = value;
    var prefix = 0;
    while (prefix < previous.length &&
        prefix < value.length &&
        previous.codeUnitAt(prefix) == value.codeUnitAt(prefix)) {
      prefix++;
    }
    var suffix = 0;
    while (suffix < previous.length - prefix &&
        suffix < value.length - prefix &&
        previous.codeUnitAt(previous.length - suffix - 1) ==
            value.codeUnitAt(value.length - suffix - 1)) {
      suffix++;
    }
    if (value.length - prefix - suffix > 1) {
      try {
        final link = YouTubeLink.parse(value);
        final timestamp = link.timestampSeconds;
        if (timestamp != null) {
          _replaceInput(_url, link.url);
          _replaceInput(
              input == _url ? _start : input, formatTimestamp(timestamp));
        }
      } on FormatException {
        // Keep invalid input intact so submission can report the validation error.
      }
    }
    _inputChanged(value);
  }

  void _replaceInput(TextEditingController input, String value) {
    _lastInput[input] = value;
    input.value = TextEditingValue(
      text: value,
      selection: TextSelection.collapsed(offset: value.length),
    );
  }

  ClipRequest _parse() => ClipRequest.parse(
        url: _url.text,
        start: _start.text,
        end: _end.text,
        outputDirectory: _output.text,
        includeSubtitles: _includeSubtitles,
        includeAutomaticTranslations:
            _includeSubtitles && _includeAutomaticTranslations,
      );

  ClipRequest? get _preview {
    try {
      return _parse();
    } on FormatException {
      return null;
    }
  }

  void _createClip() {
    try {
      final request = _parse();
      _controller.add(request);
      setState(() => _error = null);
    } on FormatException catch (error) {
      setState(() => _error = error.message);
    } on StateError catch (error) {
      setState(() => _error = error.message);
    }
  }

  void _retry(ClipJob job) {
    try {
      _controller.retry(job);
    } on StateError catch (error) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(error.message)));
    }
  }

  Future<void> _chooseDirectory() async {
    setState(() => _pickingDirectory = true);
    try {
      final directory =
          await getDirectoryPath(confirmButtonText: 'Save clips here');
      if (!mounted) return;
      if (directory != null) {
        setState(() {
          _output.text = directory;
          _controller.editOutputDirectory(directory);
          _error = null;
        });
      }
    } catch (error) {
      if (!mounted) return;
      setState(() => _error =
          'Could not open the folder chooser. Make sure your desktop file chooser is available, then try again. $error');
    } finally {
      if (mounted) setState(() => _pickingDirectory = false);
    }
  }

  @override
  void dispose() {
    for (final input in [_url, _start, _end, _output]) {
      input.dispose();
    }
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: AnimatedBuilder(
          animation: _controller,
          builder: (context, _) => LayoutBuilder(
            builder: (context, constraints) {
              final compact = constraints.maxWidth < 650;
              return SingleChildScrollView(
                padding: EdgeInsets.symmetric(
                    horizontal: compact ? 16 : 32, vertical: compact ? 16 : 24),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 1240),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _BrandHeader(
                            themeMode: widget.themeMode,
                            onThemeChanged: widget.onThemeChanged),
                        const SizedBox(height: 16),
                        LayoutBuilder(
                          builder: (context, workspace) {
                            final form = _buildForm(context);
                            final queue = ClipQueue(
                                controller: _controller,
                                onRetry: _retry,
                                compact: compact);
                            if (workspace.maxWidth < 940) {
                              return Column(children: [
                                form,
                                const SizedBox(height: 24),
                                queue
                              ]);
                            }
                            return Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Expanded(flex: 11, child: form),
                                const SizedBox(width: 24),
                                Expanded(flex: 10, child: queue),
                              ],
                            );
                          },
                        ),
                        const SizedBox(height: 20),
                        Text(
                          'Tip: Right-click a YouTube video and choose “Copy video URL at current time”. Paste it into YouTube URL, Start, or End.',
                          style: Theme.of(context)
                              .textTheme
                              .bodySmall
                              ?.copyWith(
                                  color: Theme.of(context)
                                      .colorScheme
                                      .onSurfaceVariant),
                        ),
                        const SizedBox(height: 12),
                        ToolStatusBanner(controller: _controller),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _buildForm(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final preview = _preview;
    return WorkspacePanel(
      padding: 20,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('New clip', style: theme.textTheme.titleLarge),
          const SizedBox(height: 20),
          Tooltip(
            message: 'Paste a timestamped YouTube URL to fill Start.',
            child: TextField(
              controller: _url,
              onChanged: (value) => _linkInputChanged(_url, value),
              keyboardType: TextInputType.url,
              textInputAction: TextInputAction.next,
              autocorrect: false,
              decoration: const InputDecoration(
                labelText: 'YouTube URL',
                hintText: 'https://www.youtube.com/watch?v=…',
              ),
            ),
          ),
          const SizedBox(height: 20),
          LayoutBuilder(
            builder: (context, constraints) {
              final start = Tooltip(
                message:
                    'Seconds, mm:ss, hh:mm:ss, or 1h2m3s. Paste a timestamped URL to fill YouTube URL and Start. Blank defaults to the source time or 00:00.',
                child: TextField(
                  controller: _start,
                  onChanged: (value) => _linkInputChanged(_start, value),
                  textInputAction: TextInputAction.next,
                  autocorrect: false,
                  decoration: const InputDecoration(
                      labelText: 'Start', hintText: '00:00'),
                ),
              );
              final end = Tooltip(
                message:
                    'Required, later than Start. Seconds, mm:ss, hh:mm:ss, or 1h2m3s. Paste a timestamped URL to fill YouTube URL and End.',
                child: TextField(
                  controller: _end,
                  onChanged: (value) => _linkInputChanged(_end, value),
                  textInputAction: TextInputAction.next,
                  autocorrect: false,
                  decoration: const InputDecoration(
                      labelText: 'End', hintText: '01:30'),
                ),
              );
              if (constraints.maxWidth < 350) {
                return Column(
                    children: [start, const SizedBox(height: 16), end]);
              }
              return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: start),
                    const SizedBox(width: 16),
                    Expanded(child: end)
                  ]);
            },
          ),
          if (preview != null) ...[
            const SizedBox(height: 8),
            Text(
              'Duration ${formatTimestamp(preview.durationSeconds)}',
              style: theme.textTheme.bodySmall!
                  .copyWith(color: colors.onSurfaceVariant),
            ),
          ],
          const SizedBox(height: 20),
          TextField(
            controller: _output,
            onChanged: _outputChanged,
            autocorrect: false,
            textInputAction: TextInputAction.done,
            onSubmitted: (_) {
              if (_controller.toolsReady && !_controller.checkingTools) {
                _createClip();
              }
            },
            decoration: InputDecoration(
              hintText: 'Choose an output folder',
              labelText: 'Output folder',
              suffixIcon: IconButton(
                tooltip: 'Choose output folder',
                onPressed: _pickingDirectory ? null : _chooseDirectory,
                icon: _pickingDirectory
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.folder_open_rounded, size: 21),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Material(
            color: colors.surface,
            child: Column(children: [
              Tooltip(
                message:
                    'Download and embed all available manual subtitle tracks in the MKV. Enable Include automatic translations to also request generated captions and automatic translations. Missing tracks warn without failing the clip. Settings are saved per queued clip.',
                child: SwitchListTile(
                  title: const Text('Download subs'),
                  value: _includeSubtitles,
                  onChanged: (value) => setState(() {
                    _includeSubtitles = value;
                    if (!value) _includeAutomaticTranslations = false;
                  }),
                  contentPadding: EdgeInsets.zero,
                ),
              ),
              Tooltip(
                message:
                    'Also download generated captions and automatic translations in all available languages. This can take much longer. Requires Download subs; turning subtitles off clears this selection.',
                child: SwitchListTile(
                  title: const Text('Include automatic translations'),
                  value: _includeAutomaticTranslations,
                  onChanged: _includeSubtitles
                      ? (value) =>
                          setState(() => _includeAutomaticTranslations = value)
                      : null,
                  contentPadding: EdgeInsets.zero,
                  dense: true,
                ),
              ),
            ]),
          ),
          if (_controller.outputPreferenceError case final message?) ...[
            const SizedBox(height: 12),
            Semantics(
              liveRegion: true,
              child: Text(message,
                  style:
                      theme.textTheme.bodySmall?.copyWith(color: colors.error)),
            ),
            TextButton(
              onPressed: _controller.commitOutputDirectory,
              child: const Text('Retry saving folder'),
            ),
          ],
          if (_error != null) ...[
            const SizedBox(height: 20),
            Semantics(
              liveRegion: true,
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                    color: colors.errorContainer,
                    borderRadius: BorderRadius.circular(12)),
                child: Text(_error!,
                    style: theme.textTheme.bodyMedium!
                        .copyWith(color: colors.onErrorContainer)),
              ),
            ),
          ],
          const SizedBox(height: 16),
          Tooltip(
            message:
                'Downloads the full video first, then encodes the selected range. Queued clips run one at a time.',
            child: SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: _controller.toolsReady && !_controller.checkingTools
                    ? _createClip
                    : null,
                child: Text(
                    _controller.isProcessing ? 'Add to queue' : 'Create clip'),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

enum _HeaderAction {
  system(ThemeMode.system),
  light(ThemeMode.light),
  dark(ThemeMode.dark),
  about(null);

  const _HeaderAction(this.themeMode);

  final ThemeMode? themeMode;
}

class _BrandHeader extends StatelessWidget {
  const _BrandHeader({required this.themeMode, required this.onThemeChanged});

  final ThemeMode themeMode;
  final ValueChanged<ThemeMode> onThemeChanged;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      children: [
        Expanded(
          child: Text.rich(
            TextSpan(
              children: [
                TextSpan(
                  text: 'Clip',
                  style: TextStyle(color: theme.colorScheme.primary),
                ),
                TextSpan(
                  text: 'That',
                  style: TextStyle(
                    color: theme.brightness == Brightness.dark
                        ? Colors.white
                        : theme.colorScheme.onSurface,
                  ),
                ),
                TextSpan(
                  text: '!',
                  style: TextStyle(color: theme.colorScheme.primary),
                ),
              ],
            ),
            style: theme.textTheme.titleLarge,
            semanticsLabel: AppBrand.shortName,
          ),
        ),
        PopupMenuButton<_HeaderAction>(
          tooltip: 'Appearance and About',
          initialValue: _HeaderAction.values
              .firstWhere((action) => action.themeMode == themeMode),
          onSelected: (action) {
            final mode = action.themeMode;
            if (mode != null) {
              onThemeChanged(mode);
            } else {
              showAboutDialog(
                context: context,
                applicationName: AppBrand.fullName,
                children: const [
                  Text(AppBrand.studio),
                  SizedBox(height: 8),
                  SelectableText(AppBrand.website),
                  SizedBox(height: 16),
                  Text(AppBrand.description),
                ],
              );
            }
          },
          icon: Icon(
              switch (themeMode) {
                ThemeMode.system => Icons.brightness_auto_outlined,
                ThemeMode.light => Icons.light_mode_outlined,
                ThemeMode.dark => Icons.dark_mode_outlined,
              },
              size: 21),
          itemBuilder: (context) => [
            for (final action in _HeaderAction.values)
              if (action.themeMode case final mode?)
                CheckedPopupMenuItem(
                  value: action,
                  checked: mode == themeMode,
                  child: Text(switch (mode) {
                    ThemeMode.system => 'Use system theme',
                    ThemeMode.light => 'Light',
                    ThemeMode.dark => 'Dark',
                  }),
                ),
            const PopupMenuDivider(),
            const PopupMenuItem(
              value: _HeaderAction.about,
              child: Text('About ClipThat!'),
            ),
          ],
        ),
      ],
    );
  }
}
