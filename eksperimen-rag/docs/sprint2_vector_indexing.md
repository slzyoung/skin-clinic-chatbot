# Sprint 2: Vector Indexing & Semantic Search (Qdrant & FastAPI)

## Overview
Fokus dari Sprint 2 adalah mengintegrasikan **Vector Database (Qdrant)** dan model embedding (**BAAI/bge-m3**) ke dalam Ingestion Pipeline yang telah dibangun di Sprint 1. Hal ini memungkinkan sistem RAG untuk melakukan penyimpanan representasi vektor dari dokumen (indexing) dan pencarian semantik (semantic search) secara langsung via API.

Dengan integrasi ini, seluruh dokumen yang di-ingest tidak hanya diekspor ke file JSON lokal, tetapi juga langsung diproses menjadi vektor berdimensi 1024 dan disimpan ke dalam database Qdrant lokal (`./qdrant_data`) dengan penanganan ID yang deterministik untuk menghindari duplikasi data.

---

## Arsitektur & Komponen Utama

### 1. Vector Store Adapter (`core/adapters.py`)
Menerapkan **Adapter Pattern** dengan memisahkan antarmuka (`BaseVectorStoreAdapter`) dari implementasi spesifiknya:
- **`QdrantAdapter`**: Mengontrol interaksi dengan database Qdrant. Mendukung penyimpanan lokal berbasis file (`./qdrant_data`) maupun penyimpanan memori (`:memory:`).
- **Pembuatan Koleksi Otomatis**: Secara otomatis membuat koleksi `arya_noble_kb` jika belum ada dengan konfigurasi dimensi vektor sebesar `1024` dan metrik jarak `Cosine Similarity`.
- **Deterministic ID Generation**: Menghasilkan UUIDv5 yang unik berdasarkan kombinasi `source_file` dan `chunk_index` agar re-ingestion dokumen yang sama akan memperbarui (overwrite) vektor yang ada daripada membuat entri duplikat.

### 2. Embedding Model Integration
Menggunakan `BAAI/bge-m3` melalui `HuggingFaceEmbeddings` dari LangChain. Model ini dipilih karena:
- Mendukung multibahasa secara optimal (sangat cocok untuk dokumen campuran Bahasa Indonesia dan Inggris).
- Menghasilkan representasi semantik berkualitas tinggi dengan panjang dimensi 1024.

### 3. FastAPI REST Endpoints (`app/main.py`)
Mengembangkan tiga API endpoint baru untuk mempermudah akses dan integrasi frontend:
- **`GET /health`**: Memverifikasi status API dan memastikan koneksi ke Qdrant Adapter aktif.
- **`POST /ingest`**: 
  - Menerima unggahan berkas dokumen (PDF, DOCX, dll.).
  - Menyimpannya sementara di `data/temp/`.
  - Melakukan ekstraksi struktur dokumen (Docling), chunking semantik, dan pengisian metadata secara berurutan.
  - Memasukkan representasi vektor chunk ke Qdrant (jika parameter `index=true` dikirim).
  - Melakukan pembersihan file temporer setelah ingestion selesai.
- **`GET /search`**: 
  - Menerima query teks pencarian dan parameter jumlah hasil (`top_k`).
  - Mengonversi query teks menjadi vektor embedding.
  - Melakukan pencarian kemiripan kosinus (Cosine Similarity) di Qdrant dan mengembalikan daftar chunk teks yang paling relevan beserta skor kemiripan dan metadata lengkapnya.

---

## Alur Ingestion & Indexing Terintegrasi
```
[ Upload via API /ingest ]
          │
          ▼
[ Save Temp File ] ──► [ Docling Parser ] ──► [ Custom Chunker ] ──► [ Metadata Enricher ]
                                                                             │
                                                                             ▼
[ Output JSON Saved ] ◄───────────────────────────────────────────── [ Build Payload ]
          │
          ▼
[ Embed via BGE-M3 ] ──► [ Upsert to Qdrant ] ──► [ Cleanup Temp File ]
```

---

## Analisis, Pemecahan Masalah & Optimalisasi (Sprint 2 Solved Issues)

Selama pengujian awal Sprint 2 menggunakan dokumen produk, ditemukan dua masalah utama yang kemudian berhasil **diatasi secara langsung** pada iterasi ini:

