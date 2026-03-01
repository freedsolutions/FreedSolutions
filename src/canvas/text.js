// ---------------------------------------
// Text helpers
// ---------------------------------------

function wrapText(ctx, text, maxWidth, fontSize, fontWeight, fontFamily, fontItalic) {
  fontWeight = fontWeight || "bold";
  ctx.font = composeFont(fontFamily || DEFAULT_FONT, fontSize, fontWeight, !!fontItalic);
  var words = text.split(" ");
  var lines = [];
  var line = "";
  for (var i = 0; i < words.length; i++) {
    var test = line ? line + " " + words[i] : words[i];
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line);
      line = words[i];
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function extractAccentMarkers(text) {
  var markers = [];
  var re = /\*\*(.+?)\*\*/g;
  var m;
  var offset = 0;
  while ((m = re.exec(text)) !== null) {
    var cleanStart = m.index - offset;
    offset += 4;
    markers.push({ start: cleanStart, end: cleanStart + m[1].length });
  }
  var cleanText = text.replace(/\*\*(.+?)\*\*/g, "$1");
  return { cleanText: cleanText, markers: markers };
}

function renderLineWithAccents(ctx, line, x, y, fontSize, baseWeight, baseColor, accentColor, markers, lineOffset, fontFamily, fontItalic) {
  var family = fontFamily || DEFAULT_FONT;
  if (!markers || markers.length === 0) {
    ctx.font = composeFont(family, fontSize, baseWeight, !!fontItalic);
    ctx.fillStyle = baseColor;
    ctx.fillText(line, x, y);
    return;
  }
  var lineEnd = lineOffset + line.length;
  var hits = [];
  for (var mi = 0; mi < markers.length; mi++) {
    var mk = markers[mi];
    if (mk.end <= lineOffset || mk.start >= lineEnd) continue;
    var s = Math.max(mk.start, lineOffset) - lineOffset;
    var e = Math.min(mk.end, lineEnd) - lineOffset;
    hits.push({ start: s, end: e });
  }
  if (hits.length === 0) {
    ctx.font = composeFont(family, fontSize, baseWeight, !!fontItalic);
    ctx.fillStyle = baseColor;
    ctx.fillText(line, x, y);
    return;
  }
  hits.sort(function(a, b) { return a.start - b.start; });
  var segments = [];
  var pos = 0;
  for (var hi = 0; hi < hits.length; hi++) {
    if (hits[hi].start > pos) {
      segments.push({ text: line.substring(pos, hits[hi].start), isAccent: false });
    }
    segments.push({ text: line.substring(hits[hi].start, hits[hi].end), isAccent: true });
    pos = hits[hi].end;
  }
  if (pos < line.length) segments.push({ text: line.substring(pos), isAccent: false });
  var xPos = x;
  for (var si = 0; si < segments.length; si++) {
    var seg = segments[si];
    if (seg.isAccent) {
      ctx.font = composeFont(family, fontSize, "900", !!fontItalic);
      ctx.fillStyle = accentColor;
    } else {
      ctx.font = composeFont(family, fontSize, baseWeight, !!fontItalic);
      ctx.fillStyle = baseColor;
    }
    ctx.fillText(seg.text, xPos, y);
    xPos += ctx.measureText(seg.text).width;
  }
}