import './style.css';

const APP_VERSION = '0.4.0';
const KEY = 'dma-ios-v1';
const PAGES = [
  ['home', 'Home'],
  ['fleet', 'Fleet'],
  ['pre', 'Pre-Flight'],
  ['post', 'Post-Flight'],
  ['batteries', 'Batteries'],
  ['tasks', 'Tasks'],
  ['incidents', 'Faults'],
  ['report', 'Reports'],
];
const PRE_FLIGHT = ['Airframe condition','Propellers','Motors','Landing gear','Battery','Battery contacts','Payload / camera','GNSS / GPS','Sensors','LEDs','Remote controller','Cables / connectors','Communications','Firmware','Physical damage'];
const POST_FLIGHT = ['Airframe damage','Propellers after flight','Motors / abnormal noise','Battery condition','Battery temperature','Payload / camera condition','Landing gear','Sensors','Cables / connectors','General cleanliness'];

const blank = () => ({
  drones: [],
  batteries: [],
  tasks: [],
  incidents: [],
  inspections: [],
});

let db = blank();
let page = 'home';
let reportCleared = false;
const app = document.querySelector('#app');

const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
const now = () => new Date().toISOString().slice(0, 19);
const today = () => now().slice(0, 10);
const esc = (v = '') => String(v).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const droneName = id => db.drones.find(d => d.id === id)?.name || 'Unknown drone';
const save = () => localStorage.setItem(KEY, JSON.stringify(db));
const load = () => {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY));
    if (parsed && Array.isArray(parsed.drones)) db = { ...blank(), ...parsed };
  } catch {}
};

const field = (label, id, value = '', type = 'input', placeholder = '') =>
  `<label>${label}${type === 'textarea'
    ? `<textarea id="${id}" placeholder="${placeholder}">${esc(value)}</textarea>`
    : `<input id="${id}" value="${esc(value)}" placeholder="${placeholder}" />`}</label>`;
const select = (label, id, options, value = '', extra = '') =>
  `<label>${label}<select id="${id}"><option value="">${extra || 'Select...'}</option>${options.map(o => {
    const val = typeof o === 'string' ? o : o.value;
    const text = typeof o === 'string' ? o : o.label;
    return `<option value="${esc(val)}" ${String(val) === String(value) ? 'selected' : ''}>${esc(text)}</option>`;
  }).join('')}</select></label>`;
const droneOptions = () => db.drones.map(d => ({ value: d.id, label: d.name }));
const val = id => document.getElementById(id)?.value?.trim() || '';
const badge = (text, kind = '') => `<span class="badge ${kind}">${esc(text)}</span>`;

function go(next) {
  page = next;
  if (next === 'report') reportCleared = false;
  render();
}

function render() {
  app.innerHTML = `
    <header>
      <h1>Drone Maintenance Assistant</h1>
      <p>iOS version ${APP_VERSION} • Offline field maintenance</p>
    </header>
    <main>${view()}</main>
    <nav class="nav">${PAGES.map(([id, label]) => `<button class="${page === id ? 'active' : ''}" data-page="${id}">${label}</button>`).join('')}</nav>
  `;
  bind();
}

function view() {
  if (page === 'home') return homeView();
  if (page === 'fleet') return fleetView();
  if (page === 'pre') return inspectionView('Pre-Flight', PRE_FLIGHT);
  if (page === 'post') return inspectionView('Post-Flight', POST_FLIGHT);
  if (page === 'batteries') return batteriesView();
  if (page === 'tasks') return tasksView();
  if (page === 'incidents') return incidentsView();
  return reportView();
}

function homeView() {
  const openTasks = db.tasks.filter(t => t.status !== 'COMPLETED').length;
  const openIncidents = db.incidents.filter(i => i.status !== 'RESOLVED').length;
  const failed = db.inspections.filter(i => i.status === 'FAIL').length;
  return `
    <section class="card">
      <h2>Today</h2>
      <p class="muted">Use this iPhone app in the field. Data stays on this device until you share or export a report.</p>
      <div class="stats" style="margin-top:12px">
        <div class="stat"><b>${db.drones.length}</b><span>Drones</span></div>
        <div class="stat"><b>${db.batteries.length}</b><span>Batteries</span></div>
        <div class="stat"><b>${openTasks}</b><span>Open tasks</span></div>
        <div class="stat"><b>${openIncidents}</b><span>Open faults</span></div>
        <div class="stat"><b>${db.inspections.length}</b><span>Inspections</span></div>
        <div class="stat"><b>${failed}</b><span>Failed inspections</span></div>
      </div>
    </section>
    <section class="card">
      <h2>How to install</h2>
      <p class="muted">In Safari tap Share, then Add to Home Screen. The app works offline after that.</p>
    </section>
  `;
}

