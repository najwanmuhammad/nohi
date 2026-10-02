# Product Requirements Document (PRD)

# Sistem AI Document Checking - Modul Invoice Portal, Hino Enterprise System (HES)

| Atribut      | Nilai                                                |
| ------------ | ---------------------------------------------------- |
| Dokumen      | PRD v1.6                                             |
| Project      | Verifikasi invoice, faktur pajak, dan delivery note  |
| Modul        | Invoice Portal - Hino Enterprise System (HES)        |
| Disusun oleh | Juan (Magang AI & Full-Stack Engineer)               |
| Mentor       | Pak Budi dan Pak Sapto                               |
| Status       | Arsitektur final disepakati; siap implementasi ulang |
| Tanggal      | 22 September 2026                                    |

## Riwayat revisi

| Versi    | Perubahan utama                                                                                                                                                                                                                                                                                                                                                           |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1.0     | Python microservice: FastAPI, PaddleOCR, sentence-transformers, dan Ollama/Qwen.                                                                                                                                                                                                                                                                                          |
| v1.1     | Eksplorasi migrasi penuh ke .NET dan in-process class library.                                                                                                                                                                                                                                                                                                            |
| v1.2     | AI dipisahkan dari Invoice Portal; stack .NET dengan PaddleSharp/ONNX/LLamaSharp.                                                                                                                                                                                                                                                                                         |
| v1.3     | OllamaSharp dipakai untuk embedding dan LLM lokal; server production dikonfirmasi.                                                                                                                                                                                                                                                                                        |
| v1.4     | Canonical fields disusun; ditemukan kebutuhan klasifikasi per halaman dan composite field.                                                                                                                                                                                                                                                                                |
| v1.5     | Heuristik posisi diganti dengan OCR raw text dan structuring oleh MiniCPM/Ollama.                                                                                                                                                                                                                                                                                         |
| **v1.6** | **.NET menjadi application/orchestration layer; OCR dan layout memakai local Python service dengan pipeline resmi PaddleOCR. PP-OCRv6 dan PP-StructureV3 menjadi baseline. Ollama dikeluarkan dari critical path. Ditambahkan document grouping, generic parser + supplier profile, DJP extractor, field-specific matching, calibrated confidence, dan source evidence.** |

---

## 1. Ringkasan eksekutif

Finance Hino saat ini membandingkan secara manual data yang diinput supplier di HES dengan hardfile invoice, faktur pajak, dan delivery note. Sistem ini mengotomasi proses melalui lima tahap:

1. Menerima satu PDF yang dapat berisi beberapa jenis dokumen.
2. Melakukan deep-learning OCR dan document-layout analysis secara lokal.
3. Mengklasifikasikan dan mengelompokkan halaman menjadi logical documents.
4. Mengekstrak canonical fields dan line items dengan evidence koordinat.
5. Membandingkan hasil dengan data HES dan mengarahkan kasus meragukan ke review Finance.

Seluruh data diproses di server internal Hino. Tidak ada file, gambar, OCR text, atau data finansial yang dikirim ke cloud AI/OCR service.

ASP.NET Core tetap menjadi pusat workflow, integrasi, business rules, security, audit, dan matching. OCR/layout inference menggunakan service Python lokal terisolasi agar dapat memakai pipeline resmi PaddleOCR secara lengkap.

---

## 2. Latar belakang dan temuan implementasi

### 2.1 Masalah bisnis

- Verifikasi manual memperlambat proses Finance dan closing.
- Kesalahan satu digit pada invoice number, part number, atau amount berdampak besar.
- Layout invoice dan delivery note berbeda antarsupplier.
- Faktur pajak relatif seragam karena format DJP.
- Satu PDF dapat berisi halaman tidak relevan atau beberapa transaksi.
- Scan bervariasi dalam resolusi, skew, warna, kompresi, stamp, dan tanda tangan.

### 2.2 Temuan implementasi v1.5

