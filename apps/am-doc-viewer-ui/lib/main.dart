import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:am_design_system/am_design_system.dart';
import 'package:am_auth_ui/am_auth_ui.dart';
import 'features/document_processor/document_processor_view.dart';
import 'features/email_extractor/email_extractor_view.dart';
import 'services/api_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  debugPrint('AM Doc Intelligence Utility starting...');
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiBlocProvider(
      providers: [
        ...AuthProviders.providers,
        BlocProvider<ThemeCubit>(
          create: (context) => ThemeCubit(ThemeRepository()),
        ),
      ],
      child: BlocBuilder<ThemeCubit, ThemeState>(
        builder: (context, themeState) {
          return MaterialApp(
            title: 'AM Doc Intelligence',
            debugShowCheckedModeBanner: false,
            theme: themeState.lightTheme,
            darkTheme: themeState.darkTheme,
            themeMode: themeState.themeMode,
            home: const AuthWrapper(
              child: DocParserShell(),
            ),
          );
        },
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
  @override
  void initState() {
    super.initState();
    debugPrint('DocParserShell initialized. Env: ${apiProvider.environment}');
  }

  String _activeNavItem = 'Doc Processor';

  @override
  Widget build(BuildContext context) {
    return UnifiedSidebarScaffold(
      title: 'Doc Intelligence',
      icon: Icons.psychology_outlined,
      accentColor: Theme.of(context).colorScheme.primary,
      onThemeToggle: () {
        context.read<ThemeCubit>().toggleTheme();
      },
      items: [
        SecondarySidebarItem(
          title: 'Doc Processor',
          icon: Icons.description_outlined,
          onTap: () {
            setState(() {
              _activeNavItem = 'Doc Processor';
            });
          },
        ),
        SecondarySidebarItem(
          title: 'Email Extractor',
          icon: Icons.email_outlined,
          onTap: () {
            setState(() {
              _activeNavItem = 'Email Extractor';
            });
          },
        ),
        const SidebarDivider(),
        SecondarySidebarItem(
          title: 'Environment: ${apiProvider.environment == AppEnvironment.local ? "Local" : "Preprod"}',
          icon: apiProvider.environment == AppEnvironment.local ? Icons.lan_outlined : Icons.cloud_outlined,
          onTap: () {
            setState(() {
              apiProvider.environment = apiProvider.environment == AppEnvironment.local 
                  ? AppEnvironment.preprod 
                  : AppEnvironment.local;
            });
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('Switched to ${apiProvider.environment == AppEnvironment.local ? "Local" : "Preprod"} Backend'),
                behavior: SnackBarBehavior.floating,
                width: 400,
                duration: const Duration(seconds: 2),
              ),
            );
          },
        ),
      ],
      body: AnimatedSwitcher(
        duration: const Duration(milliseconds: 300),
        child: KeyedSubtree(
          key: ValueKey('${_activeNavItem}_${apiProvider.environment}'),
          child: _activeNavItem == 'Doc Processor'
              ? const DocumentProcessorView()
              : const EmailExtractorView(),
        ),
      ),
    );
  }
}
