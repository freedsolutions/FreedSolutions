// ---------------------------------------
// hexToRgba
// ---------------------------------------

function hexToRgba(hex, opacity) {
  if (!hex || typeof hex !== "string") return "rgba(255,255,255," + ((opacity || 0) / 100) + ")";
  if (hex.indexOf("rgba") === 0 || hex.indexOf("rgb") === 0) return hex;
  if (hex.charAt(0) !== "#" || hex.length < 7) return hex;
  var r = parseInt(hex.slice(1, 3), 16);
  var g = parseInt(hex.slice(3, 5), 16);
  var b = parseInt(hex.slice(5, 7), 16);
  if (isNaN(r) || isNaN(g) || isNaN(b)) return "rgba(255,255,255," + ((opacity || 0) / 100) + ")";
  return "rgba(" + r + "," + g + "," + b + "," + ((opacity != null ? opacity : 100) / 100) + ")";
}