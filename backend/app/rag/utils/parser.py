import os
import time
from typing import Optional, Tuple
from loguru import logger


class ParseResult:
    """
    Unified parse result that can hold either a DoclingDocument (for OCR path)
    or a list of page-text dicts (for fast path).
    """
    def __init__(self, pages: list = None, docling_doc=None, method: str = "fast"):
        self.pages = pages or []       # [{"page": 1, "text": "..."}, ...]
        self.docling_doc = docling_doc  # DoclingDocument object (only for OCR path)
        self.method = method           # "fast" or "docling"

    @property
    def is_fast(self) -> bool:
        return self.method == "fast"

    @property
    def is_docling(self) -> bool:
        return self.method == "docling"


class DocumentParser:
    """
    Smart Document Parser with two extraction paths:
    
    1. FAST PATH (python-docx / pypdf / plain read):
       - For .docx, .txt, and PDF files that contain selectable digital text.
       - Extracts text in < 1 second.
       
    2. DOCLING OCR FALLBACK:
       - For scanned/image-based PDFs where no selectable text exists.
       - Uses Docling's deep layout + OCR model pipeline (~60-120s on CPU).
    """

    def __init__(self):
        logger.info("Initializing Smart DocumentParser (Fast + Docling Selective Fallback)...")
        self._docling_converter = None  # Lazy-loaded only when needed

    def _get_docling_converter(self):
        """Lazy-load Docling DocumentConverter only when OCR is actually needed."""
        if self._docling_converter is None:
            logger.info("Loading Docling DocumentConverter for OCR fallback (first use)...")
            from docling.document_converter import DocumentConverter
            self._docling_converter = DocumentConverter()
        return self._docling_converter

    # -------------------------------------------------------------------------
    # FAST EXTRACTION: DOCX
    # -------------------------------------------------------------------------
    def _parse_docx_fast(self, file_path: str) -> ParseResult:
        """Extract text from .docx using python-docx (instant)."""
        from docx import Document as DocxDocument

        doc = DocxDocument(file_path)
        pages = []
        current_page_text = []
        page_num = 1

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # Check for page break in paragraph runs
            has_page_break = False
            for run in para.runs:
                if run._element.xml and "w:br" in run._element.xml and 'w:type="page"' in run._element.xml:
                    has_page_break = True
                    break

            if has_page_break and current_page_text:
                pages.append({"page": page_num, "text": "\n".join(current_page_text)})
                current_page_text = []
                page_num += 1

            current_page_text.append(text)

        # Also extract text from tables
        for table in doc.tables:
            table_rows = []
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells]
                table_rows.append(" | ".join(row_cells))
            if table_rows:
                current_page_text.append("\n".join(table_rows))

        # Flush remaining text
        if current_page_text:
            pages.append({"page": page_num, "text": "\n".join(current_page_text)})

        return ParseResult(pages=pages, method="fast")

    # -------------------------------------------------------------------------
    # FAST EXTRACTION: TXT
    # -------------------------------------------------------------------------
    def _parse_txt_fast(self, file_path: str) -> ParseResult:
        """Extract text from .txt file (instant)."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return ParseResult(pages=[{"page": 1, "text": content}], method="fast")

    # -------------------------------------------------------------------------
    # FAST EXTRACTION: PDF (with scanned detection)
    # -------------------------------------------------------------------------
    def _parse_pdf_fast(self, file_path: str) -> Optional[ParseResult]:
        """
        Try to extract text from PDF using pypdf.
        Returns ParseResult if the PDF has sufficient digital text.
        Returns None if the PDF appears to be scanned/image-based (triggers Docling fallback).
        """
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
        pages = []
        total_chars = 0
        pages_with_text = 0

        for i, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            char_count = len(text)
            total_chars += char_count

            if char_count > 30:  # Meaningful text threshold per page
                pages_with_text += 1

            pages.append({"page": i + 1, "text": text})

        # Heuristic: if < 30% of pages have meaningful text, assume scanned PDF
        text_coverage = pages_with_text / max(total_pages, 1)
        avg_chars_per_page = total_chars / max(total_pages, 1)

        if text_coverage < 0.3 or avg_chars_per_page < 50:
            logger.warning(
                f"PDF detected as scanned/image-based "
                f"(text_coverage={text_coverage:.0%}, avg_chars={avg_chars_per_page:.0f}). "
                f"Falling back to Docling OCR..."
            )
            return None  # Signal to use Docling OCR

        # Try to extract embedded images from PDF pages and upload to MinIO
        try:
            import fitz  # PyMuPDF
            from app.services.storage import upload_image
            doc = fitz.open(file_path)
            for i, page in enumerate(doc):
                img_list = page.get_images()
                img_markdowns = []
                for img_idx, img_info in enumerate(img_list[:3]):
                    xref = img_info[0]
                    base_img = doc.extract_image(xref)
                    img_bytes = base_img.get("image")
                    img_ext = base_img.get("ext", "png")
                    if img_bytes:
                        fname = f"pdf_p{i+1}_img{img_idx+1}.{img_ext}"
                        upload_res = upload_image(img_bytes, fname, content_type=f"image/{img_ext}")
                        img_url = upload_res.get("image_url")
                        if img_url:
                            img_markdowns.append(f"![{fname}]({img_url})")
                if img_markdowns and i < len(pages):
                    pages[i]["text"] += "\n\n" + "\n".join(img_markdowns)
                    pages[i]["image_url"] = upload_res.get("image_url")
        except Exception as img_err:
            logger.debug(f"PDF embedded image extraction skipped/optional: {img_err}")

        return ParseResult(pages=pages, method="fast")

    # -------------------------------------------------------------------------
    # FAST EXTRACTION: EXCEL & CSV (.xlsx, .xls, .csv)
    # -------------------------------------------------------------------------
    def _parse_excel_fast(self, file_path: str) -> ParseResult:
        """Extract text and markdown tables from .xlsx, .xls, and .csv files using pandas."""
        import pandas as pd

        ext = os.path.splitext(file_path)[1].lower()
        pages = []

        try:
            if ext == ".csv":
                df = pd.read_csv(file_path)
                df = df.dropna(how="all")
                md_table = df.to_markdown(index=False)
                pages.append({
                    "page": 1,
                    "text": f"### CSV Data Table\n\n{md_table}"
                })
            else:
                with pd.ExcelFile(file_path) as excel_file:
                    for page_idx, sheet_name in enumerate(excel_file.sheet_names, start=1):
                        df = pd.read_excel(excel_file, sheet_name=sheet_name)
                        if df.empty:
                            continue
                        df = df.dropna(how="all")
                        md_table = df.to_markdown(index=False)
                        sheet_text = f"### Sheet: {sheet_name}\n\n{md_table}"
                        pages.append({
                            "page": page_idx,
                            "text": sheet_text
                        })

            if not pages:
                pages = [{"page": 1, "text": "Dokumen spreadsheet kosong."}]

            return ParseResult(pages=pages, method="fast")
        except Exception as e:
            logger.warning(f"Fast pandas Excel parse failed for {file_path}: {e}. Falling back to text extraction...")
            return ParseResult(pages=[{"page": 1, "text": f"Error parsing spreadsheet: {e}"}], method="fast")

    def _parse_standalone_image(self, file_path: str) -> ParseResult:
        """Uploads standalone image file to MinIO S3 and returns ParseResult with Markdown image link."""
        from app.services.storage import upload_image

        file_name = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower().replace(".", "")
        content_type = f"image/{ext}" if ext in ["png", "jpg", "jpeg", "webp"] else "image/png"

        try:
            with open(file_path, "rb") as f:
                image_bytes = f.read()

            upload_res = upload_image(image_bytes, file_name, content_type=content_type)
            image_url = upload_res.get("image_url", "")
            
            markdown_text = f"### Asset Gambar: {file_name}\n\n![{file_name}]({image_url})"
            pages = [{
                "page": 1,
                "text": markdown_text,
                "image_url": image_url
            }]
            logger.info(f"🖼️ Standalone image '{file_name}' uploaded to MinIO: {image_url}")
            return ParseResult(pages=pages, method="fast")
        except Exception as e:
            logger.warning(f"Standalone image upload to MinIO failed for {file_path}: {e}")
            return self._parse_with_docling(file_path)

    # -------------------------------------------------------------------------
    # DOCLING OCR FALLBACK (Heavy / Scanned PDFs & Standalone Images)
    # -------------------------------------------------------------------------
    def _parse_with_docling(self, file_path: str) -> Optional[ParseResult]:
        """Full Docling OCR parse for scanned/image PDFs and standalone images."""
        import io
        from docling_core.types.io import DocumentStream

        converter = self._get_docling_converter()
        file_name = os.path.basename(file_path)

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        stream = io.BytesIO(file_bytes)
        doc_stream = DocumentStream(name=file_name, stream=stream)

        result = converter.convert(doc_stream)
        doc = result.document
        return ParseResult(docling_doc=doc, method="docling")

    # -------------------------------------------------------------------------
    # MAIN ENTRY POINT
    # -------------------------------------------------------------------------
    def parse_file(self, file_path: str) -> Optional[ParseResult]:
        """
        Smart parse: tries fast extraction first for docx, txt, pdf, xlsx, csv.
        Falls back to Docling OCR for scanned PDFs & image files.
        Returns a ParseResult object.
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None

        ext = os.path.splitext(file_path)[1].lower()
        start_time = time.time()

        try:
            if ext == ".docx":
                logger.info(f"⚡ Fast DOCX extraction: {file_path}")
                result = self._parse_docx_fast(file_path)

            elif ext == ".txt":
                logger.info(f"⚡ Fast TXT extraction: {file_path}")
                result = self._parse_txt_fast(file_path)

            elif ext in [".xlsx", ".xls", ".csv"]:
                logger.info(f"📊 Fast Excel/CSV extraction: {file_path}")
                result = self._parse_excel_fast(file_path)

            elif ext == ".pdf":
                logger.info(f"⚡ Attempting fast PDF extraction: {file_path}")
                result = self._parse_pdf_fast(file_path)

                if result is None:
                    # Scanned PDF detected → Docling OCR fallback
                    logger.info(f"🔬 Docling OCR fallback for scanned PDF: {file_path}")
                    result = self._parse_with_docling(file_path)
            elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
                logger.info(f"🖼️ Standalone image extraction & MinIO upload: {file_path}")
                result = self._parse_standalone_image(file_path)
            else:
                # Unknown extension → try Docling as universal fallback
                logger.info(f"🔬 Docling universal parse for {ext}: {file_path}")
                result = self._parse_with_docling(file_path)

            elapsed = time.time() - start_time
            if result:
                method_label = "Fast" if result.is_fast else "Docling OCR"
                page_count = len(result.pages) if result.is_fast else "N/A"
                logger.info(
                    f"✅ Parsed {file_path} via {method_label} in {elapsed:.2f}s "
                    f"(pages={page_count})"
                )
            return result

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ Error parsing {file_path} after {elapsed:.2f}s: {e}")
            return None
