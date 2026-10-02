#!/usr/bin/env python3
"""Convert v1.5 extract/clean outputs into benchmark prediction JSON files.

The converter never reads ground truth, so it cannot leak expected values into
the baseline. It only normalizes the old system's own output contract.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


TYPE_MAP = {
    "invoice": "invoice",
    "deliverynote": "delivery_note",
    "taxinvoice": "tax_invoice",
    "unknown": "unknown",
}

MONTHS = {
    "january": 1, "januari": 1, "february": 2, "februari": 2,
    "march": 3, "maret": 3, "april": 4, "may": 5, "mei": 5,
    "june": 6, "juni": 6, "july": 7, "juli": 7,
    "august": 8, "agustus": 8, "september": 9, "october": 10,
    "oktober": 10, "november": 11, "december": 12, "desember": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "oct": 10, "okt": 10, "nov": 11, "dec": 12,
    "des": 12,
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def normalize_type(value: Any) -> str:
    key = re.sub(r"[^a-z]", "", str(value or "").lower())
    return TYPE_MAP.get(key, "unknown")


def document_id_from_name(path: Path) -> str:
    stem = re.sub(r"-(extract|clean)$", "", path.stem)
    match = re.fullmatch(r"(delivery-note|tax-invoice|invoice)-?(\d+)", stem)
    if not match:
        raise ValueError(f"Unsupported old-system filename: {path.name}")
    return f"{match.group(1)}-{int(match.group(2)):02d}"


def target_type(document_id: str) -> str:
    if document_id.startswith("delivery-note"):
        return "delivery_note"
    if document_id.startswith("tax-invoice"):
        return "tax_invoice"
    return "invoice"


def parse_number(value: Any) -> int | float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    text = re.sub(r"[^0-9,().+-]", "", str(value)).strip()
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    if "." in text and "," in text:
        decimal_separator = "." if text.rfind(".") > text.rfind(",") else ","
        thousands_separator = "," if decimal_separator == "." else "."
        text = text.replace(thousands_separator, "").replace(decimal_separator, ".")
    elif "," in text or "." in text:
        separator = "," if "," in text else "."
        pieces = text.split(separator)
        if len(pieces) > 2 or (len(pieces) == 2 and len(pieces[-1]) == 3):
            text = "".join(pieces)
        else:
            text = ".".join(pieces)
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    if negative:
        number = -number
    return int(number) if number == number.to_integral_value() else float(number)


def parse_date(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip().strip(",")
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            pass
    match = re.search(r"(\d{1,2})[\s/.-]+([A-Za-z]+)[\s,./-]+(\d{2,4})", text)
    if not match:
        return text or None
    day, month_name, year = match.groups()
    month = MONTHS.get(month_name.lower())
    if month is None:
        return text
    year_value = int(year)
    if year_value < 100:
        year_value += 2000
    return f"{year_value:04d}-{month:02d}-{int(day):02d}"


def normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "part_number": item.get("part_number", item.get("partNumber")),
        "part_name": item.get("part_name", item.get("partName")),
        "quantity": parse_number(item.get("quantity")),
        "unit": item.get("unit"),
        "price": parse_number(item.get("price")),
        "amount": parse_number(item.get("amount")),
    }


def normalize_extraction(data: dict[str, Any] | None, doc_type: str) -> dict[str, Any]:
    if not data:
        return {}
    header = dict(data.get("headerFields") or {})
    extraction: dict[str, Any] = {"supplier_name": header.get("supplier_name")}
    date_fields = {"invoice_date", "delivery_note_date", "tax_invoice_date"}
    numeric_fields = {
        "sub_total_amount", "taxable_base", "tax_amount", "total_amount",
        "discount", "down_payment", "luxury_goods_sales_tax",
    }
    for field, value in header.items():
        if field == "supplier_name":
            continue
        if field in date_fields:
            extraction[field] = parse_date(value)
        elif field in numeric_fields:
            extraction[field] = parse_number(value)
        else:
            extraction[field] = value
    extraction["items"] = [normalize_item(item) for item in data.get("lineItems") or []]
    if doc_type == "tax_invoice":
        full_number = re.sub(r"\D", "", str(extraction.get("tax_invoice_number") or ""))
        extraction["tax_invoice_full_number"] = full_number or None
        extraction["trans_type"] = full_number[:2] if len(full_number) >= 2 else None
        extraction["tax_replc"] = full_number[2:3] if len(full_number) >= 3 else None
        extraction["tax_invoice_number"] = full_number[3:] if len(full_number) > 3 else None
    return extraction


def page_predictions(extract: dict[str, Any], document_id: str, doc_type: str) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    previous_type: str | None = None
    group_index = 0
    target_group_assigned = False
    for page in sorted(extract.get("pages", []), key=lambda item: item.get("pageNumber", 0)):
        page_type = normalize_type(page.get("documentType"))
        if page_type != previous_type or page_type == "unknown":
            group_index += 1
        if page_type == doc_type and not target_group_assigned:
            logical_id = document_id
            target_group_assigned = True
        elif page_type == previous_type and pages:
            logical_id = pages[-1]["logicalDocumentId"]
        else:
            logical_id = f"{document_id}-predicted-group-{group_index}"
        pages.append({
            "pageNumber": page.get("pageNumber"),
            "pageType": page_type,
            "logicalDocumentId": logical_id,
            "classificationConfidence": page.get("classificationConfidence"),
        })
        previous_type = page_type
    return pages


def select_cleaned_page(clean: dict[str, Any], doc_type: str) -> dict[str, Any] | None:
    for page in sorted(clean.get("pages", []), key=lambda item: item.get("pageNumber", 0)):
        if normalize_type(page.get("documentType")) == doc_type and page.get("status") == "cleaned" and page.get("data"):
            return page
    return None


def convert_pair(extract_path: Path, clean_path: Path) -> dict[str, Any]:
    document_id = document_id_from_name(extract_path)
    doc_type = target_type(document_id)
    extract, clean = load_json(extract_path), load_json(clean_path)
    cleaned_page = select_cleaned_page(clean, doc_type)
    raw_text = "\n\n".join(
        str(page.get("rawText") or "") for page in extract.get("pages", [])
    )
    return {
        "documentId": document_id,
        "pages": page_predictions(extract, document_id, doc_type),
        "ocrText": raw_text,
        "extraction": normalize_extraction(cleaned_page.get("data") if cleaned_page else None, doc_type),
        "decision": {
            "status": "needs_review",
            "reason": "baseline_v1_5_has_no_hes_matching_output",
        },
        "runtime": {},
        "baselineMetadata": {
            "sourceExtract": extract_path.name,
            "sourceClean": clean_path.name,
            "cleanStatus": cleaned_page.get("status") if cleaned_page else "missing_or_failed",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-system", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    extract_dir = args.old_system / "extract"
    clean_dir = args.old_system / "clean"
    args.output.mkdir(parents=True, exist_ok=True)
    count = 0
    for extract_path in sorted(extract_dir.glob("*-extract.json")):
        clean_name = extract_path.name.replace("-extract.json", "-clean.json")
        clean_path = clean_dir / clean_name
        if not clean_path.is_file():
            raise FileNotFoundError(f"Missing clean output for {extract_path.name}: {clean_path}")
        prediction = convert_pair(extract_path, clean_path)
        destination = args.output / f"{prediction['documentId']}.json"
        destination.write_text(json.dumps(prediction, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        count += 1
    if count == 0:
        raise FileNotFoundError(f"No *-extract.json files found in {extract_dir}")
    print(f"Created {count} baseline predictions in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