function fleetView() {
  return `
    <section class="card">
      <div class="row"><h2>Add drone</h2></div>
      ${field('Drone name *', 'name', '', 'input', 'Alpha')}
      <div class="grid">${field('Manufacturer', 'manufacturer')}${field('Model', 'model')}</div>
      ${field('Serial number', 'serial')}
      ${field('Equipment / Hardware', 'equipment', '', 'textarea', 'Controller, payload, radio...')}
      ${field('Notes', 'notes', '', 'textarea')}
      <div class="actions"><button id="save-drone">Save drone</button></div>
    </section>
    <section class="card">
      <h2>Fleet (${db.drones.length})</h2>
      <div class="list">${db.drones.length ? db.drones.map(d => `
        <article class="item">
          <div class="row" style="margin:0">
            <strong>${esc(d.name)}</strong>
            <button class="danger" data-del-drone="${d.id}">Delete</button>
          </div>
          <p>${esc([d.manufacturer, d.model, d.serial].filter(Boolean).join(' • ') || 'No details')}</p>
          ${d.equipment ? `<p>${esc(d.equipment)}</p>` : ''}
        </article>`).join('') : '<p class="empty">No drones yet.</p>'}
      </div>
    </section>
  `;
}

function inspectionView(kind, items) {
  const recent = db.inspections.filter(i => i.type === kind).slice(0, 8);
  return `
    <section class="card">
      <h2>${kind} inspection</h2>
      ${select('Drone *', 'droneId', droneOptions(), '', 'Select drone')}
      ${items.map((item, i) => `
        <div class="inspect-item">
          <strong>${esc(item)}</strong>
          ${select('Result', 'r' + i, ['PASS', 'FAIL', 'N/A'], 'N/A')}
          ${field('Notes', 'n' + i, '', 'textarea', 'Write notes...')}
        </div>`).join('')}
      <div class="actions"><button id="save-inspection">Save inspection</button></div>
    </section>
    <section class="card">
      <h2>Saved ${kind.toLowerCase()} inspections</h2>
      <div class="list">${recent.length ? recent.map(i => `
        <article class="item">
          <strong>${esc(droneName(i.droneId))}</strong> ${badge(i.status, i.status === 'FAIL' ? 'fail' : 'pass')}
          <p class="meta">${esc(i.createdAt)}</p>
        </article>`).join('') : '<p class="empty">None saved yet.</p>'}
      </div>
    </section>
  `;
}

function batteriesView() {
  return `
    <section class="card">
      <h2>Add battery</h2>
      ${field('Battery ID *', 'batteryId', '', 'input', 'BATT-132')}
      ${select('Drone', 'droneId', droneOptions(), '', 'No drone assigned')}
      <div class="grid">${field('Cycles', 'cycles', '0')}${field('Voltage', 'voltage')}</div>
      ${select('Health', 'health', ['Good', 'Monitor', 'Replace'], 'Good')}
      ${field('Notes', 'notes', '', 'textarea')}
      <div class="actions"><button id="save-battery">Save battery</button></div>
    </section>
    <section class="card">
      <h2>Batteries (${db.batteries.length})</h2>
      <div class="list">${db.batteries.length ? db.batteries.map(b => `
        <article class="item">
          <div class="row" style="margin:0">
            <strong>${esc(b.batteryId)}</strong>
            <button class="danger" data-del-battery="${b.id}">Delete</button>
          </div>
          <p>${esc(droneName(b.droneId))} • ${esc(b.cycles || 0)} cycles • ${esc(b.health || '')}</p>
        </article>`).join('') : '<p class="empty">No batteries yet.</p>'}
      </div>
    </section>
  `;
}

function tasksView() {
  return `
    <section class="card">
      <h2>Add task</h2>
      ${select('Drone *', 'droneId', droneOptions(), '', 'Select drone')}
      ${field('Task *', 'task', '', 'input', 'Replace props')}
      <div class="grid">${select('Priority', 'priority', ['LOW', 'NORMAL', 'HIGH', 'CRITICAL'], 'NORMAL')}${select('Status', 'status', ['OPEN', 'IN PROGRESS', 'COMPLETED'], 'OPEN')}</div>
      ${field('Due date', 'dueDate', today())}
      ${field('Notes', 'notes', '', 'textarea')}
      <div class="actions"><button id="save-task">Save task</button></div>
    </section>
    <section class="card">
      <h2>Tasks (${db.tasks.length})</h2>
      <div class="list">${db.tasks.length ? db.tasks.map(t => `
        <article class="item">
          <div class="row" style="margin:0">
            <strong>${esc(t.task)}</strong>
            <button class="danger" data-del-task="${t.id}">Delete</button>
          </div>
          <p>${esc(droneName(t.droneId))} • ${badge(t.priority, t.priority === 'CRITICAL' || t.priority === 'HIGH' ? 'high' : '')} ${badge(t.status, t.status === 'COMPLETED' ? 'completed' : '')}</p>
          <p class="meta">${esc(t.dueDate || 'No due date')} • ${esc(t.createdAt)}</p>
        </article>`).join('') : '<p class="empty">No tasks yet.</p>'}
      </div>
    </section>
  `;
}

