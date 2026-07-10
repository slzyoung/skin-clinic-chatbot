import os
import json
from loguru import logger

from typing import Optional
from core.interfaces import BaseVectorStoreAdapter
from .parser import DocumentParser
from .chunker import CustomChunker
from .metadata import MetadataEnricher
from configs.settings import settings

class IngestionPipeline:
    def __init__(self, vector_store: Optional[BaseVectorStoreAdapter] = None):
        logger.info("Initializing Ingestion Pipeline...")
        self.parser = DocumentParser()
        self.chunker = CustomChunker(embedding_model_name=settings.embedding_model_name)
        self.metadata_enricher = MetadataEnricher()
        self.vector_store = vector_store
        
        # Directory for JSON output
        self.output_dir = "data/output"
        os.makedirs(self.output_dir, exist_ok=True)

    def ingest_file(self, file_path: str) -> str:
        """
        Processes a single file using Docling, chunks it by headings + semantics, 
        saves the output to JSON, and optionally indexes it into the vector database.
        """
        logger.info(f"Starting ingestion for {file_path}")
        
        # 1. Parse (Docling)
        doc = self.parser.parse_file(file_path)
        if not doc:
            logger.error("Parsing failed. Aborting ingestion for this file.")
            return ""
            
        # 2. Custom Chunking (Heading-Based + Semantic)
        chunks = self.chunker.chunk_document(doc)
        if not chunks:
            logger.error("Chunking failed or produced no chunks.")
            return ""
            
        # 3. Metadata Extraction & Formatting
        language = self.metadata_enricher.detect_document_language(doc)
        logger.info(f"Detected document language: {language}")
        enriched_data = self.metadata_enricher.enrich_chunks(chunks, file_path, language=language)
        
        # 4. JSON Output
        filename = os.path.basename(file_path)
        output_file = os.path.join(self.output_dir, f"{filename}_parsed.json")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(enriched_data, f, indent=4, ensure_ascii=False)
            logger.info(f"Successfully saved parsed data to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save JSON output: {e}")
            return ""

        # 5. Vector DB Indexing (Optional)
        if self.vector_store:
            logger.info(f"Indexing chunks from {filename} into vector store...")
            try:
                self.vector_store.insert_chunks(enriched_data)
                logger.info(f"Successfully indexed chunks from {filename} into vector store.")
            except Exception as e:
                logger.error(f"Failed to index chunks into vector store: {e}")

        return output_file

    def ingest_directory(self, directory_path: str):
        """Processes a directory and ingests all files."""
        for root, _, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                self.ingest_file(file_path)

if __name__ == "__main__":
    # CLI for testing Ingestion & Indexing
    import sys
    if len(sys.argv) > 1:
        # Check if --index flag is passed
        should_index = "--index" in sys.argv
        if should_index:
            sys.argv.remove("--index")
            
        if len(sys.argv) > 1:
            target = sys.argv[1]
        else:
            print("Usage: python -m ingestion.pipeline <path_to_file_or_directory> [--index]")
            sys.exit(0)
            
        vector_store = None
        if should_index:
            from core.adapters import AdapterFactory
            vector_store = AdapterFactory.get_vector_store()
            
        pipeline = IngestionPipeline(vector_store=vector_store)
        if os.path.isfile(target):
            pipeline.ingest_file(target)
        elif os.path.isdir(target):
            pipeline.ingest_directory(target)
        else:
            print("Invalid path provided.")
    else:
        print("Usage: python -m ingestion.pipeline <path_to_file_or_directory> [--index]")
