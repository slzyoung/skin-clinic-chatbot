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
        response = self.llm.invoke(prompt)
        return response.content



# --- System Prompt Configuration ---

SYSTEM_PROMPT = """You are CHAT AI ERHA, a helpful, professional, and highly knowledgeable medical aesthetic assistant for ERHA (PT Arya Noble) products, treatments, FAQs, promotions, and clinical SOPs.
Your tone should be professional, polite, and empathetic.

GROUND RULES:
1. Answer the user's question ONLY using the facts from the Context block provided below.
2. If the context is empty, or if it does not contain enough information to answer the question, you MUST answer exactly: "Maaf, saya tidak menemukan informasi."
3. Do not make up or assume any clinical protocols, active ingredients, indications, side effects, or promotional offers.
4. Cite the source files of the facts by adding their numbered references (e.g., [1], [2]) at the end of the sentences that use those facts. Always map the citation correctly to the matching source in the Context.
5. Provide responses in Indonesian unless asked otherwise. Format the answer using clear Markdown (e.g. bold titles, bullet points) for readability.
"""


# --- Generation Pipeline ---

class GenerationPipeline:
    def __init__(self, retriever: HybridRetriever, llm_adapter: BaseLLMAdapter):
        self.retriever = retriever
        self.llm_adapter = llm_adapter

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
            f"{SYSTEM_PROMPT}\n"
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

        # 2. Check if context is fallback/empty
        if not results or context == "Maaf, saya tidak menemukan informasi.":
            logger.info("Retrieval returned empty or fallback context. Bypassing LLM call.")
            return {
                "query": query,
                "answer": "Maaf, saya tidak menemukan informasi.",
                "context": "Maaf, saya tidak menemukan informasi.",
                "results": []
            }

        # 3. Build Prompt with Context & History
        full_prompt = self.build_prompt(query, context, history)

        # 4. Generate Answer via LLM Adapter
        try:
            logger.info("Executing LLM generation...")
            answer = self.llm_adapter.generate(full_prompt)
            answer = answer.strip()
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            answer = "Maaf, terjadi kesalahan pada pemrosesan LLM."

        return {
            "query": query,
            "answer": answer,
            "context": context,
            "results": results
        }
