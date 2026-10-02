#!/usr/bin/env python3
"""Validate the dataset and benchmark prediction JSON files without external packages."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

ALLOWED_TYPES = {"invoice", "delivery_note", "tax_invoice"}
ALLOWED_STATUSES = {"matched_high_confidence", "mismatch", "needs_review"}
IDENTIFIER_NAMES = {
    "part_number", "supplier_part_number", "model_number", "invoice_number",
    "delivery_note_number", "tax_invoice_number", "tax_invoice_full_number",
    "trans_type", "tax_replc"
}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def decimal_equal(left: Any, right: Any) -> bool:
    """Exact numeric equality after decimal parsing; no tolerance."""
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except (InvalidOperation, ValueError):
        return False


def scalar_equal(expected: Any, actual: Any) -> bool:
    if expected is None or actual is None:
        return expected is actual
    if isinstance(expected, bool) or isinstance(actual, bool):
        return expected == actual
    if isinstance(expected, (int, float, Decimal)):
        return decimal_equal(expected, actual)
    return str(expected) == str(actual)


def levenshtein(left: list[str] | str, right: list[str] | str) -> int:
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for index, left_value in enumerate(left, start=1):
        current = [index]
        for other_index, right_value in enumerate(right, start=1):
            current.append(min(
                current[-1] + 1,
                previous[other_index] + 1,
                previous[other_index - 1] + (left_value != right_value),
            ))
        previous = current
    return previous[-1]


def rate(expected: str, actual: str, words: bool = False) -> float:
    left: list[str] | str = expected.split() if words else expected
    right: list[str] | str = actual.split() if words else actual
    return levenshtein(left, right) / max(1, len(left))


def percentile(values: list[float], percentile_value: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile_value
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def flatten(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "items":
                continue
            path = f"{prefix}.{key}" if prefix else key
            yield from flatten(child, path)
    elif not isinstance(value, list):
        yield prefix, value


def read_dataset(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = load_json(root / "manifest.json")
    truths = {
        entry["documentId"]: load_json(root / entry["groundTruth"])
        for entry in manifest["documents"]
    }
    return manifest, truths


def checksum_errors(root: Path) -> list[str]:
    checksum_file = root / "checksums.sha256"
    if not checksum_file.exists():
        return ["checksums.sha256 is missing"]
    errors: list[str] = []
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected_hash, relative = line.split(maxsplit=1)
        relative = relative.lstrip("* ")
        path = root / relative
        if not path.is_file():
            errors.append(f"checksum target missing: {relative}")
            continue
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            errors.append(f"checksum mismatch: {relative}")
    return errors


def validate_dataset(root: Path, source_root: Path | None = None, check_hashes: bool = True) -> list[str]:
    errors: list[str] = []
    try:
        manifest, truths = read_dataset(root)
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        return [f"cannot load dataset: {exc}"]

    entries = manifest.get("documents", [])
    ids = [entry.get("documentId") for entry in entries]
    if len(ids) != len(set(ids)):
        errors.append("manifest contains duplicate documentId")

    split_ids: dict[str, set[str]] = {}
    split_suppliers: dict[str, set[str]] = {}
    for split_name in ("development", "holdout"):
        try:
            split = load_json(root / "splits" / f"{split_name}.json")
            split_ids[split_name] = set(split["documentIds"])
            split_suppliers[split_name] = set(split["supplierGroups"])
        except (OSError, KeyError, json.JSONDecodeError) as exc:
            errors.append(f"invalid {split_name} split: {exc}")
            split_ids[split_name], split_suppliers[split_name] = set(), set()
    if split_ids["development"] & split_ids["holdout"]:
        errors.append("development and holdout document IDs overlap")
    if (split_ids["development"] | split_ids["holdout"]) != set(ids):
        errors.append("splits must cover every manifest document exactly once")
    if split_suppliers["development"] & split_suppliers["holdout"]:
        errors.append("supplier leakage detected between development and holdout")

    required = manifest.get("requiredFields", {})
    for entry in entries:
        document_id = entry["documentId"]
        truth = truths.get(document_id)
        if truth is None:
            errors.append(f"{document_id}: ground truth missing")
            continue
        doc_type = entry.get("type")
        if doc_type not in ALLOWED_TYPES:
            errors.append(f"{document_id}: invalid document type {doc_type!r}")
        if truth.get("documentId") != document_id:
            errors.append(f"{document_id}: documentId differs in ground truth")
        if truth.get("requestedDocumentType") != doc_type:
            errors.append(f"{document_id}: requestedDocumentType differs from manifest")
        if entry.get("split") not in split_ids or document_id not in split_ids.get(entry.get("split"), set()):
            errors.append(f"{document_id}: manifest split and split file disagree")
        extraction = truth.get("expectedExtraction", {})
        status = truth.get("expectedDecision", {}).get("status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"{document_id}: invalid expected decision {status!r}")
        contract = required.get(doc_type, {})
        for field in contract.get("header", []) + contract.get("hesDerivedIdentifierFields", []):
            if field not in extraction:
                errors.append(f"{document_id}: required field key missing: {field}")
            elif extraction[field] is None and status == "matched_high_confidence":
                errors.append(f"{document_id}: matched document has null required field: {field}")
        item_required = contract.get("item", [])
        for item_index, item in enumerate(extraction.get("items", [])):
            for field in item_required:
                if field not in item:
                    errors.append(f"{document_id}: item {item_index} missing required key: {field}")
                elif item[field] is None and status == "matched_high_confidence":
                    errors.append(f"{document_id}: matched item {item_index} has null required field: {field}")
        pages = truth.get("pages", [])
        if not pages:
            errors.append(f"{document_id}: pages cannot be empty")
        for page in pages:
            if "logicalDocumentId" not in page:
                errors.append(f"{document_id}: page {page.get('pageNumber')} lacks logicalDocumentId")
        if doc_type == "tax_invoice":
            full = extraction.get("tax_invoice_full_number", "")
            parts = extraction.get("trans_type", "") + extraction.get("tax_replc", "") + extraction.get("tax_invoice_number", "")
            if not full.isdigit() or full != parts:
                errors.append(f"{document_id}: invalid tax invoice number decomposition")
            if len(extraction.get("trans_type", "")) != 2 or len(extraction.get("tax_replc", "")) != 1:
                errors.append(f"{document_id}: invalid trans_type/tax_replc length")
        if source_root is not None and not (source_root / entry["sourceFile"]).is_file():
            errors.append(f"{document_id}: source PDF missing: {entry['sourceFile']}")

    if check_hashes:
        errors.extend(checksum_errors(root))
    return errors


def load_predictions(path: Path) -> dict[str, dict[str, Any]]:
    if path.is_file():
        value = load_json(path)
        records = value if isinstance(value, list) else value.get("documents", [value])
    else:
        records = [load_json(item) for item in sorted(path.glob("*.json"))]
    return {record["documentId"]: record for record in records}


def required_paths(manifest: dict[str, Any], doc_type: str, extraction: dict[str, Any]) -> list[str]:
    contract = manifest["requiredFields"][doc_type]
    result = list(contract.get("header", [])) + list(contract.get("hesDerivedIdentifierFields", []))
    for index, _ in enumerate(extraction.get("items", [])):
        result.extend(f"items[{index}].{field}" for field in contract.get("item", []))
    return result


def get_path(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.replace("]", "").replace("[", ".").split("."):
        if isinstance(current, list):
            current = current[int(part)] if int(part) < len(current) else None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def accuracy(correct: int, total: int) -> float | None:
    return correct / total if total else None


def evaluate(
    root: Path, prediction_path: Path, output: Path, split: str, allow_missing: bool,
    model_version: str, config_version: str,
) -> int:
    errors = validate_dataset(root)
    if errors:
        print("Dataset validation failed:\n- " + "\n- ".join(errors), file=sys.stderr)
        return 2
    manifest, truths = read_dataset(root)
    predictions = load_predictions(prediction_path)
    selected = [entry for entry in manifest["documents"] if split == "all" or entry["split"] == split]
    missing = [entry["documentId"] for entry in selected if entry["documentId"] not in predictions]
    if missing and not allow_missing:
        print("Missing predictions: " + ", ".join(missing), file=sys.stderr)
        return 2

    output.mkdir(parents=True, exist_ok=True)
    field_errors: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    aggregate: Counter[str] = Counter()
    cer_values: list[float] = []
    wer_values: list[float] = []
    latencies: list[float] = []
    memories: list[float] = []

    for entry in selected:
        document_id = entry["documentId"]
        if document_id not in predictions:
            continue
        truth, prediction = truths[document_id], predictions[document_id]
        expected, actual = truth["expectedExtraction"], prediction.get("extraction", {})
        required = set(required_paths(manifest, entry["type"], expected))
        comparisons: list[tuple[str, Any, Any]] = []
        comparisons.extend((path, value, get_path(actual, path)) for path, value in flatten(expected))
        for index, item in enumerate(expected.get("items", [])):
            comparisons.extend((f"items[{index}].{path}", value, get_path(actual, f"items[{index}].{path}")) for path, value in flatten(item))

        field_correct = required_correct = identifier_correct = 0
        identifier_total = 0
        for path, expected_value, actual_value in comparisons:
            is_correct = scalar_equal(expected_value, actual_value)
            field_correct += int(is_correct)
            if path in required:
                required_correct += int(is_correct)
            if path.split(".")[-1] in IDENTIFIER_NAMES:
                identifier_total += 1
                identifier_correct += int(is_correct)
            if not is_correct:
                field_errors.append({
                    "documentId": document_id, "field": path,
                    "expected": json.dumps(expected_value, ensure_ascii=False),
                    "actual": json.dumps(actual_value, ensure_ascii=False),
                    "required": path in required,
                })

        expected_items, actual_items = expected.get("items", []), actual.get("items", [])
        row_total = max(len(expected_items), len(actual_items))
        row_correct = sum(
            index < len(actual_items) and all(
                scalar_equal(value, actual_items[index].get(field))
                for field, value in expected_items[index].items()
            ) for index in range(len(expected_items))
        ) if row_total else 0

        expected_pages = {page["pageNumber"]: page for page in truth.get("pages", [])}
        actual_pages = {page["pageNumber"]: page for page in prediction.get("pages", [])}
        classification_total = len(expected_pages)
        classification_correct = sum(
            actual_pages.get(number, {}).get("pageType") == page.get("pageType")
            for number, page in expected_pages.items()
        )
        grouping_correct = sum(
            actual_pages.get(number, {}).get("logicalDocumentId") == page.get("logicalDocumentId")
            for number, page in expected_pages.items()
        )
        expected_status = truth["expectedDecision"]["status"]
        actual_status = prediction.get("decision", {}).get("status")
        decision_correct = expected_status == actual_status

        document_cer = document_wer = None
        if isinstance(truth.get("ocrText"), str) and isinstance(prediction.get("ocrText"), str):
            document_cer = rate(truth["ocrText"], prediction["ocrText"])
            document_wer = rate(truth["ocrText"], prediction["ocrText"], words=True)
            cer_values.append(document_cer)
            wer_values.append(document_wer)
        runtime = prediction.get("runtime", {})
        if isinstance(runtime.get("latency_ms"), (int, float)):
            latencies.append(float(runtime["latency_ms"]))
        if isinstance(runtime.get("peak_memory_mb"), (int, float)):
            memories.append(float(runtime["peak_memory_mb"]))

        aggregate.update({
            "field_total": len(comparisons), "field_correct": field_correct,
            "required_total": len(required), "required_correct": required_correct,
            "identifier_total": identifier_total, "identifier_correct": identifier_correct,
            "row_total": row_total, "row_correct": row_correct,
            "classification_total": classification_total, "classification_correct": classification_correct,
            "grouping_total": classification_total, "grouping_correct": grouping_correct,
            "decision_total": 1, "decision_correct": int(decision_correct),
        })
        documents.append({
            "documentId": document_id,
            "field_accuracy": accuracy(field_correct, len(comparisons)),
            "required_field_accuracy": accuracy(required_correct, len(required)),
            "identifier_accuracy": accuracy(identifier_correct, identifier_total),
            "row_accuracy": accuracy(row_correct, row_total),
            "classification_accuracy": accuracy(classification_correct, classification_total),
            "grouping_accuracy": accuracy(grouping_correct, classification_total),
            "decision_correct": decision_correct,
            "cer": document_cer, "wer": document_wer,
            "latency_ms": runtime.get("latency_ms"), "peak_memory_mb": runtime.get("peak_memory_mb"),
        })

    metrics = {
        "prediction_coverage": accuracy(len(documents), len(selected)),
        "field_accuracy": accuracy(aggregate["field_correct"], aggregate["field_total"]),
        "required_field_accuracy": accuracy(aggregate["required_correct"], aggregate["required_total"]),
        "identifier_accuracy": accuracy(aggregate["identifier_correct"], aggregate["identifier_total"]),
        "row_accuracy": accuracy(aggregate["row_correct"], aggregate["row_total"]),
        "classification_accuracy": accuracy(aggregate["classification_correct"], aggregate["classification_total"]),
        "grouping_accuracy": accuracy(aggregate["grouping_correct"], aggregate["grouping_total"]),
        "decision_accuracy": accuracy(aggregate["decision_correct"], aggregate["decision_total"]),
        "cer_mean": statistics.fmean(cer_values) if cer_values else None,
        "wer_mean": statistics.fmean(wer_values) if wer_values else None,
        "latency_ms_p50": percentile(latencies, 0.50),
        "latency_ms_p95": percentile(latencies, 0.95),
        "peak_memory_mb_max": max(memories) if memories else None,
    }
    threshold_failures = []
    for name, minimum in manifest.get("regressionThresholds", {}).items():
        value = metrics.get(name)
        if value is None or value < minimum:
            threshold_failures.append({"metric": name, "actual": value, "minimum": minimum})
    result = {
        "datasetVersion": manifest["datasetVersion"], "split": split,
        "modelVersion": model_version, "configVersion": config_version,
        "documentsExpected": len(selected), "documentsEvaluated": len(documents),
        "metrics": metrics, "thresholdFailures": threshold_failures, "documents": documents,
    }
    (output / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (output / "document-results.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(documents[0].keys()) if documents else ["documentId"])
        writer.writeheader(); writer.writerows(documents)
    with (output / "field-errors.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["documentId", "field", "expected", "actual", "required"])
        writer.writeheader(); writer.writerows(field_errors)
    report_lines = [
        f"# Benchmark report — {split}", "", f"Dataset version: `{manifest['datasetVersion']}`", "",
        "| Metric | Result |", "|---|---:|",
    ]
    for name, value in metrics.items():
        display = "N/A" if value is None else f"{value:.6f}"
        report_lines.append(f"| {name} | {display} |")
    report_lines.extend(["", f"Evaluated {len(documents)} of {len(selected)} documents.", ""])
    if threshold_failures:
        report_lines.extend(["## Regression gate: FAILED", ""])
        for failure in threshold_failures:
            report_lines.append(f"- `{failure['metric']}` = {failure['actual']}; minimum = {failure['minimum']}")
    else:
        report_lines.extend(["## Regression gate: PASSED", ""])
    (output / "report.md").write_text("\n".join(report_lines), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 3 if threshold_failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate", help="Validate manifest, ground truth, splits, and checksums")
    validate_parser.add_argument("--dataset-root", type=Path, default=Path("."))
    validate_parser.add_argument("--source-root", type=Path)
    validate_parser.add_argument("--skip-checksums", action="store_true")
    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate prediction JSON")
    evaluate_parser.add_argument("--dataset-root", type=Path, default=Path("."))
    evaluate_parser.add_argument("--predictions", type=Path, required=True)
    evaluate_parser.add_argument("--output", type=Path, required=True)
    evaluate_parser.add_argument("--split", choices=["development", "holdout", "all"], default="development")
    evaluate_parser.add_argument("--allow-missing", action="store_true")
    evaluate_parser.add_argument("--model-version", required=True)
    evaluate_parser.add_argument("--config-version", required=True)
    args = parser.parse_args()
    if args.command == "validate":
        errors = validate_dataset(args.dataset_root, args.source_root, not args.skip_checksums)
        if errors:
            print("FAILED\n- " + "\n- ".join(errors), file=sys.stderr)
            return 1
        print("OK: dataset structure, contracts, splits, and checksums are valid")
        return 0
    return evaluate(
        args.dataset_root, args.predictions, args.output, args.split, args.allow_missing,
        args.model_version, args.config_version,
    )


if __name__ == "__main__":
    raise SystemExit(main())