function incidentsView() {
  return `
    <section class="card">
      <h2>Add fault / incident</h2>
      ${select('Drone *', 'droneId', droneOptions(), '', 'Select drone')}
      ${field('Title *', 'title')}
      ${select('Severity', 'severity', ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'], 'MEDIUM')}
      ${field('Description', 'description', '', 'textarea', 'Describe the fault or incident...')}
      ${field('Action taken', 'actionTaken', '', 'textarea', 'Action taken...')}
      ${select('Status', 'status', ['OPEN', 'INVESTIGATING', 'RESOLVED'], 'OPEN')}
      <div class="actions"><button id="save-incident">Save incident</button></div>
    </section>
    <section class="card">
      <h2>Faults / incidents (${db.incidents.length})</h2>
      <div class="list">${db.incidents.length ? db.incidents.map(i => `
        <article class="item">
          <div class="row" style="margin:0">
            <strong>${esc(i.title)}</strong>
            <button class="danger" data-del-incident="${i.id}">Delete</button>
          </div>
          <p>${esc(droneName(i.droneId))} • ${badge(i.severity, i.severity === 'CRITICAL' || i.severity === 'HIGH' ? 'high' : '')} ${badge(i.status, i.status === 'RESOLVED' ? 'resolved' : '')}</p>
          ${i.description ? `<p>${esc(i.description)}</p>` : ''}
        </article>`).join('') : '<p class="empty">No faults recorded yet.</p>'}
      </div>
    </section>
  `;
}

function reportText() {
  const openTasks = db.tasks.filter(t => t.status !== 'COMPLETED');
  const openIncidents = db.incidents.filter(i => i.status !== 'RESOLVED');
  const failed = db.inspections.filter(i => i.status === 'FAIL');
  const day = today();
  const todayInspections = db.inspections.filter(i => (i.createdAt || '').startsWith(day));
  const todayIncidents = db.incidents.filter(i => (i.createdAt || '').startsWith(day));
  const lines = [
    'TEST DAY REPORT',
    `Version: ${APP_VERSION} iOS`,
    `Generated: ${now()}`,
    `Date: ${day}`,
    '',
    'MAINTENANCE ASSISTANT',
    `- Drones: ${db.drones.length}`,
    `- Batteries: ${db.batteries.length}`,
    `- Tasks: ${db.tasks.length} (open / active: ${openTasks.length})`,
    `- Faults / incidents: ${db.incidents.length} (open / investigating: ${openIncidents.length})`,
    `- Inspections: ${db.inspections.length} (failed: ${failed.length})`,
    '',
    `Inspections on ${day}:`,
  ];
  if (todayInspections.length) todayInspections.forEach(i => lines.push(`- ${droneName(i.droneId)} — ${i.type} — ${i.status} — ${i.createdAt}`));
  else lines.push('- None recorded today.');
  lines.push('', `Faults / incidents on ${day}:`);
  if (todayIncidents.length) todayIncidents.forEach(i => lines.push(`- ${droneName(i.droneId)} — ${i.title} — ${i.severity} — ${i.status} — ${i.createdAt}`));
  else lines.push('- None recorded today.');
  lines.push('', 'Saved on this iPhone. Share or export JSON to copy into the Linux app / DroneTestDay folder.');
  return lines.join('\n');
}

function reportView() {
  const text = reportCleared ? '' : reportText();
  return `
    <section class="card">
      <div class="row">
        <h2>Reports</h2>
        <div class="actions">
          <button id="refresh-report" class="secondary">Refresh</button>
          <button id="share-report">Share</button>
          <button id="print-report" class="secondary">Export PDF</button>
          <button id="export-json" class="secondary">Export JSON</button>
          <button id="delete-report" class="danger">Delete report</button>
        </div>
      </div>
      <p class="muted">This is a live field report from data saved on this iPhone. It is separate from the Linux desktop database.</p>
      <div id="preview" class="preview">${text ? esc(text) : 'Report deleted. Tap Refresh to generate a new one.'}</div>
    </section>
  `;
}