- OCR hanya memakai satu model `LatinV5`, lalu menjalankan model yang sama pada citra asli dan hasil enhancement.
- Reading order dibangun dengan pengelompokan koordinat Y/X, bukan neural layout model.
- `layoutText` dan `regions` dibuang dari response default `/extract`, sehingga `/clean` biasanya kehilangan layout.
- Dokumen dibersihkan per halaman, bukan per logical document.
- Klasifikasi hanya berbasis fuzzy keyword.
- Regex dan arithmetic rule menjadi extractor utama pada beberapa bagian.
- MiniCPM menerima text dengan reading order yang sudah rusak.
- Kontrak `/clean` dan `/match` belum selaras untuk line items.
- Confidence belum terkalibrasi terhadap akurasi aktual.

Kesimpulan: akar masalah berada pada OCR document pipeline, layout analysis, reading order, dan grouping. Menambah prompt atau regex tidak menyelesaikannya.

### 2.3 Temuan Invoice 02 Rukun

| Halaman | Jenis                        | Perlakuan                               |
| ------: | ---------------------------- | --------------------------------------- |
|       1 | Sales Invoice                | Ekstrak dan match                       |
|       2 | Faktur Pajak DJP             | Ekstrak dan match                       |
|       3 | Packing Slip / Delivery Note | Ekstrak dan match                       |
|       4 | Purchase Order Hino          | Supporting document; bukan output utama |

Contoh ini membuktikan perlunya klasifikasi per halaman, grouping transaksi, dan supporting evidence.

---

## 3. Tujuan dan sasaran

| Tujuan                       | Sasaran                                                                                      |
| ---------------------------- | -------------------------------------------------------------------------------------------- |
| Mengurangi pengecekan manual | Finance hanya meninjau mismatch, ambiguity, dan low-confidence.                              |
| Menjaga akurasi              | Tidak ada auto-approval jika identifier/nominal kritis belum tervalidasi.                    |
| Mendukung supplier beragam   | Generic parser untuk supplier baru; supplier profile meningkatkan presisi supplier berulang. |
| Menjaga keamanan             | 100% pemrosesan di infrastruktur internal Hino.                                              |
| Menjaga auditability         | Setiap field memiliki source text, page, bbox, confidence, method, dan validation trace.     |
| Menjaga maintainability      | Business layer tetap .NET; AI runtime dipisahkan melalui REST contract stabil.               |

---

## 4. Ruang lingkup

### 4.1 In-scope MVP

- PDF scan dalam Indonesia, English, atau campuran.
- Invoice, delivery note/packing slip/surat jalan, dan faktur pajak DJP.
- PDF multi-page dan mixed-document.
- Page classification dan logical-document grouping.
- Orientation, deskew, unwarping, dan quality assessment.
- Deep-learning text detection/recognition.
- Layout, reading order, dan table analysis.
- Generic extraction + supplier profile untuk invoice/delivery note.
- Versioned DJP template/anchor extractor.
- Field evidence, confidence, HES matching, dan human review.
- Background processing dengan Hangfire.
- Self-hosted deployment pada Windows Server 2019.

### 4.2 Out-of-scope MVP

- Cloud OCR atau cloud LLM.
- Handwriting recognition umum; tanda tangan hanya dideteksi sebagai region.
- Training OCR dari nol.
- Fine-tuning sebelum pretrained baseline dibenchmark.
- Vision-language model besar sebagai extractor utama.
- Auto-approval dokumen ambigu.
- RabbitMQ/Kafka pada fase awal.
- Script selain Latin.

---

## 5. Prinsip desain final

