import 'package:flutter/material.dart';

import '../controllers/clip_controller.dart';

class ToolStatusBanner extends StatelessWidget {
  const ToolStatusBanner({super.key, required this.controller});

  final ClipController controller;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final checking = controller.checkingTools;
    final ready = controller.toolsReady;
    final missing = controller.tools.where((tool) => !tool.available).toList();
    final guidance =
        'Repair or reinstall ClipThat! to restore its bundled tools, then refresh. '
        'Keep the complete tools folder beside the application executable.';
    final tooltip = [
      for (final tool in controller.tools)
        '${tool.name}: ${tool.version ?? (tool.available ? 'available' : 'unavailable')}',
      if (!ready && !checking) guidance,
      'YouTube support uses bundled yt-dlp, FFmpeg, ffprobe and Deno.',
    ].join('\n');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 48),
          child: Row(
            children: [
              Expanded(
                child: Tooltip(
                  message: tooltip,
                  child: Semantics(
                    liveRegion: true,
                    child: Text(
                      checking
                          ? 'Checking bundled tools…'
                          : ready
                              ? 'Bundled tools ready'
                              : 'Bundled tools need repair: ${missing.map((tool) => tool.name).join(', ')}',
                      style: theme.textTheme.bodySmall!
                          .copyWith(color: colors.onSurfaceVariant),
                    ),
                  ),
                ),
              ),
              IconButton(
                tooltip: 'Refresh tool status',
                onPressed: checking ? null : controller.checkTools,
                icon: const Icon(Icons.refresh_rounded, size: 20),
                color: colors.onSurfaceVariant,
              ),
            ],
          ),
        ),
        if (!ready && !checking)
          ExpansionTile(
            tilePadding: EdgeInsets.zero,
            childrenPadding: const EdgeInsets.only(bottom: 12),
            dense: true,
            shape: const Border(),
            collapsedShape: const Border(),
            textColor: colors.onSurfaceVariant,
            collapsedTextColor: colors.onSurfaceVariant,
            iconColor: colors.onSurfaceVariant,
            collapsedIconColor: colors.onSurfaceVariant,
            title: const Text('Bundled tool details'),
            children: [
              ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 240),
                child: SingleChildScrollView(
                  primary: false,
                  child: SizedBox(
                    width: double.infinity,
                    child: SelectableText(
                      [
                        guidance,
                        for (final tool in missing)
                          '${tool.name}: ${tool.error ?? 'Unavailable; repair or reinstall ClipThat!.'}',
                      ].join('\n\n'),
                      style: theme.textTheme.bodySmall!
                          .copyWith(color: colors.onSurfaceVariant),
                    ),
                  ),
                ),
              ),
            ],
          ),
      ],
    );
  }
}
