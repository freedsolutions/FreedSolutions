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
    Tags: '',
  }, over || {});
}

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

// A tenant whose Strains read carries NO archive field at all, with the stop cleared deliberately.
// Observed live 2026-09-18: the read can return only StrainId / StrainName / StrainDescription /
// Abbreviation / StrainAbbreviation / StrainType / ExternalId, so "not archived" is UNPROVABLE
// there rather than false.
function cleanNoFlag() {
  const s = cleanWrite();
  s.label = 'StrainId write where the platform exposes no archive flag';
  s.strains.forEach(function (r) { delete r.IsArchived; });
  s.args.acceptNoArchiveFlag = true;
  return s;
}

// The acknowledgement must clear ONLY the unprovable check. A record the read positively reports
// as archived stays refused, ack or no ack.
function cleanAckWithFlag() {
  const s = cleanWrite();
  s.label = 'the ack is present but the platform DOES expose a flag';
  s.args.acceptNoArchiveFlag = true;
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
  { reason: 'FIELD_NOT_PROVEN', note: 'settable but no direct-call proof (Cost)',
    base: cleanWrite, brk: function (s) { s.args.field = 'Cost'; } },
  { reason: 'FIELD_NOT_PROVEN', note: 'Tags is settable but its direct-call semantics are unproven',
    base: cleanWrite, brk: function (s) { s.args.field = 'Tags'; } },

  // 2. an empty value is a CLEAR only behind the explicit flag
  { reason: 'EMPTY_VALUE_WITHOUT_CLEAR', note: 'the trap-1 write, refused',
    base: cleanWrite, brk: function (s) { s.args.value = ''; } },
  { reason: 'CLEAR_WITH_VALUE', note: 'clear flag set while a value is present',
    base: cleanWrite, brk: function (s) { s.args.clear = true; } },
  { reason: 'CLEAR_UNPROVEN_FOR_FIELD', note: 'the empty-box clear is proven on Flavor only',
    base: cleanClear, brk: function (s) { s.args.field = 'StrainId'; } },

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
  { reason: 'STRAIN_ID_UNRESOLVED', note: 'id absent from the live Strains read',
    base: cleanWrite, brk: function (s) { s.args.value = 777; } },
  { reason: 'STRAIN_ID_ARCHIVED', note: 'id resolves to an archived record',
    base: cleanWrite, brk: function (s) { s.args.value = 102; } },
  { reason: 'ARCHIVE_CHECK_UNAVAILABLE', note: 'strain rows expose no archive flag to check',
    base: cleanWrite, brk: function (s) {
      s.strains.forEach(function (r) { delete r.IsArchived; });
    } },
  { reason: 'ARCHIVE_CHECK_UNAVAILABLE', note: 'withdrawing the explicit ack restores the stop',
    base: cleanNoFlag, brk: function (s) { delete s.args.acceptNoArchiveFlag; } },
  { reason: 'STRAIN_ID_ARCHIVED', note: 'the ack must NOT override a proven-archived record',
    base: cleanAckWithFlag, brk: function (s) { s.args.value = 102; } },

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
      'archiveCheck names the field the liveness proof came from');

    // Where it cannot, the acknowledgement is carried in the result and parked in full, so a
    // cleared stop is never invisible after the fact.
    return run(cleanNoFlag());
  }).then(function (r) {
    eq(r.res.ok, true, 'ack — an acknowledged unprovable archive check completes');
    eq(r.res.archiveCheck, 'NOT PROVEN (accepted)',
      'ack — the result states that the check was NOT proven, not that it passed');
    const parked = r.sandbox.window.__gridWrite.runs[0];
    ok(/NOT proven/i.test(parked.archiveNote || ''),
      'ack — the full reason is parked with the run for the record');
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
  });
}

// ---------------------------------------------------------------------------------------------

runCases(0).then(extras).then(function () {
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
