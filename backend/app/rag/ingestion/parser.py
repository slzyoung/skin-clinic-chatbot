import os
from typing import Optional
from loguru import logger
from docling.document_converter import DocumentConverter

class DocumentParser:
    def __init__(self):
        logger.info("Initializing Docling DocumentConverter...")
        # DocumentConverter automatically handles PDF, DOCX, PPTX, HTML, Markdown, etc.
        self.converter = DocumentConverter()

    def parse_file(self, file_path: str):
        """
        Parses a file using Docling and returns a DoclingDocument object.
        """
        import io
        from docling_core.types.io import DocumentStream

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
            
        logger.info(f"Parsing file with Docling (in-memory): {file_path}")
        try:
            file_name = os.path.basename(file_path)
            with open(file_path, "rb") as f:
                file_bytes = f.read()
                
            stream = io.BytesIO(file_bytes)
            doc_stream = DocumentStream(name=file_name, stream=stream)
            
            result = self.converter.convert(doc_stream)
            doc = result.document
            logger.info(f"Successfully parsed {file_path}. Extracted document structure.")
            return doc
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return None
