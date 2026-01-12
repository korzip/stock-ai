import 'package:flutter/material.dart';

import '../api_client.dart';

class ChatMsg {
  final String role;
  final String text;
  final Map<String, dynamic>? data;
  final List<dynamic>? trace;
  ChatMsg(this.role, this.text, {this.data, this.trace});
}

class AiChatScreen extends StatefulWidget {
  const AiChatScreen({super.key});

  @override
  State<AiChatScreen> createState() => _AiChatScreenState();
}

class _AiChatScreenState extends State<AiChatScreen> {
  final _api = ApiClient();
  final _controller = TextEditingController();
  bool _sending = false;
  String? _prevResponseId;
  final List<ChatMsg> _msgs = [
    ChatMsg(
      'assistant',
      '안녕하세요. 종목(티커/코드/이름)을 말하면 최근 가격(데모)과 함께 요약해 드립니다. 예: "AAPL", "005930", "삼성전자"',
    )
  ];

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _sending) return;

    setState(() {
      _msgs.add(ChatMsg('user', text));
      _sending = true;
      _controller.clear();
    });

    try {
      final body = <String, dynamic>{'message': text};
      if (_prevResponseId != null) {
        body['previous_response_id'] = _prevResponseId;
      }
      final json = await _api.postJson('/ai/chat', body);
      _prevResponseId = json['response_id']?.toString();
      final reply = _formatReply(json);
      final data = json['data'] is Map<String, dynamic>
          ? (json['data'] as Map<String, dynamic>)
          : null;
      final trace = json['mcp_trace'] is List ? (json['mcp_trace'] as List) : null;
      setState(() => _msgs.add(ChatMsg('assistant', reply, data: data, trace: trace)));
    } catch (e) {
      setState(() => _msgs.add(ChatMsg('assistant', '에러: $e')));
    } finally {
      setState(() => _sending = false);
    }
  }

  String _formatReply(Map<String, dynamic> json) {
    final data = json['data'];
    if (data is Map<String, dynamic>) {
      final lines = <String>[];
      final summary = data['summary'];
      if (summary is String && summary.isNotEmpty) {
        lines.add(summary);
      }
      final keyPoints = data['key_points'];
      if (keyPoints is List && keyPoints.isNotEmpty) {
        lines.add('핵심 포인트:');
        for (final p in keyPoints) {
          lines.add('- $p');
        }
      }
      final riskNotes = data['risk_notes'];
      if (riskNotes is List && riskNotes.isNotEmpty) {
        lines.add('리스크/주의:');
        for (final r in riskNotes) {
          lines.add('- $r');
        }
      }
      final disclaimer = data['disclaimer'];
      if (disclaimer is String && disclaimer.isNotEmpty) {
        lines.add(disclaimer);
      }
      if (lines.isNotEmpty) {
        return lines.join('\n');
      }
    }
    return (json['assistant_message'] ?? json['message'] ?? '').toString();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  const Icon(Icons.auto_awesome, size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'AI 코치(데모) · MCP 도구 기반',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: _msgs.length,
            itemBuilder: (_, i) {
              final m = _msgs[i];
              final isUser = m.role == 'user';
              if (!isUser && m.data != null) {
                return _assistantCard(context, m);
              }
              return Align(
                alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(
                  margin: const EdgeInsets.symmetric(vertical: 6),
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: isUser
                        ? Colors.teal.withOpacity(0.12)
                        : Colors.white.withOpacity(0.9),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: isUser
                          ? Colors.teal.withOpacity(0.3)
                          : Colors.black12,
                    ),
                  ),
                  child: Text(m.text),
                ),
              );
            },
          ),
        ),
        if (_sending)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            child: Row(
              children: [
                const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
                const SizedBox(width: 8),
                Text(
                  '응답 생성 중...',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        const Divider(height: 1),
        Padding(
          padding: const EdgeInsets.all(8),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _controller,
                  decoration: const InputDecoration(
                    hintText: '메시지 입력 (예: AAPL 최근 종가 알려줘)',
                    border: OutlineInputBorder(),
                  ),
                  onSubmitted: (_) => _send(),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: _sending ? null : _send,
                child: const Text('전송'),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _assistantCard(BuildContext context, ChatMsg msg) {
    final data = msg.data ?? {};
    final summary = data['summary']?.toString() ?? msg.text;
    final keyPoints = (data['key_points'] is List) ? data['key_points'] as List : [];
    final riskNotes = (data['risk_notes'] is List) ? data['risk_notes'] as List : [];
    final nextActions =
        (data['next_actions'] is List) ? data['next_actions'] as List : [];
    final dataUsed = (data['data_used'] is List) ? data['data_used'] as List : [];
    final candidates =
        (data['candidates'] is List) ? data['candidates'] as List : [];
    final resolved = data['resolved_instrument'];

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(summary, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 10),
            if (keyPoints.isNotEmpty) _bulletSection('핵심 포인트', keyPoints),
            if (riskNotes.isNotEmpty) _bulletSection('리스크/주의', riskNotes),
            if (nextActions.isNotEmpty) _bulletSection('다음 액션', nextActions),
            if (resolved is Map<String, dynamic>)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(
                  '확정 종목: ${resolved['symbol']} · ${resolved['name']}',
                  style: Theme.of(context).textTheme.labelMedium,
                ),
              ),
            if (candidates.isNotEmpty) _candidateSection(candidates),
            if (dataUsed.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Wrap(
                  spacing: 6,
                  children: [
                    for (final d in dataUsed)
                      Chip(
                        label: Text(d.toString()),
                        visualDensity: VisualDensity.compact,
                      ),
                  ],
                ),
              ),
            if (msg.trace != null && msg.trace!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  '툴 호출 로그 ${msg.trace!.length}건',
                  style: Theme.of(context).textTheme.labelMedium,
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _bulletSection(String title, List items) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          for (final item in items) Text('- ${item.toString()}'),
        ],
      ),
    );
  }

  Widget _candidateSection(List items) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('후보 종목', style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          for (final c in items)
            Text('- ${c['symbol']} · ${c['name']}'),
        ],
      ),
    );
  }
}
