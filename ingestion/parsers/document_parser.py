import io
import structlog
import pytesseract
from dataclasses import dataclass
from pathlib import Path
from PIL import Image

import pdfplumber
from bs4 import BeautifulSoup
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions

logger = structlog.get_logger()


@dataclass
class ParsedDocument:
    text: str
    sections: list[dict]       # [{title, content, page_num}]
    tables: list[dict]         # [{caption, data}]
    metadata: dict
    page_count: int
    has_ocr: bool = False


class DocumentParser:
    """
    Universal document parser using Docling as primary engine.
    Falls back to pdfplumber + Tesseract for scanned PDFs.
    Handles: PDF, DOCX, HTML.
    """

    def __init__(self):
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False          # we handle OCR fallback manually
        pipeline_options.do_table_structure = True

        self._converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF, InputFormat.DOCX, InputFormat.HTML]
        )

    def parse(self, content: bytes, content_type: str, filename: str = "document") -> ParsedDocument:
        if "pdf" in content_type:
            return self._parse_pdf(content, filename)
        elif "html" in content_type:
            return self._parse_html(content)
        elif "docx" in content_type or "word" in content_type:
            return self._parse_docx(content, filename)
        else:
            # attempt generic parse
            return self._parse_html(content)

    def _parse_pdf(self, content: bytes, filename: str) -> ParsedDocument:
        # Try Docling first (handles structured PDFs well)
        try:
            tmp_path = Path(f"/tmp/{filename}.pdf")
            tmp_path.write_bytes(content)
            result = self._converter.convert(str(tmp_path))
            doc = result.document

            text = doc.export_to_text()
            if len(text.strip()) > 100:
                sections = self._extract_sections_from_docling(doc)
                tables = self._extract_tables_from_docling(doc)
                return ParsedDocument(
                    text=text,
                    sections=sections,
                    tables=tables,
                    metadata={"parser": "docling"},
                    page_count=len(doc.pages) if hasattr(doc, "pages") else 0,
                )
        except Exception as e:
            logger.warning("docling_parse_failed", error=str(e), filename=filename)

        # Fallback: pdfplumber for text-based PDFs
        try:
            return self._parse_pdf_pdfplumber(content)
        except Exception as e:
            logger.warning("pdfplumber_parse_failed", error=str(e))

        # Final fallback: OCR with Tesseract
        return self._parse_pdf_ocr(content)

    def _parse_pdf_pdfplumber(self, content: bytes) -> ParsedDocument:
        sections = []
        all_text = []
        tables = []

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text() or ""
                all_text.append(page_text)

                page_tables = page.extract_tables()
                for table in page_tables:
                    if table:
                        tables.append({"page": page_num, "data": table})

                if page_text.strip():
                    sections.append({
                        "title": f"Page {page_num}",
                        "content": page_text,
                        "page_num": page_num,
                    })

            return ParsedDocument(
                text="\n\n".join(all_text),
                sections=sections,
                tables=tables,
                metadata={"parser": "pdfplumber"},
                page_count=len(pdf.pages),
            )

    def _parse_pdf_ocr(self, content: bytes) -> ParsedDocument:
        logger.info("falling_back_to_ocr")
        pages_text = []

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                img = page.to_image(resolution=300).original
                text = pytesseract.image_to_string(img, lang="eng")
                pages_text.append(text)

        full_text = "\n\n".join(pages_text)
        return ParsedDocument(
            text=full_text,
            sections=[{"title": f"Page {i+1}", "content": t, "page_num": i+1}
                      for i, t in enumerate(pages_text)],
            tables=[],
            metadata={"parser": "tesseract_ocr"},
            page_count=page_count,
            has_ocr=True,
        )

    def _parse_html(self, content: bytes) -> ParsedDocument:
        soup = BeautifulSoup(content, "lxml")

        # Remove nav, footer, scripts, styles
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        sections = []
        current_section = {"title": "Introduction", "content": [], "page_num": 1}

        for element in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
            if element.name in ["h1", "h2", "h3", "h4"]:
                if current_section["content"]:
                    current_section["content"] = " ".join(current_section["content"])
                    sections.append(current_section)
                current_section = {
                    "title": element.get_text(strip=True),
                    "content": [],
                    "page_num": 1,
                }
            else:
                text = element.get_text(strip=True)
                if text:
                    current_section["content"].append(text)

        if current_section["content"]:
            current_section["content"] = " ".join(current_section["content"])
            sections.append(current_section)

        full_text = soup.get_text(separator="\n", strip=True)
        return ParsedDocument(
            text=full_text,
            sections=sections,
            tables=[],
            metadata={"parser": "beautifulsoup"},
            page_count=1,
        )

    def _parse_docx(self, content: bytes, filename: str) -> ParsedDocument:
        try:
            tmp_path = Path(f"/tmp/{filename}.docx")
            tmp_path.write_bytes(content)
            result = self._converter.convert(str(tmp_path))
            doc = result.document
            return ParsedDocument(
                text=doc.export_to_text(),
                sections=self._extract_sections_from_docling(doc),
                tables=self._extract_tables_from_docling(doc),
                metadata={"parser": "docling_docx"},
                page_count=1,
            )
        except Exception as e:
            logger.error("docx_parse_failed", error=str(e))
            return ParsedDocument(text="", sections=[], tables=[], metadata={}, page_count=0)

    def _extract_sections_from_docling(self, doc) -> list[dict]:
        sections = []
        try:
            for item in doc.iterate_items():
                label = getattr(item, "label", None)
                if label and "heading" in str(label).lower():
                    sections.append({
                        "title": item.text if hasattr(item, "text") else str(item),
                        "content": "",
                        "page_num": getattr(item, "page_no", 1),
                    })
        except Exception:
            pass
        return sections

    def _extract_tables_from_docling(self, doc) -> list[dict]:
        tables = []
        try:
            for table in doc.tables:
                tables.append({
                    "caption": getattr(table, "caption", ""),
                    "data": table.export_to_dataframe().to_dict() if hasattr(table, "export_to_dataframe") else {},
                })
        except Exception:
            pass
        return tables
