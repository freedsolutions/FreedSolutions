// ===================================================
// usePdfExport Hook
// ===================================================
// Manages PDF generation and download state.
// Params: canvasRef, renderSlide, seriesSlides, activeSlide, exportPrefix
// Returns: { pdfDownload, pdfError, downloadCurrentPDF, downloadAllPDF, clearPdfDownload }

function usePdfExport(canvasRef, renderSlide, seriesSlides, activeSlide, exportPrefix) {
  var pdfUrlRef = useRef(null);
  var [pdfDownload, setPdfDownload] = useState(null);
  var [pdfError, setPdfError] = useState("");

  var clearPdfDownload = function() {
    if (pdfUrlRef.current) {
      URL.revokeObjectURL(pdfUrlRef.current);
      pdfUrlRef.current = null;
    }
    setPdfDownload(null);
  };

  var captureSlideJpegBinary = function(ctx, idx) {
    var canvas = canvasRef.current;
    renderSlide(ctx, idx);
    var dataUrl = canvas.toDataURL("image/jpeg", 0.92);
    var jpeg = extractJpegBinaryFromDataUrl(dataUrl);
    if (!jpeg || jpeg.length === 0) {
      throw new Error("Failed to capture JPEG data from canvas");
    }
    return jpeg;
  };

  var downloadCurrentPDF = function() {
    var canvas = canvasRef.current;
    if (!canvas) return;
    setPdfError("");
    try {
      var ctx = canvas.getContext("2d");
      var jpeg = captureSlideJpegBinary(ctx, activeSlide);
      var blob = buildPdfFromJpegs([jpeg], W, H);
      clearPdfDownload();
      var prefix = sanitizePrefix(exportPrefix);
      var nn = (activeSlide + 1 < 10 ? "0" : "") + (activeSlide + 1);
      var fileName = prefix + "-" + nn + ".pdf";
      var url = URL.createObjectURL(blob);
      pdfUrlRef.current = url;
      setPdfDownload({ name: fileName, url: url });
    } catch (err) {
      setPdfError("PDF generation failed");
    }
  };

  var downloadAllPDF = function() {
    var canvas = canvasRef.current;
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    var total = seriesSlides.length;
    setPdfError("");
    try {
      var jpegPages = [];
      for (var i = 0; i < total; i++) {
        jpegPages.push(captureSlideJpegBinary(ctx, i));
      }
      var blob = buildPdfFromJpegs(jpegPages, W, H);
      clearPdfDownload();
      var prefix = sanitizePrefix(exportPrefix);
      var fileName = prefix + "-all.pdf";
      var url = URL.createObjectURL(blob);
      pdfUrlRef.current = url;
      setPdfDownload({ name: fileName, url: url });
    } catch (err) {
      setPdfError("PDF generation failed");
    } finally {
      renderSlide(ctx, activeSlide);
    }
  };

  // Cleanup on unmount
  useEffect(function() {
    return function() {
      if (pdfUrlRef.current) {
        URL.revokeObjectURL(pdfUrlRef.current);
        pdfUrlRef.current = null;
      }
    };
  }, []);

  return {
    pdfDownload: pdfDownload,
    pdfError: pdfError,
    setPdfError: setPdfError,
    downloadCurrentPDF: downloadCurrentPDF,
    downloadAllPDF: downloadAllPDF,
    clearPdfDownload: clearPdfDownload
  };
}