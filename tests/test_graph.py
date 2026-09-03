from clo_intel.graph import build_graph_documents
from clo_intel.sample_book import DEALS


def test_graph_has_nodes_and_edges_for_every_deal():
    docs = build_graph_documents(extracted={}, reviews={})
    nodes = [d for d in docs if d["kind"] == "node"]
    edges = [d for d in docs if d["kind"] == "edge"]
    assert {d["id"] for d in nodes if d["label"] == "Deal"} == {f"deal:{deal.id}" for deal in DEALS}
    assert len(edges) > len(DEALS)
    assert all("pk" in d and "id" in d for d in docs)


def test_apex_is_held_by_multiple_deals():
    docs = build_graph_documents(extracted={}, reviews={})
    holds = [d for d in docs if d["label"] == "HOLDS" and d["toId"] == "obligor:apex"]
    assert len(holds) >= 3
    series = {d["fromId"] for d in holds}
    assert "deal:northbridge-clo-2024-1" in series
    assert "deal:ironwood-clo-2024-1" in series


def test_hitl_override_changes_manager_node():
    reviews = {
        "manager": {"status": "overridden", "value": "Override Credit LLC"},
    }
    docs = build_graph_documents(extracted={}, reviews=reviews)
    managers = [d for d in docs if d["label"] == "Manager" and d["name"] == "Override Credit LLC"]
    assert managers
    northbridge = next(d for d in docs if d["id"] == "e:managed-by:northbridge-clo-2024-1:manager")
    assert northbridge["toId"] == managers[0]["id"]
    assert northbridge["source"] == "overridden"


def test_neighborhood_includes_apex_from_northbridge():
    from clo_intel.graph import neighborhood

    data = neighborhood("deal:northbridge-clo-2024-1")
    labels = {n["label"] for n in data["nodes"]}
    assert "Manager" in labels
    assert "Trustee" in labels
    assert "Obligor" in labels
    assert any(n["id"] == "obligor:apex" for n in data["nodes"])
    apex = neighborhood("obligor:apex")
    deals = [n for n in apex["nodes"] if n["label"] == "Deal"]
    assert len(deals) >= 3
