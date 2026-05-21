
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:intl/intl.dart';
import 'package:am_design_system/am_design_system.dart';
import '../../services/api_service.dart';
import '../../utils/file_downloader.dart';

class DocumentProcessorView extends StatefulWidget {
  const DocumentProcessorView({super.key});

  @override
  State<DocumentProcessorView> createState() => _DocumentProcessorViewState();
}

class _DocumentProcessorViewState extends State<DocumentProcessorView> {
  List<String> _docTypes = [];
  String? _selectedDocType;
  String? _selectedBrokerType = 'ZERODHA';
  bool _loadingTypes = true;
  String _status = '';
  Map<String, dynamic>? _lastResult;
  bool _processing = false;
  
  // Health check
  bool? _isServiceConnected;
  bool _checkingHealth = true;
  
  @override
  void initState() {
    super.initState();
    _checkHealthAndLoad();
  }

  Future<void> _checkHealthAndLoad() async {
    setState(() => _checkingHealth = true);
    final isConnected = await apiProvider.checkDocProcessorHealth();
    
    setState(() {
      _isServiceConnected = isConnected;
      _checkingHealth = false;
    });

    if (isConnected) {
      _loadDocTypes();
    } else {
      setState(() {
        _status = 'Service disconnected. Cannot load types.';
        _loadingTypes = false;
      });
    }
  }

  Future<void> _loadDocTypes() async {
    try {
      final types = await apiProvider.getSupportedDocumentTypes();
      setState(() {
        _docTypes = types;
        if (types.isNotEmpty) {
          _selectedDocType = types.first;
        }
        _loadingTypes = false;
      });
    } catch (e) {
      setState(() {
        _status = 'Error loading types: $e';
        _loadingTypes = false;
      });
    }
  }

  void _downloadSample() {
    // Import utility
    // ignore: avoid_web_libraries_in_flutter
    FileDownloader.downloadCSV(FileDownloader.getDummyPortfolioCSV(), 'sample_portfolio.csv');
    setState(() => _status = 'Sample file downloaded!');
  }

