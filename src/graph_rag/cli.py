"""Command line: ping Cosmos, then later ingest PDFs and ask questions."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from graph_rag.config import GRAPH_PARTITION_VALUE, load_settings
from graph_rag.cosmos_client import GraphStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Graph RAG over PDFs in Azure Cosmos DB")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ping", help="Create containers and write/read one test item")
    sub.add_parser("reset", help="Delete all items in documents, chunks, and graph")

    ingest = sub.add_parser("ingest", help="Load PDFs into the graph (Phase 1+)")
    ingest.add_argument("--pdf-dir", default="data/pdfs")

    query = sub.add_parser("query", help="Ask a question (Phase 1+)")
    query.add_argument("question", nargs="+")

    args = parser.parse_args(argv)

    if args.command == "ping":
        return cmd_ping()
    if args.command == "reset":
        return cmd_reset()
    if args.command == "ingest":
        print("Ingest is not implemented yet. Phase 0 is ping only.")
        return 1
    if args.command == "query":
        print("Query is not implemented yet. Phase 0 is ping only.")
        return 1
    return 1


def cmd_ping() -> int:
    settings = load_settings()
    store = GraphStore(settings)
    item = {
        "id": "ping-check",
        "pk": GRAPH_PARTITION_VALUE,
        "kind": "entity",
        "entityType": "Concept",
        "name": "Graph RAG ping",
        "normalizedName": "graph rag ping",
        "checkedAt": datetime.now(timezone.utc).isoformat(),
    }
    store.graph.upsert_item(item)
    read_back = store.graph.read_item(item="ping-check", partition_key=GRAPH_PARTITION_VALUE)
    print("Connected to Cosmos DB")
    print(f"  endpoint : {settings.cosmos_endpoint}")
    print(f"  database : {settings.cosmos_database}")
    print(f"  chat     : {settings.foundry_model}")
    print(f"  embed    : {settings.embedding_name}")
    print(f"  ping item: {read_back['name']} ({read_back['id']})")
    return 0


def cmd_reset() -> int:
    settings = load_settings()
    store = GraphStore(settings)
    deleted = 0
    for container, pk_field in (
        (store.documents, "id"),
        (store.chunks, "docId"),
        (store.graph, "pk"),
    ):
        for item in container.query_items(
            query="SELECT c.id, c.{pk} AS pk FROM c".format(pk=pk_field),
            enable_cross_partition_query=True,
        ):
            container.delete_item(item=item["id"], partition_key=item["pk"])
            deleted += 1
    print(f"Deleted {deleted} items from documents, chunks, and graph.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
