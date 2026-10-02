# Task Pengerjaan — Sistem AI Document Checking HES

Backlog ini mengimplementasikan PRD v1.6 dan telah diperbarui berdasarkan kondisi proyek per 29 September 2026. Urutan task bersifat dependency-driven. Task fase berikutnya tidak dianggap selesai sebelum acceptance criteria fondasinya terpenuhi.

## Konvensi

- Status: `TODO`, `IN PROGRESS`, `BLOCKED`, `REVIEW`, `DONE`.
- Prioritas: `P0` wajib MVP, `P1` penting sesudah fondasi stabil, `P2` enhancement.
- Evidence: commit/PR, automated test, benchmark report, atau sign-off stakeholder.
- Dataset sensitif, PDF asli, ground truth, dan hasil OCR tidak boleh dimasukkan ke public repository.
- Identifier dan nominal kritis dibandingkan secara exact setelah normalisasi. Fuzzy matching dilarang untuk keduanya.

---

## Ringkasan status

| Task    | Status | Keterangan                                                                    |
| ------- | ------ | ----------------------------------------------------------------------------- |
| TSK-001 | DONE   | Semantic identifier dan aturan part number sudah ditetapkan.                  |
| TSK-002 | DONE   | Required fields, zero tolerance, dan status keputusan sudah ditetapkan.       |
| TSK-003 | DONE   | Gold dataset 12 dokumen, manifest, split, dan checksum tersedia.              |
| TSK-004 | DONE   | Benchmark runner, report, dan regression gate tersedia.                       |
| TSK-005 | DONE   | Baseline v1.5 dibekukan dengan keterbatasan telemetry tercatat sebagai `N/A`. |
|         |

---

## Milestone 0 — Business decision dan benchmark foundation

Status milestone: `DONE`.

### TSK-001 — Tetapkan semantic item identifier

- Status: `DONE`
- Prioritas: P0
- Owner: Finance/HES + Developer
- Dependency: -

Keputusan final:

- `TB60573N` adalah part number milik supplier Rukun (`supplier_part_number`), bukan canonical HES part number.
- `7000002306` adalah nomor model barang (`model_number`), bukan canonical HES part number.
- `10030290` adalah kode barang internal Hino dan menjadi canonical `part_number` HES.
- `000000` pada faktur pajak adalah `tax_goods_code` yang tidak bermakna untuk matching dan harus diabaikan.
- `tax_goods_code` tidak boleh otomatis dipromosikan menjadi `part_number`.
- Jika invoice Rukun tidak mencantumkan canonical HES `part_number` yang seharusnya ada, dokumen dinyatakan `Mismatch`/ditolak; sistem tidak boleh mengambil `part_number` dari dokumen lain di PDF yang sama untuk menutup kekurangan invoice.
- Setiap upload diperiksa sebagai satu target document. Halaman invoice, delivery note, faktur pajak, purchase order, atau supporting document lain dalam PDF yang sama tetap harus diklasifikasikan dan dikelompokkan, tetapi tidak boleh saling mengisi required field target.
- Sistem tidak melakukan cross-upload reference checking karena delivery note, invoice, dan faktur pajak diunggah secara terpisah ke HES.

Acceptance criteria:

- [x] Keputusan masuk ke data contract dan regression fixture.
- [x] `tax_goods_code` tidak pernah otomatis dianggap `part_number`.
- [x] Invoice 02 Rukun menjadi test case required `part_number` yang tidak tercetak.

Evidence:

- `manifest.json`
- `ground-truth/invoice-02.json`
- `ground-truth/tax-invoice-*.json`

### TSK-002 — Definisikan critical fields dan decision policy

- Status: `DONE`
- Prioritas: P0
- Owner: Finance/HES + Developer
- Dependency: TSK-001

Required fields:

#### Invoice

Header:

- `supplier_name`
- `invoice_number`
- `invoice_date`
- `sub_total_amount`
- `taxable_base`
- `tax_amount`
- `total_amount`

