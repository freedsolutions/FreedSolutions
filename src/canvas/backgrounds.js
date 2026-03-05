// ---------------------------------------
// Background renderers
// ---------------------------------------

function drawSolidBg(ctx, color) {
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, W, H);
}

// --- Shape-specific drawing functions ---
// All share signature: (ctx, lcR, lcG, lcB, opScale)

function drawGeoLines(ctx, lcR, lcG, lcB, opScale) {
  var spheres = [
    { x: -30, y: 220, r: 170, a: 0.10 },
    { x: -10, y: 800, r: 150, a: 0.08 },
    { x: 740, y: 130, r: 110, a: 0.06 },
    { x: 700, y: 830, r: 130, a: 0.07 },
  ];
  for (var si = 0; si < spheres.length; si++) {
    var s = spheres[si];
    ctx.fillStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (s.a * opScale) + ")";
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (s.a * 0.6 * opScale) + ")";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.strokeStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (0.06 * opScale) + ")";
  ctx.lineWidth = 0.7;
  var lines = [
    [0, 50, 800, 380], [50, 0, 750, 550], [150, 0, 800, 480],
    [300, 0, 800, 350], [450, 0, 800, 200], [550, 0, 800, 120],
    [0, 150, 650, 1000], [0, 350, 500, 1000], [0, 500, 400, 1000],
    [0, 650, 350, 1000], [100, 0, 550, 1000], [250, 0, 700, 1000],
    [400, 0, 800, 800], [0, 100, 800, 650], [0, 750, 250, 1000],
    [600, 0, 800, 300], [0, 200, 300, 1000], [500, 0, 150, 700],
    [700, 0, 350, 1000], [0, 400, 700, 1000], [200, 0, 0, 400],
    [800, 200, 400, 1000], [800, 400, 500, 1000], [800, 50, 200, 700],
    [650, 0, 0, 600], [0, 600, 600, 1000], [350, 0, 800, 650],
    [800, 600, 550, 1000], [0, 900, 150, 1000], [750, 0, 800, 100],
  ];
  for (var li = 0; li < lines.length; li++) {
    ctx.beginPath();
    ctx.moveTo(lines[li][0], lines[li][1]);
    ctx.lineTo(lines[li][2], lines[li][3]);
    ctx.stroke();
  }
}

function drawGeoBokeh(ctx, lcR, lcG, lcB, opScale) {
  // Hand-placed translucent circles — organic scatter, varying size and opacity
  var orbs = [
    { x: 90,  y: 80,   r: 65,  a: 0.06 },
    { x: 680, y: 60,   r: 45,  a: 0.05 },
    { x: 350, y: 180,  r: 95,  a: 0.04 },
    { x: 750, y: 280,  r: 80,  a: 0.06 },
    { x: 60,  y: 420,  r: 110, a: 0.05 },
    { x: 520, y: 370,  r: 35,  a: 0.08 },
    { x: 200, y: 550,  r: 70,  a: 0.05 },
    { x: 700, y: 520,  r: 55,  a: 0.07 },
    { x: 420, y: 620,  r: 120, a: 0.04 },
    { x: 130, y: 740,  r: 50,  a: 0.06 },
    { x: 600, y: 760,  r: 85,  a: 0.05 },
    { x: 330, y: 870,  r: 40,  a: 0.07 },
    { x: 760, y: 900,  r: 70,  a: 0.05 },
    { x: 50,  y: 940,  r: 90,  a: 0.04 },
    { x: 480, y: 140,  r: 30,  a: 0.09 },
    { x: 260, y: 320,  r: 50,  a: 0.06 },
  ];
  for (var i = 0; i < orbs.length; i++) {
    var o = orbs[i];
    // Soft filled circle
    ctx.fillStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (o.a * opScale) + ")";
    ctx.beginPath();
    ctx.arc(o.x, o.y, o.r, 0, Math.PI * 2);
    ctx.fill();
    // Subtle rim
    ctx.strokeStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (o.a * 0.5 * opScale) + ")";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(o.x, o.y, o.r, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function drawGeoWaves(ctx, lcR, lcG, lcB, opScale) {
  // Flowing curves that sweep across the canvas — topographic/organic feel
  var curves = [
    { y: 80,   amp: 30,  freq: 1.2, phase: 0,    a: 0.10 },
    { y: 200,  amp: 45,  freq: 0.8, phase: 1.5,  a: 0.08 },
    { y: 340,  amp: 25,  freq: 1.5, phase: 0.8,  a: 0.11 },
    { y: 460,  amp: 55,  freq: 0.6, phase: 2.2,  a: 0.07 },
    { y: 580,  amp: 35,  freq: 1.1, phase: 0.4,  a: 0.10 },
    { y: 720,  amp: 40,  freq: 0.9, phase: 3.0,  a: 0.08 },
    { y: 850,  amp: 50,  freq: 0.7, phase: 1.8,  a: 0.09 },
    { y: 960,  amp: 20,  freq: 1.4, phase: 0.6,  a: 0.07 },
  ];
  ctx.lineWidth = 1.2;
  for (var i = 0; i < curves.length; i++) {
    var c = curves[i];
    // Every other pair: fill between this curve and the next curve
    if (i % 2 === 0 && i + 1 < curves.length) {
      var n = curves[i + 1];
      ctx.fillStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (c.a * 0.35 * opScale) + ")";
      ctx.beginPath();
      // Trace top wave left-to-right
      ctx.moveTo(-10, c.y + Math.sin(c.phase) * c.amp);
      for (var fx = 0; fx <= W + 10; fx += 4) {
        var ft = (fx / W) * Math.PI * 2 * c.freq + c.phase;
        ctx.lineTo(fx, c.y + Math.sin(ft) * c.amp);
      }
      // Trace bottom wave right-to-left
      for (var bx = W + 10; bx >= -10; bx -= 4) {
        var bt = (bx / W) * Math.PI * 2 * n.freq + n.phase;
        ctx.lineTo(bx, n.y + Math.sin(bt) * n.amp);
      }
      ctx.closePath();
      ctx.fill();
    }
    // Stroke the wave line
    ctx.strokeStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (c.a * opScale) + ")";
    ctx.beginPath();
    ctx.moveTo(-10, c.y + Math.sin(c.phase) * c.amp);
    for (var x = 0; x <= W + 10; x += 4) {
      var t = (x / W) * Math.PI * 2 * c.freq + c.phase;
      ctx.lineTo(x, c.y + Math.sin(t) * c.amp);
    }
    ctx.stroke();
  }
}

function drawGeoStripes(ctx, lcR, lcG, lcB, opScale) {
  ctx.strokeStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (0.07 * opScale) + ")";
  ctx.lineWidth = 1.0;
  for (var d = -1000; d < 1600; d += 50) {
    ctx.beginPath();
    ctx.moveTo(d, 0);
    ctx.lineTo(d - H, H);
    ctx.stroke();
  }
}

function drawGeoHex(ctx, lcR, lcG, lcB, opScale) {
  var side = 55;
  var colStep = side * 1.5;
  var rowStep = Math.sqrt(3) * side;
  ctx.strokeStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (0.09 * opScale) + ")";
  ctx.lineWidth = 1.0;
  ctx.beginPath();
  for (var col = -1; col * colStep < W + side * 2; col++) {
    for (var row = -1; row * rowStep < H + side * 2; row++) {
      var cx = col * colStep;
      var cy = row * rowStep + (col % 2 !== 0 ? rowStep / 2 : 0);
      for (var a = 0; a < 6; a++) {
        var angle = Math.PI / 3 * a;
        var px = cx + side * Math.cos(angle);
        var py = cy + side * Math.sin(angle);
        if (a === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
    }
  }
  ctx.stroke();
}

function drawGeoDots(ctx, lcR, lcG, lcB, opScale) {
  var radius = 22;
  var spacingX = 90;
  var spacingY = 85;
  ctx.fillStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (0.10 * opScale) + ")";
  ctx.beginPath();
  for (var row = 0; row * spacingY < H + radius * 2; row++) {
    var offsetX = (row % 2 !== 0) ? spacingX / 2 : 0;
    for (var col = -1; col * spacingX < W + radius * 2; col++) {
      var cx = col * spacingX + offsetX;
      var cy = row * spacingY;
      ctx.moveTo(cx + radius, cy);
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    }
  }
  ctx.fill();
}

// --- Dispatcher ---

function drawGeoBg(ctx, baseColor, lineColor, geoOpacity, geoShape) {
  var opScale = (geoOpacity != null ? geoOpacity : 100) / 100;
  if (baseColor) {
    ctx.fillStyle = baseColor;
    ctx.fillRect(0, 0, W, H);
  }
  var lc = lineColor || "#a0a0af";
  var lcR = 160, lcG = 160, lcB = 175;
  if (lc.charAt(0) === "#" && lc.length >= 7) {
    var pr = parseInt(lc.slice(1,3), 16);
    var pg = parseInt(lc.slice(3,5), 16);
    var pb = parseInt(lc.slice(5,7), 16);
    if (!isNaN(pr)) lcR = pr;
    if (!isNaN(pg)) lcG = pg;
    if (!isNaN(pb)) lcB = pb;
  }
  var shape = geoShape || "lines";
  if (shape === "bokeh") drawGeoBokeh(ctx, lcR, lcG, lcB, opScale);
  else if (shape === "waves") drawGeoWaves(ctx, lcR, lcG, lcB, opScale);
  else if (shape === "stripes") drawGeoStripes(ctx, lcR, lcG, lcB, opScale);
  else if (shape === "hex") drawGeoHex(ctx, lcR, lcG, lcB, opScale);
  else if (shape === "dots") drawGeoDots(ctx, lcR, lcG, lcB, opScale);
  else drawGeoLines(ctx, lcR, lcG, lcB, opScale);
}

function drawCustomBg(ctx, img) {
  if (!img.width || !img.height) return;
  var imgRatio = img.width / img.height;
  var canvasRatio = W / H;
  var dw, dh;
  if (imgRatio > canvasRatio) {
    dh = H; dw = dh * imgRatio;
  } else {
    dw = W; dh = dw / imgRatio;
  }
  var dx = (W - dw) / 2;
  var dy = (H - dh) / 2;
  ctx.drawImage(img, dx, dy, dw, dh);
  ctx.fillStyle = "rgba(0,0,0,0.70)";
  ctx.fillRect(0, 0, W, H);
}

function renderBg(ctx, bgType, solidColor, customImg, geoLines, geoEnabled, geoOpacity, geoShape) {
  if (bgType === "custom" && customImg) {
    drawCustomBg(ctx, customImg);
  } else {
    drawSolidBg(ctx, solidColor);
    if (geoEnabled) {
      drawGeoBg(ctx, null, geoLines, geoOpacity, geoShape);
    }
  }
}