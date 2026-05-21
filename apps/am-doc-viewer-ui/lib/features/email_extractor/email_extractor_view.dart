
import 'package:flutter/material.dart';
import 'package:am_design_system/am_design_system.dart';
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
       debugPrint('Gmail check error: $e');
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
    
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(),
          const SizedBox(height: 32),
          
          if (_checkingHealth)
            const LinearProgressIndicator()
          else if (_isServiceConnected == false)
             _buildConnectionError()
          else ...[
            _buildGmailStatusCard(isConnected, email),
            const SizedBox(height: 32),
            Row(
              children: [
                Icon(Icons.list_alt_outlined, color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 12),
                Text('Available Brokers', style: Theme.of(context).textTheme.titleLarge),
              ],
            ),
            const SizedBox(height: 16),
            if (_loading)
               const ShimmerLoading(height: 200, width: double.infinity)
            else
               _buildBrokerList(isConnected),
            const SizedBox(height: 32),
            _buildStatusLog(),
          ],
        ],
      ),
    );
  }

  Widget _buildHeader() {
    Color statusColor = _isServiceConnected == true ? Colors.green : (_isServiceConnected == false ? Colors.red : Colors.grey);
    String statusText = _isServiceConnected == true ? 'Online' : (_isServiceConnected == false ? 'Offline' : 'Checking...');

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Email Extractor',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
            Text(
              'Extract portfolio data directly from your email',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: statusColor.withOpacity(0.1),
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: statusColor.withOpacity(0.5)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  color: statusColor,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 10),
              Text(
                statusText,
                style: TextStyle(
                  color: statusColor,
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        )
      ],
    );
  }

  Widget _buildConnectionError() {
    return GlassCard(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          children: [
            Icon(Icons.cloud_off_outlined, size: 48, color: Theme.of(context).colorScheme.error),
            const SizedBox(height: 16),
            const Text('Email service is unreachable', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 24),
            AppButton(
              label: 'Retry Connection',
              onPressed: _checkHealthAndLoad,
              variant: AppButtonVariant.primary,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildGmailStatusCard(bool isConnected, String email) {
    return GlassCard(
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: (isConnected ? Colors.green : Colors.orange).withOpacity(0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(
                isConnected ? Icons.mark_email_read_outlined : Icons.mail_lock_outlined,
                color: isConnected ? Colors.green : Colors.orange,
                size: 32,
              ),
            ),
            const SizedBox(width: 20),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isConnected ? 'Gmail Connected' : 'Gmail Not Connected',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  Text(
                    isConnected ? email : 'Connect your account to extract data',
                    style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant),
                  ),
                ],
              ),
            ),
            AppButton(
              label: isConnected ? 'Disconnect' : 'Connect Gmail',
              onPressed: () {},
              variant: isConnected ? AppButtonVariant.secondary : AppButtonVariant.primary,
              size: AppButtonSize.small,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBrokerList(bool isConnected) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        childAspectRatio: 3,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
      ),
      itemCount: _brokers.length,
      itemBuilder: (context, index) {
        final broker = _brokers[index];
        return GlassCard(
          child: Padding(
            padding: const EdgeInsets.all(12.0),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primaryContainer.withOpacity(0.3),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(Icons.account_balance_outlined, color: Theme.of(context).colorScheme.primary, size: 24),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(broker['name'], style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                      Text('Format: ${broker['format']}', style: const TextStyle(fontSize: 11)),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: isConnected ? () => _extract(broker['id']) : null,
                  icon: Icon(Icons.download_for_offline_outlined, color: isConnected ? Theme.of(context).colorScheme.primary : Colors.grey),
                  tooltip: 'Extract Data',
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildStatusLog() {
    if (_status.isEmpty) return const SizedBox.shrink();
    
    bool isError = _status.toLowerCase().contains('error');
    Color statusColor = isError ? Colors.red : Theme.of(context).colorScheme.primary;

    return Container(
      padding: const EdgeInsets.all(16),
      width: double.infinity,
      decoration: BoxDecoration(
        color: statusColor.withOpacity(0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: statusColor.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(isError ? Icons.error_outline : Icons.info_outline, color: statusColor, size: 20),
              const SizedBox(width: 12),
              const Text('Extraction Status', style: TextStyle(fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 8),
          Text(_status, style: TextStyle(color: statusColor)),
        ],
      ),
    );
  }
}