1. **Accuracy before generative convenience.** OCR/layout dan deterministic validation menjadi fondasi.
2. **Self-hosted only.** Seluruh service hanya berjalan di jaringan internal Hino.
3. **.NET owns the business system.** Workflow, database, HES integration, rules, security, matching, dan audit tetap C#.
4. **Official AI runtime.** PaddleOCR resmi dijalankan sebagai Python service lokal.
5. **Evidence first.** Setiap nilai harus dapat ditelusuri ke halaman dan bbox.
6. **Fail safely.** Ketidakpastian menghasilkan `NeedsReview`, bukan tebakan.
7. **Field-specific matching.** Nomor dan nominal tidak dinilai dengan fuzzy text matching.
8. **Generic first, profile assisted.** Supplier profile meningkatkan presisi tetapi bukan satu-satunya mekanisme.

---

## 6. Arsitektur sistem

```text
Invoice Portal (.NET 8, IIS)
  - Upload, UI, HES snapshot, Hangfire
        |
        | REST localhost
        v
Document AI Orchestrator (.NET 8 Windows Service)
  - Job state machine
  - PDF/page orchestration
  - Classification & grouping
  - Extraction routing
  - Business validation
  - HES matching, audit, persistence
        |
        | REST localhost
        v
Local OCR/Layout Engine (Python Windows Service, 1 worker)
  - Quality assessment
  - Orientation, deskew, unwarping
  - PP-OCRv6 detection/recognition
  - PP-StructureV3 layout/table analysis
  - PaddleOCR-VL
  - JSON blocks, cells, coordinates, confidence
```

### 6.1 Keputusan teknologi

| Lapisan            | Teknologi                                           |
| ------------------ | --------------------------------------------------- |
| Invoice Portal     | ASP.NET Core 8, IIS                                 |
| Background job     | Hangfire                                            |
| AI orchestration   | ASP.NET Core Worker/Windows Service                 |
| PDF rendering      | PDFium/PDFtoImage; DPI adaptif                      |
| OCR/Layout service | Python, FastAPI, satu worker                        |
| OCR baseline       | PP-OCRv6 medium; small sebagai benchmark pembanding |
| Runtime CPU        | OpenVINO/Paddle Inference berdasarkan benchmark     |
| Layout/table       | PP-StructureV3                                      |
| Image processing   | OpenCV                                              |
| Faktur pajak       | DJP anchor + ROI + layout/table output              |
| Invoice/DN         | Generic layout parser + supplier profile            |
| Matching           | C# matcher per tipe field                           |
| LLM                | Tidak digunakan dalam critical path MVP             |

### 6.2 Batas service

- Invoice Portal hanya berkomunikasi dengan Orchestrator.
- OCR Engine bind ke `127.0.0.1` dan tidak mengakses database HES.
- Model/config dapat diganti tanpa mengubah business contract HES.

---

## 7. Alur pemrosesan

### 7.1 Job lifecycle

```text
Queued -> Preparing -> OCRProcessing -> Classifying -> Grouping
       -> Extracting -> Validating -> Matching
       -> Completed | NeedsReview | Failed
```

### 7.2 Tahapan

1. Portal menyimpan file, HES snapshot, hash, dan metadata upload.
2. Hangfire mengirim `documentJobId` ke Orchestrator.
3. Orchestrator memeriksa PDF, page count, encryption, dan native text layer.
4. Native text hanya digunakan jika lolos quality gate; text buruk di-OCR ulang.
5. Halaman dirender pada 300 DPI; dinaikkan hanya jika karakter terlalu kecil.
6. OCR Engine menjalankan preprocessing, OCR, layout, dan table analysis.
7. Orchestrator mengklasifikasikan halaman dan membentuk logical groups.
8. `Other`/supporting documents tidak dipaksa ke canonical schema.
9. Extractor dipilih berdasarkan jenis dokumen.
10. Nilai dinormalisasi tanpa mengubah source text.
11. Business dan cross-document validation dijalankan.
12. Data dibandingkan dengan HES memakai matcher sesuai tipe field.
13. Result, evidence, confidence, warnings, dan review status disimpan.

### 7.3 Preprocessing policy

