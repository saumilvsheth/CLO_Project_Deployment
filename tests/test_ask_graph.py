from clo_intel.answer import format_graph_answer
from clo_intel.graph import build_graph_documents, facts_for_question
from clo_intel.sample_book import DEALS, deal_field_ids


def test_apex_holdings_include_six_deals_and_oc():
    docs = build_graph_documents(extracted={}, reviews={})
    facts = facts_for_question("Which CLOs hold Apex Industrial Holdings?", docs=docs, cites={})
    text = facts["text"]
    assert "obligor:apex" in facts["matched"]
    assert facts["focus"]["id"] == "obligor:apex"
    for series in (
        "Northbridge CLO 2024-1",
        "Ironwood CLO 2024-1",
        "Redrock CLO 2024-3",
        "Fairmont CLO 2025-1",
        "Pinecrest CLO 2025-1",
        "Northstar CLO 2023-1",
    ):
        assert series in text
    assert "Holds Apex Industrial Holdings" in text
    assert "Class A/B OC test: FAIL" in text
    assert "Cascade Health" not in text
    compound = facts_for_question(
        "Which six deals hold Apex, and which of them failed Class A/B OC?",
        docs=docs,
        cites={},
    )
    assert "Silverlake CLO 2024-2" not in compound["text"]
    assert compound["text"].count("Holds Apex Industrial Holdings") == 6


def test_redrock_oc_is_fail():
    docs = build_graph_documents(extracted={}, reviews={})
    facts = facts_for_question("Did the Class A/B OC test pass in Redrock CLO 2024-3?", docs=docs, cites={})
    assert "Redrock CLO 2024-3" in facts["text"]
    assert "OC test: FAIL" in facts["text"]


def test_short_deal_name_focuses_that_deal():
    docs = build_graph_documents(extracted={}, reviews={})
    cases = (
        ("Redrock", "deal:redrock-clo-2024-3", "Redrock CLO 2024-3"),
        ("What about Redrock", "deal:redrock-clo-2024-3", "Redrock CLO 2024-3"),
        ("Did Redrock fail OC?", "deal:redrock-clo-2024-3", "Redrock CLO 2024-3"),
        ("Oakmont", "deal:oakmont-clo-2024-2", "Oakmont CLO 2024-2"),
        ("Did Oakmont fail the OC test?", "deal:oakmont-clo-2024-2", "Oakmont CLO 2024-2"),
    )
    for question, node_id, series in cases:
        facts = facts_for_question(question, docs=docs, cites={})
        assert facts["focus"]["id"] == node_id, question
        assert series in facts["text"], question
        assert facts["text"].count("Deal ") == 1, question
        assert "OC test: FAIL" in facts["text"]


def test_hitl_override_wins_in_graph_facts():
    redrock = next(deal for deal in DEALS if deal.id == "redrock-clo-2024-3")
    field_id = deal_field_ids(redrock)["oc_result"]
    docs = build_graph_documents(
        extracted={},
        reviews={field_id: {"status": "overridden", "value": "130.0%"}},
    )
    facts = facts_for_question(
        "Redrock CLO Class A/B OC result",
        docs=docs,
        cites={},
        extracted={},
        reviews={field_id: {"status": "overridden", "value": "130.0%"}},
    )
    assert "130.0%" in facts["text"]
    assert "overridden" in facts["text"]
    assert "OC test: PASS" in facts["text"]
    assert facts["waterfall"]
    assert facts["waterfall"][0]["redirect"] is False
    assert "Subordinated residual:" in facts["text"]


def _summary(question: str, **kwargs) -> str:
    reviews = kwargs.get("reviews") or {}
    extracted = kwargs.get("extracted") or {}
    docs = kwargs.get("docs") or build_graph_documents(extracted=extracted, reviews=reviews)
    graph = facts_for_question(question, docs=docs, cites={}, extracted=extracted, reviews=reviews)
    text = format_graph_answer(graph)
    assert text.lower().startswith("executive summary")
    assert "\nDetails\n" in text
    return text.split("\nDetails\n", 1)[0]


def test_ask_answer_leads_with_executive_summary():
    summary = _summary("Did Redrock fail OC?")
    assert "failed the Class A/B OC test" in summary
    assert "121.2%" in summary
    assert "122.5%" in summary
    assert "redirected to Class A principal" in summary
    assert "[" not in summary
    details = format_graph_answer(
        facts_for_question(
            "Did Redrock fail OC?",
            docs=build_graph_documents(extracted={}, reviews={}),
            cites={},
            extracted={},
            reviews={},
        )
    ).split("\nDetails\n", 1)[1]
    assert "Watchlist: Dustline Mining Corp." in details
    assert "Coverage-test redirect:" in details
    apex = _summary("Which CLOs hold Apex?")
    assert "6 CLOs" in apex
    assert "Redrock" in apex
    assert "failed Class A/B OC" in apex
    assert "redirect leftover interest to Class A principal" in apex
    redrock = next(deal for deal in DEALS if deal.id == "redrock-clo-2024-3")
    field_id = deal_field_ids(redrock)["oc_result"]
    override = _summary(
        "Redrock CLO Class A/B OC result",
        reviews={field_id: {"status": "overridden", "value": "130.0%"}},
    )
    assert "passed" in override.lower()
    assert "overrode" in override.lower()
    assert "residual" in override.lower()
    assert "redirected to Class A principal" not in override
