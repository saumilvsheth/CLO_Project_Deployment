"""Grounded Q&A: HITL-resolved graph facts first, then PDF passages."""

from __future__ import annotations

import re

from clo_intel.config import env
from clo_intel.graph import facts_for_question, suggest_nodes
from clo_intel.library import get_document
from clo_intel.search import search
from clo_intel.telemetry import LOG

SYSTEM = (
    "You answer questions about CLO documents. "
    "Start with a heading 'Executive summary' and 2–4 sentences that answer the question directly, "
    "with no citations and no source tags. "
    "Then a heading 'Details' and the supporting facts. "
    "GRAPH FACTS are the source of truth for names, holdings, ratings, and numeric tests. "
    "If GRAPH FACTS include a payment-date waterfall, treat those dollars as the "
    "indenture calculation for that period. Values tagged approved or overridden were confirmed by a human reviewer; "
    "prefer them over extracted or sample_book. "
    "If GRAPH FACTS and PASSAGES disagree on a name or number, trust GRAPH FACTS. "
    "Use PASSAGES only for wording, extra context, and page citations that the graph already points to. "
    "If the graph lists several matching deals or obligors, include every one — do not sample. "
    "If neither section contains the answer, say you cannot tell from the files. "
    "In Details, put each citation in the sentence it supports, using exactly [Document title, p.N] "
    "copied from the fact or passage. Never add a separate source list. "
    "Do not invent names, ratings, or numeric ratios."
)


def _chat(messages: list[dict]) -> str:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from openai import AzureOpenAI

    endpoint = env("AZURE_AI_EMBEDDING_ENDPOINT")
    model = env("FOUNDRY_MODEL")
    if not endpoint or not model:
        raise RuntimeError("FOUNDRY_MODEL and AZURE_AI_EMBEDDING_ENDPOINT must be set.")
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=get_bearer_token_provider(
            DefaultAzureCredential(exclude_interactive_browser_credential=True),
            "https://cognitiveservices.azure.com/.default",
        ),
        api_version="2024-10-21",
    )
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
        max_tokens=4000,
    )
    choice = response.choices[0]
    text = (choice.message.content or "").strip()
    LOG.info("Chat finish=%s chars=%s", getattr(choice, "finish_reason", ""), len(text))
    return text


def _passage_text(hit: dict) -> str:
    doc = get_document(hit["documentId"])
    if not doc or hit["page"] < 1 or hit["page"] > len(doc.page_texts):
        return hit.get("snippet") or ""
    return doc.page_texts[hit["page"] - 1][:2500]


def _merge_sources(graph_sources: list[dict], hits: list[dict]) -> list[dict]:
    out = []
    seen: set[tuple] = set()
    for item in graph_sources + hits:
        key = (item.get("documentId"), item.get("page"))
        if not item.get("documentId") or key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "documentId": item["documentId"],
                "title": item.get("title", ""),
                "page": item.get("page") or 1,
                "snippet": item.get("snippet") or "",
            }
        )
    return out


_SRC_TAG = re.compile(r"\s+\((approved|overridden|extracted|sample_book)\)\s*$")
_CITE_TAIL = re.compile(r"\s*\[[^\]]+\]\s*$")


def _strip_cite(line: str) -> str:
    return _CITE_TAIL.sub("", line).rstrip()


def _split_src(value: str) -> tuple[str, str]:
    match = _SRC_TAG.search(value)
    if not match:
        return value.strip(), ""
    return value[: match.start()].strip(), match.group(1)


def _join_and(items: list[str]) -> str:
    names = [item for item in items if item]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return f"{', '.join(names[:-1])}, and {names[-1]}"


def _short_series(series: str) -> str:
    return re.sub(r"\s+CLO\s+\d{4}-\d+\s*$", "", series or "").strip() or series