Setiap line item:

- `part_number`
- `part_name`
- `quantity`
- `price`
- `amount`

Optional fields:

#### Invoice

- `unit`
- `signer_name`
- `signer_position`

Required fields:

#### Delivery note

Header:

- `supplier_name`
- `delivery_note_number`
- `delivery_note_date`

Setiap line item:

- `part_number`
- `part_name`
- `quantity`

#### Faktur pajak

Required business fields:

- `supplier_name`
- `tax_invoice_number`
- `tax_invoice_date`
- `taxable_base`
- `tax_amount`

Field lain, termasuk setiap item, `sub_total_amount`, `discount`, `down payment`, `luxury_goods_sales_tax`, dan `signer_name`, tetap diekstrak jika tersedia tetapi bersifat optional untuk keputusan.

Kontrak nomor faktur pajak:

- `tax_invoice_full_number`: nomor lengkap yang terbaca pada dokumen dan disimpan sebagai evidence OCR.
- `trans_type`: dua digit pertama.
- `tax_replc`: digit ketiga.
- `tax_invoice_number`: seluruh digit setelah digit ketiga.
- Invariant: `tax_invoice_full_number = trans_type + tax_replc + tax_invoice_number`.

Contoh:

```text
tax_invoice_full_number = 04002600381077552
trans_type              = 04
tax_replc               = 0
tax_invoice_number      = 02600381077552
```

Numeric policy:

- Toleransi `quantity`, `price`, `amount`, subtotal, DPP, PPN, dan total adalah nol.
- Nilai dibandingkan exact setelah separator angka dan format mata uang dinormalisasi.
- Identifier dan nominal kritis tidak menggunakan fuzzy matching.

Decision policy:

- `MatchedHighConfidence`: seluruh required field tersedia, confidence memenuhi threshold, dan seluruh required value sama persis dengan HES setelah normalisasi.
- `Mismatch`: minimal satu required field yang dapat dibaca mempunyai nilai berbeda dari HES. Known readable mismatch lebih kuat daripada `NeedsReview`.
- `NeedsReview`: required field kosong, confidence rendah, struktur dokumen tidak dapat dipulihkan dengan andal, atau hasil belum cukup kuat untuk menyatakan match/mismatch.

Acceptance criteria:

- [x] Policy dapat diterjemahkan menjadi automated tests.
- [x] Identifier dan nominal kritis tidak memakai fuzzy matching.
- [x] Required dan optional fields tersedia dalam `manifest.json`.
- [x] Tax invoice number decomposition tersedia dalam fixture dan validator.

### TSK-003 — Bangun gold dataset awal

- Status: `DONE`
- Prioritas: P0
- Owner: Developer + Finance validator
- Dependency: TSK-001, TSK-002

Hasil:

- 12 target documents: invoice, delivery note, dan faktur pajak.
- Empat sample/supplier group: `01`, `02`, `03`, dan `05`.
- Development split: 9 dokumen dari Akebono, Rukun, dan Okaya.
- Holdout split: 3 dokumen dari Interglobal.
- Split bersifat supplier-disjoint untuk mencegah supplier/layout leakage.
- Invoice 02 Rukun menjadi regression fixture empat halaman: invoice, faktur pajak, delivery note, dan purchase order.
- Setiap page memiliki `pageType`, `isTarget`, dan `logicalDocumentId`.
- Ground truth dibuat melalui pembacaan manual manusia dan berisi expected structured fields, line items, serta expected decision.

Catatan terminology:

- `expectedExtraction` adalah structured ground truth hasil pembacaan manual dan sudah cukup untuk field, identifier, row, classification, grouping, dan decision benchmark.
- Full-page `ocrText` transcription bukan blocker MVP. Field ini hanya dibutuhkan jika proyek ingin menghitung CER/WER secara penuh terhadap seluruh teks halaman.
- Selama full-page transcription belum tersedia, CER/WER dilaporkan sebagai `N/A`, bukan sebagai nol.

