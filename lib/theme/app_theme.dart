import 'package:flutter/material.dart';

abstract final class AppTheme {
  static final light = _create(Brightness.light);
  static final dark = _create(Brightness.dark);

  static ThemeData _create(Brightness brightness) {
    final dark = brightness == Brightness.dark;
    final colors = ColorScheme.fromSeed(
      seedColor: const Color(0xFFAE4E53),
      brightness: brightness,
      primary: dark ? const Color(0xFFD56D70) : const Color(0xFFAE4E53),
      onPrimary: dark ? const Color(0xFF190606) : Colors.white,
      primaryContainer:
          dark ? const Color(0xFF303033) : const Color(0xFFECECEE),
      onPrimaryContainer:
          dark ? const Color(0xFFF1F1F3) : const Color(0xFF29292D),
      secondary: dark ? const Color(0xFFC4C4CA) : const Color(0xFF54545B),
      onSecondary: dark ? const Color(0xFF202023) : Colors.white,
      secondaryContainer:
          dark ? const Color(0xFF343438) : const Color(0xFFE6E6E9),
      onSecondaryContainer:
          dark ? const Color(0xFFECECEF) : const Color(0xFF29292D),
      tertiary: dark ? const Color(0xFFBFC1C6) : const Color(0xFF53565D),
      onTertiary: dark ? const Color(0xFF202125) : Colors.white,
      tertiaryContainer:
          dark ? const Color(0xFF33353A) : const Color(0xFFE5E6E9),
      onTertiaryContainer:
          dark ? const Color(0xFFE9EAED) : const Color(0xFF292B30),
      surface: dark ? const Color(0xFF202023) : Colors.white,
      onSurface: dark ? const Color(0xFFF2F2F4) : const Color(0xFF202024),
      onSurfaceVariant:
          dark ? const Color(0xFFBDBDC5) : const Color(0xFF5D5D66),
      outline: dark ? const Color(0xFF85858F) : const Color(0xFF777780),
      outlineVariant: dark ? const Color(0xFF48484F) : const Color(0xFFCCCCD2),
      surfaceDim: dark ? const Color(0xFF141416) : const Color(0xFFDDDDE2),
      surfaceBright: dark ? const Color(0xFF3B3B40) : Colors.white,
      surfaceContainerLowest:
          dark ? const Color(0xFF151517) : const Color(0xFFF7F7F9),
      surfaceContainerLow:
          dark ? const Color(0xFF29292D) : const Color(0xFFF0F0F3),
      surfaceContainer:
          dark ? const Color(0xFF2E2E33) : const Color(0xFFECECEF),
      surfaceContainerHigh:
          dark ? const Color(0xFF35353B) : const Color(0xFFE6E6EA),
      surfaceContainerHighest:
          dark ? const Color(0xFF3D3D44) : const Color(0xFFDFDFE4),
      surfaceTint: Colors.transparent,
      inverseSurface: dark ? const Color(0xFFECECEF) : const Color(0xFF29292D),
      onInverseSurface:
          dark ? const Color(0xFF29292D) : const Color(0xFFF2F2F4),
      inversePrimary: dark ? const Color(0xFFAE4E53) : const Color(0xFFD56D70),
      primaryFixed: const Color(0xFFE5E5E9),
      primaryFixedDim: const Color(0xFFC9C9D0),
      onPrimaryFixed: const Color(0xFF202024),
      onPrimaryFixedVariant: const Color(0xFF484850),
      secondaryFixed: const Color(0xFFE5E5E9),
      secondaryFixedDim: const Color(0xFFC9C9D0),
      onSecondaryFixed: const Color(0xFF202024),
      onSecondaryFixedVariant: const Color(0xFF484850),
      tertiaryFixed: const Color(0xFFE4E6E9),
      tertiaryFixedDim: const Color(0xFFC8CBD0),
      onTertiaryFixed: const Color(0xFF202125),
      onTertiaryFixedVariant: const Color(0xFF474A50),
      error: dark ? const Color(0xFFFFB4AB) : const Color(0xFF9C241D),
      onError: dark ? const Color(0xFF570B08) : Colors.white,
      errorContainer: dark ? const Color(0xFF492624) : const Color(0xFFFFEDEA),
      onErrorContainer:
          dark ? const Color(0xFFFFDAD5) : const Color(0xFF731812),
      shadow: Colors.black,
      scrim: Colors.black,
    );
    final base = ThemeData(useMaterial3: true, colorScheme: colors);
    final text = base.textTheme.copyWith(
      titleLarge: base.textTheme.titleLarge!.copyWith(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.3,
      ),
      titleMedium:
          base.textTheme.titleMedium!.copyWith(fontWeight: FontWeight.w600),
      bodyMedium: base.textTheme.bodyMedium!.copyWith(height: 1.5),
      bodySmall: base.textTheme.bodySmall!.copyWith(height: 1.5),
      labelSmall: base.textTheme.labelSmall!.copyWith(letterSpacing: 0.5),
    );
    final border = OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: BorderSide(color: colors.outlineVariant),
    );
    return base.copyWith(
      scaffoldBackgroundColor:
          dark ? const Color(0xFF141416) : const Color(0xFFF3F3F5),
      textTheme: text,
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: colors.surfaceContainerLowest,
        border: border,
        enabledBorder: border,
        focusedBorder: border.copyWith(
            borderSide: BorderSide(color: colors.primary, width: 2)),
        errorBorder:
            border.copyWith(borderSide: BorderSide(color: colors.error)),
        focusedErrorBorder: border.copyWith(
            borderSide: BorderSide(color: colors.error, width: 2)),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        hintStyle: TextStyle(color: colors.onSurfaceVariant),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(0, 44),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: colors.onSurface,
          minimumSize: const Size(0, 44),
          side: BorderSide(color: colors.outlineVariant),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      ),
      dividerTheme: DividerThemeData(color: colors.outlineVariant, space: 24),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: colors.primary,
        linearTrackColor: colors.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(4),
      ),
      snackBarTheme:
          const SnackBarThemeData(behavior: SnackBarBehavior.floating),
      tooltipTheme:
          const TooltipThemeData(waitDuration: Duration(milliseconds: 450)),
    );
  }
}
