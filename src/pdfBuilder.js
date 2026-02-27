// ===================================================
// PDF Builder (pure utility functions)
// ===================================================

function sanitizePrefix(raw) {
  var trimmed = (raw || "").replace(/^\s+|\s+$/g, "");
  if (!trimmed) return "linkedin-slide";
  return trimmed.replace(/[^a-zA-Z0-9_\-]/g, "_");
}

function decodeBase64ToBinary(b64) {
  if (!b64 || typeof b64 !== "string") return "";
  return atob(b64);
}

function extractJpegBinaryFromDataUrl(dataUrl) {
  if (!dataUrl || typeof dataUrl !== "string") return "";
  if (dataUrl.indexOf("data:image/jpeg;base64,") !== 0) return "";
  var marker = "base64,";
  var idx = dataUrl.indexOf(marker);
  if (idx === -1) return "";
  return decodeBase64ToBinary(dataUrl.substring(idx + marker.length));
}

function buildPdfFromJpegs(jpegPages, pageW, pageH) {
  if (!jpegPages || jpegPages.length === 0) {
    throw new Error("No JPEG pages to encode");
  }
  var numPages = jpegPages.length;
  var pieces = [];
  var pos = 0;
  var offsets = {};

  var writeStr = function(s) {
    pieces.push(s);
    pos += s.length;
  };

  var markObj = function(n) {
    offsets[n] = pos;
  };

  var padOffset = function(n) {
    var s = n.toString();
    while (s.length < 10) s = "0" + s;
    return s;
  };

  // Header
  writeStr("%PDF-1.4\n");

  // Object numbering:
  // 1 = Catalog, 2 = Pages
  // Per page i: 3+i*3 = Page, 4+i*3 = Content stream, 5+i*3 = Image XObject
  var totalObjs = 2 + numPages * 3;

  // 1: Catalog
  markObj(1);
  writeStr("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n");

  // 2: Pages
  markObj(2);
  var kids = "";
  for (var k = 0; k < numPages; k++) {
    if (k > 0) kids += " ";
    kids += (3 + k * 3) + " 0 R";
  }
  writeStr("2 0 obj\n<< /Type /Pages /Kids [" + kids + "] /Count " + numPages + " >>\nendobj\n");

  // Each page
  for (var i = 0; i < numPages; i++) {
    var pgObj = 3 + i * 3;
    var ctObj = 4 + i * 3;
    var imObj = 5 + i * 3;
    var jpeg = jpegPages[i];
    if (!jpeg || jpeg.length === 0) {
      throw new Error("Invalid JPEG page payload");
    }
    var cs = "q " + pageW + " 0 0 " + pageH + " 0 0 cm /Im0 Do Q";

    markObj(pgObj);
    writeStr(pgObj + " 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 " + pageW + " " + pageH + "] /Contents " + ctObj + " 0 R /Resources << /XObject << /Im0 " + imObj + " 0 R >> >> >>\nendobj\n");

    markObj(ctObj);
    writeStr(ctObj + " 0 obj\n<< /Length " + cs.length + " >>\nstream\n" + cs + "\nendstream\nendobj\n");

    markObj(imObj);
    var imHeader = imObj + " 0 obj\n<< /Type /XObject /Subtype /Image /Width " + pageW + " /Height " + pageH + " /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length " + jpeg.length + " >>\nstream\n";
    writeStr(imHeader);
    writeStr(jpeg);
    writeStr("\nendstream\nendobj\n");
  }

  // xref table
  var xrefPos = pos;
  writeStr("xref\n0 " + (totalObjs + 1) + "\n");
  writeStr("0000000000 65535 f\r\n");
  for (var n = 1; n <= totalObjs; n++) {
    writeStr(padOffset(offsets[n]) + " 00000 n\r\n");
  }

  writeStr("trailer\n<< /Size " + (totalObjs + 1) + " /Root 1 0 R >>\nstartxref\n" + xrefPos + "\n%%EOF\n");

  // Convert binary string pieces to Uint8Array
  var totalLen = 0;
  for (var t = 0; t < pieces.length; t++) {
    totalLen += pieces[t].length;
  }
  var buf = new Uint8Array(totalLen);
  var off = 0;
  for (var t2 = 0; t2 < pieces.length; t2++) {
    var s = pieces[t2];
    for (var c = 0; c < s.length; c++) {
      buf[off++] = s.charCodeAt(c) & 0xFF;
    }
  }

  return new Blob([buf], { type: "application/pdf" });
}