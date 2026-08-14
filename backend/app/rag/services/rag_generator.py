import os
import json
from typing import List, Dict, Any, Optional
from loguru import logger

from app.rag.services.interfaces import BaseLLMAdapter
from app.rag.services.rag_retriever import HybridRetriever
from app.rag.services.intent import QueryIntentDetector, QueryIntent, get_current_time_period, get_time_greeting_response
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
        import time
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
                    time.sleep(backoff_delay)
                    backoff_delay *= 2.0
                else:
                    logger.error(f"LLM generation failed on attempt {attempt}/{max_retries}: {e}")
                    raise e

    async def generate_stream(self, prompt: str):
        import time
        import asyncio
        max_retries = 3
        backoff_delay = 5.0
        
        for attempt in range(1, max_retries + 1):
            try:
                # We use astream to yield tokens
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
You are ERHA Medical Assistant, an expert clinical decision support and product knowledge assistant exclusively for ERHA Doctors and Clinicians (PT Arya Noble).
The user is ALWAYS an ERHA Doctor/Clinician consulting on ERHA skincare products, clinical protocols, treatment regimens, active ingredients, dosages, and contraindications for treating their patients. This chatbot is NOT used by patients directly.
Your primary responsibility is to provide accurate, concise, clinically grounded, and doctor-tailored answers using ONLY the retrieved ERHA knowledge base.
</role>

<language_and_tone_rules>
- Chatbot ini digunakan KHUSUS OLEH DOKTER ERHA (bukan pasien umum). Gunakan gaya komunikasi profesional medis klinis antar sejawat (medical assistant to doctor).
- Selalu sapa pengguna dengan sebutan 'Dokter' atau 'Dok' jika memerlukan sapaan.
- Bahasa utama yang digunakan adalah Bahasa Indonesia medis yang jelas dan natural.
- HANYA sertakan sapaan pembuka (seperti 'Halo Dok! Selamat siang') jika Dokter secara eksplisit menyapa di awal query (seperti 'halo', 'selamat pagi') ATAU pada pesan pertama percakapan. Jika percakapan sudah berlangsung (history > 0) atau Dokter langsung bertanya tanpa kata sapaan, DILARANG mengulang sapaan pembuka. Langsung jawab pertanyaan secara singkat, padat, dan objektif.
- HANYA gunakan Bahasa Inggris jika Dokter mengajukan pertanyaan dalam Bahasa Inggris.
</language_and_tone_rules>

<negative_prompting_and_strict_grounding>
1. CRITICAL RESTRICTION: NEVER recommend, invent, or mention non-ERHA third-party commercial skincare brands, outside clinic procedures, or ungrounded external prescription drugs that do NOT exist in the retrieved ERHA knowledge base context.
2. Ground all answers strictly in facts from the retrieved ERHA context. Do NOT extrapolate or speculate.
3. If requested medical/product information (e.g. specific product, dosage, protocol, or price) is NOT present in the retrieved context, state clearly and politely in the user's language that the information is not available in the ERHA knowledge base. NEVER substitute with generic outside products.
4. When asked for recommendations (treatment, products, or routine) for skin concerns (e.g. oily skin, mild inflammatory acne, papules, post-acne marks/scars), provide the relevant ERHA treatments and products found in the retrieved context.
5. If the user asks to separate categories (e.g. active acne vs post-acne, treatments vs products, morning vs night), structure the response clearly with distinct sections.
6. Preserve exact product names, ingredient names, percentages, quantities, and clinical instructions from the retrieved context.
7. Do not repeat the user's question verbatim.
8. CRITICAL: DILARANG KERAS menyertakan disclaimer pasien atau kalimat penutup seperti "Pastikan untuk melakukan konsultasi lebih lanjut sebelum memulai perawatan...", "Konsultasikan dengan dokter...", "Disarankan untuk berkonsultasi...", dsb. Pengguna sistem ini ADALAH DOKTER itu sendiri yang sedang bertugas.
9. CRITICAL: DILARANG menempelkan kalimat penutup basa-basi seperti "Jika ada pertanyaan lebih lanjut, silakan beri tahu", "Jika Dokter membutuhkan informasi tambahan...", dsb. Akhiri jawaban secara langsung pada poin fakta/penjelasan medis utama tanpa basa-basi penutup.
</negative_prompting_and_strict_grounding>

