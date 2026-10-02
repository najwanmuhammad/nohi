# AI Document Checking — Gold Dataset v1.0

Paket ini menyelesaikan fondasi TSK-003 dan TSK-004 untuk invoice, delivery note, dan faktur pajak.

## Struktur

- `manifest.json`: kontrak dataset, business rule, daftar dokumen, dan kebijakan split;
- `ground-truth/`: 12 anotasi yang telah disiapkan;
- `splits/development.json`: 9 dokumen dari Akebono, Rukun, dan Okaya;
- `splits/holdout.json`: 3 dokumen Interglobal yang tidak boleh dipakai untuk tuning;
- `benchmark/`: validator, evaluator, unit test, dan petunjuk penggunaan;
- `checksums.sha256`: integritas seluruh file penting dalam paket.

## Keputusan penting

1. Split dibuat **supplier-disjoint**, bukan random per dokumen. Ini mencegah model menghafal layout supplier yang sama di development dan holdout.
2. `tax_invoice_full_number` menyimpan hasil OCR lengkap. HES menerima komponen `trans_type` (2 digit awal), `tax_replc` (digit ketiga), dan `tax_invoice_number` (sisa digit).
3. Required field faktur pajak hanya `supplier_name`, `tax_invoice_number`, `tax_invoice_date`, `taxable_base`, dan `tax_amount`. `trans_type` dan `tax_replc` wajib diturunkan untuk kontrak HES. Field lain tetap diekstrak dan dievaluasi bila tersedia, tetapi bersifat optional untuk keputusan.
4. Semua nominal dan identifier kritis dibandingkan exact setelah normalisasi; toleransi angka adalah nol dan fuzzy matching dilarang.
5. Dokumen lain dalam satu PDF tetap diklasifikasikan dan dikelompokkan, tetapi tidak boleh dipakai untuk mengisi required field dokumen target.

## Mulai cepat

```bash
python benchmark/benchmark.py validate --dataset-root .
python -m unittest benchmark/test_benchmark.py
```

Lihat `benchmark/README.md` untuk format prediksi dan perintah evaluasi. PDF asli sengaja tidak berada di paket agar data sensitif tidak tersebar. Simpan PDF di lokasi privat dan gunakan opsi `--source-root` saat ingin memvalidasi keberadaannya.

TSK-005 (baseline v1.5) sengaja tidak dikerjakan sesuai keputusan project saat ini.
