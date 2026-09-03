# Graph RAG Planning Document

**Project:** Simple Graph RAG over PDF documents  
**Stack:** Python + Microsoft Agent Framework + Azure Cosmos DB for NoSQL  
**Status:** Phase 0 in progress — Cosmos account, Foundry embeddings, and `ping` work. Vector-indexed `chunks` container is enabled at the account level and created once the capability finishes propagating.

---

## 1. Goal

Build a small Azure-first system that:

1. Reads PDF files.
2. Extracts facts into a **knowledge graph** (entities + relationships), not just text chunks.
3. Stores that graph, chunk text, and embeddings in **Azure Cosmos DB**.
4. Lets a user ask questions in natural language.
5. Answers using an **intelligence layer** — a Microsoft Agent Framework agent that retrieves from Cosmos (vector search + graph hops), reasons over connected facts, and cites source PDFs.

This is Graph RAG, not classic vector RAG. Vector search finds similar text. The graph adds *how things are connected*, so the agent can answer questions like “who is related to X?” or “what documents mention both A and B?”

---

## 2. What we are *not* building (v1)

Keep v1 small on purpose.

| Out of scope | Why |
| --- | --- |
| Neo4j / Cypher / `neo4j-graphrag` | Replaced by Cosmos DB. |
| Cosmos DB Gremlin API | True graph API, but no DiskANN vector search and no Agent Framework GraphRAG provider. Extra language, weaker Azure AI story. See §4.2. |
| CosmosAIGraph + Apache Jena | Microsoft’s reference OmniRAG sample. Too heavy (in-memory RDF store + extra runtime) for a first Graph RAG. |
| Microsoft GraphRAG research library (`microsoft/graphrag`) | Community detection and hierarchical summaries. Different product. |
| Multi-agent workflows | One agent with retrieval + tools is enough. |
| Scanned / image-only PDFs | Needs OCR. Start with digital (text-extractable) PDFs. |
| Production auth, multi-tenant, hosted UI | CLI query first. |
| Open Gremlin or ad-hoc SQL from the LLM | Easy to generate expensive RU-burning queries. Use fixed tools. |
| Fine-tuning | Retrieval quality comes from schema + chunking first. |

---

## 3. Recommended architecture

Two pipelines share one Cosmos DB account (NoSQL API).

```
PDF files
    │
    ▼
Ingestion pipeline                         Query pipeline
─────────────────                         ──────────────
PDF text extract                           User question
    │                                          │
    ▼                                          ▼
Chunk + embed (Foundry)                    Agent (MAF)
    │                                          │
    ▼                           ┌──────────────┼──────────────┐
LLM entity/relation             │ CosmosGraph  │ Graph tools  │ CosmosHistory
extraction                      │ Context      │ (search,     │ (optional
    │                           │ Provider     │  neighbors,  │  chat memory)
    ▼                           │ (auto RAG)   │  sources)    │
Upsert to Cosmos DB             └──────────────┴──────────────┘
    │                                          │
    └──── Cosmos DB (NoSQL) ◄──────────────────┘
          documents, chunks+vectors,
          entities, relationships
```

**Ingestion** is a batch job you run when PDFs change.  
**Query** is interactive. The agent never parses PDFs at question time; it only reads Cosmos.

### Why this split still holds

Microsoft Agent Framework’s Cosmos package (`agent-framework-azure-cosmos`) stores **chat history and workflow checkpoints**. It does **not** ingest PDFs or retrieve a knowledge graph.

So we own two small pieces that Neo4j used to give us for free:

| Piece | Neo4j (old plan) | Cosmos (this plan) |
| --- | --- | --- |
| PDF → graph | `SimpleKGPipeline` | Our ingest module (PDF → chunk → extract → upsert) |
| Auto RAG into the agent | `Neo4jContextProvider` | Our `CosmosGraphContextProvider` |
| Conversation memory | (optional Neo4j memory) | Official `CosmosHistoryProvider` |

The agent, tools, Foundry models, and “cite or say unknown” rules stay the same.

---

