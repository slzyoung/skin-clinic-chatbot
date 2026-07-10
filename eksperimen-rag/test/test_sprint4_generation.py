import unittest
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any, Optional

from core.interfaces import BaseLLMAdapter
from retrieval.retriever import HybridRetriever
from generation.generator import GenerationPipeline, SYSTEM_PROMPT

class TestSprint4Generation(unittest.TestCase):
    def setUp(self):
        # Create dummy retriever candidates
        self.dummy_hits = [
            {
                "text": "Zinc PCA is an active ingredient that controls sebum.",
                "metadata": {
                    "source_file": "erha_acne_gel.docx",
                    "product_name": "ERHA Acne Clear Gel",
                    "section": "ACTIVE INGREDIENTS",
                    "page": 1,
                    "chunk_index": 1
                }
            }
        ]
        
    def test_prompt_builder_without_history(self):
        # 1. Test prompt compilation when chat history is empty
        mock_retriever = MagicMock(spec=HybridRetriever)
        mock_llm = MagicMock(spec=BaseLLMAdapter)
        pipeline = GenerationPipeline(retriever=mock_retriever, llm_adapter=mock_llm)
        
        context = "[1] Source: erha_acne_gel.docx | Product: ERHA Acne Clear Gel | Section: ACTIVE INGREDIENTS | Page: 1\nContent: Zinc PCA is..."
        query = "What does Zinc PCA do?"
        
        prompt = pipeline.build_prompt(query=query, context=context, history=[])
        
        self.assertTrue(SYSTEM_PROMPT in prompt)
        self.assertTrue(context in prompt)
        self.assertTrue("No previous conversation." in prompt)
        self.assertTrue(f"User: {query}" in prompt)

    def test_prompt_builder_with_history(self):
        # 2. Test prompt compilation with multi-turn chat history
        mock_retriever = MagicMock(spec=HybridRetriever)
        mock_llm = MagicMock(spec=BaseLLMAdapter)
        pipeline = GenerationPipeline(retriever=mock_retriever, llm_adapter=mock_llm)
        
        context = "[1] Source: erha_acne_gel.docx | Product: ERHA Acne Clear Gel | Section: ACTIVE INGREDIENTS | Page: 1\nContent: Zinc PCA is..."
        query = "Can it be used in the morning?"
        history = [
            {"role": "user", "content": "What is ERHA Acne Clear Gel?"},
            {"role": "assistant", "content": "ERHA Acne Clear Gel is a product containing Zinc PCA."}
        ]
        
        prompt = pipeline.build_prompt(query=query, context=context, history=history)
        
        self.assertTrue(SYSTEM_PROMPT in prompt)
        self.assertTrue("User: What is ERHA Acne Clear Gel?" in prompt)
        self.assertTrue("Assistant: ERHA Acne Clear Gel is a product containing Zinc PCA." in prompt)
        self.assertTrue(f"User: {query}" in prompt)

    def test_generate_answer_success(self):
        # 3. Test successful generation flow when retrieval returns valid chunks
        mock_retriever = MagicMock(spec=HybridRetriever)
        mock_retriever.retrieve.return_value = {
            "query": "What does Zinc PCA do?",
            "results": self.dummy_hits,
            "context": "[1] Source: erha_acne_gel.docx | Product: ERHA Acne Clear Gel | Section: ACTIVE INGREDIENTS\nContent: Zinc PCA..."
        }
        
        mock_llm = MagicMock(spec=BaseLLMAdapter)
        mock_llm.generate.return_value = "Zinc PCA controls sebum [1]."
        
        pipeline = GenerationPipeline(retriever=mock_retriever, llm_adapter=mock_llm)
        
        response = pipeline.generate_answer(query="What does Zinc PCA do?", history=[])
        
        self.assertEqual(response["query"], "What does Zinc PCA do?")
        self.assertEqual(response["answer"], "Zinc PCA controls sebum [1].")
        self.assertEqual(len(response["results"]), 1)
        mock_llm.generate.assert_called_once()  # Verified LLM is invoked

    def test_generate_answer_bypass_fallback(self):
        # 4. Test RAG bypass: when retriever returns fallback context, LLM is NOT called
        mock_retriever = MagicMock(spec=HybridRetriever)
        mock_retriever.retrieve.return_value = {
            "query": "ibu kota jakarta apa",
            "results": [],
            "context": "Maaf, saya tidak menemukan informasi."
        }
        
        mock_llm = MagicMock(spec=BaseLLMAdapter)
        pipeline = GenerationPipeline(retriever=mock_retriever, llm_adapter=mock_llm)
        
        response = pipeline.generate_answer(query="ibu kota jakarta apa", history=[])
        
        self.assertEqual(response["query"], "ibu kota jakarta apa")
        # Answer must be safety fallback message
        self.assertEqual(response["answer"], "Maaf, saya tidak menemukan informasi.")
        self.assertEqual(len(response["results"]), 0)
        # LLM generate MUST NOT be called to avoid hallucinations and API cost
        mock_llm.generate.assert_not_called()

if __name__ == "__main__":
    unittest.main()
