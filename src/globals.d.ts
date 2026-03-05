// ===================================================
// Global symbol declarations for LSP cross-file navigation.
// Consumed by TypeScript's language server only — NOT included in the build.
// Update this file when adding new global symbols to any source file.
// ===================================================

// --- constants.js ---
declare var W: number;
declare var H: number;
declare var MARGIN: number;
declare var BORDER_RADIUS: number;
declare var BORDER_WIDTH: number;
declare var GREEN: string;
declare var FOOTER_PIC_SIZE: number;
declare var FOOTER_BADGE_H: number;
declare var MAX_SLIDES: number;
declare var FONT_OPTIONS: Array<{ value: string; label: string }>;
declare var DEFAULT_FONT: string;
declare var CANVAS: {
  pad: number;
  innerPad: number;
  headingLH: number;
  headingBlankLH: number;
  bodyLH: number;
  bodyBlankLH: number;
  cardLineSpacing: number;
  cardBlankLH: number;
  cardGap: number;
  cardPadV: number;
  cardTextPad: number;
  cardMinH: number;
  cardExtraH: number;
  cardRadius: number;
  cardFirstLineY: number;
  cardCheckRadius: number;
  cardCheckOffsetY: number;
  ssRadius: number;
  ssMinH: number;
  ssBottomPad: number;
  ssFloorExpandHeading: number;
  ssFloorExpandNoHeading: number;
  ssFloorNormalHeading: number;
  ssFloorNormalNoHeading: number;
  footerBadgeW: number;
  footerBadgeRadius: number;
  footerTextY: number;
  footerPicOffsetY: number;
  footerStrokeWidth: number;
  accentBarW: number;
  accentBarH: number;
  accentBarOffset: number;
  cardGapAfterHeadingExpand: number;
  cardGapAfterHeading: number;
  cardGapNoHeadingExpand: number;
  cardGapNoHeading: number;
  bodyGapAfterHeadingExpand: number;
  bodyGapAfterHeading: number;
  bodyGapNoHeadingExpand: number;
  bodyGapNoHeading: number;
};
declare var GEO_SHAPES: Array<{ id: string; label: string }>;
declare function composeFont(family: string, size: number, weight: boolean | string, italic: boolean): string;

// --- layoutTokens.js ---
declare var SPACE: Record<number, number>;
declare var RADIUS: { sm: number; md: number; lg: number; xl: number; xxl: number; pill: number };
declare var Z: { dropdown: number; modal: number };
declare var SIZE: Record<string, number>;
declare var SURFACE: Record<string, string>;
declare var CLR: Record<string, string>;
declare function panelBtn(overrides?: object): object;
declare function toggleBtn(isOn: boolean, overrides?: object): object;
declare function uploadFrameStyle(overrides?: object): object;
declare function uploadBtnStyle(hasFile: boolean): object;
declare function dividerStyle(): object;
declare function dialogOverlay(): object;
declare function dialogBox(maxWidth?: number): object;
declare function dialogBtn(isPrimary: boolean): object;

// --- canvas/hexToRgba.js ---
declare function hexToRgba(hex: string, opacity?: number): string;

// --- canvas/backgrounds.js ---
declare function renderBg(ctx: CanvasRenderingContext2D, bgType: string, solidColor: string, customImg: any, geoLines: string, geoEnabled: boolean, geoOpacity: number, geoShape: string): void;

// --- canvas/text.js ---
declare function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number, fontSize: number, fontWeight?: string, fontFamily?: string, fontItalic?: boolean): string[];
declare function extractAccentMarkers(text: string): { cleanText: string; markers: any[] };
declare function renderLineWithAccents(ctx: CanvasRenderingContext2D, line: string, x: number, y: number, fontSize: number, baseWeight: string, baseColor: string, accentColor: string, markers: any[], lineOffset: number, fontFamily?: string, fontItalic?: boolean): void;

// --- canvas/overlays.js ---
declare function drawCenteredFooter(ctx: CanvasRenderingContext2D, profileImg: any, name: string, borderBottom: number, footerBg: string, footerText: string, textSize: number, opacity: number, fontFamily: string, fontBold: boolean, fontItalic: boolean): void;
declare function drawTopCorner(ctx: CanvasRenderingContext2D, text: string, color: string, opacity: number, size: number, fontFamily: string, fontBold: boolean, fontItalic: boolean, bgColor: string, bgOpacity: number): void;
declare function drawBottomCorner(ctx: CanvasRenderingContext2D, text: string, color: string, opacity: number, size: number, fontFamily: string, fontBold: boolean, fontItalic: boolean, bgColor: string, bgOpacity: number): void;
declare function drawBorderFrame(ctx: CanvasRenderingContext2D, top: number, bottom: number, hasFooter: boolean, strokeColor: string): void;

// --- canvas/screenshot.js ---
declare function drawScreenshot(ctx: CanvasRenderingContext2D, screenshot: any, x: number, y: number, w: number, h: number, scale: number, edgeToEdge: boolean): void;

// --- canvas/renderSlideContent.js ---
declare function renderSlideContent(ctx: CanvasRenderingContext2D, slide: any, screenshot: any, colors: any, sizes: any, scale: number, frameTop: number, frameBottom: number): void;

// --- canvas/renderSlide.js ---
declare function renderSlideToCanvas(ctx: CanvasRenderingContext2D, slideIndex: number, seriesSlides: any[], slideAssets: any): void;

// --- slideFactory.js ---
declare function makeDefaultSlide(title?: string, body?: string): any;

// --- undoRedo.js ---
declare var UNDO_MAX: number;
declare function createUndoManager(): {
  pushSnapshot(snapshot: any): void;
  undo(currentSnapshot: any): any;
  redo(currentSnapshot: any): any;
  canUndo(): boolean;
  canRedo(): boolean;
};

// --- pdfBuilder.js ---
declare function sanitizePrefix(raw: string): string;
declare function buildPdfFromJpegs(jpegPages: any[], pageW: number, pageH: number): Blob;

// --- ColorPickerInline.jsx ---
declare function ColorPickerInline(props: any): any;
declare function drawShapeThumbnail(ctx: CanvasRenderingContext2D, shapeId: string, w: number, h: number): void;

// --- SizeControl.jsx ---
declare function SizeControl(props: any): any;

// --- SlideSelector.jsx ---
declare function SlideSelector(props: any): any;

// --- useSlideManagement.js ---
declare function useSlideManagement(deps: any): any;

// --- useCanvasRenderer.js ---
declare function useCanvasRenderer(canvasRef: any, seriesSlides: any[], slideAssets: any, activeSlide: number): { renderSlide: () => void };

// --- usePdfExport.js ---
declare function usePdfExport(canvasRef: any, renderSlide: () => void, seriesSlides: any[], activeSlide: number, exportPrefix: string): any;

// --- usePresets.js ---
declare var PRESET_SLIDE_KEYS: string[];
declare function normalizeLegacyFontFamily(value: string): string;
declare function usePresets(deps: any): any;
