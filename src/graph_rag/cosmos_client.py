"""Open the Cosmos database and containers created by Azure CLI / Bicep.

AAD data-plane tokens can read and write items, but they cannot create
databases or containers. Those are created once with `az cosmosdb sql ...`.
"""

from __future__ import annotations

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential

from graph_rag.config import Settings


class GraphStore:
    """Thin wrapper: one Cosmos database with four containers."""

    def __init__(self, settings: Settings) -> None:
        credential = DefaultAzureCredential()
        self.client = CosmosClient(settings.cosmos_endpoint, credential=credential)
        self.database = self.client.get_database_client(settings.cosmos_database)
        self.documents = self.database.get_container_client(settings.documents_container)
        self.chunks = self.database.get_container_client(settings.chunks_container)
        self.graph = self.database.get_container_client(settings.graph_container)
        self.sessions = self.database.get_container_client(settings.sessions_container)
