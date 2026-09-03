const $ = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function formatConf(n) {
  const value = Number(n);
  if (Number.isNaN(value)) return "—";
  return `${Math.round(value * 100)}%`;
}

function confClass(n) {
  return Number(n) < 0.9 ? "conf-low" : "conf-high";
}

function byConfidence(a, b) {
  return (Number(a.confidence) || 1) - (Number(b.confidence) || 1);
}

function isPending(field) {
  const st = field.review?.status || "pending";
  return st === "pending";
}

function looksNumeric(value) {
  const v = String(value || "").trim();
  return /^\$[\d,]+(?:\.\d+)?$/.test(v) || /^\d+(?:\.\d+)?%$/.test(v);
}

function isNumericField(field) {
  const kind = field.kind || "";
  if (["money", "oc_ratio", "number", "amount", "percent"].includes(kind)) return true;
  if (kind) return false;
  return looksNumeric(field.value) || looksNumeric(field.review?.value);
}

function isNumericPending(field) {
  return isNumericField(field) && isPending(field);
}
let currentDoc = null;
let currentPage = 1;
let pageCount = 1;
let fields = [];
let selectedField = null;
let highlightCitations = [];
let lastHits = [];
let skipGraphFromDoc = false;
let dash = { totals: {}, open: [], approved: [], closed: [], documents: [] };
let dashTab = "open";

function pendingByDoc() {
  return Object.fromEntries((dash.documents || []).map((d) => [d.documentId, d.pending]));
}

function renderDocList(documents) {
  const pending = pendingByDoc();
  $("doc-list").innerHTML = documents
    .map((d) => {
      const n = pending[d.id] || 0;
      const badge = n ? `${n} open` : "cleared";
      return `<li><button type="button" data-id="${d.id}"><strong>${escapeHtml(d.title)}</strong><span class="hint">${escapeHtml(d.dealName || "")} · ${d.pages} pp · ${escapeHtml(d.documentType || "unprocessed")}</span><span class="pending-n${n ? " is-open" : ""}">${badge}</span></button></li>`;
    })
    .join("");
}

function paintDocPending() {
  const pending = pendingByDoc();
  document.querySelectorAll("#doc-list button[data-id]").forEach((btn) => {
    const n = pending[btn.dataset.id] || 0;
    let badge = btn.querySelector(".pending-n");
    if (!badge) {
      badge = document.createElement("span");
      badge.className = "pending-n";
      btn.appendChild(badge);
    }
    badge.textContent = n ? `${n} open` : "cleared";
    badge.classList.toggle("is-open", n > 0);
  });
}

function setDashTab(tab) {
  if (!["open", "approved", "closed"].includes(tab)) return;
  dashTab = tab;
  renderDashboard();
}

function renderDashboard() {
  const t = dash.totals || {};
  const stats = [
    ["open", t.open, "Open"],
    ["approved", t.approved, "Approved"],
    ["closed", t.closed, "Closed"],
    ["total", t.total, "Total"],
  ];
  $("dash-stats").innerHTML = stats
    .map(([key, n, label]) => {
      const tab = key === "total" ? "" : ` data-tab="${key}"`;
      const on = key === dashTab ? " is-on" : "";
      return `<button type="button" class="dash-stat ${key}${on}"${tab}><strong>${n ?? "—"}</strong><span>${label}</span></button>`;
    })
    .join("");
  $("mast-open").textContent = t.open ?? "—";
  $("mast-approved").textContent = t.approved ?? "—";
  $("mast-closed").textContent = t.closed ?? "—";
  document.querySelectorAll(".dash-mast button[data-tab]").forEach((btn) => {
    btn.classList.toggle("is-on", btn.dataset.tab === dashTab);
  });
  document.querySelectorAll("#dash-tabs button[data-tab]").forEach((btn) => {
    btn.classList.toggle("is-on", btn.dataset.tab === dashTab);
  });
  const items = dash[dashTab] || [];
  if (!items.length) {
    $("dash-list").innerHTML = `<p class="hint">No ${dashTab} items.</p>`;
    return;
  }
  $("dash-list").innerHTML = items
    .map((item) => {
      const on = item.fieldId === selectedField ? " is-on" : "";
      const conf = item.status === "pending" ? ` · ${formatConf(item.confidence)}` : "";
      return `<button type="button" class="dash-item${on}" data-doc="${escapeHtml(item.documentId)}" data-field="${escapeHtml(item.fieldId)}" data-page="${item.page || 1}">
        <span class="status ${item.status}">${item.status}${conf}</span>
        <strong>${escapeHtml(item.label)}</strong>
        <p class="value">${escapeHtml(item.value)}</p>
        <p class="hint">${escapeHtml(item.dealName || item.title)} · ${escapeHtml(item.title)}</p>
      </button>`;
    })
    .join("");
}

async function refreshDashboard() {
  dash = await api("/api/reviews/dashboard");
  renderDashboard();
  paintDocPending();
}

async function openDashItem(docId, fieldId, page) {
  await openDoc(docId, Number(page) || 1);
  if (fieldId && fields.some((f) => f.id === fieldId && isNumericPending(f))) {
    selectField(fieldId);
  }
}

async function loadDocs() {
  const [{ documents }, nextDash] = await Promise.all([
    api("/api/documents"),
    api("/api/reviews/dashboard"),
  ]);
  dash = nextDash;
  renderDashboard();
  renderDocList(documents);
  $("doc-list").onclick = (e) => {
    const btn = e.target.closest("button[data-id]");
    if (btn) openDoc(btn.dataset.id);
  };
  if (documents[0]) await openDoc(documents[0].id);
}

