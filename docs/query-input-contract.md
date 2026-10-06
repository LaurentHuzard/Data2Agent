# Query input and error contract

`filter_rows`, `aggregate` and `aggregate_join` publish a closed nested filter
schema. Each predicate contains `column`, `op`, and (except for missingness
operators) `value`. The operator enum is generated from the deterministic query
registry, not maintained separately in a harness prompt.

```json
{"column": "group", "op": "eq", "value": "control"}
```

`in` and `not_in` require an array value. `is_missing` and `is_not_missing` may
omit value. String/numeric values are not coerced. Unknown keys, including
`operator`, are rejected rather than translated or ignored. The same validation
is performed before MCP dispatch to the service, including when an SDK would
otherwise coerce or discard fields. Valid queries retain their values, source
checksums, contributor provenance and scientific semantics.

Expected deterministic query failures now use `QueryValidationError`, a subclass
of both `QueryError` and `ValueError`. Existing Python callers catching
`ValueError` keep working. The MCP binding exposes these anticipated diagnoses,
including invalid operators, value shapes and aggregate unit/output mismatches.
It does not treat arbitrary unexpected exceptions as query validation failures.
No operation is retried, repaired or replaced by another operation.

Clients which reject arguments against the advertised schema before calling MCP
remain responsible for preserving and displaying that local rejection. Such an
attempt did not execute a Data2Agent operation. A later valid call is a separate
attempt, not evidence that the first one succeeded.

This contract is generic to dataset queries; it contains no benchmark questions,
expected answers or model-specific behavior. Tests cover all three tool schemas,
unmodified arguments, non-dispatch of invalid filters, visible semantic errors,
and preservation of valid results. Core ingestion remains dependency-free.
