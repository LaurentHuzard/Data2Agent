"""Published nested filters and anticipated errors use the same query contract."""

import copy
import json

import pytest

pytest.importorskip("mcp")
from jsonschema import Draft202012Validator  # noqa: E402

from data2agent.errors import QueryValidationError  # noqa: E402
from data2agent.mcp import DatasetService  # noqa: E402
from data2agent.mcp.server import build_server  # noqa: E402
from data2agent.query.operations import FILTER_OPERATORS, _validate_filters  # noqa: E402


def schema_of(tool):
    value = tool.model_dump(by_alias=True)
    return value.get("inputSchema") or value["input_schema"]


async def error_text(server, name, arguments):
    try:
        result = await server.call_tool(name, arguments)
    except Exception as error:
        return str(error)
    content = getattr(result, "content", None)
    return content[0].text if content is not None else result[0][0].text


@pytest.mark.anyio
async def test_all_filter_tools_publish_closed_typed_predicates(ingested):
    server = build_server(DatasetService(ingested.output_dir))
    tools = {t.name: t for t in await server.list_tools()}
    for name in ("filter_rows", "aggregate", "aggregate_join"):
        schema = schema_of(tools[name])
        filters = schema["properties"]["filters"]
        array = next((v for v in filters.get("anyOf", []) if v.get("type") == "array"), filters)
        item = array["items"]
        assert item["additionalProperties"] is False
        assert set(item["properties"]["op"]["enum"]) == FILTER_OPERATORS
        check = Draft202012Validator(item)
        assert check.is_valid({"column": "group", "op": "eq", "value": "A"})
        assert check.is_valid({"column": "value", "op": "is_missing"})
        for bad in (
            {"column": "group", "operator": "==", "value": "A"},
            {"column": "group", "op": "equals", "value": "A"},
            {"column": "group", "op": "eq", "value": "A", "extra": True},
            {"column": 3, "op": "eq", "value": "A"},
            {"column": "group", "op": "eq"},
            {"column": "group", "op": "in", "value": "A"},
        ):
            assert not check.is_valid(bad)


@pytest.mark.anyio
async def test_bad_filter_is_visible_unchanged_and_never_reaches_service(ingested, monkeypatch):
    service = DatasetService(ingested.output_dir)
    server = build_server(service)
    calls = []
    monkeypatch.setattr(service, "filter_rows", lambda *a, **kw: calls.append(kw))
    arguments = {
        "path": "animals.csv",
        "filters": [{"column": "genotype", "operator": "==", "value": "KO"}],
    }
    original = copy.deepcopy(arguments)
    message = await error_text(server, "filter_rows", arguments)
    assert "unknown keys" in message and "operator" in message and "op" in message
    assert arguments == original and not calls


@pytest.mark.anyio
async def test_value_and_aggregate_validation_details_reach_the_caller(ingested):
    server = build_server(DatasetService(ingested.output_dir))
    message = await error_text(
        server,
        "filter_rows",
        {"path": "animals.csv", "filters": [{"column": "genotype", "op": "in", "value": "KO"}]},
    )
    assert "requires a list value" in message
    message = await error_text(
        server,
        "aggregate",
        {
            "path": "animals.csv",
            "metrics": [{"op": "mean", "column": "weight_g"}],
            "unit": ["genotype"],
        },
    )
    assert "requires a known column" in message


@pytest.mark.anyio
async def test_valid_filter_still_preserves_results_and_predicates(ingested):
    server = build_server(DatasetService(ingested.output_dir))
    args = {"path": "animals.csv", "filters": [{"column": "genotype", "op": "eq", "value": "KO"}]}
    original = copy.deepcopy(args)
    result = await server.call_tool("filter_rows", args)
    content = getattr(result, "content", None)
    body = json.loads(content[0].text if content is not None else result[0][0].text)
    assert body["matches_in_scanned_rows"] == 24
    assert args == original


def test_core_contract_rejects_bad_shapes_and_remains_value_error_compatible():
    for value in (None, [None], [{"column": "x", "op": []}], [{"column": "x", "op": "eq"}]):
        with pytest.raises(QueryValidationError) as error:
            _validate_filters(value)
        assert isinstance(error.value, ValueError)