function bind() {
  document.querySelectorAll('[data-page]').forEach(btn => btn.onclick = () => go(btn.dataset.page));
  document.querySelector('#save-drone')?.addEventListener('click', () => {
    if (!val('name')) return alert('Drone name is required.');
    db.drones.unshift({ id: uid(), name: val('name'), manufacturer: val('manufacturer'), model: val('model'), serial: val('serial'), equipment: val('equipment'), notes: val('notes'), createdAt: now() });
    save(); render();
  });
  document.querySelectorAll('[data-del-drone]').forEach(btn => btn.onclick = () => {
    if (!confirm('Delete this drone and its related records on this iPhone?')) return;
    const id = btn.dataset.delDrone;
    db.drones = db.drones.filter(d => d.id !== id);
    db.batteries = db.batteries.filter(b => b.droneId !== id);
    db.tasks = db.tasks.filter(t => t.droneId !== id);
    db.incidents = db.incidents.filter(i => i.droneId !== id);
    db.inspections = db.inspections.filter(i => i.droneId !== id);
    save(); render();
  });
  document.querySelector('#save-inspection')?.addEventListener('click', () => {
    const droneId = val('droneId');
    if (!droneId) return alert('Please select a drone first.');
    const kind = page === 'post' ? 'Post-Flight' : 'Pre-Flight';
    const items = (kind === 'Post-Flight' ? POST_FLIGHT : PRE_FLIGHT).map((name, i) => ({
      name, result: document.getElementById('r' + i)?.value || 'N/A', notes: document.getElementById('n' + i)?.value || '',
    }));
    const status = items.some(x => x.result === 'FAIL') ? 'FAIL' : 'PASS';
    db.inspections.unshift({ id: uid(), droneId, type: kind, status, items, createdAt: now() });
    save();
    alert(`${kind} inspection saved as ${status}.`);
    render();
  });
  document.querySelector('#save-battery')?.addEventListener('click', () => {
    if (!val('batteryId')) return alert('Battery ID is required.');
    db.batteries.unshift({ id: uid(), batteryId: val('batteryId'), droneId: val('droneId'), cycles: val('cycles') || '0', voltage: val('voltage'), health: val('health') || 'Good', notes: val('notes'), createdAt: now() });
    save(); render();
  });
  document.querySelectorAll('[data-del-battery]').forEach(btn => btn.onclick = () => {
    if (!confirm('Delete this battery?')) return;
    db.batteries = db.batteries.filter(b => b.id !== btn.dataset.delBattery);
    save(); render();
  });
  document.querySelector('#save-task')?.addEventListener('click', () => {
    if (!val('droneId') || !val('task')) return alert('Drone and task are required.');
    db.tasks.unshift({ id: uid(), droneId: val('droneId'), task: val('task'), priority: val('priority') || 'NORMAL', status: val('status') || 'OPEN', dueDate: val('dueDate'), notes: val('notes'), createdAt: now() });
    save(); render();
  });
  document.querySelectorAll('[data-del-task]').forEach(btn => btn.onclick = () => {
    if (!confirm('Delete this task?')) return;
    db.tasks = db.tasks.filter(t => t.id !== btn.dataset.delTask);
    save(); render();
  });
  document.querySelector('#save-incident')?.addEventListener('click', () => {
    if (!val('droneId') || !val('title')) return alert('Drone and title are required.');
    db.incidents.unshift({ id: uid(), droneId: val('droneId'), title: val('title'), severity: val('severity') || 'MEDIUM', description: val('description'), actionTaken: val('actionTaken'), status: val('status') || 'OPEN', createdAt: now() });
    save(); render();
  });
  document.querySelectorAll('[data-del-incident]').forEach(btn => btn.onclick = () => {
    if (!confirm('Delete this incident?')) return;
    db.incidents = db.incidents.filter(i => i.id !== btn.dataset.delIncident);
    save(); render();
  });
  document.querySelector('#refresh-report')?.addEventListener('click', () => { reportCleared = false; render(); });
  document.querySelector('#delete-report')?.addEventListener('click', () => {
    if (!confirm('Delete the report shown in this window?')) return;
    reportCleared = true; render();
  });
  document.querySelector('#print-report')?.addEventListener('click', () => { reportCleared = false; render(); window.print(); });
  document.querySelector('#share-report')?.addEventListener('click', shareReport);
  document.querySelector('#export-json')?.addEventListener('click', exportJson);
}

async function shareReport() {
  reportCleared = false;
  const text = reportText();
  if (navigator.share) {
    try { await navigator.share({ title: 'Drone Maintenance Report', text }); } catch {}
  } else {
    await navigator.clipboard?.writeText(text);
    alert('Report copied. Paste it into a note or send it to the Linux app.');
  }
}

function exportJson() {
  const payload = {
    source: 'drone-maintenance-assistant-ios',
    version: APP_VERSION,
    generated: now(),
    report_text: reportText(),
    ...db,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `test_day_report_${now().replace(/:/g, '-')}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    const sw = `${import.meta.env.BASE_URL}sw.js`;
    navigator.serviceWorker.register(sw).catch(() => {});
  });
}

load();
render();
