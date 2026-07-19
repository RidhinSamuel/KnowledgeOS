# Document Ingestion Pipeline - KnowledgeOS

## Why This Design Exists
Documents uploaded to an enterprise system vary wildly in layout and structure (digital PDFs, scanned images, multi-column reports, long text files). 
This ingestion pipeline exists to transform these raw binaries into structured, searchable semantic vectors. By splitting processing into distinct pipeline steps, we can track progress in real-time, handle specific stage failures, and implement modular fallback strategies.

---

## Alternative Approaches
- **Single-Stage Parsing (e.g. PyPDF2 only)**:
  - *Trade-off*: Fast, but fails on scanned images, ignores page layouts, columns read out of order, and yields poor retrieval quality.
- **Multi-Stage Adaptive Parsing (Selected)**: Use PyMuPDF for fast digital PDF text extraction; fall back to Tesseract OCR for scanned pages; use Docling for complex structural layouts (tables, headers).
  - *Trade-off*: Complex dependency layer and higher CPU usage, but provides high-fidelity chunking.

```
Raw Upload -> Mongo GridFS -> Redis Event -> Worker Fetches
                                                   │
     ┌─────────────────────────────────────────────┴────────────────────────┐
     ▼                                             ▼                        ▼
PyMuPDF (Fast Digital)                    Docling (Layout/Tables)      Tesseract (OCR Fallback)
     │                                             │                        │
     └─────────────────────────────────────────────┬────────────────────────┘
                                                   ▼
                                        Semantic Chunking
                                                   ▼
                                         Hugging Face Embedder
                                                   ▼
                                         Qdrant Vector Indexing
```

---

## Trade-offs
- **Processing Time vs. Accuracy**: Layout parsing via deep learning models (Docling) is significantly slower than regex-based line readers. However, preserving tabular structures is critical for RAG accuracy when parsing financials or technical reports.

---

## Production Considerations
- **Chunk Size Tuning**: Dynamic semantic chunking evaluates sentence similarity rather than splitting at hard character counts. This preserves paragraph-level context.
- **Resource Pooling**: Share the Hugging Face embedding model instance across worker threads to avoid reloading models into GPU/RAM for every document.

---

## Implementation Notes
- Pipeline States stored in MongoDB:
  - `PENDING`: Uploaded, event published.
  - `PROCESSING`: Worker has claimed task and started parsing.
  - `COMPLETED`: Vector indexing finished, ready for search.
  - `FAILED`: Ingestion crashed, error logged.

---

## Common Mistakes
- **Memory Exhaustion on Massive PDFs**: Attempting to read a 1000-page PDF into a single string. Parse documents page-by-page or stream chunks to keep memory flat.
- **Discarding Tables**: Converting tabular columns into running text, which completely scrambles relational data.

---

## Interview Questions
1. **Q: How does semantic chunking differ from fixed-size chunking?**
   *A: Fixed-size chunking splits text based on character or token counts (e.g. 500 characters) regardless of sentence boundaries, breaking logical thoughts. Semantic chunking computes embedding similarity between consecutive sentences, creating a split only when the semantic difference exceeds a threshold.*
2. **Q: How does the system handle scanned PDF files?**
   *A: The parser first checks if PyMuPDF retrieves any text from the page. If the text length is below a threshold (e.g. 50 characters), the page is marked as an image, converted to a pixmap, and processed via Tesseract OCR.*
