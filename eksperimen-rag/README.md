# CHAT AI ERHA - RAG (Retrieval-Augmented Generation) System

Sistem **CHAT AI ERHA** adalah asisten kecerdasan buatan berbasis *Retrieval-Augmented Generation* (RAG) medis estetika untuk PT Arya Noble (ERHA). Chatbot ini dirancang untuk membantu dokter spesialis kulit dan kecantikan mencari rekomendasi klinis, informasi produk, jenis perawatan (*treatment*), promo, serta Standar Operasional Prosedur (SOP) secara instan, akurat, dan aman.

---

## 🚀 Fitur & Kapabilitas Saat Ini (Current Capabilities)

Aplikasi eksperimen RAG saat ini memiliki arsitektur modular yang terbagi menjadi beberapa komponen utama:

### 1. Ingestion Pipeline & Metadata Enrichment
Menerima file mentah dan memprosesnya secara aman:
* **Docling Parser**: Mengekstrak struktur dokumen mentah. Menggunakan teknik *in-memory file-stream reading* untuk menghindari *Windows file locking error* (`WinError 32`).
* **Hierarchical Semantic Chunker**: Memotong teks berdasarkan bab/section dan hirarki halaman.
* **List-Merging Logic**: Menggabungkan butir-butir daftar (*bullet points*) berurutan ke dalam satu chunk (maksimal 500 karakter) untuk menjaga keutuhan konteks medis.
* **Auto Metadata Enrichment**: Mengekstrak otomatis nama produk, kategori dokumen (`product`, `treatment`, `faq`, `promotion`, `sop`), bab/section, nomor halaman, bahasa, dan jumlah token.

### 2. Advanced Hybrid Retrieval Layer
Menggabungkan dua metode pencarian untuk mengoptimalkan presisi dan ingatan (*recall*):
* **Dense Vector Search**: Menggunakan Qdrant (lokal persistent) dengan model embedding `BAAI/bge-m3` yang mendukung multi-bahasa dan metrik jarak *Cosine Similarity*.
* **Sparse Lexical Search**: Mesin pencari kata kunci lokal berbasis `rank-bm25` (BM25Okapi). Modul ini mendukung penyaringan sub-korpus dinamis untuk membatasi ruang pencarian.
* **Reciprocal Rank Fusion (RRF)**: Menggabungkan hasil Dense & Sparse secara adil sebelum diurutkan ulang.
* **Multi-Intent Query Splitting**: Mendeteksi konjungsi kata hubung majemuk seperti *dan*, *and*, *serta* untuk memecah kueri kompleks menjadi beberapa sub-kueri.
* **Sub-Query Interleaving**: Melakukan pencarian sub-kueri secara independen dan merajut hasilnya secara bergantian guna menghindari dominasi satu intent (*intent dilution*).
* **Text Deduplication & Metadata Filtering**: Menghilangkan chunk duplikat untuk menghemat kuota jendela konteks LLM dan menyaring pencarian secara presisi berdasarkan tipe dokumen dan nama section.

### 3. Reranking & Intent Boosting
* **Cross-Encoder Reranker**: Menggunakan model lintas bahasa `BAAI/bge-reranker-base` untuk menilai relevansi semantik antara kueri dan chunk kandidat secara berpasangan.
* **Context Prompt Enrichment**: Sebelum dimasukkan ke Cross-Encoder, teks chunk diperkaya secara dinamis dengan format: `"Product: {product} | Section: {section} | Content: {content}"`.
* **Heuristic Intent Boosting**: Menyuntikkan dorongan skor relevansi (+0.05) secara dinamis apabila metadata section dari chunk cocok dengan maksud kueri pengguna (contoh: kueri tentang "cara pakai" cocok dengan section "HOW TO USE").

### 4. Generation Pipeline & Guardrails (FastAPI Endpoint)
* **Medical Guardrails**: System Prompt yang dirancang ketat agar chatbot memosisikan diri sebagai asisten medis yang profesional, ramah, dan patuh terhadap batasan klinis. Model dilarang keras berasumsi atau berhalusinasi di luar konteks yang disediakan.
* **Cost-Efficient RAG Bypass**: Mengukur skor Cross-Encoder teratas terhadap nilai ambang batas keyakinan (`rerank_confidence_threshold` default `0.1`). Jika di bawah threshold atau context kosong, sistem langsung mengembalikan respons fallback *"Maaf, saya tidak menemukan informasi."* tanpa memanggil API LLM (menghemat biaya token 100% dan mengurangi latensi).
* **Multi-turn Chat Memory**: Menyertakan riwayat percakapan sebelumnya (*chat history*) untuk mendukung interaksi yang mengalir.
* **Automatic Citation**: Melampirkan nomor rujukan sitasi secara otomatis seperti `[1]`, `[2]` di akhir kalimat jawaban yang merujuk pada dokumen sumber.