## 4. Stack choices

### 4.1 Recommended (all Azure)

| Layer | Choice | Role |
| --- | --- | --- |
| Language | Python 3.11–3.13 | Agent Framework requires 3.10+. |
| Agents | `agent-framework` + `agent-framework-azure-cosmos` | Agent, sessions, tools; official Cosmos chat history. |
| Models | Microsoft Foundry (chat + embeddings) | Extraction, answering, chunk embeddings. Azure OpenAI is a drop-in alternative. |
| Database | **Azure Cosmos DB for NoSQL** | Documents, chunks + DiskANN vectors, entities, relationships, chat history. |
| Ingestion | Custom pipeline | `pypdf` (v1) or Azure Document Intelligence (later); LLM extraction; Cosmos upserts. |
| App surface | Python CLI | `python -m graph_rag ingest` and `python -m graph_rag query`. |

Use a **serverless** Cosmos account for v1. Cheap at this scale, no Docker graph database, Entra ID auth (`az login`).

The Cosmos Linux emulator exists, but it is optional. Prefer a real serverless account so vector indexing and IAM match production.

### 4.2 Why NoSQL, not Gremlin

Cosmos offers a Gremlin (graph) API. We are **not** using it in v1.

| | NoSQL API (chosen) | Gremlin API |
| --- | --- | --- |
| Vector / hybrid search | Native DiskANN + full-text + hybrid on the same documents | Not the AI vector path Microsoft is investing in |
| Agent Framework package | `CosmosHistoryProvider`, checkpoints | None |
| Graph hops | Entity + relationship documents; 1-hop SQL queries | Native traversals, but partition-key limits hurt multi-hop |
| SDK | `azure-cosmos` (same as the rest of Azure Python) | Separate Gremlin client |
| Fit for “simple Graph RAG” | Good enough: lookup neighbors by id | Overkill until we need deep path algorithms |

Think of NoSQL Graph RAG as two lists in one database:

- A **chunk list** with embeddings (“which paragraphs sound like this question?”).
- An **address book + who-knows-who list** (“which entities connect, and which chunks mentioned them?”).

That is enough for v1. If later we need 5-hop path finding at scale, we can add Gremlin or CosmosAIGraph without changing the agent.

### 4.3 Fallback if Foundry is not ready

Agent Framework also talks to Azure OpenAI. Cosmos stays the same. Only the chat client and embedder change.

### 4.4 Packages

```text
agent-framework
agent-framework-azure-cosmos
azure-cosmos
azure-identity
python-dotenv
pypdf
```

Optional later:

- `azure-ai-documentintelligence` — better PDF layout than `pypdf`
- `rich` — nicer CLI output

---

## 5. How Graph RAG works in this project

Three layers of knowledge, all in Cosmos DB.

### 5.1 Lexical layer (the document skeleton)

Always built. Stored in `documents` and `chunks`.

- `Document` — one PDF (title, path, checksum, ingest date).
- `Chunk` — a slice of text from that PDF, with an embedding and a DiskANN vector index.

This is classic RAG: “find text similar to the question.”

### 5.2 Domain graph (the extracted facts)

Built by the LLM during ingestion. Stored in `entities` and `relationships`.

- Entities: people, organizations, concepts, locations.
- Relationships: `WORKS_AT`, `MENTIONS`, `RELATED_TO`, …
- Each relationship points at source chunk ids so answers can be cited.

This is what makes it Graph RAG: the agent can walk from a company to related people, then to other documents those people appear in.

### 5.3 Intelligence layer (the agent)

Runtime behavior, not a fourth store (except optional chat history):

1. **`CosmosGraphContextProvider`** — before each answer, embed the question, DiskANN-search chunks, attach mentioned entities and one-hop neighbors.
2. **Tools** — the agent can look up an entity, expand neighbors, or fetch source snippets.
3. **`CosmosHistoryProvider`** (optional in Phase 3) — persist the conversation in Cosmos so follow-ups survive a CLI restart.
4. **Instructions** — only answer from retrieved context; cite document title; say you don’t know if Cosmos returned nothing.

