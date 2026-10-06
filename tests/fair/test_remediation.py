"""Recommendations must reflect an actual finding, not an inapplicable rule."""

from __future__ import annotations

from data2agent.profiles.fair.remediation import build_recommendations


def test_inapplicable_missing_values_do_not_request_token_decisions():
    assessment = {
        "results": [
            {
                "rule_id": "R1.3-MISSING-VALUES-DECLARED",
                "result": "not_applicable",
                "rationale": "no profiled tables",
                "evidence": [{"check": "dataset.file-count", "result": 0}],
            }
        ]
    }
    assert build_recommendations(assessment)["recommendations"] == []