### 5. Automated Evaluation Layer
* Menyediakan endpoint evaluasi pencarian untuk menghitung metrik performa retrieval secara otomatis:
  * **Hit Rate @ K**
  * **Mean Reciprocal Rank (MRR) @ K**

---

## 📅 Rencana Pengembangan Selanjutnya (Future Roadmap)

Untuk menyesuaikan dengan kebutuhan skala produksi industri dan kesepakatan arsitektur, pengembangan berikutnya akan difokuskan pada tiga pilar AI Engineering berikut:

### 1. Migrasi ke PostgreSQL & pgvector (HNSW Index)
Untuk menggantikan Qdrant, database akan dimigrasikan ke PostgreSQL dengan ekstensi `pgvector`:
* **Penyimpanan Hibrida Terpadu**: Menyimpan data relasional pengguna/dokter, riwayat chat, metadata dokumen, dan vektor embedding dalam satu database PostgreSQL tunggal.
* **HNSW (Hierarchical Navigable Small World) Index**: Mengimplementasikan indeks pencarian ANN (Approximate Nearest Neighbor) berbasis HNSW pada kolom vektor untuk pencarian berkecepatan tinggi dengan penggunaan memori yang efisien:
  ```sql
  CREATE INDEX ON items USING hnsw (embedding_column vector_cosine_ops) WITH (m = 16, ef_construction = 64);
  ```
* **Optimasi Query & Filtering**: Memanfaatkan SQL query gabungan untuk metadata filtering secara native menggunakan indexing PostgreSQL standar (B-Tree) pada kolom kategori dan nama produk bersamaan dengan pencarian vektor.

### 2. Standardisasi Model OpenAI (Embedding & Generasi)
Migrasi total model AI ke ekosistem OpenAI untuk keseragaman kualitas dan performa:
* **OpenAI Text Embeddings**: Menggunakan model `text-embedding-3-large` atau `text-embedding-3-small` melalui API resmi OpenAI untuk menggantikan model lokal Hugging Face `bge-m3`, sehingga mengurangi konsumsi beban memori RAM/GPU server lokal.
* **OpenAI Chat Completion**: Menstandarkan generator menggunakan model `gpt-4o` (untuk analisis klinis kompleks) dan `gpt-4o-mini` (untuk percakapan cepat/FAQ biasa) menggunakan *tunable capability selector*.
* **Azure OpenAI Enterprise Ready**: Mendukung opsi deployment menggunakan Azure OpenAI API demi privasi dan keamanan data rekam medis pasien sesuai regulasi HIPAA/GDPR (data tidak digunakan untuk pelatihan model publik).

### 3. Deployment Menggunakan Docker & Docker Compose
Menyediakan konfigurasi containerization untuk portabilitas deployment di server PT Arya Noble:
* **Dockerfile Multi-stage**: Menyusun container image minimalis berbasis Python untuk backend FastAPI, mengoptimalkan layer cache untuk dependensi library seperti PyTorch/sentence-transformers (jika masih menggunakan reranker lokal).
* **Docker Compose**: Mengorkestrasikan seluruh servis pendukung:
  * Container Backend FastAPI
  * Container PostgreSQL (dengan pgvector pre-installed)
  * Volume persistent untuk database storage

---

## 🚀 Cara Menjalankan Aplikasi & Pengujian

### 1. Prasyarat (Prerequisites)
Pastikan Python 3.10+ telah terinstal pada sistem Anda.

### 2. Instalasi Dependensi
Buat virtual environment dan instal library yang dibutuhkan:
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Konfigurasi Environment
Buat berkas `.env` di direktori utama proyek berdasarkan variabel berikut:
```env
LLM_PROVIDER=openai       # Atur ke 'openai' atau 'gemini'
OPENAI_API_KEY=sk-...     # Isi dengan OpenAI API Key aktif Anda
GEMINI_API_KEY=AQ...      # Isi jika menggunakan Gemini provider
QDRANT_URL=./qdrant_data
QDRANT_COLLECTION_NAME=arya_noble_kb
CHUNK_SIZE=500
CHUNK_OVERLAP=50
```

### 4. Menjalankan Server Backend FastAPI
Jalankan aplikasi dengan uvicorn:
```powershell
python -m app.main
```
Aplikasi akan aktif di `http://127.0.0.1:8000`. Anda dapat mengakses dokumentasi API interaktif Swagger UI di `http://127.0.0.1:8000/docs`.

### 5. Menjalankan Pengujian Unit (Unit Testing)
Verifikasi fungsionalitas sistem dengan menjalankan suite pengujian yang tersedia:
```powershell
# Uji seluruh modul RAG secara otomatis
python -m unittest discover -s test

# Atau uji modul tertentu secara spesifik
python -m unittest test.test_sprint4_generation
```
