from typing import List, Dict, Any, Optional
from loguru import logger
from configs.settings import settings
from core.interfaces import BaseVectorStoreAdapter
from .bm25 import BM25Index
from .reranker import Reranker
from .context_builder import PromptContextBuilder

def get_chunk_key(hit: Dict[str, Any]) -> str:
    meta = hit.get("metadata", {})
    source_file = meta.get("source_file")
    chunk_index = meta.get("chunk_index")
    if source_file is not None and chunk_index is not None:
        return f"{source_file}_{chunk_index}"
    # Fallback to hashed text if metadata is missing
    return str(hash(hit.get("text", "")))

def reciprocal_rank_fusion(
    dense_hits: List[Dict[str, Any]], 
    sparse_hits: List[Dict[str, Any]], 
    rrf_k: int = 60
) -> List[Dict[str, Any]]:
    """
    Combines dense and sparse hits using Reciprocal Rank Fusion (RRF).
    """
    rrf_scores = {}

    # Process Dense Search Hits (ranked by Qdrant similarity)
    for rank, hit in enumerate(dense_hits, start=1):
        key = get_chunk_key(hit)
        if key not in rrf_scores:
            rrf_scores[key] = {"hit": hit, "score": 0.0}
        rrf_scores[key]["score"] += 1.0 / (rrf_k + rank)

    # Process Sparse Search Hits (ranked by BM25 score)
    for rank, hit in enumerate(sparse_hits, start=1):
        key = get_chunk_key(hit)
        if key not in rrf_scores:
            rrf_scores[key] = {"hit": hit, "score": 0.0}
        rrf_scores[key]["score"] += 1.0 / (rrf_k + rank)

    # Sort candidates by combined RRF score descending
    sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k]["score"], reverse=True)

    fused_hits = []
    for key in sorted_keys:
        merged_hit = rrf_scores[key]["hit"].copy()
        # Replace search score with the deterministic RRF rank score
        merged_hit["rrf_score"] = rrf_scores[key]["score"]
        # Maintain a score field for backward compatibility
        merged_hit["score"] = rrf_scores[key]["score"]
        fused_hits.append(merged_hit)

    return fused_hits

