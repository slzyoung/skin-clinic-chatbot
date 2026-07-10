from typing import List, Dict, Any
from loguru import logger
from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        logger.info(f"Loading Cross-Encoder Reranker model: {model_name}...")
        try:
            # CrossEncoder defaults to CUDA if available, else CPU
            self.model = CrossEncoder(model_name)
            logger.info("Cross-Encoder Reranker model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load CrossEncoder model: {e}")
            self.model = None

    def rerank(self, query: str, hits: List[Dict[str, Any]], top_n: int = 3) -> List[Dict[str, Any]]:
        """
        Reranks retrieve search candidates using the Cross-Encoder.
        Returns the top_n results ordered by relevance score descending.
        """
        if not hits:
            return []
            
        if not self.model:
            logger.warning("Reranker model is not loaded. Returning original hits limited to top_n.")
            return hits[:top_n]

        try:
            # Pair query with context-enriched text for accurate scoring
            pairs = []
            for hit in hits:
                meta = hit.get("metadata", {})
                product_name = meta.get("product_name")
                if not product_name:
                    source_file = meta.get("source_file", "unknown")
                    product_name = source_file
                    for ext in [".pdf", ".docx", ".txt", "_parsed.json"]:
                        product_name = product_name.replace(ext, "")
                    pn_lower = product_name.lower()
                    for prefix in ["dummy_", "dumy_", "dummy-", "dumy-", "dummy ", "dumy "]:
                        if pn_lower.startswith(prefix):
                            product_name = product_name[len(prefix):]
                            pn_lower = pn_lower[len(prefix):]
                    if pn_lower.startswith("dummy") or pn_lower.startswith("dumy"):
                        product_name = product_name[5:]
                    product_name = product_name.replace("-", " ").replace("_", " ")
                    product_name = product_name.strip()
                
                section = meta.get("section", "General")
                text = hit.get("text", "")
                
                # Format: Product: ... | Section: ... | Content: ...
                enriched_text = f"Product: {product_name} | Section: {section} | Content: {text}"
                pairs.append([query, enriched_text])
            
            # Predict similarity scores
            scores = self.model.predict(pairs)
            
            # Attach scores and rank
            reranked_hits = []
            for hit, score in zip(hits, scores):
                updated_hit = hit.copy()
                updated_hit["rerank_score"] = float(score)
                reranked_hits.append(updated_hit)
                
            # Sort by rerank score descending
            sorted_hits = sorted(reranked_hits, key=lambda h: h["rerank_score"], reverse=True)
            
            logger.info(f"Successfully reranked {len(hits)} candidates. Top score: {sorted_hits[0]['rerank_score']:.4f}")
            return sorted_hits[:top_n]
        except Exception as e:
            logger.error(f"Reranking failed: {e}. Falling back to original rankings.")
            return hits[:top_n]