Acceptance criteria:

- [x] Structured ground truth divalidasi manusia.
- [x] Data sensitif disimpan di area privat dan tidak masuk public repository.
- [x] Fixture memiliki `manifest.json` dan `checksums.sha256`.
- [x] Development dan holdout tidak mempunyai supplier group yang sama.

### TSK-004 — Buat benchmark runner

- Status: `DONE`
- Prioritas: P0
- Owner: Developer
- Dependency: TSK-003

Kapabilitas runner:

- dataset validation;
- prediction coverage;
- field accuracy;
- required-field accuracy;
- identifier accuracy;
- line-item row accuracy;
- page classification accuracy;
- logical grouping accuracy;
- decision accuracy;
- CER/WER jika full-page `ocrText` tersedia;
- latency P50/P95;
- peak memory;
- output JSON, CSV, dan Markdown;
- model/config version tracking;
- regression threshold dan non-zero exit code untuk CI.

Acceptance criteria:

- [x] Satu perintah memvalidasi corpus.
- [x] Satu perintah mengevaluasi semua prediction dalam split tertentu.
- [x] Hasil lama dan baru dapat dibandingkan secara objektif.
- [x] Perfect-prediction self-test menghasilkan 100% untuk seluruh regression gate.

### TSK-005 — Catat dan bekukan baseline v1.5

- Status: `DONE`
- Prioritas: P0
- Owner: Developer
- Dependency: TSK-004

Hasil:

- Output `extract` dan `clean` dari sistem lama telah dikonversi menjadi 12 prediction JSON tanpa membaca ground truth.
- Development baseline telah dievaluasi dan disimpan dalam JSON/CSV/Markdown.
- Baseline dibekukan sebelum evaluasi engine baru.

Baseline development:

| Metrik                       |   Nilai |
| ---------------------------- | ------: |
| Prediction coverage          | 100.00% |
| Field accuracy               |  57.74% |
| Required-field accuracy      |  74.75% |
| Identifier accuracy          |  74.36% |
| Row accuracy                 |   0.00% |
| Page classification accuracy |  88.24% |
| Logical grouping accuracy    |  58.82% |
| Decision accuracy            |   0.00% |
| CER/WER                      |     N/A |
| Latency/memory               |     N/A |

Keterbatasan baseline:

- ZIP sistem lama tidak berisi output tahap HES matching; adapter secara aman menghasilkan `NeedsReview`, sehingga decision accuracy menjadi 0%.
- Output lama tidak merekam latency atau peak memory. Nilainya harus tetap `N/A` dan tidak boleh diperkirakan.
- CER/WER `N/A` karena gold dataset belum menyimpan full-page transcription.
- Keterbatasan tersebut dicatat sebagai bagian dari baseline dan tidak menghalangi perbandingan metrik extraction/classification/grouping.

Acceptance criteria:

- [x] Baseline tersimpan dan tidak diubah setelah evaluasi engine baru dimulai.
- [x] Failure modes tersedia pada `field-errors.csv`.
- [x] Missing telemetry ditulis eksplisit sebagai `N/A`, bukan angka buatan.

---

## Milestone 1 - Local OCR/Layout Engine

### TSK-101 - Buat Python OCR Engine service

- Prioritas: P0
- Dependency: TSK-005

Pekerjaan:

- Buat FastAPI service terpisah dengan locked dependencies.
- Implement `/health`, `/ready`, dan `/model-info`.
- Bind default ke `127.0.0.1`.

Acceptance criteria:

- Service berjalan tanpa internet setelah model/dependency terpasang.
- Tidak memiliki akses ke database HES.

### TSK-102 - Implement document preprocessing

- Prioritas: P0
- Dependency: TSK-101

Pekerjaan:

- Quality assessment, orientation, deskew, unwarping, dan optional enhancement.
- Simpan transform matrix untuk coordinate round-trip.

Acceptance criteria:

