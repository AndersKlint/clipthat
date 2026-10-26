import 'package:flutter/material.dart';

import 'portal_path_presentation.dart';

class OutputFolderField extends StatefulWidget {
  const OutputFolderField({
    super.key,
    required this.controller,
    required this.onChanged,
    required this.onSubmitted,
    required this.onBrowse,
    required this.pickingDirectory,
  });

  final TextEditingController controller;
  final ValueChanged<String> onChanged;
  final ValueChanged<String> onSubmitted;
  final VoidCallback onBrowse;
  final bool pickingDirectory;

  @override
  State<OutputFolderField> createState() => _OutputFolderFieldState();
}

class _OutputFolderFieldState extends State<OutputFolderField> {
  final _display = TextEditingController();
  final _focus = FocusNode();

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_syncDisplay);
    _focus.addListener(_syncDisplay);
    _syncDisplay();
  }

  @override
  void didUpdateWidget(OutputFolderField oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.controller != widget.controller) {
      oldWidget.controller.removeListener(_syncDisplay);
      widget.controller.addListener(_syncDisplay);
      _syncDisplay();
    }
  }

  void _syncDisplay() {
    final raw = widget.controller.text;
    final text = _focus.hasFocus ? raw : outputFolderLabel(raw);
    if (_display.text == text) return;
    _display.value = TextEditingValue(
      text: text,
      selection: TextSelection.collapsed(offset: text.length),
    );
  }

  @override
  void dispose() {
    widget.controller.removeListener(_syncDisplay);
    _focus.removeListener(_syncDisplay);
    _display.dispose();
    _focus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: widget.controller.text,
      child: TextField(
        controller: _display,
        focusNode: _focus,
        onChanged: (value) {
          widget.controller.value = _display.value;
          widget.onChanged(value);
        },
        autocorrect: false,
        textInputAction: TextInputAction.done,
        onSubmitted: (_) => widget.onSubmitted(widget.controller.text),
        decoration: InputDecoration(
          hintText: 'Choose an output folder',
          labelText: 'Output folder',
          suffixIcon: IconButton(
            tooltip: 'Choose output folder',
            onPressed: widget.pickingDirectory
                ? null
                : () {
                    _focus.unfocus();
                    widget.onBrowse();
                  },
            icon: widget.pickingDirectory
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.folder_open_rounded, size: 21),
          ),
        ),
      ),
    );
  }
}
