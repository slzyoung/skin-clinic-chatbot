import os
import json
from typing import List, Dict, Any, Optional
from loguru import logger

from app.rag.services.interfaces import BaseLLMAdapter
from app.rag.services.rag_retriever import HybridRetriever
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
            "temperature": 0.2
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



# --- System Prompt Configuration ---

SYSTEM_PROMPT = """You are CHAT AI ERHA, an expert Clinical Decision Support System & Medical Copilot designed specifically for ERHA (PT Arya Noble) Dermatologists, Medical Officers, and General Practitioners.
Your primary role is to assist doctors in selecting, prescribing, and recommending the most appropriate ERHA skin care products, active formulations, and clinical aesthetic treatments for their patients based on diagnosis, skin conditions, and clinical guidelines.

DOCTOR-FOCUSED CLINICAL COMMUNICATION GUIDELINES:
1. **Professional Clinical Tone**: Speak collegially as a peer medical aesthetic AI expert (Doctor-to-Doctor tone). Use precise dermatological terminology (e.g., *acne vulgaris*, *papulopustular*, *post-inflammatory hyperpigmentation*, *keratolytic*, *sebum control*, *skin barrier restoration*).
2. **Patient Recommendation & Prescription Focus**: When a doctor asks for product or treatment recommendations for a specific patient condition (e.g., oily skin with inflammatory acne, hyperpigmentation, sensitive skin), structure your response clearly:
   - 📌 **Rekomendasi Produk Topikal (Homecare)**: Product name, key active ingredients & concentration (e.g. 2% Salicylic Acid, 4% Niacinamide), primary clinical mechanism.
   - 💆 **Rekomendasi Tindakan Klinis (Clinical Treatments)**: In-clinic procedures if applicable.
   - 📋 **Petunjuk Penggunaan & Dosis**: Frequency (e.g. 2x sehari pagi & malam), sunscreen integration.
   - ⚠️ **Kontraindikasi & Perhatian Khusus**: Pregnancy/lactation safety (e.g., Salicylic Acid precautions), potential side effects (transient erythema, dryness).
3. **Greetings & Catalog Inquiries**: For greetings (e.g., "halo", "selamat pagi") or general catalog questions ("ada produk apa saja?"), greet the doctor warmly and provide a clean, structured overview of available ERHA products and treatments from the context.
4. **Markdown Formatting**: Output must be beautifully structured in clean Markdown with clear titles (`#`), section headers (`##`), bold highlights (`**`), bullet points (`-`), and clean tables where relevant.
5. **Contextual & Citation Grounding**: Ground all clinical facts strictly on the provided Context block. Cite source references using `[1]`, `[2]` when context passages are cited.
6. **Helpful Fallback**: If specific clinical details for an unlisted condition/product are missing from context, inform the doctor collegially in professional medical Indonesian.
"""


# --- Generation Pipeline ---

class GenerationPipeline:
    def __init__(self, retriever: HybridRetriever, llm_adapter: BaseLLMAdapter):
        self.retriever = retriever
        self.llm_adapter = llm_adapter

    def _get_approved_docs_summary(self) -> str:
        """Fetches list of approved documents for conversational context fallback."""
        approved_dir = "data/output"
        docs_list = []
        if os.path.exists(approved_dir):
            for f in os.listdir(approved_dir):
                if f.endswith(".json"):
                    try:
                        with open(os.path.join(approved_dir, f), "r", encoding="utf-8") as fp:
                            data = json.load(fp)
                            if isinstance(data, dict):
                                fn = data.get("file_name", f.replace(".json", ""))
                                summary_head = data.get("summary", "")[:200].replace("\n", " ")
                                docs_list.append(f"- **{fn}**: {summary_head}...")
                    except Exception:
                        pass
        if docs_list:
            return "Daftar Dokumen Terdaftar di Knowledge Base:\n" + "\n".join(docs_list)
        return "Basis data saat ini sedang diperbarui."

    def build_prompt(self, query: str, context: str, history: List[Dict[str, str]]) -> str:
        """
        Compiles the system prompt, retrieved context, conversation history, 
        and the user's latest query into a single string.
        """
        history_str = ""
        if history:
            for msg in history:
                role = "User" if msg.get("role") == "user" else "Assistant"
                content = msg.get("content", "")
                history_str += f"{role}: {content}\n"
        else:
            history_str = "No previous conversation.\n"

        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"--- CONTEXT ---\n"
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
        Retrieves relevant context, compiles the prompt, and generates 
        an grounded response from the LLM adapter.
        """
        logger.info(f"Generating answer for query: '{query}'")

        # 1. Retrieve relevant chunks from Hybrid Retriever
        retrieval_response = self.retriever.retrieve(
            query=query,
            top_k=top_k,
            filter_metadata=filter_metadata,
            rerank=rerank,
            rerank_top_n=top_k,
            confidence_threshold=confidence_threshold
        )

        results = retrieval_response.get("results", [])
        context = retrieval_response.get("context", "")

        # 2. If context is empty, supply fallback catalog context for conversational queries
        if not results or context in ("Maaf, saya tidak menemukan informasi.", "No relevant context found."):
            logger.info("Retrieval context empty. Using approved knowledge base catalog for fallback AI response.")
            context = self._get_approved_docs_summary()

        # 3. Build Prompt with Context & History
        full_prompt = self.build_prompt(query, context, history)

        # 4. Generate Answer via LLM Adapter
        try:
            logger.info("Executing LLM generation...")
            answer = self.llm_adapter.generate(full_prompt)
            answer = answer.strip()
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            answer = "Maaf, terjadi kesalahan teknis pada pemrosesan LLM. Silakan coba beberapa saat lagi."

        return {
            "query": query,
            "answer": answer,
            "context": context,
            "results": results
        }
