# Interview Preparation Guide - Multi-Tenant RAG & Pipelines

This document provides a set of questions, coding challenges, and system design discussions tailored for technical interviews on architectures similar to KnowledgeOS.

---

## Core System Design Questions

### 1. How would you design a multi-tenant vector search system at scale?
*   **Context**: The database contains billions of vectors for millions of users.
*   **Key Points**:
    *   Discuss the trade-offs of Collection-per-tenant vs. Single collection with metadata indexing.
    *   Explain how payload index filters in Qdrant prevent cross-tenant queries.
    *   Detail how you would shard and replicate collections across nodes.

### 2. Explain how to handle database consistency in an event-driven system.
*   **Context**: A PDF is uploaded; what happens if Qdrant indexing succeeds but updating MongoDB state fails?
*   **Key Points**:
    *   Describe idempotency. If the message is reprocessed, vectors in Qdrant are overwritten rather than duplicated.
    *   Explain how database writes should be structured to allow safe retries.

---

## Technical Python / Concurrency Questions

### 1. How does Python's `asyncio` event loop work, and when does it fail?
*   **Key Points**:
    *   The event loop runs on a single thread, scheduling execution blocks.
    *   If a function contains blocking synchronous calls (like `time.sleep` or a long CPU loop), the loop pauses and all connections hang.
    *   Use thread pools (`run_in_executor`) to run blocking code.

---

## Common Mistakes
- **Vague answers**: Failing to cite concrete technologies (like Redis Streams, Qdrant payload filters) when explaining design patterns.

---

## Mock Interview Session
*   *Interviewer*: "Why did you choose MongoDB instead of Postgres for this system?"
*   *Candidate*: "MongoDB is ideal because our ingestion pipeline extracts metadata blocks of dynamic formats from PDFs. Motor gives us native async integrations. Postgres is excellent, but its relational schema requires migration cycles that slow down dynamic schema developments."
