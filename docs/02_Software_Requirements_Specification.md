# Software Requirements Specification (SRS) - KnowledgeOS

## Why This Design Exists
The SRS bridges the gap between high-level business goals and actual implementation. It lists specific functional limits, library choices, API patterns, and performance targets (non-functional requirements) to guide developer implementation.

---

## Alternative Approaches
- **Thread-Based REST (Flask/Django)**:
  - *Trade-off*: Limited throughput on long-lived connections (SSE) due to blocking network I/O.
- **Asynchronous REST (FastAPI/AsyncIO) (Selected)**:
  - *Trade-off*: Requires async-compatible drivers (Motor, redis-py-async) and careful handling of async event loops, but enables thousands of concurrent connections and streaming chat responses out of the box.

---

## Trade-offs
- **Pydantic v2 vs Pydantic v1**: Pydantic v2 is written in Rust and is 5-10x faster for serialization/deserialization. The trade-off is the need to migrate syntax for custom validators.
- **REST vs GraphQL**: REST is simpler, easier to cache, and has first-class support in standard security layers. GraphQL is rejected due to unnecessary complexity for a document-focused system.

---

## Production Considerations
- **Non-Functional Performance Targets**:
  - API response latency (excluding LLM streaming): `< 100ms` for 95% of queries.
  - PDF Ingestion throughput: Processing 100 pages under 60 seconds.
  - Streaming Start Latency (Time-To-First-Token / TTFT): `< 1s`.
- **System Limits**:
  - Maximum upload size: `50MB` per file.
  - Supported file types: `.pdf`, `.txt`, `.docx`.

---

## Implementation Notes
- All backend routes are async and use standard FastAPI dependencies for authorization.
- Fast API handles streaming responses using `StreamingResponse` wrapping an async generator.

---

## Common Mistakes
- **Mixing Sync/Async**: Using standard `os.path` operations or standard `open()` in async endpoints. We use `anyio` or thread pools to offload local file writes.
- **No Upload Rate-Limiting**: Allowing users to upload massive files concurrently without rate limits, exhausting worker node disks.

---

## Interview Questions
1. **Q: Why is Python 3.13 selected, and what are the advantages of FastAPI in async architectures?**
   *A: Python 3.13 introduces substantial performance improvements, better error reporting, and async loop optimizations. FastAPI provides native support for OpenAPI/Swagger generation, dependency injection, and high-performance validation through Pydantic v2.*
2. **Q: How does the system handle high-concurrency file uploads?**
   *A: The API streams the uploaded bytes directly to temporary storage, registers the document in MongoDB, and drops a small payload into the Redis Stream queue. This keeps the API connection short-lived and delegates CPU processing to workers.*
