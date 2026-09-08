"""
Dedicated CRUD Service for General Knowledge Assistant (Arya Noble).

This service executes deterministic, validated database operations (READ metadata, EDIT, DELETE)
on approved Knowledge Base documents across:
- Local JSON storage (data/output/)
- PostgreSQL (Knowledge table)
- PGVector (arya_noble_kb table)
- MinIO Object Storage (approved & canonical buckets)
- BM25 Index (bm25_index.pkl)

Architectural Principle:
The LLM is NOT the primary decider of CRUD operations.
The AI Orchestrator validates requests against this service, displays a two-step preview,
and upon explicit Admin confirmation, delegates mutation to this Dedicated Service.
"""

import os
import re
import json
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
from loguru import logger

from app.rag.config import settings
from app.rag.services.rag_retriever import parse_date_safely


def resolve_approved_file(knowledge_id: str, output_dir: str = "data/output") -> Optional[str]:
    """Resolves the physical JSON file path for an approved document."""
    if not knowledge_id:
        return None
    k_id = str(knowledge_id).strip()

    # Try exact paths first
    direct_paths = [
        os.path.join(output_dir, f"{k_id}.json"),
        os.path.join(output_dir, f"{k_id}_parsed.json"),
        os.path.join("backend", output_dir, f"{k_id}.json"),
        os.path.join("backend", output_dir, f"{k_id}_parsed.json"),
    ]
    for p in direct_paths:
        if os.path.exists(p):
            return p

    # Search in directory
    for folder in [output_dir, os.path.join("backend", output_dir)]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                if f.endswith(".json") and f != "bm25_index.pkl":
                    f_path = os.path.join(folder, f)
                    try:
                        with open(f_path, "r", encoding="utf-8") as fp:
                            doc = json.load(fp)
                        if isinstance(doc, dict):
                            doc_id = str(doc.get("knowledge_id", ""))
                            doc_title = str(doc.get("title", ""))
                            file_name = str(doc.get("file_name", ""))
                            f_no_ext = f.replace(".json", "").replace("_parsed", "")
                            if k_id.lower() in (doc_id.lower(), doc_title.lower(), file_name.lower(), f_no_ext.lower(), f.lower()):
                                return f_path
                    except Exception as err:
                        logger.debug(f"[DedicatedService] Error scanning file {f}: {err}")

    return None


