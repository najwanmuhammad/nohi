# Codex Handoff — AI Document Checking HES

## Prompt untuk Codex

```text
Kamu melanjutkan project AI Document Checking untuk Hino Enterprise System (HES). Baca seluruh file project sebelum mengubah kode. Jangan mengasumsikan business rule yang tidak tertulis dan jangan mengubah ground truth agar hasil model terlihat lebih baik.

TUJUAN SISTEM
Sistem menerima PDF invoice, delivery note, faktur pajak dari supplier. Satu PDF dapat berisi beberapa jenis dokumen. Sistem harus mengklasifikasikan halaman, mengelompokkan logical document, melakukan OCR offline, mengekstrak structured fields dan line items, lalu mencocokkannya dengan data HES.

CONSTRAINT UTAMA
1. Semua pemrosesan dokumen harus lokal/on-premise. OCR cloud dilarang karena keamanan.
2. Jangan menggunakan ground truth sebagai input prediction.
3. Jangan menggunakan halaman supporting document untuk mengisi required field target document.
4. Identifier dan nominal kritis dibandingkan exact setelah normalisasi. Fuzzy matching dilarang.
5. Toleransi seluruh angka adalah nol.
6. Development split boleh digunakan untuk tuning. Holdout dilarang digunakan sampai release candidate dibekukan.
7. Data PDF dan ground truth bersifat sensitif dan tidak boleh masuk public repository.

BUSINESS RULE FINAL
- TB60573N = supplier_part_number Rukun.
- 7000002306 = model_number.
- 10030290 = canonical HES part_number.
- tax_goods_code 000000 diabaikan dan tidak boleh dianggap part_number.
- Invoice yang tidak mencantumkan required canonical HES part_number harus ditolak/mismatch. Jangan mengambil part_number dari PO atau halaman lain di PDF yang sama untuk menutupi kekurangan invoice.
- Setiap upload diperiksa sendiri; tidak ada cross-upload document reference checking.

REQUIRED FIELDS
Invoice header: supplier_name, invoice_number, invoice_date, sub_total_amount, taxable_base, tax_amount, total_amount.
Invoice item: part_number, part_name, quantity, price, amount.

Delivery note header: supplier_name, delivery_note_number, delivery_note_date.
Delivery note item: part_number, part_name, quantity.

Tax invoice required: supplier_name, tax_invoice_number, tax_invoice_date, taxable_base, tax_amount.
Field di invoice, delivery note, dan tax invoice lain tetap diekstrak tetapi optional untuk decision.

TAX INVOICE NUMBER CONTRACT
- tax_invoice_full_number = nomor lengkap hasil OCR/evidence.
- trans_type = 2 digit pertama.
- tax_replc = digit ketiga.
- tax_invoice_number = semua digit setelah digit ketiga.
- full number harus sama dengan concatenation ketiga komponen HES tersebut.

DECISION POLICY
- matched_high_confidence: seluruh required field tersedia, confidence cukup, dan exact match dengan HES.
- mismatch: minimal satu readable required field berbeda dari HES. Known readable mismatch lebih kuat daripada needs_review.
- needs_review: required field kosong/low confidence atau hasil tidak cukup andal untuk menentukan match/mismatch.

STRUKTUR PROJECT YANG DIHARAPKAN PADA TAHAP BENCHMARKING
benchmark-data/
  benchmark/
  documents/
  ground-truth/
  splits/
  old-system/
  manifest.json
  checksums.sha256

STATUS TASK
- TSK-001 sampai TSK-005 selesai.
- Task aktif: TSK-006, menjalankan offline OCR runner baru.
- Jangan mengerjakan TSK-008/009/010 sebelum TSK-006 dan TSK-007 memenuhi acceptance criteria.

DATASET
- Total 12 target documents.
- Development: 9 dokumen dari Akebono, Rukun, dan Okaya.
- Holdout: 3 dokumen dari Interglobal.
- Split supplier-disjoint.
- Invoice 02 Rukun adalah fixture 4 halaman.
- expectedExtraction adalah structured ground truth hasil pembacaan manual.
- Full-page ocrText belum tersedia; CER/WER harus N/A. Jangan menganggap N/A sebagai 0.

BASELINE V1.5 YANG SUDAH DIBEKUKAN
- prediction coverage: 100.00%
- field accuracy: 57.74%
- required-field accuracy: 74.75%
- identifier accuracy: 74.36%
- row accuracy: 0.00%
- page classification: 88.24%
- logical grouping: 58.82%
- decision accuracy: 0.00%
- CER/WER: N/A
- latency/memory: N/A

Decision accuracy baseline 0% karena ZIP lama tidak memiliki output HES matching. Latency/memory tidak direkam oleh sistem lama dan tidak boleh direkayasa.

IMPLEMENTASI OCR BARU YANG SUDAH ADA
- old-system/ocr_runner/run_ocr.py
- old-system/ocr_runner/configs/ppocrv6-quality.json
- old-system/ocr_runner/configs/ppocrv6-balanced.json
- engine awal PP-OCRv6 medium, lang=id, offline.
- output: rawText, line confidence, polygon, bounding box, preprocessing metadata, latency.
- runner mendukung manifest dan split filtering.

aku menggunakan miniconda environment. source ~/miniconda3/bin/activate
conda activate hino.
menggunakan python 3.12, fastapi, .net 8

TUGAS YANG HARUS DIKERJAKAN SEKARANG
1. Inspeksi struktur project dan baca README, manifest, serta task backlog terbaru.
2. Validasi dataset:
   python benchmark/benchmark.py validate --dataset-root . --source-root documents
3. Periksa environment Python, PaddlePaddle, GPU/CUDA, dan dependency tanpa mengubah sistem secara destruktif.
4. Jalankan smoke test hanya pada invoice-02 menggunakan development split dan quality config.
5. Jika GPU gagal, diagnosis penyebabnya; gunakan CPU sebagai control test, bukan sebagai solusi diam-diam. Utamakan gunakan CPU, karena server Hino tidak ada GPU-nya.
6. Verifikasi output mempunyai 4 halaman, text, confidence, polygon/bounding box, dan latency.
7. Jalankan unit test yang tersedia.
8. Laporkan hasil dan failure mode sebelum menjalankan seluruh development corpus.

CONTOH SMOKE TEST
python old-system/ocr_runner/run_ocr.py \
  --documents documents \
  --output old-system/ocr-results/ppocrv6-quality-v1 \
  --config old-system/ocr_runner/configs/ppocrv6-quality.json \
  --manifest manifest.json \
  --split development \
  --document-id invoice-02 \
  --device gpu:0

DEFINITION OF DONE TSK-006
- invoice-02 menghasilkan tepat 4 page OCR results.
- setiap recognized line memiliki text, confidence, polygon/bounding box.
- tidak ada dokumen dikirim ke cloud.
- model/config/runtime tercatat.
- holdout tidak dipakai.

CARA KERJA YANG WAJIB
- Jelaskan temuan berdasarkan file dan output command, bukan tebakan.
- Jangan langsung mengganti arsitektur atau menambahkan LLM.
- Jangan mengubah ground truth, manifest, required field, decision policy, atau split tanpa meminta persetujuan.
- Jangan menandai task DONE sebelum acceptance criteria dan evidence terpenuhi.
- Pertahankan perubahan user yang tidak terkait.
- Setelah perubahan kode, jalankan test yang relevan dan laporkan perintah serta hasilnya.
```

## Catatan penggunaan

1. Letakkan file ini di root project sebagai `CODEX-HANDOFF.md`.
2. Letakkan backlog terbaru sebagai `TASKS.md`.
3. Saat membuka sesi Codex baru, berikan instruksi singkat: `Baca CODEX-HANDOFF.md, TASKS.md, manifest.json, dan README terkait. Lanjutkan task aktif tanpa mengubah keputusan bisnis.`
4. Jangan menempelkan ulang seluruh PRD setiap sesi selama file PRD dan handoff tersedia di repository privat.
