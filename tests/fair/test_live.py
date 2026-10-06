"""Opt-in publication checks can verify only evidence they actually observe."""

from __future__ import annotations

import pytest

from data2agent.mcp import DatasetService
from data2agent.profiles.fair.live import (
    PublicURLRequired,
    bound_doi_url,
    matching_declared_doi,
    probe_public_url,
)


def _reached(url: str, *, identifier_seen: bool = False) -> dict:
    return {
        "method": "bounded-public-http-get",
        "source": url,
        "observed_at": "2026-09-30T12:00:00Z",
        "result": "reached",
        "final_url": "https://repository.example/record",
        "status_code": 200,
        "identifier_seen_in_sample": identifier_seen,
        "chain": [{"url": url, "status_code": 302}],
    }


def test_doi_binding_requires_exact_dataset_identifier():
    identifiers = ["10.5281/zenodo.0000000"]
    assert bound_doi_url("https://doi.org/10.5281/zenodo.0000000", identifiers)
    assert not bound_doi_url("https://doi.org/10.5281/zenodo.0000001", identifiers)
    assert not bound_doi_url("https://fake.example/10.5281/zenodo.0000000", identifiers)
    assert not bound_doi_url("https://doi.org/10.5281/zenodo.0000000?token=x", identifiers)
    assert (
        matching_declared_doi(
            "https://doi.org/10.5281/zenodo.0000000", ["10.1234/unrelated", *identifiers]
        )
        == identifiers[0]
    )


def test_sample_doi_match_requires_token_boundaries(monkeypatch):
    url = "https://doi.org/10.1234/dataset"
    monkeypatch.setattr(
        "data2agent.profiles.fair.live._fetch_once",
        lambda value: {
            "url": value,
            "status_code": 200,
            "location": None,
            "content_type": "text/html",
            "body_sample": "Unrelated reference: 10.1234/dataset-extra",
        },
    )
    observation = probe_public_url(url, expected_identifier="10.1234/dataset")
    assert observation["result"] == "reached"
    assert observation["identifier_seen_in_sample"] is False


def test_live_probe_uses_the_doi_that_matched_the_url(ingested, monkeypatch):
    service = DatasetService(ingested.output_dir, mode="fair-deterministic")
    url = "https://doi.org/10.5281/zenodo.0000000"
    captured = {}

    def probe(value, *, expected_identifier):
        captured["identifier"] = expected_identifier
        return _reached(value)

    monkeypatch.setattr("data2agent.profiles.fair.live.probe_public_url", probe)
    service.assess_fair_principles("A1.1", live=True, publication_url=url)
    assert captured["identifier"] == "10.5281/zenodo.0000000"


def test_local_assessment_never_calls_network(ingested, monkeypatch):
    service = DatasetService(ingested.output_dir, mode="fair-deterministic")

    def unexpected(*args, **kwargs):
        raise AssertionError("unexpected network call")

    monkeypatch.setattr("data2agent.profiles.fair.live.probe_public_url", unexpected)
    assert service.assess_fair_principles("A1.1")["results"][0]["result"] == "unknown"
    with pytest.raises(ValueError, match="opt-in"):
        service.assess_fair_principles(publication_url="https://doi.org/10.5281/zenodo.0000000")
    with pytest.raises(ValueError, match="requires publication_url"):
        service.assess_fair_principles(live=True)


def test_bound_live_http_records_partial_a1_1_evidence_without_false_pass(ingested, monkeypatch):
    service = DatasetService(ingested.output_dir, mode="fair-deterministic")
    url = "https://doi.org/10.5281/zenodo.0000000"
    monkeypatch.setattr(
        "data2agent.profiles.fair.live.probe_public_url",
        lambda value, **kwargs: _reached(value, identifier_seen=True),
    )
    assessment = service.assess_fair_principles(live=True, publication_url=url)
    by_id = {item["principle"]: item for item in assessment["results"]}
    assert assessment["publication_binding"] is True
    assert assessment["summary"] == {"total": 15, "pass": 0, "unknown": 15}
    assert by_id["A1.1"]["result"] == "unknown"
    assert by_id["A1.1"]["evidence_plan"][0]["status"] == "observed_partial"
    assert all(need["status"] == "not_verified" for need in by_id["A1.1"]["evidence_plan"][1:])
    assert by_id["A1.1"]["evidence"][0]["observed_at"]
    assert by_id["A1"]["result"] == "unknown"
    assert by_id["F1"]["result"] == "unknown"
    assert by_id["F4"]["result"] == "unknown"


def test_unbound_or_failed_live_observation_cannot_pass(ingested, monkeypatch):
    service = DatasetService(ingested.output_dir, mode="fair-deterministic")
    monkeypatch.setattr(
        "data2agent.profiles.fair.live.probe_public_url",
        lambda value, **kwargs: _reached(value),
    )
    unbound = service.assess_fair_principles(
        "A1.1", live=True, publication_url="https://repository.example/record"
    )
    assert unbound["publication_binding"] is False
    assert unbound["results"][0]["result"] == "unknown"
    monkeypatch.setattr(
        "data2agent.profiles.fair.live.probe_public_url",
        lambda value, **kwargs: {**_reached(value), "result": "not_reached", "status_code": 404},
    )
    failed = service.assess_fair_principles(
        "A1.1", live=True, publication_url="https://doi.org/10.5281/zenodo.0000000"
    )
    assert failed["results"][0]["result"] == "unknown"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost/",
        "https://user:pass@example.org/",
        "https://example.org/?token=secret",
        "https://example.org/?session=secret",
        "https://example.org/?signature=secret",
        "file:///etc/passwd",
    ],
)
def test_probe_rejects_private_or_credential_bearing_urls(url):
    with pytest.raises(PublicURLRequired):
        probe_public_url(url)
