"""Evidence-linked, non-mutating FAIR remediation guidance.

Recommendations are deterministic projections of assessment results. They
describe candidate actions and verification steps; they never edit dataset
bytes or decide owner-controlled values such as licences and missing tokens.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_METADATA_RULES = {
    "F1-PID-METADATA",
    "F2-METADATA-PRESENT",
    "F3-METADATA-LINKS-DATA",
    "F4-METADATA-MACHINE-READABLE",
    "R1.3-COMMUNITY-STANDARD",
}


def build_recommendations(assessment: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic remediation actions supported by a FAIR assessment."""
    results = {item["rule_id"]: item for item in assessment.get("results", [])}
    recommendations: list[dict[str, Any]] = []

    def add(
        recommendation_id: str,
        priority: str,
        title: str,
        why: str,
        actions: list[str],
        verification: str,
        rule_ids: set[str],
        example: str | None = None,
        owner_decision: bool = False,
    ) -> None:
        findings = [
            {
                "rule_id": rule_id,
                "result": results[rule_id]["result"],
                "rationale": results[rule_id].get("rationale", ""),
                "evidence": results[rule_id].get("evidence", []),
            }
            for rule_id in sorted(rule_ids)
            if rule_id in results and results[rule_id]["result"] in {"fail", "unknown"}
        ]
        if not findings:
            return
        recommendations.append(
            {
                "id": recommendation_id,
                "priority": priority,
                "title": title,
                "why": why,
                "actions": actions,
                "example": example,
                "verification": verification,
                "owner_decision_required": owner_decision,
                "findings": findings,
            }
        )

    if any(
        rule_id in results and results[rule_id]["result"] != "pass" for rule_id in _METADATA_RULES
    ):
        add(
            "FAIR-METADATA-01",
            "P1",
            "Add a machine-readable dataset descriptor",
            (
                "One or more metadata or identifier checks found a gap. A descriptor "
                "gives identifiers, resource links, provenance, licence, and vocabulary "
                "references one explicit home. Use a community format such as a Frictionless "
                "Data Package when it fits the dataset."
            ),
            [
                (
                    "Review existing data dictionaries, workbook notes, and protocol or "
                    "presentation documents for authoritative metadata before duplicating it."
                ),
                (
                    "Create a `datapackage.json` at the package root; replace every placeholder "
                    "with curator-verified information."
                ),
                (
                    "List each intended resource using a stable path relative to the descriptor. "
                    "Identify raw data, processed outputs, and supporting documents in names or "
                    "descriptions."
                ),
                (
                    "Add the persistent identifier only after one has been assigned. Add licence "
                    "and provenance fields only after the responsible owner confirms them."
                ),
                (
                    "Re-ingest and rerun the FAIR assessment; inspect any remaining "
                    "findings rather than assuming the descriptor passes automatically."
                ),
            ],
            (
                "F2 should recognise the descriptor; F3 should confirm that its resource paths "
                "name the intended files; F4 should assess the JSON metadata. Review F1, R1.1, "
                "R1.2, and R1.3 separately."
            ),
            _METADATA_RULES
            | {"I2-VOCABULARY-REFERENCED", "R1.1-LICENCE-DECLARED", "R1.2-PROVENANCE-DECLARED"},
            example=(
                "{\n"
                '  "profile": "data-package",\n'
                '  "name": "<stable-dataset-name>",\n'
                '  "title": "<curator-written title>",\n'
                '  "description": "<what this package contains and how it was produced>",\n'
                '  "resources": [\n'
                '    {"name": "<resource-name>", "path": "<relative-path>", '
                '"format": "<verified format>", "mediatype": "<matching media type>", '
                '"schema": {"fields": [{"name": "<field-name>", "type": "<field-type>"}], '
                '"missingValues": [""]}}\n'
                "  ]\n"
                "}"
            ),
            owner_decision=True,
        )

    add(
        "FAIR-MISSING-01",
        "P0",
        "Decide what each ambiguous token means before declaring it missing",
        (
            "A token can mean a missing observation, a valid category, or something else. "
            "Guessing changes downstream counts and can erase meaning."
        ),
        [
            (
                "Review each token in the evidence and source context with the data owner or "
                "protocol owner."
            ),
            (
                "If a token means missing, list it under the relevant resource schema's "
                "`missingValues`; if it is a valid value, preserve it and document its meaning "
                "instead."
            ),
            (
                "Re-ingest with the descriptor and compare missingness counts before and after. "
                "Confirm that only the intended tokens changed classification."
            ),
        ],
        (
            "The R1.3 missing-values rule should pass only when every absence-like token "
            "has a declared, owner-approved interpretation."
        ),
        {"R1.3-MISSING-VALUES-DECLARED"},
        example=(
            "{\n"
            '  "schema": {\n'
            '    "fields": [{"name": "<field-name>", "type": "<field-type>"}],\n'
            '    "missingValues": ["", "<owner-confirmed token>"]\n'
            "  }\n"
            "}"
        ),
        owner_decision=True,
    )

    add(
        "FAIR-LICENCE-01",
        "P1",
        "Record the reuse terms chosen by the rights holder",
        "A licence is a permission decision, not something the scanner can infer from the files.",
        [
            (
                "Have the rights holder choose the licence or access terms that fit this "
                "dataset and its consent, contract, and publication constraints."
            ),
            (
                "Record the exact licence name and authoritative URI in the dataset descriptor. "
                "If redistribution is not permitted, state the access conditions instead of "
                "adding an open licence."
            ),
        ],
        (
            "R1.1 should change only after the chosen licence or access declaration is "
            "present in recognised metadata."
        ),
        {"R1.1-LICENCE-DECLARED"},
        example=(
            '{\n  "licenses": [{"name": "<chosen licence identifier>", '
            '"path": "<authoritative licence URI>"}]\n}'
        ),
        owner_decision=True,
    )

    add(
        "FAIR-PROVENANCE-01",
        "P1",
        "Describe who produced the data and how it was derived",
        (
            "The ingest provenance describes this Data2Agent run; it does not replace "
            "provenance for the experiment or subsequent transformations."
        ),
        [
            (
                "Add curator-confirmed creator or organization, collection date or period, "
                "method/protocol reference, and source or parent dataset where known."
            ),
            (
                "For processed resources, name the software or transformation and its version "
                "when available; leave unknown details explicitly unknown."
            ),
        ],
        (
            "The narrow R1.2 provenance rule should pass when recognised dataset "
            "metadata contains provenance about the data itself, not merely the ingest run."
        ),
        {"R1.2-PROVENANCE-DECLARED"},
        example=(
            '{\n  "contributors": [{"title": "<verified creator or organization>", '
            '"role": "author"}]\n}'
        ),
        owner_decision=True,
    )

    add(
        "FAIR-VOCABULARY-01",
        "P2",
        "Reference controlled vocabularies for fields that have agreed terms",
        (
            "The assessment cannot determine vocabulary use without readable recognised "
            "metadata. Vocabulary choice depends on the domain and field meaning."
        ),
        [
            (
                "Ask the domain curator which fields have controlled terms and select the "
                "appropriate maintained vocabulary for those fields."
            ),
            (
                "Record the vocabulary name, version when available, and stable namespace URI "
                "in metadata. Do not map terms automatically from column names alone."
            ),
        ],
        (
            "Rerun I2 after metadata is recognised. A vocabulary reference establishes the "
            "reference only; it does not validate every cell value."
        ),
        {"I2-VOCABULARY-REFERENCED"},
        example=(
            '{\n  "keywords": ["<curator-approved term>"],\n'
            '  "description": "Controlled vocabulary: <name, version, namespace URI>"\n}'
        ),
        owner_decision=True,
    )

    add(
        "FAIR-FORMAT-01",
        "P2",
        "Offer open tabular exports alongside workbook originals",
        (
            "The current FAIR profile flags the observed workbook format as outside its "
            "explicit open-format list. Preserve the workbook where it carries formulas or "
            "layout that an export cannot retain."
        ),
        [
            (
                "For tabular resources intended for exchange, export CSV or TSV copies with "
                "UTF-8 encoding and a documented delimiter, header, and missing-value "
                "convention."
            ),
            (
                "Compare row and column counts and representative values against the workbook "
                "export before publishing the copy; keep the original workbook as a companion "
                "where needed."
            ),
        ],
        (
            "Re-ingest the exported package and confirm the profile reports the intended "
            "open formats and the exported tables retain the expected shape."
        ),
        {"I1-DATA-FORMATS-OPEN"},
    )

    add(
        "FAIR-PUBLISH-01",
        "P3",
        "Verify retrieval at the eventual publication location",
        (
            "A local snapshot cannot establish whether a repository serves the dataset over "
            "a standard protocol."
        ),
        [
            (
                "When release is approved, deposit the package in a repository that provides a "
                "stable landing page and standard HTTPS download or API access."
            ),
            (
                "Record the repository URL and test retrieval from the published location. For "
                "restricted data, document the access request route and its protocol."
            ),
        ],
        (
            "A1 remains unknown in this local-only assessment; it needs a check against the "
            "actual published endpoint."
        ),
        {"A1-RETRIEVAL-PROTOCOL"},
        owner_decision=True,
    )

    add(
        "FAIR-PID-01",
        "P3",
        "Assign and externally resolve a persistent identifier when ready to publish",
        (
            "The local identifier rules cannot establish published resolution. "
            "An opt-in Foundation assessment can record a public DOI resolver "
            "observation when a matching DOI is declared in dataset metadata."
        ),
        [
            (
                "Obtain a DOI or other persistent identifier through the selected repository "
                "after the record is ready."
            ),
            (
                "Put the assigned identifier in the recognised dataset metadata, then verify "
                "resolution using the identifier provider or repository. Do not invent an "
                "identifier or treat a DOI-shaped string as proof of resolution."
            ),
        ],
        (
            "Re-ingest to check identifier presence. The narrow F1-PID-RESOLVABLE "
            "rule remains unknown; use an opt-in publication probe to record a "
            "bounded DOI resolver observation in the Foundation assessment."
        ),
        {"F1-PID-METADATA", "F1-PID-RESOLVABLE"},
        owner_decision=True,
    )

    priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    recommendations.sort(key=lambda item: (priority_rank[item["priority"]], item["id"]))
    return {
        "recommendation_version": "0.1.0",
        "assessment": {
            "profile": assessment.get("profile", {}),
            "assessment_version": assessment.get("assessment_version"),
            "generator": assessment.get("generator", {}),
        },
        "summary": {
            "recommendation_count": len(recommendations),
            "priorities": {
                priority: sum(item["priority"] == priority for item in recommendations)
                for priority in ("P0", "P1", "P2", "P3")
            },
            "mutates_source": False,
        },
        "recommendations": recommendations,
    }


