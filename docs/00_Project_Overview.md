# Project Overview - KnowledgeOS

## Why This Design Exists
KnowledgeOS is a multi-tenant SaaS platform built to securely ingest, process, and query massive corporate document bases using Retrieval-Augmented Generation (RAG). Modern enterprises require an AI search solution that combines:
1. **Strict Multi-Tenant Separation**: Zero data leakage across different clients.
2. **Event-Driven Asynchronous Ingestion**: Ingesting complex PDFs takes seconds or minutes. Uploads must return instantly, delegating layout parsing and vector indexing to independent workers.
3. **Hybrid Retrieval**: Standard semantic search is enhanced with keyword filtering and cross-encoder reranking to ensure precise answers.

This architecture exists to isolate heavy CPU-bound processing (PDF layout analysis via IBM's Docling, OCR, Hugging Face embedding generation) from the FastAPI web server. By using Redis Streams for task queues, Motor/MongoDB for transactional storage, and Qdrant for vector retrieval, the system achieves maximum responsiveness, scalability, and security.

---

## Alternative Approaches
When designing a document knowledge extraction platform, different architectural paradigms can be selected:

| Paradigm | Technology Stack | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **Monolithic Sync** | FastAPI + SQLite + local python threads | Very simple to deploy, no external message queue needed | PDF parsing blocks event loop, zero scalability, risk of data loss on crash |
| **Traditional Task Queue** | Django + Celery + PostgreSQL + Redis | Mature ecosystem, robust task management | Heavy dependencies, Django ORM lacks native async optimization, Celery has serialization overhead |
| **Decoupled Event-Driven (Selected)** | FastAPI (Async) + Redis Streams + Workers + MongoDB + Qdrant | Highly scalable, low latency, non-blocking async, strict containerization | More complex infrastructure setup, requires custom worker loop |

---

## Trade-offs
- **Complexity vs. Performance**: Decoupling ingestion into an asynchronous, stream-based microservice model requires setting up consumer groups, handling dead-letter queues (DLQ), and managing state synchronization across databases. However, it completely immunizes the HTTP API from backend CPU spikes.
- **Local Embeddings vs. External API**: Running local Hugging Face embedding models inside the worker containers saves API costs and guarantees data privacy. The trade-off is higher RAM/CPU utilization in the worker containers compared to querying OpenAI or Cohere embedding endpoints.

---

## Production Considerations
- **Memory Management**: PDF extraction libraries like Docling and PyMuPDF can be memory-intensive. Production deployments should restrict worker container RAM using Docker/Kubernetes limits to prevent host system crashes due to out-of-memory (OOM) situations.
- **Valkey/Redis Persistence**: Enable Append Only File (AOF) on Valkey to prevent losing task state on system restart.

---

## Implementation Notes
- The FastAPI server writes raw metadata to MongoDB and publishes a message containing `document_id` and `workspace_id` to the Redis stream `stream:document_ingestion`.
- Workers subscribe via a consumer group, download the document, process it, extract text, partition it into semantic chunks, embed them, and index into Qdrant.

---

## Common Mistakes
- **Blocking Async Loops**: Using synchronous libraries (like standard `requests` or `open()`) within the FastAPI async routes. Always use motor, httpx, and run CPU-heavy functions in threat pools or background subprocesses.
- **Ignoring Multi-Tenancy in Search**: Querying the vector database without strict payload filtering, resulting in cross-tenant data leaks.

---

## Interview Questions
1. **Q: Why use Redis Streams instead of Celery/RQ for task queuing?**
   *A: Redis Streams provide native stream processing, consumer groups, offsets, acknowledgements, and low overhead. This eliminates Celery's heavy dependency footprint and provides better performance in modern async-first Python ecosystems.*
2. **Q: How does the system ensure that Tenant A cannot retrieve Tenant B's data?**
   *A: Every vector stored in Qdrant includes metadata payloads for `workspace_id` and `user_id`. Every query made to Qdrant is appended with a hard payload filter enforcing the workspace boundaries.*
