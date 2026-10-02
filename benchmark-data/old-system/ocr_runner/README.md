# Offline OCR runner

Runner ini mengerjakan OCR murni: PDF menjadi teks, confidence, polygon, dan bounding box. Runner belum melakukan klasifikasi dokumen, ekstraksi field, LLM processing, atau HES matching.

## Instalasi

Gunakan Python virtual environment. Instal PaddlePaddle CPU/GPU yang cocok dengan sistem operasi, driver, dan CUDA dari petunjuk resmi PaddlePaddle terlebih dahulu, kemudian:

```bash
pip install -r ocr_runner/requirements.txt
```

Model akan diunduh saat penggunaan pertama. Setelah model tersedia di cache lokal, pemrosesan dokumen berjalan offline.

## Smoke test satu dokumen

Jalankan dari folder `old-system`:

```bash
python ocr_runner/run_ocr.py \
  --documents ../documents \
  --output ocr-results/ppocrv6-quality-v1 \
  --config ocr_runner/configs/ppocrv6-quality.json \
  --manifest ../manifest.json \
  --split development \
  --document-id invoice-02 \
  --device gpu:0
```

Jika GPU tidak tersedia:

```bash
python ocr_runner/run_ocr.py \
  --documents ../documents \
  --output ocr-results/ppocrv6-quality-v1 \
  --config ocr_runner/configs/ppocrv6-quality.json \
  --manifest ../manifest.json \
  --split development \
  --document-id invoice-02 \
  --device cpu
```

Periksa `ocr-results/ppocrv6-quality-v1/invoice-02.json`. Setelah smoke test benar, hapus `--document-id` untuk memproses seluruh **development split**. Jangan mengubah `--split development` menjadi `holdout` selama tuning. Gunakan `--overwrite` hanya ketika memang ingin mengganti hasil konfigurasi yang sama.

## Eksperimen yang harus dijalankan

1. `ppocrv6-balanced.json`: tanpa unwarping, lebih cepat dan menjaga geometri tabel.
2. `ppocrv6-quality.json`: dengan unwarping dan detection resolution lebih tinggi.

Jangan menentukan pemenang dari satu dokumen. Jalankan keduanya pada development split dan bandingkan OCR/field accuracy setelah extraction adapter tersedia.
