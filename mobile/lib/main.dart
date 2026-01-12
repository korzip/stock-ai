import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import 'screens/ai_chat_screen.dart';
import 'screens/search_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: '.env');
  runApp(const StockAiApp());
}

class StockAiApp extends StatelessWidget {
  const StockAiApp({super.key});

  @override
  Widget build(BuildContext context) {
    final colorScheme =
        ColorScheme.fromSeed(seedColor: const Color(0xFF0C6B58));
    return MaterialApp(
      title: 'StockAI',
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: colorScheme,
        scaffoldBackgroundColor: const Color(0xFFF6F4EF),
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.transparent,
          elevation: 0,
        ),
        cardTheme: const CardThemeData(
          elevation: 0,
          color: Color(0xFFFFFFFF),
          surfaceTintColor: Colors.transparent,
          margin: EdgeInsets.symmetric(vertical: 6),
        ),
      ),
      home: const Home(),
    );
  }
}

class Home extends StatefulWidget {
  const Home({super.key});

  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  int idx = 0;

  @override
  Widget build(BuildContext context) {
    final pages = const [
      SearchScreen(),
      AiChatScreen(),
      PlaceholderWidget('관심/알림(다음 단계)'),
      PlaceholderWidget('포트폴리오/기록(다음 단계)'),
      PlaceholderWidget('인사이트(다음 단계)'),
    ];

    return Scaffold(
      appBar: AppBar(title: const Text('StockAI')),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFFF6F4EF), Color(0xFFF1F7F5)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: SafeArea(child: pages[idx]),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: idx,
        onDestinationSelected: (i) => setState(() => idx = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.search), label: '발굴'),
          NavigationDestination(icon: Icon(Icons.chat_bubble_outline), label: 'AI'),
          NavigationDestination(icon: Icon(Icons.notifications_none), label: '관심'),
          NavigationDestination(icon: Icon(Icons.pie_chart_outline), label: '포트폴리오'),
          NavigationDestination(icon: Icon(Icons.insights), label: '인사이트'),
        ],
      ),
    );
  }
}

class PlaceholderWidget extends StatelessWidget {
  final String text;
  const PlaceholderWidget(this.text, {super.key});

  @override
  Widget build(BuildContext context) => Center(child: Text(text));
}
