# Study Guide - RAG, Async IO, & Messaging

This guide acts as a syllabus for studying the concepts, tools, and algorithms integrated into the KnowledgeOS repository.

---

## Core Topics to Master

### 1. Asynchronous Programming in Python
*   **Concepts**: Event loop, Coroutines, Tasks, Futures, Lifespans.
*   **Practice**:
    *   Write a simple HTTP server using `asyncio` and `sockets`.
    *   Implement an async task scheduler with queue limits.

### 2. Stream Processing with Valkey/Redis
*   **Concepts**: Stream commands (`XADD`, `XREAD`, `XACK`, `XPENDING`), consumer groups, recovery loops.
*   **Practice**:
    *   Build a simple producer-consumer setup using redis-py.
    *   Write a script that claims dead consumer tasks using `XCLAIM`.

### 3. Vector Databases and Retrieval
*   **Concepts**: Dense vs. Sparse embeddings, HNSW graphs, Cosine similarity, hybrid searches, and cross-encoders.
*   **Practice**:
    *   Set up Qdrant locally and index random arrays.
    *   Query vectors using payload metadata filters.

---

## Resources & References
- *Python Concurrency with Asyncio* (Matthew Fowler)
- *Designing Data-Intensive Applications* (Martin Kleppmann)
- *Qdrant Documentation (Multi-Tenancy and Hybrid Search guides)*

---

## Final Review Questions
1. How does the worker pipeline handle PDF parsing failures without crashing the container?
2. What are the benefits of using a hybrid search over standard semantic search?
