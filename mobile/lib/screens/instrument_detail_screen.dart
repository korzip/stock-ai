import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../api_client.dart';
import '../models.dart';

class InstrumentDetailScreen extends StatefulWidget {
  final Instrument instrument;
  const InstrumentDetailScreen({super.key, required this.instrument});

  @override
  State<InstrumentDetailScreen> createState() => _InstrumentDetailScreenState();
}

class _InstrumentDetailScreenState extends State<InstrumentDetailScreen> {
  final _api = ApiClient();
  bool _loading = true;
  String? _error;
  List<DailyPrice> _prices = [];
  List<Map<String, dynamic>> _events = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final json = await _api.getJson('/prices/daily', query: {
        'instrument_id': widget.instrument.id.toString(),
        'from_date': '2026-01-01',
        'to_date': '2026-01-31',
      });
      final list = (json['items'] as List).cast<Map<String, dynamic>>();
      setState(() {
        _prices = list.map(DailyPrice.fromJson).toList();
      });
      if (widget.instrument.marketCode == 'KR') {
        final items = await _api.getList('/events/dart', query: {
          'stock_code': widget.instrument.symbol,
          'limit': '5',
        });
        setState(() {
          _events = items.cast<Map<String, dynamic>>();
        });
      }
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final it = widget.instrument;
    final lastClose = _lastClose();
    final change = _change();

    return Scaffold(
      appBar: AppBar(title: Text('${it.symbol} · ${it.name}')),
      body: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        '${it.symbol} · ${it.name}',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ),
                    Chip(label: Text(it.marketCode)),
                    const SizedBox(width: 6),
                    Chip(label: Text(it.currency)),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            if (_loading) const LinearProgressIndicator(),
            if (_error != null)
              Text(
                _error!,
                style: const TextStyle(color: Colors.red),
              ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _statCard(
                    '최근 종가',
                    lastClose == null ? '-' : lastClose.toString(),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _statCard(
                    '기간 변동',
                    change == null ? '-' : change.toStringAsFixed(2),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Expanded(
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: _buildChart(),
                ),
              ),
            ),
            if (_events.isNotEmpty) ...[
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('최근 공시', style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      for (final e in _events)
                        ListTile(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          title: Text(
                            e['report_nm']?.toString() ?? '-',
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          subtitle: Text(e['published_at']?.toString() ?? '-'),
                          trailing: const Icon(Icons.open_in_new, size: 16),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  double? _lastClose() {
    final closes = _prices.where((p) => p.close != null).toList();
    if (closes.isEmpty) return null;
    return closes.last.close;
  }

  double? _change() {
    final closes = _prices.where((p) => p.close != null).toList();
    if (closes.length < 2) return null;
    return closes.last.close! - closes.first.close!;
  }

  Widget _statCard(String label, String value) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: Theme.of(context).textTheme.labelMedium),
            const SizedBox(height: 6),
            Text(value, style: Theme.of(context).textTheme.titleLarge),
          ],
        ),
      ),
    );
  }

  Widget _buildChart() {
    final closes = _prices.where((p) => p.close != null).toList();
    if (closes.isEmpty) {
      return const Center(child: Text('가격 데이터가 없습니다(데모 seed 기준)'));
    }

    final spots = <FlSpot>[];
    for (var i = 0; i < closes.length; i++) {
      spots.add(FlSpot(i.toDouble(), closes[i].close!));
    }

    return LineChart(
      LineChartData(
        titlesData: const FlTitlesData(show: true),
        gridData: const FlGridData(show: true),
        borderData: FlBorderData(show: true),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: false,
            dotData: const FlDotData(show: false),
          )
        ],
      ),
    );
  }
}
