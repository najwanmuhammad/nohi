#!/usr/bin/env python3
"""Offline PDF OCR runner using the PaddleOCR 3.x general OCR pipeline."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        return value.tolist()
    return list(value)


def result_payload(result: Any) -> dict[str, Any]:
    value = result.json
    if callable(value):
        value = value()
    if not isinstance(value, dict):
        raise TypeError(f"Unexpected PaddleOCR result type: {type(value)!r}")
    payload = value.get("res", value)
    if not isinstance(payload, dict):
        raise TypeError("PaddleOCR result has no object payload")
    return payload


def polygon_top_left(polygon: list[list[float]]) -> tuple[float, float]:
    if not polygon:
        return (0.0, 0.0)
    return (min(point[1] for point in polygon), min(point[0] for point in polygon))


def normalize_page(result: Any, fallback_page_index: int) -> dict[str, Any]:
    payload = result_payload(result)
    texts = as_list(payload.get("rec_texts"))
    scores = as_list(payload.get("rec_scores"))
    polygons = as_list(payload.get("rec_polys"))
    boxes = as_list(payload.get("rec_boxes"))
    lines = []
    for index, text in enumerate(texts):
        polygon = as_list(polygons[index]) if index < len(polygons) else []
        lines.append({
            "text": str(text),
            "confidence": float(scores[index]) if index < len(scores) else None,
            "polygon": polygon,
            "box": as_list(boxes[index]) if index < len(boxes) else None,
        })
    lines.sort(key=lambda line: polygon_top_left(line["polygon"]))
    valid_scores = [line["confidence"] for line in lines if line["confidence"] is not None]
    page_index = payload.get("page_index")
    return {
        "pageNumber": int(page_index) + 1 if page_index is not None else fallback_page_index,
        "rawText": "\n".join(line["text"] for line in lines if line["text"]),
        "meanConfidence": statistics.fmean(valid_scores) if valid_scores else None,
        "minimumConfidence": min(valid_scores) if valid_scores else None,
        "lines": lines,
        "preprocessing": {
            "documentAngle": (payload.get("doc_preprocessor_res") or {}).get("angle"),
            "modelSettings": payload.get("model_settings"),
        },
    }


def build_pipeline(config: dict[str, Any], device_override: str | None) -> Any:
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise RuntimeError(
            "paddleocr is not installed. Follow ocr_runner/README.md, including the "
            "PaddlePaddle build matching your CUDA or CPU environment."
        ) from exc
    return PaddleOCR(
        lang=config["language"],
        ocr_version=config["ocrVersion"],
        device=device_override or config.get("device"),
        engine=config.get("engine"),
        use_doc_orientation_classify=config["useDocumentOrientation"],
        use_doc_unwarping=config["useDocumentUnwarping"],
        use_textline_orientation=config["useTextlineOrientation"],
        text_det_limit_side_len=config["textDetectionLimitSideLength"],
        text_det_limit_type=config["textDetectionLimitType"],
        text_det_thresh=config["textDetectionThreshold"],
        text_det_box_thresh=config["textDetectionBoxThreshold"],
        text_det_unclip_ratio=config["textDetectionUnclipRatio"],
        text_rec_score_thresh=config["textRecognitionScoreThreshold"],
    )


def process_pdf(pipeline: Any, pdf: Path, config: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    pages = [normalize_page(result, index) for index, result in enumerate(pipeline.predict(str(pdf)), start=1)]
    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "schemaVersion": "1.0.0",
        "documentId": pdf.stem,
        "sourceFile": pdf.name,
        "engine": {
            "name": "PaddleOCR",
            "ocrVersion": config["ocrVersion"],
            "language": config["language"],
            "configVersion": config["configVersion"],
        },
        "pages": pages,
        "ocrText": "\n\n".join(page["rawText"] for page in pages),
        "runtime": {
            "latency_ms": round(elapsed_ms, 3),
            "page_count": len(pages),
            "average_ms_per_page": round(elapsed_ms / len(pages), 3) if pages else None,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--device", help="Override config device, e.g. gpu:0 or cpu")
    parser.add_argument("--document-id", help="Run only one PDF stem")
    parser.add_argument("--manifest", type=Path, help="Dataset manifest used to select a split")
    parser.add_argument("--split", choices=["development", "holdout", "all"], default="all")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    config = load_json(args.config)
    pdfs = sorted(args.documents.glob("*.pdf"))
    if args.split != "all":
        if args.manifest is None:
            parser.error("--manifest is required when --split is development or holdout")
        manifest = load_json(args.manifest)
        allowed_ids = {
            document["documentId"] for document in manifest.get("documents", [])
            if document.get("split") == args.split
        }
        pdfs = [path for path in pdfs if path.stem in allowed_ids]
    if args.document_id:
        pdfs = [path for path in pdfs if path.stem == args.document_id]
    if not pdfs:
        print("No matching PDF files found", file=sys.stderr)
        return 2
    args.output.mkdir(parents=True, exist_ok=True)
    pipeline = build_pipeline(config, args.device)
    completed = failed = 0
    for pdf in pdfs:
        destination = args.output / f"{pdf.stem}.json"
        if destination.exists() and not args.overwrite:
            print(f"SKIP {pdf.name}: output exists")
            continue
        try:
            payload = process_pdf(pipeline, pdf, config)
            destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"OK   {pdf.name}: {len(payload['pages'])} page(s), {payload['runtime']['latency_ms']} ms")
            completed += 1
        except Exception as exc:  # Keep batch processing and record actionable failure.
            failed += 1
            error_path = args.output / f"{pdf.stem}.error.json"
            error_path.write_text(json.dumps({"documentId": pdf.stem, "error": str(exc)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"FAIL {pdf.name}: {exc}", file=sys.stderr)
    print(f"Completed: {completed}; failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
