# Architecture Decision Records (ADR) - KnowledgeOS

This document stores the technical decisions, reasons, alternatives, and impacts of the KnowledgeOS architecture.

---

## ADR 01: Use of Redis Streams (instead of Celery or RabbitMQ)
- **Status**: Approved.
- **Context**: The platform needs an ingestion queue for parsing. Celery is standard but heavy, and RabbitMQ requires dedicated servers.
- **Decision**: Use Redis Streams (or Valkey Streams) for messaging.
- **Why**: Since Redis is already required for API caching and rate-limiting, reusing it for streams eliminates the operational overhead of a separate message broker.
- **Impact**: Requires writing a custom python polling loop but keeps the stack extremely lightweight and easy to orchestrate.

---

## ADR 02: Use of Qdrant (instead of pgvector)
- **Status**: Approved.
- **Context**: Vector storage and similarity retrieval are required for the RAG chat.
- **Decision**: Deploy Qdrant vector database.
- **Why**: Qdrant offers superior performance on multi-tenant payload filtering, dense-sparse hybrid vectors, and sub-millisecond retrieval.
- **Impact**: Requires maintaining MongoDB for document metadata and Qdrant for vectors, necessitating synchronization logic inside workers.

---

## ADR 03: Motor Driver for MongoDB
- **Status**: Approved.
- **Context**: MongoDB stores workspace documents and chat histories. FastAPI is asynchronous.
- **Decision**: Use Motor, MongoDB's official async driver.
- **Why**: Motor integrates with FastAPI's asyncio loop, preventing database network delays from blocking the server.
- **Impact**: Requires using `await` syntax for all Mongo queries.

---

## ADR 04: Local PDF Parsing and Fallbacks
- **Status**: Approved.
- **Context**: PDFs uploaded contain formatting, tables, and scanned text.
- **Decision**: Combine PyMuPDF, IBM Docling, and Tesseract OCR.
- **Why**: PyMuPDF handles standard digital text rapidly. Docling parses complex layout tables. Tesseract handles scanned sheets.
- **Impact**: Heavy dependencies increase worker container sizes.

---

## Common Mistakes
- **Modifying Approved ADRs without team consent**: Making undocumented architectural changes.

---

## Interview Questions
1. **Q: What is the purpose of an ADR and why is it important?**
   *A: Architecture Decision Records (ADRs) capture the context, alternatives, and reasons behind design choices. It helps future developers understand why a system was built a certain way, preventing regression and repeating past mistakes.*