async function openDoc(id, page, quote) {
  const keepField = selectedField;
  $("doc-title").textContent = "Loading…";
  $("review-status").textContent = "Finding citations in the PDF…";
  highlightCitations = [];
  const extracted = await api(`/api/documents/${id}/extractions`);
  currentDoc = { id, title: extracted.title, filename: extracted.filename };
  fields = (Array.isArray(extracted.items) ? extracted.items : []).slice().sort(byConfidence);
  pageCount = extracted.pages || 1;
  if (quote) {
    const located = await api(`/api/locate?doc=${encodeURIComponent(id)}&q=${encodeURIComponent(quote)}`);
    highlightCitations = located.citations || [];
  }
  if (page) {
    currentPage = page;
  } else if (highlightCitations[0]) {
    currentPage = highlightCitations[0].page;
  } else {
    currentPage = fields.filter(isNumericPending)[0]?.citations?.[0]?.page || 1;
  }
  const pending = fields.filter(isNumericPending);
  if (keepField && fields.some((f) => f.id === keepField && isNumericPending(f))) {
    selectedField = keepField;
  } else {
    selectedField = pending[0]?.id || null;
  }
  $("doc-title").textContent = extracted.title || id;
  $("doc-file").textContent = `${extracted.filename || ""} · ${extracted.documentType || ""}`;
  $("review-status").textContent = pending.length
    ? `${pending.length} number${pending.length === 1 ? "" : "s"} waiting for review`
    : fields.some(isNumericField)
      ? "All numeric fields on this file have been reviewed"
      : "No numeric fields to review on this file";
  renderFields();
  renderPage();
  renderDashboard();
  if (!skipGraphFromDoc) loadGraph({ doc: id });
  if (extracted.dealId) {
    const keepPay = window.__pay?.dealId === extracted.dealId ? window.__pay.paymentDate : "";
    loadDisbursement(extracted.dealId, keepPay);
  }
}

function primaryCitations(field) {
  const cites = field.citations || [];
  if (!cites.length) return [];
  const first = cites[0];
  return cites.filter((c) => c.page === first.page && Math.abs(c.bbox.y0 - first.bbox.y0) < 0.04);
}

function renderFields() {
  const pending = fields.filter(isNumericPending);
  if (!pending.length) {
    $("field-list").innerHTML = "";
    return;
  }
  $("field-list").innerHTML = pending
    .map((f) => {
      const cite = f.citations?.[0];
      const citeLabel = cite ? `p.${cite.page} · “${f.quote}”` : "No citation found";
      const conf = formatConf(f.confidence);
      const band = confClass(f.confidence);
      return `<div class="field ${f.id === selectedField ? "is-on" : ""} pending" data-id="${f.id}">
        <div class="status pending">pending · <span class="conf ${band}">${conf}</span></div>
        <strong>${escapeHtml(f.label)}</strong>
        <p class="hint">${escapeHtml(f.group || "")}</p>
        <p class="value">${escapeHtml(f.review?.value ?? f.value)}</p>
        <button type="button" class="cite">${escapeHtml(citeLabel)}</button>
        <div class="field-actions">
          <button type="button" data-act="approve">Approve</button>
          <button type="button" class="ghost" data-act="edit">Edit</button>
        </div>
        <div class="edit-row">
          <input type="text" value="${escapeHtml(f.review?.value ?? f.value)}" />
          <button type="button" data-act="save">Save</button>
        </div>
      </div>`;
    })
    .join("");
}

function boxStyle(b) {
  const padX = 0.006;
  const padY = 0.003;
  const x0 = Math.max(0, b.x0 - padX);
  const y0 = Math.max(0, b.y0 - padY);
  const x1 = Math.min(1, b.x1 + padX);
  const y1 = Math.min(1, b.y1 + padY);
  return `left:${x0 * 100}%;top:${y0 * 100}%;width:${(x1 - x0) * 100}%;height:${(y1 - y0) * 100}%`;
}

function renderPage() {
  if (!currentDoc) return;
  $("page-label").textContent = `Page ${currentPage} of ${pageCount}`;
  $("page-img").src = `/api/documents/${currentDoc.id}/pages/${currentPage}?t=${Date.now()}`;
  const boxes = [];
  for (const field of fields) {
    if (!isNumericPending(field)) continue;
    for (const cite of primaryCitations(field).filter((c) => c.page === currentPage)) {
      boxes.push({
        fieldId: field.id,
        bbox: cite.bbox,
        label: field.label,
        confidence: cite.confidence ?? field.confidence,
        kind: "field",
      });
    }
  }
  for (const cite of highlightCitations.filter((c) => c.page === currentPage)) {
    boxes.push({
      fieldId: null,
      bbox: cite.bbox,
      label: "Search hit",
      confidence: 1,
      kind: "search",
    });
  }
  $("boxes").innerHTML = boxes
    .map((box) => {
      const on = box.fieldId === selectedField ? "is-on" : "";
      const band = box.kind === "search" ? "search" : confClass(box.confidence);
      const fieldAttr = box.fieldId ? `data-field="${box.fieldId}"` : "";
      return `<div class="bbox ${on} ${band}" ${fieldAttr} title="${escapeHtml(box.label)}" style="${boxStyle(box.bbox)}"></div>`;
    })
    .join("");
}

function selectField(id) {
  const field = fields.find((f) => f.id === id);
  if (!field) return;
  selectedField = id;
  if (field.citations?.[0]) currentPage = field.citations[0].page;
  renderFields();
  renderPage();
  renderDashboard();
  const on = document.querySelector(".bbox.is-on");
  if (on) on.scrollIntoView({ block: "center", behavior: "smooth" });
}

$("boxes").onclick = (e) => {
  const box = e.target.closest(".bbox[data-field]");
  if (box) selectField(box.dataset.field);
};