v1 uses **one agent**. No workflow graph yet.

---

## 6. Cosmos data model

One database, four containers. Small closed schema. Do not let the LLM invent unlimited entity types.

**Database:** `graph_rag`

| Container | Partition key | Holds |
| --- | --- | --- |
| `documents` | `/id` | One item per PDF |
| `chunks` | `/docId` | Text + embedding; vector index lives here |
| `graph` | `/pk` | Entities and relationships (`kind` discriminator). For v1, `pk = "global"` so 1-hop queries stay in one partition. |
| `sessions` | `/session_id` | Chat history for `CosmosHistoryProvider` |

`pk = "global"` is a deliberate v1 shortcut. A few PDFs will not need sharding. If the graph grows, partition entities by `entityType` and keep a well-known lookup for names.

### Document item

```json
{
  "id": "doc-a1b2",
  "title": "Q2 Credit Memo.pdf",
  "path": "data/pdfs/q2-credit-memo.pdf",
  "checksum": "sha256:...",
  "ingestedAt": "2026-09-03T10:00:00Z"
}
```

### Chunk item

```json
{
  "id": "chunk-a1b2-0007",
  "docId": "doc-a1b2",
  "chunkIndex": 7,
  "text": "...",
  "embedding": [0.01, 0.02],
  "entityIds": ["ent-acme", "ent-jane"]
}
```

Vector policy on `/embedding` (DiskANN for production-shaped accounts; `quantizedFlat` is fine while the corpus is tiny). Embedding dimensions must match the Foundry embedding model (for example 1536 for `text-embedding-3-small`).

### Entity item (`kind: "entity"`)

```json
{
  "id": "ent-acme",
  "pk": "global",
  "kind": "entity",
  "entityType": "Organization",
  "name": "Acme Corp",
  "normalizedName": "acme corp",
  "aliases": ["Acme Corporation"]
}
```

### Relationship item (`kind: "relationship"`)

```json
{
  "id": "rel-jane-works-at-acme",
  "pk": "global",
  "kind": "relationship",
  "relType": "WORKS_AT",
  "fromId": "ent-jane",
  "toId": "ent-acme",
  "sourceChunkIds": ["chunk-a1b2-0007"],
  "sourceDocIds": ["doc-a1b2"]
}
```

Also store `MENTIONS` edges from chunks to entities (or rely on `chunk.entityIds`). Explicit `MENTIONS` relationships make `get_sources` a single query.

### Starter entity types (CLO domain)

| Type | Meaning |
| --- | --- |
| `Person` | Named individual (PM, analyst, CEO, trustee contact) |
| `Organization` | Manager, trustee, borrower, sponsor, bank, counsel |
| `CLO` | The securitization vehicle / deal |
| `Loan` | A credit in the portfolio or warehouse |
| `Tranche` | Class A–E or subordinated notes |
| `Covenant` | OC/IC test, concentration limit, eligibility rule |
| `Location` | Place (New York, Chicago, Cayman Islands, …) |

### Starter relationship types

| Type | From → To |
| --- | --- |
| `MENTIONS` | Chunk → entity (or tracked on the chunk) |
| `WORKS_AT` | Person → Organization |
| `MANAGES` | Organization → CLO |
| `TRUSTEE_OF` | Organization → CLO |
| `CONTAINS` | CLO → Loan |
| `BORROWS` | Organization → Loan |
| `SPONSORS` | Organization → Organization |
| `HAS_TRANCHE` | CLO → Tranche |
| `GOVERNED_BY` | CLO → Covenant |
| `LOCATED_IN` | Organization or CLO → Location |
| `PART_OF` | Organization → Organization |

Sample PDFs in `data/pdfs/` are fictional Northbridge CLO 2024-1 documents that reuse the same manager, trustee, borrowers, and tests so Graph RAG can hop across files.

Entity resolution: normalize names (lowercase, strip punctuation) and upsert on `(entityType, normalizedName)` so “Acme Corp” and “Acme Corporation” can merge via aliases.

---

