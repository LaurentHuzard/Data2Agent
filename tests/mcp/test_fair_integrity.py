"""FAIR findings must describe the same source bytes recorded at ingest."""

from __future__ import annotations

from pathlib import Path

import pytest

from data2agent.errors import OutputError
from data2agent.ingest import ingest
from data2agent.mcp import DatasetService


@pytest.mark.parametrize("changed_file", ["dataset_description.json", "animals.csv"])
@pytest.mark.parametrize(
    "assessment", ["run_fair_check", "assess_fair_principles", "plan_fair_publication"]
)
def test_fair_assessment_rejects_changed_source_file(
    dataset_copy: Path, tmp_path: Path, changed_file: str, assessment: str
) -> None:
    ingested = ingest(dataset_copy, tmp_path / "out")
    service = DatasetService(ingested.output_dir, mode="fair-deterministic")

    # Every advice path works for the intact snapshot.
    initial = getattr(service, assessment)()
    if assessment == "plan_fair_publication":
        assert initial["recommended_path"]
    else:
        assert initial["results"]

    source_file = dataset_copy / changed_file
    source_file.write_bytes(source_file.read_bytes() + b"\nchanged after ingest\n")

    with pytest.raises(OutputError) as error:
        getattr(service, assessment)()
    assert changed_file in str(error.value)
    assert "re-ingest" in str(error.value)


def test_single_fair_rule_rejects_missing_source_file(dataset_copy: Path, tmp_path: Path) -> None:
    ingested = ingest(dataset_copy, tmp_path / "out")
    service = DatasetService(ingested.output_dir, mode="fair-deterministic")
    (dataset_copy / "animals.csv").unlink()

    with pytest.raises(OutputError, match="animals.csv"):
        service.run_fair_check("F2-METADATA-PRESENT")
