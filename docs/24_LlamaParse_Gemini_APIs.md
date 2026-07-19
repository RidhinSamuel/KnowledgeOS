# LlamaParse & Google Gemini API Integration Guide

## Why This Design Exists
For applications deployed on machines without high-end dedicated GPUs, processing documents locally presents substantial challenges:
1. **CPU Exhaustion**: Complex PDF layout extraction (like IBM Docling or deep-learning OCR models) is highly CPU-bound, blocking other microservice operations.
2. **Quality of Layout Extraction**: standard PDF text extraction tools scramble multi-column layouts, tables, headers, and footers. LlamaParse is a specialized cloud parser that transforms documents into markdown, retaining formatting, tables, and structures.
3. **RAM Optimization**: Loading deep learning embedding models (like sentence-transformers) or running local LLMs can consume multiple gigabytes of memory, causing host system crashes. Enlisting the Google Gemini API handles both embeddings generation and chat streaming completely in the cloud.

---

## Alternative Approaches

| Tool Area | Option | Approach | Pros | Cons |
| :--- | :--- | :--- | :--- | :--- |
| **Parsing** | LlamaParse (Selected) | Cloud-based layout-aware parsing | High structural fidelity, converts tables to Markdown tables, zero CPU load | Requires API key, dependent on internet connectivity |
| **Parsing** | Local Docling | CPU/GPU local layout analysis | Free, completely offline, high quality | High RAM (2-4GB), slow on CPU-only machines |
| **Parsing** | PyMuPDF | Local text extraction | Free, offline, extremely fast | Lacks table parsing, scrambles multi-column layouts, fails on scanned images |
| **Embeddings** | Gemini Embeddings (Selected) | Cloud Vector Generator (`text-embedding-004`) | Sub-millisecond generation, high dimension (768), free/low cost | API dependency |
| **Embeddings** | SentenceTransformers | Local model (`all-MiniLM-L6-v2`) | Completely offline, customizable | Consumes local memory, slower on CPU |

---

## Trade-offs
- **API Cost vs. Hardware Cost**: Utilizing cloud APIs introduces potential charges (Gemini has a free tier, LlamaParse has a free tier of 1000 pages per day). However, it completely eliminates the need for expensive GPU cloud instances, saving hundreds of dollars in operational hosting.
- **Data Privacy**: Files are sent to LlamaParse and Google servers for processing. For enterprises with strict data residency requirements, local processing (Docling + SentenceTransformers) remains the only compliant option.

---

## Production Considerations
- **API Rate Limiting**: Google Gemini and LlamaParse enforce rate limits (e.g. Requests Per Minute / RPM). The ingestion worker handles rate limits by implementing retry mechanisms, exponential backoffs, and fallback to local parsing on persistent errors.
- **Batch Processing**: Send multiple sentences concurrently to `embeddings.aembed_documents()` instead of calling the API one-by-one. This prevents hitting RPM limits.

---

## Implementation Notes
- **LlamaParse Async Call**:
  ```python
  from llama_parse import LlamaParse
  parser = LlamaParse(api_key="KEY", result_type="markdown")
  documents = await parser.aload_data("temp_file.pdf")
  ```
- **Gemini Embeddings Async Call**:
  ```python
  from langchain_google_genai import GoogleGenAIEmbeddings
  embeddings = GoogleGenAIEmbeddings(model="models/text-embedding-004", google_api_key="KEY")
  vectors = await embeddings.aembed_documents(["sentence 1", "sentence 2"])
  ```

---

## Common Mistakes
- **Exposing Keys**: Accidentally checking in API keys to Git. Always load keys from environment variables using `settings.GEMINI_API_KEY`.
- **Failing to ACK on API Errors**: If the API goes down and the worker throws an error, leaving the task unacknowledged causes infinite retry loops. Implement maximum retry checks and DLQ routing.

---

## Interview Questions
1. **Q: How does LlamaParse preserve tabular data compared to traditional PDF parsers?**
   *A: Traditional parsers read characters based on coordinate sequences, which mixes text lines within tables. LlamaParse processes the page layout as an image, isolates boundaries, and uses vision models to reconstruct the content into structured Markdown tables.*
2. **Q: Why do we use `text-embedding-004` and what is its output dimension?**
   *A: `text-embedding-004` is Google's latest embedding model, optimized for semantic retrieval. It produces a 768-dimensional vector, which represents a rich representation of text meaning.*