$("page-prev").onclick = () => {
  if (currentPage > 1) {
    currentPage -= 1;
    renderPage();
  }
};
$("page-next").onclick = () => {
  if (currentPage < pageCount) {
    currentPage += 1;
    renderPage();
  }
};

function markResolved(id, status, value) {
  const field = fields.find((f) => f.id === id);
  if (!field) return;
  field.review = { ...(field.review || {}), status, value: value ?? field.review?.value ?? field.value };
  const next = fields.find((f) => f.id !== id && isNumericPending(f));
  selectedField = next?.id || id;
  renderFields();
  renderPage();
}

$("field-list").onclick = async (e) => {
  const fieldEl = e.target.closest(".field");
  if (!fieldEl) return;
  const id = fieldEl.dataset.id;
  if (e.target.classList.contains("cite") || !e.target.closest("button, input")) {
    selectField(id);
    return;
  }
  const act = e.target.dataset.act;
  if (!act) return;
  if (act === "edit") {
    fieldEl.classList.add("editing");
    fieldEl.querySelector("input")?.focus();
    return;
  }
  try {
    if (act === "save") {
      const value = fieldEl.querySelector("input").value;
      await api(`/api/reviews/${id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "override", value }),
      });
      markResolved(id, "overridden", value);
    } else {
      await api(`/api/reviews/${id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: act }),
      });
      markResolved(id, "approved");
    }
    await openDoc(currentDoc.id, currentPage);
    await refreshDashboard();
    const question = $("question").value.trim();
    if (question && !$("answer-box").hidden) $("ask-form").requestSubmit();
  } catch (err) {
    $("review-status").textContent = err.message;
  }
};

$("dash-mast").onclick = (e) => {
  const btn = e.target.closest("button[data-tab]");
  if (btn) setDashTab(btn.dataset.tab);
};
$("dash-stats").onclick = (e) => {
  const btn = e.target.closest("button[data-tab]");
  if (btn) setDashTab(btn.dataset.tab);
};
$("dash-tabs").onclick = (e) => {
  const btn = e.target.closest("button[data-tab]");
  if (btn) setDashTab(btn.dataset.tab);
};
$("dash-list").onclick = (e) => {
  const btn = e.target.closest("button.dash-item");
  if (btn) openDashItem(btn.dataset.doc, btn.dataset.field, btn.dataset.page);
};

loadDocs().catch((err) => {
  $("review-status").textContent = err.message;
});

$("search-form").onsubmit = async (e) => {
  e.preventDefault();
  const q = $("q").value.trim();
  $("search-status").textContent = q ? "Searching…" : "";
  if (!q) {
    lastHits = [];
    $("hit-list").innerHTML = "";
    return;
  }
  try {
    const { hits, mode } = await api(`/api/search?q=${encodeURIComponent(q)}`);
    lastHits = hits;
    $("search-status").textContent = hits.length
      ? `${hits.length} hit${hits.length === 1 ? "" : "s"} · ${mode} search`
      : "No matches";
    $("hit-list").innerHTML = hits
      .map(
        (h, i) =>
          `<li><button type="button" data-idx="${i}"><strong>${escapeHtml(h.title)}</strong><span class="hint">p.${h.page}</span><p class="snippet">…${escapeHtml(h.snippet)}…</p></button></li>`
      )
      .join("");
  } catch (err) {
    $("search-status").textContent = err.message;
  }
};

$("hit-list").onclick = (e) => {
  const btn = e.target.closest("button[data-idx]");
  if (!btn) return;
  const hit = lastHits[Number(btn.dataset.idx)];
  if (hit) openDoc(hit.documentId, hit.page, $("q").value.trim());
};

function clearSearch() {
  $("q").value = "";
  lastHits = [];
  $("hit-list").innerHTML = "";
  $("search-status").textContent = "";
  highlightCitations = [];
  renderPage();
  $("q").dispatchEvent(new Event("input"));
}

$("search-clear").onclick = clearSearch;

const GRAPH_COLORS = {
  Deal: "#7a2e12",
  Obligor: "#2b4c7e",
  Manager: "#1f4d38",
  Trustee: "#6b4a1b",
  Person: "#5a5470",
  Sponsor: "#8a5a12",
  Tranche: "#6b6256",
};

const GRAPH_EDGE = {
  MANAGED_BY: "manages",
  TRUSTEED_BY: "trustee",
  HAS_PM: "PM",
  HAS_TRANCHE: "Class A",
  HOLDS: "holds",
  WATCHLIST: "watch",
  SPONSORED_BY: "sponsor",
};

