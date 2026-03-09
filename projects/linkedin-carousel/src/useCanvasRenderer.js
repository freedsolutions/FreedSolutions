// ===================================================
// useCanvasRenderer Hook
// ===================================================
// Manages canvas rendering with 40ms debounce.
// Params: canvasRef, seriesSlides, slideAssets, activeSlide
// Returns: { renderSlide }

function useCanvasRenderer(canvasRef, seriesSlides, slideAssets, activeSlide) {
  var renderTimerRef = useRef(null);

  var renderSlide = useCallback(function(ctx, slideIndex) {
    renderSlideToCanvas(ctx, slideIndex, seriesSlides, slideAssets);
  }, [seriesSlides, slideAssets]);

  var render = useCallback(function() {
    var canvas = canvasRef.current;
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    renderSlide(ctx, activeSlide);
  }, [renderSlide, activeSlide]);

  useEffect(function() {
    if (renderTimerRef.current) clearTimeout(renderTimerRef.current);
    renderTimerRef.current = setTimeout(function() {
      render();
    }, 40);
    return function() {
      if (renderTimerRef.current) clearTimeout(renderTimerRef.current);
    };
  }, [render]);

  return { renderSlide: renderSlide };
}