class GeneralKnowledgeService:
    """Dedicated service for performing safe, item-level CRUD operations on approved KB data."""

    @staticmethod
    async def find_all_target_documents_and_item(
        query: str, output_dir: str = "data/output", db: Optional[Any] = None
    ) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
        """
        Scans approved documents to identify the matching target entity/item name and
        ALL documents in the Knowledge Base that contain, define, or are affected by it.
        Returns (target_item_name, list_of_matched_docs) sorted by priority:
        1. Explicit UUID matches
        2. Dedicated documents (where doc_title or file_name matches target entity)
        3. Catalog documents (where target entity is a section heading)
        4. Content mentions
        """
        q_lower = query.lower()

        # Check if an explicit UUID is present in query
        uuid_matches = re.findall(
            r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',
            query
        )
        explicit_uuid = uuid_matches[0].lower() if uuid_matches else None

        # Extract explicit command structure: <action> <item> (dari|pada|di|dalam) <container>
        container_candidate = None
        explicit_item_candidate = None
        cmd_match = re.search(
            r'\b(?:hapus|delete|hilangkan|remove|buang|bersihkan|wipe|erase|ubah|ganti|edit|tukar|salin|update|perbarui|revisi)\s+(?:bagian|item|produk|tahapan|parameter|indikator|baris|kolom|tabel)?\s*["\'“]?([^"\'”\n]+?)["\'”?]?\s+(?:dari|pada|di|dalam)\s+["\'“]?([^"\'”\n]+)["\'”]?',
            query,
            re.IGNORECASE
        )
        if cmd_match:
            explicit_item_candidate = cmd_match.group(1).strip()
            container_candidate = cmd_match.group(2).strip()
        else:
            quote_match = re.search(r'["\'“]([^"\'”]+)["\'”]', query)
            if quote_match:
                explicit_item_candidate = quote_match.group(1).strip()
            else:
                keyword_match = re.search(
                    r'\b(?:bagian|item|produk|tahapan|parameter|indikator|baris|kolom|tabel)\s+([a-zA-Z0-9\s&+\-_/]+?)(?:\s+(?:pada|di|dari|dalam|menjadi|ke|sebagai)\b|$)',
                    query,
                    re.IGNORECASE
                )
                if keyword_match:
                    candidate = keyword_match.group(1).strip()
                    if len(candidate) > 2 and candidate.lower() not in ("dokumen", "doc", "kb", "knowledge"):
                        explicit_item_candidate = candidate

        # Clean core entity extraction for edit/update patterns:
        # e.g.: "edit ukuran ERHA Acneact Gentle Acne Moisturizer ke 40 g"
        if not explicit_item_candidate:
            core = re.sub(
                r'^\s*(?:tolong\s+|mohon\s+|coba\s+)?(?:ubah|ganti|edit|tukar|salin|update|perbarui|revisi|hapus|delete|hilangkan|remove|buang|bersihkan)\s+',
                '',
                query,
                flags=re.IGNORECASE
            )
            # Strip trailing target value (ke 40 g / jadi 40 g / dengan 50000 / menjadi 50000)
            val_m = re.search(r'\b(?:menjadi|jadi|ke|sebagai|dengan|sebesar|berupa|=)\s+[`"\'“]?([^\n\r`"\'”]+)[\'"”`]?$', core, re.IGNORECASE)
            if val_m:
                core = core[:val_m.start()].strip()
            else:
                # Also strip raw trailing value without transition word (e.g. "Facial Wash 40 g" -> "Facial Wash")
                raw_val_m = re.search(r'\b(\d+(?:\.\d+)?\s*(?:g|gram|ml|l|kg|oz)\b|(?:Rp\.?\s*)?\d[\d\.\,]+)$', core, re.IGNORECASE)
                if raw_val_m:
                    core = core[:raw_val_m.start()].strip()

            # Strip leading field words
            field_words = [
                'ukuran', 'size', 'berat', 'volume', 'netto',
                'harga', 'price', 'biaya', 'tarif',
                'sku', 'kode_sku', 'kode',
                'nama_produk', 'nama', 'judul',
                'kategori', 'category',
                'deskripsi', 'description', 'keterangan',
                'indikasi', 'cara_pakai', 'dosis',
                'kandungan', 'komposisi', 'ingredients', 'key ingredients', 'bahan'
            ]
            for fw in field_words:
                core = re.sub(rf'\b{fw}\b', '', core, flags=re.IGNORECASE).strip()

            core = re.sub(r'^\s*(?:pada|di|dari|dalam|untuk|bagian|item|produk|treatment|dokumen)\s+', '', core, flags=re.IGNORECASE).strip()
            core = re.sub(r'\s*(?:pada|di|dari|dalam|untuk|bagian|item|produk|treatment|dokumen)\s*$', '', core, flags=re.IGNORECASE).strip()
            if len(core) > 2 and not re.match(r'^[0-9a-fA-F\-]{10,}$', core):
                explicit_item_candidate = core

        search_folders = [output_dir, os.path.join("backend", output_dir)]
        seen_doc_ids = set()
        matched_docs = []
        resolved_entity_name = explicit_item_candidate

        for folder in search_folders:
            if not os.path.exists(folder):
                continue
            for f in os.listdir(folder):
                if not f.endswith(".json") or f == "bm25_index.pkl":
                    continue
                f_path = os.path.join(folder, f)
                try:
                    with open(f_path, "r", encoding="utf-8") as fp:
                        doc = json.load(fp)
                    if not isinstance(doc, dict):
                        continue

                    doc_id = str(doc.get("knowledge_id") or doc.get("id") or f.replace(".json", "").replace("_parsed", ""))
                    if doc_id in seen_doc_ids:
                        continue

                    doc_title = str(doc.get("title") or doc.get("file_name") or "")
                    file_name = str(doc.get("file_name") or "")
                    summary = str(doc.get("summary") or "")

                    # Collect candidate items/sections from this document
                    doc_candidates = []
                    for k in ["product_name", "title", "section", "heading", "treatment", "treatment_name", "category"]:
                        v = doc.get(k)
                        if v and isinstance(v, str) and len(v.strip()) > 2 and v.strip().lower() not in ("general", "unknown"):
                            doc_candidates.append(v.strip())

                    # Headings in summary
                    for h in re.findall(r'^#{1,4}\s+([^\n\r]+)', summary, re.MULTILINE):
                        h_clean = re.sub(r'[\*\_]', '', h).strip()
                        if len(h_clean) > 2:
                            doc_candidates.append(h_clean)

                    # Chunks metadata
                    for chunk in doc.get("chunks", []):
                        if not isinstance(chunk, dict):
                            continue
                        meta = chunk.get("metadata", {})
                        for k in ["product_name", "title", "section", "heading", "treatment", "treatment_name"]:
                            v = meta.get(k)
                            if v and isinstance(v, str) and len(v.strip()) > 2 and v.strip().lower() not in ("general", "unknown"):
                                doc_candidates.append(v.strip())

                    # Clean candidates
                    unique_candidates = []
                    seen_c = set()
                    for c in doc_candidates:
                        if c.lower() not in seen_c:
                            seen_c.add(c.lower())
                            unique_candidates.append(c)
                    unique_candidates.sort(key=len, reverse=True)

                    # Calculate match score
                    score = 0
                    match_type = "mention"
                    matched_item_for_doc = None

                    # 1. Explicit UUID in prompt matches this doc
                    if explicit_uuid and (explicit_uuid == doc_id.lower()):
                        score += 1000
                        match_type = "explicit_uuid"

                    # 2. Check explicit item candidate against document title / filename
                    if explicit_item_candidate:
                        cand_low = explicit_item_candidate.lower()
                        # Exact or strong title match -> Dedicated document!
                        if cand_low == doc_title.lower() or cand_low in doc_title.lower() or cand_low in file_name.lower().replace("_", " "):
                            score += 500 + len(doc_title)
                            match_type = "dedicated_document"
                            matched_item_for_doc = explicit_item_candidate
                            if not resolved_entity_name or len(doc_title) > len(resolved_entity_name):
                                resolved_entity_name = doc_title

                        # Section match in catalog document
                        for c in unique_candidates:
                            if cand_low == c.lower() or cand_low in c.lower() or c.lower() in cand_low:
                                if match_type != "dedicated_document":
                                    score += 200 + len(c)
                                    match_type = "section"
                                matched_item_for_doc = c
                                if not resolved_entity_name:
                                    resolved_entity_name = c
                                break

                    # 3. Check query text against document title or unique candidates
                    if score == 0:
                        if doc_title and len(doc_title) > 3 and doc_title.lower() in q_lower:
                            score += 300 + len(doc_title)
                            match_type = "title_in_query"
                            matched_item_for_doc = doc_title
                            if not resolved_entity_name:
                                resolved_entity_name = doc_title
                        else:
                            for c in unique_candidates:
                                if len(c) > 3 and c.lower() in q_lower:
                                    score += 150 + len(c)
                                    match_type = "item_in_query"
                                    matched_item_for_doc = c
                                    if not resolved_entity_name or len(c) > len(resolved_entity_name):
                                        resolved_entity_name = c
                                    break

                    if score > 0:
                        seen_doc_ids.add(doc_id)
                        doc_copy = dict(doc)
                        doc_copy["_matched_context_label"] = matched_item_for_doc or resolved_entity_name or doc_title
                        matched_docs.append({
                            "knowledge_id": doc_id,
                            "title": doc_title,
                            "file_name": file_name,
                            "batch_id": doc.get("batch_id") or doc.get("metadata", {}).get("batch_id"),
                            "score": score,
                            "match_type": match_type,
                            "target_item": matched_item_for_doc or resolved_entity_name,
                            "doc_data": doc_copy
                        })

                except Exception as e:
                    logger.debug(f"[DedicatedService] scan error {f}: {e}")

        # DB Hydration fallback: scan active PostgreSQL Knowledge records if disk scan yields no matches
        if not matched_docs:
            try:
                from app.models.knowledge import Knowledge
                from sqlalchemy import select

                async def _scan_db(session):
                    stmt = select(Knowledge).where(Knowledge.deleted_at.is_(None))
                    res = await session.execute(stmt)
                    return res.scalars().all()

                if db:
                    k_rows = await _scan_db(db)
                else:
                    from app.core.database import AsyncSessionLocal
                    async with AsyncSessionLocal() as session:
                        k_rows = await _scan_db(session)

                for k_obj in k_rows:
                    doc_id = str(k_obj.id)
                    if doc_id in seen_doc_ids:
                        continue
                    doc_title = str(k_obj.title or k_obj.file_name or doc_id)
                    file_name = str(k_obj.file_name or "")
                    summary = str(k_obj.ai_summary or "")
                    m_dict = dict(k_obj.metadata_) if isinstance(k_obj.metadata_, dict) else {}
                    doc = {
                        "knowledge_id": doc_id,
                        "batch_id": m_dict.get("batch_id"),
                        "file_name": file_name,
                        "title": doc_title,
                        "summary": summary,
                        "chunks": m_dict.get("chunks", []),
                        "images": m_dict.get("images", []),
                        "image_urls": m_dict.get("image_urls", []),
                        "categories": m_dict.get("categories", []),
                        "visibility_settings": m_dict.get("visibility_settings", {})
                    }

                    doc_candidates = [doc_title]
                    for h in re.findall(r'^#{1,4}\s+([^\n\r]+)', summary, re.MULTILINE):
                        h_clean = re.sub(r'[\*\_]', '', h).strip()
                        if len(h_clean) > 2:
                            doc_candidates.append(h_clean)

                    score = 0
                    match_type = "mention"
                    matched_item_for_doc = None

                    if explicit_uuid and (explicit_uuid == doc_id.lower()):
                        score += 1000
                        match_type = "explicit_uuid"

                    if explicit_item_candidate:
                        cand_low = explicit_item_candidate.lower()
                        if cand_low == doc_title.lower() or cand_low in doc_title.lower() or cand_low in file_name.lower().replace("_", " "):
                            score += 500 + len(doc_title)
                            match_type = "dedicated_document"
                            matched_item_for_doc = explicit_item_candidate
                            if not resolved_entity_name:
                                resolved_entity_name = doc_title

                        for c in doc_candidates:
                            if cand_low == c.lower() or cand_low in c.lower() or c.lower() in cand_low:
                                if match_type != "dedicated_document":
                                    score += 200 + len(c)
                                    match_type = "section"
                                matched_item_for_doc = c
                                if not resolved_entity_name:
                                    resolved_entity_name = c
                                break

                    if score == 0:
                        if doc_title and len(doc_title) > 3 and doc_title.lower() in q_lower:
                            score += 300 + len(doc_title)
                            match_type = "title_in_query"
                            matched_item_for_doc = doc_title
                            if not resolved_entity_name:
                                resolved_entity_name = doc_title
                        else:
                            for c in doc_candidates:
                                if len(c) > 3 and c.lower() in q_lower:
                                    score += 150 + len(c)
                                    match_type = "item_in_query"
                                    matched_item_for_doc = c
                                    if not resolved_entity_name:
                                        resolved_entity_name = c
                                    break

                    if score > 0:
                        seen_doc_ids.add(doc_id)
                        doc_copy = dict(doc)
                        doc_copy["_matched_context_label"] = matched_item_for_doc or resolved_entity_name or doc_title
                        matched_docs.append({
                            "knowledge_id": doc_id,
                            "title": doc_title,
                            "file_name": file_name,
                            "batch_id": doc.get("batch_id"),
                            "score": score,
                            "match_type": match_type,
                            "target_item": matched_item_for_doc or resolved_entity_name,
                            "doc_data": doc_copy
                        })
            except Exception as db_scan_err:
                logger.debug(f"[GeneralKnowledgeService] DB scan fallback note: {db_scan_err}")

        if not matched_docs:
            return None

        # Sort: highest score first (dedicated document first, then catalog sections)
        matched_docs.sort(key=lambda x: x["score"], reverse=True)
        return (resolved_entity_name, matched_docs)

    @staticmethod
    async def find_target_document_and_item(
        query: str, output_dir: str = "data/output", db: Optional[Any] = None
    ) -> Optional[Tuple[str, Optional[str], Dict[str, Any]]]:
        """
        Scans approved documents to identify the matching document ID and target item/entity/section name.
        Returns the highest-priority matching document (knowledge_id, target_item_name, doc_data).
        """
        res = await GeneralKnowledgeService.find_all_target_documents_and_item(query, output_dir, db=db)
        if not res:
            return None
        target_item, matched_docs = res
        if not matched_docs:
            return None
        top_doc = matched_docs[0]
        return (top_doc["knowledge_id"], target_item, top_doc["doc_data"])

    @staticmethod
    def validate_target_entity(knowledge_id: str, target_item: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validates that the target document and (if specified) target item/entity exist in approved KB.
        Returns (is_valid, error_message, doc_data).
        """
        approved_file = resolve_approved_file(knowledge_id)
        if not approved_file:
            return False, f"Dokumen dengan ID/Nama '{knowledge_id}' tidak ditemukan dalam Basis Data Pengetahuan ERHA.", None

        try:
            with open(approved_file, "r", encoding="utf-8") as f:
                doc_data = json.load(f)

            if target_item and target_item.strip():
                item_lower = target_item.strip().lower()
                doc_summary = doc_data.get("summary", "").lower()
                chunks = doc_data.get("chunks", [])
                item_found = item_lower in doc_summary or any(
                    item_lower in str(ch.get("text", "")).lower()
                    or item_lower in str(ch.get("metadata", {}).get("product_name", "")).lower()
                    or item_lower in str(ch.get("metadata", {}).get("section", "")).lower()
                    or item_lower in str(ch.get("metadata", {}).get("heading", "")).lower()
                    or item_lower in str(ch.get("metadata", {}).get("title", "")).lower()
                    for ch in chunks if isinstance(ch, dict)
                )
                if not item_found:
                    return False, f"Item/bagian '{target_item}' tidak ditemukan di dalam dokumen '{knowledge_id}'.", doc_data

            return True, None, doc_data
        except Exception as e:
            return False, f"Gagal membaca data dokumen: {str(e)}", None

    @staticmethod
    async def sync_knowledge_db(
        knowledge_id: str,
        existing_doc: Optional[Dict[str, Any]] = None,
        deleted: bool = False,
        db: Optional[Any] = None
    ):
        """Synchronously updates the PostgreSQL Knowledge record and commits."""
        from app.models.knowledge import Knowledge
        from sqlalchemy import select
        import uuid as _uuid

        async def _do_sync(session):
            k_obj = None
            try:
                kid_uuid = _uuid.UUID(str(knowledge_id).strip())
                stmt = select(Knowledge).where(Knowledge.id == kid_uuid)
                res = await session.execute(stmt)
                k_obj = res.scalar_one_or_none()
            except Exception:
                pass

            if not k_obj:
                stmt2 = select(Knowledge).where(
                    Knowledge.deleted_at.is_(None),
                    Knowledge.metadata_.op("->>")("document_id") == str(knowledge_id)
                )
                res2 = await session.execute(stmt2)
                k_obj = res2.scalar_one_or_none()

            if not k_obj:
                stmt3 = select(Knowledge).where(
                    Knowledge.deleted_at.is_(None),
                    Knowledge.file_name == str(knowledge_id)
                )
                res3 = await session.execute(stmt3)
                k_obj = res3.scalar_one_or_none()

            if k_obj:
                if deleted:
                    k_obj.deleted_at = datetime.now(timezone.utc)
                    logger.info(f"[DedicatedService] Marked Knowledge '{k_obj.id}' as deleted_at={k_obj.deleted_at}")
                elif existing_doc:
                    k_obj.title = existing_doc.get("title", k_obj.title)
                    k_obj.ai_summary = existing_doc.get("summary", k_obj.ai_summary)
                    meta = dict(k_obj.metadata_) if isinstance(k_obj.metadata_, dict) else {}
                    meta.update(existing_doc.get("metadata", {}))
                    meta["chunks"] = existing_doc.get("chunks", [])
                    meta["summary"] = existing_doc.get("summary")
                    if existing_doc.get("batch_summary"):
                        meta["batch_summary"] = existing_doc.get("batch_summary")
                    if "staging_history" in existing_doc:
                        meta["staging_history"] = existing_doc["staging_history"]
                    if "edit_history" in existing_doc:
                        meta["edit_history"] = existing_doc["edit_history"]
                    k_obj.metadata_ = meta
                    logger.info(f"[DedicatedService] Updated Knowledge '{k_obj.id}' metadata & summary in DB")
                await session.commit()

        try:
            if db:
                await _do_sync(db)
            else:
                from app.core.database import AsyncSessionLocal
                async with AsyncSessionLocal() as session:
                    await _do_sync(session)
        except Exception as e:
            logger.error(f"[DedicatedService] Failed to sync Knowledge DB record '{knowledge_id}': {e}")

    @staticmethod
    async def apply_edit(
        knowledge_id: str,
        field: str,
        new_value: str,
        vector_store=None,
        bm25_index=None,
        pipeline=None,
        target_item: Optional[str] = None,
        db=None
    ) -> Dict[str, Any]:
        """
        Applies a surgical, item-level edit to an approved KB document.
        Updates local JSON, PostgreSQL, PGVector, MinIO, and BM25 index.
        """
        approved_file = resolve_approved_file(knowledge_id)
        if not approved_file:
            return {"success": False, "error": f"Dokumen dengan ID/Nama '{knowledge_id}' tidak ditemukan di approved KB."}

        try:
            with open(approved_file, "r", encoding="utf-8") as f:
                existing_doc = json.load(f)

            doc_kid = str(existing_doc.get("knowledge_id") or knowledge_id)
            old_value = None
            clean_field = (field or "").strip().lower()
            formatted_val = str(new_value).strip()

            # Prevent chatbot conversational response from polluting summary
            conv_phrases = ["berhasil diubah", "berhasil diperbarui", "telah diubah", "telah diperbarui", "berhasil diterapkan", "berhasil dihapus"]
            if clean_field in ("summary", "deskripsi", "ringkasan") and any(p in formatted_val.lower() for p in conv_phrases):
                logger.warning(f"[DedicatedService] Rejected chatbot conversational response as summary value: {formatted_val}")
                return {"success": False, "error": "Value summary tidak boleh berupa kalimat konfirmasi percakapan chatbot."}

            # Update document root ONLY if no target_item is specified (item-level isolation)
            if not target_item:
                if clean_field in ("price", "harga", "biaya"):
                    old_value = existing_doc.get("price") or existing_doc.get("metadata", {}).get("price")
                    existing_doc["price"] = formatted_val
                    if "metadata" not in existing_doc or not isinstance(existing_doc["metadata"], dict):
                        existing_doc["metadata"] = {}
                    existing_doc["metadata"]["price"] = formatted_val
                elif clean_field in ("title", "nama", "nama_produk"):
                    old_value = existing_doc.get("title", existing_doc.get("file_name", ""))
                    existing_doc["title"] = formatted_val
                elif clean_field in ("valid_until", "expiry_date", "end_date", "periode", "masa_berlaku"):
                    old_value = existing_doc.get("valid_until")
                    existing_doc["valid_until"] = formatted_val
                elif clean_field in ("categories", "kategori"):
                    old_value = existing_doc.get("categories", [])
                    try:
                        parsed_cats = json.loads(new_value) if isinstance(new_value, str) else new_value
                        existing_doc["categories"] = parsed_cats if isinstance(parsed_cats, list) else [str(parsed_cats)]
                    except Exception:
                        existing_doc["categories"] = [formatted_val]
                else:
                    old_value = existing_doc.get(clean_field) or existing_doc.get("metadata", {}).get(clean_field)
                    existing_doc[clean_field] = formatted_val
                    if "metadata" not in existing_doc or not isinstance(existing_doc["metadata"], dict):
                        existing_doc["metadata"] = {}
                    existing_doc["metadata"][clean_field] = formatted_val

            # Surgically update summary and chunks
            chunks = existing_doc.get("chunks", [])
            clean_item_name = re.sub(r'^\*+|\*+$|^_+|_+$|^#+\s*', '', target_item.strip()).strip() if target_item else ""
            target_item_lower = clean_item_name.lower() if clean_item_name else None

            # 1. Update summary for target item
            curr_summary = existing_doc.get("summary", "")
            if curr_summary:
                doc_title = str(existing_doc.get("title") or existing_doc.get("file_name") or "")
                is_dedicated = bool(target_item and (target_item_lower in doc_title.lower() or doc_title.lower() in target_item_lower))

                # Field synonym regex helper
                field_synonyms = [re.escape(clean_field)]
                if clean_field in ("ukuran", "size", "netto", "berat", "weight", "volume"):
                    field_synonyms = ["ukuran", "size", "netto", "berat", "weight", "volume"]
                elif clean_field in ("harga", "price", "biaya", "tarif"):
                    field_synonyms = ["harga", "price", "biaya", "tarif"]
                elif clean_field in ("sku", "kode", "kode_sku"):
                    field_synonyms = ["sku", "kode", "kode_sku"]
                elif clean_field in ("kategori", "category"):
                    field_synonyms = ["kategori", "category"]
                elif clean_field in ("deskripsi", "description", "keterangan"):
                    field_synonyms = ["deskripsi", "description", "keterangan"]
                elif clean_field in ("indikasi", "indication"):
                    field_synonyms = ["indikasi", "indication", "indications"]
                elif clean_field in ("cara_pakai", "aturan_pakai", "instruksi", "penggunaan", "dosis"):
                    field_synonyms = ["cara_pakai", "aturan_pakai", "instruksi", "penggunaan", "dosis", "cara pakai", "aturan pakai"]
                elif clean_field in ("kandungan", "komposisi", "ingredients", "key_ingredients", "key ingredients", "ingridients", "bahan"):
                    field_synonyms = ["kandungan", "komposisi", "ingredients", "key ingredients", "key_ingredients", "ingridients", "bahan"]

                syn_regex = "|".join(field_synonyms)
                bullet_attr_pattern = re.compile(
                    r'(^[|\-\*]\s*\*+(?:' + syn_regex + r')[:\*\s]+|^[|\-\*]\s*(?:' + syn_regex + r')[:\s]+)[^\n\r]+',
                    re.MULTILINE | re.IGNORECASE
                )

                if is_dedicated:
                    # In a dedicated document, the entire document is about target_item
                    if bullet_attr_pattern.search(curr_summary):
                        curr_summary = bullet_attr_pattern.sub(rf'\g<1>{formatted_val}', curr_summary)
                    else:
                        if "## Informasi Produk" in curr_summary:
                            curr_summary = re.sub(
                                r'(## Informasi Produk[^\n]*\n(?:[^\n]*\n)*?)(?=\n##|\Z)',
                                rf'\g<1>- **{field.capitalize()}:** {formatted_val}\n',
                                curr_summary
                            )
                        else:
                            curr_summary = curr_summary.rstrip() + f"\n- **{field.capitalize()}:** {formatted_val}\n"
                    existing_doc["summary"] = curr_summary

                elif target_item and target_item_lower:
                    escaped_item = re.escape(target_item.strip())
                    # Heading section match: ## target_item ... until next same-level or higher heading
                    item_section_pattern = re.compile(
                        r'(#{1,4}\s*[^\n]*' + escaped_item + r'[^\n]*\n(?:(?!^#{1,2}\s)[^\n]*\n?)*)',
                        re.MULTILINE | re.IGNORECASE
                    )
                    match = item_section_pattern.search(curr_summary)
                    if match:
                        section_text = match.group(1)
                        if clean_field in ("price", "harga", "biaya"):
                            clean_num = re.sub(r'^(?:rp\.?\s*)', '', formatted_val, flags=re.IGNORECASE).strip()
                            price_pat = re.compile(
                                r'(^[|\-\*]\s*\*+(?:harga|price|biaya|tarif)[:\*\s]+|^[|\-\*]\s*(?:harga|price|biaya|tarif)[:\s]+)(?:Rp\.?\s*)?[^\n\r]+',
                                re.MULTILINE | re.IGNORECASE
                            )
                            if price_pat.search(section_text):
                                section_text = price_pat.sub(rf'\g<1>Rp {clean_num}', section_text)
                            else:
                                section_text = section_text.rstrip() + f"\n- **Harga**: Rp {clean_num}\n\n"
                        elif clean_field in ("sku", "kode", "kode_sku"):
                            sku_pat = re.compile(
                                r'(^[|\-\*]\s*\*+(?:sku|kode)[:\*\s]+|^[|\-\*]\s*(?:sku|kode)[:\s]+)[^\n\r]+',
                                re.MULTILINE | re.IGNORECASE
                            )
                            if sku_pat.search(section_text):
                                section_text = sku_pat.sub(rf'\g<1>{formatted_val}', section_text)
                            else:
                                section_text = section_text.rstrip() + f"\n- **SKU**: {formatted_val}\n\n"
                        else:
                            if bullet_attr_pattern.search(section_text):
                                section_text = bullet_attr_pattern.sub(rf'\g<1>{formatted_val}', section_text)
                            else:
                                section_text = section_text.rstrip() + f"\n- **{field.capitalize()}**: {formatted_val}\n\n"

                        curr_summary = curr_summary[:match.start()] + section_text + curr_summary[match.end():]
                        existing_doc["summary"] = curr_summary

                    # 1B. Table row match: | target_item | ... |
                    table_row_pattern = re.compile(rf'(^\s*\|\s*[^\n|]*{escaped_item}[^\n|]*\|)([^\n]+)$', re.MULTILINE | re.IGNORECASE)
                    if table_row_pattern.search(curr_summary):
                        curr_summary = table_row_pattern.sub(rf'\g<1> {formatted_val} |', curr_summary)
                        existing_doc["summary"] = curr_summary

                    # 1C. Bullet key match: - **target_item**: ...
                    bullet_key_pattern = re.compile(rf'(^[|\-\*]\s*\*\*[^\*\n:]*{escaped_item}[^\*\n:]*\*\*\s*:\s*)[^\n]+', re.MULTILINE | re.IGNORECASE)
                    if bullet_key_pattern.search(curr_summary):
                        curr_summary = bullet_key_pattern.sub(rf'\g<1>{formatted_val}', curr_summary)
                        existing_doc["summary"] = curr_summary

            # 2. Update matching chunks
            for chunk in chunks:
                if not isinstance(chunk, dict):
                    continue
                if "metadata" not in chunk:
                    chunk["metadata"] = {}
                chunk["metadata"]["knowledge_id"] = doc_kid

                chunk_text = chunk.get("text", "")
                chunk_text_lower = chunk_text.lower()

                # If target_item is specified, skip chunks that do not belong to this item
                if target_item_lower and target_item_lower not in chunk_text_lower:
                    continue

                # Apply field metadata to matching chunk
                chunk["metadata"][clean_field] = formatted_val

                # Update chunk text
                escaped_item = re.escape(target_item.strip()) if target_item else ""
                if clean_field in ("price", "harga", "biaya"):
                    clean_num = re.sub(r'^(?:rp\.?\s*)', '', formatted_val, flags=re.IGNORECASE).strip()
                    price_pattern = re.compile(r'(^[|\-\*]\s*\*+(?:harga|price|biaya|tarif)[:\*\s]+|^[|\-\*]\s*(?:harga|price|biaya|tarif)[:\s]+)(?:Rp\.?\s*)?[^\n\r]+', re.MULTILINE | re.IGNORECASE)
                    if price_pattern.search(chunk_text):
                        chunk["text"] = price_pattern.sub(rf'\g<1>Rp {clean_num}', chunk_text)
                    elif not re.match(r'^#{1,3}\s+[^\n]+$', chunk_text.strip()):
                        chunk["text"] = chunk_text.strip() + f"\n- **Harga**: Rp {clean_num}"
                elif clean_field in ("sku", "kode_sku", "kode"):
                    sku_pattern = re.compile(r'(^[|\-\*]\s*\*+(?:sku|kode)[:\*\s]+|^[|\-\*]\s*(?:sku|kode)[:\s]+)[^\n\r]+', re.MULTILINE | re.IGNORECASE)
                    if sku_pattern.search(chunk_text):
                        chunk["text"] = sku_pattern.sub(rf'\g<1>{formatted_val}', chunk_text)
                    elif not re.match(r'^#{1,3}\s+[^\n]+$', chunk_text.strip()):
                        chunk["text"] = chunk_text.strip() + f"\n- **SKU**: {formatted_val}"
                elif escaped_item:
                    # Check table row in chunk
                    t_pattern = re.compile(rf'(^\s*\|\s*[^\n|]*{escaped_item}[^\n|]*\|)([^\n]+)$', re.MULTILINE | re.IGNORECASE)
                    if t_pattern.search(chunk_text):
                        chunk["text"] = t_pattern.sub(rf'\g<1> {formatted_val} |', chunk_text)
                    else:
                        b_pattern = re.compile(rf'(^[|\-\*]\s*\*\*[^\*\n:]*{escaped_item}[^\*\n:]*\*\*\s*:\s*)[^\n]+', re.MULTILINE | re.IGNORECASE)
                        if b_pattern.search(chunk_text):
                            chunk["text"] = b_pattern.sub(rf'\g<1>{formatted_val}', chunk_text)
                        elif bullet_attr_pattern.search(chunk_text):
                            chunk["text"] = bullet_attr_pattern.sub(rf'\g<1>{formatted_val}', chunk_text)
                        elif not re.match(r'^#{1,3}\s+[^\n]+$', chunk_text.strip()):
                            chunk["text"] = chunk_text.strip() + f"\n- **{field.capitalize()}**: {formatted_val}"
                else:
                    if bullet_attr_pattern.search(chunk_text):
                        chunk["text"] = bullet_attr_pattern.sub(rf'\g<1>{formatted_val}', chunk_text)
                    elif not re.match(r'^#{1,3}\s+[^\n]+$', chunk_text.strip()):
                        chunk["text"] = chunk_text.strip() + f"\n- **{field.capitalize()}**: {formatted_val}"

            # Synchronize last assistant turn in staging_history/history if present
            curr_summary = existing_doc.get("summary", "")
            if curr_summary:
                for hist_key in ("staging_history", "history"):
                    if hist_key in existing_doc and isinstance(existing_doc[hist_key], list) and existing_doc[hist_key]:
                        for turn in reversed(existing_doc[hist_key]):
                            if isinstance(turn, dict) and turn.get("role") == "assistant":
                                turn["content"] = curr_summary
                                break

            # Append to edit_history
            edit_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "edit",
                "field": clean_field,
                "target_item": target_item,
                "old_value": str(old_value)[:200] if old_value else None,
                "new_value": formatted_val,
                "source": "general_prompt"
            }
            if "edit_history" not in existing_doc or not isinstance(existing_doc["edit_history"], list):
                existing_doc["edit_history"] = []
            existing_doc["edit_history"].append(edit_entry)

            # Update batch_summary if this document belongs to a batch
            batch_id = existing_doc.get("batch_id")
            cur_bs = existing_doc.get("batch_summary") or existing_doc.get("metadata", {}).get("batch_summary")
            if cur_bs and target_item:
                if bullet_attr_pattern.search(cur_bs):
                    cur_bs = bullet_attr_pattern.sub(rf'\g<1>{formatted_val}', cur_bs)
                existing_doc["batch_summary"] = cur_bs
                if "metadata" in existing_doc and isinstance(existing_doc["metadata"], dict):
                    existing_doc["metadata"]["batch_summary"] = cur_bs

                # Propagate updated batch_summary to other output/pending files in this batch
                out_dir = settings.output_dir if hasattr(settings, "output_dir") else "data/output"
                if os.path.exists(out_dir):
                    for fn in os.listdir(out_dir):
                        if fn.endswith(".json") and fn != os.path.basename(approved_file):
                            f_path = os.path.join(out_dir, fn)
                            try:
                                with open(f_path, "r", encoding="utf-8") as bf:
                                    b_data = json.load(bf)
                                if b_data.get("batch_id") == batch_id:
                                    b_data["batch_summary"] = cur_bs
                                    if "metadata" in b_data and isinstance(b_data["metadata"], dict):
                                        b_data["metadata"]["batch_summary"] = cur_bs
                                    with open(f_path, "w", encoding="utf-8") as bf:
                                        json.dump(b_data, bf, indent=4, ensure_ascii=False)
                            except Exception:
                                pass

            # Save local JSON file
            with open(approved_file, "w", encoding="utf-8") as f:
                json.dump(existing_doc, f, indent=4, ensure_ascii=False)

            # Re-index PGVector
            if vector_store:
                logger.info(f"[DedicatedService] Re-indexing PGVector for '{doc_kid}'...")
                vector_store.delete_document(doc_kid)
                vector_store.insert_chunks(chunks)

            # Re-index BM25
            if bm25_index:
                logger.info(f"[DedicatedService] Re-indexing BM25 for '{doc_kid}'...")
                bm25_index.remove_file_chunks(doc_kid)
                bm25_index.add_chunks(chunks)
                bm25_index.save(settings.bm25_index_path)

            # Sync MinIO approved JSON
            try:
                from app.services.storage import upload_approved_json
                upload_approved_json(doc_kid, existing_doc)
            except Exception as s3_err:
                logger.debug(f"[DedicatedService] MinIO approved sync note: {s3_err}")

            # Sync PostgreSQL Knowledge DB record directly and commit
            await GeneralKnowledgeService.sync_knowledge_db(doc_kid, existing_doc=existing_doc, db=db)

            logger.info(f"[DedicatedService] Successfully applied edit to '{doc_kid}' field='{field}' target_item='{target_item}'")
            return {
                "success": True,
                "knowledge_id": doc_kid,
                "field": field,
                "target_item": target_item,
                "old_value": str(old_value)[:200] if old_value else None,
                "new_value": str(new_value)[:200]
            }

        except Exception as e:
            logger.error(f"[DedicatedService] Failed to apply edit for '{knowledge_id}': {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def apply_delete(
        knowledge_id: str,
        vector_store=None,
        bm25_index=None,
        target_item: Optional[str] = None,
        db=None
    ) -> Dict[str, Any]:
        """
        Deletes a KB document or surgically deletes a specific item within a multi-item document.
        Synchronizes local JSON, PostgreSQL, PGVector, MinIO, and BM25 index.
        """
        clean_target = (knowledge_id or "").strip().lower()

        # 1. Item-Level Surgical Deletion
        if target_item and target_item.strip():
            raw_item_clean = re.sub(r'^\*+|\*+$|^_+|_+$|^#+\s*', '', target_item.strip()).strip()
            target_item_clean = raw_item_clean
            target_item_lower = target_item_clean.lower()
            approved_file = resolve_approved_file(knowledge_id)
            if not approved_file:
                return {"success": False, "error": f"Dokumen dengan ID '{knowledge_id}' tidak ditemukan di approved KB."}

            try:
                with open(approved_file, "r", encoding="utf-8") as f:
                    existing_doc = json.load(f)

                doc_kid = str(existing_doc.get("knowledge_id") or knowledge_id)
                original_chunks = existing_doc.get("chunks", [])
                filtered_chunks = []
                removed_count = 0

                for chunk in original_chunks:
                    chunk_text = chunk.get("text", "") if isinstance(chunk, dict) else ""
                    chunk_lower = chunk_text.lower()
                    if target_item_lower in chunk_lower or re.sub(r'[\*\_#]', '', chunk_lower).find(target_item_lower) != -1:
                        meta = chunk.get("metadata", {})
                        meta_match = (
                            target_item_lower == str(meta.get("product_name", "")).lower()
                            or target_item_lower == str(meta.get("title", "")).lower()
                            or target_item_lower == str(meta.get("section", "")).lower()
                            or target_item_lower == str(meta.get("heading", "")).lower()
                        )
                        escaped_name = re.escape(target_item_clean)
                        has_heading = bool(re.search(rf'^#{1,4}\s*[^\n]*{escaped_name}', chunk_text, re.MULTILINE | re.IGNORECASE))

                        line_pattern = re.compile(rf'^[|\-\*\d\.]*\s*[^\n]*{escaped_name}[^\n]*$\n?', re.MULTILINE | re.IGNORECASE)
                        new_chunk_text = line_pattern.sub('', chunk_text).strip()

                        if meta_match or has_heading or len(new_chunk_text) < 30:
                            removed_count += 1
                        else:
                            chunk_copy = dict(chunk)
                            chunk_copy["text"] = new_chunk_text
                            filtered_chunks.append(chunk_copy)
                            removed_count += 1
                    else:
                        filtered_chunks.append(chunk)

                existing_doc["chunks"] = filtered_chunks

                # Remove target item section from summary
                summary = existing_doc.get("summary", "")
                if summary and target_item_lower in summary.lower():
                    escaped_name = re.escape(target_item_clean)
                    section_pattern = re.compile(
                        r'(?:^|\n)(#{1,4}\s*[^\n]*' + escaped_name + r'[^\n]*\n(?:(?!^#{1,4}\s)[^\n]*\n?)*)',
                        re.MULTILINE | re.IGNORECASE
                    )
                    summary = section_pattern.sub('\n', summary)
                    line_pattern = re.compile(
                        rf'^[|\-\*]\s*[^\n]*{escaped_name}[^\n]*$\n?',
                        re.MULTILINE | re.IGNORECASE
                    )
                    summary = line_pattern.sub('', summary)
                    summary = re.sub(r'\n{3,}', '\n\n', summary).strip()
                    existing_doc["summary"] = summary

                if summary:
                    for hist_key in ("staging_history", "history"):
                        if hist_key in existing_doc and isinstance(existing_doc[hist_key], list) and existing_doc[hist_key]:
                            for turn in reversed(existing_doc[hist_key]):
                                if isinstance(turn, dict) and turn.get("role") == "assistant":
                                    turn["content"] = summary
                                    break

                with open(approved_file, "w", encoding="utf-8") as f:
                    json.dump(existing_doc, f, indent=4, ensure_ascii=False)

                if vector_store:
                    vector_store.delete_document(doc_kid)
                    if filtered_chunks:
                        vector_store.insert_chunks(filtered_chunks)

                if bm25_index:
                    bm25_index.remove_file_chunks(doc_kid)
                    if filtered_chunks:
                        bm25_index.add_chunks(filtered_chunks)
                    bm25_index.save(settings.bm25_index_path)

                try:
                    from app.services.storage import upload_approved_json
                    upload_approved_json(doc_kid, existing_doc)
                except Exception as s3_err:
                    logger.debug(f"[DedicatedService] MinIO update note: {s3_err}")

                # Sync PostgreSQL Knowledge DB record directly and commit
                await GeneralKnowledgeService.sync_knowledge_db(doc_kid, existing_doc=existing_doc, db=db)

                logger.info(f"[DedicatedService] Surgically deleted item '{target_item_clean}' from doc '{doc_kid}' ({removed_count} chunks removed)")
                return {
                    "success": True,
                    "knowledge_id": doc_kid,
                    "target_item": target_item_clean,
                    "title": f"Item '{target_item_clean}' berhasil dihapus dari basis pengetahuan."
                }
            except Exception as e:
                logger.error(f"[DedicatedService] Item-level delete failed: {e}")
                return {"success": False, "error": str(e)}

        # 2. Batch Delete Expired Promos
        if clean_target in ("expired", "expired_promos", "promo_expired", "promo expired", "promo bulan lalu", "semua promo expired", "promo yang sudah expired"):
            today = datetime.now(timezone.utc).date()
            deleted_items = []
            pending_dir = "data/pending"
            approved_dir = "data/output"

            for folder in [pending_dir, approved_dir, os.path.join("backend", pending_dir), os.path.join("backend", approved_dir)]:
                if os.path.exists(folder):
                    for f in os.listdir(folder):
                        if f.endswith(".json") and f != "bm25_index.pkl":
                            f_path = os.path.join(folder, f)
                            try:
                                with open(f_path, "r", encoding="utf-8") as fp:
                                    f_data = json.load(fp)
                                is_expired = False
                                vu = f_data.get("valid_until") or f_data.get("expiry_date")
                                if vu:
                                    parsed_vu = parse_date_safely(vu)
                                    if parsed_vu and parsed_vu < today:
                                        is_expired = True

                                if is_expired:
                                    doc_id = str(f_data.get("knowledge_id", f.replace(".json", "")))
                                    doc_title = str(f_data.get("title", f_data.get("file_name", doc_id)))
                                    os.remove(f_path)
                                    if vector_store:
                                        vector_store.delete_document(doc_id)
                                    if bm25_index:
                                        bm25_index.remove_file_chunks(doc_id)
                                    deleted_items.append(f"{doc_title} (expired: {vu})")
                            except Exception as err:
                                logger.debug(f"[DedicatedService] Error checking expired file {f}: {err}")

            if bm25_index and deleted_items:
                bm25_index.save(settings.bm25_index_path)

            return {
                "success": True,
                "knowledge_id": "expired",
                "title": f"Berhasil menghapus {len(deleted_items)} promo kadaluarsa:\n" + "\n".join(f"- {d}" for d in deleted_items[:10])
            }

        # 3. Full Document Deletion
        approved_file = resolve_approved_file(knowledge_id)
        if not approved_file:
            return {"success": False, "error": f"Dokumen dengan ID/Nama '{knowledge_id}' tidak ditemukan di database."}

        try:
            with open(approved_file, "r", encoding="utf-8") as fp:
                f_data = json.load(fp)
            target_kid = str(f_data.get("knowledge_id") or knowledge_id)
            deleted_title = str(f_data.get("title", f_data.get("file_name", target_kid)))

            # Delete local file
            os.remove(approved_file)

            # Clear Vector Store
            if vector_store:
                vector_store.delete_document(target_kid)

            # Clear BM25
            if bm25_index:
                bm25_index.remove_file_chunks(target_kid)
                bm25_index.save(settings.bm25_index_path)

            # Delete from MinIO (including all embedded images and documents)
            try:
                from app.services.storage import delete_knowledge_images_and_assets
                delete_knowledge_images_and_assets(target_kid, doc_data=f_data)
            except Exception as s3_err:
                logger.debug(f"[DedicatedService] MinIO delete note: {s3_err}")

            # Soft-delete in PostgreSQL Knowledge DB record directly and commit
            await GeneralKnowledgeService.sync_knowledge_db(target_kid, deleted=True, db=db)

            return {
                "success": True,
                "knowledge_id": target_kid,
                "title": deleted_title
            }

        except Exception as e:
            logger.error(f"[DedicatedService] Failed to delete document '{knowledge_id}': {e}")
            return {"success": False, "error": str(e)}