function shortenName(name, max = 34) {
  const text = String(name || "");
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

const GRAPH_LAYOUT = { w: 960, h: 540 };
const GRAPH_VIEW = { w: 960, h: 540, x: 0, y: 0, scale: 1 };
const GRAPH_WEST = { Manager: 0, Trustee: 1, Person: 2, Sponsor: 3, Tranche: 4 };

function byGraphName(a, b) {
  return String(a.name || "").localeCompare(String(b.name || ""));
}

function labelSide(p, center) {
  if (p?.side && p.side !== "center") return p.side;
  const dx = p.x - (center?.x ?? GRAPH_LAYOUT.w / 2);
  const dy = p.y - (center?.y ?? GRAPH_LAYOUT.h / 2);
  if (Math.abs(dx) >= Math.abs(dy)) return dx < 0 ? "left" : "right";
  return dy < 0 ? "top" : "bottom";
}

function nodeLabelLayout(p, center) {
  const side = labelSide(p, center);
  if (side === "left") {
    return {
      name: { x: p.x - 22, y: p.y - 2, anchor: "end" },
      kind: { x: p.x - 22, y: p.y + 12, anchor: "end" },
      rel: { x: p.x + 20, y: p.y + 4, anchor: "start" },
    };
  }
  if (side === "right") {
    return {
      name: { x: p.x + 22, y: p.y - 2, anchor: "start" },
      kind: { x: p.x + 22, y: p.y + 12, anchor: "start" },
      rel: { x: p.x - 20, y: p.y + 4, anchor: "end" },
    };
  }
  if (side === "top") {
    return {
      name: { x: p.x, y: p.y - 30, anchor: "middle" },
      kind: { x: p.x, y: p.y - 16, anchor: "middle" },
      rel: { x: p.x, y: p.y + 28, anchor: "middle" },
    };
  }
  return {
    name: { x: p.x, y: p.y + 28, anchor: "middle" },
    kind: { x: p.x, y: p.y + 42, anchor: "middle" },
    rel: { x: p.x, y: p.y - 28, anchor: "middle" },
  };
}

function relationsToward(nodeId, data) {
  const labels = [];
  for (const edge of data.edges || []) {
    const touches = edge.fromId === nodeId || edge.toId === nodeId;
    const fromCenter = edge.fromId === data.center || edge.toId === data.center;
    if (touches && fromCenter) labels.push(GRAPH_EDGE[edge.label] || edge.label);
  }
  return [...new Set(labels)].join(" · ");
}

function stackColumn(list, x, cy, side, pos) {
  const gap = 74;
  const startY = cy - ((list.length - 1) * gap) / 2;
  list.forEach((node, i) => {
    pos[node.id] = { x, y: startY + i * gap, side };
  });
}

function graphPositions(centerId, nodes) {
  const cx = GRAPH_LAYOUT.w / 2;
  const cy = GRAPH_LAYOUT.h / 2;
  const center = nodes.find((n) => n.id === centerId);
  const others = nodes.filter((n) => n.id !== centerId);
  const west = [];
  const east = [];
  const north = [];
  const centerLabel = center?.label || "Deal";
  for (const node of others) {
    if (centerLabel === "Deal") {
      if (node.label === "Obligor") east.push(node);
      else if (node.label === "Tranche") north.push(node);
      else west.push(node);
    } else if (centerLabel === "Obligor") {
      if (node.label === "Sponsor") east.push(node);
      else west.push(node);
    } else if (node.label === "Deal") {
      east.push(node);
    } else if (node.label === "Obligor") {
      east.push(node);
    } else {
      west.push(node);
    }
  }
  west.sort((a, b) => (GRAPH_WEST[a.label] ?? 9) - (GRAPH_WEST[b.label] ?? 9) || byGraphName(a, b));
  east.sort(byGraphName);
  north.sort(byGraphName);
  const pos = { [centerId]: { x: cx, y: cy, side: "bottom" } };
  const westX = cx - 280;
  const eastX = cx + 280;
  stackColumn(west, westX, cy, "left", pos);
  stackColumn(east, eastX, cy, "right", pos);
  north.forEach((node, i) => {
    const spread = 180;
    pos[node.id] = {
      x: cx + (i - (north.length - 1) / 2) * spread,
      y: cy - 190,
      side: "top",
    };
  });
  return pos;
}

function mergedGraphPositions(data) {
  const auto = graphPositions(data.center, data.nodes);
  const prev = window.__graphLayout;
  if (!prev || prev.center !== data.center) {
    window.__graphLayout = { center: data.center, pos: auto };
    fitGraphView(auto, data.nodes, data.center);
    return auto;
  }
  const pos = {};
  for (const node of data.nodes) {
    pos[node.id] = prev.pos[node.id] ? { ...prev.pos[node.id] } : auto[node.id];
  }
  window.__graphLayout.pos = pos;
  return pos;
}

function fitGraphView(pos, nodes, centerId) {
  const center = pos[centerId] || { x: GRAPH_LAYOUT.w / 2, y: GRAPH_LAYOUT.h / 2 };
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const node of nodes) {
    const p = pos[node.id];
    if (!p) continue;
    const side = labelSide(p, center);
    const padX = side === "left" || side === "right" ? 190 : 150;
    const padY = 48;
    minX = Math.min(minX, p.x - (side === "left" ? padX : 28));
    maxX = Math.max(maxX, p.x + (side === "right" ? padX : 28));
    minY = Math.min(minY, p.y - padY);
    maxY = Math.max(maxY, p.y + padY);
  }
  GRAPH_VIEW.x = minX;
  GRAPH_VIEW.y = minY;
  GRAPH_VIEW.w = Math.max(640, maxX - minX);
  GRAPH_VIEW.h = Math.max(320, maxY - minY);
  GRAPH_VIEW.scale = 1;
}

function svgPoint(svg, clientX, clientY) {
  const ctm = svg.getScreenCTM();
  if (!ctm) return { x: 0, y: 0 };
  const pt = new DOMPoint(clientX, clientY).matrixTransform(ctm.inverse());
  return { x: pt.x, y: pt.y };
}

function applyGraphView(svg) {
  const w = GRAPH_VIEW.w / GRAPH_VIEW.scale;
  const h = GRAPH_VIEW.h / GRAPH_VIEW.scale;
  svg.setAttribute("viewBox", `${GRAPH_VIEW.x} ${GRAPH_VIEW.y} ${w} ${h}`);
}

function layoutStatus(data) {
  const center = data.nodes.find((n) => n.id === data.center);
  if (!center) return;
  $("graph-status").textContent = `${center.name} · ${data.nodes.length - 1} linked ${
    data.nodes.length === 2 ? "node" : "nodes"
  }. Drag nodes or the canvas to rearrange. Click a node to open the PDF.`;
}

function edgeSiblings(edges) {
  const groups = new Map();
  for (const edge of edges || []) {
    const key = [edge.fromId, edge.toId].sort().join("|");
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(edge.id);
  }
  const meta = {};
  for (const ids of groups.values()) {
    ids.forEach((id, i) => {
      meta[id] = { index: i, count: ids.length };
    });
  }
  return meta;
}

