/* backoffice_grid_write.js — a guarded catalog write for an already-logged-in Backoffice tab.
 *
 * WHAT THIS IS
 *   The bulk-edit grid's own Save posts one flat body to `update-products-multiple`. Calling that
 *   endpoint directly costs one request per target value instead of ~8 browser calls per item, and
 *   it binds by RECORD id, which is what makes it safe where a name-bound CSV load is not.
 *   The platform KB section "Backoffice bulk-edit grid" (Path A' and its Traps) is the source; read
 *   it before using this. This file turns the traps that section documents into REFUSALS, because a
 *   recipe a session must remember is weaker than a tool that refuses the bad write. A real run on
 *   2026-09-18 read that section and still cleared a live field with an empty value box.
 *
 * HOW TO USE IT
 *   1. Sign in to Backoffice yourself and open the catalog grid. This file NEVER touches a login
 *      form, a cookie jar or a credential; if a password field is on screen, stop.
 *   2. Evaluate this file in that tab. It installs a request interceptor immediately.
 *   3. Let the page do its own reads (open the grid; for retired work, apply the Retired filter).
 *      `gridWriteCapture()` reports what it has observed and whether it can build a request.
 *   4. `await gridWrite({...})` — dryRun is TRUE by default and returns the plan without writing.
 *   5. Read `window.__gridWrite` for the full per-item before/after; the in-page JS channel
 *      truncates near 1 KB, so the return value is a summary by design.
 *
 * WHAT IT WILL NOT DO
 *   It never invents an endpoint, a payload key or an id. Every value in the envelope is harvested
 *   from a request the PAGE made, every read is a replay of a request the page made, and anything
 *   it cannot prove is a named hard stop rather than a warning. If a guard is in your way, the
 *   answer is to prove the missing fact, never to widen the guard.
 *
 *   No stop here is clearable by a flag. Every one is cleared by proving the missing fact.
 *
 * HOW AN ARCHIVED STRAIN IS CAUGHT
 *   By RESOLUTION, not by a flag. The Strains read is the live list: proven 2026-09-19 on a live
 *   tenant, where a strain id bound to six current items was absent from it entirely. So an
 *   archived id simply fails to resolve and is refused as STRAIN_ID_UNRESOLVED. The separate
 *   archived-flag branch is kept for the day the platform exposes one.
 *
 * Selftest: `node backoffice_grid_write_selftest.js` (login-free, mocked fetch).
 */
