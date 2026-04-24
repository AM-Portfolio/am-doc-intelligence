
import 'package:flutter/material.dart';
import '../../services/api_service.dart';

class EmailExtractorView extends StatefulWidget {
  const EmailExtractorView({super.key});

  @override
  State<EmailExtractorView> createState() => _EmailExtractorViewState();
}

class _EmailExtractorViewState extends State<EmailExtractorView> {
  List<Map<String, dynamic>> _brokers = [];
  bool _loading = true;
  String _status = '';
  Map<String, dynamic>? _gmailStatus;
  
  // Health
  bool? _isServiceConnected;
  bool _checkingHealth = true;

  @override
  void initState() {
    super.initState();
    _checkHealthAndLoad();
  }

  Future<void> _checkHealthAndLoad() async {
    setState(() => _checkingHealth = true);
    final isConnected = await apiProvider.checkEmailExtractorHealth();
    
    setState(() {
      _isServiceConnected = isConnected;
      _checkingHealth = false;
    });

    if (isConnected) {
      _loadData();
    } else {
      setState(() {
        _status = 'Service disconnected. Cannot load brokers.';
        _loading = false;
      });
    }
  }

  Future<void> _loadData() async {
    setState(() => _loading = true);
    try {
      final brokersData = await apiProvider.getBrokers();
      await _checkGmail(); // Check connection status
      
      setState(() {
        _brokers = List<Map<String, dynamic>>.from(brokersData['brokers']);
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _status = 'Error loading data: $e';
        _loading = false;
      });
    }
  }

  Future<void> _checkGmail() async {
    try {
      final status = await apiProvider.checkGmailStatus();
      setState(() {
        _gmailStatus = status;
      });
    } catch (e) {
       // Ignore error for now or log
       print('Gmail check error: $e');
    }
  }

  Future<void> _extract(String brokerId) async {
    setState(() => _status = 'Extracting from $brokerId...');
    try {
      final result = await apiProvider.extractFromGmail(brokerId);
      setState(() {
        _status = 'Success! Extracted ${result['count']} holdings.\nID: ${result['db_id']}';
      });
    } catch (e) {
      setState(() {
        _status = 'Error extracting: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    bool isConnected = _gmailStatus?['connected'] == true;
    String email = _gmailStatus?['email'] ?? 'Not Connected';
    
    Color statusColor;
    String statusText;
    
    if (_checkingHealth) {
      statusColor = Colors.grey;
      statusText = 'Checking Service...';
    } else if (_isServiceConnected == true) {
      statusColor = Colors.green;
      statusText = 'Service Connected';
    } else {
      statusColor = Colors.red;
      statusText = 'Service Disconnected';
    }

    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Email Extractor',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: statusColor),
                ),
                child: Row(
                  children: [
                    Icon(Icons.circle, size: 12, color: statusColor),
                    const SizedBox(width: 8),
                    Text(statusText, style: TextStyle(color: statusColor, fontWeight: FontWeight.bold)),
                  ],
                ),
              )
            ],
          ),
          
          const SizedBox(height: 16),
          
          if (_isServiceConnected == false)
             Card(
              color: Theme.of(context).colorScheme.errorContainer,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline),
                    const SizedBox(width: 16),
                    const Text('Backend service is unreachable. Is Docker running?'),
                    const Spacer(),
                    TextButton(onPressed: _checkHealthAndLoad, child: const Text('Retry'))
                  ],
                ),
              ),
             ),

          const SizedBox(height: 16),
          
          Card(
            child: ListTile(
              leading: Icon(
                isConnected ? Icons.check_circle : Icons.warning,
                color: isConnected ? Colors.green : Colors.orange,
              ),
              title: Text('Gmail Status: $email'),
              trailing: isConnected 
                ? OutlinedButton(onPressed: () {}, child: const Text('Disconnect'))
                : FilledButton(onPressed: () {}, child: const Text('Connect')),
            ),
          ),
          const SizedBox(height: 24),
          if (_loading && _checkingHealth == false && _isServiceConnected == true)
            const CircularProgressIndicator()
          else if (_isServiceConnected == true)
            Expanded(
              child: ListView.builder(
                itemCount: _brokers.length,
                itemBuilder: (context, index) {
                  final broker = _brokers[index];
                  return Card(
                    margin: const EdgeInsets.symmetric(vertical: 8),
                    child: ListTile(
                      title: Text(broker['name']),
                      subtitle: Text('Format: ${broker['format']}'),
                      trailing: FilledButton.tonal(
                        onPressed: isConnected ? () => _extract(broker['id']) : null,
                        child: const Text('Extract'),
                      ),
                    ),
                  );
                },
              ),
            ),
          const SizedBox(height: 16),
          const Divider(),
          Text('Log:', style: Theme.of(context).textTheme.titleMedium),
          Container(
            padding: const EdgeInsets.all(12),
            width: double.infinity,
            height: 100,
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(8),
            ),
            child: SingleChildScrollView(child: Text(_status)),
          ),
        ],
      ),
    );
  }
}
