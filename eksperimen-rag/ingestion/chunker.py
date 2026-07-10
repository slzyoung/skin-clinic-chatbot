from typing import List, Dict, Any
from loguru import logger
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings

try:
    from docling.chunking import HierarchicalChunker
    from docling_core.types.doc import DoclingDocument
except ImportError:
    DoclingDocument = Any
    HierarchicalChunker = None
    logger.error("docling is not installed.")

class CustomChunker:
    def __init__(self, embedding_model_name: str = "BAAI/bge-m3"):
        logger.info("Initializing Custom Chunker (Docling Hierarchical + Semantic)...")
        
        # 1. Structural Chunker (Docling)
        if HierarchicalChunker:
            self.structural_chunker = HierarchicalChunker()
        else:
            self.structural_chunker = None
            
        # 2. Semantic Chunker
        try:
            logger.info(f"Loading Embedding Model for Semantic Chunking: {embedding_model_name}")
            self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)
            self.semantic_splitter = SemanticChunker(
                self.embeddings, 
                breakpoint_threshold_type="percentile"
            )
        except Exception as e:
            logger.error(f"Failed to initialize SemanticChunker: {e}")
            self.semantic_splitter = None

    def _extract_docling_headings(self, chunk: Any) -> List[str]:
        """Extracts the heading hierarchy from a docling chunk's metadata."""
        headings = []
        if hasattr(chunk, "meta") and hasattr(chunk.meta, "headings"):
            if chunk.meta.headings:
                # Docling headings might be objects or strings depending on version.
                for h in chunk.meta.headings:
                    headings.append(str(h))
        return headings

    def _extract_docling_page(self, chunk: Any) -> int:
        """Extracts the page number from a docling chunk's metadata."""
        if hasattr(chunk, "meta") and hasattr(chunk.meta, "doc_items") and chunk.meta.doc_items:
            first_item = chunk.meta.doc_items[0]
            if hasattr(first_item, "prov") and first_item.prov:
                prov_item = first_item.prov[0]
                if hasattr(prov_item, "page_no"):
                    return int(prov_item.page_no)
        return 1  # Fallback to page 1


    def chunk_document(self, doc: DoclingDocument, max_length_for_semantic: int = 500) -> List[Dict]:
        """
        Takes a DoclingDocument, chunks it using the native Document Tree (HierarchicalChunker).
        If a structural chunk is too long, it applies SemanticChunking to it.
        Groups and merges consecutive short chunks belonging to the same section and page.
        """
        if not self.structural_chunker:
            logger.error("Structural chunker unavailable.")
            return []

        logger.info("Applying Docling HierarchicalChunker to Document Tree...")
        try:
            structural_chunks = list(self.structural_chunker.chunk(doc))
        except Exception as e:
            logger.error(f"Failed to chunk document hierarchically: {e}")
            return []
            
        logger.info(f"Created {len(structural_chunks)} structural chunks from Document Tree.")
        
        KNOWN_SECTIONS = {
            "product name", "brand", "category", "description", "target skin type",
            "active ingredients", "ingredients", "benefits", "indications",
            "contraindications", "how to use", "directions", "warnings", "storage",
            "reference", "references", "product overview", "product information",
            "target patient"
        }
        
        processed_chunks = []
        current_section = "Root"
        
        # Phase 1: Clean, extract section headers, and structure all raw chunks
        for sc in structural_chunks:
            text = sc.text if hasattr(sc, "text") else str(sc)
            text_strip = text.strip()
            if not text_strip:
                continue
                
            headings = self._extract_docling_headings(sc)
            page = self._extract_docling_page(sc)
            
            # Determine chunk type by inspecting doc items (Docling returns DocChunk for everything)
            is_table = any(type(item).__name__ == "TableItem" for item in sc.meta.doc_items) if hasattr(sc, "meta") and hasattr(sc.meta, "doc_items") and sc.meta.doc_items else False
            is_picture = any(type(item).__name__ == "PictureItem" for item in sc.meta.doc_items) if hasattr(sc, "meta") and hasattr(sc.meta, "doc_items") and sc.meta.doc_items else False
            
            if is_table:
                chunk_type = "TableChunk"
            elif is_picture:
                chunk_type = "PictureChunk"
            else:
                chunk_type = "TextChunk"
            
            # If docling didn't detect headings, but we hit a known section header, update active section
            if not headings and text_strip.lower() in KNOWN_SECTIONS:
                current_section = text_strip.upper()
                # Skip emitting the header itself as a text chunk
                continue
                
            # Determine active section
            if headings:
                section = headings[-1].upper()
            else:
                section = current_section
                
            base_metadata = {
                "headings": headings,
                "section": section,
                "chunk_type": chunk_type,
                "page": page
            }
            
            processed_chunks.append({
                "text": text,
                "metadata": base_metadata
            })

        # Phase 2: Merge consecutive text chunks belonging to the same section and page
        final_chunks = []
        current_merged = None
        
        def push_chunk(merged_chunk):
            if not merged_chunk:
                return
            txt = merged_chunk["text"]
            meta = merged_chunk["metadata"]
            c_type = meta.get("chunk_type")
            
            # If the chunk is long and it's text, apply semantic splitting
            if len(txt) > max_length_for_semantic and self.semantic_splitter and c_type == "TextChunk":
                try:
                    semantic_sub_chunks = self.semantic_splitter.split_text(txt)
                    for sub_text in semantic_sub_chunks:
                        final_chunks.append({
                            "text": sub_text,
                            "metadata": meta.copy()
                        })
                except Exception as e:
                    logger.warning(f"Semantic chunking failed on a section: {e}. Using structural chunk directly.")
                    final_chunks.append({
                        "text": txt,
                        "metadata": meta
                    })
            else:
                final_chunks.append({
                    "text": txt,
                    "metadata": meta
                })

        for pc in processed_chunks:
            text = pc["text"]
            meta = pc["metadata"]
            c_type = meta.get("chunk_type")
            
            if c_type == "TextChunk":
                if current_merged:
                    same_section = current_merged["metadata"]["section"] == meta["section"]
                    same_page = current_merged["metadata"]["page"] == meta["page"]
                    not_too_long = (len(current_merged["text"]) + len(text) + 2) <= max_length_for_semantic
                    
                    if same_section and same_page and not_too_long:
                        # Merge text chunks. We separate list items with a newline.
                        current_merged["text"] += "\n" + text
                    else:
                        # Push the old merged chunk and start a new one
                        push_chunk(current_merged)
                        current_merged = {
                            "text": text,
                            "metadata": meta
                        }
                else:
                    current_merged = {
                        "text": text,
                        "metadata": meta
                    }
            else:
                # Non-text chunks (e.g. TableChunk) are not merged
                push_chunk(current_merged)
                current_merged = None
                # Push the non-text chunk directly
                final_chunks.append({
                    "text": text,
                    "metadata": meta
                })
                
        # Push any remaining merged chunk
        push_chunk(current_merged)
        
        logger.info(f"Final total chunks generated after merging and semantic splitting: {len(final_chunks)}")
        return final_chunks