function quadPoint(a, c, b, t) {
  const u = 1 - t;
  return {
    x: u * u * a.x + 2 * u * t * c.x + t * t * b.x,
    y: u * u * a.y + 2 * u * t * c.y + t * t * b.y,
  };
}

function edgeGeom(a, b, index, count) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  const nx = -dy / len;
  const ny = dx / len;
  const spread = (index - (count - 1) / 2) * 56;
  const bow = spread !== 0 ? spread : 14;
  const c = { x: (a.x + b.x) / 2 + nx * bow, y: (a.y + b.y) / 2 + ny * bow };
  const t = count > 1 ? 0.74 + index * 0.1 : 0.82;
  const p = quadPoint(a, c, b, t);
  const nOff = count > 1 ? (index === 0 ? -12 : 12) : 10;
  return {
    d: `M ${a.x.toFixed(1)} ${a.y.toFixed(1)} Q ${c.x.toFixed(1)} ${c.y.toFixed(1)} ${b.x.toFixed(1)} ${b.y.toFixed(1)}`,
    lx: p.x + nx * nOff,
    ly: p.y + ny * nOff,
  };
}

function paintGraphGeometry(svg, data, pos) {
  const center = pos[data.center];
  const siblings = edgeSiblings(data.edges);
  svg.querySelectorAll("path.g-edge").forEach((line) => {
    const edge = (data.edges || []).find((item) => item.id === line.dataset.edge);
    if (!edge) return;
    const a = pos[edge.fromId];
    const b = pos[edge.toId];
    if (!a || !b) return;
    const sib = siblings[edge.id] || { index: 0, count: 1 };
    const geom = edgeGeom(a, b, sib.index, sib.count);
    line.setAttribute("d", geom.d);
  });
  svg.querySelectorAll("g.g-node").forEach((g) => {
    const p = pos[g.dataset.id];
    if (!p) return;
    const circle = g.querySelector("circle");
    const lab = nodeLabelLayout(p, center);
    circle.setAttribute("cx", p.x);
    circle.setAttribute("cy", p.y);
    const name = g.querySelector("text.g-name");
    const kind = g.querySelector("text.g-kind");
    const rel = g.querySelector("text.g-rel");
    if (name) {
      name.setAttribute("x", lab.name.x);
      name.setAttribute("y", lab.name.y);
      name.setAttribute("text-anchor", lab.name.anchor);
    }
    if (kind) {
      kind.setAttribute("x", lab.kind.x);
      kind.setAttribute("y", lab.kind.y);
      kind.setAttribute("text-anchor", lab.kind.anchor);
    }
    if (rel) {
      rel.setAttribute("x", lab.rel.x);
      rel.setAttribute("y", lab.rel.y);
      rel.setAttribute("text-anchor", lab.rel.anchor);
    }
  });
}

function renderGraph(data) {
  const svg = $("graph-svg");
  if (!svg || !data?.nodes?.length) return;
  const pos = mergedGraphPositions(data);
  applyGraphView(svg);
  const siblings = edgeSiblings(data.edges);
  const lines = (data.edges || [])
    .map((edge) => {
      const a = pos[edge.fromId];
      const b = pos[edge.toId];
      if (!a || !b) return "";
      const sib = siblings[edge.id] || { index: 0, count: 1 };
      const geom = edgeGeom(a, b, sib.index, sib.count);
      return `<path class="g-edge" data-edge="${escapeHtml(edge.id)}" d="${geom.d}"></path>`;
    })
    .join("");
  const centerPos = pos[data.center];
  const dots = data.nodes
    .map((node) => {
      const p = pos[node.id];
      if (!p) return "";
      const color = GRAPH_COLORS[node.label] || "#1c1914";
      const on = node.id === data.center ? " is-center" : "";
      const lab = nodeLabelLayout(p, centerPos);
      const r = node.id === data.center ? 18 : 12;
      const rel = node.id === data.center ? "" : relationsToward(node.id, data);
      const relText = rel
        ? `<text class="g-rel" x="${lab.rel.x}" y="${lab.rel.y}" text-anchor="${lab.rel.anchor}">${escapeHtml(rel)}</text>`
        : "";
      return `<g class="g-node${on}" data-id="${escapeHtml(node.id)}" data-doc="${escapeHtml(node.documentId || "")}" data-query="${escapeHtml(node.query || "")}">
        <title>${escapeHtml(node.name)}${rel ? ` · ${rel}` : ""}</title>
        <circle cx="${p.x}" cy="${p.y}" r="${r}" fill="#fff" stroke="${color}"></circle>
        <text class="g-name" x="${lab.name.x}" y="${lab.name.y}" text-anchor="${lab.name.anchor}">${escapeHtml(shortenName(node.name))}</text>
        <text class="g-kind" x="${lab.kind.x}" y="${lab.kind.y}" text-anchor="${lab.kind.anchor}">${escapeHtml(node.label)}</text>
        ${relText}
      </g>`;
    })
    .join("");
  svg.innerHTML = `<g class="g-edges">${lines}</g><g class="g-nodes">${dots}</g>`;
  layoutStatus(data);
}

async function loadGraph(opts) {
  const params = new URLSearchParams();
  if (opts.node) params.set("node", opts.node);
  if (opts.doc) params.set("doc", opts.doc);
  try {
    const data = await api(`/api/graph/neighborhood?${params}`);
    window.__graph = data;
    renderGraph(data);
    const center = (data.nodes || []).find((n) => n.id === data.center);
    if (center?.label === "Deal" && center.dealId) loadDisbursement(center.dealId);
  } catch (err) {
    $("graph-status").textContent = err.message;
  }
}

