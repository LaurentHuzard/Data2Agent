"""Publication guidance must depend on evidence and explicit owner choices."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from data2agent.ingest import ingest
from data2agent.mcp import DatasetService
from data2agent.profiles.fair.publication import advise_publication


def _service(ingested) -> DatasetService:
    return DatasetService(ingested.output_dir, mode="fair-deterministic")


def test_unanswered_real_dataset_stays_local(ingested):
    advice = _service(ingested).plan_fair_publication()
    assert advice["recommended_path"] == "local_preparation"
    assert advice["recommendation_is_release_approval"] is False
    assert advice["external_action_taken"] is False
    assert {item["key"] for item in advice["questions"]} == {
        "purpose",
        "owner_approval",
        "metadata_public_approved",
        "files_reviewed",
        "files_public_approved",
    }
    assert {item["id"] for item in advice["options"]} == {
        "local_preparation",
        "sandbox_test",
        "unpublished_draft",
        "published_restricted",
        "published_public",
        "published_embargoed",
    }
    assert all(item["fair_implication"] for item in advice["options"])


def test_sandbox_is_for_synthetic_testing_and_real_test_needs_owner_approval(ingested):
    service = _service(ingested)
    synthetic = service.plan_fair_publication(purpose="test")
    assert synthetic["recommended_path"] == "sandbox_test"
    assert synthetic["questions"] == []
    real_unapproved = service.plan_fair_publication(purpose="test", test_with_real_data=True)
    assert real_unapproved["recommended_path"] == "local_preparation"
    real_approved = service.plan_fair_publication(
        purpose="test", test_with_real_data=True, owner_approval=True
    )
    assert real_approved["recommended_path"] == "unpublished_draft"


@pytest.mark.parametrize(
    ("public_files", "embargo_until", "expected"),
    [
        (False, None, "published_restricted"),
        (True, None, "published_public"),
        (True, "2099-12-31", "published_embargoed"),
    ],
)
def test_cleared_release_choice_distinguishes_file_visibility(
    ingested, public_files, embargo_until, expected
):
    advice = _service(ingested).plan_fair_publication(
        purpose="release",
        owner_approval=True,
        metadata_public_approved=True,
        files_reviewed=True,
        files_public_approved=public_files,
        embargo_until=embargo_until,
    )
    assert advice["recommended_path"] == expected
    assert advice["recommendation_is_release_approval"] is False
    assert advice["questions"] == []


def test_known_metadata_and_terms_gaps_hold_release_at_draft(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "data.csv").write_text("id,value\n1,2\n", encoding="utf-8")
    ingested = ingest(source, tmp_path / "out")
    advice = _service(ingested).plan_fair_publication(
        purpose="release",
        owner_approval=True,
        metadata_public_approved=True,
        files_reviewed=True,
        files_public_approved=False,
    )
    assert advice["recommended_path"] == "unpublished_draft"
    assert {item["result"] for item in advice["local_readiness_findings"]} >= {"fail"}
    assert any("usage terms" in action for action in advice["next_actions"])


def test_missing_provenance_keeps_a_public_release_at_draft(ingested):
    assessment = _service(ingested).run_fair_check()
    provenance = next(
        item for item in assessment["results"] if item["rule_id"] == "R1.2-PROVENANCE-DECLARED"
    )
    provenance["result"] = "fail"
    advice = advise_publication(
        assessment,
        purpose="release",
        owner_approval=True,
        metadata_public_approved=True,
        files_reviewed=True,
        files_public_approved=True,
    )
    assert advice["recommended_path"] == "unpublished_draft"
    assert any("processing history" in action for action in advice["next_actions"])


def test_community_submission_surfaces_auto_publication_and_invalid_answers(ingested):
    service = _service(ingested)
    advice = service.plan_fair_publication(community_submission=True)
    assert any("automatically publish" in reason for reason in advice["reasoning"])
    with pytest.raises(ValueError, match="purpose"):
        service.plan_fair_publication(purpose="private")
    with pytest.raises(ValueError, match="answers"):
        service.plan_fair_publication(owner_approval="yes")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="future public file access"):
        service.plan_fair_publication(files_public_approved=False, embargo_until="2099-12-31")


def test_publication_guidance_matches_schema(ingested):
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = (
        Path(__file__).resolve().parents[2] / "schemas" / "fair-publication-advice.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(_service(ingested).plan_fair_publication(), schema)
    jsonschema.validate(_service(ingested).plan_fair_publication(purpose="test"), schema)
