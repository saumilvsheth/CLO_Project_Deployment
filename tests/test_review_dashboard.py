import json

from clo_intel import review


def test_is_numeric_field_uses_kind_and_value():
    assert review.is_numeric_field({"kind": "money", "value": "n/a"})
    assert review.is_numeric_field({"kind": "oc_ratio", "value": "122.5%"})
    assert review.is_numeric_field({"kind": "", "value": "$248,000,000"})
    assert review.is_numeric_field({"value": "122.5%"})
    assert not review.is_numeric_field({"kind": "", "value": "Northbridge CLO 2024-1"})
    assert not review.is_numeric_field({"kind": "text", "value": "$248,000,000"})


def test_resolution_dashboard_counts_numeric_only(monkeypatch, tmp_path):
    path = tmp_path / "reviews.json"
    path.write_text(
        json.dumps(
            {
                "reviews": {
                    "f-money": {
                        "id": "f-money",
                        "status": "approved",
                        "value": "$1",
                        "reviewedAt": "2026-01-01T00:00:00+00:00",
                    },
                    "f-oc": {
                        "id": "f-oc",
                        "status": "overridden",
                        "value": "110%",
                        "reviewedAt": "2026-01-02T00:00:00+00:00",
                    },
                }
            }
        )
    )
    monkeypatch.setattr(review, "REVIEWS_PATH", path)
    monkeypatch.setattr(review, "list_runs", lambda: [{"documentId": "doc-a"}])
    monkeypatch.setattr(
        review,
        "load_run",
        lambda _id: {
            "extraction": {
                "document_id": "doc-a",
                "filename": "northbridge-clo-2024-1-term-sheet.pdf",
                "document_type": "term_sheet",
                "deal_id": "northbridge",
                "fields": [
                    {"id": "f-name", "label": "Deal name", "value": "Northbridge", "citations": [{"page": 1}]},
                    {
                        "id": "f-money",
                        "label": "Class A par",
                        "value": "$1",
                        "kind": "money",
                        "confidence": 0.95,
                        "citations": [{"page": 1}],
                    },
                    {
                        "id": "f-oc",
                        "label": "OC trigger",
                        "value": "122.5%",
                        "kind": "oc_ratio",
                        "confidence": 0.8,
                        "citations": [{"page": 2}],
                    },
                    {
                        "id": "f-alloc",
                        "label": "Allocation",
                        "value": "$5,000,000",
                        "kind": "money",
                        "confidence": 0.7,
                        "citations": [{"page": 1}],
                    },
                ],
            }
        },
    )

    dash = review.resolution_dashboard()
    totals = dash["totals"]
    assert totals["total"] == 3
    assert totals["open"] == 1
    assert totals["pending"] == 1
    assert totals["approved"] == 1
    assert totals["overridden"] == 1
    assert totals["closed"] == 2
    assert dash["open"][0]["fieldId"] == "f-alloc"
    assert dash["approved"][0]["fieldId"] == "f-money"
    assert [item["fieldId"] for item in dash["closed"]] == ["f-oc", "f-money"]
    assert dash["documents"][0]["pending"] == 1
    assert dash["documents"][0]["open"] is True
