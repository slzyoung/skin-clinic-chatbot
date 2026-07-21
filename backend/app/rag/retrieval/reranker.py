from typing import List, Dict
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
import json
from loguru import logger

class ExternalReranker:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def rerank(self, query: str, candidates: List[Dict], top_n: int = 3) -> List[Dict]:
        if not candidates:
            return []
            
        system_prompt = """You are a relevance scoring engine.
Given a user query and a list of document chunks, score each chunk from 0.0 to 1.0 based on its relevance to answering the query.
Return the result EXACTLY as a JSON list of floats, in the same order as the chunks.
Example output: [0.9, 0.2, 0.0, 0.8]"""
        
        human_text = f"Query: {query}\n\nChunks:\n"
        for i, chunk in enumerate(candidates):
            human_text += f"--- Chunk {i} ---\n{chunk['content']}\n\n"
            
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_text)
            ])
            
            text = response.content.strip()
            if text.startswith("```json"):
                text = text[7:-3].strip()
            elif text.startswith("```"):
                text = text[3:-3].strip()
                
            scores = json.loads(text)
            
            if len(scores) != len(candidates):
                logger.warning(f"Reranker returned {len(scores)} scores for {len(candidates)} candidates. Falling back.")
                return candidates[:top_n]
                
            for i, chunk in enumerate(candidates):
                chunk["score"] = scores[i]
                
            reranked = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)
            return reranked[:top_n]
            
        except Exception as e:
            logger.error(f"External reranker failed: {e}")
            return candidates[:top_n]