async function loadDisbursement(dealId, pay) {
  if (!dealId) return;
  const params = new URLSearchParams();
  if (pay) params.set("pay", pay);
  try {
    const data = await api(`/api/deals/${encodeURIComponent(dealId)}/disbursement?${params}`);
    window.__pay = data;
    renderDisbursement(data);
  } catch (err) {
    $("pay-panel").hidden = false;
    $("pay-status").textContent = err.message;
  }
}

function renderDisbursement(data) {
  const panel = $("pay-panel");
  panel.hidden = false;
  const tests = [
    data.ocPass ? "Class A/B OC passed" : "Class A/B OC failed",
    data.icPass ? "Class A/B IC passed" : "Class A/B IC failed",
    data.diversionPass ? "diversion passed" : "diversion failed",
  ].join(" · ");
  const redirect = data.redirect
    ? " Remaining interest is redirected to Class A principal until the coverage test is cured."
    : " Interest pays sequentially through Class E, then residual to the subordinated notes.";
  const hitl = data.ocSource === "overridden" || data.ocSource === "approved" || data.classASource === "overridden" || data.classASource === "approved"
    ? " OC/par inputs include human review."
    : "";
  $("pay-status").textContent = `${data.series} · payment ${data.paymentDateDisplay} · ${data.days} days Actual/${data.dayCount} · SOFR ${data.sofrDisplay}. ${tests}.${redirect}${hitl}`;
  $("pay-dates").innerHTML = (data.schedule || [])
    .map((row) => {
      const on = row.selected ? " is-on" : "";
      const flag = row.redirect ? " redirect" : "";
      return `<button type="button" class="pay-date${on}${flag}" data-deal="${escapeHtml(data.dealId)}" data-pay="${escapeHtml(row.paymentDate)}">${escapeHtml(row.paymentDateDisplay.replace(/ \d{4}$/, ""))}<span>${row.redirect ? "redirect" : row.residualDisplay}</span></button>`;
    })
    .join("");
  const noteRows = (data.notes || [])
    .map(
      (n) => `<tr>
        <td>Class ${escapeHtml(n.cls)}</td>
        <td>${escapeHtml(n.parDisplay)}</td>
        <td>${escapeHtml(n.spreadDisplay)}</td>
        <td>${escapeHtml(n.allInDisplay)}</td>
        <td>${escapeHtml(n.dueDisplay)}</td>
      </tr>`
    )
    .join("");
  const collRows = (data.collections || [])
    .map((c) => `<tr><td>${escapeHtml(c.name)}</td><td>${escapeHtml(c.parDisplay)}</td><td>${escapeHtml(c.amountDisplay)}</td></tr>`)
    .join("");
  const stepRows = (data.steps || [])
    .map((s) => {
      const extra = s.deferred ? ` deferred ${escapeHtml(s.deferredDisplay)}` : s.shortfall ? ` shortfall ${escapeHtml(s.shortfallDisplay)}` : "";
      return `<tr class="kind-${escapeHtml(s.kind)}"><td>${escapeHtml(s.label)}</td><td>${escapeHtml(s.dueDisplay)}</td><td>${escapeHtml(s.paidDisplay)}</td><td>${escapeHtml(extra)}</td></tr>`;
    })
    .join("");
  $("pay-body").innerHTML = `
    <p class="pay-formula hint">${escapeHtml(data.formula)} Collateral is modeled at target par ${escapeHtml(data.targetPar)} earning ${escapeHtml(data.assetRateDisplay)}. Trustee-reported OC ${escapeHtml(data.ocResult)} vs ${escapeHtml(data.ocTrigger)} (${escapeHtml(data.ocSource)}). Modeled IC ${escapeHtml(data.modeledIcDisplay)} vs trustee ${escapeHtml(data.icResult)}.</p>
    <div class="pay-grid">
      <div>
        <h4>Notes this period</h4>
        <table class="pay-table">
          <thead><tr><th>Tranche</th><th>Par</th><th>Spread</th><th>All-in</th><th>Interest due</th></tr></thead>
          <tbody>${noteRows}</tbody>
        </table>
      </div>
      <div>
        <h4>Interest collected</h4>
        <table class="pay-table">
          <thead><tr><th>Source</th><th>Par</th><th>Interest</th></tr></thead>
          <tbody>${collRows}<tr><th>Total</th><th></th><th>${escapeHtml(data.collectedDisplay)}</th></tr></tbody>
        </table>
      </div>
    </div>
    <h4>Waterfall</h4>
    <table class="pay-table">
      <thead><tr><th>Step</th><th>Due</th><th>Paid</th><th></th></tr></thead>
      <tbody>${stepRows}</tbody>
    </table>
  `;
}

$("pay-dates").onclick = (e) => {
  const btn = e.target.closest("button[data-pay]");
  if (!btn) return;
  loadDisbursement(btn.dataset.deal, btn.dataset.pay);
};

async function openGraphNode(g) {
  const nodeId = g.dataset.id;
  const docId = g.dataset.doc;
  const query = g.dataset.query;
  skipGraphFromDoc = true;
  try {
    await loadGraph({ node: nodeId });
    if (docId && (!currentDoc || currentDoc.id !== docId)) {
      await openDoc(docId, 1, query);
    }
  } finally {
    skipGraphFromDoc = false;
  }
}

let graphDrag = null;

