import os
import re
import pickle
from typing import List, Dict, Any, Optional
from loguru import logger
from rank_bm25 import BM25Okapi

class BM25Index:
    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []       # Original chunks with text and metadata
        self.corpus: List[List[str]] = []            # Tokenized corpus for BM25
        self.bm25: Optional[BM25Okapi] = None         # rank-bm25 object

    def tokenize(self, text: str) -> List[str]:
        """Simple lowercase alphanumeric word tokenization."""
        if not text:
            return []
        return re.findall(r'\w+', text.lower())

    def add_chunks(self, new_chunks: List[Dict[str, Any]]):
        """Adds new chunks to the BM25 index, removing old chunks of the same source file first."""
        if not new_chunks:
            return

        # Try to extract the source_file name to clear older entries
        source_file = new_chunks[0].get("metadata", {}).get("source_file")
        if source_file:
            logger.debug(f"Clearing old BM25 chunks for source file: {source_file}")
            self.remove_file_chunks(source_file)

        for chunk in new_chunks:
            text = chunk.get("text", "")
            metadata = chunk.get("metadata", {})
            self.chunks.append({
                "text": text,
                "metadata": metadata
            })
            self.corpus.append(self.tokenize(text))

        # Re-initialize the BM25 model with the updated corpus
        if self.corpus:
            self.bm25 = BM25Okapi(self.corpus)
            logger.info(f"Re-initialized BM25 index. Total chunks in index: {len(self.chunks)}")
        else:
            self.bm25 = None

    def remove_file_chunks(self, source_file: str):
        """Removes all chunks associated with a given source file name."""
        indices_to_keep = [
            i for i, chunk in enumerate(self.chunks) 
            if chunk.get("metadata", {}).get("source_file") != source_file
        ]
        self.chunks = [self.chunks[i] for i in indices_to_keep]
        self.corpus = [self.corpus[i] for i in indices_to_keep]
        
        if self.corpus:
            self.bm25 = BM25Okapi(self.corpus)
        else:
            self.bm25 = None

    def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Searches the corpus using BM25.
        Applies metadata filtering before scoring if filter_metadata is provided.
        """
        if not self.chunks:
            return []

        # Step 1: Filter chunk candidates by metadata
        filtered_indices = []
        for idx, chunk in enumerate(self.chunks):
            match = True
            if filter_metadata:
                meta = chunk.get("metadata", {})
                for k, v in filter_metadata.items():
                    if meta.get(k) != v:
                        match = False
                        break
            if match:
                filtered_indices.append(idx)

        if not filtered_indices:
            logger.debug(f"No chunks matched metadata filter {filter_metadata} in BM25 index.")
            return []

        tokenized_query = self.tokenize(query)

        # Step 2: Calculate BM25 scores
        # If we have a filter, build a temporary BM25 okapi index of just the filtered candidates
        if filter_metadata and len(filtered_indices) < len(self.chunks):
            filtered_corpus = [self.corpus[i] for i in filtered_indices]
            temp_bm25 = BM25Okapi(filtered_corpus)
            scores = temp_bm25.get_scores(tokenized_query)
            
            top_temp_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            results = []
            for idx in top_temp_indices:
                score = scores[idx]
                if score == 0.0:  # Skip chunks with absolutely zero term matches
                    continue
                orig_idx = filtered_indices[idx]
                results.append({
                    "text": self.chunks[orig_idx]["text"],
                    "score": float(score),
                    "metadata": self.chunks[orig_idx]["metadata"]
                })
            return results
        else:
            # Score against global BM25 model
            if not self.bm25:
                return []
            scores = self.bm25.get_scores(tokenized_query)
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            results = []
            for idx in top_indices:
                score = scores[idx]
                if score == 0.0:  # Skip chunks with absolutely zero term matches
                    continue
                results.append({
                    "text": self.chunks[idx]["text"],
                    "score": float(score),
                    "metadata": self.chunks[idx]["metadata"]
                })
            return results

    def save(self, file_path: str):
        """Serializes and saves the index to disk using pickle."""
        try:
            parent_dir = os.path.dirname(file_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(file_path, "wb") as f:
                pickle.dump({
                    "chunks": self.chunks,
                    "corpus": self.corpus
                }, f)
            logger.info(f"Successfully saved BM25 index to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save BM25 index: {e}")

    def load(self, file_path: str):
        """Loads and deserializes the index from disk."""
        if not os.path.exists(file_path):
            logger.info(f"No existing BM25 index file found at {file_path}. Creating new.")
            return
            
        try:
            with open(file_path, "rb") as f:
                data = pickle.load(f)
                self.chunks = data.get("chunks", [])
                self.corpus = data.get("corpus", [])
            
            if self.corpus:
                self.bm25 = BM25Okapi(self.corpus)
                logger.info(f"Successfully loaded BM25 index from {file_path}. Loaded {len(self.chunks)} chunks.")
            else:
                self.bm25 = None
        except Exception as e:
            logger.error(f"Failed to load BM25 index: {e}")