def write_recommendations(output_dir: Path, assessment: dict[str, Any]) -> tuple[Path, Path]:
    """Write the machine-readable plan and its human-readable Markdown view."""
    plan = build_recommendations(assessment)
    json_path = output_dir / "recommendations.json"
    json_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# FAIR remediation plan",
        "",
        (
            "Actions below come from the recorded assessment outcomes and evidence. They "
            "are suggestions, not edits."
        ),
        (
            "The source dataset is unchanged. Human approval is required for licences, "
            "identifiers, vocabularies, and token meaning."
        ),
        (
            "Example JSON snippets contain placeholders and must be completed with verified "
            "information before use."
        ),
        "",
        "## Prioritized actions",
        "",
    ]
    if not plan["recommendations"]:
        lines.extend(["No remediation actions were triggered by this assessment.", ""])
    for item in plan["recommendations"]:
        rules = ", ".join(
            f"`{finding['rule_id']}` ({finding['result']})" for finding in item["findings"]
        )
        lines.extend(
            [
                f"### {item['priority']} — {item['title']}",
                "",
                f"**Why this is recommended:** {item['why']}",
                f"**Assessment findings:** {rules}",
                "",
            ]
        )
        lines.extend(f"{i}. {action}" for i, action in enumerate(item["actions"], 1))
        lines.extend(["", f"**How to verify:** {item['verification']}", ""])
        if item.get("example"):
            lines.extend(["**Example:**", "", "```json", item["example"], "```", ""])
        if item["owner_decision_required"]:
            lines.extend(["**Owner or curator decision required.**", ""])
        lines.extend(["**Evidence checked:**", ""])
        for finding in item["findings"]:
            lines.append(f"- `{finding['rule_id']}`: {finding['rationale']}")
        lines.append("")

    lines.extend(
        [
            "## Next pass",
            "",
            (
                "After an approved metadata change or a separate open-format export, re-ingest "
                "into a new output directory, verify source integrity, rerun the FAIR "
                "assessment, and compare the findings. Keep the original dataset unchanged."
            ),
            "",
        ]
    )
    report_dir = output_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    md_path = report_dir / "fair-remediation-plan.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