- Fitur dapat diaktifkan per config.
- Original image tidak dimodifikasi.
- Test memverifikasi bbox kembali ke koordinat asli.

### TSK-103 - Integrasikan PP-OCRv6

- Prioritas: P0
- Dependency: TSK-102

Pekerjaan:

- Integrasikan model medium dan siapkan small sebagai pembanding.
- Return polygon, text, confidence, dan timings.
- Implement crop-level retry untuk region kritis.

Acceptance criteria:

- Critical text Invoice Rukun terbaca sesuai ground truth.
- Response selalu memuat model/config version.
- Tidak ada automatic second pass seluruh halaman.

### TSK-104 - Integrasikan PP-StructureV3

- Prioritas: P0
- Dependency: TSK-103

Pekerjaan:

- Aktifkan layout, table, dan reading-order output.
- Nonaktifkan formula/chart submodels yang tidak dibutuhkan.
- Return blocks, rows, cells, coordinates, labels, dan confidence.

Acceptance criteria:

- Tabel Invoice Rukun dikenali dengan row/column yang benar.
- Wrapped description terhubung dengan item yang tepat.
- Totals tidak tergabung dengan informasi bank.

### TSK-105 - Definisikan OCR Engine API v1

- Prioritas: P0
- Dependency: TSK-104

Pekerjaan:

- Implement `POST /v1/analyze-page`.
- Versioned JSON schema, request limits, timeout, cancellation, dan error contract.

Acceptance criteria:

- OpenAPI schema dan .NET-to-Python contract test tersedia.
- Error/log tidak membocorkan full document text.

### TSK-106 - Benchmark model dan CPU runtime

- Prioritas: P0
- Dependency: TSK-105

Pekerjaan:

- Bandingkan PP-OCRv6 small vs medium.
- Bandingkan Paddle Inference vs OpenVINO jika didukung.
- Ukur accuracy, P50/P95, CPU, dan peak RAM mendekati production.

Acceptance criteria:

- Model/runtime production dipilih berdasarkan report yang reproducible.

---

## Milestone 2 - Refactor .NET Orchestrator

### TSK-201 - Buat branch arsitektur v1.6

- Prioritas: P0
- Dependency: TSK-106

Pekerjaan:

- Buat branch implementasi baru.
- Pertahankan v1.5 sebagai baseline/reference.
- Dokumentasikan migration boundaries.

Acceptance criteria:

- Tidak ada destructive rewrite baseline.
- Solution build/test lulus di development machine.

### TSK-202 - Definisikan domain model dan interfaces

- Prioritas: P0
- Dependency: TSK-201

Interfaces:

- `IOcrLayoutClient`
- `IPageClassifier`
- `IDocumentGrouper`
- `IDocumentExtractor`
- `IBusinessValidator`
- `IHesMatcher`
- `IConfidenceCalculator`

Acceptance criteria:

- Model-specific DTO tidak bocor ke HES layer.
- Domain mendukung header, line items, evidence, dan multiple identifiers.

### TSK-203 - Implement job state machine

- Prioritas: P0
- Dependency: TSK-202

Pekerjaan:

- States dari Queued sampai Completed/NeedsReview/Failed.
- Idempotency, cancellation, stage retry, correlation ID.
- Hangfire queue concurrency satu.

Acceptance criteria:

- Retry tidak membuat hasil ganda.
- OCR failure tidak menjatuhkan Invoice Portal.

### TSK-204 - Implement PDF intake dan native-text quality gate

- Prioritas: P0
- Dependency: TSK-202

Pekerjaan:

- Validasi signature/MIME/size/encryption/page count.
- Nilai native text; OCR ulang jika buruk.
- Render dengan DPI adaptif.

Acceptance criteria:

- Text layer buruk Invoice 02 tidak dianggap authoritative.
- Invalid file gagal dengan safe reason code.

### TSK-205 - Implement typed OCR/Layout client

- Prioritas: P0
- Dependency: TSK-105, TSK-202