<multimodal_image_display_rules>
- Saat merekomendasikan atau menjelaskan produk atau tindakan ERHA, jika konteks dari database menyertakan image URL yang valid (misalnya `![Product Name](url)` atau `Image: <url>`), SELALU tampilkan gambar produk dalam format Markdown:
  `![Nama Lengkap Produk](image_url)`
  tepat di bawah teks rekomendasi/penjelasan produk tersebut agar dokter dapat melihat bentuk fisik dan kemasan produk.
- Jika di database/konteks TIDAK terdapat image_url untuk produk tersebut, jawab CUKUP DENGAN TEKS saja. DILARANG membuat, mengarang, atau menebak URL gambar palsu/placeholder.
</multimodal_image_display_rules>

<response_length_rules>
- Routine / Multi-product steps / Categorized recommendations: Provide clear step-by-step or categorized structure without skipping retrieved products.
- Product name question: 1 sentence.
- Ingredient question: 1-2 sentences or a concise list.
- Function/benefit question: 2-3 sentences.
- How-to-use question: 2-4 sentences.
- Comparison question: concise comparison using only relevant information.
</response_length_rules>"""


# --- Generation Pipeline ---

class GenerationPipeline:
    def __init__(self, retriever: HybridRetriever, llm_adapter: BaseLLMAdapter):
        self.retriever = retriever
        self.llm_adapter = llm_adapter

    def build_prompt(
        self, 
        query: str, 
        context: str, 
        history: List[Dict[str, str]], 
        intent: QueryIntent, 
        intent_rules: Dict[str, Any]
    ) -> str:
        """
        Compiles system prompt, retrieved context, intent instructions,
        conversation history, and user query into a grounded prompt.
        """
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
            f"--- CONTEXT (RETRIEVED FROM ERHA KNOWLEDGE BASE) ---\n"
            f"{context}\n\n"
            f"--- CONVERSATION HISTORY ---\n"
            f"{history_str}\n"
            f"User: {query}\n"
            f"Assistant:"
        )
        return prompt

    def generate_answer(
        self, 
        query: str, 
        top_k: int = 5, 
        filter_metadata: Optional[Dict[str, Any]] = None,
        rerank: bool = True,
        confidence_threshold: Optional[float] = None,
        history: List[Dict[str, str]] = []
    ) -> Dict[str, Any]:
        """
        Retrieves relevant context, compiles prompt, and generates grounded response.
        Includes intent classification, dynamic top_k boosting, guardrails, and debug logging.
        """
        from app.rag.services.guardrails import GuardrailsPipeline

        # 0. Input Guardrails Validation (Prompt Injection & Topicality)
        is_safe, rejection_msg = GuardrailsPipeline.validate_input(query)
        if not is_safe:
            logger.warning(f"Query blocked by Guardrails: '{query[:80]}...'")
            return {
                "query": query,
                "answer": rejection_msg or "Maaf, permintaan Anda tidak dapat diproses.",
                "context": "Blocked by security guardrails.",
                "results": []
            }

        # 1. Query Intent Detection & Dynamic Top-K Calculation
        intent, intent_rules = QueryIntentDetector.detect(query)

        # Handle pure greeting immediately with warm time-adjusted response
        if intent == QueryIntent.GREETING:
            greeting_ans = get_time_greeting_response(query)
            logger.info(
                f"\n"
                f"================================================================================\n"
                f"🩺 [RAG CLINICAL CHAT] Doctor Query Execution\n"
                f"--------------------------------------------------------------------------------\n"
                f"❓ Query               : \"{query}\"\n"
                f"🎯 Detected Intent     : {intent.value}\n"
                f"📊 Top Akurasi         : 100.0% (Fast-path Sapaan)\n"
                f"📚 Retrieved Chunks    : 0 chunk(s)\n"
                f"--------------------------------------------------------------------------------\n"
                f"📝 Jawaban AI (Preview): {greeting_ans}\n"
                f"🛡️ Guardrails Check    : Passed (Sanitized)\n"
                f"================================================================================\n"
            )
            return {
                "query": query,
                "answer": greeting_ans,
                "context": "",
                "results": []
            }

        effective_top_k = QueryIntentDetector.get_recommended_top_k(query, intent, top_k)
        if effective_top_k != top_k:
            logger.debug(f"Dynamic top_k applied: adjusted from {top_k} to {effective_top_k} based on query complexity ({intent.value}).")

        # 2. Retrieve relevant chunks from Hybrid Retriever
        retrieval_response = self.retriever.retrieve(
            query=query,
            top_k=effective_top_k,
            filter_metadata=filter_metadata,
            rerank=rerank,
            rerank_top_n=effective_top_k,
            confidence_threshold=confidence_threshold
        )

        results = retrieval_response.get("results", [])
        context = retrieval_response.get("context", "")

        # 3. Check for empty context or low confidence
        is_context_empty = (
            not results 
            or context in ("Maaf, saya tidak menemukan informasi.", "No relevant context found.")
            or len(context.strip()) == 0
        )

        if is_context_empty:
            missing_msg = intent_rules.get("missing_fallback", "Informasi tersebut tidak tersedia dalam knowledge base.")
            missing_preview = " ".join(missing_msg.split())
            if len(missing_preview) > 130:
                missing_preview = missing_preview[:130] + "..."

            logger.info(
                f"\n"
                f"================================================================================\n"
                f"🩺 [RAG CLINICAL CHAT] Doctor Query Execution\n"
                f"--------------------------------------------------------------------------------\n"
                f"❓ Query               : \"{query}\"\n"
                f"🎯 Detected Intent     : {intent.value} (Top-K: {effective_top_k})\n"
                f"📊 Top Akurasi         : 0.0% (No matching context)\n"
                f"📚 Retrieved Chunks    : 0 chunk(s)\n"
                f"--------------------------------------------------------------------------------\n"
                f"📝 Jawaban AI (Preview): {missing_preview}\n"
                f"🛡️ Guardrails Check    : Passed (Sanitized)\n"
                f"================================================================================\n"
            )
            return {
                "query": query,
                "answer": missing_msg,
                "context": "No relevant context found in knowledge base.",
                "results": []
            }

        # 4. Build Grounded Prompt with Context, Intent & History
        full_prompt = self.build_prompt(query, context, history, intent, intent_rules)

        # 5. Generate Answer via LLM Adapter
        try:
            answer = self.llm_adapter.generate(full_prompt)
            answer = answer.strip()
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            answer = "Maaf, terjadi kesalahan teknis pada pemrosesan LLM. Silakan coba beberapa saat lagi."

        # 6. Output Guardrails Processing (PII Redaction & Medical Disclaimer)
        answer = GuardrailsPipeline.process_output(answer)

        # --- VISUAL BACKEND LOGS ---
        top_accuracy_pct = 0.0
        scores_summary = []
        for i, res in enumerate(results[:5], 1):
            sc = res.get("rerank_score", res.get("score", 0.0))
            if 0.0 <= sc <= 1.0:
                acc_pct = sc * 100.0
            else:
                import math
                acc_pct = (1.0 / (1.0 + math.exp(-sc))) * 100.0

            if i == 1:
                top_accuracy_pct = acc_pct

            meta = res.get("metadata", {})
            src = meta.get("source_file", "unknown")
            p_name = meta.get("product_name") or meta.get("title") or "-"
            img_tag = f" 🖼️ [Image]" if meta.get("image_url") else ""
            scores_summary.append(f"   [{i}] {src} | {p_name} | Akurasi: {acc_pct:.1f}% (Score: {sc:.4f}){img_tag}")

        retrieved_list_str = "\n".join(scores_summary) if scores_summary else "   (No chunks retrieved)"
        accuracy_display = f"{top_accuracy_pct:.1f}%" if results else "0.0%"

        ans_preview = " ".join(answer.split())
        if len(ans_preview) > 130:
            ans_preview = ans_preview[:130] + "..."

        logger.info(
            f"\n"
            f"================================================================================\n"
            f"🩺 [RAG CLINICAL CHAT] Doctor Query Execution\n"
            f"--------------------------------------------------------------------------------\n"
            f"❓ Query               : \"{query}\"\n"
            f"🎯 Detected Intent     : {intent.value} (Top-K: {effective_top_k})\n"
            f"📊 Top Akurasi         : {accuracy_display}\n"
            f"📚 Retrieved Chunks    : {len(results)} document chunk(s)\n"
            f"{retrieved_list_str}\n"
            f"--------------------------------------------------------------------------------\n"
            f"📝 Jawaban AI (Preview): {ans_preview}\n"
            f"🛡️ Guardrails Check    : Passed (Sanitized)\n"
            f"================================================================================\n"
        )

        return {
            "query": query,
            "answer": answer,
            "context": context,
            "results": results
        }

    async def generate_answer_stream(
        self, 
        query: str, 
        top_k: int = 5, 
        filter_metadata: Optional[Dict[str, Any]] = None,
        rerank: bool = True,
        confidence_threshold: Optional[float] = None,
        history: List[Dict[str, str]] = []
    ):
        """
        Retrieves context and yields a stream of response tokens.
        First yields a JSON object with 'type': 'context' containing the results.
        Then yields text tokens.
        """
        import json
        from app.rag.services.guardrails import GuardrailsPipeline

        # 0. Input Guardrails Validation
        is_safe, rejection_msg = GuardrailsPipeline.validate_input(query)
        if not is_safe:
            yield json.dumps({"type": "context", "results": []}) + "\n"
            yield rejection_msg or "Maaf, permintaan Anda tidak dapat diproses."
            return
        
        intent, intent_rules = QueryIntentDetector.detect(query)

        # Handle pure greeting immediately in stream with warm time-adjusted response
        if intent == QueryIntent.GREETING:
            greeting_ans = get_time_greeting_response(query)
            logger.info(f"Pure greeting stream detected ('{query}'). Yielding warm time-adjusted response.")
            yield json.dumps({"type": "context", "results": []}) + "\n"
            yield greeting_ans
            return

        effective_top_k = QueryIntentDetector.get_recommended_top_k(query, intent, top_k)
        if effective_top_k != top_k:
            logger.info(f"Dynamic stream top_k applied: adjusted from {top_k} to {effective_top_k} based on query complexity ({intent.value}).")

        # Using thread for retrieve since it might be sync
        import asyncio
        retrieval_response = await asyncio.to_thread(
            self.retriever.retrieve,
            query=query,
            top_k=effective_top_k,
            filter_metadata=filter_metadata,
            rerank=rerank,
            rerank_top_n=effective_top_k,
            confidence_threshold=confidence_threshold
        )

        results = retrieval_response.get("results", [])
        context = retrieval_response.get("context", "")

        # Send initial context metadata block so frontend knows sources immediately
        yield json.dumps({"type": "context", "results": results})

        is_context_empty = (
            not results 
            or context in ("Maaf, saya tidak menemukan informasi.", "No relevant context found.")
            or len(context.strip()) == 0
        )

        if is_context_empty:
            missing_msg = intent_rules.get("missing_fallback", "Informasi tersebut tidak tersedia dalam knowledge base.")
            yield missing_msg
            return

        full_prompt = self.build_prompt(query, context, history, intent, intent_rules)

        try:
            async for token in self.llm_adapter.generate_stream(full_prompt):
                yield token
        except Exception as e:
            logger.error(f"LLM stream generation failed: {e}")
            yield "Maaf, terjadi kesalahan teknis pada pemrosesan LLM. Silakan coba beberapa saat lagi."
