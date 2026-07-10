import os
import sys
import unittest

# Ensure the root of the project is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.adapters import AdapterFactory
from configs.settings import settings

class TestSprint2Indexing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Override settings for testing: use in-memory vector store to prevent file lock conflict with running app
        settings.qdrant_url = ":memory:"
        settings.qdrant_collection_name = "test_arya_noble_kb"
        # Reset the factory cache to ensure it initializes with the in-memory settings
        AdapterFactory._vector_store_instance = None
        cls.vector_store = AdapterFactory.get_vector_store()

    def test_indexing_and_search(self):
        # 1. Define dummy chunks
        dummy_chunks = [
            {
                "text": "ERHA Acne Clear Gel helps reduce inflammatory acne and control excess sebum production.",
                "metadata": {
                    "source_file": "test_brochure.docx",
                    "document_type": "brochure",
                    "section": "ACTIVE INGREDIENTS",
                    "page": 1,
                    "chunk_index": 1,
                    "language": "en"
                }
            },
            {
                "text": "The protocol for clinical SOP indicates dermatologists should apply a soothing cream after laser treatments.",
                "metadata": {
                    "source_file": "clinical_sop.pdf",
                    "document_type": "sop",
                    "section": "POST-TREATMENT PROTOCOL",
                    "page": 3,
                    "chunk_index": 12,
                    "language": "en"
                }
            }
        ]

        # 2. Insert chunks into Qdrant
        print("\n[Test] Inserting dummy chunks into Qdrant test collection...")
        self.vector_store.insert_chunks(dummy_chunks)

        # 3. Perform a query search
        print("[Test] Searching for 'acne treatment'...")
        results = self.vector_store.search("acne treatment", top_k=1)
        
        self.assertTrue(len(results) > 0, "Should return at least one search result.")
        best_hit = results[0]
        print(f"[Test] Best hit text: '{best_hit['text']}' (Score: {best_hit['score']})")
        
        # Verify text and metadata
        self.assertIn("Acne Clear", best_hit["text"], "The closest text should be about Acne Clear.")
        self.assertEqual(best_hit["metadata"]["source_file"], "test_brochure.docx")
        self.assertEqual(best_hit["metadata"]["section"], "ACTIVE INGREDIENTS")

        # 4. Perform another search
        print("[Test] Searching for 'laser treatment protocol'...")
        results_sop = self.vector_store.search("laser treatment protocol", top_k=1)
        self.assertTrue(len(results_sop) > 0)
        best_hit_sop = results_sop[0]
        print(f"[Test] Best hit text: '{best_hit_sop['text']}' (Score: {best_hit_sop['score']})")
        self.assertIn("laser", best_hit_sop["text"])
        self.assertEqual(best_hit_sop["metadata"]["source_file"], "clinical_sop.pdf")
        
        print("[Test] Test completed successfully!")

if __name__ == "__main__":
    unittest.main()
