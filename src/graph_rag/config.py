"""Load settings from environment variables (and an optional .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# text-embedding-3-small always returns this many numbers per vector.
EMBEDDING_DIMENSIONS = 1536
GRAPH_PARTITION_VALUE = "global"


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Missing environment variable {name}. Copy .env.example to .env and fill it in."
        )
    return value


@dataclass(frozen=True)
class Settings:
    cosmos_endpoint: str
    cosmos_database: str
    documents_container: str
    chunks_container: str
    graph_container: str
    sessions_container: str
    foundry_project_endpoint: str
    foundry_model: str
    embedding_endpoint: str
    embedding_name: str


def load_settings() -> Settings:
    return Settings(
        cosmos_endpoint=_require("AZURE_COSMOS_ENDPOINT"),
        cosmos_database=os.getenv("AZURE_COSMOS_DATABASE", "graph_rag"),
        documents_container=os.getenv("AZURE_COSMOS_DOCUMENTS_CONTAINER", "documents"),
        chunks_container=os.getenv("AZURE_COSMOS_CHUNKS_CONTAINER", "chunks"),
        graph_container=os.getenv("AZURE_COSMOS_GRAPH_CONTAINER", "graph"),
        sessions_container=os.getenv("AZURE_COSMOS_SESSIONS_CONTAINER", "sessions"),
        foundry_project_endpoint=_require("FOUNDRY_PROJECT_ENDPOINT"),
        foundry_model=os.getenv("FOUNDRY_MODEL", "Kimi-K2.6"),
        embedding_endpoint=_require("AZURE_AI_EMBEDDING_ENDPOINT"),
        embedding_name=os.getenv("AZURE_AI_EMBEDDING_NAME", "text-embedding-3-small"),
    )