Pekerjaan:

- Timeout, cancellation, retry policy, circuit breaker.
- Mapping response ke domain model.
- Simpan model execution metadata.

Acceptance criteria:

- Contract tests lulus dan retry tidak menduplikasi stage.

### TSK-206 - Ganti public processing API

- Prioritas: P0
- Dependency: TSK-203, TSK-205

Pekerjaan:

- Implement create/status/result/retry document-job endpoints.
- Deprecate atau jadikan diagnostic endpoint extract/clean/match lama.
- Jangan meminta frontend mengirim kembali OCR regions.

Acceptance criteria:

- Layout/evidence tidak hilang antartahap.
- API versioning terdokumentasi.

---

## Milestone 3 - Classification dan grouping

### TSK-301 - Implement page feature builder

- Prioritas: P0
- Dependency: TSK-205

Pekerjaan: bangun feature dari title/header blocks, anchors, supplier, page number, reference, dan layout signature.

Acceptance criteria: feature auditable tanpa menaruh full image/text sensitif di log.

### TSK-302 - Implement hybrid page classifier

- Prioritas: P0
- Dependency: TSK-301

Classes: `Invoice`, `DeliveryNote`, `TaxInvoice`, `SupportingDocument`, `Other`.

Acceptance criteria:

- Invoice 02 halaman 1-4 sesuai ground truth.
- Continuation page tidak menjadi `Other` hanya karena title tidak ada.

### TSK-303 - Implement logical-document grouper

- Prioritas: P0
- Dependency: TSK-302

Pekerjaan:

- Gunakan supplier, buyer, PO/invoice reference, date, page continuation, item, dan amount.
- Dukung satu PDF dengan banyak transaksi.

Acceptance criteria:

- Test mencakup single/multi transaction, continuation, dan irrelevant page.
- Ambiguity menghasilkan review, bukan forced grouping.

---

## Milestone 4 - Extractor dan evidence

### TSK-401 - Implement evidence framework

- Prioritas: P0
- Dependency: TSK-202, TSK-205

Pekerjaan:

- Simpan raw value, page, bbox, OCR/layout confidence, method, dan validation trace.
- Sediakan crop reference untuk review UI.

Acceptance criteria:

- Tidak ada non-derived value tanpa source evidence.

### TSK-402 - Implement DJP Tax Invoice extractor

- Prioritas: P0
- Dependency: TSK-303, TSK-401

Pekerjaan:

- Versioned anchor/ROI.
- Seller/buyer, nomor faktur, date, items, DPP, PPN, PPnBM, signer.
- Bedakan `tax_goods_code` dan `part_number`.

Acceptance criteria:

- Invoice 02 halaman 2 sesuai ground truth.
- Template mismatch memakai fallback + mandatory review.

### TSK-403 - Implement generic invoice extractor

- Prioritas: P0
- Dependency: TSK-303, TSK-401

Pekerjaan:

- Header, table mapping, wrapped description, totals, dan signature policy.

Acceptance criteria:

- Invoice Rukun menghasilkan field PRD.
- Company stamp tidak menjadi `signer_name`.
- Arithmetic failure membuat warning/review, bukan silent deletion.

### TSK-404 - Implement generic delivery-note extractor

- Prioritas: P0
- Dependency: TSK-303, TSK-401

Pekerjaan: document number/date/supplier dan item table untuk Packing Slip, Delivery Slip, Delivery Order, dan Surat Jalan.

Acceptance criteria: Invoice 02 halaman 3 sesuai ground truth.

### TSK-405 - Implement item identifier resolver

- Prioritas: P0
- Dependency: TSK-001, TSK-402, TSK-403, TSK-404

Pekerjaan:

- Simpan seluruh candidates.
- Resolve canonical part dengan label semantics dan master mapping.
- Return ambiguity jika beberapa kandidat valid.

Acceptance criteria:

- Semua kode Invoice 02 tersimpan dengan source yang benar.
- Tidak ada fuzzy substitution pada part number.

