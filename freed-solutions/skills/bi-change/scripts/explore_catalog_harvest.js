// explore_catalog_harvest.js — the COMPLETE explore / view / field catalog of the Looker model, read from
// the embed session's internal API. Runs INSIDE the page (leaflogix.looker.com/embed/preload) through
// Playwright `browser_evaluate` with `filename` (the saved file is double-encoded: JSON.parse twice), or
// through the Browser pane's javascript_tool (a large result spills to a tool-results file on disk).
// Read-only. Output shape:
//   { harvested_at, model, explore_count, explores: [ { name, label, views: [..],
//       dimensions: [{name,label,type,view,hidden,description}], measures: [..], filters: [..] } ] }
// The two headers are mandatory — a bare fetch is a silent 403 with an empty body.
async () => {
  const h = { 'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content, 'X-Requested-With': 'XMLHttpRequest' };
  const get = async (u) => { const r = await fetch(u, { credentials: 'include', headers: h }); if (!r.ok) throw new Error(u + ' -> ' + r.status); return r.json(); };
  const base = '/api/internal/core/4.0/lookml_models/sql_server';
  const model = await get(base);
  const pick = (f) => ({ name: f.name, label: f.label || f.label_short || '', type: f.type || '', view: f.view || (f.name || '').split('.')[0], hidden: !!f.hidden, description: f.description || '' });
  const out = { harvested_at: new Date().toISOString(), model: 'sql_server', explore_count: (model.explores || []).length, explores: [] };
  for (const e of model.explores || []) {
    const x = await get(base + '/explores/' + e.name);
    const dims = (x.fields && x.fields.dimensions) || [], meas = (x.fields && x.fields.measures) || [], filt = (x.fields && x.fields.filters) || [];
    out.explores.push({ name: x.name, label: x.label || e.label || '', views: [...new Set([...dims, ...meas].map(f => f.view || (f.name || '').split('.')[0]))].sort(),
      dimensions: dims.map(pick), measures: meas.map(pick), filters: filt.map(pick) });
  }
  return JSON.stringify(out);
}
