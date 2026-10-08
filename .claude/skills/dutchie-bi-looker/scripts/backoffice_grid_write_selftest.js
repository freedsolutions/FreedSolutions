#!/usr/bin/env node
'use strict';
//
// Login-free selftest for `backoffice_grid_write.js`.
//
//   node backoffice_grid_write_selftest.js
//
// The helper is PAGE-SIDE code: it is evaluated inside an already-logged-in Backoffice tab and it
// talks to the platform over `fetch`. This test evaluates that same file in a `vm` context with a
// mocked `fetch`, so it exercises the REAL source — not a re-implementation of it — and needs no
// login, no browser and no network.
//
// The contract under test is the refusal list. A guard that cannot be made to FAIL has not been
// tested, so every refusal is proven twice:
//
//   GREEN  the clean fixture completes and does NOT raise that reason
//   RED    a fixture broken in EXACTLY ONE place raises that reason and no other
//
// Each case below names its single break. If a break needs two edits to fire, the guard it claims
// to test is not the guard that fired, and the case is wrong.
//
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HELPER = path.join(__dirname, 'backoffice_grid_write.js');
const SRC = fs.readFileSync(HELPER, 'utf8');
const ORIGIN = 'https://backoffice.example.invalid';

// ---------------------------------------------------------------------------------------------
// Fixtures. Every literal here is synthetic: this is tracked skill code and carries no tenant
// name, record name, tag name or path. The shapes come from the platform KB's "Backoffice
// bulk-edit grid" section (Path A' and the two product-master read endpoints).
// ---------------------------------------------------------------------------------------------

const ENVELOPE = { SessionId: 'FIXTURE-SESSION', LspId: 11, LocId: 22, OrgId: 33, UserId: 44 };

function product(id, over) {
  return Object.assign({
    ProductId: id,
    ProductName: 'FIXTURE ITEM ' + id,
    StrainId: 999,          // deliberately NOT the target, so a swallowed write is visible
    StrainType: 'Unknown',
    Flavor: 'FIXTURE-FLAVOR',
    Cost: 999,              // the three numeric per-item fields, each deliberately NOT the target
    Price: 999,
    FlowerEquivalent: 999,
    ProductCategoryId: 999, // deliberately NOT the target
    Category: 'FIXTURE-CATEGORY-OLD',
    Tags: '',
  }, over || {});
}

// A clean Category move (ProductCategoryId, proven 2026-09-28 on retired items) of one retired item.
function cleanCategory() {
  const s = cleanWrite();
  s.label = 'move one retired item to another Category by record id';
  s.args = {
    productIds: [9101], field: 'ProductCategoryId', value: 501,
    expectCount: 1, scope: 'retired', refuseTags: ['FIXTURE-DEAD-TAG'], dryRun: false,
  };
  return s;
}

// A clean numeric write of one of the per-item number fields (Cost / Price / FlowerEquivalent) to
// one active item, mirroring cleanWrite's mocked reads.
function cleanNumber(field) {
  return function () {
    const s = cleanWrite();
    s.label = 'write ' + field + ' (a number) to one active item';
    s.args = {
      productIds: [9001], field: field, value: 12.5,
      expectCount: 1, scope: 'active', refuseTags: ['FIXTURE-DEAD-TAG'], dryRun: false,
    };
    return s;
  };
}
const NUMBER_FIELDS = ['Cost', 'Price', 'FlowerEquivalent'];

function cleanWrite() {
  return {
    label: 'write StrainId to two active items',
    prime: ['active', 'retired', 'strains'],
    ctxKeysOmit: [],
    strains: [
      { StrainId: 101, StrainName: 'FIXTURE-ALPHA', IsArchived: false, StrainType: 'Hybrid' },
      { StrainId: 102, StrainName: 'FIXTURE-BETA', IsArchived: true, StrainType: 'Indica' },
    ],
    active: [product(9001), product(9002)],
    retired: [product(9101)],
    readShape: 'good',
    writeResult: true,
    swallow: false,
    applyWrong: null,
    hideFieldOnReadback: false,
    args: {
      productIds: [9001, 9002], field: 'StrainId', value: 101,
      expectCount: 2, scope: 'active', refuseTags: ['FIXTURE-DEAD-TAG'], dryRun: false,
    },
  };
}

// The shape a live tenant actually returns: no archive field anywhere on the record. Proven
// 2026-09-19 — the read is the LIVE list, so an archived id is caught by failing to resolve, not
// by a flag. This fixture must therefore COMPLETE, not stop.
function cleanNoFlag() {
  const s = cleanWrite();
  s.label = 'StrainId write where the platform exposes no archive flag at all';
  s.strains.forEach(function (r) { delete r.IsArchived; });
  return s;
}

function cleanClear() {
  const s = cleanWrite();
  s.label = 'clear Flavor on one active item';
  s.args = {
    productIds: [9001], field: 'Flavor', value: '', clear: true,
    expectCount: 1, scope: 'active', refuseTags: ['FIXTURE-DEAD-TAG'], dryRun: false,
  };
  return s;
}

// ---------------------------------------------------------------------------------------------
// The mocked platform.
// ---------------------------------------------------------------------------------------------

function reply(json, status) {
  const code = status || 200;
  return Promise.resolve({
    ok: code < 400,
    status: code,
    json: function () { return Promise.resolve(json); },
    text: function () { return Promise.resolve(JSON.stringify(json)); },
  });
}