## 7. Ingestion pipeline (PDF → Cosmos)

There is no `SimpleKGPipeline` equivalent. Keep the pipeline short and linear.

### Steps

1. List PDFs in `data/pdfs`. Skip if `checksum` already exists on a `documents` item.
2. Extract text with `pypdf`.
3. Split into overlapping chunks (~800–1000 characters, ~150 overlap — tune after real PDFs).
4. Embed each chunk with the Foundry embedding model.
5. Upsert `documents` + `chunks` (lexical RAG now works).
6. For each chunk, call the chat model with **structured output** constrained to the schema in §6. Collect entities and relationships.
7. Upsert entities (merge on normalized name) and relationships.
8. Patch `chunk.entityIds`.

### Ingest CLI

```text
python -m graph_rag ingest --pdf-dir data/pdfs
```

- Log per-file success/failure; continue on a bad PDF in early runs.
- Re-ingest of the same file: delete that `docId`’s chunks and its `MENTIONS` / source-linked relationships, then write again — or provide `python -m graph_rag reset` to wipe the database.

### PDF quality rules

- Digital text PDFs only in v1.
- Prefer reports, contracts, and memos over image-heavy slide decks.
- Keep `data/pdfs/` gitignored; use 2–3 sample files for demos.

Later upgrade: Azure Document Intelligence instead of `pypdf` if layout (columns, tables) is poor.

---

## 8. Intelligence layer (query)

### 8.1 Agent shape

One `Agent` from Microsoft Agent Framework:

- **Client:** `FoundryChatClient`.
- **Instructions:** Q&A over the Cosmos knowledge graph; cite sources; do not invent facts.
- **Context providers:**
  - `CosmosGraphContextProvider` (ours) — knowledge retrieval.
  - `CosmosHistoryProvider` (official, optional) — conversation memory.
- **Tools:** the four functions below.
- **Session:** `agent.create_session()` for follow-ups.

The graph context provider injects Cosmos results **before** the model runs. Tools are for extra hops (“show everything connected to Issuer X”).

### 8.2 `CosmosGraphContextProvider` (replaces Neo4jContextProvider)

Implement Agent Framework’s context-provider interface. On each user turn:

1. Embed the question.
2. Run a Cosmos vector query on `chunks` (`VectorDistance`, `top_k=5`). Enable hybrid (vector + full-text) once a full-text policy is on the container.
3. Load `documents` for those chunks (titles/paths).
4. Load entities in `chunk.entityIds`.
5. Load relationships where `fromId` or `toId` is in that entity set (cap, e.g. 20).
6. Format a short context block: chunk text, entity names, triples, document titles.

That is graph-enriched RAG: similar paragraphs **plus** the neighborhood around entities those paragraphs mention.

### 8.3 Tools (explicit graph actions)

Read-only. Parameterized SQL — never pass model-generated queries to Cosmos.

| Tool | Input | Cosmos work |
| --- | --- | --- |
| `search_chunks` | natural language query | embed + vector search on `chunks` |
| `get_entity` | entity name | query `graph` where `kind = "entity"` and name/alias match |
| `expand_neighbors` | entity name, optional rel type | relationships for that id, then load neighbor entities |
| `get_sources` | entity name | chunks/documents linked via `entityIds` or `MENTIONS` |

Pass them as typed Python functions into `Agent(..., tools=[...])`. Agent Framework infers the tool schema from type hints.

### 8.4 Answer contract

Every answer should include:

- Direct answer, or “not in the knowledge graph.”
- Supporting facts as entity–relationship–entity triples when available.
- Source list: PDF title (and chunk index if useful).

### 8.5 Query CLI

```text
python -m graph_rag query "What organizations are mentioned alongside Project Atlas?"
```

Print the answer, then a short “retrieved context” section for debugging.

---

## 9. Proposed repo layout

