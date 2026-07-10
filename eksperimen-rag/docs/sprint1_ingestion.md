# Sprint 1: Data Ingestion (Docling -> JSON)

## Overview
Fokus dari Sprint 1 ini adalah membangun pondasi Ingestion Pipeline yang kokoh dan **AI-ready** untuk RAG skala produksi. Dibandingkan dengan naive chunking tradisional, pipeline ini memahami struktur dokumen (tabel, paragraf, hierarki judul) secara utuh dan memperkaya data dengan metadata yang sangat melimpah untuk mendukung retrieval, filtering, citation, serta monitoring.

Hasil parsing dan chunking di-ekspor ke file `JSON` terlebih dahulu untuk mempermudah Quality Assurance (QA) atau Data Engineering dalam memvalidasi integritas data sebelum masuk ke tahap embedding dan penyimpanan di Vector DB (Qdrant).

---

## Arsitektur Pipeline & Komponen

### 1. Loader & Parser (`ingestion/parser.py`)
Menggunakan `DocumentConverter` dari **Docling** (oleh IBM). Parser ini memanfaatkan model AI vision dan tata letak terpadu untuk mengekstrak struktur halaman dari PDF, DOCX, PPTX, HTML, dan Markdown. Ini menjamin pemisahan tabel dan data semi-terstruktur berjalan secara konsisten tanpa merusak relasi datanya.

### 2. Section Chunker (`ingestion/chunker.py`)
Menerapkan kombinasi chunking bertingkat:
- **Hierarchical Chunker**: Membagi dokumen berdasarkan struktur pohon dokumen asli (Heading H1-H6, Paragraf, Tabel) sehingga batas potongannya logis.
- **Semantic Chunker**: Jika satu bagian bab dokumen (misal, penjelasan di bawah section "Ingredients") terlalu panjang (melebihi batas toleransi `max_length_for_semantic`), chunk tersebut akan dipotong kembali secara semantik menggunakan cosine similarity antar-kalimat (memanfaatkan embedding model `BAAI/bge-m3`).
- **Section Fallback (Rule-Based)**: Pada dokumen DOCX/PDF yang tidak diformat menggunakan heading style bawaan (namun hanya teks biasa yang ditebalkan), chunker menggunakan daftar `KNOWN_SECTIONS` (contoh: `ACTIVE INGREDIENTS`, `DESCRIPTION`, `STORAGE`, dll.) untuk melacak pergeseran bab secara dinamis dan menetapkan section yang tepat.

### 3. Metadata Enricher (`ingestion/metadata.py`)
Setiap chunk diperkaya secara otomatis dengan skema metadata produksi berikut:
- `source_file`: Nama file sumber dokumen.
- `document_type`: Tipe dokumen (misal: `brochure`, `sop`, `faq`, `guideline`) yang disimpulkan lewat nama file atau judul bab.
- `section`: Nama bab/bagian aktif saat teks berada (sangat krusial untuk LLM citation).
- `page`: Nomor halaman asli dari dokumen (1-based, untuk sitasi akurat).
- `chunk_index`: Indeks urutan chunk dalam satu dokumen (1-based).
- `language`: Deteksi bahasa otomatis menggunakan library `langdetect` (misal: `en`, `id`).
- `token_count`: Estimasi jumlah token teks chunk secara deterministik.
- `processed_at`: Waktu pemrosesan dalam format ISO UTC timestamp standar (`YYYY-MM-DDTHH:MM:SSZ`).

### 4. Orkestrator Pipeline (`ingestion/pipeline.py`)
Menghubungkan parser, chunker, dan enricher dalam satu alur kerja, lalu menulis hasilnya ke file output `data/output/<filename>_parsed.json`.

---

## Contoh Struktur Output JSON (`KNOWLEDGE_CHUNK`)

Berikut adalah representasi chunk hasil ekspor yang sudah siap digunakan untuk production:
```json
[
    {
        "text": "ERHA Acne Clear Gel is formulated to help reduce inflammatory acne and excess oil while maintaining the skin barrier.",
        "metadata": {
            "source_file": "dumy-ERHA-Acne-Clear-Gel.docx",
            "document_type": "document",
            "section": "DESCRIPTION",
            "page": 1,
            "chunk_index": 4,
            "language": "en",
            "token_count": 24,
            "processed_at": "2026-07-08T17:08:14Z"
        }
    }
]
```

---

## Cara Menjalankan & Validasi

### 1. Install Dependencies
Pastikan virtual environment aktif, kemudian install semua paket yang dibutuhkan:
```bash
pip install -r requirements.txt
```
*(Catatan: Pertama kali dijalankan, sistem akan mengunduh model tata letak Docling serta bobot model embedding `BAAI/bge-m3` ke dalam local cache).*

### 2. Jalankan Pipeline
Gunakan CLI bawaan untuk menguji satu file:
```bash
python -m ingestion.pipeline data/dumy-ERHA-Acne-Clear-Gel.docx
```
Atau jalankan server FastAPI:
```bash
python -m uvicorn app.main:app --host localhost --port 8000 --reload
```
Akses Swagger UI di `http://localhost:8000/docs` untuk melakukan upload dan pengetesan API endpoint `/ingest` secara visual.

### 3. Validasi Output
Periksa output file di direktori `data/output/`. Pastikan seluruh data JSON memiliki atribut metadata lengkap, nomor halaman (*page*) yang sesuai, serta bab (*section*) yang terisi dengan benar.
