import 'package:flutter/material.dart';

import 'app_brand.dart';
import 'screens/clip_workspace.dart';
import 'theme/app_theme.dart';

void main() => runApp(const ClipThatApp());

class ClipThatApp extends StatefulWidget {
  const ClipThatApp({super.key});

  @override
  State<ClipThatApp> createState() => _ClipThatAppState();
}

class _ClipThatAppState extends State<ClipThatApp> {
  ThemeMode _themeMode = ThemeMode.system;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: AppBrand.fullName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: _themeMode,
      home: ClipWorkspace(
        themeMode: _themeMode,
        onThemeChanged: (mode) => setState(() => _themeMode = mode),
      ),
    );
  }
}
