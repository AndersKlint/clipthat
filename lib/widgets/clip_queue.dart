import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../controllers/clip_controller.dart';
import '../models/clip_job.dart';
import '../models/clip_request.dart';
import 'workspace_panel.dart';

class ClipQueue extends StatelessWidget {
  const ClipQueue(
      {super.key,
      required this.controller,
      required this.onRetry,
      this.compact = false});

  final ClipController controller;
  final ValueChanged<ClipJob> onRetry;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final jobs = controller.jobs;
    final finished = jobs
        .where((job) =>
            job.status == ClipJobStatus.completed ||
            job.status == ClipJobStatus.failed)
        .length;
    return WorkspacePanel(
      padding: compact ? 20 : 28,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 12,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text('Clip queue (${jobs.length})',
                  style: theme.textTheme.titleLarge),
              if (finished > 0)
                TextButton(
                    onPressed: controller.clearFinished,
                    child: const Text('Clear finished')),
            ],
          ),
          if (jobs.isEmpty)
            const _EmptyQueue()
          else ...[
            const SizedBox(height: 16),
            for (final job in jobs) ...[
              _JobCard(
                key: ValueKey(job.id),
                job: job,
                onRemove: () => controller.remove(job),
                onRetry: controller.toolsReady && !controller.checkingTools
                    ? () => onRetry(job)
                    : null,
              ),
              if (job != jobs.last) const SizedBox(height: 8),
            ],
          ],
        ],
      ),
    );
  }
}

class _EmptyQueue extends StatelessWidget {
  const _EmptyQueue();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 36),
      child: Center(
        child: Text(
          'No clips queued.',
          style: theme.textTheme.bodyMedium!
              .copyWith(color: theme.colorScheme.onSurfaceVariant),
        ),
      ),
    );
  }
}

class _JobCard extends StatelessWidget {
  const _JobCard(
      {super.key,
      required this.job,
      required this.onRemove,
      required this.onRetry});

  final ClipJob job;
  final VoidCallback onRemove;
  final VoidCallback? onRetry;

  Future<void> _copyPath(BuildContext context) async {
    try {
      await Clipboard.setData(ClipboardData(text: job.outputPath!));
      if (!context.mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Output path copied')));
    } catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Could not copy path: $error')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final failed = job.status == ClipJobStatus.failed;
    final completed = job.status == ClipJobStatus.completed;
    final color = failed
        ? colors.error
        : job.isActive
            ? colors.primary
            : colors.onSurfaceVariant;
    final progress = job.progress?.clamp(0.0, 1.0);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: colors.surfaceContainerLow,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
            color: failed
                ? colors.error.withValues(alpha: 0.35)
                : colors.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(job.request.videoId,
                        style: theme.textTheme.titleSmall,
                        overflow: TextOverflow.ellipsis),
                    const SizedBox(height: 3),
                    Text(
                      '${formatTimestamp(job.request.startSeconds)} → ${formatTimestamp(job.request.endSeconds)} · ${formatTimestamp(job.request.durationSeconds)}',
                      style: theme.textTheme.bodySmall!
                          .copyWith(color: colors.onSurfaceVariant),
                    ),
                  ],
                ),
              ),
              if (!job.isActive)
                IconButton(
                    tooltip: 'Remove from queue',
                    onPressed: onRemove,
                    icon: const Icon(Icons.close_rounded, size: 18),
                    visualDensity: VisualDensity.compact),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 12,
            runSpacing: 4,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Tooltip(
                message: job.request.includeSubtitles
                    ? job.request.includeAutomaticTranslations
                        ? 'This clip requests all available manual tracks, generated captions, and automatic translations for embedding in the MKV. Missing tracks warn without failing the clip.'
                        : 'This clip requests all available manual subtitle tracks only for embedding in the MKV. Missing manual tracks warn without failing the clip.'
                    : 'Subtitles not requested',
                child: Text(
                  '${job.statusLabel}${job.isActive && progress != null ? ' · ${(progress * 100).round()}%' : ''}',
                  style: theme.textTheme.labelMedium!.copyWith(color: color),
                ),
              ),
              if (failed)
                TextButton(onPressed: onRetry, child: const Text('Retry')),
            ],
          ),
          if (job.isActive) ...[
            const SizedBox(height: 10),
            LinearProgressIndicator(value: progress, minHeight: 5),
          ],
          if (job.error != null) ...[
            const SizedBox(height: 10),
            _JobMessage(
                label: 'Error', message: job.error!, color: colors.error),
          ],
          if (job.warning != null) ...[
            const SizedBox(height: 10),
            _JobMessage(
                label: 'Warning',
                message: job.warning!,
                color: colors.onSurfaceVariant),
          ],
          if (completed && job.outputPath != null) ...[
            const SizedBox(height: 12),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: SelectableText(job.outputPath!,
                      style: theme.textTheme.bodySmall),
                ),
                IconButton(
                  tooltip: 'Copy output path',
                  onPressed: () => _copyPath(context),
                  icon: const Icon(Icons.copy_outlined, size: 16),
                  visualDensity: VisualDensity.compact,
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _JobMessage extends StatelessWidget {
  const _JobMessage(
      {required this.label, required this.message, required this.color});

  final String label;
  final String message;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ExpansionTile(
      tilePadding: EdgeInsets.zero,
      childrenPadding: const EdgeInsets.only(top: 8, bottom: 8),
      expandedCrossAxisAlignment: CrossAxisAlignment.start,
      shape: const Border(),
      collapsedShape: const Border(),
      dense: true,
      title: Text(label,
          style: theme.textTheme.labelMedium!.copyWith(color: color)),
      subtitle: Text(
        message.trimLeft().split('\n').first,
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
        style: theme.textTheme.bodySmall!.copyWith(color: color),
      ),
      children: [
        ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 240),
          child: SingleChildScrollView(
            child: SelectableText(message, style: theme.textTheme.bodySmall),
          ),
        ),
      ],
    );
  }
}
