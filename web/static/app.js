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

let currentDoc = null;
let currentPage = 1;
let pageCount = 1;
let fields = [];
let selectedField = null;

async function loadDocs() {
  const { documents } = await api("/api/documents");
  $("doc-list").innerHTML = documents
    .map(
      (d) =>
        `<li><button type="button" data-id="${d.id}"><strong>${escapeHtml(d.title)}</strong><span class="hint">${d.pages} pp · ${escapeHtml(d.documentType || "unprocessed")}</span></button></li>`
    )
    .join("");
  $("doc-list").onclick = (e) => {
    const btn = e.target.closest("button[data-id]");
    if (btn) openDoc(btn.dataset.id);
  };
  if (documents[0]) await openDoc(documents[0].id);
}

async function openDoc(id, page) {
  const keepField = selectedField;
  $("doc-title").textContent = "Loading…";
  $("review-status").textContent = "Finding citations in the PDF…";
  const extracted = await api(`/api/documents/${id}/extractions`);
  currentDoc = { id, title: extracted.title, filename: extracted.filename };
  fields = Array.isArray(extracted.items) ? extracted.items : [];
  pageCount = extracted.pages || 1;
  currentPage = page || fields[0]?.citations?.[0]?.page || 1;
  selectedField = fields.some((f) => f.id === keepField) ? keepField : fields[0]?.id || null;
  $("doc-title").textContent = extracted.title || id;
  $("doc-file").textContent = `${extracted.filename || ""} · ${extracted.documentType || ""}`;
  $("review-status").textContent = extracted.pending
    ? `${extracted.pending} field${extracted.pending === 1 ? "" : "s"} waiting for review`
    : fields.length
      ? "All fields on this file have been reviewed"
      : "No extracted fields on this file — run python -m clo_intel run";
  renderFields();
  renderPage();
}

function primaryCitations(field) {
  const cites = field.citations || [];
  if (!cites.length) return [];
  const first = cites[0];
  return cites.filter((c) => c.page === first.page && Math.abs(c.bbox.y0 - first.bbox.y0) < 0.04);
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
      const changed = st === "overridden" && f.review.value !== f.value;
      return `${group}<div class="field ${f.id === selectedField ? "is-on" : ""} ${st}" data-id="${f.id}">
        <div class="status ${st}">${st}</div>
        <strong>${escapeHtml(f.label)}</strong>
        <p class="value">${escapeHtml(f.review?.value)}</p>
        ${changed ? `<p class="hint">extracted as ${escapeHtml(f.value)}</p>` : ""}
        <button type="button" class="cite">${escapeHtml(citeLabel)}</button>
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

function renderPage() {
  if (!currentDoc) return;
  $("page-label").textContent = `Page ${currentPage} of ${pageCount}`;
  $("page-img").src = `/api/documents/${currentDoc.id}/pages/${currentPage}?t=${Date.now()}`;
  const boxes = [];
  for (const field of fields) {
    for (const cite of primaryCitations(field).filter((c) => c.page === currentPage)) {
      boxes.push({ fieldId: field.id, bbox: cite.bbox, label: field.label });
    }
  }
  $("boxes").innerHTML = boxes
    .map((box) => {
      const on = box.fieldId === selectedField ? "is-on" : "";
      return `<div class="bbox ${on}" data-field="${box.fieldId}" title="${escapeHtml(box.label)}" style="${boxStyle(box.bbox)}"></div>`;
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

loadDocs().catch((err) => {
  $("review-status").textContent = err.message;
});