- Original image tetap authoritative selama job.
- Binarization/CLAHE tidak diterapkan ke semua halaman.
- Enhancement hanya dijalankan jika quality/confidence membutuhkannya.
- Second pass dilakukan pada crop field kritis, bukan seluruh halaman.
- Transform matrix wajib disimpan agar bbox kembali ke koordinat asli.

---

## 8. Functional requirements

| ID    | Requirement                                                                                           |
| ----- | ----------------------------------------------------------------------------------------------------- |
| FR-1  | Menerima PDF/JPG/PNG dan membuat asynchronous job.                                                    |
| FR-2  | Memproses PDF image-only, native-text, dan campuran.                                                  |
| FR-3  | Menjalankan orientation, deskew, unwarping, dan quality assessment.                                   |
| FR-4  | Menghasilkan OCR text, polygon/bbox, dan confidence setiap region.                                    |
| FR-5  | Mendeteksi layout blocks, tables, rows, dan cells.                                                    |
| FR-6  | Mengklasifikasikan halaman sebagai Invoice, DeliveryNote, TaxInvoice, SupportingDocument, atau Other. |
| FR-7  | Mengelompokkan continuation pages menjadi logical document.                                           |
| FR-8  | Mengekstrak canonical header dan line-item fields.                                                    |
| FR-9  | Memakai template DJP dan tidak memetakan `Kode Barang/Jasa` sebagai `part_number`.                    |
| FR-10 | Memakai generic parser untuk supplier baru dan profile untuk supplier berulang.                       |
| FR-11 | Menyimpan semua kandidat item identifier sebelum memilih canonical `part_number`.                     |
| FR-12 | Memvalidasi arithmetic, totals, date, identifier format, dan cross-document consistency.              |
| FR-13 | Membandingkan extracted data dengan HES per field dan line item.                                      |
| FR-14 | Menyertakan evidence, confidence components, warning, dan reason code.                                |
| FR-15 | Menandai ambiguity/low-confidence/mismatch sebagai `NeedsReview`.                                     |
| FR-16 | Menampilkan source crop/bbox untuk review Finance.                                                    |
| FR-17 | Menggunakan supporting document sebagai evidence tanpa memasukkannya ke output utama.                 |
| FR-18 | Reprocessing tidak menghapus hasil historis.                                                          |

---

## 9. Non-functional requirements

| Kategori        | Requirement                                                                      |
| --------------- | -------------------------------------------------------------------------------- |
| Security        | Tidak ada data dikirim ke OCR/LLM eksternal.                                     |
| Network         | OCR Engine hanya melalui loopback/internal service account.                      |
| Isolation       | Portal, Orchestrator, dan OCR Engine merupakan proses berbeda.                   |
| Auditability    | Field menyimpan page, bbox, source, method, model version, dan validation trace. |
| Reliability     | Job idempotent dan dapat retry per stage tanpa hasil ganda.                      |
| Performance     | Target awal paket tipikal sebisa mungkin <30 detik; SLA final dari pilot.        |
| Resource        | Aman pada 4 vCPU dan 16 GB RAM bersama service lain.                             |
| Concurrency     | OCR Engine satu worker awal; Hangfire mengendalikan antrean.                     |
| Maintainability | REST contract versioned; business logic berada di .NET.                          |
| Observability   | Structured logs, durations, latency, RAM, queue length, dan reason code.         |

---

## 10. Canonical data model

### 10.1 Invoice

Header: `supplier_name`, `invoice_number`, `invoice_date`, `sub_total_amount`, `taxable_base`, `tax_amount`, `total_amount`, `signer_name`, `signer_position`.

Line item: `part_number`, `part_name`, `quantity`, `unit`, `price`, `amount`.

### 10.2 Delivery note

Header: `supplier_name`, `delivery_note_number`, `delivery_note_date`.

Line item: `part_number`, `part_name`, `quantity`, `unit`.

### 10.3 Faktur pajak

