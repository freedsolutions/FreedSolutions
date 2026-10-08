/* intake_ui_rows.js — the page side of the R124 batch's UI rows, for an already-logged-in Backoffice tab.
 *
 * WHAT THIS IS
 *   gridBatch (dutchie-bi-looker, backoffice_grid_write.js) sends every grid row itself and HANDS OFF the rest.
 *   This file runs the handed-off rows, one per call, after a FULL navigation to the item (the SPA hop between
 *   item forms carries the previous Strain into the next Save: platform KB "Load each item form by a FULL
 *   navigation"). `intake_ui_run.py emit` wraps one plan row into a neo `run` script that loads this file and
 *   calls the matching function; `intake_ui_run.py record` writes the result to the progress JSONL and keyMap.
 *
 *   uiRowsHarvest()                          keep the page's own record-read envelope (session storage, this tab)
 *   uiRowsCopy({ name, dryRun })             Actions > Copy > `Confirm copy product`, `Copy online details` CHECKED
 *   uiRowsContent({ productId, title, description, dryRun })   Online details tab, native setter, ONE guarded Save
 *   uiRowsUnretire({ productId, dryRun })    the UI fallback for a `ui_unretire` row (Actions > Unretire)
 *   uiRowsMintStrain({ name, type, dryRun }) `update-strain` with StrainId 0, guarded on the live Strains read
 *
 * WHAT IT WILL NOT DO
 *   It never builds an `update-product` body: a form Save posts the form's own body, and a guard installed on the
 *   page's fetch and XHR inspects that body BEFORE it leaves and BLOCKS it when a key the row does not touch
 *   differs from a fresh `get-product-details-v2` read (StrainId, Flavor, BrandId, ProductCategoryId, Name,
 *   Price, VendorId - KB "Load each item form by a FULL navigation"). It never unchecks `Copy online details`
 *   (ruled 2026-10-08: CHECKED on every copy). It never types a credential. dryRun is TRUE by default.
 *   Every envelope value comes from a request the page made (`uiRowsHarvest`), never from a guess.
 */
