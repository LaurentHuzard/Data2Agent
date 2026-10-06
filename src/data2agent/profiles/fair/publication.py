"""Evidence-aware Zenodo publication choices; this module never deposits data."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any

_SOURCES = {
    "records": "https://help.zenodo.org/docs/deposit/about-records/",
    "drafts": "https://help.zenodo.org/docs/deposit/create-new-upload/",
    "sharing": "https://help.zenodo.org/docs/share/user-sharing/",
    "community_review": "https://help.zenodo.org/docs/share/submit-for-review/",
    "sandbox": "https://developers.zenodo.org/",
    "fair_principles": "https://www.gofair.foundation/fair-principles",
}

_OPTIONS = [
    {
        "id": "local_preparation",
        "use_when": "Real files have not been approved for deposit on an external service.",
        "visibility": "Keep the dataset local while decisions and metadata are prepared.",
        "fair_implication": "Published discovery, access, and persistence remain unverified.",
        "source": None,
    },
    {
        "id": "sandbox_test",
        "use_when": "Testing the Zenodo workflow with synthetic or cleared example files.",
        "visibility": "Separate test environment; do not treat it as private archival storage.",
        "fair_implication": (
            "A test DOI or search result is not evidence of production publication."
        ),
        "source": _SOURCES["sandbox"],
    },
    {
        "id": "unpublished_draft",
        "use_when": "Preparing real data and metadata before a publication decision.",
        "visibility": "Unpublished; selected people can be given draft access.",
        "fair_implication": "DOI registration and public discovery are still pending publication.",
        "source": _SOURCES["drafts"],
    },
    {
        "id": "published_restricted",
        "use_when": (
            "The owner approves public record metadata and depositing files, "
            "but not public files."
        ),
        "visibility": "Metadata public; files restricted; DOI registered.",
        "fair_implication": (
            "Restricted files can be FAIR if the access procedure is clear; "
            "verify DOI, indexing, and authorization after publication."
        ),
        "source": _SOURCES["records"],
    },
    {
        "id": "published_public",
        "use_when": "The owner approves public metadata and public files after content review.",
        "visibility": "Metadata and files public; DOI registered.",
        "fair_implication": (
            "Verify actual DOI resolution, indexing, and file retrieval after publication."
        ),
        "source": _SOURCES["records"],
    },
    {
        "id": "published_embargoed",
        "use_when": "The owner approves future public files and sets a release date.",
        "visibility": "Metadata public immediately; files restricted until the embargo ends.",
        "fair_implication": (
            "Verify metadata discovery and the access procedure now, then file access "
            "after the embargo date."
        ),
        "source": _SOURCES["drafts"],
    },
]

_QUESTIONS = {
    "owner_approval": "Has the rights holder approved depositing these exact files on Zenodo?",
    "metadata_public_approved": (
        "Has the owner reviewed the proposed title, names, description, and other metadata "
        "for public disclosure?"
    ),
    "files_reviewed": (
        "Have the exact files and their contents been reviewed for confidentiality, "
        "third-party rights, and unintended disclosure?"
    ),
    "files_public_approved": (
        "After publication, may everyone download the files, or should access be restricted?"
    ),
}


def advise_publication(
    assessment: dict[str, Any],
    *,
    purpose: str = "explore",
    owner_approval: bool | None = None,
    metadata_public_approved: bool | None = None,
    files_reviewed: bool | None = None,
    files_public_approved: bool | None = None,
    test_with_real_data: bool = False,
    community_submission: bool = False,
    embargo_until: str | None = None,
) -> dict[str, Any]:
    """Choose a provisional publication path from checks and explicit owner answers.

    The answers are declarations, not verified facts or permission to publish.
    Even a candidate published path requires a separate release decision.
    """
    if purpose not in {"explore", "test", "release"}:
        raise ValueError("purpose must be explore, test, or release")
    answers = {
        "owner_approval": owner_approval,
        "metadata_public_approved": metadata_public_approved,
        "files_reviewed": files_reviewed,
        "files_public_approved": files_public_approved,
    }
    if any(value is not None and type(value) is not bool for value in answers.values()):
        raise ValueError("publication decision answers must be true, false, or omitted")
    if type(test_with_real_data) is not bool or type(community_submission) is not bool:
        raise ValueError("test_with_real_data and community_submission must be booleans")
    if embargo_until is not None:
        try:
            embargo_date = date.fromisoformat(embargo_until)
        except (TypeError, ValueError) as error:
            raise ValueError("embargo_until must be an ISO date (YYYY-MM-DD)") from error
        if embargo_date <= date.today():
            raise ValueError("embargo_until must be a future date")
        if files_public_approved is not True:
            raise ValueError("an embargo needs explicit approval for future public file access")

    by_rule = {item["rule_id"]: item for item in assessment["results"]}
    relevant = (
        "F2-METADATA-PRESENT",
        "R1.1-LICENCE-DECLARED",
        "R1.2-PROVENANCE-DECLARED",
    )
    findings = [
        {
            "rule_id": rule_id,
            "result": by_rule[rule_id]["result"],
            "rationale": by_rule[rule_id].get("rationale", ""),
        }
        for rule_id in relevant
    ]
    metadata_ready = by_rule["F2-METADATA-PRESENT"]["result"] == "pass"
    terms_declared = by_rule["R1.1-LICENCE-DECLARED"]["result"] == "pass"
    provenance_declared = by_rule["R1.2-PROVENANCE-DECLARED"]["result"] == "pass"
    explicit_release_answers = (
        owner_approval is True
        and metadata_public_approved is True
        and files_reviewed is True
        and files_public_approved is not None
    )
    questions = [
        {"key": key, "question": question}
        for key, question in _QUESTIONS.items()
        if answers[key] is None and not (purpose == "test" and not test_with_real_data)
    ]
    if purpose == "explore":
        questions.insert(
            0,
            {
                "key": "purpose",
                "question": (
                    "Are you testing the workflow, preparing a real unpublished draft, "
                    "or deciding whether to publish now?"
                ),
            },
        )
    reasons: list[str] = []
    if purpose == "test" and not test_with_real_data:
        path = "sandbox_test"
        reasons.append("A workflow test needs no real unpublished dataset bytes.")
    elif purpose == "test" and test_with_real_data and owner_approval is not True:
        path = "local_preparation"
        reasons.append(
            "Permission to deposit these real files on Zenodo is not approved or confirmed."
        )
    elif purpose == "test" and test_with_real_data:
        path = "unpublished_draft"
        reasons.append("Use an unpublished production draft; the sandbox can be cleared.")
    elif owner_approval is not True:
        path = "local_preparation"
        reasons.append(
            "Permission to deposit these real files on Zenodo is not approved or confirmed."
        )
    elif purpose != "release":
        path = "unpublished_draft"
        reasons.append("Publication has not been requested or cleared by this decision record.")
    elif not explicit_release_answers:
        path = "unpublished_draft"
        reasons.append("Publication needs affirmative owner, metadata, and file review decisions.")
    elif not metadata_ready or not terms_declared or not provenance_declared:
        path = "unpublished_draft"
        reasons.append(
            "Recognized dataset metadata, usage terms, and provenance should be "
            "completed before release."
        )
    else:
        path = (
            "published_embargoed"
            if embargo_until
            else "published_public" if files_public_approved else "published_restricted"
        )
        reasons.append(
            "This is a candidate route from supplied decisions, not a release approval "
            "or a full FAIR verdict."
        )

    actions: list[str] = []
    if not metadata_ready:
        actions.append("Prepare and review a machine-readable dataset description for the deposit.")
    if not terms_declared:
        actions.append(
            "Have the rights holder choose and record file usage terms or access conditions."
        )
    if not provenance_declared:
        actions.append("Document the experiment's origin and processing history for reuse.")
    if path == "local_preparation":
        actions.append("Keep real files local; obtain owner approval before a Zenodo upload.")
    elif path == "sandbox_test":
        actions.append("Use synthetic or explicitly cleared files in Zenodo Sandbox.")
    elif path == "unpublished_draft":
        actions.append("Save a Zenodo draft; review its files and metadata before publishing.")
    elif path == "published_restricted":
        actions.append("Publish with restricted files and document how access may be requested.")
        actions.append("Check that the recorded usage terms fit restricted access.")
    elif path == "published_embargoed":
        actions.append(
            "Publish with restricted files and confirm automatic public release "
            f"on {embargo_until}."
        )
    else:
        actions.append("Publish only the owner-approved files with public visibility.")
    if community_submission:
        reasons.append(
            "A community curator's acceptance can automatically publish a submitted draft."
        )
        actions.append("Confirm the community review workflow before submitting a draft.")

    return {
        "guide_version": "2026-09-30",
        "repository": "Zenodo",
        "dataset_id": assessment["dataset_id"],
        "purpose": purpose,
        "recommended_path": path,
        "recommendation_is_release_approval": False,
        "local_findings_are_narrow_checks": True,
        "reasoning": reasons,
        "questions": questions,
        "declared_answers": answers,
        "embargo_until": embargo_until,
        "local_readiness_findings": findings,
        "next_actions": actions,
        "options": deepcopy(_OPTIONS),
        "sources": dict(_SOURCES),
        "external_action_taken": False,
    }