Header: `supplier_name`, `tax_invoice_number`, `tax_invoice_date`, `sub_total_amount`, `discount`, `down_payment`, `taxable_base`, `tax_amount`, `luxury_goods_sales_tax`, `signer_name`.

Line item: `part_number`, `part_name`, `quantity`, `unit`, `price`, `amount`.

### 10.4 Item identifier evidence

Sistem menyimpan semua kandidat internal:

- `supplier_item_code`
- `hino_item_code`
- `reference_item_code`
- `tax_goods_code`
- `source_label`, `source_page`, `source_bbox`

Canonical `part_number` dipilih berdasarkan label semantics, master data, dan aturan HES. `tax_goods_code` tidak boleh otomatis menjadi `part_number`.

### 10.5 Field evidence

```json
{
  "canonicalField": "invoice_number",
  "value": "IN00260705553",
  "rawValue": "IN00260705553",
  "pageNumber": 1,
  "boundingBox": [0.7, 0.04, 0.92, 0.09],
  "detectionConfidence": 0.99,
  "recognitionConfidence": 0.99,
  "layoutConfidence": 0.98,
  "extractionMethod": "anchor-right-value",
  "validation": ["format-valid", "ocr-crop-confirmed"]
}
```

---

## 11. Extraction strategy

### 11.1 Faktur pajak DJP

- Versioned template berdasarkan anchor text dan relative ROI.
- Ekstrak seller, buyer, nomor seri, item table, summary, date, dan signer dari region semantik.
- `Kode Barang/Jasa` disimpan sebagai `tax_goods_code`.
- Part number/name/quantity/price diurai dari cell nama barang jika gabungan.
- Tanggal diambil dari signature area tervalidasi, bukan tanggal terakhir global.
- Jika anchor utama hilang, gunakan generic fallback dan mandatory review.

### 11.2 Invoice dan delivery note

Generic parser:

- Mendeteksi title, supplier/buyer, header fields, table, totals, footer, dan signature.
- Memetakan table header dengan synonym dictionary dan relasi spasial.
- Menggabungkan wrapped description ke row yang benar.
- Memisahkan composite field hanya jika pattern/evidence mendukung.

Supplier profile:

- Berisi supplier identity, anchor synonyms, spatial relations, header aliases, document-number pattern, dan item-code semantics.
- Tidak bergantung pada pixel absolut.
- Diaktifkan setelah diuji pada beberapa dokumen supplier.
- Generic parser tetap fallback.

### 11.3 Signer policy

- Nama signer hanya diisi jika nama manusia terbaca di signature region.
- Company stamp bukan signer name.
- Coretan tanda tangan tidak ditranskripsikan.
- Jika hanya `Prepared`/`Approved` tanpa nama, signer `null`.

---

## 12. Classification dan grouping

Classification menggabungkan visual/layout features, title/header text, anchor location, supplier identity, page number, continuation markers, reference number, dan similarity dengan halaman sebelumnya.

Grouping memakai invoice/PO/delivery/tax references, supplier, buyer, date proximity, item/amount consistency, dan continuation evidence. Keyword fuzzy hanya satu feature, bukan classifier tunggal.

---

## 13. Matching strategy

| Tipe field       | Metode                                                        |
| ---------------- | ------------------------------------------------------------- |
| Document number  | Exact setelah normalisasi case/separator yang diizinkan       |
| Part number      | Exact atau approved master-data mapping                       |
| Date             | Exact parsed date                                             |
| Quantity         | Exact decimal dan unit normalization                          |
| Price/amount/tax | Exact decimal dengan approved rounding tolerance              |
| Supplier         | Supplier master ID; normalized name hanya supporting evidence |
| Part name        | Token similarity; bukan satu-satunya auto-approval signal     |
| Signer           | Normalized text similarity jika diwajibkan                    |

Satu digit berbeda pada critical identifier tetap mismatch/review.

Business validation mencakup quantity x price, line sum, totals, tax, date, dan cross-document consistency. Validator tidak boleh memperbaiki OCR value tanpa evidence.

