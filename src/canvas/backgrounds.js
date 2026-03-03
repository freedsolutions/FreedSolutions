// ---------------------------------------
// Background renderers
// ---------------------------------------

function drawSolidBg(ctx, color) {
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, W, H);
}

function drawGeoBg(ctx, baseColor, lineColor) {
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
  var spheres = [
    { x: -30, y: 220, r: 170, a: 0.10 },
    { x: -10, y: 800, r: 150, a: 0.08 },
    { x: 740, y: 130, r: 110, a: 0.06 },
    { x: 700, y: 830, r: 130, a: 0.07 },
  ];
  for (var si = 0; si < spheres.length; si++) {
    var s = spheres[si];
    ctx.fillStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + s.a + ")";
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (s.a * 0.6) + ")";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.strokeStyle = "rgba(" + lcR + "," + lcG + "," + lcB + ",0.06)";
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

function renderBg(ctx, bgType, solidColor, customImg, geoLines, geoEnabled) {
  if (bgType === "custom" && customImg) {
    drawCustomBg(ctx, customImg);
  } else {
    drawSolidBg(ctx, solidColor);
    if (geoEnabled) {
      drawGeoBg(ctx, null, geoLines);
    }
  }
}