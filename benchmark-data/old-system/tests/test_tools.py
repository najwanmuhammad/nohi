import tempfile
import unittest
from pathlib import Path

from tools.export_baseline_predictions import (
    document_id_from_name,
    normalize_type,
    parse_date,
    parse_number,
)
from ocr_runner.run_ocr import normalize_page


class FakeResult:
    json = {
        "res": {
            "page_index": 0,
            "rec_texts": ["B", "A"],
            "rec_scores": [0.8, 0.9],
            "rec_polys": [
                [[0, 20], [10, 20], [10, 30], [0, 30]],
                [[0, 0], [10, 0], [10, 10], [0, 10]],
            ],
            "rec_boxes": [[0, 20, 10, 30], [0, 0, 10, 10]],
            "model_settings": {},
            "doc_preprocessor_res": {"angle": 0},
        }
    }


class BaselineAdapterTests(unittest.TestCase):
    def test_document_id(self):
        self.assertEqual(document_id_from_name(Path("tax-invoice5-extract.json")), "tax-invoice-05")

    def test_type_normalization(self):
        self.assertEqual(normalize_type("deliveryNote"), "delivery_note")
        self.assertEqual(normalize_type("taxInvoice"), "tax_invoice")

    def test_number_formats(self):
        self.assertEqual(parse_number("Rp 641.667,00"), 641667)
        self.assertEqual(parse_number("641,666.67"), 641666.67)
        self.assertEqual(parse_number("7,000.00"), 7000)

    def test_indonesian_and_english_dates(self):
        self.assertEqual(parse_date("21 Juli 2026"), "2026-07-21")
        self.assertEqual(parse_date("21 July 2026"), "2026-07-21")
        self.assertEqual(parse_date("07/Aug/26"), "2026-08-07")

    def test_ocr_lines_are_sorted_in_reading_order(self):
        page = normalize_page(FakeResult(), 1)
        self.assertEqual(page["rawText"], "A\nB")
        self.assertAlmostEqual(page["meanConfidence"], 0.85)


if __name__ == "__main__":
    unittest.main()
