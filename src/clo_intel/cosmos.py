"""Cosmos DB helpers for the Phase 2 knowledge graph."""

from __future__ import annotations

from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient, ContainerProxy

from clo_intel.config import env


def graph_container() -> ContainerProxy:
    endpoint = env("AZURE_COSMOS_ENDPOINT")
    database = env("AZURE_COSMOS_DATABASE") or "graph_rag"
    name = env("AZURE_COSMOS_GRAPH_CONTAINER") or "graph"
    if not endpoint:
        raise RuntimeError("AZURE_COSMOS_ENDPOINT is not set.")
    client = CosmosClient(
        endpoint,
        credential=DefaultAzureCredential(exclude_interactive_browser_credential=True),
    )
    return client.get_database_client(database).get_container_client(name)


def upsert_documents(docs: list[dict]) -> int:
    container = graph_container()
    for doc in docs:
        container.upsert_item(doc)
    return len(docs)


def query_items(query: str, parameters: list[dict] | None = None) -> list[dict]:
    container = graph_container()
    return list(
        container.query_items(
            query=query,
            parameters=parameters or [],
            enable_cross_partition_query=True,
        )
    )