(function (root) {
  'use strict';

  // ------------------------------------------------------------------------------------------
  // What the KB proves, and nothing more.
  // ------------------------------------------------------------------------------------------

  // The 25 settable fields, internal names, read from the modal's Field dropdown 2026-09-15.
  var SETTABLE = ['CustomerTypes', 'BrandId', 'CBDContent', 'IsCannabisProduct', 'ProductCategoryId',
    'Cost', 'DefaultUnitId', 'ExternalSubCategory', 'Flavor', 'FlowerEquivalent', 'EcomCategory',
    'Grams', 'LowInventory', 'MetrcBrand', 'Name', 'IsOnlineProduct', 'IsPosProduct', 'Price',
    'PricingTier', 'ServingSizePerUnit', 'StrainId', 'SyncToMetrcItem', 'Tags', 'UnitTypeId',
    'VendorId'];

  // The v1 allowlist is the subset the DIRECT-CALL entry names, with its provenance carried into
  // every plan so an operator approving a live write sees how strong the proof is. Being settable
  // in the modal is NOT proof that the same field rides this payload the same way.
  //
  // `Tags` is deliberately absent: its direct-call semantics (replace or append?) are unproven, and
  // a guess there silently rewrites governance. Note that the ENVELOPE also carries a `Tags: []`
  // key — that is part of the captured body, not the Tags field, and the two never mix.
  var ALLOWED = {
    BrandId: {
      cast: 'number',
      clearProven: false,             // an empty brand box was never proven; a clear is not this batch
      provenance: 'payload captured from a real UI save 2026-09-22: FieldList:[{"BrandId": <id>}], ' +
        'key for key the envelope Name and Flavor were captured with',
      derives: 'BrandName',           // the read-back display name follows the record; declare it
    },
    StrainId: {
      cast: 'number',
      clearProven: false,               // the empty-box clear was proven on Flavor, not here
      provenance: 'payload captured from a real UI save: FieldList:[{"StrainId": <id>}]',
      derives: 'StrainType',            // setting the strain DERIVES the type; declare it, never "fix" it
    },
    Flavor: {
      cast: 'string',
      clearProven: true,                // "Clearing an attribute through the grid" — proven on Flavor
      provenance: 'named by the KB direct-call entry; its empty-value CLEAR is separately proven',
    },
    Name: {
      cast: 'string',
      clearProven: false,
      provenance: 'named by the KB direct-call entry as a per-item field (one call each)',
    },
  };

  var WRITE_PATH = '/api/product-master/update-products-multiple';   // documented in full
  var STRAINS_PATH = '/api/strain/get-strains';                      // documented in full

  // The two product reads are documented by NAME, not by path, so they are resolved from an
  // observed request rather than assembled from a guess.
  var READ_NAME = {
    active: 'get-product-master-v2',
    retired: 'get-product-master-retired-v2',
  };
  var WRITE_NAME = 'update-products-multiple';
  var STRAINS_NAME = 'get-strains';
  var WATCH = [WRITE_NAME, READ_NAME.retired, READ_NAME.active, STRAINS_NAME];

  var CTX_KEYS = ['SessionId', 'LspId', 'LocId', 'OrgId', 'UserId'];

  // ------------------------------------------------------------------------------------------
  // Capture. Installed on load, so by the time an operator asks for a plan the page's own traffic
  // has already supplied the request shapes. It must never break the page's request.
  // ------------------------------------------------------------------------------------------

  var CAP = root.__gridWriteCapture = root.__gridWriteCapture || { requests: {}, installed: false };
  var INTERNAL = false;   // true while THIS file is making a call, so a replay is not re-captured

  function nameFor(url) {
    for (var i = 0; i < WATCH.length; i++) if (url.indexOf(WATCH[i]) >= 0) return WATCH[i];
    return null;
  }

  function record(url, headers, rawBody) {
    if (INTERNAL) return;
    var name = nameFor(String(url));
    if (!name || typeof rawBody !== 'string') return;
    var parsed;
    try { parsed = JSON.parse(rawBody); } catch (e) { return; }
    CAP.requests[name] = { url: String(url), headers: headers || null, body: parsed, at: Date.now() };
  }

  if (!CAP.installed) {
    if (typeof root.fetch === 'function') {
      var origFetch = root.fetch;
      root.fetch = function (input, init) {
        try {
          var url = typeof input === 'string' ? input : (input && input.url);
          if (url && init) record(url, init.headers, init.body);
        } catch (e) { /* capture is best-effort; the page's own call always proceeds */ }
        return origFetch.apply(this, arguments);
      };
    }
    if (typeof root.XMLHttpRequest === 'function') {
      var xhrOpen = root.XMLHttpRequest.prototype.open;
      var xhrSend = root.XMLHttpRequest.prototype.send;
      root.XMLHttpRequest.prototype.open = function (method, url) {
        this.__gwUrl = url;
        return xhrOpen.apply(this, arguments);
      };
      root.XMLHttpRequest.prototype.send = function (body) {
        try { if (this.__gwUrl) record(this.__gwUrl, null, body); } catch (e) { /* as above */ }
        return xhrSend.apply(this, arguments);
      };
    }
    CAP.installed = true;
  }

  // ------------------------------------------------------------------------------------------
  // Small helpers.
  // ------------------------------------------------------------------------------------------

  var STORE = root.__gridWrite = root.__gridWrite || { runs: [], done: [] };

  function refuse(reason, detail) {
    return { ok: false, refused: true, reason: reason, detail: detail };
  }

  function isBlank(v) {
    return v === undefined || v === null || String(v).trim() === '';
  }

  // Key lookup is case-tolerant because the response casing is not something this file gets to
  // assume. The key that was actually used is reported, so a wrong guess is visible, not silent.
  function keyOf(obj, re) {
    if (!obj || typeof obj !== 'object') return null;
    var ks = Object.keys(obj);
    for (var i = 0; i < ks.length; i++) if (re.test(ks[i])) return ks[i];
    return null;
  }

  // Find the record array in a response without hardcoding a path into it. The KB documents
  // `{Data:{products:[...]}}`; this accepts that and any equivalent nesting, and reports failure
  // rather than returning an empty list that would read as "nothing matched".
  function findRows(json, idRe, nameRe) {
    var seen = 0;
    function walk(node, depth) {
      if (!node || typeof node !== 'object' || depth > 4 || seen > 200) return null;
      seen++;
      if (Array.isArray(node)) {
        if (node.length && node[0] && typeof node[0] === 'object' && keyOf(node[0], idRe)) return node;
        return null;
      }
      var ks = Object.keys(node);
      for (var i = 0; i < ks.length; i++) {
        var v = node[ks[i]];
        // An empty array under a plausibly-named key is a real empty result, not a shape failure.
        if (Array.isArray(v) && !v.length && nameRe.test(ks[i])) return v;
        var hit = walk(v, depth + 1);
        if (hit) return hit;
      }
      return null;
    }
    return walk(json, 0);
  }

  // ------------------------------------------------------------------------------------------
  // Envelope context. Harvested, never invented.
  // ------------------------------------------------------------------------------------------

  function ctxFrom(body) {
    if (!body || typeof body !== 'object') return null;
    var out = {}, missing = [];
    CTX_KEYS.forEach(function (k) {
      if (body[k] === undefined || body[k] === null) missing.push(k); else out[k] = body[k];
    });
    return missing.length ? { missing: missing } : { ctx: out };
  }

  function ensureContext(explicit) {
    if (explicit) {
      var e = ctxFrom(explicit);
      if (e && e.ctx) return { ctx: e.ctx, source: 'caller' };
      return { error: refuse('MISSING_CONTEXT', 'the ctx you passed is short: ' +
        (e ? e.missing.join(', ') : CTX_KEYS.join(', '))) };
    }
    // A captured WRITE is the strongest provenance: it is the request the picker itself sent.
    var order = [WRITE_NAME].concat(WATCH.filter(function (n) { return n !== WRITE_NAME; }));
    var shortfall = [];
    for (var i = 0; i < order.length; i++) {
      var cap = CAP.requests[order[i]];
      if (!cap) continue;
      var got = ctxFrom(cap.body);
      if (got && got.ctx) {
        return { ctx: got.ctx, source: 'captured:' + order[i] +
          (order[i] === WRITE_NAME ? ' (a real UI save)' : ' (a page read)') };
      }
      if (got) shortfall.push(order[i] + ' lacks ' + got.missing.join('/'));
    }
    return { error: refuse('MISSING_CONTEXT', 'no observed request carries all of ' +
      CTX_KEYS.join(', ') + '. ' + (shortfall.length ? shortfall.join('; ') : 'nothing observed yet') +
      '. Let the page issue a catalog read (open the grid, or apply the Retired filter) and retry; ' +
      'do NOT assemble these values by hand.') };
  }

  // ------------------------------------------------------------------------------------------
  // Replayed reads.
  // ------------------------------------------------------------------------------------------

  function post(url, headers, body) {
    INTERNAL = true;
    var p;
    try {
      p = root.fetch(url, {
        method: 'POST',
        headers: headers || { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      });
    } finally { INTERNAL = false; }
    return p;
  }

  // `fallbackPath` is supplied only where the KB documents the path in full. Where it documents
  // the endpoint by name only, a missing capture is a hard stop with the action that fixes it.
  function apiRead(name, fallbackPath, ctx, whatToTrigger) {
    var cap = CAP.requests[name];
    var url, headers, body;
    if (cap) {
      url = cap.url; headers = cap.headers; body = cap.body;
    } else if (fallbackPath) {
      url = root.location.origin + fallbackPath; headers = null; body = ctx;
    } else {
      return Promise.resolve({ error: refuse('MISSING_READ_CAPTURE',
        'no observed request for `' + name + '`, and the KB documents it by name, not by path. ' +
        whatToTrigger + ' so the page issues it, then retry.') });
    }
    return post(url, headers, body).then(function (r) {
      if (!r || !r.ok) {
        return { error: refuse('READ_UNVERIFIED', 'the read `' + name + '` returned HTTP ' +
          (r ? r.status : 'no response')) };
      }
      return r.json().then(function (j) { return { json: j, replayed: !!cap }; });
    });
  }

  // ------------------------------------------------------------------------------------------
  // gridWrite
  // ------------------------------------------------------------------------------------------

  function gridWrite(opts) {
    var o = opts || {};
    var ids = o.productIds;
    var field = o.field;
    var clear = o.clear === true;
    var dryRun = o.dryRun !== false;              // the default is a PLAN, never a write
    var refuseTags = o.refuseTags || [];
    var scope = o.scope;

    // --- pre-flight: pure input, no network -------------------------------------------------
    if (!Array.isArray(ids) || !ids.length) {
      return Promise.resolve(refuse('NO_PRODUCT_IDS', 'productIds must be a non-empty array of ids'));
    }
    if (scope !== 'active' && scope !== 'retired') {
      return Promise.resolve(refuse('SCOPE_INVALID',
        'scope must be "active" or "retired" — the active read never returns a retired item, ' +
        'so the scope decides which endpoint proves the row. Got: ' + JSON.stringify(scope)));
    }
    if (SETTABLE.indexOf(field) < 0) {
      return Promise.resolve(refuse('FIELD_NOT_SETTABLE',
        '`' + field + '` is not one of the 25 internal field names the bulk-edit modal exposes. ' +
        'Assert the internal name in the modal, never the label.'));
    }
    var allow = ALLOWED[field];
    if (!allow) {
      return Promise.resolve(refuse('FIELD_NOT_PROVEN',
        '`' + field + '` is settable in the modal but is not on this helper’s v1 direct-call ' +
        'allowlist (' + Object.keys(ALLOWED).join(', ') + '). Prove its payload on a real UI save ' +
        'and add it with that provenance; do not widen the list on a guess.'));
    }
    if (clear && !isBlank(o.value)) {
      return Promise.resolve(refuse('CLEAR_WITH_VALUE',
        'clear:true was passed with a value (' + JSON.stringify(o.value) + '). A clear is an ' +
        'explicit flag AND an empty value, never one of the two.'));
    }
    if (!clear && isBlank(o.value)) {
      return Promise.resolve(refuse('EMPTY_VALUE_WITHOUT_CLEAR',
        'the value is empty and clear is not true. Save is enabled with an empty box and blanks the ' +
        'field across the whole selection — this is the trap that cleared a live field in a real run.'));
    }
    if (clear && !allow.clearProven) {
      return Promise.resolve(refuse('CLEAR_UNPROVEN_FOR_FIELD',
        'the empty-value clear is proven on the fields marked clearProven, not on `' + field +
        '`. Prove it on one item through the modal first.'));
    }
    if (clear && ids.length > 1 && o.expectCount !== ids.length) {
      return Promise.resolve(refuse('CLEAR_MULTI_COUNT_UNCONFIRMED',
        'a clear across ' + ids.length + ' items requires expectCount to state that number ' +
        'exactly (got ' + JSON.stringify(o.expectCount) + ').'));
    }
    if (o.expectCount === undefined || o.expectCount === null) {
      return Promise.resolve(refuse('COUNT_MISSING',
        'expectCount is required on every call: it is the invariant that catches a selection that ' +
        'grew since you counted it.'));
    }
    if (o.expectCount !== ids.length) {
      return Promise.resolve(refuse('COUNT_MISMATCH',
        'expectCount ' + o.expectCount + ' but productIds holds ' + ids.length));
    }
    var dupes = ids.filter(function (v, i) { return ids.indexOf(v) !== i; });
    if (dupes.length) {
      return Promise.resolve(refuse('DUPLICATE_ID',
        'id(s) appear more than once: ' + dupes.join(', ')));
    }
    if (field === 'StrainId' && !clear &&
        (typeof o.value !== 'number' || !isFinite(o.value) || String(o.value).trim() === '')) {
      return Promise.resolve(refuse('STRAIN_ID_NOT_NUMERIC',
        'StrainId binds by RECORD: pass the numeric id from the Strains read, not a name. ' +
        'Got ' + JSON.stringify(o.value) + '. Resolving a name here is what a CSV load does, and ' +
        'that is the path that can hit an archived namesake.'));
    }

    // --- network: context, then the reads that back each remaining refusal -------------------
    var got = ensureContext(o.ctx);
    if (got.error) return Promise.resolve(got.error);
    var ctx = got.ctx;

    var payloadValue = clear ? '' : (allow.cast === 'number' ? Number(o.value) : String(o.value));
    var doneKey = field + '|' + (clear ? '<CLEAR>' : String(payloadValue)) + '|';

    var state = { ctx: ctx, ctxSource: got.source, rows: null, idKey: null, tagKey: null,
      before: {}, declares: [], archiveCheck: null };

    var trigger = scope === 'retired'
      ? 'Open the catalog grid with More → Retired products → Save'
      : 'Open the catalog grid';

    return apiRead(READ_NAME[scope], null, ctx, trigger).then(function (r) {
      if (r.error) return r.error;
      var rows = findRows(r.json, /^productid$/i, /product/i);
      if (!rows) {
        return refuse('READ_UNVERIFIED', 'the `' + READ_NAME[scope] + '` response holds no array of ' +
          'records carrying a ProductId. The KB documents {Data:{products:[...]}}; this is a ' +
          'different shape, so nothing downstream can be trusted.');
      }
      state.rows = rows;
      state.idKey = rows.length ? keyOf(rows[0], /^productid$/i) : 'ProductId';

      // Refusal: every id must resolve on the read for its scope.
      var index = {};
      rows.forEach(function (row) { index[String(row[state.idKey])] = row; });
      var missing = ids.filter(function (id) { return !index[String(id)]; });
      if (missing.length) {
        return refuse('PRODUCT_ID_UNRESOLVED',
          missing.length + ' id(s) did not resolve on the ' + scope + ' read: ' +
          missing.slice(0, 5).join(', ') + (missing.length > 5 ? ' …' : '') +
          '. The active read never returns a retired item; a paged replay can also simply not ' +
          'reach the row. Widen the page’s own read and retry.');
      }

      // Refusal: the field must be readable back, or the write cannot be verified at all.
      var absent = ids.filter(function (id) { return !(field in index[String(id)]); });
      if (absent.length) {
        return refuse('READBACK_FIELD_ABSENT',
          'the ' + scope + ' read does not return `' + field + '` (' + absent.length + ' item(s)), ' +
          'so a write could not be proven. A toast is not a read-back.');
      }

      // Refusal: the caller's dead-record tags. This file names no tag; the caller passes them.
      if (refuseTags.length) {
        var tagKey = rows.length ? keyOf(rows[0], /tag/i) : null;
        if (!tagKey) {
          return refuse('TAG_CHECK_UNAVAILABLE',
            'refuseTags was supplied but this read exposes no tag-bearing field, so the check ' +
            'cannot be made. Either prove the tag on a read that carries it, or drop refuseTags ' +
            'knowingly — this helper will not skip a check it was asked to make.');
        }
        state.tagKey = tagKey;
        var tagged = [];
        ids.forEach(function (id) {
          var raw = index[String(id)][tagKey];
          var hay = (Array.isArray(raw) ? raw.join(',') : String(raw == null ? '' : raw)).toLowerCase();
          refuseTags.forEach(function (t) {
            if (t && hay.indexOf(String(t).toLowerCase()) >= 0) tagged.push(id + ' [' + t + ']');
          });
        });
        if (tagged.length) {
          return refuse('REFUSED_TAG',
            'item(s) carry a refused tag: ' + tagged.slice(0, 5).join(', ') +
            (tagged.length > 5 ? ' …' : ''));
        }
      }

      ids.forEach(function (id) { state.before[String(id)] = index[String(id)][field]; });

      // Refusal 5 needs the live Strains read: numeric, resolves, and is not archived.
      if (field !== 'StrainId' || clear) return null;
      return apiRead(STRAINS_NAME, STRAINS_PATH, ctx,
        'Open the Strains page').then(function (s) {
        if (s.error) return s.error;
        var srows = findRows(s.json, /^strainid$/i, /strain/i);
        if (!srows || !srows.length) {
          return refuse('READ_UNVERIFIED', 'the `' + STRAINS_NAME + '` response holds no array of ' +
            'records carrying a StrainId, so the record behind this id cannot be proven.');
        }
        var sIdKey = keyOf(srows[0], /^strainid$/i);
        var sNameKey = keyOf(srows[0], /^strainname$/i);
        var hit = srows.filter(function (x) { return Number(x[sIdKey]) === payloadValue; });
        if (!hit.length) {
          return refuse('STRAIN_ID_UNRESOLVED',
            'StrainId ' + payloadValue + ' is not in the live Strains read (' + srows.length +
            ' records). Mint or correct the record first.');
        }
        if (hit.length > 1) {
          return refuse('STRAIN_ID_UNRESOLVED',
            'StrainId ' + payloadValue + ' matched ' + hit.length + ' records — abort on an ambiguity.');
        }
        var archKey = keyOf(hit[0], /archiv/i) || keyOf(hit[0], /^is_?active$/i) ||
          keyOf(hit[0], /^(is)?deleted$/i);
        if (!archKey) {
          // No archive/active field on the record — and that is not a gap, it is the answer.
          //
          // Proven 2026-09-19 on a live tenant: this read EXCLUDES records that still exist and are
          // still referenced. Of the distinct strain ids carried by the active plus retired catalog,
          // one was bound to six catalog items — the item rows render its name and type — and it was absent
          // from this read entirely. Separately, seven strain records that a name-bound CSV load had
          // demonstrably bound items to were absent here, while their live namesakes were present,
          // and the response carried no case-insensitive duplicate names at all.
          //
          // So the read is the LIVE list, and `hit.length` above is already the liveness proof: an
          // archived id fails to resolve and is refused as STRAIN_ID_UNRESOLVED before reaching here.
          // An extra "prove it is not archived" stop would be ceremony, and a stop a caller must
          // always wave through is a stop that stops meaning anything. The flag branch below is kept
          // for the day this surface grows one.
          state.archiveCheck = 'by resolution — this read is the live list';
          state.strainName = sNameKey ? hit[0][sNameKey] : null;
          return null;
        }
        var raw = hit[0][archKey];
        var archived = /archiv|deleted/i.test(archKey) ? !!raw : !raw;
        if (archived) {
          return refuse('STRAIN_ID_ARCHIVED',
            'StrainId ' + payloadValue + ' resolves to an ARCHIVED record (' + archKey + '=' +
            JSON.stringify(raw) + ').');
        }
        state.archiveCheck = 'proven on `' + archKey + '`';
        state.strainName = sNameKey ? hit[0][sNameKey] : null;
        return null;
      });
    }).then(function (stop) {
      if (stop) return stop;

      // --- resume: an interrupted run never re-writes an item it already proved ---------------
      var pending = ids.filter(function (id) { return STORE.done.indexOf(doneKey + id) < 0; });
      var skipped = ids.length - pending.length;
      if (!pending.length) {
        return { ok: true, field: field, scope: scope, count: ids.length, wrote: 0,
          skipped: skipped, verified: 0, conflicts: [],
          detail: 'every item was already written and verified in this page session' };
      }

      var body = {
        ProductList: pending,
        FieldList: [(function () { var f = {}; f[field] = payloadValue; return f; })()],
        CustomerTypes: [], TaxCategories: [], Tags: [],
        SessionId: ctx.SessionId, LspId: ctx.LspId, LocId: ctx.LocId,
        OrgId: ctx.OrgId, UserId: ctx.UserId,
      };
      var capWrite = CAP.requests[WRITE_NAME];
      var capRead = CAP.requests[READ_NAME[scope]];
      var url = capWrite ? capWrite.url : root.location.origin + WRITE_PATH;
      var headers = (capWrite && capWrite.headers) || (capRead && capRead.headers) || null;

      if (allow.derives) {
        state.declares.push(allow.derives + ' is DERIVED from ' + field +
          '; its value after this write is DECLARED, not a defect — never "fix" it.');
      }

      var plan = {
        ok: true, dryRun: true, field: field, provenance: allow.provenance,
        value: clear ? '<CLEAR>' : payloadValue, scope: scope,
        count: pending.length, skipped: skipped, wrote: 0,
        url: url, ctxSource: state.ctxSource, archiveCheck: state.archiveCheck,
        declares: state.declares,
        detail: 'plan only — nothing was written. Pass dryRun:false to run it.',
      };
      STORE.runs.push({ at: new Date().toISOString(), plan: plan, body: body,
        before: state.before, strainName: state.strainName || null,
        after: null, conflicts: [] });
      if (dryRun) return plan;

      var run = STORE.runs[STORE.runs.length - 1];
      return post(url, headers, body).then(function (r) {
        if (!r || !r.ok) {
          return refuse('WRITE_NOT_OK', 'the write returned HTTP ' + (r ? r.status : 'no response'));
        }
        return r.json().then(function (j) {
          if (!j || j.Result !== true) {
            return refuse('WRITE_NOT_OK', 'the documented success pair is HTTP 200 plus ' +
              '{"Result":true}; got ' + JSON.stringify(j).slice(0, 120));
          }
          // Read EVERY item back on the matching read. A success response is not a read-back:
          // a write can report success and change nothing.
          return apiRead(READ_NAME[scope], null, ctx, trigger).then(function (r2) {
            if (r2.error) return r2.error;
            var rows = findRows(r2.json, /^productid$/i, /product/i);
            if (!rows) {
              return refuse('READ_UNVERIFIED',
                'the post-write read returned a shape with no ProductId array, so the write is ' +
                'UNVERIFIED. Treat it as done-unknown and read the rows by hand before retrying.');
            }
            var idx = {};
            rows.forEach(function (row) { idx[String(row[state.idKey])] = row; });
            var after = {}, conflicts = [], verified = 0, derived = {};
            pending.forEach(function (id) {
              var row = idx[String(id)];
              if (!row || !(field in row)) {
                conflicts.push({ id: id, why: 'absent from the post-write read' });
                return;
              }
              var got2 = row[field];
              after[String(id)] = got2;
              if (allow.derives && allow.derives in row) derived[String(id)] = row[allow.derives];
              var match = clear
                ? (got2 === null || got2 === undefined || String(got2).trim() === '')
                : (allow.cast === 'number'
                  ? Number(got2) === payloadValue
                  : String(got2) === String(payloadValue));
              if (match) verified++;
              else conflicts.push({ id: id, want: clear ? '<CLEAR>' : payloadValue, got: got2 });
            });
            run.after = after;
            run.derived = derived;
            run.conflicts = conflicts;

            if (conflicts.length) {
              // Never retry blind. A group whose read-back disagrees is a CONFLICT, and a write
              // that reported success while nothing moved is the same finding, not a success.
              return { ok: false, reason: 'CONFLICT', field: field, scope: scope,
                count: pending.length, wrote: pending.length, verified: verified,
                conflicts: conflicts.slice(0, 3),
                detail: conflicts.length + ' of ' + pending.length + ' item(s) did not read back as ' +
                  'written' + (verified === 0 ? ' — nothing moved, so treat the success response as ' +
                  'swallowed' : '') + '. STOPPED; see window.__gridWrite for the full rows.' };
            }
            pending.forEach(function (id) { STORE.done.push(doneKey + id); });
            return { ok: true, field: field, value: clear ? '<CLEAR>' : payloadValue, scope: scope,
              count: pending.length, wrote: pending.length, skipped: skipped, verified: verified,
              conflicts: [], ctxSource: state.ctxSource, archiveCheck: state.archiveCheck,
              declares: state.declares, detail: 'all item(s) read back as written' };
          });
        });
      });
    });
  }

  // ------------------------------------------------------------------------------------------
  // Operator-facing status.
  // ------------------------------------------------------------------------------------------

  function gridWriteCapture() {
    var have = {}, ctx = ensureContext(null);
    WATCH.forEach(function (n) { have[n] = CAP.requests[n] ? 'observed' : 'NOT observed'; });
    return {
      installed: CAP.installed,
      observed: have,
      context: ctx.ctx ? ('ready from ' + ctx.source) : ('NOT ready — ' + ctx.error.detail),
      allowlist: Object.keys(ALLOWED),
      note: 'let the page issue its own reads; this file replays them rather than composing one.',
    };
  }

  function gridWriteStatus() {
    var last = STORE.runs[STORE.runs.length - 1] || null;
    return { runs: STORE.runs.length, done: STORE.done.length,
      lastConflicts: last ? last.conflicts : [], lastPlan: last ? last.plan : null };
  }

  function gridWriteReset() {
    STORE.done = [];
    return { done: 0, note: 'the done-list is cleared; runs are kept for the record' };
  }

  root.gridWrite = gridWrite;
  root.gridWriteCapture = gridWriteCapture;
  root.gridWriteStatus = gridWriteStatus;
  root.gridWriteReset = gridWriteReset;
})(typeof globalThis !== 'undefined' ? globalThis : this);
