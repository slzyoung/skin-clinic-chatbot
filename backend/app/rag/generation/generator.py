import os
from typing import List, Dict, Any, Optional
from loguru import logger

from app.rag.core.interfaces import BaseLLMAdapter
from app.rag.retrieval.retriever import HybridRetriever

SYSTEM_PROMPT = """You are CHAT AI ERHA, a helpful, professional, and highly knowledgeable medical aesthetic assistant for ERHA (PT Arya Noble) products, treatments, FAQs, promotions, and clinical SOPs.
Your tone should be professional, polite, and empathetic.

GROUND RULES:
1. Answer the user's question ONLY using the facts from the Context block provided below.
2. If the context is empty, or if it does not contain enough information to answer the question, you MUST answer exactly: "Maaf, saya tidak menemukan informasi."
3. Do not make up or assume any clinical protocols, active ingredients, indications, side effects, or promotional offers.
4. Cite the source files of the facts by adding their numbered references (e.g., [1], [2]) at the end of the sentences that use those facts. Always map the citation correctly to the matching source in the Context.
5. Provide responses in Indonesian unless asked otherwise. Format the answer using clear Markdown (e.g. bold titles, bullet points) for readability.
"""

from langchain_core.language_models.chat_models import BaseChatModel
from .builder import PromptContextBuilder

class GenerationPipeline:
    def __init__(self, retriever: HybridRetriever, llm_adapter: BaseChatModel):
        self.retriever = retriever
        self.llm_adapter = llm_adapter

    def build_prompt(self, query: str, context: str, history: List[Dict[str, str]]) -> str:
        """
        Compiles the system prompt, retrieved context, conversation history, 
        and the user's latest query into a single string.
        """
        # Format the chat history
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

    async def generate_answer(
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
        results = await self.retriever.retrieve(
            query=query,
            top_k=top_k,
            filter_metadata=filter_metadata,
            rerank=rerank,
            rerank_top_n=top_k,
            confidence_threshold=confidence_threshold
        )
        
        # Format context from results list
        if not results:
            context = "Maaf, saya tidak menemukan informasi."
        else:
            context = PromptContextBuilder.build_context(results)

        # 2. Check if context is fallback/empty
        if not results or context == "Maaf, saya tidak menemukan informasi.":
            logger.info("Retrieval returned empty or fallback context. Bypassing LLM call.")
            return {
                "query": query,
                "answer": "Maaf, saya tidak menemukan informasi.",
                "context": context,
                "results": []
            }

        # 3. Build Prompt with Context & History
        full_prompt = self.build_prompt(query, context, history)

        # 4. Generate Answer via LLM Adapter
        try:
            logger.info("Executing LLM generation...")
            # We use ainvoke because we are using LangChain Chat models natively now
            from langchain_core.messages import HumanMessage
            response = await self.llm_adapter.ainvoke([HumanMessage(content=full_prompt)])
            answer = response.content.strip()
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            answer = "Maaf, terjadi kesalahan pada pemrosesan LLM."

        return {
            "query": query,
            "answer": answer,
            "context": context,
            "results": results
        }
