import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:am_auth_ui/am_auth_ui.dart';
import 'package:am_design_system/am_design_system.dart';
import 'features/document_processor/document_processor_view.dart';
import 'features/email_extractor/email_extractor_view.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiBlocProvider(
      providers: AuthProviders.providers,
      child: MaterialApp(
        title: 'AM Doc Parser Util',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF6750A4),
            brightness: Brightness.light,
          ),
          useMaterial3: true,
          textTheme: GoogleFonts.interTextTheme(),
        ),
        darkTheme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFFD0BCFF),
            brightness: Brightness.dark,
          ),
          useMaterial3: true,
          textTheme: GoogleFonts.interTextTheme(ThemeData.dark().textTheme),
        ),
        themeMode: ThemeMode.system,
        home: const AuthWrapper(
          child: DocParserShell(),
        ),
      ),
    );
  }
}

class DocParserShell extends StatefulWidget {
  const DocParserShell({super.key});

  @override
  State<DocParserShell> createState() => _DocParserShellState();
}

class _DocParserShellState extends State<DocParserShell> {
  String _activeNavItem = 'Doc Processor';

  @override
  Widget build(BuildContext context) {
    return UnifiedSidebarScaffold(
      title: 'Doc Parser',
      subtitle: 'Intelligence Service',
      icon: Icons.analytics_outlined,
      accentColor: const Color(0xFF6750A4),
      items: [
        SecondarySidebarItem(
          title: 'Doc Processor',
          icon: Icons.description_outlined,
          isSelected: _activeNavItem == 'Doc Processor',
          onTap: () {
            setState(() {
              _activeNavItem = 'Doc Processor';
            });
          },
        ),
        SecondarySidebarItem(
          title: 'Email Extractor',
          icon: Icons.email_outlined,
          isSelected: _activeNavItem == 'Email Extractor',
          onTap: () {
            setState(() {
              _activeNavItem = 'Email Extractor';
            });
          },
        ),
      ],
      body: _activeNavItem == 'Doc Processor'
          ? const DocumentProcessorView()
          : const EmailExtractorView(),
    );
  }
}
