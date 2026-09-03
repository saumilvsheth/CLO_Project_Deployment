"""Build and backfill the CLO knowledge graph (deals, parties, obligors, tests)."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from clo_intel.review import all_reviews
from clo_intel.sample_book import DEALS, Obligor, deal_field_ids, deal_for_document, title_for_filename
from clo_intel.store import load_run, list_runs
from clo_intel.telemetry import LOG
from clo_intel.waterfall import disbursement_for_deal, format_waterfall_facts

_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    return _SLUG.sub("-", text.lower()).strip("-")[:80]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extracted_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for row in list_runs():
        run = load_run(row["documentId"])
        if not run:
            continue
        for field in run.get("extraction", {}).get("fields", []):
            values[field["id"]] = field["value"]
    return values


def _resolve(field_id: str, fallback: str, extracted: dict[str, str], reviews: dict) -> tuple[str, str]:
    review = reviews.get(field_id) or {}
    status = review.get("status", "pending")
    if status in {"approved", "overridden"} and str(review.get("value") or "").strip():
        return str(review["value"]).strip(), status
    if field_id in extracted:
        return extracted[field_id], "extracted"
    return fallback, "sample_book"


def _node(label: str, node_id: str, name: str, **props) -> dict:
    return {
        "id": node_id,
        "pk": label.lower(),
        "kind": "node",
        "label": label,
        "name": name,
        "updatedAt": _now(),
        **props,
    }


def _edge(label: str, from_id: str, to_id: str, extra_id: str = "", **props) -> dict:
    edge_id = f"e:{_slug(label)}:{extra_id}" if extra_id else f"e:{_slug(label)}:{from_id}:{to_id}"
    return {
        "id": edge_id[:80],
        "pk": "edge",
        "kind": "edge",
        "label": label,
        "fromId": from_id,
        "toId": to_id,
        "updatedAt": _now(),
        **props,
    }


def _obligor_node(item: Obligor, name: str | None = None, rating: str | None = None, source: str = "sample_book") -> dict:
    display = name or item.name
    return _node(
        "Obligor",
        f"obligor:{item.slug}",
        display,
        slug=item.slug,
        city=item.city,
        industry=item.industry,
        moodys=rating or item.moodys,
        sp=item.sp,
        source=source,
    )


def build_graph_documents(
    extracted: dict[str, str] | None = None,
    reviews: dict | None = None,
) -> list[dict]:
    extracted = extracted if extracted is not None else _extracted_values()
    reviews = reviews if reviews is not None else all_reviews()
    docs: dict[str, dict] = {}

    def put(doc: dict) -> None:
        existing = docs.get(doc["id"])
        if existing and existing.get("kind") == "node":
            existing.update({k: v for k, v in doc.items() if k not in {"id", "pk", "kind", "label"}})
            return
        docs[doc["id"]] = doc

    for deal in DEALS:
        ids = deal_field_ids(deal)
        issuer, issuer_src = _resolve(ids["deal_name"], deal.issuer, extracted, reviews)
        manager, manager_src = _resolve(ids["manager"], deal.manager, extracted, reviews)
        trustee, trustee_src = _resolve(ids["trustee"], deal.trustee, extracted, reviews)
        pm, pm_src = _resolve(ids["pm"], deal.pm, extracted, reviews)
        class_a, class_a_src = _resolve(ids["class_a_par"], deal.class_a_par, extracted, reviews)
        oc_trig, oc_trig_src = _resolve(ids["oc_trigger"], f"{deal.oc_ab_trigger}%", extracted, reviews)
        oc_res, oc_res_src = _resolve(ids["oc_result"], f"{deal.oc_ab_result}%", extracted, reviews)
        primary_name, primary_src = _resolve(ids["obligor"], deal.primary.name, extracted, reviews)
        allocation, alloc_src = _resolve(ids["allocation"], deal.primary.allocation, extracted, reviews)
        sponsor, sponsor_src = _resolve(ids["sponsor"], deal.primary.sponsor, extracted, reviews)
        rating, rating_src = _resolve(ids["rating"], deal.primary.moodys, extracted, reviews)
        watch, watch_src = _resolve(ids["watch"], next((o.name for o in deal.obligors if o.watch), "None"), extracted, reviews)

        deal_id = f"deal:{deal.id}"
        manager_id = f"manager:{_slug(manager)}"
        trustee_id = f"trustee:{_slug(trustee)}"
        pm_id = f"person:{_slug(pm)}"
        tranche_id = f"tranche:{deal.id}:a"

        put(
            _node(
                "Deal",
                deal_id,
                issuer,
                dealId=deal.id,
                series=deal.series,
                year=deal.year,
                ocTrigger=oc_trig,
                ocResult=oc_res,
                ocPass=deal.oc_ab_pass,
                icPass=deal.ic_ab_pass,
                source=issuer_src,
                fieldSources={
                    "name": issuer_src,
                    "ocTrigger": oc_trig_src,
                    "ocResult": oc_res_src,
                },
            )
        )
        put(_node("Manager", manager_id, manager, city=deal.manager_city, source=manager_src))
        put(_node("Trustee", trustee_id, trustee, city=deal.trustee_city, source=trustee_src))
        put(_node("Person", pm_id, pm, role="portfolio_manager", source=pm_src))
        put(
            _node(
                "Tranche",
                tranche_id,
                f"{deal.series} Class A",
                dealId=deal.id,
                className="A",
                par=class_a,
                source=class_a_src,
            )
        )
        put(_edge("MANAGED_BY", deal_id, manager_id, extra_id=f"{deal.id}:manager", source=manager_src))
        put(_edge("TRUSTEED_BY", deal_id, trustee_id, extra_id=f"{deal.id}:trustee", source=trustee_src))
        put(_edge("HAS_PM", deal_id, pm_id, extra_id=f"{deal.id}:pm", source=pm_src))
        put(_edge("HAS_TRANCHE", deal_id, tranche_id, extra_id=f"{deal.id}:class-a", source=class_a_src))

        for item in deal.obligors:
            name = primary_name if item.slug == deal.primary.slug else item.name
            item_rating = rating if item.slug == deal.primary.slug else item.moodys
            item_source = primary_src if item.slug == deal.primary.slug else "sample_book"
            put(_obligor_node(item, name=name, rating=item_rating, source=item_source))
            if item.slug == deal.primary.slug:
                put(_node("Sponsor", f"sponsor:{_slug(sponsor)}", sponsor, source=sponsor_src))
                put(
                    _edge(
                        "SPONSORED_BY",
                        f"obligor:{item.slug}",
                        f"sponsor:{_slug(sponsor)}",
                        extra_id=f"{item.slug}:sponsor",
                        source=sponsor_src,
                    )
                )
            else:
                put(_node("Sponsor", f"sponsor:{_slug(item.sponsor)}", item.sponsor, source="sample_book"))
                put(
                    _edge(
                        "SPONSORED_BY",
                        f"obligor:{item.slug}",
                        f"sponsor:{_slug(item.sponsor)}",
                        extra_id=f"{item.slug}:sponsor",
                        source="sample_book",
                    )
                )
            put(
                _edge(
                    "HOLDS",
                    deal_id,
                    f"obligor:{item.slug}",
                    extra_id=f"{deal.id}:{item.slug}",
                    allocation=allocation if item.slug == deal.primary.slug else item.allocation,
                    pct=item.pct,
                    watch=item.watch or (item.name == watch),
                    source=alloc_src if item.slug == deal.primary.slug else "sample_book",
                )
            )

        if watch and watch.lower() != "none":
            watched = next((item for item in deal.obligors if item.name == watch), None)
            watched_id = f"obligor:{watched.slug}" if watched else f"obligor:{_slug(watch)}"
            if not watched:
                put(_node("Obligor", watched_id, watch, slug=_slug(watch), source=watch_src))
            put(_edge("WATCHLIST", deal_id, watched_id, extra_id=f"{deal.id}:watch", source=watch_src))

    return list(docs.values())


_DOCS: list[dict] | None = None


def clear_graph_cache() -> None:
    global _DOCS
    _DOCS = None


def graph_documents() -> list[dict]:
    global _DOCS
    if _DOCS is None:
        _DOCS = build_graph_documents()
    return _DOCS


def node_id_for_document(doc_id: str) -> str:
    deal = deal_for_document(doc_id)
    if not deal:
        return ""
    if "credit-memo" in doc_id:
        return f"obligor:{deal.primary.slug}"
    return f"deal:{deal.id}"


def _document_id_for(node: dict, docs: list[dict]) -> str:
    label = node.get("label")
    if label in {"Deal", "Tranche"} and node.get("dealId"):
        return f"{node['dealId']}-term-sheet"
    if label == "Obligor":
        slug = node.get("slug") or node["id"].split(":", 1)[-1]
        for deal in DEALS:
            if deal.primary.slug == slug:
                return deal.credit_memo_id()
        for edge in docs:
            if edge.get("kind") == "edge" and edge.get("label") == "HOLDS" and edge.get("toId") == node["id"]:
                deal_id = edge["fromId"].split(":", 1)[-1]
                return f"{deal_id}-term-sheet"
        return ""
    if label in {"Manager", "Trustee", "Person"}:
        want = {"Manager": "MANAGED_BY", "Trustee": "TRUSTEED_BY", "Person": "HAS_PM"}[label]
        for edge in docs:
            if edge.get("kind") == "edge" and edge.get("label") == want and edge.get("toId") == node["id"]:
                deal_id = edge["fromId"].split(":", 1)[-1]
                return f"{deal_id}-term-sheet"
        return ""
    if label == "Sponsor":
        for edge in docs:
            if edge.get("kind") == "edge" and edge.get("label") == "SPONSORED_BY" and edge.get("toId") == node["id"]:
                slug = edge["fromId"].split(":", 1)[-1]
                for deal in DEALS:
                    if deal.primary.slug == slug:
                        return deal.credit_memo_id()
        return ""
    return ""


def _public_node(node: dict, docs: list[dict]) -> dict:
    return {
        "id": node["id"],
        "label": node["label"],
        "name": node["name"],
        "slug": node.get("slug"),
        "dealId": node.get("dealId"),
        "ocPass": node.get("ocPass"),
        "moodys": node.get("moodys"),
        "documentId": _document_id_for(node, docs),
        "query": node["name"] if node.get("label") in {"Obligor", "Person", "Manager", "Trustee", "Sponsor"} else "",
    }


def neighborhood(node_id: str) -> dict:
    docs = graph_documents()
    by_id = {item["id"]: item for item in docs}
    center = by_id.get(node_id) or by_id.get(f"deal:{node_id}")
    if not center or center.get("kind") != "node":
        raise ValueError(f"Unknown graph node: {node_id}")
    node_id = center["id"]
    related = [
        edge
        for edge in docs
        if edge.get("kind") == "edge" and (edge.get("fromId") == node_id or edge.get("toId") == node_id)
    ]
    neighbor_ids = {edge["fromId"] for edge in related} | {edge["toId"] for edge in related}
    neighbor_ids.discard(node_id)
    nodes = [_public_node(center, docs)]
    for nid in sorted(neighbor_ids):
        item = by_id.get(nid)
        if item and item.get("kind") == "node":
            nodes.append(_public_node(item, docs))
    edges = [
        {
            "id": edge["id"],
            "label": edge["label"],
            "fromId": edge["fromId"],
            "toId": edge["toId"],
            "allocation": edge.get("allocation"),
            "watch": edge.get("watch"),
        }
        for edge in related
    ]
    return {"center": node_id, "nodes": nodes, "edges": edges}


_ASK_STOP = {
    "a",
    "an",
    "and",
    "class",
    "clo",
    "clos",
    "corp",
    "deal",
    "deals",
    "did",
    "does",
    "fail",
    "failed",
    "for",
    "from",
    "hold",
    "holding",
    "holds",
    "how",
    "inc",
    "llc",
    "ltd",
    "of",
    "or",
    "pass",
    "passed",
    "rating",
    "report",
    "test",
    "the",
    "to",
    "what",
    "which",
    "who",
    "whom",
}


_YEARISH = re.compile(r"^(19|20)\d{2}$")


def _ask_tokens(text: str) -> set[str]:
    return {tok for tok in re.findall(r"[a-z0-9]+", text.lower()) if tok not in _ASK_STOP and len(tok) >= 3}


def _lead_word(text: str) -> str:
    """First distinctive word of a deal series or entity name (e.g. Redrock, Apex)."""
    for part in re.findall(r"[a-z][a-z0-9]+", (text or "").lower()):
        if part in _ASK_STOP or len(part) < 4 or _YEARISH.match(part):
            continue
        return part
    return ""


def _lead_in_question(lead: str, question: str) -> bool:
    return bool(lead) and re.search(rf"\b{re.escape(lead)}\b", question.lower()) is not None


def _mentions_deal(question: str) -> bool:
    q = question.lower()
    for deal in DEALS:
        if deal.series.lower() in q or deal.id.replace("-", " ") in q:
            return True
        if _lead_in_question(_lead_word(deal.series), q):
            return True
    return False


def _ask_intents(question: str) -> set[str]:
    q = question.lower()
    intents: set[str] = set()
    if re.search(r"\b(hold|holds|holding|portfolio|obligor|names? on)\b", q):
        intents.add("holds")
    if re.search(r"\b(oc|overcollat|coverage|pass|fail|trigger|result)\b", q):
        intents.add("oc")
    if re.search(r"\b(watch|watchlist)\b", q):
        intents.add("watch")
    if re.search(r"\b(manager|managed)\b", q):
        intents.add("manager")
    if re.search(r"\b(trustee|trusteed)\b", q):
        intents.add("trustee")
    if re.search(r"\b(pm|portfolio manager)\b", q):
        intents.add("pm")
    if re.search(r"\b(sponsor|rating|moody)", q):
        intents.add("credit")
    if re.search(
        r"\b(waterfall|disburs|payment date|paydown|residual|interest due|how much|class a principal)\b",
        q,
    ):
        intents.add("pay")
    if not _mentions_deal(q) and (
        re.search(r"\b(which|list|all)\b.*\b(fail|failed|pass|passed)\b", q)
        or re.search(r"\b(fail|failed)\b.*\b(oc|test)\b", q)
    ):
        intents.add("oc_all")
    return intents


def _oc_status(trigger: str, result: str, fallback: bool | None) -> str:
    try:
        t = float(str(trigger).replace("%", "").replace(",", "").strip())
        r = float(str(result).replace("%", "").replace(",", "").strip())
        return "PASS" if r >= t else "FAIL"
    except (TypeError, ValueError):
        if fallback is None:
            return "unknown"
        return "PASS" if fallback else "FAIL"


def _field_cites() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in list_runs():
        run = load_run(row["documentId"])
        if not run:
            continue
        ext = run.get("extraction", {})
        title = title_for_filename(ext.get("filename") or f"{row['documentId']}.pdf")
        for field in ext.get("fields", []):
            cites = field.get("citations") or []
            page = cites[0].get("page") if cites else 1
            out[field["id"]] = {
                "documentId": row["documentId"],
                "title": title,
                "page": page or 1,
            }
    return out


def _cite_for(field_id: str, cites: dict, document_id: str = "") -> dict | None:
    if field_id and field_id in cites:
        return cites[field_id]
    if not document_id:
        return None
    return {
        "documentId": document_id,
        "title": title_for_filename(f"{document_id}.pdf"),
        "page": 1,
    }


def _score_node(question: str, tokens: set[str], node: dict) -> int:
    if node.get("kind") != "node" or node.get("label") == "Tranche":
        return 0
    name = str(node.get("name") or "")
    series = str(node.get("series") or "")
    slug = str(node.get("slug") or node.get("id", "").split(":", 1)[-1]).replace("-", " ")
    hay = f"{name} {series} {slug}".lower()
    score = 0
    q = question.lower()
    if name and name.lower() in q:
        score += 8
    if series and series.lower() in q:
        score += 8
    score += 2 * len(tokens & _ask_tokens(hay))
    lead = _lead_word(series) or _lead_word(name)
    if _lead_in_question(lead, q):
        score += 8
    if node.get("label") == "Deal" and series:
        short = " ".join(series.split()[:2]).lower()
        if short and short in q:
            score += 4
    return score


def _match_nodes(question: str, docs: list[dict]) -> list[dict]:
    tokens = _ask_tokens(question)
    scored = []
    for node in docs:
        score = _score_node(question, tokens, node)
        if score >= 4:
            scored.append((score, node))
    scored.sort(key=lambda item: (-item[0], item[1].get("label", ""), item[1].get("name", "")))
    return [node for _, node in scored[:8]]


def _focus_from_seeds(seeds: list[dict], question: str) -> dict:
    q = question.lower()
    prefer_obligor = bool(_ask_intents(question) & {"holds", "credit"})

    def key(node: dict) -> tuple:
        lead = _lead_word(node.get("series") or "") or _lead_word(node.get("name") or "")
        hit = 0 if _lead_in_question(lead, q) else 1
        if prefer_obligor:
            pri = {"Obligor": 0, "Deal": 1, "Person": 2, "Manager": 3, "Trustee": 4}.get(node.get("label"), 5)
        else:
            pri = {"Deal": 0, "Obligor": 1, "Person": 2, "Manager": 3, "Trustee": 4}.get(node.get("label"), 5)
        return (hit, pri, node.get("name") or "")

    node = sorted(seeds, key=key)[0]
    return {"id": node["id"], "name": node.get("name") or "", "label": node.get("label") or ""}


def facts_for_question(
    question: str,
    docs: list[dict] | None = None,
    cites: dict | None = None,
    extracted: dict | None = None,
    reviews: dict | None = None,
) -> dict:
    """HITL-resolved graph facts for a question, plus clickable PDF citations."""
    docs = docs if docs is not None else graph_documents()
    cites = cites if cites is not None else _field_cites()
    by_id = {item["id"]: item for item in docs}
    intents = _ask_intents(question)
    seeds = _match_nodes(question, docs)
    if "oc_all" in intents and not seeds:
        seeds.extend([item for item in docs if item.get("kind") == "node" and item.get("label") == "Deal"])
    if not seeds:
        return {"text": "", "sources": [], "matched": [], "focus": None, "waterfall": []}

    deal_ids: set[str] = set()
    obligor_ids: set[str] = set()
    other_ids: set[str] = set()
    focus_obligors = {node["id"] for node in seeds if node.get("label") == "Obligor"}
    for node in seeds:
        label = node.get("label")
        if label == "Deal":
            deal_ids.add(node["id"])
        elif label == "Obligor":
            obligor_ids.add(node["id"])
        else:
            other_ids.add(node["id"])
        for edge in docs:
            if edge.get("kind") != "edge":
                continue
            if edge.get("fromId") != node["id"] and edge.get("toId") != node["id"]:
                continue
            if edge["label"] == "HOLDS":
                deal_ids.add(edge["fromId"])
                obligor_ids.add(edge["toId"])
            elif edge["label"] in {"MANAGED_BY", "TRUSTEED_BY", "HAS_PM", "HAS_TRANCHE", "WATCHLIST"}:
                if str(edge.get("fromId", "")).startswith("deal:"):
                    deal_ids.add(edge["fromId"])
            elif edge["label"] == "SPONSORED_BY":
                obligor_ids.add(edge["fromId"])

    lines: list[str] = []
    sources: list[dict] = []
    seen_sources: set[tuple] = set()

    def add_source(cite: dict | None, snippet: str) -> None:
        if not cite:
            return
        key = (cite["documentId"], cite.get("page") or 1)
        if key in seen_sources:
            return
        seen_sources.add(key)
        sources.append(
            {
                "documentId": cite["documentId"],
                "title": cite["title"],
                "page": cite.get("page") or 1,
                "snippet": snippet[:180],
            }
        )

    def cite_line(cite: dict | None) -> str:
        if not cite:
            return ""
        return f" [{cite['title']}, p.{cite.get('page') or 1}]"

    waterfall: list[dict] = []
    compact = len(deal_ids) > 1
    for deal_id in sorted(deal_ids):
        deal_node = by_id.get(deal_id)
        if not deal_node:
            continue
        deal = next((item for item in DEALS if item.id == deal_node.get("dealId")), None)
        ids = deal_field_ids(deal) if deal else {}
        srcs = deal_node.get("fieldSources") or {}
        oc_trig = deal_node.get("ocTrigger")
        oc_res = deal_node.get("ocResult")
        oc = _oc_status(oc_trig, oc_res, deal_node.get("ocPass"))
        trig_cite = _cite_for(ids.get("oc_trigger", ""), cites, deal.term_sheet_id() if deal else "")
        res_cite = _cite_for(ids.get("oc_result", ""), cites, deal.report_id() if deal else "")
        mgr = next(
            (
                by_id.get(edge["toId"])
                for edge in docs
                if edge.get("kind") == "edge"
                and edge.get("label") == "MANAGED_BY"
                and edge.get("fromId") == deal_node["id"]
            ),
            None,
        )
        trustee = next(
            (
                by_id.get(edge["toId"])
                for edge in docs
                if edge.get("kind") == "edge"
                and edge.get("label") == "TRUSTEED_BY"
                and edge.get("fromId") == deal_node["id"]
            ),
            None,
        )
        pm = next(
            (
                by_id.get(edge["toId"])
                for edge in docs
                if edge.get("kind") == "edge" and edge.get("label") == "HAS_PM" and edge.get("fromId") == deal_node["id"]
            ),
            None,
        )
        watch = next(
            (
                by_id.get(edge["toId"])
                for edge in docs
                if edge.get("kind") == "edge"
                and edge.get("label") == "WATCHLIST"
                and edge.get("fromId") == deal_node["id"]
            ),
            None,
        )
        holds = [
            edge
            for edge in docs
            if edge.get("kind") == "edge" and edge.get("label") == "HOLDS" and edge.get("fromId") == deal_node["id"]
        ]
        name_cite = _cite_for(ids.get("deal_name", ""), cites, deal.term_sheet_id() if deal else "")
        header = f"Deal {deal_node.get('name')} ({deal_node.get('series') or deal_node.get('dealId')})"
        lines.append(header + cite_line(name_cite))
        add_source(name_cite, header)
        if oc_trig is not None:
            line = f"  Class A/B OC trigger: {oc_trig} ({srcs.get('ocTrigger', 'sample_book')})" + cite_line(trig_cite)
            lines.append(line)
            add_source(trig_cite, line.strip())
        if oc_res is not None:
            line = f"  Class A/B OC result: {oc_res} ({srcs.get('ocResult', 'sample_book')})" + cite_line(res_cite)
            lines.append(line)
            add_source(res_cite, line.strip())
        lines.append(f"  Class A/B OC test: {oc}")
        if mgr and (not focus_obligors or "manager" in intents or any(n.get("label") == "Deal" for n in seeds)):
            cite = _cite_for(ids.get("manager", ""), cites, deal.term_sheet_id() if deal else "")
            line = f"  Manager: {mgr.get('name')} ({mgr.get('source', 'sample_book')})" + cite_line(cite)
            lines.append(line)
            add_source(cite, line.strip())
        if trustee and (not focus_obligors or "trustee" in intents or any(n.get("label") == "Deal" for n in seeds)):
            cite = _cite_for(ids.get("trustee", ""), cites, deal.term_sheet_id() if deal else "")
            line = f"  Trustee: {trustee.get('name')} ({trustee.get('source', 'sample_book')})" + cite_line(cite)
            lines.append(line)
            add_source(cite, line.strip())
        if pm and (not focus_obligors or "pm" in intents or any(n.get("label") == "Deal" for n in seeds)):
            cite = _cite_for(ids.get("pm", ""), cites, deal.term_sheet_id() if deal else "")
            line = f"  Portfolio manager: {pm.get('name')} ({pm.get('source', 'sample_book')})" + cite_line(cite)
            lines.append(line)
            add_source(cite, line.strip())
        for edge in sorted(holds, key=lambda item: item.get("toId", "")):
            obligor = by_id.get(edge["toId"])
            if not obligor:
                continue
            if focus_obligors and edge["toId"] not in focus_obligors:
                continue
            primary = bool(deal and deal.primary.slug == obligor.get("slug"))
            if primary:
                cite = _cite_for(ids.get("allocation", ""), cites, deal.credit_memo_id() if deal else "")
            elif deal:
                cite = _cite_for(ids.get("deal_name", ""), cites, deal.term_sheet_id())
            else:
                cite = None
            alloc = edge.get("allocation") or ""
            src = edge.get("source", "sample_book")
            line = f"  Holds {obligor.get('name')} {alloc} ({src})" + cite_line(cite)
            lines.append(line)
            add_source(cite, line.strip())
        if watch:
            cite = _cite_for(ids.get("watch", ""), cites, deal.report_id() if deal else "")
            line = f"  Watchlist: {watch.get('name')} ({watch.get('source', 'sample_book')})" + cite_line(cite)
            lines.append(line)
            add_source(cite, line.strip())
        fail_only = "oc_all" in intents and len(deal_ids) > 8 and "pay" not in intents
        if deal and not (fail_only and oc == "PASS"):
            try:
                model = disbursement_for_deal(
                    deal.id,
                    extracted=extracted,
                    reviews=reviews,
                    with_schedule=False,
                )
            except ValueError:
                model = None
            if model:
                pay_cite = res_cite or _cite_for(ids.get("oc_result", ""), cites, deal.report_id())
                suffix = cite_line(pay_cite)
                add_source(pay_cite, f"{deal.series} waterfall {model['paymentDateDisplay']}")
                if compact:
                    if model["redirect"]:
                        line = (
                            f"  Waterfall {model['paymentDateDisplay']}: "
                            f"redirect {model['paydownDisplay']} to Class A principal"
                        )
                    else:
                        line = (
                            f"  Waterfall {model['paymentDateDisplay']}: "
                            f"residual {model['residualDisplay']} to subordinated notes"
                        )
                    lines.append(line + suffix)
                else:
                    lines.extend(format_waterfall_facts(model, suffix))
                waterfall.append(
                    {
                        "dealId": deal.id,
                        "series": deal.series,
                        "paymentDateDisplay": model["paymentDateDisplay"],
                        "redirect": model["redirect"],
                        "paydownDisplay": model["paydownDisplay"],
                        "residualDisplay": model["residualDisplay"],
                        "ocPass": model["ocPass"],
                        "ocSource": model["ocSource"],
                        "classASource": model["classASource"],
                        "collectedDisplay": model["collectedDisplay"],
                    }
                )

    for oid in sorted(obligor_ids):
        node = by_id.get(oid)
        if not node:
            continue
        deal = next((item for item in DEALS if item.primary.slug == node.get("slug")), None)
        ids = deal_field_ids(deal) if deal else {}
        cite = _cite_for(ids.get("obligor", ""), cites, deal.credit_memo_id() if deal else "")
        rating_cite = _cite_for(ids.get("rating", ""), cites, deal.credit_memo_id() if deal else "")
        sponsor = next(
            (
                by_id.get(edge["toId"])
                for edge in docs
                if edge.get("kind") == "edge" and edge.get("label") == "SPONSORED_BY" and edge.get("fromId") == oid
            ),
            None,
        )
        header = f"Obligor {node.get('name')}"
        extra = []
        if node.get("moodys"):
            extra.append(f"Moody's {node['moodys']}")
        if sponsor:
            extra.append(f"sponsor {sponsor.get('name')}")
        if extra:
            header += " — " + "; ".join(extra)
        lines.append(header + cite_line(cite or rating_cite))
        add_source(cite or rating_cite, header)

    for oid in sorted(other_ids):
        node = by_id.get(oid)
        if not node:
            continue
        lines.append(f"{node.get('label')} {node.get('name')} ({node.get('source', 'sample_book')})")

    return {
        "text": "\n".join(lines),
        "sources": sources,
        "matched": [node["id"] for node in seeds],
        "focus": _focus_from_seeds(seeds, question),
        "waterfall": waterfall,
    }


def suggest_nodes(query: str, limit: int = 8) -> list[dict]:
    q = query.strip()
    docs = graph_documents()
    nodes = [item for item in docs if item.get("kind") == "node" and item.get("label") != "Tranche"]
    if not q:
        nodes = [item for item in nodes if item["label"] == "Deal"]
        return [_public_node(item, docs) for item in nodes[:limit]]
    tokens = _ask_tokens(q)
    scored = []
    q_l = q.lower()
    for item in nodes:
        hay = f"{item.get('name', '')} {item.get('label', '')} {item.get('slug', '')} {item.get('series', '')}".lower()
        score = _score_node(q, tokens, item)
        if q_l in hay:
            score = max(score, 12)
        if score >= 4:
            scored.append((score, item))
    scored.sort(key=lambda item: (-item[0], item[1].get("name", "")))
    return [_public_node(item, docs) for _, item in scored[:limit]]


def backfill_graph() -> dict:
    docs = build_graph_documents()
    from clo_intel.cosmos import upsert_documents

    LOG.info("Writing %s graph documents to Cosmos", len(docs))
    upsert_documents(docs)
    clear_graph_cache()
    nodes = sum(1 for d in docs if d["kind"] == "node")
    edges = sum(1 for d in docs if d["kind"] == "edge")
    return {"documents": len(docs), "nodes": nodes, "edges": edges, "deals": len(DEALS)}


def deals_holding(obligor_slug: str) -> list[dict]:
    from clo_intel.cosmos import query_items

    target = f"obligor:{obligor_slug}"
    edges = query_items(
        "SELECT c.fromId, c.allocation, c.pct, c.watch FROM c WHERE c.kind = 'edge' AND c.label = 'HOLDS' AND c.toId = @id",
        [{"name": "@id", "value": target}],
    )
    deals = {
        item["id"]: item
        for item in query_items(
            "SELECT c.id, c.name, c.dealId, c.series FROM c WHERE c.kind = 'node' AND c.label = 'Deal'"
        )
    }
    out = []
    for edge in edges:
        deal = deals.get(edge["fromId"])
        if deal:
            out.append(
                {
                    "dealId": deal.get("dealId"),
                    "name": deal.get("name"),
                    "series": deal.get("series"),
                    "allocation": edge.get("allocation"),
                    "pct": edge.get("pct"),
                    "watch": edge.get("watch"),
                }
            )
    return out
