
import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
// import 'package:http_parser/http_parser.dart';

class ApiService {
  // Ports from docker-compose
  static const String docProcessorBaseUrl = 'http://localhost:8082/api/v1'; // am-document-processor
  static const String emailExtractorBaseUrl = 'http://localhost:8080/api/v1'; // gmail-extractor

  // Headers (Simulating Gateway/Auth if needed, or allowing bypass if dev)
  // For internal testing, we might need to mock headers if the services expect them
  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    'X-User-ID': 'test-user-123', // Mock User ID for testing
    'Authorization': 'Bearer test-token', // Mock Token
  };

  // --- Document Processor endpoints ---

  Future<List<String>> getSupportedDocumentTypes() async {
    final response = await http.get(Uri.parse('$docProcessorBaseUrl/documents/types'));
    if (response.statusCode == 200) {
      return List<String>.from(jsonDecode(response.body));
    } else {
      throw Exception('Failed to load document types: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> processDocument(
      Uint8List fileBytes, String filename, String docType) async {
    var request = http.MultipartRequest(
      'POST',
      Uri.parse('$docProcessorBaseUrl/documents/process'),
    );
    
    request.headers.addAll({
      'X-User-ID': 'test-user-123',
    });

    request.fields['documentType'] = docType;
    request.files.add(http.MultipartFile.fromBytes(
      'file',
      fileBytes,
      filename: filename,
    ));

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to process document: ${response.body}');
    }
  }

  // --- Health Checks ---

  Future<bool> checkDocProcessorHealth() async {
    try {
      final response = await http.get(Uri.parse('http://localhost:8082/actuator/health'));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  Future<bool> checkEmailExtractorHealth() async {
    try {
      final response = await http.get(Uri.parse('$emailExtractorBaseUrl/health'));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  // --- Email Extractor endpoints ---

  Future<Map<String, dynamic>> checkGmailStatus() async {
    // Requires mocked JWT for now or dev mode
    // The python service validates JWT. We set JWT_SECRET=dev-secret-key-12345
    // We need to generate a valid JWT signed with that secret if we want to test properly.
    // Or we rely on the service being in a mode that accepts our token?
    // The service verifies signature.
    // We might need to implement a simple JWT generator or just handle 401.
    final response = await http.get(
      Uri.parse('$emailExtractorBaseUrl/gmail/status'),
      headers: _headers, 
    );
     // If auth fails, we'll see 401
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else if (response.statusCode == 401) {
       return {'connected': false, 'error': 'Auth failed (need valid JWT)'};
    }
     else {
      throw Exception('Failed to check status: ${response.body}');
    }
  }
  
  Future<Map<String, dynamic>> getBrokers() async {
      final response = await http.get(Uri.parse('$emailExtractorBaseUrl/brokers'));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to load brokers');
      }
  }
  
   Future<Map<String, dynamic>> extractFromGmail(String broker) async {
      final response = await http.get(
        Uri.parse('$emailExtractorBaseUrl/extract/gmail/$broker?pan=PANK1234F'), // Dummy PAN
        headers: _headers,
      );
      
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
         try {
             final err = jsonDecode(response.body);
             throw Exception(err['error'] ?? 'Extraction failed');
         } catch(_) {
             throw Exception('Extraction failed: ${response.body}');
         }
      }
  }
}

final apiProvider = ApiService();