  Future<void> _pickAndUpload() async {
    if (_selectedDocType == null) return;

    FilePickerResult? result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'xlsx', 'xls', 'csv'],
      withData: true,
    );

    if (result != null) {
      PlatformFile file = result.files.first;
      setState(() {
        _status = 'Uploading ${file.name}...';
        _processing = true;
        _lastResult = null;
      });

      try {
        final response = await apiProvider.processDocument(
          file.bytes!, 
          file.name, 
          _selectedDocType!,
          brokerType: _selectedBrokerType ?? 'ZERODHA'
        );
        setState(() {
          _lastResult = response;
          _status = 'Success! Processed ${file.name}';
          _processing = false;
        });
      } catch (e) {
        setState(() {
          _status = 'Error uploading: $e';
          _processing = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
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
            _buildConfigurationSection(),
            const SizedBox(height: 24),
            _buildUploadSection(),
            const SizedBox(height: 24),
            if (_status.isNotEmpty || _processing) _buildStatusLog(),
            if (_lastResult != null) ...[
              const SizedBox(height: 24),
              _buildResultSection(),
            ],
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
              'Document Intelligence',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
            Text(
              'Automated parser for financial statements',
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
                  boxShadow: [
                    BoxShadow(
                      color: statusColor.withOpacity(0.5),
                      blurRadius: 4,
                      spreadRadius: 2,
                    )
                  ],
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
            Text(
              'Backend service is unreachable',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Current Environment: ${apiProvider.environment == AppEnvironment.local ? "Local" : "Preprod"}',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 24),
            AppButton(
              text: 'Retry Connection',
              onPressed: _checkHealthAndLoad,
              type: AppButtonType.primary,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildConfigurationSection() {
    return GlassCard(
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.settings_outlined, color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 12),
                Text('Parser Configuration', style: Theme.of(context).textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Document Type', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 8),
                      _loadingTypes 
                        ? const ShimmerLoading(child: SkeletonBox(height: 45, width: double.infinity))
                        : CustomDropdown<String>(
                            value: _selectedDocType,
                            items: _docTypes.map((type) => type.toDropdownItem(text: type)).toList(),
                            hint: 'Select Doc Type',
                            onChanged: (v) => setState(() => _selectedDocType = v),
                          ),
                    ],
                  ),
                ),
                const SizedBox(width: 20),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Broker / Institution', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 8),
                      CustomDropdown<String>(
                        value: _selectedBrokerType,
                        items: apiProvider.brokerTypes.map((broker) => broker.toDropdownItem(text: broker)).toList(),
                        hint: 'Select Broker',
                        onChanged: (v) => setState(() => _selectedBrokerType = v),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }


  Widget _buildUploadSection() {
    return GlassCard(
      child: InkWell(
        onTap: (_processing || _selectedDocType == null) ? null : _pickAndUpload,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 20),
          decoration: BoxDecoration(
            border: Border.all(
              color: Theme.of(context).colorScheme.primary.withOpacity(0.3),
              style: BorderStyle.solid,
              width: 2,
            ),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            children: [
              _processing 
                ? const CircularProgressIndicator()
                : Icon(
                    Icons.upload_file_outlined, 
                    size: 64, 
                    color: Theme.of(context).colorScheme.primary
                  ),
              const SizedBox(height: 16),
              Text(
                _processing ? 'Processing Document...' : 'Click to select or Drop files here',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: Theme.of(context).colorScheme.primary,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              const Text('Supports PDF, Excel (XLSX, XLS), and CSV'),
              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  TextButton.icon(
                    onPressed: _downloadSample, 
                    icon: const Icon(Icons.download, size: 18),
                    label: const Text('Download Sample Portfolio'),
                  ),
                ],
              )
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatusLog() {
    bool isError = _status.toLowerCase().contains('error');
    Color statusColor = isError ? Colors.red : Colors.blue;

    return Container(
      padding: const EdgeInsets.all(16),
      width: double.infinity,
      decoration: BoxDecoration(
        color: statusColor.withOpacity(0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: statusColor.withOpacity(0.2)),
      ),
      child: Row(
        children: [
          Icon(isError ? Icons.error_outline : Icons.info_outline, color: statusColor, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              _status.isEmpty ? 'Ready for next upload' : _status,
              style: TextStyle(color: statusColor, fontWeight: FontWeight.w500),
            ),
          ),
          if (_processing)
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
        ],
      ),
    );
  }

  Widget _buildResultSection() {
    if (_lastResult == null) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.analytics_outlined, color: Theme.of(context).colorScheme.primary),
            const SizedBox(width: 12),
            Text('Processing Result', style: Theme.of(context).textTheme.titleLarge),
          ],
        ),
        const SizedBox(height: 16),
        GlassCard(
          child: Padding(
            padding: const EdgeInsets.all(20.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    _buildStatTile('Status', _lastResult!['status'] ?? 'N/A', Icons.check_circle_outline, Colors.green),
                    const SizedBox(width: 12),
                    _buildStatTile('Process ID', _lastResult!['processId']?.toString().substring(0, 8) ?? 'N/A', Icons.tag, Colors.blue),
                    const SizedBox(width: 12),
                    _buildStatTile('Items', _lastResult!['count']?.toString() ?? '0', Icons.list, Colors.orange),
                  ],
                ),
                const SizedBox(height: 24),
                const Text('Response Data (Raw)', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  width: double.infinity,
                  constraints: const BoxConstraints(maxHeight: 300),
                  decoration: BoxDecoration(
                    color: Colors.black87,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: SingleChildScrollView(
                    child: Text(
                      JsonEncoder.withIndent('  ').convert(_lastResult),
                      style: const TextStyle(
                        color: Colors.greenAccent, 
                        fontFamily: 'monospace',
                        fontSize: 12,
                      ),
                    ),
                  ),
                ),

              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildStatTile(String label, String value, IconData icon, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: color.withOpacity(0.05),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.1)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 16, color: color),
                const SizedBox(width: 8),
                Text(label, style: TextStyle(fontSize: 12, color: color, fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              value,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}
