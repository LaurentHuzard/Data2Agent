# Fork contribution workflow

This fork develops generic improvements for Neuronautix/Data2Agent and supplies pinned integration commits to Data2AgentBench.

## Branches

- `main`: existing historical integration state; do not force-reset or rewrite it during this transition. Avoid merging new fork-only changes here.
- `integration/bench`: integration branch initially preserved at `76bd06b20c3c3884ac232d1fc19f52a8d7c15114`. Proposed integrations require a PR and validation. Do not repin completed benchmark campaigns.
- `upstream-pr/*`: narrowly scoped branches created from a fetched, identified `upstream/main` commit, never from the divergent fork main. Check the upstream comparison before opening a PR.

## Contribution path

1. Review changes and tests in a fork PR. Where a historical fork PR depends on unrelated patches, extract only the required functionality onto a fresh upstream-based branch.
2. Verify the exact extracted branch. Distinguish checks run on this head from historical results on another head. Open an upstream draft when full validation/review remains outstanding.
3. Submit the generic contribution to Neuronautix/Data2Agent. Keep benchmark budgets, models, scoring and campaign policies in the benchmark repository.
4. If the benchmark needs a change before upstream acceptance, propose a separate PR into `integration/bench`. Never merge a clean upstream branch with the whole integration branch merely to resolve its integration needs.
5. After upstream acceptance, qualify a new upstream commit for a new campaign. Preserve all old dependency pins and artifacts.
6. Let fork main converge toward upstream by subsequent integration of accepted commits. Any later destructive reset or branch deletion requires a separate decision; it is not part of this migration.

## Initial migration — 2026-10-06

Upstream base: `b1b09fd6005d6f2ff4edad06896942b9b94d46f8`.

| Contribution | Fork origin | Upstream PR |
| --- | --- | --- |
| Aggregate contributor provenance | #3 | https://github.com/Neuronautix/Data2Agent/pull/83 |
| Closed MCP contracts, typed filters, visible expected errors | #1, #4, #5, functional changes in #6 | https://github.com/Neuronautix/Data2Agent/pull/84 |

Both upstream branches contain one independent commit on the upstream base. The unrelated FAIR formatting from #6 was excluded. Metrics and unit_metrics nested schemas remain outside this extraction.

Targeted Python/MCP checks passed on the extracted changes. Full pytest and Ruff have not been run in the migration environment; upstream drafts must receive full validation and human review. The historical 589-test claim on fork #6 is not validation of either extracted head.
