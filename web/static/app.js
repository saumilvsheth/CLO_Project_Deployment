const money = (n) =>
  Number(n).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

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

function show(view) {
  $("view-docs").hidden = view !== "docs";
  $("view-pay").hidden = view !== "pay";
  $("tab-docs").classList.toggle("is-on", view === "docs");
  $("tab-pay").classList.toggle("is-on", view === "pay");
}

$("tab-docs").onclick = () => show("docs");
$("tab-pay").onclick = () => {
  show("pay");
  loadBook();
};

let currentDoc = null;
let currentPage = 1;
let pageCount = 1;
let fields = [];
let selectedField = null;
let highlightCitations = [];
let lastHits = [];

async function loadDocs() {
  const { documents } = await api("/api/documents");
  $("doc-list").innerHTML = documents
    .map(
      (d) =>
        `<li><button type="button" data-id="${d.id}"><strong>${escapeHtml(d.title)}</strong><span class="hint">${d.pages} pp · ${escapeHtml(d.filename)}</span></button></li>`
    )
    .join("");
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
  const doc = await api(`/api/documents/${id}`);
  const extracted = await api(`/api/documents/${id}/extractions`);
  currentDoc = doc;
  fields = Array.isArray(extracted.items) ? extracted.items : [];
  pageCount = extracted.pages || doc.pages || 1;
  highlightCitations = [];
  if (quote) {
    const located = await api(`/api/locate?doc=${encodeURIComponent(id)}&q=${encodeURIComponent(quote)}`);
    highlightCitations = located.citations || [];
  }
  if (page) {
    currentPage = page;
  } else if (highlightCitations[0]) {
    currentPage = highlightCitations[0].page;
  } else {
    currentPage = fields[0]?.citations[0]?.page ?? 1;
  }
  selectedField = fields.some((f) => f.id === keepField) ? keepField : fields[0]?.id || null;
  $("doc-title").textContent = doc.title;
  $("doc-file").textContent = doc.filename;
  const link = $("doc-download");
  link.hidden = false;
  link.href = `/api/documents/${id}/file`;
  $("review-status").textContent = extracted.pending
    ? `${extracted.pending} field${extracted.pending === 1 ? "" : "s"} waiting for review`
    : fields.length
      ? "All fields on this file have been reviewed"
      : "No extracted fields on this file";
  renderFields();
  renderPage();
}

function renderFields() {
  let lastGroup = "";
  $("field-list").innerHTML = fields
    .map((f) => {
      const st = f.review?.status || "pending";
      const cite = f.citations?.[0];
      const citeLabel = cite ? `p.${cite.page} · “${f.quote}”` : "No citation found";
      const group =
        f.group && f.group !== lastGroup ? `<p class="eyebrow group">${escapeHtml(f.group)}</p>` : "";
      lastGroup = f.group || lastGroup;
      const changed = st === "overridden" && f.review.value !== f.extracted;
      return `${group}<div class="field ${f.id === selectedField ? "is-on" : ""} ${st}" data-id="${f.id}">
        <div class="status ${st}">${st}</div>
        <strong>${escapeHtml(f.label)}</strong>
        <p class="value">${escapeHtml(f.review?.value)}</p>
        ${changed ? `<p class="hint">extracted as ${escapeHtml(f.extracted)}</p>` : ""}
        <button type="button" class="cite" data-cite="${f.id}">${escapeHtml(citeLabel)}</button>
        <div class="field-actions">
          <button type="button" data-act="verify">Verify</button>
          <button type="button" class="ghost" data-act="edit">Edit</button>
          <button type="button" class="ghost" data-act="reject">Reject</button>
        </div>
        <div class="edit-row">
          <input type="text" value="${escapeHtml(f.review?.value)}" />
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

function primaryCitations(field) {
  const cites = field.citations || [];
  if (!cites.length) return [];
  const first = cites[0];
  return cites.filter((c) => c.page === first.page && Math.abs(c.bbox.y0 - first.bbox.y0) < 0.04);
}

function boxesOnPage() {
  const boxes = [];
  for (const field of fields) {
    const source = primaryCitations(field).filter((c) => c.page === currentPage);
    for (const cite of source) {
      boxes.push({ fieldId: field.id, bbox: cite.bbox, kind: "field", label: field.label });
    }
  }
  for (const cite of highlightCitations.filter((c) => c.page === currentPage)) {
    boxes.push({ fieldId: null, bbox: cite.bbox, kind: "search", label: "Search hit" });
  }
  return boxes;
}

function renderPage() {
  if (!currentDoc) return;
  $("page-label").textContent = `Page ${currentPage} of ${pageCount}`;
  $("page-img").src = `/api/documents/${currentDoc.id}/pages/${currentPage}?t=${Date.now()}`;
  $("boxes").innerHTML = boxesOnPage()
    .map((box) => {
      const on = box.fieldId === selectedField ? "is-on" : "";
      const kind = box.kind === "search" ? "search" : "";
      const fieldAttr = box.fieldId ? `data-field="${box.fieldId}"` : "";
      return `<div class="bbox ${on} ${kind}" ${fieldAttr} title="${escapeHtml(box.label)}" style="${boxStyle(box.bbox)}"></div>`;
    })
    .join("");
}

function selectField(id) {
  const field = fields.find((f) => f.id === id);
  if (!field) return;
  selectedField = id;
  if (field.citations[0]) currentPage = field.citations[0].page;
  renderFields();
  renderPage();
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
    } else {
      await api(`/api/reviews/${id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: act }),
      });
    }
    selectedField = id;
    await openDoc(currentDoc.id, currentPage);
  } catch (err) {
    $("review-status").textContent = err.message;
  }
};