### TSK-406 - Implement supplier-profile registry

- Prioritas: P1
- Dependency: TSK-403, TSK-404

Pekerjaan:

- Schema profile tanpa pixel absolute.
- Profile Rukun dari beberapa sample tervalidasi.
- Versioning, disable, dan generic fallback.

Acceptance criteria:

- Profile baru wajib melewati regression suite.

---

## Milestone 5 - Validation, matching, confidence

### TSK-501 - Implement locale-safe normalizers

- Prioritas: P0
- Dependency: TSK-402, TSK-403, TSK-404

Pekerjaan:

- Indonesia/English date parser.
- Decimal parser untuk `7,000.00`, `7.000,00`, currency, dan unit.
- Identifier normalization tanpa mengubah digit/huruf.

Acceptance criteria:

- Culture-specific tests lengkap; raw value tetap tersimpan.

### TSK-502 - Implement business validators

- Prioritas: P0
- Dependency: TSK-002, TSK-501

Pekerjaan: quantity x price, line sum, totals, tax, date, identifier, dan cross-document consistency.

Acceptance criteria:

- Result berupa pass/fail/unknown + reason code.
- Validator tidak memperbaiki value tanpa evidence.

### TSK-503 - Redesign match contract

- Prioritas: P0
- Dependency: TSK-202, TSK-405

Pekerjaan:

- Match header + line items, bukan flat list.
- Align extracted rows dengan HES rows.
- Return unmatched/duplicate/ambiguous rows.

Acceptance criteria:

- Tests mencakup reordered, duplicate, missing, dan extra rows.

### TSK-504 - Implement field-specific HES matcher

- Prioritas: P0
- Dependency: TSK-501, TSK-503

Pekerjaan: exact identifiers, decimal/date/unit, supplier master, dan token similarity hanya untuk descriptive text.

Acceptance criteria:

- Satu digit berbeda pada critical identifier tidak match.
- False-match tests bersifat blocking.

### TSK-505 - Implement confidence calculator

- Prioritas: P0
- Dependency: TSK-502, TSK-504

Pekerjaan:

- Gabungkan detection, recognition, layout, extraction, validation, dan match confidence.
- Confidence per field, row, document, dan group.
- Implement policy TSK-002.

Acceptance criteria:

- Tidak ada confidence hardcoded berdasarkan method.
- Critical low-confidence selalu review.

---

## Milestone 6 - Persistence dan Finance review

### TSK-601 - Implement persistence schema

- Prioritas: P0
- Dependency: TSK-203, TSK-401

Pekerjaan: migration untuk job, page, logical document, evidence, extraction, validation, match, review, dan model execution.

Acceptance criteria:

- Reprocessing tidak menghapus history.
- Dashboard query tidak perlu membaca raw OCR JSON penuh.

### TSK-602 - Implement review API

- Prioritas: P0
- Dependency: TSK-505, TSK-601

Pekerjaan: review queue, comparison/evidence detail, accept/correct/reject, reason, dan reviewer audit.

Acceptance criteria:

- Correction tidak mengubah raw OCR evidence.
- Semua keputusan reviewer auditable.

### TSK-603 - Implement Finance review UI

- Prioritas: P1
- Dependency: TSK-602

Pekerjaan:

- HES vs extracted side-by-side.
- Highlight mismatch/low-confidence.
- Tampilkan page crop/bbox.
- Filter status, supplier, type, dan date.

Acceptance criteria:

- Reviewer memahami mismatch tanpa membuka aplikasi lain.

### TSK-604 - Capture review feedback dataset

- Prioritas: P1
- Dependency: TSK-602

Pekerjaan: simpan correction sebagai candidate gold data dengan approval workflow.

Acceptance criteria: feedback mentah tidak otomatis menjadi ground truth.

---

## Milestone 7 - Security, deployment, operations

### TSK-701 - Package OCR Engine untuk Windows Server

