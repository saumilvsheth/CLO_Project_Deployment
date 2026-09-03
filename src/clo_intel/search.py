"""Hybrid search across CLO PDFs: keyword + Azure embedding vectors, fused with RRF."""

from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from hashlib import sha256

from clo_intel.config import INDEX_PATH, env
from clo_intel.library import list_pdfs
from clo_intel.telemetry import LOG

_TOKEN = re.compile(r"[a-z0-9%$]+", re.I)
_INDEX: list[dict] | None = None
_MODE = "keyword"


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text)]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _keyword_score(query: str, text: str) -> float:
    q = query.strip().lower()
    if not q or not text:
        return 0.0
    blob = text.lower()
    score = 5.0 if q in blob else 0.0
    q_terms = _tokens(q)
    counts = Counter(_tokens(blob))
    for term in q_terms:
        score += counts.get(term, 0)
    return score


def _snippet(text: str, query: str, width: int = 110) -> str:
    blob = text.replace("\n", " ").strip()
    if not blob:
        return ""
    needle = query.strip().lower()
    lower = blob.lower()
    idx = lower.find(needle) if needle else -1
    if idx < 0:
        first = _tokens(query)
        if first:
            idx = lower.find(first[0])
    if idx < 0:
        return blob[: width * 2]
    left = max(0, idx - width)
    right = min(len(blob), idx + len(query) + width)
    snippet = blob[left:right].strip()
    if left:
        snippet = "…" + snippet
    if right < len(blob):
        snippet = snippet + "…"
    return snippet


def _embed(texts: list[str]) -> list[list[float]] | None:
    endpoint = env("AZURE_AI_EMBEDDING_ENDPOINT")
    model = env("AZURE_AI_EMBEDDING_NAME") or "text-embedding-3-small"
    if not endpoint:
        return None
    try:
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=endpoint,
            azure_ad_token_provider=get_bearer_token_provider(
                DefaultAzureCredential(exclude_interactive_browser_credential=True),
                "https://cognitiveservices.azure.com/.default",
            ),
            api_version="2024-06-01",
        )
        vectors: list[list[float]] = []
        batch_size = 8
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            for attempt in range(5):
                try:
                    response = client.embeddings.create(model=model, input=batch)
                    vectors.extend(item.embedding for item in response.data)
                    break
                except Exception as exc:  # noqa: BLE001
                    message = str(exc)
                    if "429" not in message and "RateLimit" not in message:
                        raise
                    wait = 20 * (attempt + 1)
                    LOG.warning("Embedding rate limit; retrying in %ss (%s)", wait, exc)
                    time.sleep(wait)
            else:
                raise RuntimeError("Embedding rate limit persisted after retries.")
        return vectors
    except Exception as exc:  # noqa: BLE001 — local keyword search still works
        LOG.warning("Embedding search unavailable (%s); using keyword only", exc)
        return None


def _fingerprint() -> str:
    parts = []
    for doc in list_pdfs():
        parts.append(f"{doc.id}:{doc.path.stat().st_mtime_ns}:{doc.pages}")
    return sha256("|".join(parts).encode()).hexdigest()


def _chunks() -> list[dict]:
    chunks = []
    for doc in list_pdfs():
        for page_no, text in enumerate(doc.page_texts, start=1):
            chunks.append(
                {
                    "id": f"{doc.id}:{page_no}",
                    "documentId": doc.id,
                    "title": doc.title,
                    "filename": doc.filename,
                    "page": page_no,
                    "text": text,
                }
            )
    return chunks


def build_index() -> str:
    global _INDEX, _MODE
    fingerprint = _fingerprint()
    cached = None
    if INDEX_PATH.exists():
        cached = json.loads(INDEX_PATH.read_text())
        if cached.get("fingerprint") == fingerprint and cached.get("chunks"):
            cached_mode = cached.get("mode", "keyword")
            has_vectors = any(chunk.get("vector") for chunk in cached["chunks"])
            if has_vectors or not env("AZURE_AI_EMBEDDING_ENDPOINT"):
                _INDEX = cached["chunks"]
                _MODE = cached_mode
                LOG.info("Loaded search index (%s, %s chunks)", _MODE, len(_INDEX))
                return _MODE
    chunks = _chunks()
    vectors = _embed([c["text"] or " " for c in chunks]) if chunks else None
    if vectors:
        for chunk, vector in zip(chunks, vectors):
            chunk["vector"] = vector
        _MODE = "hybrid"
    else:
        for chunk in chunks:
            chunk["vector"] = None
        _MODE = "keyword"
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps({"fingerprint": fingerprint, "mode": _MODE, "chunks": chunks}))
    _INDEX = chunks
    LOG.info("Built search index (%s, %s chunks)", _MODE, len(chunks))
    return _MODE


def _rrf(keyword_ranked: list[dict], vector_ranked: list[dict], k: int = 60) -> list[dict]:
    scores: dict[str, float] = {}
    by_id = {c["id"]: c for c in keyword_ranked + vector_ranked}
    for rank, chunk in enumerate(keyword_ranked, start=1):
        scores[chunk["id"]] = scores.get(chunk["id"], 0) + 1 / (k + rank)
    for rank, chunk in enumerate(vector_ranked, start=1):
        scores[chunk["id"]] = scores.get(chunk["id"], 0) + 1 / (k + rank)
    return [by_id[cid] | {"_rrf": scores[cid]} for cid, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]


def search(query: str, limit: int = 8) -> dict:
    q = query.strip()
    if not q:
        return {"hits": [], "mode": _MODE or "keyword"}
    if _INDEX is None:
        build_index()
    chunks = _INDEX or []
    keyword_scored = []
    for chunk in chunks:
        score = _keyword_score(q, f"{chunk['title']} {chunk['text']}")
        if score > 0:
            keyword_scored.append({**chunk, "_kw": score})
    keyword_scored.sort(key=lambda c: c["_kw"], reverse=True)

    vector_scored = []
    query_vec = None
    if any(c.get("vector") for c in chunks):
        embedded = _embed([q])
        query_vec = embedded[0] if embedded else None
    if query_vec:
        for chunk in chunks:
            if not chunk.get("vector"):
                continue
            sim = _cosine(query_vec, chunk["vector"])
            if sim > 0.15:
                vector_scored.append({**chunk, "_vec": sim})
        vector_scored.sort(key=lambda c: c["_vec"], reverse=True)

    if keyword_scored and vector_scored:
        ranked = _rrf(keyword_scored[:20], vector_scored[:20])
        mode = "hybrid"
    elif vector_scored:
        ranked = vector_scored
        mode = "semantic"
    else:
        ranked = keyword_scored
        mode = "keyword"

    hits = []
    for chunk in ranked[:limit]:
        hits.append(
            {
                "documentId": chunk["documentId"],
                "title": chunk["title"],
                "filename": chunk["filename"],
                "page": chunk["page"],
                "snippet": _snippet(chunk["text"], q),
                "score": round(chunk.get("_rrf") or chunk.get("_vec") or chunk.get("_kw") or 0, 4),
            }
        )
    return {"hits": hits, "mode": mode}