```text
CLO/
├── docs/
│   └── graph-rag-plan.md
├── src/
│   └── graph_rag/
│       ├── __init__.py
│       ├── config.py                 # env / settings
│       ├── schema.py                 # entity/rel types
│       ├── cosmos_client.py          # account, DB, containers, vector policy
│       ├── ingest.py                 # PDF → chunks → extract → upsert
│       ├── extract.py                # LLM structured entity/relation extraction
│       ├── retrieve.py               # vector search + neighbor expansion
│       ├── context_provider.py       # CosmosGraphContextProvider
│       ├── tools.py                  # agent tools
│       ├── agent.py                  # Agent wiring
│       └── cli.py                    # ingest | query | reset
├── infra/
│   └── cosmos.bicep                  # serverless account + database (optional)
├── data/
│   └── pdfs/
├── requirements.txt
├── .env.example
└── README.md
```

No `docker-compose` graph database. Cosmos lives in Azure.

---

## 10. Environment, IAM, and Azure resources

`.env.example` (never commit keys):

```text
AZURE_COSMOS_ENDPOINT=https://clo-graphrag.documents.azure.com:443/
AZURE_COSMOS_DATABASE=graph_rag
AZURE_COSMOS_DOCUMENTS_CONTAINER=documents
AZURE_COSMOS_CHUNKS_CONTAINER=chunks
AZURE_COSMOS_GRAPH_CONTAINER=graph
AZURE_COSMOS_SESSIONS_CONTAINER=sessions

FOUNDRY_PROJECT_ENDPOINT=https://saumilsheth-7860-resource.services.ai.azure.com/api/projects/saumilsheth-7860
FOUNDRY_MODEL=Kimi-K2.6
AZURE_AI_EMBEDDING_ENDPOINT=https://saumilsheth-7860-resource.cognitiveservices.azure.com
AZURE_AI_EMBEDDING_NAME=text-embedding-3-small
```

**Auth:** `DefaultAzureCredential` / `AzureCliCredential` (`az login`). Prefer Entra ID over account keys. The identity needs Cosmos Data Contributor (or equivalent) on the account.

**Account settings to turn on at create time:**

- API: **NoSQL**
- Capacity: **Serverless**
- Vector search (DiskANN) on the `chunks` container
- Optional: full-text policy on `chunks.text` for hybrid search

A small Bicep file under `infra/` can create the account, database, and containers with the vector indexing policy so setup is repeatable.

---

## 11. Implementation phases

Each phase should be demoable before starting the next.

### Phase 0 — Skeleton (half day)

- Serverless Cosmos account + database (portal or Bicep).
- Python package, `.env.example`, CLI stubs.
- Smoke test: Entra auth, create containers, upsert and read one item.

### Phase 1 — Lexical RAG (1 day)

- Ingest PDFs into `documents` + `chunks` + embeddings only.
- Vector index on `/embedding`.
- Agent with `CosmosGraphContextProvider` doing **chunk search only**.
- Prove: “ask a question, get an answer with PDF citations.”

This is the safety net. If entity extraction is noisy, lexical RAG still works.

### Phase 2 — Domain graph (1–2 days)

- Structured LLM extraction into `graph` entities/relationships.
- Entity upsert by normalized name.
- Context provider also returns one-hop neighbors.
- Inspect items in Azure Portal Data Explorer.

Prove: “who/what is connected to X?” returns graph facts, not just similar paragraphs.

### Phase 3 — Intelligence tools + memory (1 day)

- Add `search_chunks`, `get_entity`, `expand_neighbors`, `get_sources`.
- Optional `CosmosHistoryProvider` on `sessions`.
- Tighten instructions (citations, refusal when empty).
- Multi-turn CLI session.

Prove: follow-ups (“what else is that organization connected to?”) use tools, not guesswork.

### Phase 4 — Hardening (optional)

- Skip already-ingested files (checksum).
- Hybrid search (vector + full-text).
- Eval set: 10 questions with expected entity/document names.
- Log retrieved context and RU charges.
- Optional Document Intelligence for harder PDFs.
- Optional Foundry-hosted agent later.

Do not start Phase 4 until 5–10 real PDFs look clean in Data Explorer.

---

## 12. Risks and how we keep them small

