
import 'dart:convert';
// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

class FileDownloader {
  static void downloadCSV(String content, String fileName) {
    final bytes = utf8.encode(content);
    final blob = html.Blob([bytes]);
    final url = html.Url.createObjectUrlFromBlob(blob);
    final anchor = html.AnchorElement(href: url)
      ..setAttribute("download", fileName)
      ..click();
    html.Url.revokeObjectUrl(url);
  }

  static String getDummyPortfolioCSV() {
    return '''
Symbol,ISIN,Quantity,Average Price,Current Price
HDFCBANK,INE040A01034,50,1450.00,1600.00
RELIANCE,INE002A01018,10,2400.00,2500.00
INFY,INE009A01021,25,1300.00,1450.00
TCS,INE467B01029,5,3200.00,3500.00
''';
  }
}