function rows(sc, scope) {
  const list = (scope === 'retired' ? sc.retired : sc.active).map(function (p) {
    const copy = Object.assign({}, p);
    if (sc.hideFieldOnReadback) delete copy[sc.args.field];
    return copy;
  });
  if (sc.readShape === 'junk') return { Data: { message: 'no array here' } };
  return { Data: { products: list } };
}

function strainRows(sc) {
  if (sc.readShape === 'junk') return { Data: {} };
  return { Data: { strains: sc.strains } };
}

function applyWrite(sc, body) {
  const field = Object.keys(body.FieldList[0])[0];
  const written = sc.applyWrong !== null ? sc.applyWrong : body.FieldList[0][field];
  const all = sc.active.concat(sc.retired);
  body.ProductList.forEach(function (id) {
    const rec = all.filter(function (p) { return p.ProductId === id; })[0];
    if (rec) rec[field] = written;
  });
}

function makeEnv(sc) {
  const calls = [];
  const sandbox = {
    console: console,
    setTimeout: setTimeout,
    clearTimeout: clearTimeout,
    location: { origin: ORIGIN, href: ORIGIN + '/products/catalog' },
  };
  sandbox.fetch = function (url, init) {
    const u = String(url);
    const body = init && init.body ? JSON.parse(init.body) : null;
    calls.push({ url: u, method: (init && init.method) || 'GET', body: body });
    if (u.indexOf('update-products-multiple') >= 0) {
      if (sc.writeResult === false) return reply({ Result: false });
      if (!sc.swallow) applyWrite(sc, body);
      return reply({ Result: true });
    }
    if (u.indexOf('get-strains') >= 0) return reply(strainRows(sc));
    if (u.indexOf('get-product-master-retired-v2') >= 0) return reply(rows(sc, 'retired'));
    if (u.indexOf('get-product-master-v2') >= 0) return reply(rows(sc, 'active'));
    return reply({ error: 'unmapped endpoint' }, 404);
  };
  vm.createContext(sandbox);
  vm.runInContext('globalThis.window = globalThis;', sandbox);
  vm.runInContext(SRC, sandbox, { filename: HELPER });
  return { sandbox: sandbox, calls: calls };
}