class HybridRetriever:
    def __init__(
        self, 
        vector_store: BaseVectorStoreAdapter, 
        bm25_index: BM25Index,
        reranker: Optional[Reranker] = None
    ):
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.reranker = reranker

    def retrieve(
        self, 
        query: str, 
        top_k: int = 5, 
        filter_metadata: Optional[Dict[str, Any]] = None,
        rerank: bool = True,
        rerank_top_n: int = 3,
        confidence_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes Advanced Retrieval Pipeline:
        1. Dense Retrieval (Qdrant)
        2. Sparse Retrieval (BM25)
        3. Reciprocal Rank Fusion (RRF)
        4. Cross-Encoder Reranking (optional)
        5. Prompt Context Generation
        """
        logger.info(f"Retrieving for query: '{query}' with top_k={top_k}, metadata_filter={filter_metadata}")

        # Check if the query is a multi-intent query (contains conjunctions)
        sub_queries = []
        for separator in [" dan ", " serta ", " and ", " & "]:
            if separator in query:
                # Split by the separator
                parts = query.split(separator)
                # Filter out short parts (less than 3 chars) to avoid split artifacts
                parts = [p.strip() for p in parts if len(p.strip()) > 3]
                if len(parts) > 1:
                    sub_queries = parts
                    break

        candidate_k = top_k * 2
        
        # 1 & 2 & 3: Dense and Sparse Search with RRF Fusion
        if sub_queries:
            logger.info(f"Multi-intent query detected. Splitting query into sub-queries: {sub_queries}")
            sub_fused_hits = []
            
            for sq in sub_queries:
                sq_dense = self.vector_store.search(sq, top_k=candidate_k, filter_metadata=filter_metadata)
                sq_sparse = self.bm25_index.search(sq, top_k=candidate_k, filter_metadata=filter_metadata)
                sq_fused = reciprocal_rank_fusion(sq_dense, sq_sparse)
                sub_fused_hits.append(sq_fused)
                
            # Interleave the results of the sub-queries to ensure fair representation of each intent
            fused_hits = []
            seen_keys = set()
            
            max_len = max(len(lst) for lst in sub_fused_hits) if sub_fused_hits else 0
            for i in range(max_len):
                for lst in sub_fused_hits:
                    if i < len(lst):
                        hit = lst[i]
                        key = get_chunk_key(hit)
                        if key not in seen_keys:
                            seen_keys.add(key)
                            fused_hits.append(hit)
            logger.info(f"Interleaved sub-queries completed. Combined into {len(fused_hits)} candidates.")
        else:
            # Single intent query
            dense_hits = self.vector_store.search(query, top_k=candidate_k, filter_metadata=filter_metadata)
            logger.debug(f"Dense retrieval returned {len(dense_hits)} candidates.")
            
            sparse_hits = self.bm25_index.search(query, top_k=candidate_k, filter_metadata=filter_metadata)
            logger.debug(f"Sparse retrieval returned {len(sparse_hits)} candidates.")
            
            fused_hits = reciprocal_rank_fusion(dense_hits, sparse_hits)
            logger.info(f"RRF Fusion completed. Fused {len(fused_hits)} candidates.")

        # Deduplicate hits based on exact normalized text content
        seen_texts = set()
        deduplicated_hits = []
        for hit in fused_hits:
            text = hit.get("text", "").strip()
            norm_text = " ".join(text.split()).lower()
            if norm_text not in seen_texts:
                seen_texts.add(norm_text)
                deduplicated_hits.append(hit)
        logger.info(f"Deduplicated fused hits from {len(fused_hits)} to {len(deduplicated_hits)} unique candidates.")

        # 4. Optional Cross-Encoder Reranking
        final_hits = deduplicated_hits
        if rerank and self.reranker:
            # Score all unique fused hits using the Reranker
            all_reranked = self.reranker.rerank(query, deduplicated_hits, top_n=len(deduplicated_hits))
            
            # Apply heuristic intent boosting to resolve model bias towards longer passages
            query_lower = query.lower()
            usage_keywords = ["how to use", "directions", "cara pakai", "cara penggunaan", "aturan pakai", "dosis", "instruksi"]
            ingredients_keywords = ["kandungan", "ingredients", "bahan aktif", "komposisi", "active ingredients"]
            
            is_usage_intent = any(k in query_lower for k in usage_keywords)
            is_ingredients_intent = any(k in query_lower for k in ingredients_keywords)
            
            boosted_hits = []
            for hit in all_reranked:
                updated_hit = hit.copy()
                section_upper = updated_hit.get("metadata", {}).get("section", "").upper()
                boost = 0.0
                if is_usage_intent and any(s in section_upper for s in ["HOW TO USE", "DIRECTIONS"]):
                    boost += 0.05
                elif is_ingredients_intent and any(s in section_upper for s in ["INGREDIENT", "KANDUNGAN", "KOMPOSISI"]):
                    boost += 0.05
                
                if boost > 0:
                    updated_hit["rerank_score"] = updated_hit.get("rerank_score", 0.0) + boost
                    logger.debug(f"Applied intent boost of +{boost} to section '{section_upper}' (new score: {updated_hit['rerank_score']:.4f})")
                boosted_hits.append(updated_hit)
                
            # Re-sort hits by updated rerank score descending
            final_hits = sorted(boosted_hits, key=lambda h: h.get("rerank_score", 0.0), reverse=True)[:rerank_top_n]
            logger.info(f"Reranking and intent boosting completed. Returned top {len(final_hits)} chunks.")
        else:
            # No reranking, simply slice to top_k
            final_hits = deduplicated_hits[:top_k]

        # 4.5. Confidence Threshold Check (BRD requirement)
        threshold = confidence_threshold if confidence_threshold is not None else settings.rerank_confidence_threshold
        if rerank and self.reranker and final_hits:
            max_score = final_hits[0].get("rerank_score", 0.0)
            if max_score < threshold:
                logger.warning(f"Retrieval confidence score {max_score:.4f} is below threshold {threshold:.4f}. Rejecting retrieved context.")
                return {
                    "query": query,
                    "results": [],
                    "context": "Maaf, saya tidak menemukan informasi."
                }

        # 5. Build prompt context block
        context_string = PromptContextBuilder.build_context(final_hits)

        return {
            "query": query,
            "results": final_hits,
            "context": context_string
        }
