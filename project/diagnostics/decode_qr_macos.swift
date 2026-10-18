import CoreImage
import Foundation

guard CommandLine.arguments.count == 2,
      let image = CIImage(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])),
      let detector = CIDetector(ofType: CIDetectorTypeQRCode,
                                context: CIContext(options: [.useSoftwareRenderer: true]),
                                options: [CIDetectorAccuracy: CIDetectorAccuracyHigh]) else {
    exit(2)
}
let enlarged = image.transformed(by: CGAffineTransform(scaleX: 8, y: 8))
for feature in detector.features(in: enlarged) {
    if let qr = feature as? CIQRCodeFeature, let value = qr.messageString {
        print(value)
    }
}