// The page's own traffic, replayed: the grid issues these reads on load, and the helper's capture
// interceptor is what turns them into a replayable request + a harvested envelope.
function prime(env, sc) {
  const body = {};
  Object.keys(ENVELOPE).forEach(function (k) {
    if (sc.ctxKeysOmit.indexOf(k) < 0) body[k] = ENVELOPE[k];
  });
  body.PageSize = 100;
  const urls = {
    active: ORIGIN + '/api/product-master/get-product-master-v2',
    retired: ORIGIN + '/api/product-master/get-product-master-retired-v2',
    strains: ORIGIN + '/api/strain/get-strains',
  };
  return sc.prime.reduce(function (chain, name) {
    return chain.then(function () {
      return env.sandbox.window.fetch(urls[name], {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
    });
  }, Promise.resolve());
}

function run(sc) {
  const env = makeEnv(sc);
  return prime(env, sc).then(function () {
    return env.sandbox.window.gridWrite(sc.args);
  }).then(function (res) {
    return {
      res: res,
      calls: env.calls,
      writes: env.calls.filter(function (c) { return c.url.indexOf('update-products-multiple') >= 0; }),
      sandbox: env.sandbox,
    };
  });
}

// ---------------------------------------------------------------------------------------------
// Assertions.
// ---------------------------------------------------------------------------------------------

let passed = 0;
const failures = [];

function ok(cond, what) {
  passed++;
  if (!cond) failures.push(what);
}

function eq(actual, expected, what) {
  passed++;
  if (actual !== expected) failures.push(what + '  (expected ' + JSON.stringify(expected) +
    ', got ' + JSON.stringify(actual) + ')');
}

// ---------------------------------------------------------------------------------------------
// The refusal cases. `base` is the clean scenario; `brk` is the SINGLE place that is broken.
// ---------------------------------------------------------------------------------------------

const CASES = [
  // 1. field is not settable / not on the v1 proven allowlist
  { reason: 'FIELD_NOT_SETTABLE', note: 'field absent from the KB 25',
    base: cleanWrite, brk: function (s) { s.args.field = 'NotARealField'; } },
  { reason: 'FIELD_NOT_PROVEN', note: 'settable but no direct-call proof (Grams)',
    base: cleanWrite, brk: function (s) { s.args.field = 'Grams'; } },
  { reason: 'FIELD_NOT_PROVEN', note: 'Tags is settable but its direct-call semantics are unproven',
    base: cleanWrite, brk: function (s) { s.args.field = 'Tags'; } },

  // 2. an empty value is a CLEAR only behind the explicit flag
  { reason: 'EMPTY_VALUE_WITHOUT_CLEAR', note: 'the trap-1 write, refused',
    base: cleanWrite, brk: function (s) { s.args.value = ''; } },
  { reason: 'CLEAR_WITH_VALUE', note: 'clear flag set while a value is present',
    base: cleanWrite, brk: function (s) { s.args.clear = true; } },
  { reason: 'CLEAR_UNPROVEN_FOR_FIELD', note: 'the empty-box clear is proven on Flavor only',
    base: cleanClear, brk: function (s) { s.args.field = 'StrainId'; } },

  // 2b. the per-item number fields (proven 2026-09-28): an empty value is refused without clear,
  //     and a clear is refused because none of the three has a proven empty-box clear
  { reason: 'EMPTY_VALUE_WITHOUT_CLEAR', note: 'Cost — empty value, no clear flag',
    base: cleanNumber('Cost'), brk: function (s) { s.args.value = ''; } },
  { reason: 'EMPTY_VALUE_WITHOUT_CLEAR', note: 'Price — empty value, no clear flag',
    base: cleanNumber('Price'), brk: function (s) { s.args.value = ''; } },
  { reason: 'EMPTY_VALUE_WITHOUT_CLEAR', note: 'FlowerEquivalent — empty value, no clear flag',
    base: cleanNumber('FlowerEquivalent'), brk: function (s) { s.args.value = ''; } },
  { reason: 'CLEAR_UNPROVEN_FOR_FIELD', note: 'Price — a clear is not proven on the number fields',
    base: cleanNumber('Price'), brk: function (s) { s.args.value = ''; s.args.clear = true; } },

  //     and a NON-NUMERIC value is refused: Number('3.5g') is NaN, which would post as null
  { reason: 'VALUE_NOT_NUMERIC', note: 'Cost — a currency string where a number belongs',
    base: cleanNumber('Cost'), brk: function (s) { s.args.value = '$12'; } },
  { reason: 'VALUE_NOT_NUMERIC', note: 'Price — a numeric STRING is still a string',
    base: cleanNumber('Price'), brk: function (s) { s.args.value = '12.50'; } },
  { reason: 'VALUE_NOT_NUMERIC', note: 'FlowerEquivalent — the export grams string ("3.5g")',
    base: cleanNumber('FlowerEquivalent'), brk: function (s) { s.args.value = '3.5g'; } },

  // 2c. ProductCategoryId (proven 2026-09-28): binds by record id, and no clear is proven
  { reason: 'CATEGORY_ID_NOT_NUMERIC', note: 'a Category label passed where the record id belongs',
    base: cleanCategory, brk: function (s) { s.args.value = 'FIXTURE-CATEGORY-NEW'; } },
  { reason: 'EMPTY_VALUE_WITHOUT_CLEAR', note: 'ProductCategoryId — empty value, no clear flag',
    base: cleanCategory, brk: function (s) { s.args.value = ''; } },
  { reason: 'CLEAR_UNPROVEN_FOR_FIELD', note: 'ProductCategoryId — a clear is not proven',
    base: cleanCategory, brk: function (s) { s.args.value = ''; s.args.clear = true; } },

  // 3. a multi-item clear needs the count stated
  { reason: 'CLEAR_MULTI_COUNT_UNCONFIRMED', note: 'clear widened to 2 items, count still 1',
    base: cleanClear, brk: function (s) { s.args.productIds = [9001, 9002]; } },

  // 4. the count guard and the duplicate guard
  { reason: 'NO_PRODUCT_IDS', note: 'empty id list',
    base: cleanWrite, brk: function (s) { s.args.productIds = []; } },
  { reason: 'COUNT_MISMATCH', note: 'expectCount disagrees with the id list',
    base: cleanWrite, brk: function (s) { s.args.expectCount = 3; } },
  { reason: 'COUNT_MISSING', note: 'no expectCount at all',
    base: cleanWrite, brk: function (s) { delete s.args.expectCount; } },
  { reason: 'DUPLICATE_ID', note: 'the same id twice',
    base: cleanWrite, brk: function (s) { s.args.productIds = [9001, 9001]; } },

  // 5. StrainId must be numeric, live and not archived
  { reason: 'STRAIN_ID_NOT_NUMERIC', note: 'a name passed where the record id belongs',
    base: cleanWrite, brk: function (s) { s.args.value = 'FIXTURE-ALPHA'; } },
  // THIS is the archive guard. Proven live 2026-09-19: a strain id bound to six current items was
  // absent from this read, so an archived record fails here and never reaches a flag check.
  { reason: 'STRAIN_ID_UNRESOLVED', note: 'id absent from the read — the archive guard itself',
    base: cleanWrite, brk: function (s) { s.args.value = 777; } },
  { reason: 'STRAIN_ID_ARCHIVED', note: 'id resolves to an archived record',
    base: cleanWrite, brk: function (s) { s.args.value = 102; } },
  { reason: 'STRAIN_ID_ARCHIVED', note: 'the flag branch still refuses where a platform has one',
    base: cleanNoFlag, brk: function (s) {
      s.strains.forEach(function (r) { r.IsArchived = Number(r.StrainId) === 102; });
      s.args.value = 102;
    } },

  // 6. every product id must resolve on the read for its scope
  { reason: 'SCOPE_INVALID', note: 'a scope with no read endpoint',
    base: cleanWrite, brk: function (s) { s.args.scope = 'archived'; } },
  { reason: 'PRODUCT_ID_UNRESOLVED', note: 'a retired id under the active read',
    base: cleanWrite, brk: function (s) { s.args.productIds = [9001, 9101]; } },

  // 7. the caller's refuse-tag list
  { reason: 'REFUSED_TAG', note: 'an item carries a tag the caller refuses',
    base: cleanWrite, brk: function (s) { s.active[1].Tags = 'FIXTURE-DEAD-TAG'; } },
  { reason: 'TAG_CHECK_UNAVAILABLE', note: 'refuseTags supplied but no tag field on the record',
    base: cleanWrite, brk: function (s) {
      s.active.forEach(function (p) { delete p.Tags; });
    } },

  // Infrastructure: never guess an envelope value, an endpoint or a response shape
  { reason: 'MISSING_CONTEXT', note: 'a captured body is short one envelope key',
    base: cleanWrite, brk: function (s) { s.ctxKeysOmit = ['UserId']; } },
  { reason: 'MISSING_READ_CAPTURE', note: 'the product-master read was never observed',
    base: cleanWrite, brk: function (s) { s.prime = ['strains']; } },
  { reason: 'READ_UNVERIFIED', note: 'the read returns a shape the KB does not document',
    base: cleanWrite, brk: function (s) { s.readShape = 'junk'; } },

  // The write itself, and the read-back
  { reason: 'WRITE_NOT_OK', note: 'Result:false instead of the documented success pair',
    base: cleanWrite, brk: function (s) { s.writeResult = false; } },
  { reason: 'CONFLICT', note: 'a swallowed write: success reported, nothing changed',
    base: cleanWrite, brk: function (s) { s.swallow = true; } },
  { reason: 'CONFLICT', note: 'read-back holds a value nobody asked for',
    base: cleanWrite, brk: function (s) { s.applyWrong = 555; } },
  { reason: 'READBACK_FIELD_ABSENT', note: 'the read does not return the field that was written',
    base: cleanWrite, brk: function (s) { s.hideFieldOnReadback = true; } },
];

function runCases(i) {
  if (i >= CASES.length) return Promise.resolve();
  const c = CASES[i];
  const clean = c.base();
  const broken = c.base();
  c.brk(broken);

  return run(clean).then(function (g) {
    // GREEN: the clean fixture completes, and this reason is not what stopped it.
    eq(g.res.ok, true, 'GREEN ' + c.reason + ' — clean fixture should complete (' + c.note + ')' +
      (g.res.ok ? '' : ' [got ' + g.res.reason + ': ' + g.res.detail + ']'));
    ok(g.res.reason !== c.reason, 'GREEN ' + c.reason + ' — clean fixture must not raise it');
    return run(broken);
  }).then(function (r) {
    // RED: the one broken place raises exactly this reason.
    eq(r.res.ok, false, 'RED ' + c.reason + ' — broken fixture must refuse (' + c.note + ')');
    eq(r.res.reason, c.reason, 'RED ' + c.reason + ' — reason (' + c.note + ')');
    // A refusal raised BEFORE the write must not have written. CONFLICT and the two write-time
    // reasons are raised after it by definition, so they are exempt.
    const postWrite = ['CONFLICT', 'WRITE_NOT_OK', 'READBACK_FIELD_ABSENT'];
    if (postWrite.indexOf(c.reason) < 0) {
      eq(r.writes.length, 0, 'RED ' + c.reason + ' — must refuse before any write (' + c.note + ')');
    }
    return runCases(i + 1);
  });
}

// ---------------------------------------------------------------------------------------------
// Behaviour that is not a refusal.
// ---------------------------------------------------------------------------------------------

function extras() {
  // dryRun is the default, and it sends zero write requests.
  const a = cleanWrite();
  delete a.args.dryRun;
  return run(a).then(function (r) {
    eq(r.res.ok, true, 'dryRun default — plan returns ok');
    eq(r.res.dryRun, true, 'dryRun default — dryRun is TRUE when the caller omits it');
    eq(r.writes.length, 0, 'dryRun default — zero write requests');
    eq(r.res.wrote, 0, 'dryRun default — nothing reported as written');

    // The payload is the KB envelope, key for key. This is the anti-guess assertion: if a future
    // edit invents a key or drops one, this fails before it can reach a live tenant.
    return run(cleanWrite());
  }).then(function (r) {
    eq(r.writes.length, 1, 'one call per value — two items, one request');
    const body = r.writes[0].body;
    eq(Object.keys(body).sort().join(','),
      'CustomerTypes,FieldList,LocId,LspId,OrgId,ProductList,SessionId,Tags,TaxCategories,UserId',
      'payload keys match the captured body in the KB, exactly');
    eq(JSON.stringify(body.ProductList), '[9001,9002]', 'payload ProductList');
    eq(JSON.stringify(body.FieldList), '[{"StrainId":101}]', 'payload FieldList carries one value');
    eq(JSON.stringify(body.CustomerTypes), '[]', 'payload CustomerTypes stays empty as captured');
    eq(JSON.stringify(body.TaxCategories), '[]', 'payload TaxCategories stays empty as captured');
    eq(JSON.stringify(body.Tags), '[]', 'payload envelope Tags stays empty (not the Tags FIELD)');
    eq(body.SessionId, ENVELOPE.SessionId, 'payload SessionId is the harvested value');
    eq(body.UserId, ENVELOPE.UserId, 'payload UserId is the harvested value');

    // The derived Strain Type is DECLARED, never repaired.
    ok(/declared/i.test(JSON.stringify(r.res.declares || [])),
      'StrainId write declares the derived Strain Type rather than treating it as a defect');

    // Where the platform CAN answer the archive question, the result says so by field name.
    eq(r.res.archiveCheck, 'proven on `IsArchived`',
      'archiveCheck names the field the liveness proof came from, where one exists');

    // Where it cannot, the acknowledgement is carried in the result and parked in full, so a
    // cleared stop is never invisible after the fact.
    return run(cleanNoFlag());
  }).then(function (r) {
    eq(r.res.ok, true, 'no-flag tenant — completes with no ceremony and no flag to pass');
    eq(r.res.archiveCheck, 'by resolution — this read is the live list',
      'no-flag tenant — the result states HOW liveness was established');
    return run(cleanWrite());
  }).then(function (r) {

    // Full detail is parked for a follow-up read, because the in-page JS channel truncates.
    const parked = r.sandbox.window.__gridWrite;
    ok(parked && parked.runs && parked.runs.length === 1, 'full detail parked on window.__gridWrite');
    ok(JSON.stringify(r.res).length < 1024, 'summary stays under the ~1 KB in-page output cap');

    // Resume: a second identical call re-writes nothing.
    const sc = cleanWrite();
    const env = makeEnv(sc);
    return prime(env, sc)
      .then(function () { return env.sandbox.window.gridWrite(sc.args); })
      .then(function (first) {
        eq(first.wrote, 2, 'resume — first pass writes both items');
        return env.sandbox.window.gridWrite(sc.args);
      })
      .then(function (second) {
        eq(second.ok, true, 'resume — second pass completes');
        eq(second.wrote, 0, 'resume — second pass writes nothing');
        eq(second.skipped, 2, 'resume — both items reported as already done');
        const writes = env.calls.filter(function (c) {
          return c.url.indexOf('update-products-multiple') >= 0;
        });
        eq(writes.length, 1, 'resume — exactly one write request across both passes');
      });
  }).then(function () {
    // A clear that IS the target completes, and posts an empty string for the field.
    const sc = cleanClear();
    return run(sc).then(function (r) {
      eq(r.res.ok, true, 'clear — the explicit clear completes');
      eq(JSON.stringify(r.writes[0].body.FieldList), '[{"Flavor":""}]', 'clear — posts an empty value');
    });
  }).then(function () {
    // The per-item number fields (Cost / Price / FlowerEquivalent, proven 2026-09-28): each PLANS on
    // the mocked read with dryRun as the default (zero writes, the 9/28 provenance carried in the
    // plan), and a live write posts the value as a NUMBER, one item per call, read back exactly.
    return NUMBER_FIELDS.reduce(function (chain, field) {
      return chain.then(function () {
        const plan = cleanNumber(field)();
        delete plan.args.dryRun;
        return run(plan);
      }).then(function (r) {
        eq(r.res.ok, true, field + ' — plans on a mocked read');
        eq(r.res.dryRun, true, field + ' — dryRun is the default');
        eq(r.writes.length, 0, field + ' — the plan sends zero writes');
        ok(/2026-09-28/.test(String(r.res.provenance || '')), field + ' — the plan carries the 2026-09-28 provenance');
        return run(cleanNumber(field)());
      }).then(function (r) {
        eq(r.res.ok, true, field + ' — the live write completes');
        eq(r.writes.length, 1, field + ' — one item, one call');
        eq(JSON.stringify(r.writes[0].body.FieldList), '[{"' + field + '":12.5}]',
          field + ' — FieldList carries the value as a NUMBER, not a string');
        eq(r.res.verified, 1, field + ' — read back exactly once');
      });
    }, Promise.resolve());
  }).then(function () {
    // ProductCategoryId (proven 2026-09-28): plans with dryRun as the default and the 9/28
    // provenance; a live write posts the id as a NUMBER on the retired read and DECLARES the
    // derived Category label instead of treating it as a defect.
    const plan = cleanCategory();
    delete plan.args.dryRun;
    return run(plan).then(function (r) {
      eq(r.res.ok, true, 'ProductCategoryId — plans on a mocked retired read');
      eq(r.res.dryRun, true, 'ProductCategoryId — dryRun is the default');
      eq(r.writes.length, 0, 'ProductCategoryId — the plan sends zero writes');
      ok(/2026-09-28/.test(String(r.res.provenance || '')), 'ProductCategoryId — the plan carries the 2026-09-28 provenance');
      ok(/cross-MC move is UNPROVEN/.test(String(r.res.provenance || '')), 'ProductCategoryId — the plan states the cross-MC gap');
      return run(cleanCategory());
    }).then(function (r) {
      eq(r.res.ok, true, 'ProductCategoryId — the live write completes');
      eq(r.writes.length, 1, 'ProductCategoryId — one item, one call');
      eq(JSON.stringify(r.writes[0].body.FieldList), '[{"ProductCategoryId":501}]',
        'ProductCategoryId — FieldList carries the id as a NUMBER');
      eq(r.res.verified, 1, 'ProductCategoryId — read back exactly once');
      ok(/Category is DERIVED/.test(JSON.stringify(r.res.declares || [])),
        'ProductCategoryId — declares the derived Category label rather than treating it as a defect');
    });
  });
}

// ---------------------------------------------------------------------------------------------
// gridBatch — the R124 batch mode. A synthetic plan in the shape intake_plan.py writes, a mocked
// platform with a per-item record read, and a driver that plays the neo runtime: it logs each call,
// waits the PACE / BACKOFF it is told to on a FAKE clock, and runs the UI rows (HANDOFF) itself.
// ---------------------------------------------------------------------------------------------

const BATCH_IDS = { BrandId: { 'Brand A': 5101, 'Brand B': 5102 } };
// The cross-language vector: intake_plan.py's selftest asserts the SAME row hashes to the SAME value.
const SHA_VECTOR = {
  row: { seq: '1', step: 'ALIGN', line_no: '3', product_key: 'new:3', field: 'Price', before: '20',
    target: '18', channel: 'grid', depends_on: '5', provenance: '§2A row 10 · Brand A | Gummies' },
  sha: '134d396126fcd0c7bc03b49d0da22069df4e16f3',
};

function rec(id, over) {
  return Object.assign({ ProductId: id, ProductName: 'FIXTURE ' + id, StrainId: 101, Price: 20,
    Flavor: 'Mango', BrandId: 5102, Cost: 9, Tags: 'FIXTURE-ACTIVE' }, over || {});
}

function batchPlan(sha) {
  const rows = [
    ['COPY', '2', 'new:2', '_copy', '9001', 'Brand A | Pre-Roll | Strain Q | 1g', 'ui_copy', ''],
    ['ALIGN', '2', 'new:2', 'StrainId', 'name:Strain X', 'name:Strain Q', 'grid', '1'],
    ['ALIGN', '3', '9002', 'Price', '20', '18', 'grid', ''],
    ['ALIGN', '3', '9002', 'Flavor', 'Mango', 'Lime', 'grid', ''],
    ['ALIGN', '3', '9002', 'BrandId', 'name:Brand B', 'name:Brand A', 'grid', ''],
    ['ALIGN', '4', '9003', 'Cost', '9', '8', 'grid', ''],
    ['CONTENT', '2', 'new:2', 'Online title', 'Strain X Pre-Roll 1g', 'Strain Q Pre-Roll 1g', 'item_form', '1'],
  ].map(function (c, i) {
    return { seq: String(i + 1), step: c[0], line_no: c[1], product_key: c[2], field: c[3], before: c[4],
      target: c[5], channel: c[6], depends_on: c[7], provenance: 'synthetic' };
  });
  rows.forEach(function (r) { r.row_sha1 = sha(r); });
  return rows;
}

function rehash(env, plan) {
  plan.forEach(function (r) { r.row_sha1 = env.sandbox.window.gridPlanRowSha1(r); });
  return plan;
}

// A mocked platform for the batch: the record read answers {Data: <record>} for body.ProductId.
// `inject` = { guard429: {seq-free ProductId: n times}, write429: {pid: n}, guard401: pid, writeFalse: pid }
function batchEnv(opts) {
  const o = opts || {};
  const db = {};
  [rec(9001), rec(9002), rec(9003)].forEach(function (r) { db[r.ProductId] = r; });
  Object.keys(o.over || {}).forEach(function (id) { Object.assign(db[id], o.over[id]); });
  const inj = { guard429: Object.assign({}, o.guard429 || {}), write429: Object.assign({}, o.write429 || {}) };
  const calls = [];
  const sandbox = { console: console, location: { origin: ORIGIN, href: ORIGIN + '/products/catalog' } };
  sandbox.fetch = function (url, init) {
    const u = String(url);
    const body = init && init.body ? JSON.parse(init.body) : null;
    const call = { url: u, body: body, status: 200, applied: false };
    calls.push(call);
    if (u.indexOf('get-product-details-v2') >= 0) {
      const id = body.ProductId;
      if (inj.guard429[id] > 0) { inj.guard429[id]--; call.status = 429; return reply({ Message: 'Too many' }, 429); }
      if (o.guard401 === id) { call.status = 401; return reply({}, 401); }
      return reply(db[id] ? { Data: Object.assign({}, db[id]) } : { Data: null });
    }
    if (u.indexOf('update-products-multiple') >= 0) {
      const id = body.ProductList[0];
      if (inj.write429[id] > 0) { inj.write429[id]--; call.status = 429; return reply({ Message: 'Too many' }, 429); }
      if (o.writeFalse === id) return reply({ Result: false });
      const f = Object.keys(body.FieldList[0])[0];
      db[id][f] = body.FieldList[0][f];
      call.applied = true;
      return reply({ Result: true });
    }
    if (u.indexOf('get-strains') >= 0) {
      return reply({ Data: { strains: [{ StrainId: 101, StrainName: 'Strain X' }, { StrainId: 103, StrainName: 'Strain Q' }] } });
    }
    if (u.indexOf('get-product-master') >= 0) return reply({ Data: { products: Object.values(db) } });
    return reply({ error: 'unmapped' }, 404);
  };
  vm.createContext(sandbox);
  vm.runInContext('globalThis.window = globalThis;', sandbox);
  vm.runInContext(SRC, sandbox, { filename: HELPER });
  const env = { sandbox: sandbox, calls: calls, db: db };
  // the page's own traffic: a catalog read (the envelope) and ONE item form load (the record read)
  const ctxBody = Object.assign({}, ENVELOPE, { PageSize: 100 });
  const primes = [[ORIGIN + '/api/product-master/get-product-master-v2', ctxBody]];
  if (o.noDetailsCapture !== true) {
    primes.push([ORIGIN + '/api/product/get-product-details-v2', Object.assign({}, ENVELOPE, { ProductId: 9001 })]);
  }
  return primes.reduce(function (ch, p) {
    return ch.then(function () {
      return sandbox.window.fetch(p[0], { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(p[1]) });
    });
  }, Promise.resolve()).then(function () {
    env.primeCalls = calls.length;
    return env;
  });
}

// The runtime: one gridBatch call at a time, the clock moved only by the waits it is told to make.
function drive(env, plan, o) {
  const st = { done: (o && o.done) || [], keyMap: Object.assign({}, (o && o.keyMap) || {}), clock: 1000000,
    statuses: [], rowStarts: [], log: [], stop: null, final: null };
  function step(n) {
    if (n > 200) { st.stop = { reason: 'DRIVER_RUNAWAY' }; return Promise.resolve(st); }
    return env.sandbox.window.gridBatch(plan, { dryRun: false, done: st.done, keyMap: st.keyMap,
      ids: (o && o.ids) || BATCH_IDS, now: st.clock }).then(function (res) {
      st.statuses.push(res.status || res.reason);
      if (res.log) st.log.push(res.log);
      if (res.ok === false) { st.stop = res; return st; }
      if (res.status === 'DONE') { st.final = res; return st; }
      if (res.status === 'PACE' || res.status === 'BACKOFF') {
        st.clock += res.waitMs;
        return step(n + 1);
      }
      if (res.status === 'HANDOFF') {
        if (res.step === 'COPY' && !st.keyMap[res.product_key]) {   // the UI copy creates the item
          env.db[9500] = rec(9500, { StrainId: 101, Price: 11, Cost: 4.5, Flavor: '', BrandId: 5101 });
          st.keyMap[res.product_key] = 9500;
        }
        st.done.push(String(res.seq));
        return step(n + 1);
      }
      st.rowStarts.push(st.clock);
      st.done.push(String(res.seq));
      return step(n + 1);
    });
  }
  return step(0);
}

function batchCalls(env, what) {
  return env.calls.slice(env.primeCalls).filter(function (c) { return c.url.indexOf(what) >= 0; });
}

function batchCases() {
  let plan;
  return batchEnv().then(function (env) {
    // the cross-language hash and the dry run
    eq(env.sandbox.window.gridPlanRowSha1(SHA_VECTOR.row), SHA_VECTOR.sha,
      'batch — row_sha1 in the page equals intake_plan.py on the shared vector (U+001F join, UTF-8)');
    plan = batchPlan(env.sandbox.window.gridPlanRowSha1);
    return env.sandbox.window.gridBatch(plan, { ids: BATCH_IDS }).then(function (r) {
      eq(r.ok, true, 'batch dry run — ok (dryRun is the default)' + (r.ok ? '' : ' [' + r.reason + ']'));
      eq(r.planned, 5, 'batch dry run — N = 5 planned grid writes');
      eq(r.handoff, 2, 'batch dry run — 2 UI rows handed off');
      eq(r.refusals, 0, 'batch dry run — 0 refusals');
      eq(env.calls.length - env.primeCalls, 0, 'batch dry run — zero requests of any kind');
    });
  }).then(function () {
    return batchEnv();
  }).then(function (env) {
    return drive(env, plan).then(function (st) {
      eq(st.stop, null, 'batch live — runs to DONE with no stop' + (st.stop ? ' [' + st.stop.reason + ': ' + st.stop.detail + ']' : ''));
      const applied = batchCalls(env, 'update-products-multiple').filter(function (c) { return c.applied; });
      eq(applied.length, 5, 'batch live — N = 5 writes');
      eq(batchCalls(env, 'get-product-details-v2').length, 5, 'batch live — one guard read per grid row');
      eq(batchCalls(env, 'get-product-master').length, 0, 'batch live — NO per-item read-back (no catalog read at all)');
      eq(JSON.stringify(applied[0].body.FieldList), '[{"StrainId":103}]',
        'batch live — the new item\'s strain is resolved by NAME to the one live record id');
      eq(applied[0].body.ProductList[0], 9500, 'batch live — `new:2` resolved through the keyMap the COPY step filled');
      eq(JSON.stringify(applied[3].body.FieldList), '[{"BrandId":5101}]', 'batch live — BrandId from opts.ids, a NUMBER');
      eq(JSON.stringify(applied[1].body.FieldList), '[{"Price":18}]', 'batch live — Price posts as a NUMBER');
      eq(Object.keys(applied[1].body).sort().join(','),
        'CustomerTypes,FieldList,LocId,LspId,OrgId,ProductList,SessionId,Tags,TaxCategories,UserId',
        'batch live — the write body is the KB envelope, key for key');
      const gaps = st.rowStarts.slice(1).map(function (t, i) { return t - st.rowStarts[i]; });
      ok(gaps.every(function (g) { return g >= 2000; }) && st.statuses.indexOf('PACE') >= 0,
        'batch live — paced: >= 2 s between rows (<= 30 writes / 60 requests a minute), waited in the runtime');
      ok(st.log.length === 5 && st.log.every(function (l) { return l.seq && l.status === 'WROTE' && 'live_before' in l && l.at; }),
        'batch live — a write-log line per grid row (seq, status, live before, time) for the progress JSONL');
      // the idempotent re-run on a catalog already at target
      return drive(env, plan, { keyMap: { 'new:2': 9500 } }).then(function (st2) {
        const w2 = batchCalls(env, 'update-products-multiple').length;
        eq(st2.statuses.filter(function (s) { return s === 'AT_TARGET'; }).length, 5, 'batch re-run — N AT_TARGET');
        eq(w2, 5, 'batch re-run — 0 further writes');
      });
    });
  }).then(function () {
    // an injected guard mismatch on row k = 4 (Flavor): stop AT row 4, nothing after it
    return batchEnv({ over: { 9002: { Flavor: 'Peach' } } }).then(function (env) {
      return drive(env, plan).then(function (st) {
        eq(st.stop && st.stop.reason, 'GUARD_MISMATCH', 'batch guard mismatch — the batch STOPS');
        ok(/seq 4/.test(st.stop && st.stop.detail), 'batch guard mismatch — at row k = 4');
        const ids = batchCalls(env, 'update-products-multiple').map(function (c) { return JSON.stringify(c.body.FieldList); });
        eq(ids.join(' '), '[{"StrainId":103}] [{"Price":18}]', 'batch guard mismatch — 0 writes at or after row k');
      });
    });
  }).then(function () {
    // an injected 429 on row k (the Price write, twice) and on a guard read: wait, re-read, resume
    return batchEnv({ write429: { 9002: 2 }, guard429: { 9003: 1 } }).then(function (env) {
      return drive(env, plan).then(function (st) {
        eq(st.stop, null, 'batch 429 — no stop');
        const all = batchCalls(env, 'update-products-multiple');
        const applied = all.filter(function (c) { return c.applied; });
        eq(applied.length, 5, 'batch 429 — ends with N writes applied');
        const per = {};
        applied.forEach(function (c) { const k = c.body.ProductList[0] + JSON.stringify(c.body.FieldList); per[k] = (per[k] || 0) + 1; });
        ok(Object.keys(per).every(function (k) { return per[k] === 1; }), 'batch 429 — 0 doubles');
        eq(st.statuses.filter(function (s) { return s === 'BACKOFF'; }).length >= 3, true, 'batch 429 — backed off on each 429');
        ok(st.log.some(function (l) { return l.status === 'RATE_LIMITED'; }), 'batch 429 — the 429 is logged as RATE_LIMITED (not applied)');
      });
    });
  }).then(function () {
    // refusals that fire BEFORE the first request
    const pre = [
      ['PLAN_SHA_MISMATCH', 'one edited row', function (p) { p[2].target = '17'; return p; }, false],
      ['FIELD_NOT_PROVEN', 'a VendorId row (UNPROVEN, P7) — the shared refusal set', function (p) { p[5].field = 'VendorId'; return p; }, true],
      ['FIELD_NOT_PROVEN', 'a Tags row on the grid (UNPROVEN, P4)', function (p) { p[3].field = 'Tags'; return p; }, true],
      ['VALUE_NOT_NUMERIC', 'a Cost target that will not cast', function (p) { p[5].target = '$8'; return p; }, true],
      ['CLEAR_UNPROVEN_FOR_FIELD', 'a blank Price target (a clear)', function (p) { p[2].target = ''; return p; }, true],
      ['NAME_UNRESOLVED', 'a BrandId name with no live id', function (p) { p[4].target = 'name:Brand Z'; return p; }, true],
      ['PLAN_ORDER_INVALID', 'a row out of the step order', function (p) { p[6].step = 'COPY'; return p; }, true],
    ];
    return pre.reduce(function (ch, c) {
      return ch.then(function () {
        return batchEnv().then(function (env) {
          let p = JSON.parse(JSON.stringify(plan));
          p = c[2](p);
          if (c[3]) rehash(env, p);
          return env.sandbox.window.gridBatch(p, { dryRun: false, done: [], ids: BATCH_IDS, now: 1 }).then(function (r) {
            eq(r.reason, c[0], 'batch RED ' + c[0] + ' — ' + c[1]);
            eq(env.calls.length - env.primeCalls, 0, 'batch RED ' + c[0] + ' — refused before any request');
          });
        });
      });
    }, Promise.resolve());
  }).then(function () {
    // stops raised at run time, each by one break
    const live = [
      ['NEW_KEY_UNRESOLVED', 'the COPY ran but no keyMap names the new id', {}, { done: ['1'] }],
      ['SESSION_LOST', 'a 401 on the guard read', { guard401: 9002 }, {}],
      ['MISSING_READ_CAPTURE', 'no item form was opened, so the record read was never observed', { noDetailsCapture: true }, { done: ['1'], keyMap: { 'new:2': 9001 } }],
      ['WRITE_NOT_OK', 'Result:false', { writeFalse: 9002 }, {}],
    ];
    return live.reduce(function (ch, c) {
      return ch.then(function () {
        return batchEnv(c[2]).then(function (env) {
          return drive(env, plan, c[3]).then(function (st) {
            eq(st.stop && st.stop.reason, c[0], 'batch STOP ' + c[0] + ' — ' + c[1]);
          });
        });
      });
    }, Promise.resolve());
  }).then(function () {
    // a strain the live read does not hold
    return batchEnv().then(function (env) {
      const p = rehash(env, JSON.parse(JSON.stringify(plan)).map(function (r) {
        if (r.field === 'StrainId') r.target = 'name:Strain Nowhere';
        return r;
      }));
      return drive(env, p).then(function (st) {
        eq(st.stop && st.stop.reason, 'STRAIN_ID_UNRESOLVED', 'batch STOP STRAIN_ID_UNRESOLVED — a strain absent from the live read');
        eq(batchCalls(env, 'update-products-multiple').length, 0, 'batch STOP STRAIN_ID_UNRESOLVED — 0 writes');
      });
    });
  });
}

// ---------------------------------------------------------------------------------------------

runCases(0).then(extras).then(batchCases).then(function () {
  console.log('backoffice_grid_write selftest');
  console.log('  helper: ' + HELPER);
  console.log('  ' + CASES.length + ' refusal case(s), each proven GREEN on a clean fixture and ' +
    'RED on a fixture broken in one place');
  console.log('  ' + passed + ' assertion(s)\n');
  if (!failures.length) {
    console.log('PASS — ' + passed + '/' + passed + '.');
    process.exit(0);
  }
  failures.forEach(function (f) { console.log('  FAIL  ' + f); });
  console.log('\nFAIL — ' + failures.length + ' of ' + passed + ' assertion(s).');
  process.exit(1);
}).catch(function (e) {
  console.log('backoffice_grid_write selftest');
  console.log('\nFAIL — the harness threw: ' + (e && e.stack ? e.stack : e));
  process.exit(1);
});
