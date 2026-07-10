# Panduan Pengelolaan & Penyiapan Dokumen untuk RAG (Arya Noble KB)

Dokumen ini berisi panduan, tips, dan best practices dalam menyiapkan berkas-berkas internal PT Arya Noble (seperti brosur produk, SOP klinis, panduan treatment, FAQ, dan promo) sebelum di-ingest ke dalam sistem RAG. 

Kualitas data masukan sangat menentukan akurasi jawaban RAG (*Garbage In, Garbage Out*). Dengan mengikuti panduan ini, akurasi pemotongan data (chunking) dan pencarian semantik (retrieval) akan meningkat secara signifikan.

---

## 1. Aturan Penamaan Berkas (Naming Conventions)

Sistem RAG menggunakan nama berkas sebagai sumber konteks produk (Product Name) yang akan disisipkan ke dalam embedding vektor chunk. 

* **Rekomendasi Utama**: Gunakan nama produk/topik yang spesifik dan jelas sebagai nama file. Gunakan pemisah strip (`-`) atau garis bawah (`_`).
* **Format Bagus (Recommended)**:
  * `ERHA-Acne-Clear-Gel-Brosur.pdf` (Akan dibaca sistem sebagai: *Product: ERHA Acne Clear Gel Brosur*)
  * `SOP-Clinical-Acne-Peeling-Treatment.docx` (Akan dibaca sistem sebagai: *Product: SOP Clinical Acne Peeling Treatment*)
  * `FAQ-Promo-ERHA-Ultimate-Acne-Cure.pdf`
* **Format Buruk (Avoid)**:
  * `Brosur_Produk_Fix.pdf` (Tidak spesifik produk apa)
  * `Scan_09_07_2026.pdf` (Kehilangan semua konteks)
  * `Doc1.docx`

---

## 2. Struktur Judul dan Heading (Document Hierarchy)

Sistem chunking bertingkat (*Hierarchical Chunker*) membagi dokumen berdasarkan pohon struktur heading.

* **Gunakan Heading Style Standar**: Pada Microsoft Word atau Google Docs, pastikan untuk memformat judul bab menggunakan style **Heading 1, Heading 2, atau Heading 3**, bukan hanya teks biasa yang dipertebal (bold) secara manual.
* **Gunakan Nama Section yang Konsisten**: Sistem chunking menggunakan daftar section bawaan untuk melacak bab secara otomatis. Gunakan nama section yang umum dan konsisten di seluruh dokumen produk:
  * Bahan Aktif: `ACTIVE INGREDIENTS` atau `INGREDIENTS`
  * Deskripsi: `DESCRIPTION` atau `PRODUCT OVERVIEW`
  * Cara Pakai: `HOW TO USE` atau `DIRECTIONS FOR USE`
  * Indikasi: `INDICATIONS`
  * Kontraindikasi: `CONTRAINDICATIONS`
  * Efek Samping/Peringatan: `WARNINGS` atau `PRECAUTIONS`
  * Penyimpanan: `STORAGE`

---

## 3. Penulisan Daftar dan Poin (Lists & Bullet Points)

Sistem chunking sekarang menggabungkan daftar poin berturut-turut di bawah section yang sama menjadi satu chunk tunggal agar LLM mendapatkan konteks yang utuh.

* **Format Poin yang Rapi**: Gunakan bullet points standar (simbol bulat, strip, atau angka) segera setelah judul section.
* **Hindari Teks Sisipan**: Jangan menyisipkan teks narasi panjang di tengah-tengah daftar bahan aktif/poin jika tidak berhubungan langsung, karena dapat memicu pemotongan chunk baru secara paksa.
* **Contoh Format Daftar Terbaik**:
  ```markdown
  ### ACTIVE INGREDIENTS
  * Salicylic Acid 2%
  * Niacinamide 5%
  * Zinc PCA
  * Green Tea Extract
  ```

---

## 4. Format Tabel yang AI-Ready

Sistem parser Docling mampu mengekstrak tabel secara utuh (tidak rusak menjadi teks acak). Namun, desain tabel harus ramah AI:

* **Header Jelas**: Selalu definisikan baris pertama sebagai Header kolom yang jelas.
* **Hindari Sel Gabungan (Merged Cells)**: Minimalkan penggunaan *Merged Cells* (gabungan baris atau kolom) serta tabel bersarang (*Nested Tables*) karena dapat membuat pemetaan kolom di database vektor menjadi kurang presisi.
* **Satu Sel Satu Informasi**: Isi sel tabel secara ringkas. Jika berisi paragraf penjelasan yang sangat panjang, lebih baik tuliskan dalam bentuk paragraf biasa di bawah heading daripada dimasukkan ke dalam sel tabel.

---

## 5. Dokumen PDF Native vs Dokumen Hasil Scan (OCR)

* **Utamakan PDF Native / DOCX**: Selalu prioritaskan dokumen yang diekspor langsung dari Word/aplikasi desain (PDF Text/Native) dibandingkan dokumen hasil scan printer atau foto kamera (PDF Scanned).
* **Kelebihan PDF Native**:
  * Proses parsing jauh lebih cepat (tidak membutuhkan resource CPU/GPU untuk OCR).
  * Karakter dan angka 100% akurat (tidak ada typo akibat kesalahan pembacaan gambar oleh mesin OCR).
  * Struktur tabel terekstrak secara sempurna.
* **Jika Terpaksa Menggunakan Scan (OCR)**: Pastikan resolusi dokumen tinggi (minimal 300 DPI), posisi dokumen tegak (tidak miring/rotasi), dan teks tidak tertutup coretan/stempel tinta basah.

---

## 6. Tips Tambahan untuk Data Admin

Sebelum mengunggah file ke `/ingest`:
1. **Lakukan Pembersihan Metadata Lama**: Hapus komentar, revisi (*track changes*), atau catatan kaki editor yang masih tertinggal di dokumen Word agar tidak ikut ter-index.
2. **Uji Coba File Kecil Terlebih Dahulu**: Unggah satu berkas sampel produk ke endpoint `/ingest` dengan parameter `index=false` terlebih dahulu untuk melihat hasil parsing JSON-nya di folder `data/output/`. Jika struktur JSON sudah rapi dan daftar poinnya tergabung dengan benar, baru lakukan ingest dengan `index=true`.