(function (root) {
  'use strict';

  var CTX_KEYS = ['SessionId', 'LspId', 'LocId', 'OrgId', 'UserId'];
  var STORE_KEY = '__intakeUiRowsCtx';
  var GUARD_KEYS = ['StrainId', 'Flavor', 'BrandId', 'ProductCategoryId', 'Name', 'Price', 'VendorId'];
  var STRAIN_TYPES = ['None', 'Hybrid', 'Indica', 'Indica-Hybrid', 'Sativa', 'Sativa-Hybrid', 'CBD', 'THC',
    '1 to 1', '2 to 1', '5 to 1', '10 to 1', '20 to 1', '50 to 1'];   // KB "Minting a Strain record"
  var S = root.__intakeUiRows = root.__intakeUiRows || { rec: [], installed: false, saveGuard: null };

  function refuse(reason, detail) { return { ok: false, refused: true, reason: reason, detail: detail }; }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function redact(s) { return String(s || '').replace(/"SessionId":"[^"]+"/, '"SessionId":"…"'); }

  // ---- the recorder and the form-Save guard (fetch AND XHR; a bound fetch, KB "A page-side fetch wrapper") ----
  function guardVerdict(url, body) {
    var g = S.saveGuard;
    if (!g || String(url).indexOf('/update-product') < 0 || String(url).indexOf('update-products-multiple') >= 0) return null;
    var b; try { b = JSON.parse(body); } catch (e) { return 'the update-product body is not JSON'; }
    if (Number(b.ProductId) !== Number(g.productId)) return 'the Save is for ' + b.ProductId + ', not ' + g.productId;
    for (var i = 0; i < GUARD_KEYS.length; i++) {
      var k = GUARD_KEYS[i];
      if (!(k in b)) return 'the body has no `' + k + '` (shape unproven: nothing sent)';
      if (JSON.stringify(b[k]) !== JSON.stringify(g.live[k])) {
        return '`' + k + '` would post ' + JSON.stringify(b[k]) + ' over the live ' + JSON.stringify(g.live[k]);
      }
    }
    var want = g.want || {};
    for (var w in want) {
      if (!(w in b)) return 'the body has no `' + w + '`';
      if (b[w] !== want[w]) return '`' + w + '` posts ' + JSON.stringify(String(b[w]).slice(0, 60)) + ', not the target';
    }
    return null;
  }

  if (!S.installed) {
    var bf = root.fetch.bind(root);
    root.fetch = function (input, init) {
      var url = typeof input === 'string' ? input : (input && input.url);
      var body = init && typeof init.body === 'string' ? init.body : null;
      var e = { t: Date.now(), url: String(url), body: body };
      if (String(url).indexOf('/api/') >= 0) S.rec.push(e);
      var why = body ? guardVerdict(url, body) : null;
      if (why) { e.blocked = why; S.saveGuard.blocked = why; return Promise.reject(new Error('SAVE_GUARD: ' + why)); }
      return bf(input, init).then(function (r) {
        e.status = r.status;
        r.clone().text().then(function (tx) { e.resp = tx.length > 20000 ? tx.slice(0, 20000) : tx; }, function () {});
        return r;
      });
    };
    var xo = root.XMLHttpRequest.prototype.open, xs = root.XMLHttpRequest.prototype.send;
    root.XMLHttpRequest.prototype.open = function (m, u) { this.__u = u; return xo.apply(this, arguments); };
    root.XMLHttpRequest.prototype.send = function (b) {
      var x = this, e = { t: Date.now(), url: String(x.__u), body: typeof b === 'string' ? b : null, xhr: true };
      if (String(x.__u).indexOf('/api/') >= 0) S.rec.push(e);
      var why = e.body ? guardVerdict(x.__u, e.body) : null;
      if (why) {
        e.blocked = why; S.saveGuard.blocked = why;
        setTimeout(function () { x.dispatchEvent(new Event('error')); x.dispatchEvent(new Event('loadend')); }, 0);
        return undefined;
      }
      x.addEventListener('loadend', function () {
        e.status = x.status;
        try { e.resp = String(x.responseText || '').slice(0, 20000); } catch (err) { /* binary */ }
      });
      return xs.apply(this, arguments);
    };
    S.installed = true;
  }

  // ---- the envelope: harvested from the page's own record read ----------------------------------------------
  function ctx() {
    var c; try { c = JSON.parse(root.sessionStorage.getItem(STORE_KEY) || 'null'); } catch (e) { c = null; }
    if (!c || !c.url || !c.body) return null;
    for (var i = 0; i < CTX_KEYS.length; i++) if (c.body[CTX_KEYS[i]] == null) return null;
    return c;
  }

  function uiRowsHarvest() {
    var e = S.rec.filter(function (x) { return x.url.indexOf('get-product-details-v2') >= 0 && x.body; }).pop();
    if (!e) {
      return refuse('MISSING_READ_CAPTURE', 'no `get-product-details-v2` request observed since this file was ' +
        'loaded. Load it BEFORE the page reads (or hop away and back once, read-only) and call again.');
    }
    var b = JSON.parse(e.body);
    root.sessionStorage.setItem(STORE_KEY, JSON.stringify({ url: e.url, body: b }));
    return { ok: true, detail: 'envelope kept for this tab (' + CTX_KEYS.join(', ') + ')' };
  }

  function post(path, body) {
    return root.fetch(root.location.origin + path, { method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(function (r) { return r.json().then(function (j) { return { status: r.status, json: j }; }); });
  }

  function details(productId) {
    var c = ctx();
    if (!c) return Promise.resolve({ error: refuse('MISSING_CONTEXT', 'call uiRowsHarvest() on an item page first') });
    var b = {}; Object.keys(c.body).forEach(function (k) { b[k] = c.body[k]; });
    b.ProductId = Number(productId);
    return root.fetch(c.url, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(b) }).then(function (r) {
      if (r.status === 401) return { error: refuse('SESSION_LOST', 'the record read returned 401') };
      return r.json().then(function (j) {
        if (!j || !j.Data || Number(j.Data.ProductId) !== Number(productId)) {
          return { error: refuse('READ_UNVERIFIED', 'the record read for ' + productId + ' returned no such record') };
        }
        return { rec: j.Data };
      });
    });
  }

  function byText(sel, txt, scope) {
    return [].slice.call((scope || root.document).querySelectorAll(sel)).filter(function (n) {
      return n.innerText && n.innerText.trim() === txt;
    })[0] || null;
  }

  function dialog(re) {
    return [].slice.call(root.document.querySelectorAll('[role=dialog]')).filter(function (d) {
      return re.test(d.innerText || '');
    })[0] || null;
  }

  function setNative(el, value) {
    var proto = el.tagName === 'TEXTAREA' ? root.HTMLTextAreaElement.prototype : root.HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function pageProductId() {
    var m = /\/products\/catalog\/(\d+)/.exec(root.location.pathname);
    return m ? Number(m[1]) : null;
  }

  function openAction(label) {
    var a = byText('button', 'Actions');
    if (!a) return Promise.resolve(refuse('UI_NOT_FOUND', 'no Actions button: is this an item page?'));
    a.click();
    return sleep(900).then(function () {
      var mi = byText('[role=menuitem]', label);
      if (!mi) return refuse('UI_NOT_FOUND', 'the Actions menu has no `' + label + '`');
      mi.click();
      return sleep(1300).then(function () { return null; });
    });
  }

  // ---- COPY ------------------------------------------------------------------------------------------------
  function uiRowsCopy(o) {
    o = o || {};
    var dry = o.dryRun !== false, name = String(o.name || '');
    var src = pageProductId();
    if (!src) return Promise.resolve(refuse('UI_NOT_FOUND', 'not on an item page (/products/catalog/<id>)'));
    if (o.sourceId && Number(o.sourceId) !== src) {
      return Promise.resolve(refuse('WRONG_SOURCE', 'the page is item ' + src + ', the row copies ' + o.sourceId));
    }
    if (!name.trim() || /\(Copy\)\s*$/.test(name)) {
      return Promise.resolve(refuse('NAME_REFUSED', 'the planned name is blank or ends in "(Copy)": never save it'));
    }
    var mark = S.rec.length;
    return openAction('Copy').then(function (stop) {
      if (stop) return stop;
      var d = dialog(/Confirm copy product/);
      if (!d) return refuse('UI_NOT_FOUND', 'no `Confirm copy product` dialog');
      var nameEl = d.querySelector('[id="input-input_Product name:"]');
      var box = [].slice.call(d.querySelectorAll('input[type=checkbox]')).filter(function (c) {
        var l = c.closest('label'); return l && /Copy online details/.test(l.innerText);
      })[0];
      var cancel = byText('button', 'Cancel', d), confirm = byText('button', 'Confirm', d);
      if (!nameEl || !box || !cancel || !confirm) {
        if (cancel) cancel.click();
        return refuse('UI_NOT_FOUND', 'the dialog lacks the name field, the `Copy online details` box or its buttons');
      }
      if (!box.checked) {
        cancel.click();
        return refuse('COPY_ONLINE_DETAILS_UNCHECKED', 'the box reads UNCHECKED; the ruling is CHECKED on every ' +
          'copy and this file never toggles it. Cancelled; nothing created.');
      }
      setNative(nameEl, name);
      return sleep(300).then(function () {
        if (nameEl.value !== name) {
          cancel.click();
          return refuse('NAME_NOT_SET', 'the name field reads ' + JSON.stringify(nameEl.value) + '. Cancelled.');
        }
        if (dry) {
          cancel.click();
          return { ok: true, dryRun: true, sourceId: src, name: name, copyOnlineDetails: true,
            detail: 'dialog verified (name set, box CHECKED) and CANCELLED - nothing created' };
        }
        confirm.click();
        var t0 = Date.now();
        return (function waitNew() {
          var id = pageProductId();
          if (id && id !== src) return sleep(1500).then(function () { return id; });
          if (Date.now() - t0 > 20000) return null;
          return sleep(500).then(waitNew);
        })().then(function (newId) {
          var calls = S.rec.slice(mark).map(function (e) {
            return { url: e.url.replace(root.location.origin, ''), status: e.status, body: redact(e.body).slice(0, 300),
              resp: String(e.resp || '').slice(0, 300) };
          });
          S.lastCopy = { at: new Date().toISOString(), sourceId: src, name: name, newId: newId, calls: calls };
          if (!newId) {
            return { ok: false, reason: 'COPY_DONE_UNKNOWN', sourceId: src, name: name, calls: calls.slice(0, 8),
              detail: 'Confirm was clicked but the page never moved to a new item: done-UNKNOWN. Find the item ' +
                'by its exact name on a live read before any retry; never copy again blind.' };
          }
          return { ok: true, status: 'WROTE', sourceId: src, name: name, newProductId: newId,
            calls: calls.slice(0, 8), detail: 'created; the new ProductId is the page URL (P1 records the request)' };
        });
      });
    });
  }

  // ---- CONTENT ---------------------------------------------------------------------------------------------
  function uiRowsContent(o) {
    o = o || {};
    var dry = o.dryRun !== false, pid = Number(o.productId);
    if (pageProductId() !== pid) return Promise.resolve(refuse('WRONG_ITEM', 'the page is not item ' + pid));
    var want = {};
    if (o.title !== undefined) want.OnlineTitle = String(o.title);
    if (o.description !== undefined) want.OnlineDescription = String(o.description);
    if (!Object.keys(want).length) return Promise.resolve(refuse('NOTHING_TO_WRITE', 'pass title and/or description'));
    if (Object.keys(want).some(function (k) { return !want[k].trim(); })) {
      return Promise.resolve(refuse('CONTENT_BLANK', 'a blank target is a clear, which is not the ruled path'));
    }
    return details(pid).then(function (d) {
      if (d.error) return d.error;
      var live = d.rec;
      if (Object.keys(want).every(function (k) { return live[k] === want[k]; })) {
        return { ok: true, status: 'AT_TARGET', productId: pid, wrote: 0 };
      }
      var tab = byText('[role=tab]', 'Online details');
      if (!tab) return refuse('UI_NOT_FOUND', 'no Online details tab');
      tab.click();
      return sleep(1200).then(function () {
        var tEl = root.document.querySelector('[id="input-input_Online title:"]');
        var dEl = root.document.querySelector('[id="input-input_Online description:"]');
        if ((want.OnlineTitle !== undefined && !tEl) || (want.OnlineDescription !== undefined && !dEl)) {
          return refuse('UI_NOT_FOUND', 'the Online title / description field is not on the tab');
        }
        if (want.OnlineTitle !== undefined) setNative(tEl, want.OnlineTitle);
        if (want.OnlineDescription !== undefined) setNative(dEl, want.OnlineDescription);
        return sleep(400).then(function () {
          if ((tEl && want.OnlineTitle !== undefined && tEl.value !== want.OnlineTitle) ||
              (dEl && want.OnlineDescription !== undefined && dEl.value !== want.OnlineDescription)) {
            return refuse('VALUE_NOT_SET', 'a field does not read its target after the native setter');
          }
          if (dry) {
            return { ok: true, dryRun: true, productId: pid, fields: Object.keys(want),
              detail: 'fields staged, NOT saved. Reload the page to discard them.' };
          }
          var save = byText('button', 'Save');
          if (!save) return refuse('UI_NOT_FOUND', 'no Save button');
          var mark = S.rec.length;
          S.saveGuard = { productId: pid, live: live, want: want, blocked: null };
          save.click();
          var t0 = Date.now();
          return (function waitSave() {
            var hit = S.rec.slice(mark).filter(function (e) {
              return e.url.indexOf('/update-product') >= 0 && e.url.indexOf('multiple') < 0;
            })[0];
            if (S.saveGuard.blocked) return 'blocked';
            if (hit && hit.status) return hit;
            if (Date.now() - t0 > 20000) return null;
            return sleep(400).then(waitSave);
          })().then(function (hit) {
            var blocked = S.saveGuard.blocked;
            S.saveGuard = null;
            if (hit === 'blocked') {
              return refuse('SAVE_GUARD', 'the form Save was BLOCKED before it left: ' + blocked + '. Nothing written; ' +
                'reload the item by a full navigation.');
            }
            if (!hit) return { ok: false, reason: 'SAVE_DONE_UNKNOWN', productId: pid, detail: 'no update-product ' +
              'response in 20 s: done-UNKNOWN. The certify (or a record read) decides; never Save again blind.' };
            var ok = false; try { ok = JSON.parse(hit.resp).Result === true; } catch (e) { ok = false; }
            if (hit.status === 401) return refuse('SESSION_LOST', 'the Save returned 401');
            if (!ok) return refuse('WRITE_NOT_OK', 'update-product HTTP ' + hit.status + ' ' + String(hit.resp).slice(0, 120));
            return { ok: true, status: 'WROTE', productId: pid, fields: Object.keys(want),
              declares: 'the form-Save signature (hidden nulls -> form defaults, LocationRecPrice null) - KB',
              detail: 'saved; NOT read back (R124: the certify proves it)' };
          });
        });
      });
    });
  }

  // ---- UNRETIRE (the UI fallback) ----------------------------------------------------------------------------
  function uiRowsUnretire(o) {
    o = o || {};
    var dry = o.dryRun !== false, pid = Number(o.productId);
    if (pageProductId() !== pid) return Promise.resolve(refuse('WRONG_ITEM', 'the page is not item ' + pid));
    return details(pid).then(function (d) {
      if (d.error) return d.error;
      if (d.rec.IsRetired === false) return { ok: true, status: 'AT_TARGET', productId: pid, wrote: 0 };
      if (d.rec.IsRetired !== true) return refuse('GUARD_MISMATCH', pid + ' IsRetired reads ' + JSON.stringify(d.rec.IsRetired));
      return openAction('Unretire').then(function (stop) {
        if (stop) return stop;
        var dl = dialog(/Confirm unretire/);
        if (!dl) return refuse('UI_NOT_FOUND', 'no `Confirm unretire` dialog');
        if (dry) { byText('button', 'Cancel', dl).click(); return { ok: true, dryRun: true, productId: pid }; }
        var mark = S.rec.length;
        byText('button', 'Confirm', dl).click();
        return sleep(4000).then(function () {
          var hit = S.rec.slice(mark).filter(function (e) { return e.url.indexOf('unretire-product') >= 0; })[0];
          var ok = false; try { ok = JSON.parse(hit.resp).Result === true; } catch (e) { ok = false; }
          if (!hit) return { ok: false, reason: 'UNRETIRE_DONE_UNKNOWN', productId: pid };
          return ok ? { ok: true, status: 'WROTE', productId: pid } : refuse('WRITE_NOT_OK', 'unretire-product ' + hit.status);
        });
      });
    });
  }

  // ---- MINT_STRAIN -----------------------------------------------------------------------------------------
  function uiRowsMintStrain(o) {
    o = o || {};
    var dry = o.dryRun !== false, name = String(o.name || '').trim(), type = String(o.type || '').trim();
    if (!name) return Promise.resolve(refuse('NAME_REFUSED', 'a blank strain name'));
    if (STRAIN_TYPES.indexOf(type) < 0) {
      return Promise.resolve(refuse('STRAIN_TYPE_UNKNOWN', JSON.stringify(type) + ' is not on the Strains form Type list'));
    }
    var c = ctx();
    if (!c) return Promise.resolve(refuse('MISSING_CONTEXT', 'call uiRowsHarvest() on an item page first'));
    var env = {}; CTX_KEYS.forEach(function (k) { env[k] = c.body[k]; });
    return post('/api/strain/get-strains', env).then(function (r) {
      var list = (r.json && r.json.Data) || [];
      if (!Array.isArray(list)) list = list.strains || [];
      if (!list.length) return refuse('READ_UNVERIFIED', 'the live Strains read returned no records');
      var clash = list.filter(function (s) { return String(s.StrainName).trim().toLowerCase() === name.toLowerCase(); });
      if (clash.length === 1 && clash[0].StrainType === type) {
        return { ok: true, status: 'AT_TARGET', strainId: clash[0].StrainId, wrote: 0 };
      }
      if (clash.length) return refuse('GUARD_MISMATCH', 'a live record already carries ' + JSON.stringify(name) +
        ' (' + clash.map(function (s) { return s.StrainId + ' ' + s.StrainType; }).join('; ') + ')');
      var body = {};
      Object.keys(env).forEach(function (k) { body[k] = env[k]; });
      body.StrainId = 0; body.StrainName = name; body.StrainDescription = name; body.Abbreviation = name;
      body.StrainType = type; body.ExternalId = '';
      if (dry) return { ok: true, dryRun: true, name: name, type: type, liveCount: list.length };
      return post('/api/strain/update-strain', body).then(function (w) {
        if (w.status === 401) return refuse('SESSION_LOST', 'update-strain returned 401');
        if (!w.json || w.json.Result !== true) return refuse('WRITE_NOT_OK', 'update-strain ' + w.status);
        return { ok: true, status: 'WROTE', name: name, type: type, strainId: w.json.Data };
      });
    });
  }

  root.uiRowsHarvest = uiRowsHarvest;
  root.uiRowsCopy = uiRowsCopy;
  root.uiRowsContent = uiRowsContent;
  root.uiRowsUnretire = uiRowsUnretire;
  root.uiRowsMintStrain = uiRowsMintStrain;
})(typeof window !== 'undefined' ? window : globalThis);
