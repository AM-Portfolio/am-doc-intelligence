import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:http/browser_client.dart';

enum AppEnvironment { local, preprod }

class ApiService {
  AppEnvironment environment = AppEnvironment.preprod;

  // Create a BrowserClient with withCredentials = false
  // This ensures the browser doesn't send cookies/credentials,
  // allowing the server's "Access-Control-Allow-Origin: *" to work.
  http.Client _makeClient() {
    if (kIsWeb) {
      final client = BrowserClient()..withCredentials = false;
      return client;
    }
    return http.Client();
  }

  // Base URLs — matching test_api.py exactly
  String get _docBase {
    if (environment == AppEnvironment.local) {
      return 'http://localhost:8080/v1';
    }
    return kIsWeb ? '/doc/processor/v1' : 'https://am.asrax.in/doc/processor/v1';
  }

  String get _emailBase {
    if (environment == AppEnvironment.local) {
      return 'http://localhost:8080/api/v1';
    }
    return kIsWeb ? '/email/api/v1' : 'https://am.asrax.in/email/api/v1';
  }

  // Credentials — matching test_api.py exactly
  static const String _authToken =
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NzkwMDcyNzUsImlhdCI6MTc3ODkyMDg3NSwic3ViIjoiYjc1NzQzYzktZmUwZS00YzU0LThlZTAtOGRhMzUwY2MyN2IzIiwidXNlcm5hbWUiOiJzc2QyNjU4QGdtYWlsLmNvbSIsImVtYWlsIjoic3NkMjY1OEBnbWFpbC5jb20iLCJzY29wZXMiOlsicmVhZCIsIndyaXRlIl19.uqaDH_iDEZeSgnjOD7Q5gnG3MrE8jnxzhrPgYQjUUpU";
  static const String _userId = "b75743c9-fe0e-4c54-8ee0-8da350cc27b3";

  Map<String, String> get _headers => {
        'Authorization': 'Bearer $_authToken',
        'X-User-ID': _userId,
      };

  final List<String> brokerTypes = [
    'ZERODHA',
    'UPSTOX',
    'GROWW',
    'ICICI_DIRECT',
    'HDFC_SECURITIES',
    'ANGEL_ONE',
    'OTHER',
  ];

  // --- Document Processor endpoints ---

  Future<List<String>> getSupportedDocumentTypes() async {
    final url = '$_docBase/documents/types';
    debugPrint('[ApiService] GET $url');
    final client = _makeClient();
    try {
      final response = await client
          .get(Uri.parse(url), headers: _headers)
          .timeout(const Duration(seconds: 10));
      debugPrint('[ApiService] types: ${response.statusCode}');
      if (response.statusCode == 200) {
        return List<String>.from(jsonDecode(response.body));
      }
      throw Exception('types failed: ${response.statusCode} ${response.body}');
    } catch (e) {
      debugPrint('[ApiService] types error: $e');
      throw Exception('Connection error: $e');
    } finally {
      client.close();
    }
  }

  Future<Map<String, dynamic>> processDocument(
      Uint8List fileBytes, String filename, String docType,
      {String brokerType = 'ZERODHA'}) async {
    final url = '$_docBase/documents/process';
    debugPrint('[ApiService] POST $url (type=$docType, broker=$brokerType)');
    var request = http.MultipartRequest('POST', Uri.parse(url));
    request.headers.addAll(_headers);
    request.fields['brokerType'] = brokerType;
    request.fields['documentType'] = docType;
    request.files
        .add(http.MultipartFile.fromBytes('file', fileBytes, filename: filename));

    final client = _makeClient();
    try {
      final streamedResponse = await client.send(request);
      final response = await http.Response.fromStream(streamedResponse);
      debugPrint('[ApiService] process: ${response.statusCode}');
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      throw Exception(
          'Process failed: ${response.statusCode}\n${response.body}');
    } finally {
      client.close();
    }
  }

  // --- Health Checks ---

  Future<bool> checkDocProcessorHealth() async {
    final url = '$_docBase/documents/types';
    debugPrint('[ApiService] Health -> GET $url');
    final client = _makeClient();
    try {
      final response = await client
          .get(Uri.parse(url), headers: _headers)
          .timeout(const Duration(seconds: 10));
      debugPrint('[ApiService] Health: ${response.statusCode}');
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[ApiService] Health failed: $e');
      return false;
    } finally {
      client.close();
    }
  }

  Future<bool> checkEmailExtractorHealth() async {
    final url = '$_emailBase/health';
    debugPrint('[ApiService] Email health -> GET $url');
    final client = _makeClient();
    try {
      final response = await client
          .get(Uri.parse(url), headers: _headers)
          .timeout(const Duration(seconds: 10));
      debugPrint('[ApiService] Email health: ${response.statusCode}');
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[ApiService] Email health failed: $e');
      return false;
    } finally {
      client.close();
    }
  }

  // --- Email Extractor endpoints ---

  Future<Map<String, dynamic>> checkGmailStatus() async {
    final url = '$_emailBase/gmail/status';
    debugPrint('[ApiService] GET $url');
    final client = _makeClient();
    try {
      final response = await client
          .get(Uri.parse(url), headers: _headers)
          .timeout(const Duration(seconds: 10));
      debugPrint('[ApiService] gmail/status: ${response.statusCode}');
      if (response.statusCode == 200) return jsonDecode(response.body);
      return {'connected': false, 'error': 'Status ${response.statusCode}'};
    } catch (e) {
      debugPrint('[ApiService] gmail/status error: $e');
      return {'connected': false, 'error': '$e'};
    } finally {
      client.close();
    }
  }

  Future<Map<String, dynamic>> getBrokers() async {
    final url = '$_emailBase/brokers';
    debugPrint('[ApiService] GET $url');
    final client = _makeClient();
    try {
      final response = await client
          .get(Uri.parse(url), headers: _headers)
          .timeout(const Duration(seconds: 10));
      debugPrint('[ApiService] brokers: ${response.statusCode}');
      if (response.statusCode == 200) return jsonDecode(response.body);
      throw Exception('Failed to load brokers: ${response.statusCode}');
    } finally {
      client.close();
    }
  }

  Future<Map<String, dynamic>> extractFromGmail(String broker) async {
    final url = '$_emailBase/extract/gmail/$broker?pan=PANK1234F';
    debugPrint('[ApiService] GET $url');
    final client = _makeClient();
    try {
      final response = await client
          .get(Uri.parse(url), headers: _headers)
          .timeout(const Duration(seconds: 30));
      debugPrint('[ApiService] extract: ${response.statusCode}');
      if (response.statusCode == 200) return jsonDecode(response.body);
      throw Exception(
          'Extraction failed: ${response.statusCode}\n${response.body}');
    } finally {
      client.close();
    }
  }
}

final apiProvider = ApiService();