### 1. Masalah File Lock pada Windows (`WinError 32`) - SOLVED ✅
* **Gejala:** Saat mengunggah dokumen via `/ingest`, server gagal menghapus file temporer di `data/temp/` dan memunculkan peringatan `[WinError 32] The process cannot access the file because it is being used by another process`.
* **Penyebab:** Instans `DocumentConverter` milik Docling menahan OS-level file handle dokumen selama konversi berlangsung.
* **Solusi Perbaikan:** Mengubah parser di [parser.py](file:///c:/Users/wildan/Downloads/ARYA-NOBLE/arya-noble-rag/ingestion/parser.py) agar membaca bytes berkas terlebih dahulu menggunakan context manager Python (`with open`), kemudian melewatkannya sebagai in-memory stream menggunakan `docling_core.types.io.DocumentStream` ke Docling. Dengan cara ini, file handle langsung tertutup di level OS dan file temporer dapat dihapus dengan sukses setelah ingestion selesai.

---

### 2. Masalah Presisi Retrieval (Context Loss) - SOLVED ✅
* **Gejala:** Query *"kandungan ERHA Acne Clear Gel"* malah mengembalikan chunk dari `PRODUCT OVERVIEW` alih-alih chunk berisi bahan aktif di `ACTIVE INGREDIENTS` (seperti Salicylic Acid, Niacinamide, Zinc PCA).
* **Penyebab:** Chunk `ACTIVE INGREDIENTS` tidak memuat kata kunci produk *"ERHA Acne Clear Gel"* secara eksplisit (hanya berbunyi *"The formulation contains..."*), sehingga model embedding dense tidak mendeteksi kemiripan yang cukup kuat jika dibandingkan dengan chunk `PRODUCT OVERVIEW` yang menyebutkan nama produk di awal kalimat.
* **Solusi Perbaikan (Context Enrichment / Metadata Prepending):**
  Mengubah penyusunan teks sebelum pembuatan embedding di [adapters.py](file:///c:/Users/wildan/Downloads/ARYA-NOBLE/arya-noble-rag/core/adapters.py). Sebelum di-embed, teks chunk diperkaya secara dinamis dengan format:
  `"Product: [Nama Produk] | Section: [Nama Section] | Content: [Teks Asli Chunk]"`
  
  *Nama Produk* diekstrak secara dinamis dari nama file dokumen yang di-ingest.
  * **Hasil Uji Coba Baru:**
    Setelah dokumen re-ingested, query *"kandungan ERHA Acne Clear Gel"* berhasil menempatkan chunk dari `ACTIVE INGREDIENTS` di peringkat **Top 1, 2, dan 3** secara konsisten dengan skor kemiripan tertinggi (~0.78). Teks payload yang disimpan ke database Qdrant tetap bersih (tanpa prepended header) untuk kebutuhan LLM generation.

---

### 3. Masalah Fragmentasi List / Micro-Chunking - SOLVED ✅
* **Gejala:** Teks yang berformat daftar/list (seperti bahan aktif: *Salicylic Acid, Niacinamide, Zinc PCA*) dipisah oleh parser menjadi chunk-chunk mikro mandiri yang hanya berisi satu kata/bahan. Hal ini menyebabkan LLM kehilangan konteks keseluruhan bahan aktif (hanya mendapatkan satu bahan saja saat retrieval).
* **Penyebab:**
  1. Docling secara bawaan membagi setiap butir list item menjadi objek terpisah.
  2. Adanya bug bawaan pada klasifikasi tipe chunk di `chunker.py`, di mana class name dideteksi menggunakan `type(sc).__name__` yang selalu bernilai `"DocChunk"`, sehingga pemeriksaan tipe `"TextChunk"` selalu bernilai `False` dan memblokir alur pemrosesan teks.
* **Solusi Perbaikan (Sequential Chunk Merging & Classification Fix):**
  1. **Deteksi Chunk Dinamis**: Memperbaiki file [chunker.py](file:///c:/Users/wildan/Downloads/ARYA-NOBLE/arya-noble-rag/ingestion/chunker.py) agar memeriksa isi `sc.meta.doc_items` secara dinamis. Jika terdeteksi mengandung `TableItem` atau `PictureItem`, chunk diklasifikasikan sebagai `TableChunk` atau `PictureChunk`. Jika tidak, diklasifikasikan sebagai `TextChunk`.
  2. **Algoritma Merging Berurutan**: Menambahkan logika penggabungan chunk berturut-turut yang berada pada **halaman yang sama** dan **section yang sama** hingga batas karakter tertentu (`max_length_for_semantic = 500`).
* **Hasil**: Daftar bahan aktif berhasil digabungkan menjadi satu chunk utuh (`"Salicylic Acid\nNiacinamide\nZinc PCA"`). RAG kini mengembalikan seluruh bahan aktif sekaligus, siap memberikan konteks yang lengkap kepada LLM.

---

## Rencana Pengembangan Selanjutnya (Sprint 3)

### Hybrid Search & Reranking
Meskipun pencarian semantik (dense) sudah presisi menggunakan Context Enrichment, untuk mendukung skala produksi kita akan mengintegrasikan:
1. **Hybrid Search**: Kombinasi pencarian vektor (Dense) dengan pencarian kata kunci eksak (Sparse / BM25).
2. **Reranker (Cross-Encoder)**: Model reranking untuk menghitung ulang relevansi pasangan query-chunk guna menekan angka halusinasi LLM secara optimal.

---

## Cara Menjalankan & Menguji API

### 1. Jalankan Uvicorn Server
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Melakukan Ingest & Indexing Dokumen
Kirim permintaan `POST` ke `/ingest` menggunakan curl atau visual via Swagger UI (`http://127.0.0.1:8000/docs`):
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/ingest?index=true' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@data/temp/dummy.pdf;type=application/pdf'
```

### 3. Melakukan Pencarian Semantik
Kirim permintaan `GET` ke `/search`:
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/search?query=kandungan%20ERHA%20Acne%20Clear%20Gel&top_k=3' \
  -H 'accept: application/json'
```