$("graph-svg").addEventListener("pointerdown", (e) => {
  const svg = $("graph-svg");
  const node = e.target.closest(".g-node");
  const start = svgPoint(svg, e.clientX, e.clientY);
  if (node) {
    const pos = window.__graphLayout?.pos?.[node.dataset.id];
    graphDrag = {
      kind: "node",
      id: node.dataset.id,
      el: node,
      x: start.x,
      y: start.y,
      origX: pos?.x ?? start.x,
      origY: pos?.y ?? start.y,
      moved: false,
    };
    node.classList.add("is-dragging");
  } else {
    graphDrag = {
      kind: "pan",
      x: e.clientX,
      y: e.clientY,
      origX: GRAPH_VIEW.x,
      origY: GRAPH_VIEW.y,
      moved: false,
    };
    svg.classList.add("is-panning");
  }
  svg.setPointerCapture(e.pointerId);
  e.preventDefault();
});

$("graph-svg").addEventListener("pointermove", (e) => {
  if (!graphDrag) return;
  const svg = $("graph-svg");
  const data = window.__graph;
  if (graphDrag.kind === "node" && data && window.__graphLayout?.pos) {
    const pt = svgPoint(svg, e.clientX, e.clientY);
    const dx = pt.x - graphDrag.x;
    const dy = pt.y - graphDrag.y;
    if (Math.hypot(dx, dy) > 4) graphDrag.moved = true;
    const next = { x: graphDrag.origX + dx, y: graphDrag.origY + dy };
    next.side = labelSide(next, window.__graphLayout.pos[data.center]);
    window.__graphLayout.pos[graphDrag.id] = next;
    paintGraphGeometry(svg, data, window.__graphLayout.pos);
  } else if (graphDrag.kind === "pan") {
    if (Math.hypot(e.clientX - graphDrag.x, e.clientY - graphDrag.y) > 4) graphDrag.moved = true;
    const rect = svg.getBoundingClientRect();
    const vbW = GRAPH_VIEW.w / GRAPH_VIEW.scale;
    const vbH = GRAPH_VIEW.h / GRAPH_VIEW.scale;
    GRAPH_VIEW.x = graphDrag.origX - (e.clientX - graphDrag.x) * (vbW / rect.width);
    GRAPH_VIEW.y = graphDrag.origY - (e.clientY - graphDrag.y) * (vbH / rect.height);
    applyGraphView(svg);
  }
});

$("graph-svg").addEventListener("pointerup", async (e) => {
  const svg = $("graph-svg");
  const drag = graphDrag;
  graphDrag = null;
  svg.classList.remove("is-panning");
  svg.querySelectorAll(".g-node.is-dragging").forEach((el) => el.classList.remove("is-dragging"));
  if (!drag) return;
  if (drag.kind === "node" && !drag.moved && drag.el) {
    await openGraphNode(drag.el);
  }
});

$("graph-svg").addEventListener("pointercancel", () => {
  graphDrag = null;
  $("graph-svg").classList.remove("is-panning");
  $("graph-svg").querySelectorAll(".g-node.is-dragging").forEach((el) => el.classList.remove("is-dragging"));
});

$("graph-svg").addEventListener(
  "wheel",
  (e) => {
    e.preventDefault();
    const svg = $("graph-svg");
    const before = svgPoint(svg, e.clientX, e.clientY);
    const factor = e.deltaY < 0 ? 1.08 : 1 / 1.08;
    GRAPH_VIEW.scale = Math.min(2.4, Math.max(0.55, GRAPH_VIEW.scale * factor));
    applyGraphView(svg);
    const after = svgPoint(svg, e.clientX, e.clientY);
    GRAPH_VIEW.x += before.x - after.x;
    GRAPH_VIEW.y += before.y - after.y;
    applyGraphView(svg);
  },
  { passive: false }
);

$("graph-q").addEventListener("keydown", async (e) => {
  if (e.key !== "Enter") return;
  e.preventDefault();
  const q = $("graph-q").value.trim();
  if (!q) return;
  try {
    const { nodes } = await api(`/api/graph/suggest?q=${encodeURIComponent(q)}`);
    const hit = nodes[0];
    if (!hit) {
      $("graph-status").textContent = "No matching deal or name.";
      return;
    }
    skipGraphFromDoc = true;
    try {
      await loadGraph({ node: hit.id });
      if (hit.documentId) await openDoc(hit.documentId, 1, hit.query);
    } finally {
      skipGraphFromDoc = false;
    }
  } catch (err) {
    $("graph-status").textContent = err.message;
  }
});

function findSourceIndex(sources, title, page) {
  const t = title.trim().toLowerCase();
  const p = Number(page);
  let idx = sources.findIndex(
    (s) => Number(s.page) === p && (s.title.toLowerCase() === t || s.title.toLowerCase().includes(t) || t.includes(s.title.toLowerCase()))
  );
  if (idx < 0) idx = sources.findIndex((s) => s.title.toLowerCase() === t || s.title.toLowerCase().includes(t) || t.includes(s.title.toLowerCase()));
  if (idx < 0) idx = sources.findIndex((s) => Number(s.page) === p);
  return idx;
}

function citeButton(idx, label) {
  return `<button type="button" class="inline-cite" data-src="${idx}">${escapeHtml(label)}</button>`;
}

function splitAnswerSections(text) {
  const body = String(text || "").trim();
  const match = body.match(/^(?:executive\s+summary\s*\n+)([\s\S]+?)(?:\n+details\s*\n+)([\s\S]+)$/i);
  if (match) return { summary: match[1].trim(), detail: match[2].trim() };
  return { summary: "", detail: body };
}