- Prioritas: P0
- Dependency: TSK-106

Pekerjaan:

- Offline installation bundle dan locked dependencies.
- Windows Service wrapper.
- Model/checksum/log/service-account configuration.

Acceptance criteria:

- Fresh staging server dapat di-install dari runbook tanpa internet runtime.
- Start/stop/restart/recovery teruji.

### TSK-702 - Implement security controls

- Prioritas: P0
- Dependency: TSK-701, TSK-203

Pekerjaan: loopback, firewall, ACL, request limits, temp cleanup, secret handling, dan log redaction.

Acceptance criteria:

- Security checklist disetujui IT.
- OCR endpoint tidak dapat diakses dari host lain.

### TSK-703 - Implement observability

- Prioritas: P0
- Dependency: TSK-203, TSK-205

Pekerjaan: structured logs, correlation IDs, queue/stage/model/resource/error/review metrics, dashboard, dan alerts.

Acceptance criteria:

- Satu job dapat ditelusuri end-to-end.
- Log tidak berisi full sensitive content.

### TSK-704 - Load, soak, dan failure testing

- Prioritas: P0
- Dependency: TSK-601, TSK-701, TSK-703

Pekerjaan:

- Uji file besar/korup, timeout, engine crash, restart, duplicate request, backlog, dan native memory leak.

Acceptance criteria:

- Portal tetap tersedia saat OCR gagal.
- Retry aman dan resource tidak melewati batas.

### TSK-705 - Production runbook dan rollback

- Prioritas: P0
- Dependency: TSK-704

Pekerjaan: install, configure, update/rollback model, backup/restore, troubleshooting, dan incident procedure.

Acceptance criteria:

- Tim IT dapat mengoperasikan service.
- Rollback aplikasi/model diuji di staging.

---

## Milestone 8 - Pilot dan production gate

### TSK-801 - Jalankan staging shadow pilot

- Prioritas: P0
- Dependency: Seluruh P0 Milestone 0-7

Pekerjaan:

- Jalankan supplier nyata dalam shadow mode.
- Bandingkan dengan pemeriksaan manual Finance.
- Rekam false match/mismatch, latency, memory, dan review rate.

Acceptance criteria:

- Tidak ada auto-action production selama shadow mode.
- Pilot report mendapat sign-off stakeholder.

### TSK-802 - Kalibrasi threshold

- Prioritas: P0
- Dependency: TSK-801

Pekerjaan: kalibrasi confidence berdasarkan pilot labels dan error cost.

Acceptance criteria:

- False automatic match menjadi safety metric utama.
- Threshold dan rationale terdokumentasi.

### TSK-803 - Production readiness review

- Prioritas: P0
- Dependency: TSK-802

Gates: accuracy, security, capacity, operations, review workflow, dan rollback.

Acceptance criteria:

- Go/no-go decision terdokumentasi.
- Auto-approval hanya aktif setelah seluruh critical gate lulus.

---

## Urutan implementasi wajib

1. Konfirmasi semantics dan gold dataset.
2. Ukur baseline lama.
3. Buktikan OCR/layout baru pada Invoice 02 dan corpus awal.
4. Pilih model dari benchmark CPU.
5. Refactor .NET orchestration/persistence.
6. Bangun classification/grouping.
7. Bangun extractor/evidence.
8. Bangun validation/matching/confidence.
9. Bangun review UI.
10. Hardening, shadow pilot, calibration, lalu production gate.

Jangan mulai fine-tuning, menambah LLM, atau membuat banyak supplier-specific rule sebelum benchmark dan generic pipeline selesai.

## Definition of Done global

Task berstatus `DONE` hanya jika:

- Code selesai dan direview.
- Automated test relevan lulus.
- Logging/error handling tersedia.
- Tidak ada data sensitif pada repository/log fixture.
- Dokumentasi/config diperbarui.
- Benchmark/regression tidak turun melewati threshold.
- Acceptance criteria dibuktikan dengan artifact hasil uji.
