"""
Lightweight structure-aware summary chunker.
Zero heavy dependencies — only re + loguru.
Import: from app.rag.utils.summary_chunker import chunk_summary_markdown
"""
import re
from loguru import logger


def chunk_summary_markdown(
    summary: str,
    source_file: str = "",
    knowledge_id: str = "",
    batch_id: str = None,
    file_hash: str = "",
    title: str = "",
    doc_type: str = "GENERAL",
    categories: list = None,
    valid_from: str = None,
    valid_until: str = None,
    visibility_settings: dict = None,
    max_section_chars: int = 1200,
) -> list:
    """
    Structure-aware chunking of AI-reviewed Markdown summary.
    Splits by ## headings, extracts contextual image_url/sku/price per chunk.
    No embedding model required — instant execution.
    """
    if not summary or not summary.strip():
        return []

    categories = categories or []
    visibility_settings = visibility_settings or {
        "clinics": ["all"], "doctor_types": ["all"], "doctors": ["all"]
    }

    # Split summary into sections by ## headings
    raw_sections = re.split(r'(?=\n##\s+)', summary)
    sections = [s.strip() for s in raw_sections if s.strip() and len(s.strip()) >= 30]
    if not sections:
        sections = [summary.strip()]

    logger.info(f"Structure-aware chunking: split summary into {len(sections)} sections by ## headings.")

    # Lightweight meta builder
    def _build_meta(chunk_text, entity_name, chunk_index):
        meta = {
            "source_file": source_file,
            "entity": entity_name,
            "section": entity_name,
            "page": 1,
            "chunk_index": chunk_index,
            "knowledge_id": knowledge_id,
            "batch_id": batch_id,
            "file_hash": file_hash,
            "title": title,
            "document_type": doc_type,
            "clinics": visibility_settings.get("clinics", ["all"]),
            "doctor_types": visibility_settings.get("doctor_types", ["all"]),
            "doctors": visibility_settings.get("doctors", ["all"]),
        }
        if doc_type == "TREATMENT":
            meta["treatment_name"] = entity_name
        else:
            meta["product_name"] = entity_name
        if chunk_text:
            # Extract image_url from markdown images in this chunk's text
            img_matches = re.findall(r'!\[.*?\]\((https?://[^\s\)]+)\)', chunk_text)
            if img_matches:
                meta["image_url"] = img_matches[0]

            # Extract SKU
            sku_match = re.search(
                r'(?:-\s*\*\*SKU\*\*|\bSKU\b)\s*[:=]\s*([A-Za-z0-9\-\_]+)',
                chunk_text, re.IGNORECASE
            )
            if sku_match:
                meta["sku"] = sku_match.group(1).strip()

            # Extract price
            price_match = re.search(
                r'(?:-\s*\*\*(?:Harga|Price|Harga Normal|Harga Promo)\*\*|\b(?:Harga|Price)\b)\s*[:=]\s*([^\n\r]+)',
                chunk_text, re.IGNORECASE
            )
            if price_match:
                meta["price"] = price_match.group(1).strip()

            # Extract promo dates
            date_matches = re.findall(r'\b(20\d{2}-\d{2}-\d{2})\b', chunk_text)
            if len(date_matches) >= 2:
                meta["valid_from"] = date_matches[0]
                meta["valid_until"] = date_matches[1]
            elif len(date_matches) == 1:
                meta["valid_until"] = date_matches[0]
            else:
                if valid_from:
                    meta["valid_from"] = valid_from
                if valid_until:
                    meta["valid_until"] = valid_until

        if categories:
            str_cats = [c["name"] if isinstance(c, dict) else str(c) for c in categories]
            chunk_txt_lower = (chunk_text + " " + entity_name).lower()
            matched_cat = None

            # First: check if any category name is explicitly mentioned in chunk text
            for cat_name in str_cats:
                if cat_name.lower() in chunk_txt_lower:
                    matched_cat = cat_name
                    break

            # Second: if no direct match, check common keyword synonyms
            if not matched_cat:
                synonym_map = {
                    "acne": ["jerawat", "acne", "bha", "salicylic", "spot gel"],
                    "brightening": ["truwhite", "brightening", "cerah", "niacinamide", "vitamin c"],
                    "anti-aging": ["wrinkle", "retinol", "aging", "penuaan", "firming"],
                    "moisturizer": ["moisturizer", "pelembap", "hydrating", "hydration"],
                    "cleanser": ["facial wash", "cleansing", "cleanser", "sabun"],
                }
                for cat_name in str_cats:
                    cat_key = cat_name.lower()
                    for syn_group_key, keywords in synonym_map.items():
                        if syn_group_key in cat_key:
                            if any(kw in chunk_txt_lower for kw in keywords):
                                matched_cat = cat_name
                                break
                    if matched_cat:
                        break

            if matched_cat:
                reordered = [matched_cat] + [c for c in str_cats if c != matched_cat]
                meta["category"] = matched_cat
                meta["categories"] = reordered
            else:
                meta["category"] = str_cats[0]
                meta["categories"] = str_cats
        return meta

    chunks = []
    chunk_idx = 0

    for section_text in sections:
        h2_match = re.match(r'^##\s+(?:\d+[\.\)]\s*)?(.+)', section_text)
        entity_name = h2_match.group(1).strip() if h2_match else title

        if len(section_text) <= max_section_chars:
            chunk_idx += 1
            chunks.append({
                "text": section_text,
                "metadata": _build_meta(section_text, entity_name, chunk_idx)
            })
        else:
            # Split long sections at paragraph boundaries
            paragraphs = [p.strip() for p in section_text.split("\n\n") if p.strip()]
            running_parts = []
            running_len = 0
            for para in paragraphs:
                if running_len + len(para) > max_section_chars and running_parts:
                    chunk_idx += 1
                    sub_text = "\n\n".join(running_parts)
                    if entity_name and not sub_text.startswith("##"):
                        sub_text = f"## {entity_name}\n\n{sub_text}"
                    chunks.append({
                        "text": sub_text,
                        "metadata": _build_meta(sub_text, entity_name, chunk_idx)
                    })
                    running_parts = []
                    running_len = 0
                running_parts.append(para)
                running_len += len(para)
            if running_parts:
                chunk_idx += 1
                sub_text = "\n\n".join(running_parts)
                if entity_name and not sub_text.startswith("##"):
                    sub_text = f"## {entity_name}\n\n{sub_text}"
                chunks.append({
                    "text": sub_text,
                    "metadata": _build_meta(sub_text, entity_name, chunk_idx)
                })

    logger.info(f"Structure-aware chunking complete: {len(chunks)} chunks from {len(sections)} sections.")
    return chunks
