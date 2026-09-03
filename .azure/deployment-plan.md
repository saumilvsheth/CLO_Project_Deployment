# Azure Deployment Plan

> **Status:** Executing (Phase 1 local application rebuild). Azure resource provisioning is deferred until this codebase is ready for azure-validate.

Generated: 2026-09-03

---

## 1. Project Overview

**Goal:** Rebuild CLO Document Intelligence on Azure: ingest trustee reports, indentures, offering memoranda, and rating reports; extract layout/tables; map fields to a canonical schema; then (later) GraphRAG and an agent query layer.

**Path:** New Project (workspace was wiped; git history retained)

**Product phases (from architecture):**

1. Extraction only (stages 1–4 + HITL, guardrails, observability)
2. Knowledge graph (Cosmos DB + Azure AI Search)
3. Intelligence layer (Foundry Agent Service / tool-calling)
4. Production hardening (CI/CD, canary, full guardrails)

This iteration implements **Phase 1 as a local-first Python system** with Azure adapters. No `azd up` in this pass (prior App Service VM quota in eastus2 was 0).

---

## 2. Requirements

| Attribute | Value |
|-----------|-------|
| Classification | Development / POC toward production |
| Scale | Small (sample CLO book; spiky document-arrival later) |
| Budget | Cost-optimized (reuse existing Foundry + Cosmos; serverless later) |
| **Subscription** | Azure subscription 1 (`3fc99a76-c448-4a6e-b802-2fb7f6085a06`) — from prior session |
| **Location** | eastus2 — from prior session |
| **Resource group** | `rg-saumilsheth-2906` |

---

## 3. Components Detected

| Component | Type | Technology | Path |
|-----------|------|------------|------|
| Pipeline orchestrator | Worker | Python 3.11 | `src/clo_intel/pipeline.py` |
| Extraction | Worker | Document Intelligence + PyMuPDF fallback | `src/clo_intel/extract/` |
| Contextualization | Worker | Azure AI Foundry (`Kimi-K2.6`) | `src/clo_intel/contextualize.py` |
| Review API + UI | API / Frontend | FastAPI + static HTML | `apps/review/` |
| Structured store | Data | Local JSON now; Cosmos adapter later | `src/clo_intel/store.py` |

---

## 4. Recipe Selection

**Selected:** Bicep (single-cloud Azure), not AZD in this pass.

**Rationale:** Architecture specifies Bicep. Prior App Service quota blocked PaaS web SKUs; Phase 1 glue runs locally. Container Apps + Functions Bicep will be added before azure-validate, not deployed now.

---

## 5. Architecture

**Stack:** Serverless ingestion later (Event Grid + Durable Functions) + Container Apps for glue. Phase 1 runs in-process locally.

### Service Mapping

| Component | Azure Service | SKU / notes |
|-----------|---------------|-------------|
| Source PDFs | Blob Storage (hot) / ADLS Gen2 | Reuse later; local `data/pdfs` now |
| Ingestion | Event Grid + Durable Functions | Stubbed locally |
| Layout / tables | Azure AI Document Intelligence | `prebuilt-layout`; PyMuPDF fallback |
| OCR fallback | Azure AI Vision | Not wired until DI misses scans |
| Contextualization | Azure AI Foundry | Existing project `saumilsheth-7860`, chat `Kimi-K2.6` |
| Graph store (Phase 2) | Cosmos DB NoSQL (existing `clo-graphrag`) | Architecture also allows Gremlin; keep NoSQL to reuse account |
| Vector index (Phase 2) | Azure AI Search | Not provisioned yet |
| Agent (Phase 3) | Foundry Agent Service | Stub tools only |
| Guardrails | Azure AI Content Safety | Adapter + Pydantic schema now |
| API | Container Apps (later) | Local uvicorn now |
| Observability | App Insights | Structured logs now; SDK when connection string set |

### Supporting Services

| Service | Purpose |
|---------|---------|
| Log Analytics | Unified logs (Phase 4) |
| Application Insights | Traces with document/deal/stage |
| Key Vault | Secrets (Managed Identity preferred) |
| Managed Identity | Service-to-service auth |

---

## 6. Provisioning Limit Checklist

**No new Azure resources are deployed in this iteration.** Existing resources:

| Resource Type | Number to Deploy now | Total After Deployment | Limit/Quota | Notes |
|---------------|----------------------|------------------------|-------------|-------|
| Microsoft.DocumentDB/databaseAccounts | 0 (exists: `clo-graphrag`) | 1 | 50 / region (docs) | Reuse |
| Microsoft.CognitiveServices/accounts (Foundry) | 0 (exists: `saumilsheth-7860-resource`) | 1 | subscription quota | Reuse chat + embeddings |
| Microsoft.Web/serverfarms (App Service) | 0 | 0 | **Total VMs = 0 in eastus2** | Do not use App Service; prior deploy failed |
| Microsoft.App/containerApps | 0 | 0 | not fetched this pass | Deferred |
| Microsoft.Storage/storageAccounts | 0 | existing RG storage if any | 250 / region (docs) | Local files for Phase 1 |

**Status:** ✅ No new provision in this pass. ❌ App Service blocked in eastus2. Next Azure wave should target Container Apps / Functions, not App Service.

---

## 7. Execution Checklist

### Phase 1: Planning
- [x] Analyze workspace (empty except `.git` + `.env`)
- [x] Gather requirements (user architecture markdown)
- [x] Confirm subscription and location from prior session
- [x] Resource inventory (no new deploy)
- [x] Quota notes (App Service VMs = 0)
- [x] Select Bicep recipe
- [x] Plan architecture
- [ ] **User approved Azure provision** (not requested yet)

### Phase 2: Execution
- [x] Rebuild Phase 1 application locally
- [ ] Generate full production Bicep
- [ ] Dockerfiles for Container Apps
- [ ] Plan status Ready for Validation (only when infra is complete)

---

## 8. Files to Generate

| File | Purpose | Status |
|------|---------|--------|
| `.azure/deployment-plan.md` | This plan | ✅ |
| `docs/architecture.md` | Product architecture | ✅ |
| Phase 1 Python package | Pipeline + review UI | ✅ this pass |
| `infra/main.bicep` | Production IaC | ⏳ later |
| `azure.yaml` | AZD | ⏳ later |

---

## 9. Next Steps

> Current: Phase 1 local rebuild

1. Land ingest → extract → contextualize → HITL on sample PDFs
2. When ready to provision: Blob + Document Intelligence + App Insights, then Container Apps
3. Phase 2 graph + AI Search; Phase 3 agent tools
