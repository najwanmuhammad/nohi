# Old System v1.5 Baseline and New OCR Runner

Folder ini menyimpan output asli sistem lama dan program untuk mengubahnya menjadi baseline benchmark tanpa membaca ground truth.

## Membuat prediction baseline v1.5

Jalankan dari folder `old-system`:

```bash
python tools/export_baseline_predictions.py \
  --old-system . \
  --output predictions/baseline-v1.5
```

Kemudian jalankan benchmark dari root `benchmark-data`:

```bash
python benchmark/benchmark.py evaluate \
  --dataset-root . \
  --predictions old-system/predictions/baseline-v1.5 \
  --split development \
  --model-version old-system-v1.5 \
  --config-version original-extract-clean \
  --output benchmark-results/old-system-v1.5/development
```

Baseline ini selalu memberi keputusan `needs_review` karena ZIP tidak memiliki output tahap HES matching. Nilai extraction, classification, dan grouping tetap dihitung secara nyata.

### Hasil development baseline yang dibekukan

| Metrik | Hasil |
|---|---:|
| Prediction coverage | 100.00% |
| Field accuracy | 57.74% |
| Required-field accuracy | 74.75% |
| Identifier accuracy | 74.36% |
| Row accuracy | 0.00% |
| Page classification accuracy | 88.24% |
| Logical grouping accuracy | 58.82% |
| Decision accuracy | 0.00% |

Decision accuracy bernilai nol karena ZIP baseline tidak berisi tahap HES matching. Latency dan peak memory juga tidak direkam oleh output lama, sehingga bernilai `N/A`; keduanya tidak boleh diperkirakan atau dikarang. Detail error tersedia di `benchmark-results/development/field-errors.csv`.

## Menjalankan OCR baru

Lihat `ocr_runner/README.md`. Mulai dari `invoice-02` sebagai smoke test, lalu jalankan semua PDF pada development split. Jangan gunakan holdout untuk memilih konfigurasi.

## Membuat checksum baru

Setiap kali ground truth, manifest, split, benchmark, atau program berubah, jalankan dari root `benchmark-data`:

```bash
python old-system/tools/generate_checksums.py \
  --root . \
  --output checksums.sha256
```

File checksum lama sengaja tidak ikut dihitung. Folder cache, virtual environment, `.git`, `.vscode`, `.idea`, dan bytecode Python juga dikecualikan. Folder hasil yang berubah setiap eksperimen (`old-system`, `ocr-results`, `benchmark-results`, dan `predictions`) tidak ikut dihitung ketika perintah dijalankan dari root `benchmark-data`.

## Unit test

```bash
python -m unittest discover -s old-system/tests -p "test_*.py"
```
