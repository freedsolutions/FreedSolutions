// ===================================================
// useCanvasRenderer Hook
// ===================================================
// Manages canvas rendering with 40ms debounce.
// Also generates offscreen thumbnail data URLs for each slide.
// Params: canvasRef, seriesSlides, slideAssets, sizes, profileImg, activeSlide
// Returns: { renderSlide, thumbUrls }

function useCanvasRenderer(canvasRef, seriesSlides, slideAssets, sizes, profileImg, activeSlide) {
  var renderTimerRef = useRef(null);
  var thumbCanvasRef = useRef(null);
  var thumbRenderingRef = useRef(false);
  var thumbQueuedRef = useRef(false);
  var thumbHashesRef = useRef([]);
  var thumbUrlsRef = useRef(null);
  var [thumbUrls, setThumbUrls] = useState(function() {
    var init = seriesSlides.map(function() { return null; });
    thumbUrlsRef.current = init;
    return init;
  });

  var renderSlide = useCallback(function(ctx, slideIndex) {
    renderSlideToCanvas(ctx, slideIndex, seriesSlides, slideAssets, sizes, profileImg);
  }, [sizes, profileImg, seriesSlides, slideAssets]);

  var render = useCallback(function() {
    var canvas = canvasRef.current;
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    renderSlide(ctx, activeSlide);
  }, [renderSlide, activeSlide]);

  // Build a lightweight fingerprint for a slide to detect changes
  var buildSlideHash = useCallback(function(slide, asset) {
    var parts = [];
    var keys = Object.keys(slide);
    for (var k = 0; k < keys.length; k++) {
      var key = keys[k];
      var val = slide[key];
      if (key === "customBgImage") {
        parts.push(key + ":" + (val ? (val.src ? val.src.length : "img") : "null"));
      } else if (key === "cards") {
        parts.push(key + ":" + (val ? val.join("|") : ""));
      } else {
        parts.push(key + ":" + String(val));
      }
    }
    if (asset && asset.image) {
      parts.push("asset:" + (asset.image.src ? asset.image.src.length : "img") + ":" + (asset.scale || 1));
    }
    if (profileImg) {
      parts.push("profile:" + (profileImg.src ? profileImg.src.length : "img"));
    }
    parts.push("sizes:" + JSON.stringify(sizes));
    return parts.join(";");
  }, [profileImg, sizes]);

  // Generate thumbnails for all slides on the offscreen canvas
  var generateThumbnails = useCallback(function() {
    if (thumbRenderingRef.current) {
      thumbQueuedRef.current = true;
      return;
    }
    thumbRenderingRef.current = true;

    if (!thumbCanvasRef.current) {
      thumbCanvasRef.current = document.createElement("canvas");
      thumbCanvasRef.current.width = W;
      thumbCanvasRef.current.height = H;
    }
    var offCanvas = thumbCanvasRef.current;
    var offCtx = offCanvas.getContext("2d");

    var newUrls = [];
    var newHashes = [];
    var oldHashes = thumbHashesRef.current;
    var oldUrls = thumbUrlsRef.current || [];
    var changed = seriesSlides.length !== oldUrls.length;

    for (var i = 0; i < seriesSlides.length; i++) {
      var slide = seriesSlides[i];
      var asset = slideAssets[i] || { image: null, name: null, scale: 1 };
      var hash = buildSlideHash(slide, asset);
      newHashes.push(hash);

      if (!changed && i < oldHashes.length && oldHashes[i] === hash && oldUrls[i]) {
        newUrls.push(oldUrls[i]);
      } else {
        changed = true;
        try {
          renderSlideToCanvas(offCtx, i, seriesSlides, slideAssets, sizes, profileImg);
          newUrls.push(offCanvas.toDataURL("image/jpeg", 0.5));
        } catch (e) {
          newUrls.push(null);
        }
      }
    }

    thumbHashesRef.current = newHashes;
    if (changed) {
      thumbUrlsRef.current = newUrls;
      setThumbUrls(newUrls);
    }

    thumbRenderingRef.current = false;
    if (thumbQueuedRef.current) {
      thumbQueuedRef.current = false;
      setTimeout(generateThumbnails, 0);
    }
  }, [seriesSlides, slideAssets, sizes, profileImg, buildSlideHash]);

  useEffect(function() {
    if (renderTimerRef.current) clearTimeout(renderTimerRef.current);
    renderTimerRef.current = setTimeout(function() {
      render();
      generateThumbnails();
    }, 40);
    return function() {
      if (renderTimerRef.current) clearTimeout(renderTimerRef.current);
    };
  }, [render, generateThumbnails]);

  // Keep thumbUrls array length in sync with seriesSlides length
  useEffect(function() {
    setThumbUrls(function(prev) {
      if (prev.length === seriesSlides.length) return prev;
      var next = [];
      for (var i = 0; i < seriesSlides.length; i++) {
        next.push(i < prev.length ? prev[i] : null);
      }
      thumbUrlsRef.current = next;
      return next;
    });
  }, [seriesSlides.length]);

  return { renderSlide: renderSlide, thumbUrls: thumbUrls };
}