---

## 14. Confidence dan keputusan otomatis

Confidence dipisahkan menjadi `detection`, `recognition`, `layout`, `extraction`, `validation`, dan `match`. Final confidence tidak boleh hardcoded atau sekadar rata-rata tanpa kalibrasi.

Dokumen hanya `MatchedHighConfidence` jika:

- Semua critical identifiers exact match.
- Semua critical amounts match.
- Tidak ada ambiguity pada part mapping.
- Required validations lolos.
- Tidak ada target page gagal.
- Confidence setiap critical field melewati threshold terkalibrasi.

Selain itu statusnya `NeedsReview` atau `Mismatch`.

---

## 15. API contract

### 15.1 Portal ke Orchestrator

```http
POST /api/v1/document-jobs
GET  /api/v1/document-jobs/{jobId}
GET  /api/v1/document-jobs/{jobId}/result
POST /api/v1/document-jobs/{jobId}/retry
```

### 15.2 Orchestrator ke OCR Engine

```http
GET  /health
GET  /ready
GET  /model-info
POST /v1/analyze-page
```

`analyze-page` mengembalikan preprocessing metadata, OCR regions/polygons, text confidence, layout blocks, tables/rows/cells, reading order, model/config version, dan timings. OCR Engine tidak menghasilkan canonical HES fields.

---

## 16. Persistence dan audit

Entitas minimum:

- `DocumentJob`, `DocumentFile`, `DocumentPage`, `LogicalDocument`
- `OcrRegion`, `LayoutBlock`
- `ExtractedField`, `ExtractedLineItem`, `FieldEvidence`
- `ValidationResult`, `MatchResult`, `ReviewDecision`, `ModelExecution`

Setiap execution menyimpan model/config/application version, duration, dan resource metrics. Reprocessing membuat execution baru.

---

## 17. Keamanan

- Endpoint AI bind ke localhost dan dibatasi firewall.
- Dedicated Windows service account dengan least privilege.
- Temporary directory memiliki ACL dan automatic cleanup.
- Tidak ada telemetry/model download otomatis di production.
- Model diimpor melalui IT dan diverifikasi checksum.
- Log tidak mencetak full OCR text atau data sensitif secara default.
- Review dan akses memiliki audit trail.

---

## 18. Observability

Metrics minimum: queue length/job age, stage duration, OCR latency, peak RAM/CPU, failure rate, classification distribution, review rate, false match/mismatch, model version, dan automatic completion rate.

Correlation IDs: `uploadId`, `documentJobId`, `logicalDocumentId`, dan `modelExecutionId`.

---

## 19. Lingkungan production

| Komponen     | Spesifikasi                                                 |
| ------------ | ----------------------------------------------------------- |
| CPU          | Intel Xeon Gold 5118, 2.3 GHz, 4 vCPU                       |
| RAM          | 16 GB bersama OS, IIS, Portal, Orchestrator, dan OCR Engine |
| GPU          | Tidak ada                                                   |
| Virtualisasi | VMware                                                      |
| OS           | Windows Server 2019                                         |
| Web server   | IIS                                                         |

Kebijakan awal:

- OCR Engine dan Hangfire AI queue concurrency satu.
- PP-OCRv6 medium baseline; small dibandingkan pada corpus sama.
- Fitur formula/chart PP-StructureV3 dinonaktifkan.
- Ollama tidak dijalankan pada critical path.
- SLA final ditetapkan setelah pilot.

---

## 20. Benchmark dan acceptance criteria

Gold dataset memuat seluruh supplier sampel, tiga target document types, supporting documents, single/multi-page, variasi scan, supplier baru, serta ground truth text, order, type, grouping, fields, rows, dan match decision.

