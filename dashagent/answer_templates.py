from __future__ import annotations

import re
from typing import Any


def classify_answer_family(query: str) -> str:
    lowered = query.lower()
    if ("journey" in lowered or "campaign" in lowered) and "publish" in lowered:
        return "journey_published"
    if "inactive" in lowered and ("journey" in lowered or "campaign" in lowered):
        return "inactive_journeys"
    if "list" in lowered and "journey" in lowered:
        return "list_journeys"
    if ("destination" in lowered or "target" in lowered) and any(token in lowered for token in ["export", "list", "recent", "modified"]):
        if "audience" in lowered or "segment" in lowered or "mapped" in lowered:
            return "audit_destination_mapping"
        return "destination_export"
    if ("audience" in lowered or "segment" in lowered) and ("destination" in lowered or "target" in lowered):
        return "segment_destination"
    if "failed" in lowered and ("dataflow" in lowered or "run" in lowered or "file" in lowered):
        return "failed_dataflow_runs"
    if "merge polic" in lowered:
        return "merge_policy"
    if "timeseries." in lowered or "observability" in lowered or "ingestion record" in lowered:
        return "observability_metrics"
    if "batch" in lowered or "batches" in lowered:
        return "batch"
    if "tag" in lowered:
        return "tags"
    if "schema" in lowered or "dataset" in lowered:
        return "schema_dataset"
    if "audit" in lowered or "created by" in lowered:
        return "audit_destination_mapping"
    return "generic"


def render_answer_template(
    query: str,
    sql_results: list[dict[str, Any]],
    api_results: list[dict[str, Any]],
) -> str | None:
    family = classify_answer_family(query)
    rows = first_ok_rows(sql_results)
    api_phrase = api_evidence_phrase(api_results)
    lowered = query.lower()

    if family == "journey_published":
        row = first_row(rows)
        name = row_value(row, ["campaign_name", "campaignname", "name"]) or quoted_text(query) or "the journey"
        published_time = row_value(row, ["published_time", "lastdeployedtime"])
        if row and published_time not in (None, "", "None", "null"):
            return f'The journey "{name}" was published at {published_time}.'
        return (
            f'The journey "{name}" has not been published. '
            f"The database shows a null published_time for this journey, and {api_phrase}."
        )

    if family == "inactive_journeys" and rows is not None:
        if not rows:
            return f"No inactive journeys were found in the database, and {api_phrase}."
        pieces = []
        for row in rows[:6]:
            name = row_value(row, ["campaign_name", "campaignname", "name"]) or "unnamed campaign"
            updated = row_value(row, ["updated_time", "updatedtime"])
            if updated:
                pieces.append(f"{name} (last updated {human_date(updated)})")
            else:
                pieces.append(str(name))
        return f"There are {len(rows)} inactive campaigns: {join_human(pieces)}. {sentence_case(api_phrase)}."

    if family == "list_journeys" and rows is not None:
        names = extract_names(rows, ["campaign_name", "campaignname", "name"])
        if names:
            return f"Based on the available evidence, there are {len(names)} journeys found in the database: {join_human(names)}. {sentence_case(api_phrase)}."
        return f"No journeys were found in the database. {sentence_case(api_phrase)}."

    if family == "destination_export" and rows is not None:
        if not rows:
            return f"No destinations were found in the database. {sentence_case(api_phrase)}."
        row = rows[0]
        dataflow = row_value(row, ["dataflow_name", "dataflowname"]) or "unknown dataflow"
        target = row_value(row, ["target_name", "name"]) or "unknown target"
        modified = row_value(row, ["modified", "updated_time", "updatedtime"])
        suffix = f" with a modification timestamp of {human_datetime(modified)}" if modified else ""
        return f'Based on the evidence provided, {len(rows)} destination(s) were found. The most recent is "{dataflow}" ({target} target){suffix}. {sentence_case(api_phrase)}.'

    if family in {"segment_destination", "audit_destination_mapping"} and rows is not None:
        if not rows:
            return f"Based on the available evidence, no matching audience-destination relationship was found. The SQL query returned zero rows, and {api_phrase}."
        names = extract_names(rows, ["segment_name", "audience_name", "name"])
        target_names = extract_names(rows, ["target_name", "destination_name", "dataflow_name"])
        created = row_value(rows[0], ["created_time", "createdtime"])
        target_phrase = f" mapped to {join_human(target_names)}" if target_names else " mapped to a destination"
        date_phrase = f" on {human_date(created)}" if created else ""
        return f"Based on the evidence, {len(rows)} audience(s) match: {join_human(names) if names else 'unnamed audience'}{target_phrase}{date_phrase}. {sentence_case(api_phrase)}."

    if family == "failed_dataflow_runs":
        if rows == [] or rows is None:
            return "There are no failed dataflow runs to report based on the available evidence."
        ids = extract_names(rows, ["dataflow_id", "run_id", "id"])
        return f"Based on the available evidence, failed dataflow identifiers are: {join_human(ids) if ids else format_rows(rows)}. {sentence_case(api_phrase)}."

    if family == "schema_dataset":
        answer = schema_dataset_answer(query, rows, api_phrase)
        if answer:
            return answer

    if family == "merge_policy":
        if rows:
            names = extract_names(rows, ["name", "policy_name", "merge_policy_name"])
            if names:
                return f"The matching merge policy evidence identifies: {join_human(names)}. {sentence_case(api_phrase)}."
        if "default" in lowered:
            return f"The default merge policy requires live Adobe API evidence. {sentence_case(api_phrase)}."
        return f"Merge policy information requires Adobe API evidence. {sentence_case(api_phrase)}."

    if family == "observability_metrics":
        if api_has_live_payload(api_results):
            return f"Observability metrics were returned by the API. {sentence_case(api_phrase)}."
        return f"Observability metric values require live API evidence. {sentence_case(api_phrase)}."

    if family == "batch":
        if api_has_live_payload(api_results):
            return f"Batch evidence was returned by the API. {sentence_case(api_phrase)}."
        return f"Batch details and files require live API evidence. {sentence_case(api_phrase)}."

    if family == "tags":
        if api_has_live_payload(api_results):
            return f"Tag evidence was returned by the API. {sentence_case(api_phrase)}."
        if "category" in lowered:
            return f"Tag category membership requires live API evidence. {sentence_case(api_phrase)}."
        return f"Tag details require live API evidence. {sentence_case(api_phrase)}."

    return None


