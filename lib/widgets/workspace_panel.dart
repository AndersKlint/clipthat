import 'package:flutter/material.dart';

class WorkspacePanel extends StatelessWidget {
  const WorkspacePanel({super.key, required this.child, this.padding = 28});

  final Widget child;
  final double padding;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Container(
      padding: EdgeInsets.all(padding),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: colors.outlineVariant),
      ),
      child: child,
    );
  }
}
