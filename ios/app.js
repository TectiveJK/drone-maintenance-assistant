(() => {
  const APP_VERSION = "0.4.0";
  const STORAGE_KEY = "dma-ios-v1";

  const PRE_FLIGHT = [
    "Airframe condition",
    "Propellers",
    "Motors",
    "Landing gear",
    "Battery",
    "Battery contacts",
    "Payload / camera",
    "GNSS / GPS",
    "Sensors",
    "LEDs",
    "Remote controller",
    "Cables / connectors",
    "Communications",
    "Firmware",
    "Physical damage",
  ];

  const POST_FLIGHT = [
    "Airframe damage",
    "Propellers after flight",
    "Motors / abnormal noise",
    "Battery condition",
    "Battery temperature",
    "Payload / camera condition",
    "Landing gear",
    "Sensors",
    "Cables / connectors",
    "General cleanliness",
  ];

  const NAV = [
    ["dashboard", "Dashboard"],
    ["fleet", "Drone Fleet"],
    ["preflight", "Pre-Flight Inspection"],
    ["postflight", "Post-Flight Inspection"],
    ["batteries", "Batteries"],
    ["tasks", "Maintenance Tasks"],
    ["incidents", "Faults / Incidents"],
    ["reports", "Reports"],
    ["install", "Install on iOS"],
  ];

  const emptyState = () => ({
    drones: [],
    batteries: [],
    tasks: [],
    incidents: [],
    inspections: [],
    nextId: 1,
  });

  let state = load();
  let currentPanel = "dashboard";
  let modalMode = null;

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return emptyState();
      const parsed = JSON.parse(raw);
      return { ...emptyState(), ...parsed };
    } catch {
      return emptyState();
    }
  }

  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function uid() {
    const id = state.nextId++;
    save();
    return id;
  }

  function now() {
    return new Date().toISOString().slice(0, 19);
  }

  function toast(message) {
    const el = $("#toast");
    el.textContent = message;
    el.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove("show"), 2200);
  }

  function droneName(id) {
    const drone = state.drones.find((d) => d.id === id);
    return drone ? drone.name : "";
  }

  function badgeClass(value) {
    const v = String(value || "").toLowerCase();
    if (["fail", "critical", "replace"].includes(v)) return v === "fail" ? "fail" : v;
    if (["pass", "good", "resolved", "completed"].includes(v)) return v;
    if (["monitor", "high", "open"].includes(v)) return v;
    return "";
  }

  function fillDroneSelects() {
    const options =
      state.drones.length === 0
        ? `<option value="">No drones yet</option>`
        : `<option value="">Select drone</option>` +
          state.drones
            .slice()
            .sort((a, b) => a.name.localeCompare(b.name))
            .map((d) => `<option value="${d.id}">${escapeHtml(d.name)}</option>`)
            .join("");
    ["#preflightDrone", "#postflightDrone"].forEach((sel) => {
      const el = $(sel);
      const prev = el.value;
      el.innerHTML = options;
      if ([...el.options].some((o) => o.value === prev)) el.value = prev;
    });
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function renderNav() {
    const side = $("#sideNav");
    side.innerHTML = NAV.map(
      ([id, label]) =>
        `<button class="side-link${id === currentPanel ? " active" : ""}" type="button" data-nav="${id}">${label}</button>`
    ).join("");
  }

  function setPanel(id) {
    if (!NAV.some(([key]) => key === id) && id !== "more") return;
    if (id === "more") {
      $("#moreMenu").classList.toggle("open");
      return;
    }
    currentPanel = id;
    $("#moreMenu").classList.remove("open");
    $$(".panel").forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === id));
    $$(".side-link").forEach((btn) => btn.classList.toggle("active", btn.dataset.nav === id));
    const mobileMap = {
      dashboard: "dashboard",
      fleet: "fleet",
      preflight: "preflight",
      postflight: "preflight",
      batteries: "more",
      tasks: "more",
      incidents: "more",
      reports: "more",
      install: "more",
    };
    $$(".tab").forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.nav === mobileMap[id]);
    });
    if (id === "reports") renderReport();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function renderDashboard() {
    const openTasks = state.tasks.filter((t) => t.status !== "COMPLETED").length;
    const openIncidents = state.incidents.filter((i) => i.status !== "RESOLVED").length;
    const failed = state.inspections.filter((i) => i.status === "FAIL").length;
    $("#dashboardStats").innerHTML = [
      ["Drones", state.drones.length],
      ["Batteries", state.batteries.length],
      ["Open tasks", openTasks],
      ["Open incidents", openIncidents],
      ["Inspections", state.inspections.length],
      ["Failed checks", failed],
    ]
      .map(
        ([label, value]) =>
          `<div class="card stat"><strong>${value}</strong><span>${label}</span></div>`
      )
      .join("");
  }

  function renderFleet() {
    const list = $("#fleetList");
    if (!state.drones.length) {
      list.innerHTML = `<div class="card empty">No drones yet. Tap + Add Drone to register the fleet.</div>`;
      return;
    }
    list.innerHTML = state.drones
      .slice()
      .sort((a, b) => a.name.localeCompare(b.name))
      .map(
        (d) => `<article class="card item">
          <h3>${escapeHtml(d.name)}</h3>
          <p>${escapeHtml([d.manufacturer, d.model, d.serial_number].filter(Boolean).join(" · ") || "No manufacturer details")}</p>
          <p style="margin-top:8px">${escapeHtml(d.equipment || "No equipment / hardware notes")}</p>
          <div class="meta"><span class="badge">${escapeHtml(d.created_at)}</span></div>
        </article>`
      )
      .join("");
  }

  function buildInspection(containerId, items) {
    const root = $(containerId);
    root.innerHTML = items
      .map(
        (item, index) => `<div class="card inspection-item" data-index="${index}">
          <strong>${escapeHtml(item)}</strong>
          <label>Result
            <select class="result">
              <option>PASS</option>
              <option>FAIL</option>
              <option>N/A</option>
            </select>
          </label>
          <label>Notes
            <textarea class="notes" placeholder="Write notes..."></textarea>
          </label>
        </div>`
      )
      .join("");
  }

  function collectInspection(containerId, items) {
    return $$(`${containerId} .inspection-item`).map((row, index) => ({
      item_name: items[index],
      result: $(".result", row).value,
      notes: $(".notes", row).value.trim(),
    }));
  }

  function saveInspection(kind, droneSelectId, containerId, items) {
    const droneId = Number($(droneSelectId).value);
    if (!droneId) {
      toast("Please select a drone first.");
      return;
    }
    const results = collectInspection(containerId, items);
    const status = results.some((r) => r.result === "FAIL") ? "FAIL" : "PASS";
    state.inspections.unshift({
      id: uid(),
      drone_id: droneId,
      inspection_type: kind,
      status,
      notes: "",
      items: results,
      created_at: now(),
    });
    save();
    toast(`${kind} inspection saved as ${status}.`);
    renderAll();
    $$(`${containerId} .result`).forEach((el) => (el.value = "PASS"));
    $$(`${containerId} .notes`).forEach((el) => (el.value = ""));
  }

  function renderBatteries() {
    const list = $("#batteryList");
    if (!state.batteries.length) {
      list.innerHTML = `<div class="card empty">No batteries recorded yet.</div>`;
      return;
    }
    list.innerHTML = state.batteries
      .map(
        (b) => `<article class="card item">
          <h3>${escapeHtml(b.battery_id)}</h3>
          <p>${escapeHtml(droneName(b.drone_id) || "No drone assigned")} · ${escapeHtml(b.cycles)} cycles · ${escapeHtml(b.voltage || "—")} V</p>
          <div class="meta">
            <span class="badge ${badgeClass(b.health)}">${escapeHtml(b.health)}</span>
            <span class="badge">${escapeHtml(b.created_at)}</span>
          </div>
          ${b.notes ? `<p style="margin-top:8px">${escapeHtml(b.notes)}</p>` : ""}
        </article>`
      )
      .join("");
  }

  function renderTasks() {
    const list = $("#taskList");
    if (!state.tasks.length) {
      list.innerHTML = `<div class="card empty">No maintenance tasks yet.</div>`;
      return;
    }
    list.innerHTML = state.tasks
      .map(
        (t) => `<article class="card item">
          <h3>${escapeHtml(t.task)}</h3>
          <p>${escapeHtml(droneName(t.drone_id))} · due ${escapeHtml(t.due_date || "—")}</p>
          <div class="meta">
            <span class="badge ${badgeClass(t.priority)}">${escapeHtml(t.priority)}</span>
            <span class="badge ${badgeClass(t.status)}">${escapeHtml(t.status)}</span>
          </div>
          ${t.notes ? `<p style="margin-top:8px">${escapeHtml(t.notes)}</p>` : ""}
          <div class="toolbar" style="margin-top:12px;margin-bottom:0">
            <button class="btn danger" type="button" data-delete-task="${t.id}">Delete Task</button>
          </div>
        </article>`
      )
      .join("");
  }

  function renderIncidents() {
    const list = $("#incidentList");
    if (!state.incidents.length) {
      list.innerHTML = `<div class="card empty">No faults or incidents yet.</div>`;
      return;
    }
    list.innerHTML = state.incidents
      .map(
        (i) => `<article class="card item">
          <h3>${escapeHtml(i.title)}</h3>
          <p>${escapeHtml(droneName(i.drone_id))}</p>
          <div class="meta">
            <span class="badge ${badgeClass(i.severity)}">${escapeHtml(i.severity)}</span>
            <span class="badge ${badgeClass(i.status)}">${escapeHtml(i.status)}</span>
            <span class="badge">${escapeHtml(i.created_at)}</span>
          </div>
          ${i.description ? `<p style="margin-top:8px">${escapeHtml(i.description)}</p>` : ""}
          ${i.action_taken ? `<p style="margin-top:8px"><strong>Action:</strong> ${escapeHtml(i.action_taken)}</p>` : ""}
        </article>`
      )
      .join("");
  }

  function reportText() {
    const openTasks = state.tasks.filter((t) => t.status !== "COMPLETED").length;
    const openIncidents = state.incidents.filter((i) => i.status !== "RESOLVED").length;
    const failed = state.inspections.filter((i) => i.status === "FAIL").length;
    return [
      "DRONE MAINTENANCE REPORT",
      `Version: ${APP_VERSION}`,
      `Generated: ${now()}`,
      "",
      "Fleet",
      `- Drones: ${state.drones.length}`,
      `- Batteries: ${state.batteries.length}`,
      "",
      "Maintenance",
      `- Tasks: ${state.tasks.length}`,
      `- Open / active tasks: ${openTasks}`,
      "",
      "Faults / Incidents",
      `- Total incidents: ${state.incidents.length}`,
      `- Open / investigating incidents: ${openIncidents}`,
      "",
      "Inspections",
      `- Total inspections: ${state.inspections.length}`,
      `- Failed inspections: ${failed}`,
    ].join("\n");
  }

  function renderReport() {
    $("#reportText").textContent = reportText();
  }

  function renderAll() {
    fillDroneSelects();
    renderDashboard();
    renderFleet();
    renderBatteries();
    renderTasks();
    renderIncidents();
    renderReport();
  }

  function droneOptions(required) {
    const blank = required ? "Select drone" : "No drone assigned";
    return (
      `<option value="">${blank}</option>` +
      state.drones
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name))
        .map((d) => `<option value="${d.id}">${escapeHtml(d.name)}</option>`)
        .join("")
    );
  }

  function openModal(mode) {
    modalMode = mode;
    const title = {
      drone: "Add Drone",
      battery: "Add Battery",
      task: "Add Maintenance Task",
      incident: "Add Fault / Incident",
    }[mode];
    $("#modalTitle").textContent = title;
    const body = $("#modalBody");
    if (mode === "drone") {
      body.innerHTML = `
        <label>Drone name *<input id="f-name" required /></label>
        <label>Manufacturer<input id="f-man" /></label>
        <label>Model<input id="f-model" /></label>
        <label>Serial number<input id="f-serial" /></label>
        <label>Equipment / Hardware<textarea id="f-equipment"></textarea></label>
        <label>Notes<textarea id="f-notes" placeholder="Write notes..."></textarea></label>`;
    } else if (mode === "battery") {
      body.innerHTML = `
        <label>Battery ID *<input id="f-bid" required /></label>
        <label>Drone<select id="f-drone">${droneOptions(false)}</select></label>
        <label>Cycles<input id="f-cycles" type="number" min="0" value="0" /></label>
        <label>Voltage<input id="f-voltage" /></label>
        <label>Health<select id="f-health"><option>Good</option><option>Monitor</option><option>Replace</option></select></label>
        <label>Notes<textarea id="f-notes" placeholder="Write notes..."></textarea></label>`;
    } else if (mode === "task") {
      body.innerHTML = `
        <label>Drone *<select id="f-drone">${droneOptions(true)}</select></label>
        <label>Task *<input id="f-task" required /></label>
        <label>Priority<select id="f-priority"><option>LOW</option><option selected>NORMAL</option><option>HIGH</option><option>CRITICAL</option></select></label>
        <label>Status<select id="f-status"><option>OPEN</option><option>IN PROGRESS</option><option>COMPLETED</option></select></label>
        <label>Due date<input id="f-due" type="date" value="${new Date().toISOString().slice(0, 10)}" /></label>
        <label>Notes<textarea id="f-notes" placeholder="Write notes..."></textarea></label>`;
    } else if (mode === "incident") {
      body.innerHTML = `
        <label>Drone *<select id="f-drone">${droneOptions(true)}</select></label>
        <label>Title *<input id="f-title" required /></label>
        <label>Severity<select id="f-severity"><option>LOW</option><option selected>MEDIUM</option><option>HIGH</option><option>CRITICAL</option></select></label>
        <label>Description<textarea id="f-desc" placeholder="Describe the fault or incident..."></textarea></label>
        <label>Action Taken<textarea id="f-action" placeholder="Action taken..."></textarea></label>
        <label>Status<select id="f-status"><option>OPEN</option><option>INVESTIGATING</option><option>RESOLVED</option></select></label>`;
    }
    const backdrop = $("#modalBackdrop");
    backdrop.hidden = false;
    backdrop.classList.add("open");
  }

  function closeModal() {
    modalMode = null;
    const backdrop = $("#modalBackdrop");
    backdrop.classList.remove("open");
    backdrop.hidden = true;
  }

  function saveModal() {
    if (modalMode === "drone") {
      const name = $("#f-name").value.trim();
      if (!name) return toast("Drone name is required.");
      state.drones.push({
        id: uid(),
        name,
        manufacturer: $("#f-man").value.trim(),
        model: $("#f-model").value.trim(),
        serial_number: $("#f-serial").value.trim(),
        equipment: $("#f-equipment").value.trim(),
        notes: $("#f-notes").value.trim(),
        created_at: now(),
      });
    } else if (modalMode === "battery") {
      const battery_id = $("#f-bid").value.trim();
      if (!battery_id) return toast("Battery ID is required.");
      const droneVal = $("#f-drone").value;
      state.batteries.unshift({
        id: uid(),
        drone_id: droneVal ? Number(droneVal) : null,
        battery_id,
        cycles: Number($("#f-cycles").value || 0),
        voltage: $("#f-voltage").value.trim(),
        health: $("#f-health").value,
        notes: $("#f-notes").value.trim(),
        created_at: now(),
      });
    } else if (modalMode === "task") {
      const drone_id = Number($("#f-drone").value);
      const task = $("#f-task").value.trim();
      if (!drone_id || !task) return toast("Drone and task are required.");
      state.tasks.unshift({
        id: uid(),
        drone_id,
        task,
        priority: $("#f-priority").value,
        status: $("#f-status").value,
        due_date: $("#f-due").value,
        notes: $("#f-notes").value.trim(),
        created_at: now(),
      });
    } else if (modalMode === "incident") {
      const drone_id = Number($("#f-drone").value);
      const title = $("#f-title").value.trim();
      if (!drone_id || !title) return toast("Drone and title are required.");
      state.incidents.unshift({
        id: uid(),
        drone_id,
        title,
        severity: $("#f-severity").value,
        description: $("#f-desc").value.trim(),
        action_taken: $("#f-action").value.trim(),
        status: $("#f-status").value,
        created_at: now(),
      });
    }
    save();
    closeModal();
    renderAll();
    toast("Saved.");
  }

  async function shareReport() {
    const text = reportText();
    $("#reportText").textContent = text;
    if (navigator.share) {
      try {
        await navigator.share({ title: "Drone Maintenance Report", text });
        return;
      } catch {
        /* user cancelled or share failed — fall through */
      }
    }
    try {
      await navigator.clipboard.writeText(text);
      toast("Report copied to clipboard.");
    } catch {
      toast("Could not share or copy the report.");
    }
  }

  function bind() {
    document.addEventListener("click", (event) => {
      const nav = event.target.closest("[data-nav]");
      if (nav) {
        setPanel(nav.dataset.nav);
        return;
      }
      const open = event.target.closest("[data-open]");
      if (open) {
        openModal(open.dataset.open);
        return;
      }
      const del = event.target.closest("[data-delete-task]");
      if (del) {
        const id = Number(del.dataset.deleteTask);
        const task = state.tasks.find((t) => t.id === id);
        if (!task) return;
        if (!confirm(`Delete the selected task?\n${task.task}`)) return;
        state.tasks = state.tasks.filter((t) => t.id !== id);
        save();
        renderAll();
        toast("Task deleted.");
      }
    });

    $("#modalCancel").addEventListener("click", closeModal);
    $("#modalSave").addEventListener("click", saveModal);
    $("#modalBackdrop").addEventListener("click", (event) => {
      if (event.target === $("#modalBackdrop")) closeModal();
    });
    $("#savePreflight").addEventListener("click", () =>
      saveInspection("Pre-Flight", "#preflightDrone", "#preflightItems", PRE_FLIGHT)
    );
    $("#savePostflight").addEventListener("click", () =>
      saveInspection("Post-Flight", "#postflightDrone", "#postflightItems", POST_FLIGHT)
    );
    $("#refreshReport").addEventListener("click", () => {
      renderReport();
      toast("Report refreshed.");
    });
    $("#shareReport").addEventListener("click", shareReport);
    $("#installHelpBtn").addEventListener("click", () => setPanel("install"));
  }

  function registerWorker() {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("./sw.js").catch(() => {});
  }

  renderNav();
  buildInspection("#preflightItems", PRE_FLIGHT);
  buildInspection("#postflightItems", POST_FLIGHT);
  bind();
  renderAll();
  setPanel("dashboard");
  registerWorker();
})();