$("search-form").onsubmit = async (e) => {
  e.preventDefault();
  const q = $("q").value.trim();
  $("search-status").textContent = q ? "Searching…" : "";
  if (!q) {
    lastHits = [];
    $("hit-list").innerHTML = "";
    return;
  }
  const { hits } = await api(`/api/search?q=${encodeURIComponent(q)}`);
  lastHits = hits;
  $("search-status").textContent = hits.length ? `${hits.length} passage${hits.length === 1 ? "" : "s"}` : "No passages";
  $("hit-list").innerHTML = hits
    .map(
      (h, i) =>
        `<li><button type="button" data-idx="${i}"><strong>${escapeHtml(h.title)}</strong><span class="hint">p.${h.page}</span><p class="snippet">…${escapeHtml(h.snippet)}…</p></button></li>`
    )
    .join("");
  $("hit-list").onclick = (e2) => {
    const btn = e2.target.closest("button[data-idx]");
    if (!btn) return;
    const hit = lastHits[Number(btn.dataset.idx)];
    if (hit) openDoc(hit.documentId, hit.page, q);
  };
};

function readAmounts() {
  const amounts = {};
  document.querySelectorAll("#ob-body input").forEach((input) => {
    amounts[input.dataset.id] = Number(input.value || 0);
  });
  return amounts;
}

function renderBook(book, preview) {
  $("pool-value").textContent = money(book.fundingRemaining);
  const rows = preview ? preview.allocations : book.obligors.map((o) => ({ ...o, proposed: 0 }));
  $("ob-body").innerHTML = rows
    .map(
      (o) => `<tr>
        <td>${o.name}${o.watch ? ' <span class="watch">watch</span>' : ""}<div class="hint">${o.sponsor} · ${o.location} · ${o.rate}</div></td>
        <td>${money(o.heldPar)}</td>
        <td>${money(o.unusedCommitment)}</td>
        <td><input data-id="${o.id}" type="number" min="0" step="1000" value="${o.proposed || 0}" /></td>
      </tr>`
    )
    .join("");
  const total = rows.reduce((s, o) => s + Number(o.proposed || 0), 0);
  $("pay-total").textContent = money(total);
  const fall = preview ? preview.noteholderWaterfall : [];
  $("waterfall").innerHTML = fall
    .map((t) => `<li><strong>${t.name}</strong> ${money(t.paid)} <span class="hint">of ${money(t.balance)}</span></li>`)
    .join("");
  const batches = book.batches || [];
  $("batches").innerHTML = batches.length
    ? batches
        .map((b) => `<li><strong>${b.id}</strong> ${money(b.total)}<div class="hint">${b.memo}</div></li>`)
        .join("")
    : "<li class='hint'>No disbursements yet.</li>";
}

async function refreshPreview() {
  $("pay-error").hidden = true;
  const preview = await api("/api/disbursements/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ amounts: readAmounts() }),
  });
  const book = await api("/api/book");
  renderBook(book, preview);
}

async function loadBook() {
  const book = await api("/api/book");
  renderBook(book);
}

$("btn-prorata").onclick = async () => {
  const book = await api("/api/book");
  const preview = await api("/api/disbursements/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ method: "prorata", pool: book.fundingRemaining }),
  });
  renderBook(book, preview);
};

$("btn-clear").onclick = () => loadBook();

$("ob-body").addEventListener("change", refreshPreview);

$("btn-confirm").onclick = async () => {
  $("pay-error").hidden = true;
  try {
    const result = await api("/api/disbursements", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amounts: readAmounts(), memo: $("memo").value }),
    });
    renderBook(result.book);
    $("memo").value = "";
  } catch (err) {
    $("pay-error").hidden = false;
    $("pay-error").textContent = err.message;
  }
};

loadDocs().catch((err) => {
  $("review-status").textContent = err.message;
});