def schema_dataset_answer(query: str, rows: list[dict[str, Any]] | None, api_phrase: str) -> str | None:
    lowered = query.lower()
    if rows is None:
        return None
    if not rows:
        name = quoted_text(query)
        if name:
            return f"Based on the evidence provided, no datasets use the schema '{name}'. The SQL query returned zero results, and {api_phrase}."
        return f"The SQL query returned zero matching schema or dataset rows, and {api_phrase}."
    first = rows[0]
    if asks_count(lowered):
        count = first_count_value(first)
        if count is not None:
            if "experience event" in lowered:
                return f"Based on the SQL query result, there are {count} XDM Experience Event schemas enabled for profile in your environment."
            if "schema" in lowered and "dataset" not in lowered:
                return f"You have {count} schemas. {sentence_case(api_phrase)}."
            schema_name = row_value(first, ["blueprint_name", "schema_name", "name"])
            tail = f' These datasets use "{schema_name}".' if schema_name else ""
            return f"Based on the evidence provided, {count} datasets have been ingested using the same schema.{tail} {sentence_case(api_phrase)}."
    if "detail" in lowered or "details" in lowered:
        name = row_value(first, ["name", "blueprint_name"]) or quoted_text(query) or "the schema"
        class_value = row_value(first, ["class"])
        props = row_value(first, ["property_count"])
        collections = row_value(first, ["collection_count"])
        updated = row_value(first, ["updated_time", "updatedtime"])
        bits = []
        if class_value:
            bits.append(f"has class {class_value}")
        if props is not None:
            bits.append(f"has {props} properties")
        if collections is not None:
            bits.append(f"across {collections} collection(s)")
        if updated:
            bits.append(f"and was last updated on {human_date(updated)}")
        details = ", ".join(bits) if bits else "was found"
        return f"The '{name}' schema {details}. {sentence_case(api_phrase)}."
    names = extract_names(rows, ["collection_name", "dataset_name", "name"])
    if names:
        return f"Based on the evidence provided, matching datasets are: {join_human(names[:10])}. {sentence_case(api_phrase)}."
    return None


def first_ok_rows(sql_results: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    for result in sql_results:
        payload = result.get("payload", {})
        if payload.get("ok"):
            return payload.get("rows") or []
    return None


def first_row(rows: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    return rows[0] if rows else None


def api_evidence_phrase(api_results: list[dict[str, Any]]) -> str:
    if not api_results:
        return "API evidence was not requested"
    if any(result.get("payload", {}).get("dry_run") for result in api_results):
        return "live API verification was not executed because Adobe credentials are unavailable"
    live_payloads = [result.get("payload", {}) for result in api_results]
    if any(payload.get("ok") and payload.get("result_preview") not in (None, "", [], {}) for payload in live_payloads):
        return "the API returned usable supporting evidence"
    if any(payload.get("ok") for payload in live_payloads):
        return "the API returned no matching results"
    return "API evidence did not provide usable data"


def api_has_live_payload(api_results: list[dict[str, Any]]) -> bool:
    return any(
        result.get("payload", {}).get("ok") and not result.get("payload", {}).get("dry_run")
        for result in api_results
    )


def row_value(row: dict[str, Any] | None, candidates: list[str]) -> Any:
    if not row:
        return None
    normalized = {normalize_key(key): value for key, value in row.items()}
    for candidate in candidates:
        value = normalized.get(normalize_key(candidate))
        if value is not None:
            return value
    return None


def normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def extract_names(rows: list[dict[str, Any]], candidates: list[str]) -> list[str]:
    names = []
    for row in rows:
        value = row_value(row, candidates)
        if value not in (None, ""):
            names.append(str(value))
    return list(dict.fromkeys(names))


def first_count_value(row: dict[str, Any]) -> Any:
    for key, value in row.items():
        if "count" in key.lower() or normalize_key(key) in {"total", "num"}:
            return value
    if len(row) == 1:
        return next(iter(row.values()))
    return None


def asks_count(lowered_query: str) -> bool:
    return any(token in lowered_query for token in ["how many", "count", "number of", "total"])


def quoted_text(query: str) -> str | None:
    match = re.search(r"'([^']+)'|\"([^\"]+)\"", query)
    return (match.group(1) or match.group(2)).strip() if match else None


def human_date(value: Any) -> str:
    text = str(value)
    if len(text) >= 10 and re.match(r"\d{4}-\d{2}-\d{2}", text):
        return text[:10]
    return text


def human_datetime(value: Any) -> str:
    text = str(value)
    if "T" in text:
        return text.replace("T", " ").replace("+00:00", " UTC").replace("Z", " UTC")
    return text


def sentence_case(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:]


def join_human(items: list[str]) -> str:
    items = [item for item in items if item]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def format_rows(rows: list[dict[str, Any]], limit: int = 5) -> str:
    parts = []
    for row in rows[:limit]:
        parts.append(", ".join(f"{key}={value}" for key, value in list(row.items())[:4]))
    return "; ".join(parts)
