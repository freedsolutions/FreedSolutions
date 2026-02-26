// ---------------------------------------
// Screenshot renderer
// ---------------------------------------

function drawScreenshot(ctx, screenshot, x, y, w, h, scale) {
  if (!screenshot) {
    ctx.strokeStyle = "rgba(255,255,255,0.1)";
    ctx.lineWidth = 1;
    ctx.setLineDash([6, 6]);
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, 12);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "rgba(255,255,255,0.15)";
    ctx.font = '500 16px "Helvetica Neue", Helvetica, Arial, sans-serif';
    var phText = "Upload screenshot";
    var phW = ctx.measureText(phText).width;
    ctx.fillText(phText, x + (w - phW) / 2, y + h / 2 + 6);
    return;
  }
  var s = scale || 1;
  var imgRatio = screenshot.width / screenshot.height;
  var boxRatio = w / h;
  var dw, dh;
  if (imgRatio > boxRatio) {
    dw = w; dh = dw / imgRatio;
  } else {
    dh = h; dw = dh * imgRatio;
  }
  dw *= s;
  dh *= s;
  var dx = x + (w - dw) / 2;
  var dy = y + (h - dh) / 2;

  ctx.save();
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, 12);
  ctx.clip();
  ctx.drawImage(screenshot, dx, dy, dw, dh);
  ctx.restore();

  ctx.strokeStyle = "rgba(255,255,255,0.1)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, 12);
  ctx.stroke();
}