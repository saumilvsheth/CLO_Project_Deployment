# Graph RAG (PDF → Cosmos DB → Agent)

Python Graph RAG using Microsoft Agent Framework and Azure Cosmos DB for NoSQL. Planning notes: [docs/graph-rag-plan.md](docs/graph-rag-plan.md).

## Azure (already chosen)

- Subscription: `Azure subscription 1`
- Resource group: `rg-saumilsheth-2906` (`eastus2`)
- Foundry: project `saumilsheth-7860`, chat `Kimi-K2.6`, embeddings `text-embedding-3-small`
- Cosmos: serverless account `clo-graphrag`, database `graph_rag`

Sign in once: `az login`

## Setup

Use Python 3.11 (3.14 is not the target runtime).

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
az login
python -m graph_rag ping
```

`ping` writes one test item to the `graph` container. PDF ingest and question answering are Phase 1.

Sample (fictional) CLO PDFs live in `data/pdfs/`. Regenerate with:

```bash
pip install fpdf2
python scripts/generate_sample_pdfs.py
```
