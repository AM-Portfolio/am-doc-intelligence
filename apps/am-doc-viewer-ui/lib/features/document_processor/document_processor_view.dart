
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:intl/intl.dart';
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
  bool _loadingTypes = true;
  String _status = '';
  
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
      });

      try {
        final response = await apiProvider.processDocument(
          file.bytes!, 
          file.name, 
          _selectedDocType!
        );
        setState(() {
          _status = 'Success! Process ID: ${response['processId'] ?? 'N/A'}\n'
                    'Status: ${response['status'] ?? 'Unknown'}';
        });
      } catch (e) {
        setState(() {
          _status = 'Error uploading: $e';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
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
                'Dr. M Document Processor',
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
          const SizedBox(height: 24),
          
          if (_checkingHealth)
            const LinearProgressIndicator()
          else if (_isServiceConnected == false)
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
          
          // Sample Data Section
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                   Text('Test Data', style: Theme.of(context).textTheme.titleMedium),
                   const SizedBox(height: 8),
                   const Text('Need a file to test connection? Download a sample CSV here.'),
                   const SizedBox(height: 8),
                   ElevatedButton.icon(
                     onPressed: _downloadSample, 
                     icon: const Icon(Icons.download),
                     label: const Text('Download Sample Portfolio'),
                   ),
                ],
              ),
            ),
          ),
          
          const SizedBox(height: 32),
          const Text('Upload Document'),
          const SizedBox(height: 16),
          
          if (_loadingTypes && _isServiceConnected == true)
            const CircularProgressIndicator()
          else 
            Row(
              children: [
                DropdownButton<String>(
                  value: _selectedDocType,
                  hint: const Text('Select Type'),
                  items: _docTypes.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
                  onChanged: (v) => setState(() => _selectedDocType = v),
                  disabledHint: const Text('No Types Available'),
                ),
                const SizedBox(width: 16),
                ElevatedButton.icon(
                  onPressed: (_isServiceConnected == true && _selectedDocType != null) ? _pickAndUpload : null,
                  icon: const Icon(Icons.upload_file),
                  label: const Text('Upload & Process'),
                ),
              ],
            ),
          const SizedBox(height: 32),
          const Divider(),
          const SizedBox(height: 16),
          Text('Status Log:', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(12),
            width: double.infinity,
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(_status.isEmpty ? 'Ready' : _status),
          ),
        ],
      ),
    );
  }
}
