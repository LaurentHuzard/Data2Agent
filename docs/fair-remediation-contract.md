# FAIR remediation contract

Assessment answers **what the profile could establish**. The remediation plan
answers **what a curator can do next**. They are separate projections of the
same assessment, so advice cannot change a verdict or add unsupported facts.

## Pipeline

```text
immutable dataset
  → deterministic ingest + evidence ledger
  → deterministic FAIR assessment
  → prioritized recommendations linked to rule findings
  → curator approves and edits a separate metadata/package copy
  → re-ingest + re-assess + compare
```

`data2agent assess <output>` writes `assessment.json`,
`recommendations.json`, and `report/fair-remediation-plan.md`. Run
`data2agent recommend <output>` to regenerate the latter two from the saved
assessment. This version proposes changes; it does not edit the source dataset
or metadata automatically. The same finding-linked catalog is available through
the `get_fair_recommendations` MCP tool in `fair-deterministic` mode.

## Recommendation requirements

- Each action names the assessment rule IDs and carries their result, rationale,
  and evidence from `assessment.json`.
- Actions have an ordered priority, concrete steps, an example where useful, and
  a way to verify the improvement on the next ingest/assessment pass.
- Owner-controlled choices (licence, persistent identifier, vocabulary, and the
  meaning of ambiguous tokens) are explicit decisions. Data2Agent must not fill
  these in by inference.
- `unknown` and `not_applicable` remain visible. A recommendation may identify
  what new evidence could settle an unknown, but must not describe the unknown
  as a failure or promise a pass.
- Examples use placeholders and are scaffolds, not assertions about the
  dataset. User-approved edits belong in a curated copy; the original stays
  immutable.

## POC limits

The first action catalog covers the shipped FAIR rules. Its deterministic
guidance is a starting point for human review, not a domain-specific data
curation agent. Later iterations can add a review UI, before/after comparison,
broader repository checks, and approved metadata patch generation. A patch must remain
separate from the source and must be re-ingested before any improvement is
reported as achieved.
