// ===================================================
// Layout Tokens — design system constants
// ===================================================

// --- Spacing scale ---
// Every gap, margin, and padding should use one of these values.
var SPACE = { 0: 0, 1: 2, 2: 4, 3: 6, 4: 8, 5: 10, 6: 12, 7: 16, 8: 24, 9: 48 };

// --- Border radius scale ---
var RADIUS = { sm: 4, md: 6, lg: 8, xl: 10, xxl: 12, pill: 20 };

// --- Z-index layers ---
var Z = { dropdown: 60, modal: 9999 };

// --- Component sizes ---
var SIZE = {
  swatchBtn: 18,
  swatch: 20,
  colorInput: 24,
  stepper: 28,
  stepperInput: 30,
  slideBtn: 35,
  toggleSm: 32,
  toggleMd: 44,
  removeBadge: 16,
  uploadFrame: 88,
  uploadBtn: 24,
  uploadBgWidth: 107,
  leftPane: 220,
  rightPaneMax: 480,
  pagePadH: 48,
  pagePadV: 28,
  columnGap: 48,
  pickerWidth: 200,
  dialogSm: 320,
  dialogMd: 360,
};

// --- UI surface colors (dark to light) ---
var SURFACE = {
  page: "#000000",
  inputDeep: "#0e0e1a",
  uploadBg: "#0f0f1a",
  panelDeep: "#10101a",
  uploadBtn: "#111119",
  panel: "#1a1a30",
  canvasBorder: "#222",
  input: "#28283e",
  pipeSep: "#2a2a3e",
  divider: "#2a2a40",
  uploadBorder: "#343447",
  panelBorder: "#3a3a50",
  border: "#444",
  muted: "#555",
  dimmed: "#666",
  secondary: "#777",
  tertiary: "#888",
  subtle: "#999",
  inactive: "#aaa",
  label: "#bbb",
  text: "#ccc",
  body: "#e0e0e0",
  white: "#fff",
};

// --- Semantic colors ---
var CLR = {
  primary: "#6366f1",
  primaryLight: "#a5b4fc",
  danger: "#f87171",
  dangerBorder: "#f8717133",
  error: "#ef4444",
  errorLight: "#fca5a5",
  errorBg: "#3a1a1a",
  errorBorder: "#7f1d1d",
  activeOverlay: "rgba(165,180,252,0.25)",
  activeOverlay2: "rgba(165,180,252,0.2)",
  dragTarget: "rgba(99,102,241,0.10)",
  activeSlide: "rgba(34,197,94,0.15)",
  removeBadgeBg: "rgba(100,100,100,0.7)",
  modalOverlay: "rgba(0,0,0,0.5)",
  shadow: "0 8px 24px rgba(0,0,0,0.6)",
  shadowLg: "0 8px 32px rgba(0,0,0,0.6)",
};

// --- Style helpers ---
// Compose common inline style objects from tokens.

function panelBtn(overrides) {
  var base = {
    padding: SPACE[3] + "px " + SPACE[6] + "px",
    borderRadius: RADIUS.md,
    border: "1px solid " + SURFACE.border,
    background: SURFACE.input,
    color: SURFACE.text,
    cursor: "pointer",
    fontSize: 11,
    fontWeight: 700,
  };
  return overrides ? Object.assign({}, base, overrides) : base;
}

function toggleBtn(isOn, overrides) {
  var base = {
    minWidth: SIZE.toggleMd,
    padding: "3px " + SPACE[6] + "px",
    borderRadius: RADIUS.pill,
    border: "none",
    background: isOn ? GREEN : SURFACE.muted,
    color: SURFACE.white,
    cursor: "pointer",
    fontSize: 11,
    fontWeight: 600,
  };
  return overrides ? Object.assign({}, base, overrides) : base;
}

function uploadFrameStyle(overrides) {
  var base = {
    height: SIZE.uploadFrame,
    background: SURFACE.uploadBg,
    border: "1px solid " + SURFACE.uploadBorder,
    borderRadius: RADIUS.lg,
    padding: SPACE[2] + "px " + SPACE[4] + "px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    boxSizing: "border-box",
    overflow: "hidden",
  };
  return overrides ? Object.assign({}, base, overrides) : base;
}

function uploadBtnStyle(hasFile) {
  return {
    width: "100%",
    height: SIZE.uploadBtn,
    borderRadius: 5,
    border: "1px solid " + (hasFile ? GREEN : SURFACE.border),
    background: SURFACE.uploadBtn,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    gap: SPACE[7],
  };
}

function dividerStyle() {
  return { borderTop: "1px solid " + SURFACE.divider, marginTop: SPACE[4], marginBottom: SPACE[4] };
}

function dialogOverlay() {
  return {
    position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
    background: CLR.modalOverlay,
    display: "flex", alignItems: "center", justifyContent: "center",
    zIndex: Z.modal,
  };
}

function dialogBox(maxWidth) {
  return {
    background: SURFACE.panel,
    border: "1px solid " + SURFACE.border,
    borderRadius: RADIUS.xl,
    padding: SPACE[8] + "px",
    maxWidth: maxWidth || SIZE.dialogSm,
    boxShadow: CLR.shadowLg,
  };
}

function dialogBtn(isPrimary) {
  return {
    padding: SPACE[3] + "px " + SPACE[7] + "px",
    borderRadius: RADIUS.md,
    border: isPrimary ? "none" : "1px solid " + SURFACE.border,
    background: isPrimary ? CLR.primary : SURFACE.input,
    color: isPrimary ? SURFACE.white : SURFACE.subtle,
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 600,
  };
}