| Lapisan        | Metrik                                   |
| -------------- | ---------------------------------------- |
| Recognition    | CER, WER, identifier exact accuracy      |
| Detection      | Precision, recall, H-mean                |
| Reading order  | Block/line sequence accuracy             |
| Table          | Row/column/cell F1                       |
| Classification | Precision/recall per type                |
| Grouping       | Logical-group accuracy                   |
| Extraction     | Exact match per field/row                |
| Matching       | False match, false mismatch, review rate |
| Operational    | P50/P95 latency, peak RAM/CPU            |

Initial pilot targets, bukan jaminan sebelum benchmark:

- Critical identifier exact accuracy >=99% pada minimum scan quality yang disepakati.
- Header field exact accuracy >=98%.
- Line-item row exact accuracy >=97%.
- False automatic match mendekati nol dan dilaporkan terpisah.
- Tidak ada hallucinated value; non-derived value wajib memiliki evidence.
- OCR Engine stabil pada soak test dan tidak menyebabkan Portal crash.
- Peak memory berada dalam batas aman server.

---

## 21. Risiko dan mitigasi

| Risiko                        | Mitigasi                                                                                       |
| ----------------------------- | ---------------------------------------------------------------------------------------------- |
| Layout model lambat di 4 vCPU | Nonaktifkan submodel, quality gating, benchmark tier, pertahankan async workflow.              |
| Python menambah maintenance   | Service kecil, locked dependencies, health endpoint, installer, runbook, REST contract stabil. |
| Supplier baru ekstrem         | Generic parser + review; buat profile setelah sample cukup.                                    |
| Native text PDF buruk         | Native-text quality gate dan OCR fallback.                                                     |
| Salah memilih part number     | Simpan seluruh identifier evidence dan gunakan approved master mapping.                        |
| Format DJP berubah            | Versioned template + generic fallback dengan mandatory review.                                 |
| OCR confident tetapi salah    | Crop retry, type validation, exact HES comparison, calibrated confidence.                      |
| PDF mencampur transaksi       | Logical grouping dan cross-document checks.                                                    |
| Resource contention           | Single worker, queue control, metrics, dan circuit breaker.                                    |

---

## 22. Rencana rilis

1. Benchmark foundation: gold dataset, baseline v1.5, target metrics.
2. OCR/Layout POC: local Python service, PP-OCRv6, PP-StructureV3, Invoice 02 Rukun.
3. .NET orchestration: job state, API, persistence, retry, evidence contract.
4. Document intelligence: classification, grouping, DJP extractor, invoice/DN parser.
5. Matching and review: HES matching, confidence gate, Finance review UI.
6. Supplier profiles: Rukun dan supplier prioritas dari validated samples.
7. Pilot/calibration: threshold, performance, memory, false-match analysis.
8. Production hardening: security, monitoring, runbook, rollback.

---

## 23. Keputusan final

- Application/business layer tetap .NET 8/C#.
- AI inference tidak dipaksa full .NET.
- OCR/Layout Engine memakai Python local service dan PaddleOCR resmi.
- PP-OCRv6 + PP-StructureV3 wajib dibenchmark.
- Ollama/MiniCPM keluar dari critical path MVP.
- Faktur pajak memakai versioned DJP extractor.
- Invoice/DN memakai generic layout parser + supplier profile.
- Supporting documents dapat menjadi evidence.
- Matching memakai aturan per tipe field.
- Human review menangani ambiguity dan low confidence.
- Seluruh pemrosesan tetap self-hosted.

---

## 24. Konfirmasi wajib sebelum auto-approval

1. Definisi `part_number` ketika tersedia PLU supplier, kode referensi, dan kode Hino. `part_number` adalah kode dari hino pokoknya.
2. Tolerance pembulatan amount/tax dari Finance.
3. Critical fields per document type untuk auto-approval.
4. Volume dokumen harian/bulanan untuk capacity target.
5. Retention period untuk OCR evidence, crops, raw output, dan review history.

Konfirmasi ini tidak menghalangi OCR/Layout POC, tetapi wajib selesai sebelum auto-approval aktif.
