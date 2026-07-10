# Sprint 4: Generation Layer & Chat RAG

Sprint 4 menandai penyelesaian dari **Generation Layer** pada arsitektur RAG **CHAT AI ERHA**. Tahap ini menghubungkan layer retrieval pencarian hibrida dari Sprint 3 dengan model bahasa besar (LLM) untuk menghasilkan jawaban yang ramah, medis estetika, terstruktur, dan memiliki rujukan sitasi presisi.

---

## 1. Fitur Utama yang Diimplementasikan

### A. Integrasi LLM Adapter Terstruktur
* Mengaktifkan implementasi riil dari `GeminiAdapter` & `OpenAIAdapter` menggunakan pembungkus LangChain (`ChatGoogleGenerativeAI` & `ChatOpenAI`).
* Default model diatur menggunakan model generasi mutakhir yang didukung secara penuh: `gemini-2.5-flash` untuk Gemini dan `gpt-4o-mini` untuk OpenAI.
* Penanganan deteksi API key yang aman dengan validasi terstruktur saat inisialisasi aplikasi startup.

### B. Prompt Estetika Medis (Prompt Engineering)
* **Persona Ahli**: Memposisikan model sebagai asisten kecantikan medis estetika ERHA yang profesional, ramah, dan empatik.
* **Grounding Ketat**: Menginstruksikan model untuk hanya menjawab menggunakan fakta yang ada pada Context. Dilarang keras melakukan halusinasi kandungan aktif, harga, atau tata cara pemakaian yang tidak tertera pada dokumen.
* **Sitasi Bernomor Otomatis**: Hasil jawaban secara otomatis melampirkan angka rujukan seperti `[1]`, `[2]` di akhir kalimat rujukan, dipetakan secara akurat ke metadata sumber file asli.

### C. Mekanisme RAG Bypass Hemat Biaya (Cost-Efficient Bypass)
* Jika kueri berada di luar domain atau tidak lolos ambang batas keyakinan (Confidence Check), sistem akan melewati panggilan API LLM sepenuhnya dan mengembalikan respons fallback `"Maaf, saya tidak menemukan informasi."`. Langkah ini menghemat biaya tagihan API token hingga 100% pada pertanyaan tidak relevan dan memotong latensi respons.

### D. Manajemen Riwayat Percakapan (Multi-turn Chat)
* Endpoint `/chat` menerima riwayat pesan percakapan sebelumnya (`history`) untuk merangkai memori kontekstual sehingga pengguna dapat melakukan tanya-jawab secara mengalir (berkelanjutan).

---

## 2. API Endpoint Baru: `POST /chat`

Endpoint ini menangani interaksi chat interaktif dengan RAG terintegrasi.

* **URL**: `http://127.0.0.1:8000/chat`
* **Metode**: `POST`
* **Request Payload**:
```json
{
  "query": "Apa saja manfaat klinis ERHA Acne Clear Gel?",
  "top_k": 3,
  "rerank": true,
  "document_type": "product",
  "confidence_threshold": 0.1,
  "history": []
}
```

* **Response Payload**:
```json
{
  "query": "Apa saja manfaat klinis ERHA Acne Clear Gel?",
  "answer": "Tentu, berikut adalah manfaat klinis dari ERHA Acne Clear Gel:\n\n*   Mengurangi lesi jerawat inflamasi [1]\n*   Mengontrol produksi sebum berlebih [1]\n*   Meminimalkan pori-pori tersumbat [1]\n*   Memperbaiki tekstur kulit [1]\n*   Mengurangi kemerahan pasca-inflamasi [1]\n*   Mendukung perawatan jerawat jangka panjang [1]\n\nPerbaikan yang terlihat umumnya muncul setelah empat hingga delapan minggu penggunaan yang konsisten [1].",
  "context": "[1] Source: ERHA Acne Clear Gel.docx | Product: ERHA Acne Clear Gel | Section: BENEFITS | Page: 1\nContent:\nClinical use of  ERHA Acne Clear Gel may provide the following benefits:\n- Reduce inflammatory acne lesions\n- Control excessive sebum production\n- Minimize clogged pores\n- Improve skin texture\n- Reduce post-inflammatory redness\n- Support long-term acne maintenance\nVisible improvement generally appears after four to eight weeks of consistent use...",
  "results": [
    {
      "text": "Clinical use of  ERHA Acne Clear Gel may provide the following benefits...",
      "metadata": {
        "source_file": "ERHA Acne Clear Gel.docx",
        "product_name": "ERHA Acne Clear Gel",
        "document_type": "product",
        "section": "BENEFITS",
        "page": 1
      }
    }
  ]
}
```

---

## 3. Hasil Pengujian Unit Test

Pengujian unit test baru di `test/test_sprint4_generation.py` memverifikasi empat skenario kunci:
1. **`test_prompt_builder_without_history`**: Memastikan prompt kompilasi tersusun benar tanpa chat history.
2. **`test_prompt_builder_with_history`**: Memastikan prompt mengintegrasikan riwayat percakapan secara terurut dengan label `User` dan `Assistant`.
3. **`test_generate_answer_success`**: Memastikan generasi berjalan sukses saat retrieve mengembalikan data, dan LLM Adapter terpanggil sekali.
4. **`test_generate_answer_bypass_fallback`**: Memverifikasi fitur RAG bypass di mana LLM tidak dipanggil sama sekali saat context kosong atau terfilter, langsung mengembalikan pesan fallback secara aman.

Semua pengujian lolos dengan status **`OK`**.
