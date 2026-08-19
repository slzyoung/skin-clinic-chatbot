"""Unified Chatbot Pipeline for ERHA (PT Arya Noble).

Single Entry Point and Single Source of Truth:
- Input Guardrails Validation (Prompt Injection & Topicality)
- Intent Detection & Dynamic Complexity Router (Simple 1-turn vs Complex Agent Orchestration)
- Evidence Collection & Deduplication
- Clinical Safety Gate & Evidence Validation
- Single Unified Prompt Compilation & Single LLM Response Generation
- Output Guardrails (PII Redaction & Patient Disclaimer Stripping)
- Standardized Visual Backend Logger (log_rag_chat)
"""

import os
import re
import json
import time as _time
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

from app.rag.services.interfaces import BaseLLMAdapter
from app.rag.services.rag_retriever import HybridRetriever
from app.rag.services.intent import QueryIntentDetector, QueryIntent, get_current_time_period, get_time_greeting_response
from app.rag.services.guardrails import GuardrailsPipeline
from app.rag.config import settings


# --- LLM Adapter Implementations ---

class OpenAIAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str, model_name: Optional[str] = None, base_url: Optional[str] = None):
        if not api_key:
            raise ValueError("API key is not configured in settings, database, or environment.")
        from langchain_openai import ChatOpenAI
        target_model = model_name or settings.openai_model_name
        logger.info(f"Initializing OpenAI-compatible LLM Adapter: model='{target_model}', base_url='{base_url or 'default'}'")
        
        kwargs = {
            "model": target_model,
            "api_key": api_key,
            "temperature": 0.0  # Grounded & factual response (0.0 temperature)
        }
        if base_url:
            kwargs["base_url"] = base_url
            
        self.llm = ChatOpenAI(**kwargs)

    def generate(self, prompt: str) -> str:
        max_retries = 3
        backoff_delay = 5.0
        
        for attempt in range(1, max_retries + 1):
            try:
                response = self.llm.invoke(prompt)
                return response.content
            except Exception as e:
                err_msg = str(e)
                if ("429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "Quota exceeded" in err_msg or "rate-limit" in err_msg.lower()) and attempt < max_retries:
                    logger.warning(f"LLM 429 Rate limit hit (attempt {attempt}/{max_retries}). Retrying in {backoff_delay}s... Error: {err_msg}")
                    _time.sleep(backoff_delay)
                    backoff_delay *= 2.0
                else:
                    logger.error(f"LLM generation failed on attempt {attempt}/{max_retries}: {e}")
                    raise e

    async def generate_stream(self, prompt: str):
        import asyncio
        max_retries = 3
        backoff_delay = 5.0
        
        for attempt in range(1, max_retries + 1):
            try:
                async for chunk in self.llm.astream(prompt):
                    yield chunk.content
                return
            except Exception as e:
                err_msg = str(e)
                if ("429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "Quota exceeded" in err_msg or "rate-limit" in err_msg.lower()) and attempt < max_retries:
                    logger.warning(f"LLM Stream 429 Rate limit hit (attempt {attempt}/{max_retries}). Retrying in {backoff_delay}s... Error: {err_msg}")
                    await asyncio.sleep(backoff_delay)
                    backoff_delay *= 2.0
                else:
                    logger.error(f"LLM stream generation failed on attempt {attempt}/{max_retries}: {e}")
                    raise e


# --- Grounded System Prompt Configuration ---

SYSTEM_PROMPT = """<role>
You are ERHA Medical Assistant, a professional, intelligent, and helpful Clinical AI Assistant for ERHA Doctors and Clinicians (PT Arya Noble).
Your mission is to provide accurate, grounded, natural, and helpful clinical guidance on ERHA treatments, protocols, and skincare products in fluent medical Indonesian.
You converse as a knowledgeable peer to doctors — concise, warm, practical, and on-point.
</role>

<language_and_tone_rules>
- Use professional, respectful, and peer-to-peer clinical Indonesian (medical assistant to doctor).
- Address the user as 'Dokter' or 'Dok'.
- Include greeting (e.g., 'Halo Dok!') ONLY if the Doctor explicitly greets in the initial turn or if history is empty. Do NOT repeat greetings in ongoing conversations.
- Match English if the Doctor asks in English.
</language_and_tone_rules>

<negative_constraints>
- STRICTLY BAN SYSTEM, DATABASE & DOCUMENT JARGON (DILARANG JARGON KAKU):
  * DILARANG KERAS menggunakan kata/singkatan kaku seperti:
    - ❌ "KB" / "Berdasarkan KB" / "Knowledge Base" / "basis data"
    - ❌ "SOP" / "di SOP" / "dalam SOP" / "dokumen SOP" / "menurut SOP"
    - ❌ "tercantum" / "tidak tercantum" / "pada konteks yang tersedia" / "evidence"
  * Jawab langsung secara alami, cerdas, dan to-the-point (contoh: "Untuk kondisi kulit berminyak dan berjerawat, rekomendasi produk yang sesuai adalah...", BUKAN "Berdasarkan KB, produk yang tercantum...").
- NO PATIENT-FACING DISCLAIMER: The user is a Doctor. DO NOT add disclaimers like "Konsultasikan dengan dokter...".
- NO PLEASANTRY CLOSINGS: DO NOT attach fluff closings ("Semoga membantu Dok", "Jika ada pertanyaan..."). End response directly after the main factual response.
- CONTEXT RELEVANCE: Use only context relevant to the query.
</negative_constraints>

<three_level_grounding_policy>
LEVEL 1 — STRICT ERHA GROUNDING:
Apply Strict Grounding for any queries involving:
- ERHA product names, ingredients, concentrations, usage steps, treatment protocols, aftercare, contraindications, product compatibility, recommendations, guidelines, or ERHA clinical claims.
- Rules:
  - Synthesize facts helpfully without reciting raw internal document labels.
  - If partial information is present: Answer using available evidence, and naturally note if specific details (e.g. percentage or dosage) are omitted.
  - NEVER manufacture false product facts, numbers, percentages, dosages, wavelengths, or compatibility rules.

LEVEL 2 — GENERAL CLINICAL KNOWLEDGE:
Apply General Knowledge when the query asks about generic medical/dermatological concepts without requiring proprietary ERHA facts.
Examples: "Apa perbedaan papule dan pustule?", "Apa fungsi skin barrier?", "Apa itu PIH?"
- Rules:
  - You MAY answer using sound medical general knowledge.
  - Do NOT claim that generic medical definitions come from internal documents.

LEVEL 3 — MIXED QUERIES:
Combine proprietary ERHA product/treatment evidence with sound clinical dermatological knowledge to provide comprehensive, actionable answers for the Doctor.
</three_level_grounding_policy>

<evidence_priority_and_conflicts>
When retrieved evidence is available, prioritize sources in order:
1. ERHA Authoritative Source / Official Guideline
2. ERHA Product Documentation
3. ERHA Treatment Documentation
4. Other Approved Reference Sources
5. General Clinical Knowledge (for non-ERHA generic concepts)
</evidence_priority_and_conflicts>

<anti_hallucination_and_clinical_precision>
- DO NOT fabricate numbers, percentages, dosages, concentrations, wavelengths, durations, frequencies, treatment results, contraindications, or compatibility rules.
- Preserve exact product names, active ingredients, percentages, dosages, frequencies, and warnings as stated in the evidence.
- Synthesize available facts helpfully and intelligently.
</anti_hallucination_and_clinical_precision>

<llm_reasoning_and_synthesis>
- You MUST perform synthesis, comparison, structural formatting, and natural language reasoning over retrieved evidence rather than verbatim chunk copy-pasting.
- Connect related pieces of retrieved evidence (e.g. combining treatment protocols with product aftercare) into coherent clinical advice.
</llm_reasoning_and_synthesis>

<multimodal_image_display_rules>
- Display an image in Markdown format ONLY IF an actual valid HTTP/HTTPS image URL (e.g. https://.../image.jpg) is explicitly present in the retrieved context.
- DILARANG KERAS mencetak string literal "image_url", "(url)", atau placeholder palsu.
- RESPONSE FOR IMAGE REQUESTS / PERMINTAAN GAMBAR PRODUK:
  Jika Dokter menanyakan atau meminta melihat foto/gambar produk:
  * Jika gambar asli tidak ada di dokumen, jawab secara ramah dan profesional:
    "Mohon maaf Dok, untuk saat ini foto atau visual resmi produk belum tersedia di sistem panduan ini. Apakah ada produk tertentu yang ingin Dokter ketahui detailnya?"
  * DILARANG KERAS menggunakan istilah teknis developer seperti "tidak ada URL gambar valid", "evidence KB", "tidak ada di evidence", atau "konteks yang tersedia".
</multimodal_image_display_rules>

<recommendation_query_rules>
- When the user asks for BOTH treatments and products (e.g. 'rekomendasi treatment + produk'), you MUST provide explicit recommendations for BOTH categories (Treatment & Produk Skincare) based on available evidence.
- Separate recommendations clearly:
  1. Active Acne: Treatment & Produk
  2. Post-Acne: Treatment & Produk
</recommendation_query_rules>

<response_formatting_rules>
- HIGHLY STRUCTURED & SCANNABLE CLINICAL MARKDOWN (DILARANG WALL OF TEXT):
  * DILARANG KERAS merangkai daftar banyak produk atau tindakan dalam satu paragraf panjang padat (wall of text).
  * Ketika menyajikan daftar produk, katalog database, rekomendasi multi-fase, atau tindakan klinis:
    WAJIB mengelompokkan secara teratur berdasarkan kategori atau fungsinya menggunakan Markdown headings (### Kategori) dan bullet points (- Nama Item: Deskripsi singkat):
    
    Contoh Struktur yang Rapi:
    ### Pembersih Wajah (Cleanser)
    - Gentle Acne Facial Wash: Pembersih lembut dengan pH seimbang untuk kulit berjerawat dan sensitif.
    - Oil Control Facial Wash: Mengontrol sebum berlebih dan membersihkan pori.

    ### Toner & Eksfoliasi
    - Clarifying Toner: Menyeimbangkan pH dan menyegarkan kulit berminyak.
    - Pore Clear Pad: Eksfoliasi lembut untuk membersihkan komedo dan sumbatan pori.

    ### Serum & Perawatan Bertarget
    - Acneact Anti Acne Serum: Meredakan inflamasi dan menghambat bakteri jerawat.
    - Acne Spot Gel: Perawatan intensif untuk jerawat meradang aktif.

    ### Pelembap & Perlindungan UV
    - Acne Protection Sunscreen: Tabir surya harian non-komedogenik untuk kulit berjerawat.

  * Berikan deskripsi klinis singkat (1 kalimat) di samping nama produk agar Dokter langsung mendapatkan informasi yang komprehensif.
- COMPARISONS: Present as a clean markdown comparison table.
- HOW-TO / DOSAGE: Use numbered steps (1, 2, 3) with frequency and area of application.
</response_formatting_rules>"""


def log_rag_chat(
    query: str,
    intent_val: str,
    top_k: int,
    results: List[Dict[str, Any]],
    context_status: str,
    retrieval_ms: int,
    llm_ms: int,
    guardrails_status: str = "PASSED",
    agent_used: bool = False,
    error_msg: Optional[str] = None
):
    """
    Renders standardized, developer-focused visual backend logs for RAG CHAT execution.
    """
    total_ms = retrieval_ms + llm_ms
    retrieved_count = len(results) if results else 0

    top_score_str = "-"
    if results:
        top_sc = results[0].get("rerank_score", results[0].get("score", 0.0))
        if 0.0 <= top_sc <= 1.0:
            top_score_str = f"{top_sc:.3f}"
        else:
            import math
            prob = 1.0 / (1.0 + math.exp(-top_sc))
            top_score_str = f"{prob:.3f}"

    sources_lines = []
    if results:
        for i, res in enumerate(results[:5], 1):
            meta = res.get("metadata", {})
            src_file = meta.get("source_file") or meta.get("file_name") or "unknown"
            p_name = meta.get("product_name") or meta.get("title") or "-"
            page = meta.get("page") or meta.get("page_number")
            page_str = f"p.{page}" if page else None
            section = meta.get("section") or meta.get("heading") or meta.get("chunk_category")

            parts = [src_file, p_name]
            if page_str:
                parts.append(page_str)
            if section:
                parts.append(str(section))

            sources_lines.append(f"  [{i}] " + " | ".join(parts))
        sources_block = "Sources:\n" + "\n".join(sources_lines)
    else:
        sources_block = "Sources      : (None)"

    error_line = f"\nError        : {error_msg}" if error_msg else ""
    agent_str = " (Agent Tool Orchestration)" if agent_used else " (Direct 1-Turn)"

    logger.info(
        f"\n"
        f"============================================================\n"
        f"🩺 UNIFIED RAG CHAT{agent_str}\n"
        f"------------------------------------------------------------\n"
        f"Query        : \"{query}\"\n"
        f"Intent       : {intent_val}\n"
        f"Top-K        : {top_k}\n"
        f"Retrieved    : {retrieved_count} chunks\n"
        f"Top Score    : {top_score_str}\n\n"
        f"{sources_block}\n\n"
        f"Context      : {context_status}\n"
        f"Retrieval    : {retrieval_ms:,} ms\n"
        f"LLM          : {llm_ms:,} ms\n"
        f"Total        : {total_ms:,} ms\n"
        f"Guardrails   : {guardrails_status}"
        f"{error_line}\n"
        f"============================================================"
    )


# --- Unified Generation Pipeline ---

class GenerationPipeline:
    def __init__(
        self,
        retriever: HybridRetriever,
        llm_adapter: BaseLLMAdapter,
        medical_agent: Optional[Any] = None
    ):
        self.retriever = retriever
        self.llm_adapter = llm_adapter
        self.medical_agent = medical_agent

    @staticmethod
    def contextualize_retrieval_query(query: str, history: List[Dict[str, str]]) -> str:
        """Resolves conversational anaphora and pronoun references in follow-up queries."""
        if not history:
            return query

        clean_q = query.lower().strip()
        
        # 1. Ignore conversational fillers / short acknowledgments from context rewriting
        filler_words = {
            "oke", "ok", "okay", "sip", "siap", "baik", "baiklah", "noted", 
            "makasih", "terima kasih", "terimakasih", "thanks", "thank you", 
            "halo", "hai", "tes", "test", "ping", "paham", "mengerti", "clear",
            "oke dok", "ok dok", "siap dok", "baik dok", "noted dok", "makasih dok"
        }
        if clean_q in filler_words or set(clean_q.split()).issubset(filler_words):
            return query

        anaphora_indicators = [
            r"\bnya\b", r"\bini\b", r"\bitu\b", r"\btersebut\b", r"\bdia\b", 
            r"\bproduk ini\b", r"\btreatment ini\b", r"\btindakan ini\b",
            r"\bcara pakai\b", r"\bcara penggunaan\b", r"\bkandungan\b", 
            r"\bkomposisi\b", r"\bharga\b", r"\befek samping\b", 
            r"\bkontraindikasi\b", r"\bdosis\b", r"\bberapa\b", r"\burutan\b"
        ]

        has_anaphora = any(re.search(ind, clean_q) for ind in anaphora_indicators)
        # Only consider short queries as follow-ups if they aren't fresh questions starting with standard interrogatives
        is_short_incomplete = len(clean_q.split()) <= 4 and not any(
            clean_q.startswith(w) for w in ["apakah", "apa", "bagaimana", "siapa", "dimana", "di mana", "kapan", "mengapa", "kenapa", "tolong", "rekomendasi"]
        )

        is_follow_up = has_anaphora or is_short_incomplete
        if not is_follow_up:
            return query

        last_context = ""
        for msg in reversed(history):
            content = msg.get("content", "")
            if content and not content.startswith("{"):
                cleaned = content.replace("###", "").replace("##", "").replace("**", "").replace("\n", " ")
                words = cleaned.split()
                last_context = " ".join(words[:20]) if len(words) > 20 else " ".join(words)
                break

        if last_context:
            return f"{last_context} {query}"

        return query

    def build_prompt(
        self, 
        query: str, 
        context: str, 
        history: List[Dict[str, str]], 
        intent: QueryIntent, 
        intent_rules: Dict[str, Any]
    ) -> str:
        """Compiles system prompt, retrieved context, intent instructions, history, and query into a grounded prompt."""
        history_str = ""
        if history:
            for msg in history:
                role = "User" if msg.get("role") == "user" else "Assistant"
                content = msg.get("content", "")
                history_str += f"{role}: {content}\n"
        else:
            history_str = "No previous conversation.\n"

        length_instruction = intent_rules.get("length_instruction", "Be concise and factual.")
        period = get_current_time_period()

        import re
        has_greeting_word = bool(re.search(r'\b(halo|hallo|hai|hi|selamat|assalamualaikum|ping)\b', query.lower()))
        
        if not history and (has_greeting_word or intent == QueryIntent.GREETING):
            turn_greeting_rule = f"Pesan pertama atau Dokter menyapa: Balas sapaan dengan ramah ('Halo Dok! Selamat {period}')."
        else:
            turn_greeting_rule = "Percakapan sudah berlangsung (history > 0) atau tidak ada kata sapaan: DILARANG mengulang sapaan pembuka (seperti 'Halo Dok', 'Selamat siang'). Langsung berikan jawaban medis/produk secara singkat, padat, dan objektif."

        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"--- TURN GREETING RULE ---\n"
            f"{turn_greeting_rule}\n\n"
            f"--- CURRENT TIME CONTEXT ---\n"
            f"Current Local Period: {period} (Greeting: 'Selamat {period}')\n\n"
            f"--- DETECTED INTENT ---\n"
            f"Intent Category: {intent.value}\n"
            f"Specific Instruction: {length_instruction}\n\n"
            f"--- CLINICAL & PRODUCT REFERENCE DATA ---\n"
            f"{context}\n\n"
            f"--- CONVERSATION HISTORY ---\n"
            f"{history_str}\n"
            f"User: {query}\n"
            f"Assistant:"
        )
        return prompt

    @staticmethod
    def validate_clinical_safety_gate(
        query: str,
        answer: str,
        context_status: str,
        results: List[Dict[str, Any]],
        intent: QueryIntent
    ) -> Tuple[bool, str]:
        """
        Clinical Safety Gate: Single Evidence Validation before final answer delivery.
        1. Safety-critical queries (pregnancy, lactation, contraindications, allergies, interactions):
           - If context_status is REJECTED (empty evidence), blocks speculation and returns a safe rejection.
           - If context lacks explicit safety text, appends a clinical safety note.
        2. Strips literal image_url placeholders (e.g. ![Product](image_url)) if no HTTP URL is present.
        """
        import re
        sanitized = answer.strip()
        q_lower = query.lower()

        safety_critical_keywords = [
            "ibu hamil", "bumil", "kehamilan", "pregnancy", "pregnant",
            "menyusui", "lactation", "breastfeeding",
            "kontraindikasi", "contraindication",
            "alergi", "allergy", "interaksi", "interaction"
        ]

        is_safety_critical = any(kw in q_lower for kw in safety_critical_keywords)

        if is_safety_critical:
            if context_status == "REJECTED":
                logger.warning(f"⚠️ [CLINICAL SAFETY GATE] Safety-critical query ('{query}') with empty context. Enforcing safe non-speculative rejection.")
                return False, (
                    "Data mengenai keamanan, kontraindikasi, atau interaksi medis untuk kondisi tersebut tidak tersedia dalam basis pengetahuan ERHA. "
                    "Demi keamanan pasien, tidak direkomendasikan penggunaan tanpa rujukan klinis resmi."
                )

            context_texts = " ".join([r.get("text", "").lower() for r in results])
            has_safety_evidence = any(kw in context_texts for kw in ["kontraindikasi", "hamil", "menyusui", "alergi", "efek samping", "perhatian", "peringatan"])

            if not has_safety_evidence and "tidak disarankan" not in sanitized.lower() and "kontraindikasi" not in sanitized.lower():
                logger.warning("⚠️ [CLINICAL SAFETY GATE] Safety-critical query lacks explicit safety text in context. Appending clinical safety notice.")
                sanitized += "\n\n*Catatan Keamanan Klinis: Informasi spesifik mengenai kontraindikasi/keamanan kondisi ini tidak tercantum dalam dokumen rujukan. Disarankan untuk menunda tindakan/penggunaan bahan aktif hingga ada petunjuk klinis resmi.*"

        # Strip literal image_url placeholders
        sanitized = re.sub(r'!\[([^\]]*)\]\((image_url|url|\s*)\)', r'\1', sanitized)

        return True, sanitized

    def generate_answer(
        self, 
        query: str, 
        top_k: int = 5, 
        filter_metadata: Optional[Dict[str, Any]] = None,
        rerank: bool = True,
        confidence_threshold: Optional[float] = None,
        history: List[Dict[str, str]] = [],
        force_agent: bool = False
    ) -> Dict[str, Any]:
        """
        Unified Entry Point: Processes query via Input Guardrails, Complexity Routing,
        Evidence Retrieval/Orchestration, Evidence Validation, Safety Gate, Single LLM Synthesis, and Output Guardrails.
        """
        t0_total = _time.time()

        # 0. Input Guardrails Validation
        is_safe, rejection_msg = GuardrailsPipeline.validate_input(query)
        if not is_safe:
            log_rag_chat(
                query=query,
                intent_val="UNKNOWN",
                top_k=top_k,
                results=[],
                context_status="REJECTED",
                retrieval_ms=0,
                llm_ms=0,
                guardrails_status="BLOCKED"
            )
            return {
                "query": query,
                "answer": rejection_msg or "Maaf, permintaan Anda tidak dapat diproses.",
                "context": "Blocked by security guardrails.",
                "results": [],
                "agent_used": False
            }

        # 1. Query Intent Detection & Fast-Path Checking
        intent, intent_rules = QueryIntentDetector.detect(query)

        if intent == QueryIntent.GREETING:
            greeting_ans = get_time_greeting_response(query)
            llm_ms = int((_time.time() - t0_total) * 1000)
            log_rag_chat(
                query=query,
                intent_val=intent.value,
                top_k=top_k,
                results=[],
                context_status="ACCEPTED",
                retrieval_ms=0,
                llm_ms=llm_ms,
                guardrails_status="PASSED"
            )
            return {
                "query": query,
                "answer": greeting_ans,
                "context": "",
                "results": [],
                "agent_used": False
            }

        if intent == QueryIntent.CLOSING:
            closing_ans = "Sama-sama, Dokter! Siap membantu kembali jika ada pertanyaan seputar produk atau protokol ERHA."
            llm_ms = int((_time.time() - t0_total) * 1000)
            log_rag_chat(
                query=query,
                intent_val=intent.value,
                top_k=top_k,
                results=[],
                context_status="ACCEPTED",
                retrieval_ms=0,
                llm_ms=llm_ms,
                guardrails_status="PASSED"
            )
            return {
                "query": query,
                "answer": closing_ans,
                "context": "",
                "results": [],
                "agent_used": False
            }

        effective_top_k = QueryIntentDetector.get_recommended_top_k(query, intent, top_k)

        # 2. Dynamic Complexity Router & Evidence Collection Layer
        t0_retrieval = _time.time()
        is_complex = force_agent or QueryIntentDetector.should_use_agent(query, intent)
        agent_used = False

        if is_complex and self.medical_agent:
            logger.info(f"🤖 [UNIFIED PIPELINE] Complex query ('{query}') -> Running MedicalAgent Tool Orchestration...")
            effective_context, results = self.medical_agent.run_tool_orchestration(query, history)
            agent_used = True
        else:
            logger.info(f"⚡ [UNIFIED PIPELINE] Simple query ('{query}') -> Running Direct 1-Turn Hybrid Retrieval...")
            search_query = self.contextualize_retrieval_query(query, history)
            retrieval_response = self.retriever.retrieve(
                query=search_query,
                top_k=effective_top_k,
                filter_metadata=filter_metadata,
                rerank=rerank,
                rerank_top_n=effective_top_k,
                confidence_threshold=confidence_threshold
            )
            results = retrieval_response.get("results", [])
            effective_context = retrieval_response.get("context", "")

        retrieval_ms = int((_time.time() - t0_retrieval) * 1000)

        # 3. Context & Evidence Validation
        is_context_empty = (
            not results 
            or effective_context in ("Maaf, saya tidak menemukan informasi.", "No relevant context found.")
            or len(effective_context.strip()) == 0
        )
        context_status = "REJECTED" if is_context_empty else "ACCEPTED"
        context_for_prompt = effective_context if not is_context_empty else "(Tidak ada dokumen spesifik ERHA yang ditemukan dalam basis pengetahuan untuk kueri ini.)"

        # 4. Clinical Safety Gate Check before LLM generation
        is_safe_gate, safe_msg = self.validate_clinical_safety_gate(query, "", context_status, results, intent)
        if not is_safe_gate:
            log_rag_chat(
                query=query,
                intent_val=intent.value,
                top_k=effective_top_k,
                results=results,
                context_status=context_status,
                retrieval_ms=retrieval_ms,
                llm_ms=0,
                guardrails_status="PASSED",
                agent_used=agent_used
            )
            return {
                "query": query,
                "answer": safe_msg,
                "context": effective_context,
                "results": results,
                "agent_used": agent_used
            }

        # 5. Unified Single LLM Prompt & Synthesis
        full_prompt = self.build_prompt(query, context_for_prompt, history, intent, intent_rules)
        t0_llm = _time.time()
        error_msg = None
        try:
            raw_answer = self.llm_adapter.generate(full_prompt).strip()
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            raw_answer = "Maaf, terjadi kesalahan teknis pada pemrosesan LLM. Silakan coba beberapa saat lagi."
        llm_ms = int((_time.time() - t0_llm) * 1000)

        # 6. Output Guardrails Processing & Clinical Safety Gate
        sanitized_answer = GuardrailsPipeline.process_output(raw_answer)
        _, final_answer = self.validate_clinical_safety_gate(query, sanitized_answer, context_status, results, intent)

        # 7. Standardized Visual Backend Logging
        log_rag_chat(
            query=query,
            intent_val=intent.value,
            top_k=effective_top_k,
            results=results,
            context_status=context_status,
            retrieval_ms=retrieval_ms,
            llm_ms=llm_ms,
            guardrails_status="PASSED",
            agent_used=agent_used,
            error_msg=error_msg
        )

        return {
            "query": query,
            "answer": final_answer,
            "context": effective_context,
            "results": results,
            "agent_used": agent_used
        }

    async def generate_answer_stream(
        self, 
        query: str, 
        top_k: int = 5, 
        filter_metadata: Optional[Dict[str, Any]] = None,
        rerank: bool = True,
        confidence_threshold: Optional[float] = None,
        history: List[Dict[str, str]] = [],
        force_agent: bool = False
    ):
        """Unified Entry Point for Streaming API with Output Guardrails & Safety Validation."""
        import asyncio
        t0_total = _time.time()

        # 0. Input Guardrails Validation
        is_safe, rejection_msg = GuardrailsPipeline.validate_input(query)
        if not is_safe:
            log_rag_chat(
                query=query,
                intent_val="UNKNOWN",
                top_k=top_k,
                results=[],
                context_status="REJECTED",
                retrieval_ms=0,
                llm_ms=0,
                guardrails_status="BLOCKED"
            )
            yield json.dumps({"type": "context", "results": []}) + "\n"
            yield rejection_msg or "Maaf, permintaan Anda tidak dapat diproses."
            return
        
        intent, intent_rules = QueryIntentDetector.detect(query)

        if intent == QueryIntent.GREETING:
            greeting_ans = get_time_greeting_response(query)
            llm_ms = int((_time.time() - t0_total) * 1000)
            log_rag_chat(
                query=query,
                intent_val=intent.value,
                top_k=top_k,
                results=[],
                context_status="ACCEPTED",
                retrieval_ms=0,
                llm_ms=llm_ms,
                guardrails_status="PASSED"
            )
            yield json.dumps({"type": "context", "results": []}) + "\n"
            yield greeting_ans
            return

        effective_top_k = QueryIntentDetector.get_recommended_top_k(query, intent, top_k)
        
        # 1. Complexity Routing & Evidence Retrieval
        t0_retrieval = _time.time()
        is_complex = force_agent or QueryIntentDetector.should_use_agent(query, intent)
        agent_used = False

        if is_complex and self.medical_agent:
            effective_context, results = await asyncio.to_thread(
                self.medical_agent.run_tool_orchestration,
                question=query,
                history=history
            )
            agent_used = True
        else:
            search_query = self.contextualize_retrieval_query(query, history)
            retrieval_response = await asyncio.to_thread(
                self.retriever.retrieve,
                query=search_query,
                top_k=effective_top_k,
                filter_metadata=filter_metadata,
                rerank=rerank,
                rerank_top_n=effective_top_k,
                confidence_threshold=confidence_threshold
            )
            results = retrieval_response.get("results", [])
            effective_context = retrieval_response.get("context", "")

        retrieval_ms = int((_time.time() - t0_retrieval) * 1000)

        # First yield context SSE JSON chunk
        yield json.dumps({"type": "context", "results": results}) + "\n"

        is_context_empty = (
            not results 
            or effective_context in ("Maaf, saya tidak menemukan informasi.", "No relevant context found.")
            or len(effective_context.strip()) == 0
        )
        context_status = "REJECTED" if is_context_empty else "ACCEPTED"
        context_for_prompt = effective_context if not is_context_empty else "(Tidak ada dokumen spesifik ERHA yang ditemukan dalam basis pengetahuan untuk kueri ini.)"

        # Check Clinical Safety Gate before streaming LLM tokens
        is_safe_gate, safe_msg = self.validate_clinical_safety_gate(query, "", context_status, results, intent)
        if not is_safe_gate:
            log_rag_chat(
                query=query,
                intent_val=intent.value,
                top_k=effective_top_k,
                results=results,
                context_status=context_status,
                retrieval_ms=retrieval_ms,
                llm_ms=0,
                guardrails_status="PASSED",
                agent_used=agent_used
            )
            yield safe_msg
            return

        full_prompt = self.build_prompt(query, context_for_prompt, history, intent, intent_rules)

        t0_llm = _time.time()
        error_msg = None
        full_stream_text = ""
        try:
            async for token in self.llm_adapter.generate_stream(full_prompt):
                full_stream_text += token
                yield token
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            yield "Maaf, terjadi kesalahan teknis pada pemrosesan LLM. Silakan coba beberapa saat lagi."
        finally:
            llm_ms = int((_time.time() - t0_llm) * 1000)
            if full_stream_text:
                GuardrailsPipeline.process_output(full_stream_text)

            log_rag_chat(
                query=query,
                intent_val=intent.value,
                top_k=effective_top_k,
                results=results,
                context_status=context_status,
                retrieval_ms=retrieval_ms,
                llm_ms=llm_ms,
                guardrails_status="PASSED",
                agent_used=agent_used,
                error_msg=error_msg
            )