| Risk | Mitigation |
| --- | --- |
| Messy entity labels | Closed schema; reject unknown types in `extract.py`. |
| Duplicate entities | Upsert on `(entityType, normalizedName)`; keep `aliases`. |
| Cross-partition graph queries | v1: all graph items share `pk = "global"`. |
| High RU from vector search | Serverless + small `top_k`; DiskANN; don’t scan the container in Python. |
| Bad PDF text | Start with clean digital PDFs; swap in Document Intelligence if needed. |
| Hallucinated answers | Instructions + “cite or say unknown”; tools are read-only parameterized queries. |
| We had to write the pipeline ourselves | Keep ingest/retrieve/provider as three small modules; no mini-framework. |
| Cosmos history vs graph mixed together | Separate `sessions` container; never store chat in `graph`. |

---

## 13. Success criteria for v1

The project is “done enough” when all of these are true:

1. Dropping 3 PDFs into `data/pdfs` and running ingest produces documents, chunks, entities, and relationships visible in Cosmos Data Explorer.
2. A CLI question about content in those PDFs returns a grounded answer with document titles.
3. A question about something **not** in the PDFs is refused, not invented.
4. A relationship question (“how are A and B connected?”) uses graph neighbors, not only vector-similar text.
5. Re-running ingest on the same folder does not require hand-written Cosmos queries.

---

## 14. Locked Azure decisions

Taken from the signed-in Azure CLI account on 3 September 2026. Remaining product choices (PDF domain, sample files) are still open.

| Decision | Value |
| --- | --- |
| Subscription | `Azure subscription 1` (`3fc99a76-c448-4a6e-b802-2fb7f6085a06`) |
| Resource group | `rg-saumilsheth-2906` |
| Region | `eastus2` (same as existing Foundry) |
| Models | **Microsoft Foundry**, not a standalone Azure OpenAI account |
| Foundry account | `saumilsheth-7860-resource` (kind `AIServices`) |
| Foundry project | `saumilsheth-7860` |
| Project endpoint | `https://saumilsheth-7860-resource.services.ai.azure.com/api/projects/saumilsheth-7860` |
| Chat model | Existing deployment `Kimi-K2.6` |
| Embedding model | `text-embedding-3-small` (1536 dimensions, GlobalStandard) |
| Cosmos account | `clo-graphrag` — serverless NoSQL, `eastus2` |
| Cosmos database | `graph_rag` |
| UI | CLI only for v1 |
| Chat memory | `CosmosHistoryProvider` in Phase 3, not Phase 1 |

Still open: none for domain — sample PDFs are Northbridge CLO 2024-1 (fictional) in `data/pdfs/`.

Auth: `az login` as `saumilsheth@hotmail.com` with Entra ID. No account keys in git.

---

## 15. Suggested first implementation step

Azure decisions in section 14 are locked. Next:

1. Finish Cosmos account + database + containers (Phase 0 smoke: upsert one item).
2. Scaffold the Python package and ingest **chunks only** (Phase 1).
3. Wire a single Agent Framework agent with `CosmosGraphContextProvider`.
4. Only then turn on entity extraction (Phase 2).

Lexical RAG first, graph enrichment second. That order avoids debugging extraction, retrieval, and the agent all at once.

---

## References

- [Microsoft Agent Framework overview](https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview)
- [Azure Cosmos DB integrations for AI (includes Agent Framework)](https://learn.microsoft.com/en-us/azure/cosmos-db/gen-ai/integrations)
- [Azure Cosmos DB integrated vector store](https://learn.microsoft.com/en-us/azure/cosmos-db/vector-search)
- [AI knowledge graphs on Cosmos DB (CosmosAIGraph / OmniRAG)](https://learn.microsoft.com/en-us/azure/cosmos-db/gen-ai/cosmos-ai-graph)
- [`agent-framework-azure-cosmos` on PyPI](https://pypi.org/project/agent-framework-azure-cosmos/)
- [Adding tools in Agent Framework](https://learn.microsoft.com/en-us/agent-framework/journey/adding-tools)
