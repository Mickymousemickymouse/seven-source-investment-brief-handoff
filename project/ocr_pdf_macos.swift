import Foundation
import PDFKit
import Vision
import AppKit

guard CommandLine.arguments.count == 3,
      let document = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1])) else {
    fputs("usage: swift ocr_pdf_macos.swift INPUT.pdf OUTPUT.txt\n", stderr)
    exit(2)
}

var output = ""
for index in 0..<document.pageCount {
    guard let page = document.page(at: index) else { continue }
    let bounds = page.bounds(for: .mediaBox)
    let image = page.thumbnail(of: NSSize(width: bounds.width * 2, height: bounds.height * 2), for: .mediaBox)
    guard let tiff = image.tiffRepresentation,
          let bitmap = NSBitmapImageRep(data: tiff),
          let cgImage = bitmap.cgImage else { continue }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["zh-Hans", "en-US"]
    request.usesLanguageCorrection = true
    try VNImageRequestHandler(cgImage: cgImage).perform([request])
    output += "\n===== PAGE \(index + 1) =====\n"
    for observation in request.results ?? [] {
        if let text = observation.topCandidates(1).first?.string { output += text + "\n" }
    }
}
try output.write(to: URL(fileURLWithPath: CommandLine.arguments[2]), atomically: true, encoding: .utf8)
