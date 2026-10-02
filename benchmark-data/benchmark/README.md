# Benchmark runner

Runner ini hanya memakai Python standard library dan dapat dijalankan offline.

## 1. Validasi dataset

```bash
python benchmark/benchmark.py validate --dataset-root .
```

Jika PDF sumber disimpan terpisah:

```bash
python benchmark/benchmark.py validate --dataset-root . --source-root /secure/path/to/pdfs
```

## 2. Format prediksi

Prediksi boleh berupa satu JSON berisi array `documents`, satu object dokumen, atau satu file JSON per dokumen dalam sebuah folder.

```json
{
  "documentId": "invoice-02",
  "pages": [
    {"pageNumber": 1, "pageType": "invoice", "logicalDocumentId": "invoice-02"}
  ],
  "ocrText": "optional raw OCR truth-aligned text",
  "extraction": {
    "supplier_name": "PT. RUKUN SEJAHTERA TEKNIK",
    "invoice_number": "IN00260705553",
    "items": []
  },
  "decision": {"status": "mismatch"},
  "runtime": {"latency_ms": 1234.5, "peak_memory_mb": 2048.0}
}
```

Nama dan struktur field di dalam `extraction` harus sama dengan `expectedExtraction` pada ground truth.

## 3. Jalankan benchmark

```bash
python benchmark/benchmark.py evaluate \
  --dataset-root . \
  --predictions /secure/path/to/predictions \
  --split development \
  --model-version ocr-v2.0.0 \
  --config-version config-v1.0.0 \
  --output benchmark-results/development
```

Untuk evaluasi final, ganti split menjadi `holdout`. Jangan melihat hasil holdout untuk menyetel model, prompt, rule, atau threshold.

Output yang dibuat:

- `results.json`: hasil terstruktur per versi/config;
- `document-results.csv`: metrik per dokumen;
- `field-errors.csv`: daftar field yang salah;
- `report.md`: ringkasan yang mudah dibaca.

CER/WER hanya dihitung bila `ocrText` tersedia pada ground truth dan prediksi. Dataset awal ini berfokus pada structured ground truth, sehingga CER/WER akan tampil `N/A` sampai transkripsi OCR manusia ditambahkan. Nilai angka dibandingkan tepat setelah parsing desimal, tanpa toleransi. Identifier dibandingkan exact, tanpa fuzzy matching.

Perintah mengembalikan exit code `3` bila salah satu regression threshold pada `manifest.json` tidak tercapai, sehingga dapat langsung dipakai sebagai quality gate di CI.
