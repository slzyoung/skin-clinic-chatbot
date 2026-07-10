# Sprint 3: Hybrid Search, Metadata Filtering & Reranking Layer

## Overview
Fokus utama dari Sprint 3 adalah membangun **Retriever Layer** tingkat lanjut yang melampaui pencarian semantik (dense) sederhana. Kami mengintegrasikan pencarian semantik dense (Qdrant) dan pencarian kata kunci sparse (BM25) menggunakan algoritma **Reciprocal Rank Fusion (RRF)**, dilanjutkan dengan penyaringan metadata (metadata filtering) secara native dan pengurutan ulang (reranking) menggunakan model **Cross-Encoder** untuk performa RAG skala produksi.

Pencarian hibrida ini menjamin akurasi pencarian yang tinggi untuk query yang kaya akan kata kunci spesifik (lexical) maupun query semantik, sementara reranker meminimalisir halusinasi dengan memilah konteks yang benar-benar relevan sebelum dikirimkan ke LLM.

---

## Arsitektur & Komponen Layer Retrieval

### 1. Sparse BM25 Index (`retrieval/bm25.py`)
Membangun mesin indeks kata kunci lokal menggunakan pustaka `rank-bm25` (BM25Okapi):
- **Tokenisasi**: Membersihkan teks dan memecahnya menjadi token kata (lowercase, regex split).
- **Penyaringan Metadata**: Mendukung penyaringan metadata (*metadata filtering*) secara dinamis pada calon kandidat sebelum dilakukan perhitungan skor BM25.
- **Deteksi Overwrite Re-Ingestion**: Secara otomatis menghapus data chunk lama dari dokumen/berkas sumber yang sama (`source_file`) sebelum menyimpan data chunk baru untuk menghindari duplikasi data.
- **Persistensi Lokal**: Menyimpan (`save`) dan memuat (`load`) data indeks ke berkas lokal `qdrant_data/bm25_index.pkl` menggunakan serialisasi `pickle`.

### 2. Cross-Encoder Reranker (`retrieval/reranker.py`)
Mengintegrasikan model Cross-Encoder untuk mengukur relevansi query dengan teks chunk secara berpasangan:
- **Model**: Menggunakan model lintas bahasa `BAAI/bge-reranker-base` melalui pustaka `sentence-transformers`.
- **Akurasi**: Model mengevaluasi hubungan semantik antara query dan teks chunk secara penuh (bukan sekadar kemiripan vektor kosinus), memberikan skor kecocokan baru (*rerank_score*).
- **Context Enrichment**: Reranker memasangkan kueri dengan teks kandidat yang diperkaya secara terstruktur dengan format `"Product: {product_name} | Section: {section} | Content: {text}"` sebelum dievaluasi oleh model. Hal ini memastikan model memahami dengan tepat produk/perawatan mana yang memiliki kandungan atau petunjuk tersebut, sehingga menekan angka salah asosiasi.
- **Top-N Slicing**: Memilah sejumlah `rerank_top_n` kandidat terbaik dari hasil fusion untuk dikirimkan sebagai konteks LLM.

### 3. RRF Fusion & Hybrid Retriever (`retrieval/retriever.py`)
Sebagai orkestrator yang menyatukan alur pencarian:
- **Reciprocal Rank Fusion (RRF)**: Menggabungkan hasil Dense Search (Qdrant) dan Sparse Search (BM25). Skor RRF dihitung dengan rumus:
  $$Score_{RRF}(d) = \frac{1}{60 + Rank_{dense}} + \frac{1}{60 + Rank_{sparse}}$$
  Mekanisme ini memastikan chunk yang muncul di peringkat atas pada kedua pencarian akan mendapatkan prioritas utama.
- **Fusi Alur**: Mengoordinasikan langkah: `Retrieve (Dense & Sparse) -> Filter -> RRF -> Reranking -> Top-N Context`.

