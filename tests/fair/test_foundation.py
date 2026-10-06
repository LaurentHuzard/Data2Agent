"""The Foundation surface must not promote local proxies to FAIR verdicts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from data2agent.ingest import ingest
from data2agent.mcp import DatasetService

EXPECTED = {
    "F1",
    "F2",
    "F3",
    "F4",
    "A1",
    "A1.1",
    "A1.2",
    "A2",
    "I1",
    "I2",
    "I3",
    "R1",
    "R1.1",
    "R1.2",
    "R1.3",
}


def test_every_foundation_item_is_addressable_and_links_to_known_rules(ingested):
    service = DatasetService(ingested.output_dir, mode="fair-rules")
    listing = service.list_fair_principles()["principles"]
    assert {item["id"] for item in listing} == EXPECTED
    known_rules = {item["id"] for item in service.list_fair_rules()["rules"]}
    for item in listing:
        detail = service.get_fair_principle(item["id"])
        assert detail["source"].startswith("https://www.gofair.foundation/")
        assert detail["required_evidence"] and detail["next_action"]
        assert detail["acceptance_criteria"]
        assert item["id"] in detail["acceptance_criteria"]
        assert len(detail["evidence_plan"]) == len(detail["required_evidence"])
        assert all(need["action"] for need in detail["evidence_plan"])
        assert all(
            need["evidence_origin"] in {
                "local",
                "live_publication",
                "external_document",
                "reviewed_assertion",
                "validator_report",
            }
            for need in detail["evidence_plan"]
        )
        assert set(detail["local_rules"]) <= known_rules
    with pytest.raises(KeyError, match="unknown FAIR principle"):
        service.get_fair_principle("F9")


def test_every_item_has_a_recommendation_without_an_unsupported_pass(ingested):
    service = DatasetService(ingested.output_dir, mode="fair-deterministic")
    assessment = service.assess_fair_principles()
    assert assessment["summary"] == {"total": 15, "pass": 0, "unknown": 15}
    assert {item["principle"] for item in assessment["results"]} == EXPECTED
    for item in assessment["results"]:
        assert item["result"] == "unknown"
        assert item["evidence"] and item["required_evidence"]
        assert item["recommendations"]
        assert len(item["evidence_plan"]) == len(item["required_evidence"])
        assert all(need["status"] == "not_verified" for need in item["evidence_plan"])
        assert all(need["action"] in item["recommendations"] for need in item["evidence_plan"])
    f4 = next(item for item in assessment["results"] if item["principle"] == "F4")
    assert f4["local_findings"][0]["result"] == "pass"
    assert f4["observed_local_gaps"] == []
    assert f4["result"] == "unknown", "structured metadata does not prove indexing"


def test_one_item_keeps_its_local_gap_and_scoped_action(ingested):
    service = DatasetService(ingested.output_dir, mode="fair-deterministic")
    item = service.assess_fair_principles("I2")["results"][0]
    assert item["principle"] == "I2"
    assert item["local_findings"][0]["result"] == "fail"
    assert len(item["observed_local_gaps"]) == 1
    assert item["observed_local_gaps"][0]["rule_id"] == "I2-VOCABULARY-REFERENCED"
    assert item["observed_local_gaps"][0]["evidence"]
    assert len(item["recommendations"]) == 5
    assert "bare namespace" in item["recommendations"][0]
    a2 = service.assess_fair_principles("A2")["results"][0]
    assert a2["local_findings"] == []
    assert a2["observed_local_gaps"] == []
    assert len(a2["evidence_plan"]) == 3
    with pytest.raises(KeyError, match="unknown FAIR principle"):
        service.assess_fair_principles("Z9")


def test_missing_metadata_produces_repair_then_discovery_evidence_steps(tmp_path: Path):
    source = tmp_path / "dataset"
    source.mkdir()
    (source / "data.csv").write_text("id,value\n1,2\n", encoding="utf-8")
    ingested = ingest(source, tmp_path / "out")
    service = DatasetService(ingested.output_dir, mode="fair-deterministic")
    item = service.assess_fair_principles("F2")["results"][0]
    assert item["result"] == "unknown"
    assert item["observed_local_gaps"][0]["rule_id"] == "F2-METADATA-PRESENT"
    assert "metadata record" in item["recommendations"][0]
    assert "discovery metadata schema" in item["recommendations"][-1]


def test_foundation_assessment_matches_public_schema(ingested):
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "fair-foundation-assessment.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assessment = DatasetService(
        ingested.output_dir, mode="fair-deterministic"
    ).assess_fair_principles()
    jsonschema.validate(assessment, schema)
    unpublished = DatasetService(
        ingested.output_dir, mode="fair-deterministic"
    ).assess_fair_principles(unpublished=True)
    jsonschema.validate(unpublished, schema)


def test_unpublished_assessment_marks_only_release_dependent_requirements(ingested):
    service = DatasetService(ingested.output_dir, mode="fair-deterministic")
    assessment = service.assess_fair_principles(unpublished=True)
    by_id = {item["principle"]: item for item in assessment["results"]}
    assert assessment["publication_state"] == "user_declared_unpublished"
    assert assessment["summary"] == {"total": 15, "pass": 0, "unknown": 15}
    assert [need["status"] for need in by_id["F4"]["evidence_plan"]] == [
        "not_verified", "pending_publication", "pending_publication"
    ]
    assert all(
        need["status"] == "not_verified" for need in by_id["I2"]["evidence_plan"]
    )
    assert all(
        need["action"].startswith("Prepare this for release")
        for need in by_id["F4"]["evidence_plan"][1:]
    )
    with pytest.raises(ValueError, match="cannot be probed"):
        service.assess_fair_principles(
            unpublished=True,
            live=True,
            publication_url="https://doi.org/10.5281/zenodo.0000000",
        )
