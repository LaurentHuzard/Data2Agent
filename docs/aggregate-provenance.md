# Aggregate input provenance

`aggregate` and `aggregate_join` return a checksum-bound input envelope with
`scope: "post_filter_pre_metric"`. Its locators describe rows entering the whole
query after filtering, not membership in each group or metric.
`row_occurrences_entering_aggregation` counts located input occurrences, including
join duplicates. Missing locators make completeness false where expected row
counts are available; this counter does not include those unlocated rows.

`complete: true` means the input locators are represented exactly within the
output cap and no unit policy dropped listed rows. It does not mean every listed
row contributed a numeric value to every result. For example, a mean over values
1, 3, 5 and a missing value is 3: its envelope can be complete with four input
rows although only three values enter the mean. Unit aggregation can also be
complete when all units feed a group, without providing per-metric membership.

`rows_dropped_by_unit_policy` reports listed rows excluded by unit policy,
including missing units, excluded inconsistent units and refused aggregation.
These cases mark the envelope and its inputs incomplete. Missing locators,
unsupported locator types and output caps can also prevent completeness.
Source integrity failure withholds content and omits provenance; absence never
means completeness.

Consumers must retain scope, query filters, grouping, metrics, missingness and
unit policies alongside locators. Citation existence, observation through tools,
and sufficient support for a claim remain distinct checks. A complete input
envelope alone is not proof of exact per-metric contributors. Offline evaluators
must determine sufficiency against their independent evidence contract.