def _parse_graph_facts(text: str) -> dict:
    deals: list[dict] = []
    obligors: list[dict] = []
    current: dict | None = None
    for raw in (text or "").splitlines():
        line = _strip_cite(raw)
        if line.startswith("Deal "):
            body = line[5:]
            split_at = body.rfind(" (")
            name = body[:split_at] if split_at > 0 else body
            series = body[split_at + 2 : -1] if split_at > 0 and body.endswith(")") else name
            current = {"name": name.strip(), "series": series.strip(), "holds": []}
            deals.append(current)
            continue
        if line.startswith("Obligor "):
            current = None
            body = line[len("Obligor ") :]
            name, _, extra = body.partition(" — ")
            obligors.append({"name": name.strip(), "extra": extra.strip()})
            continue
        if not current or not line.startswith("  "):
            continue
        if line.startswith("  Holds "):
            rest, src = _split_src(line[8:])
            alloc = ""
            alloc_m = re.search(r"(\$[\d,]+(?:\.\d+)?|\d+(?:\.\d+)?%)\s*$", rest)
            if alloc_m:
                alloc = alloc_m.group(1)
                rest = rest[: alloc_m.start()].strip()
            current["holds"].append({"name": rest, "allocation": alloc, "source": src})
            continue
        if ":" not in line:
            continue
        field, value = line[2:].split(":", 1)
        value, src = _split_src(value.strip())
        key = field.strip()
        if key == "Class A/B OC trigger":
            current["trigger"] = value
            current["trigger_src"] = src
        elif key == "Class A/B OC result":
            current["result"] = value
            current["result_src"] = src
        elif key == "Class A/B OC test":
            current["oc"] = value
        elif key == "Manager":
            current["manager"] = value
        elif key == "Trustee":
            current["trustee"] = value
        elif key == "Portfolio manager":
            current["pm"] = value
        elif key == "Watchlist":
            current["watch"] = value
    return {"deals": deals, "obligors": obligors}


def _oc_clause(deal: dict) -> str:
    trig = deal.get("trigger")
    res = deal.get("result")
    if res and trig:
        return f"{res} vs a {trig} trigger"
    return ""


def _review_note(deal: dict) -> str:
    tags = [deal.get("result_src"), deal.get("trigger_src")]
    if "overridden" in tags:
        which = "result" if deal.get("result_src") == "overridden" else "trigger"
        return f"A reviewer overrode the Class A/B OC {which} to {deal.get(which)}."
    if "approved" in tags:
        return "The OC figures were confirmed in human review."
    return ""


def _executive_summary(graph: dict) -> str:
    parsed = _parse_graph_facts(graph.get("text") or "")
    deals = parsed["deals"]
    obligors = parsed["obligors"]
    focus = graph.get("focus") or {}
    sentences: list[str] = []

    if focus.get("label") == "Obligor" and (obligors or deals):
        name = focus.get("name") or (obligors[0]["name"] if obligors else "This obligor")
        n = len(deals)
        fails = [deal for deal in deals if deal.get("oc") == "FAIL"]
        passes = [deal for deal in deals if deal.get("oc") == "PASS"]
        if n:
            sentences.append(
                f"{name} is held by {n} CLO{'s' if n != 1 else ''}: "
                f"{_join_and([_short_series(deal['series']) for deal in deals])}."
            )
        else:
            sentences.append(f"{name} is in the knowledge graph.")
        if fails and passes:
            sentences.append(
                f"{_join_and([_short_series(deal['series']) for deal in fails])} failed Class A/B OC; "
                f"the other {len(passes)} passed."
            )
        elif fails:
            sentences.append(
                f"{_join_and([_short_series(deal['series']) for deal in fails])} failed Class A/B OC."
            )
        elif passes:
            sentences.append("All of those deals passed Class A/B OC.")
        extra = obligors[0].get("extra") if obligors else ""
        if extra:
            sentences.append(f"{name} — {extra}.")
        sentences.extend(_waterfall_sentences(graph.get("waterfall") or []))
    elif len(deals) == 1:
        deal = deals[0]
        series = deal["series"]
        oc = deal.get("oc")
        clause = _oc_clause(deal)
        if oc == "FAIL":
            sentences.append(
                f"{series} failed the Class A/B OC test" + (f" ({clause})." if clause else ".")
            )
        elif oc == "PASS":
            sentences.append(
                f"{series} passed the Class A/B OC test" + (f" ({clause})." if clause else ".")
            )
        else:
            sentences.append(f"{series} is in the knowledge graph.")
        review = _review_note(deal)
        if review:
            sentences.append(review)
        if deal.get("manager") and deal.get("pm"):
            sentences.append(
                f"The deal is managed by {deal['manager']}, with portfolio manager {deal['pm']}."
            )
        elif deal.get("manager"):
            sentences.append(f"The deal is managed by {deal['manager']}.")
        elif deal.get("pm"):
            sentences.append(f"The portfolio manager is {deal['pm']}.")
        holds = deal.get("holds") or []
        if holds:
            shown = [item["name"] for item in holds[:4]]
            more = len(holds) - 4
            if more:
                sentences.append(
                    f"Holdings include {', '.join(shown)}, and {more} other{'s' if more != 1 else ''}."
                )
            else:
                sentences.append(f"Holdings include {_join_and(shown)}.")
        if deal.get("watch"):
            sentences.append(f"{deal['watch']} is on the watchlist.")
        sentences.extend(_waterfall_sentences(graph.get("waterfall") or []))
    elif deals:
        fails = [deal for deal in deals if deal.get("oc") == "FAIL"]
        passes = [deal for deal in deals if deal.get("oc") == "PASS"]
        sentences.append(f"{len(deals)} deals match this question.")
        if fails:
            sentences.append(
                f"{len(fails)} failed Class A/B OC: "
                f"{_join_and([_short_series(deal['series']) for deal in fails])}."
            )
        if passes:
            sentences.append(f"{len(passes)} passed.")
        sentences.extend(_waterfall_sentences(graph.get("waterfall") or []))
    else:
        sentences.append("Matching facts from the knowledge graph are below.")

    return " ".join(sentences)