function linkifyAnswer(text, sources, opts) {
  let body = text
    .trim()
    .replace(/\n+(?:sources?|references)\s*:\s*\n[\s\S]*$/i, "")
    .trim();
  const citeRe = /\[(?:(\d+)|([^\]\n]+?)(?:,\s*|\s+)p\.\s*(\d+))\]/gi;
  if (
    opts?.addCiteIfMissing !== false &&
    !citeRe.test(body) &&
    sources[0] &&
    !/cannot tell|do not contain|no passages/i.test(body)
  ) {
    body += ` [${sources[0].title}, p.${sources[0].page}]`;
  }
  citeRe.lastIndex = 0;
  let html = "";
  let last = 0;
  let match;
  while ((match = citeRe.exec(body))) {
    html += escapeHtml(body.slice(last, match.index));
    let idx = -1;
    let label = match[0];
    if (match[1]) {
      idx = Number(match[1]) - 1;
      const src = sources[idx];
      label = src ? `${src.title}, p.${src.page}` : match[0];
    } else {
      idx = findSourceIndex(sources, match[2], match[3]);
      label = `${match[2].trim()}, p.${match[3]}`;
    }
    html += idx >= 0 && sources[idx] ? citeButton(idx, label) : escapeHtml(match[0]);
    last = match.index + match[0].length;
  }
  html += escapeHtml(body.slice(last));
  return html.replaceAll("\n", "<br>");
}

function clearAsk() {
  $("question").value = "";
  $("ask-status").textContent = "";
  $("answer-text").innerHTML = "";
  $("answer-box").hidden = true;
  window.__answerSources = [];
  $("question").dispatchEvent(new Event("input"));
}

$("ask-clear").onclick = clearAsk;

$("ask-form").onsubmit = async (e) => {
  e.preventDefault();
  const question = $("question").value.trim();
  $("ask-status").textContent = question ? "Walking the knowledge graph and asking the model…" : "";
  $("answer-box").hidden = true;
  if (!question) return;
  try {
    const result = await api("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const mode = result.mode || "";
    $("ask-status").textContent = mode.startsWith("graph")
      ? "Answered from the knowledge graph and HITL-approved facts"
      : `Answered from ${mode} retrieval`;
    window.__answerSources = result.sources || [];
    const parts = splitAnswerSections(result.answer);
    $("answer-text").innerHTML = parts.summary
      ? `<p class="answer-kicker">Executive summary</p><div class="answer-summary">${linkifyAnswer(parts.summary, window.__answerSources, { addCiteIfMissing: false })}</div><p class="answer-kicker">Details</p><div class="answer-detail">${linkifyAnswer(parts.detail, window.__answerSources)}</div>`
      : `<div class="answer-detail">${linkifyAnswer(result.answer, window.__answerSources)}</div>`;
    $("answer-box").hidden = false;
    let node = result.graphNode;
    if (!node?.id) {
      const { nodes } = await api(`/api/graph/suggest?q=${encodeURIComponent(question)}`);
      node = nodes?.[0];
    }
    if (node?.id) {
      $("graph-q").value = node.name || "";
      skipGraphFromDoc = true;
      try {
        await loadGraph({ node: node.id });
      } finally {
        skipGraphFromDoc = false;
      }
    }
  } catch (err) {
    $("ask-status").textContent = err.message;
  }
};

$("answer-text").onclick = (e) => {
  const btn = e.target.closest(".inline-cite");
  if (!btn) return;
  const src = (window.__answerSources || [])[Number(btn.dataset.src)];
  if (src) openDoc(src.documentId, src.page, $("question").value.trim());
};

const SEARCH_SUGGESTIONS = [
  "Apex Industrial Holdings",
  "Helios Telecom",
  "Redwood Packaging",
  "Redrock CLO",
  "Silverlake CLO",
  "Priya Raman",
  "Meridian Credit Partners",
  "Class A/B OC trigger",
];

const ASK_SUGGESTIONS = [
  "Which CLOs hold Apex Industrial Holdings?",
  "Which six deals hold Apex, and which of them failed Class A/B OC?",
  "Did the Class A/B OC test pass in Redrock CLO 2024-3?",
  "Who is the collateral manager of Northbridge CLO 2024-1?",
  "Who is on the watchlist in Windward CLO 2025-1?",
  "What is Moody's rating for Apex Industrial?",
  "Who is the trustee of Silverlake CLO 2024-2?",
];

function suggestionPool(list, typed) {
  const t = typed.trim().toLowerCase();
  if (!t) return list;
  const prefix = list.filter((s) => s.toLowerCase().startsWith(t));
  if (prefix.length) return prefix;
  const inside = list.filter((s) => s.toLowerCase().includes(t));
  return inside.length ? inside : list;
}

function bindTabComplete(el, list, hintEl) {
  const show = () => {
    const pool = suggestionPool(list, el.value);
    const typed = el.value.trim().toLowerCase();
    const rec = pool.find((s) => s.toLowerCase() !== typed) || "";
    hintEl.textContent = rec ? `Tab to complete: ${rec}` : "";
    hintEl.hidden = !rec;
  };
  el.addEventListener("input", show);
  el.addEventListener("focus", show);
  el.addEventListener("keydown", (e) => {
    if (e.key !== "Tab") return;
    const pool = suggestionPool(list, el.value);
    if (!pool.length) return;
    e.preventDefault();
    const typed = el.value.trim().toLowerCase();
    let idx = pool.findIndex((s) => s.toLowerCase() === typed);
    if (idx < 0) {
      idx = e.shiftKey ? pool.length - 1 : 0;
    } else {
      idx = e.shiftKey ? (idx - 1 + pool.length) % pool.length : (idx + 1) % pool.length;
    }
    el.value = pool[idx];
    show();
  });
  hintEl.addEventListener("click", () => {
    const pool = suggestionPool(list, el.value);
    const typed = el.value.trim().toLowerCase();
    const rec = pool.find((s) => s.toLowerCase() !== typed) || pool[0];
    if (rec) el.value = rec;
    el.focus();
    show();
  });
  show();
}

bindTabComplete($("q"), SEARCH_SUGGESTIONS, $("search-suggest"));
bindTabComplete($("question"), ASK_SUGGESTIONS, $("ask-suggest"));
