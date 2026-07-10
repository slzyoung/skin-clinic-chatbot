import os
import unittest
import tempfile
from unittest.mock import MagicMock
from core.interfaces import BaseVectorStoreAdapter
from retrieval.bm25 import BM25Index
from retrieval.reranker import Reranker
from retrieval.context_builder import PromptContextBuilder
from retrieval.retriever import HybridRetriever, reciprocal_rank_fusion
from retrieval.evaluation import RetrievalEvaluator

class TestSprint3Retrieval(unittest.TestCase):
    def setUp(self):
        # Create some dummy chunks for testing
        self.dummy_chunks = [
            {
                "text": "Salicylic Acid Niacinamide Zinc PCA",
                "metadata": {
                    "source_file": "erha_acne_gel.pdf",
                    "section": "ACTIVE INGREDIENTS",
                    "page": 1,
                    "chunk_index": 1,
                    "document_type": "brochure"
                }
            },
            {
                "text": "ERHA Acne Clear Gel is a topical dermatological formulation...",
                "metadata": {
                    "source_file": "erha_acne_gel.pdf",
                    "section": "PRODUCT OVERVIEW",
                    "page": 1,
                    "chunk_index": 2,
                    "document_type": "brochure"
                }
            },
            {
                "text": "Apply a thin layer twice daily after cleansing.",
                "metadata": {
                    "source_file": "erha_acne_gel.pdf",
                    "section": "HOW TO USE",
                    "page": 2,
                    "chunk_index": 3,
                    "document_type": "brochure"
                }
            },
            {
                "text": "Acne Peeling Treatment is a clinical treatment for mild acne.",
                "metadata": {
                    "source_file": "acne_peeling_sop.pdf",
                    "section": "TREATMENT DESCRIPTION",
                    "page": 1,
                    "chunk_index": 1,
                    "document_type": "sop"
                }
            }
        ]

    def test_bm25_index_basic_and_filtering(self):
        # 1. Test basic search and tokenization
        index = BM25Index()
        index.add_chunks(self.dummy_chunks)
        
        self.assertEqual(len(index.chunks), 4)
        
        # Test search matching "peeling"
        results = index.search("peeling", top_k=2)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["metadata"]["source_file"], "acne_peeling_sop.pdf")
        
        # Test search with metadata filtering
        filter_meta = {"document_type": "sop"}
        results_filtered = index.search("acne", top_k=5, filter_metadata=filter_meta)
        self.assertEqual(len(results_filtered), 1)
        self.assertEqual(results_filtered[0]["metadata"]["source_file"], "acne_peeling_sop.pdf")

        # Test search with negative filtering (no matches)
        results_no_match = index.search("acne", top_k=5, filter_metadata={"document_type": "faq"})
        self.assertEqual(len(results_no_match), 0)

    def test_bm25_persistence(self):
        # 2. Test persistence (saving and loading)
        index = BM25Index()
        index.add_chunks(self.dummy_chunks[:2])
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "bm25.pkl")
            index.save(file_path)
            
            # Load in a new index
            new_index = BM25Index()
            new_index.load(file_path)
            
            self.assertEqual(len(new_index.chunks), 2)
            self.assertEqual(new_index.chunks[0]["text"], self.dummy_chunks[0]["text"])

    def test_bm25_reingest_overwrite(self):
        # 3. Test overwrite on duplicate ingestion
        index = BM25Index()
        index.add_chunks(self.dummy_chunks[:2])  # 2 chunks from erha_acne_gel.pdf
        self.assertEqual(len(index.chunks), 2)
        
        # Ingest updated chunks from same file (only 1 chunk this time)
        updated_chunks = [
            {
                "text": "Updated active ingredients",
                "metadata": {
                    "source_file": "erha_acne_gel.pdf",
                    "section": "ACTIVE INGREDIENTS",
                    "page": 1,
                    "chunk_index": 1
                }
            }
        ]
        index.add_chunks(updated_chunks)
        self.assertEqual(len(index.chunks), 1)
        self.assertEqual(index.chunks[0]["text"], "Updated active ingredients")

    def test_reciprocal_rank_fusion(self):
        # 4. Test RRF Fusion
        dense_hits = [
            {"text": "A", "score": 0.9, "metadata": {"source_file": "f1.pdf", "chunk_index": 1}},
            {"text": "B", "score": 0.85, "metadata": {"source_file": "f1.pdf", "chunk_index": 2}},
            {"text": "C", "score": 0.8, "metadata": {"source_file": "f2.pdf", "chunk_index": 1}}
        ]
        sparse_hits = [
            {"text": "C", "score": 12.0, "metadata": {"source_file": "f2.pdf", "chunk_index": 1}},
            {"text": "A", "score": 8.0, "metadata": {"source_file": "f1.pdf", "chunk_index": 1}},
            {"text": "D", "score": 5.0, "metadata": {"source_file": "f2.pdf", "chunk_index": 2}}
        ]
        
        # Running RRF (default k=60)
        # Reciprocal Rank score:
        # A: Dense Rank 1 (1/61), Sparse Rank 2 (1/62). Total: 0.01639 + 0.01612 = 0.0325
        # B: Dense Rank 2 (1/62), Sparse None. Total: 0.01612
        # C: Dense Rank 3 (1/63), Sparse Rank 1 (1/61). Total: 0.01587 + 0.01639 = 0.0322
        # D: Dense None, Sparse Rank 3 (1/63). Total: 0.01587
        
        fused = reciprocal_rank_fusion(dense_hits, sparse_hits, rrf_k=60)
        self.assertEqual(len(fused), 4)
        
        # Winner should be 'A'
        self.assertEqual(fused[0]["text"], "A")
        # Runner-up should be 'C'
        self.assertEqual(fused[1]["text"], "C")

    def test_context_builder(self):
        # 5. Test context string construction
        hits = [
            {"text": "Salicylic Acid", "metadata": {"source_file": "f.pdf", "section": "INGREDIENTS", "page": 1}}
        ]
        context = PromptContextBuilder.build_context(hits)
        expected = "[1] Source: f.pdf | Product: f | Section: INGREDIENTS | Page: 1\nContent:\nSalicylic Acid"
        self.assertEqual(context, expected)

    def test_evaluation_metrics(self):
        # 6. Test Hit Rate and MRR metrics
        results = [
            {"metadata": {"source_file": "A.pdf", "section": "X"}},
            {"metadata": {"source_file": "B.pdf", "section": "Y"}},
            {"metadata": {"source_file": "C.pdf", "section": "Z"}}
        ]
        
        gt_hit = {"source_file": "B.pdf"}
        gt_miss = {"source_file": "D.pdf"}
        
        # Hit Rate @ 2 should find B.pdf
        self.assertEqual(RetrievalEvaluator.calculate_hit_rate(results, gt_hit, top_k=2), 1.0)
        self.assertEqual(RetrievalEvaluator.calculate_hit_rate(results, gt_miss, top_k=2), 0.0)
        
        # Reciprocal Rank for B.pdf is 1/2 = 0.5 (rank 2)
        self.assertEqual(RetrievalEvaluator.calculate_reciprocal_rank(results, gt_hit, top_k=2), 0.5)
        self.assertEqual(RetrievalEvaluator.calculate_reciprocal_rank(results, gt_miss, top_k=2), 0.0)

    def test_hybrid_retriever_flow(self):
        # 7. Test overall Hybrid Retriever flow with mocks
        mock_vector_store = MagicMock(spec=BaseVectorStoreAdapter)
        mock_vector_store.search.return_value = [self.dummy_chunks[1]]
        
        mock_bm25 = MagicMock(spec=BM25Index)
        mock_bm25.search.return_value = [self.dummy_chunks[0]]
        
        # Reranker mocks
        mock_reranker = MagicMock(spec=Reranker)
        chunk_with_score = self.dummy_chunks[0].copy()
        chunk_with_score["rerank_score"] = 0.95
        mock_reranker.rerank.return_value = [chunk_with_score]
        
        retriever = HybridRetriever(
            vector_store=mock_vector_store,
            bm25_index=mock_bm25,
            reranker=mock_reranker
        )
        
        response = retriever.retrieve("active ingredients", top_k=1, rerank=True, rerank_top_n=1)
        
        self.assertEqual(response["query"], "active ingredients")
        self.assertEqual(len(response["results"]), 1)
        self.assertEqual(response["results"][0]["text"], self.dummy_chunks[0]["text"])
        self.assertTrue("ACTIVE INGREDIENTS" in response["context"])

    def test_hybrid_retriever_confidence_threshold(self):
        # 8. Test Hybrid Retriever confidence threshold check
        mock_vector_store = MagicMock(spec=BaseVectorStoreAdapter)
        mock_vector_store.search.return_value = [self.dummy_chunks[1]]
        
        mock_bm25 = MagicMock(spec=BM25Index)
        mock_bm25.search.return_value = [self.dummy_chunks[0]]
        
        # Mock reranker returning a very low score
        mock_reranker = MagicMock(spec=Reranker)
        low_score_chunk = self.dummy_chunks[0].copy()
        low_score_chunk["rerank_score"] = 0.000037
        mock_reranker.rerank.return_value = [low_score_chunk]
        
        retriever = HybridRetriever(
            vector_store=mock_vector_store,
            bm25_index=mock_bm25,
            reranker=mock_reranker
        )
        
        # Using a threshold of 0.1, this low score (0.000037) should fail the check
        response = retriever.retrieve("ibu kota jakarta apa", top_k=1, rerank=True, rerank_top_n=1, confidence_threshold=0.1)
        
        self.assertEqual(len(response["results"]), 0)
        self.assertEqual(response["context"], "Maaf, saya tidak menemukan informasi.")

    def test_hybrid_retriever_multi_intent(self):
        # 9. Test multi-intent query splitting and interleaving
        mock_vector_store = MagicMock(spec=BaseVectorStoreAdapter)
        def mock_vector_search(q, top_k, filter_metadata=None):
            if "produk" in q:
                return [self.dummy_chunks[1]]
            else:
                return [self.dummy_chunks[3]]
        mock_vector_store.search.side_effect = mock_vector_search
        
        mock_bm25 = MagicMock(spec=BM25Index)
        mock_bm25.search.return_value = []
        
        mock_reranker = MagicMock(spec=Reranker)
        def mock_rerank(q, hits, top_n):
            for h in hits:
                h["rerank_score"] = 0.9
            return hits[:top_n]
        mock_reranker.rerank.side_effect = mock_rerank
        
        retriever = HybridRetriever(
            vector_store=mock_vector_store,
            bm25_index=mock_bm25,
            reranker=mock_reranker
        )
        
        response = retriever.retrieve("produk untuk bekas jerawat dan treatment untuk acne scars", top_k=2, rerank=True, rerank_top_n=2)
        
        self.assertEqual(response["query"], "produk untuk bekas jerawat dan treatment untuk acne scars")
        self.assertEqual(len(response["results"]), 2)
        
        sections = [hit["metadata"]["section"] for hit in response["results"]]
        self.assertTrue("PRODUCT OVERVIEW" in sections)
        self.assertTrue("TREATMENT DESCRIPTION" in sections)

if __name__ == "__main__":
    unittest.main()