### 4. Prompt Context Builder (`retrieval/context_builder.py`)
Menyusun chunk-chunk hasil pencarian menjadi format string tunggal yang siap dibaca oleh LLM dengan sitasi yang terstruktur. Metadata `product_name` ditambahkan di dalam payload agar frontend dapat menampilkan kartu produk atau menyaring daftar rekomendasi dengan mudah:
```text
[1] Source: ERHA-Acne-Clear-Gel.pdf | Product: ERHA Acne Clear Gel | Section: ACTIVE INGREDIENTS | Page: 1
Content:
Salicylic Acid
Niacinamide
Zinc PCA
```

### 5. Confidence Check (BRD Requirement)
Mekanisme pertahanan terhadap pertanyaan di luar domain pengetahuan (*out-of-domain queries*):
- **Ambang Batas (Threshold)**: Menggunakan konfigurasi `rerank_confidence_threshold` (default `0.1`).
- **Penolakan Otomatis**: Jika hasil teratas memiliki `rerank_score` di bawah batas threshold, sistem akan mengosongkan list hasil (`results: []`) dan mengembalikan teks context fallback: `"Maaf, saya tidak menemukan informasi."`. Hal ini mencegah LLM melakukan halusinasi jawaban.

### 6. Retrieval Evaluator (`retrieval/evaluation.py`)
Mengevaluasi kualitas hasil pencarian secara kuantitatif melalui metrik:
- **Hit Rate @ K**: Apakah dokumen/chunk target yang benar masuk ke dalam Top K hasil pencarian.
- **Mean Reciprocal Rank (MRR) @ K**: Mengukur kualitas peringkat chunk yang benar (makin atas peringkatnya, makin mendekati 1.0).

---

## Alur Integrasi API (FastAPI)

Semua modul retrieval di atas diintegrasikan ke dalam [app/main.py](file:///c:/Users/wildan/Downloads/ARYA-NOBLE/arya-noble-rag/app/main.py):

1. **startup_event**: Menginisialisasi `BM25Index`, memuat model `CrossEncoder` reranker, dan merakit instance `HybridRetriever` global pada saat server dimulai.
2. **POST /ingest**: 
   Setelah parsing dan indexing di Qdrant selesai, server secara otomatis mendaftarkan chunk dokumen baru ke dalam `BM25Index` lokal, lalu menyimpannya ke disk di `./qdrant_data/bm25_index.pkl`.
3. **GET /search**:
   Endpoint pencarian terstruktur yang diperbarui untuk mendukung:
   - `query` (string): Query pencarian.
   - `top_k` (integer, default 5): Jumlah hasil akhir.
   - `rerank` (boolean, default True): Menyalakan/mematikan Cross-Encoder reranker.
   - `document_type` (string opsional): Menyaring berdasarkan tipe dokumen (`product`, `treatment`, `faq`, `promotion`, `sop`).
   - `section` (string opsional): Menyaring berdasarkan bab/section (`ACTIVE INGREDIENTS`, `HOW TO USE`, dll).
   - `confidence_threshold` (float opsional): Nilai batas kepercayaan kustom (jika tidak diisi, menggunakan default `0.1` dari sistem).
4. **POST /search/evaluate**:
   Endpoint evaluasi yang menerima dataset berisi query dan label ground truth untuk mengukur performa RAG.

---

## Cara Menjalankan & Validasi

### 1. Jalankan Unit Test
Untuk memverifikasi fungsionalitas seluruh modul retrieval secara terpisah (BM25, Reranker, RRF, Context Builder, dan Evaluator):
```powershell
python -m unittest test.test_sprint3_retrieval
```

### 2. Menguji Search dengan Penyaringan Metadata
Gunakan curl atau Swagger UI untuk mencari dokumen dengan filter kustom secara langsung:
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/search?query=kandungan&top_k=3&document_type=product&section=ACTIVE%20INGREDIENTS' \
  -H 'accept: application/json'
```

### 3. Menguji Endpoint Evaluasi
Kirim permintaan `POST` ke `/search/evaluate` dengan dataset uji:
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/search/evaluate' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '[
    {
      "query": "kandungan ERHA Acne Clear Gel",
      "ground_truth": {
        "source_file": "dumy-ERHA-Acne-Clear-Gel.docx",
        "section": "ACTIVE INGREDIENTS"
      }
    }
  ]'
```
Sistem akan mengembalikan nilai Hit Rate dan MRR untuk evaluasi tersebut.
