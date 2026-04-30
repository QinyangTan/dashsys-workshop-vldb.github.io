from __future__ import annotations

from typing import Any


def synthesize_answer(query: str, tool_results: list[dict[str, Any]]) -> str:
    sql_results = [result for result in tool_results if result.get("type") == "sql"]
    api_results = [result for result in tool_results if result.get("type") == "api"]

    templated = synthesize_typed_answer(query, sql_results, api_results)
    if templated:
        return templated

    sql_answer = summarize_sql(sql_results)
    api_answer = summarize_api(api_results)

    if sql_answer and api_answer:
        if any(result.get("payload", {}).get("dry_run") for result in api_results):
            return f"{sql_answer} API verification was not executed because Adobe credentials are unavailable."
        return f"{sql_answer} API evidence: {api_answer}"
    if sql_answer:
        return sql_answer
    if api_answer:
        return api_answer

    errors = [
        result.get("payload", {}).get("error")
        for result in tool_results
        if result.get("payload", {}).get("error")
    ]
    if errors:
        return f"Not found. The available tool evidence produced errors: {errors[0]}"
    return "Not found in the available SQL/API evidence."


def synthesize_typed_answer(
    query: str,
    sql_results: list[dict[str, Any]],
    api_results: list[dict[str, Any]],
) -> str | None:
    lowered = query.lower()
    rows = first_ok_rows(sql_results)
    api_text = api_evidence_phrase(api_results)

    if asks_count(lowered) and rows:
        first = rows[0]
        count_key = next((key for key in first if "count" in key.lower() or len(first) == 1), None)
        if count_key:
            return f"The database count is {first[count_key]}."

    if ("journey" in lowered or "campaign" in lowered) and ("publish" in lowered or "published" in lowered):
        row = first_named_row(rows)
        if row:
            name = value_for(row, ["campaign_name", "name", "campaignname"]) or quoted_name(query) or "the journey"
            published_time = value_for(row, ["published_time", "lastdeployedtime", "published"])
            if published_time in (None, "", "None", "null"):
                return (
                    f"The journey '{name}' has not been published. "
                    f"The database shows null published_time, and {api_text}."
                )
            return f"The journey '{name}' was published at {published_time}."

    if "failed" in lowered and ("run" in lowered or "dataflow" in lowered) and rows == []:
        return "There are no failed dataflow runs to report based on the available evidence."

    if any(token in lowered for token in ["connected to", "mapped to", "associated with", "related to"]) and rows == []:
        return (
            "Based on the available evidence, no matching relationship was found. "
            f"The SQL query returned zero rows, and {api_text}."
        )

    if ("list" in lowered or "show" in lowered or "export" in lowered) and rows:
        names = extract_names(rows)
        if names:
            prefix = "Based on the database, the matching items are: "
            return prefix + ", ".join(names[:12]) + f". {api_text.capitalize()}."

    return None


def summarize_sql(sql_results: list[dict[str, Any]]) -> str | None:
    for result in sql_results:
        payload = result.get("payload", {})
        if not payload.get("ok"):
            continue
        rows = payload.get("rows") or []
        if not rows:
            return "The database query returned no matching rows."
        first = rows[0]
        if len(first) == 1 and "count" in {key.lower() for key in first}:
            value = next(iter(first.values()))
            return f"The database count is {value}."
        formatted = format_rows(rows)
        row_count = payload.get("row_count", len(rows))
        suffix = " The result may be truncated by the row limit." if payload.get("limited") else ""
        return f"The database returned {row_count} matching row(s): {formatted}.{suffix}"
    return None


def summarize_api(api_results: list[dict[str, Any]]) -> str | None:
    for result in api_results:
        payload = result.get("payload", {})
        if payload.get("dry_run"):
            return "API verification was skipped because credentials are unavailable."
        if not payload.get("ok"):
            error = payload.get("error") or "unknown API error"
            return f"API call failed or returned no usable evidence ({error})."
        preview = payload.get("result_preview")
        if preview in (None, "", [], {}):
            return "API returned an empty response."
        return f"API returned status {payload.get('status_code')} with preview {preview}."
    return None


def format_rows(rows: list[dict[str, Any]], max_rows: int = 5, max_fields: int = 6) -> str:
    formatted_rows = []
    for row in rows[:max_rows]:
        pieces = []
        for key, value in list(row.items())[:max_fields]:
            pieces.append(f"{key}={value}")
        formatted_rows.append("{" + ", ".join(pieces) + "}")
    if len(rows) > max_rows:
        formatted_rows.append(f"... {len(rows) - max_rows} more")
    return "; ".join(formatted_rows)


def first_ok_rows(sql_results: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    for result in sql_results:
        payload = result.get("payload", {})
        if payload.get("ok"):
            return payload.get("rows") or []
    return None


def api_evidence_phrase(api_results: list[dict[str, Any]]) -> str:
    if not api_results:
        return "API evidence was not requested"
    if any(result.get("payload", {}).get("dry_run") for result in api_results):
        return "API verification was not executed because credentials are unavailable"
    for result in api_results:
        payload = result.get("payload", {})
        if payload.get("ok") and payload.get("result_preview") not in (None, "", [], {}):
            return "the API returned usable evidence"
        if payload.get("ok"):
            return "the API returned no matching results"
    return "API evidence did not provide usable data"


def first_named_row(rows: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    if not rows:
        return None
    return rows[0]


def value_for(row: dict[str, Any], names: list[str]) -> Any:
    normalized = {key.lower().replace("_", ""): value for key, value in row.items()}
    for name in names:
        key = name.lower().replace("_", "")
        if key in normalized:
            return normalized[key]
    return None


def quoted_name(query: str) -> str | None:
    import re

    match = re.search(r"'([^']+)'|\"([^\"]+)\"", query)
    if not match:
        return None
    return (match.group(1) or match.group(2)).strip()


def asks_count(lowered_query: str) -> bool:
    return any(token in lowered_query for token in ["how many", "count", "number of", "total"])


def extract_names(rows: list[dict[str, Any]]) -> list[str]:
    names = []
    for row in rows:
        value = value_for(
            row,
            [
                "name",
                "campaign_name",
                "campaignname",
                "segment_name",
                "collection_name",
                "target_name",
                "dataflow_name",
                "property_name",
            ],
        )
        if value is not None:
            names.append(str(value))
    return list(dict.fromkeys(names))