def _waterfall_sentences(falls: list[dict]) -> list[str]:
    if not falls:
        return []
    if len(falls) == 1:
        item = falls[0]
        date = item.get("paymentDateDisplay") or "the current payment date"
        if item.get("redirect"):
            return [
                f"On {date}, remaining interest of {item.get('paydownDisplay')} is redirected to Class A principal, and Class C–E coupons are deferred."
            ]
        return [
            f"On {date}, the waterfall pays Class A–E interest and leaves {item.get('residualDisplay')} residual for the subordinated notes."
        ]
    redirects = [item for item in falls if item.get("redirect")]
    if not redirects:
        return []
    names = _join_and([_short_series(item.get("series") or "") for item in redirects])
    return [f"This period, {names} redirect leftover interest to Class A principal."]


def format_graph_answer(graph: dict) -> str:
    summary = _executive_summary(graph)
    return (
        "Executive summary\n\n"
        f"{summary}\n\n"
        "Details\n\n"
        "From the knowledge graph. Values marked approved or overridden were confirmed in human review.\n\n"
        + (graph.get("text") or "")
    )


def _graph_focus(graph: dict, question: str) -> dict | None:
    focus = graph.get("focus")
    if focus and focus.get("id"):
        return focus
    hits = suggest_nodes(question, limit=1)
    if not hits:
        return None
    hit = hits[0]
    return {"id": hit["id"], "name": hit.get("name") or "", "label": hit.get("label") or ""}


def answer_question(question: str) -> dict:
    q = question.strip()
    if not q:
        raise ValueError("Enter a question.")
    graph = facts_for_question(q)
    focus = _graph_focus(graph, q)
    if graph["text"]:
        sources = _merge_sources(graph["sources"], [])
        LOG.info("Answering from graph facts (%s sources)", len(sources))
        return {
            "answer": format_graph_answer(graph),
            "sources": sources,
            "mode": "graph",
            "graphNode": focus,
        }
    retrieved = search(q, limit=5)
    hits = retrieved["hits"]
    if not hits:
        return {
            "answer": "No graph facts or passages matched that question.",
            "sources": [],
            "mode": retrieved.get("mode", "keyword"),
            "graphNode": focus,
        }
    sources = _merge_sources([], hits)
    blocks = [
        f"[{i}] {hit['title']}, p.{hit['page']}\n{_passage_text(hit)}" for i, hit in enumerate(hits, start=1)
    ]
    LOG.info("Answering with %s passages (%s)", len(hits), retrieved.get("mode"))
    try:
        text = _chat(
            [
                {"role": "system", "content": SYSTEM},
                {
                    "role": "user",
                    "content": f"GRAPH FACTS:\n(none)\n\nPASSAGES:\n{chr(10).join(blocks)}\n\nQuestion: {q}",
                },
            ]
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"The model could not answer ({exc}).") from exc
    return {
        "answer": text or "The model did not return an answer.",
        "sources": sources,
        "mode": retrieved.get("mode", "keyword"),
        "graphNode": focus,
    }
