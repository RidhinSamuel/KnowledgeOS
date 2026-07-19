# workers/app/parser.py
import os
import tempfile
import asyncio
import logging
from typing import Tuple, List, Dict
import fitz # PyMuPDF
import structlog

from app.config import settings

logger = structlog.get_logger("parser")

# Apply nest_asyncio to support nested event loops if llama-parse requires it
import nest_asyncio
nest_asyncio.apply()

async def parse_document(file_bytes: bytes, filename: str) -> str:
    """
    Parses a PDF document.
    Attempts to use LlamaParse API if configured.
    Falls back to PyMuPDF (with Tesseract OCR for scanned pages) on failure or if credentials are missing.
    """
    # Write bytes to temporary file for parsing libraries
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
        temp_file.write(file_bytes)
        temp_path = temp_file.name

    try:
        # Check if LlamaParse is configured
        has_llamaparse = (
            settings.LLAMAPARSE_API_KEY 
            and settings.LLAMAPARSE_API_KEY != "mock-api-key-replace-with-real-one" 
            and len(settings.LLAMAPARSE_API_KEY) > 10
        )
        
        if has_llamaparse:
            logger.info("parsing_via_llamaparse_started", filename=filename)
            try:
                from llama_parse import LlamaParse
                parser = LlamaParse(
                    api_key=settings.LLAMAPARSE_API_KEY,
                    result_type="markdown",
                    verbose=False
                )
                
                # Load document asynchronously
                documents = await parser.aload_data(temp_path)
                parsed_text = "\n\n".join([doc.text for doc in documents])
                
                if parsed_text.strip():
                    logger.info("parsing_via_llamaparse_success", filename=filename, length=len(parsed_text))
                    return parsed_text
                else:
                    logger.warn("llamaparse_returned_empty_text_falling_back", filename=filename)
            except Exception as le:
                logger.error("llamaparse_failed_falling_back", filename=filename, error=str(le))

        # Fallback Local Parsing
        logger.info("parsing_locally_via_pymupdf", filename=filename)
        loop = asyncio.get_running_loop()
        parsed_text = await loop.run_in_executor(None, parse_local_pdf, temp_path)
        logger.info("parsing_locally_success", filename=filename, length=len(parsed_text))
        return parsed_text

    finally:
        # Cleanup temp file
        try:
            os.unlink(temp_path)
        except Exception:
            pass

def parse_local_pdf(file_path: str) -> str:
    """
    Synchronous local PDF parsing using PyMuPDF and Tesseract OCR.
    Runs inside a thread pool to avoid blocking the event loop.
    """
    text_blocks = []
    try:
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            
            # If the page yields minimal text, it is likely a scanned image. Use Tesseract OCR.
            if len(page_text.strip()) < 50:
                logger.debug("page_is_scanned_ocr_triggered", page=page_num + 1)
                try:
                    import pytesseract
                    from PIL import Image
                    import io
                    
                    # Convert page to high-res image bytes
                    pix = page.get_pixmap(dpi=150)
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    
                    # Perform OCR
                    ocr_text = pytesseract.image_to_string(img)
                    if ocr_text.strip():
                        page_text = ocr_text
                except Exception as oe:
                    logger.error("tesseract_ocr_failed", page=page_num + 1, error=str(oe))
            
            # Format and save text block with page number metadata
            text_blocks.append(f"<!-- PAGE_NUM: {page_num + 1} -->\n{page_text}\n")
            
        doc.close()
    except Exception as e:
        logger.error("local_pdf_parsing_crashed", error=str(e))
        raise e
        
    return "\n\n".join(text_blocks)
