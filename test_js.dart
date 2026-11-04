import 'dart:js_interop';
import 'dart:typed_data';

void main() {
  final uint8List = Uint8List.fromList([1,2,3]);
  final blobParts = [uint8List.toJS].toJS;
}
