from typing import List, Dict, Any, Optional
from loguru import logger

class RetrievalEvaluator:
    @staticmethod
    def calculate_hit_rate(
        results: List[Dict[str, Any]], 
        ground_truth: Dict[str, Any], 
        top_k: int
    ) -> float:
        """
        Returns 1.0 if any of the top_k results match the ground_truth criteria, else 0.0.
        ground_truth is a dict of metadata field key-value matches, 
        e.g., {"source_file": "Dummy_ERHA_Product_Brochure.pdf", "section": "ACTIVE INGREDIENTS"}
        """
        hits = results[:top_k]
        for hit in hits:
            metadata = hit.get("metadata", {})
            match = True
            for k, v in ground_truth.items():
                if metadata.get(k) != v:
                    match = False
                    break
            if match:
                return 1.0
        return 0.0

    @staticmethod
    def calculate_reciprocal_rank(
        results: List[Dict[str, Any]], 
        ground_truth: Dict[str, Any], 
        top_k: int
    ) -> float:
        """
        Returns the reciprocal rank (1/rank) of the first matching result in top_k, else 0.0.
        """
        hits = results[:top_k]
        for rank, hit in enumerate(hits, start=1):
            metadata = hit.get("metadata", {})
            match = True
            for k, v in ground_truth.items():
                if metadata.get(k) != v:
                    match = False
                    break
            if match:
                return 1.0 / rank
        return 0.0

    @classmethod
    def evaluate_dataset(
        cls, 
        retriever: Any, 
        dataset: List[Dict[str, Any]], 
        top_k: int = 5, 
        rerank: bool = True, 
        rerank_top_n: int = 3
    ) -> Dict[str, float]:
        """
        Runs retrieval evaluation over a dataset of test queries.
        Each dataset item format:
        {
            "query": "query string",
            "ground_truth": {
                "source_file": "file_name.pdf",
                "section": "ACTIVE INGREDIENTS"
            }
        }
        """
        total_queries = len(dataset)
        if total_queries == 0:
            return {
                "hit_rate": 0.0,
                "mrr": 0.0,
                "total_queries": 0.0
            }

        hit_rate_sum = 0.0
        mrr_sum = 0.0

        for item in dataset:
            query = item.get("query", "")
            gt = item.get("ground_truth", {})
            
            # Execute search
            retrieved = retriever.retrieve(
                query=query, 
                top_k=top_k, 
                rerank=rerank, 
                rerank_top_n=rerank_top_n
            )
            results = retrieved.get("results", [])

            # Compute metrics
            hit_rate_sum += cls.calculate_hit_rate(results, gt, top_k)
            mrr_sum += cls.calculate_reciprocal_rank(results, gt, top_k)

        metrics = {
            "hit_rate": hit_rate_sum / total_queries,
            "mrr": mrr_sum / total_queries,
            "total_queries": float(total_queries)
        }
        logger.info(f"Evaluated {total_queries} queries. Hit Rate@{top_k}: {metrics['hit_rate']:.4f}, MRR@{top_k}: {metrics['mrr']:.4f}")
        return metrics
