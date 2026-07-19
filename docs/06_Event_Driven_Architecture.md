# Event-Driven Architecture - KnowledgeOS

## Why This Design Exists
PDF processing and OCR are slow, variable-duration operations (taking from hundreds of milliseconds to multiple minutes). If these occurred synchronously within the HTTP thread, client connections would timeout, API throughput would drop to single digits, and the application would fail. 
An Event-Driven Architecture (EDA) decouples document ingestion from vector indexing, using an event broker to communicate task requests.

---

## Alternative Approaches
- **Choreography (Publish/Subscribe)**: Every component publishes events, and other components listen.
  - *Trade-off*: Highly decoupled but tracking the state of a single document is difficult as events scatter.
- **Orchestration (Worker Queue) (Selected)**: The backend API orchestrates the request by publishing a structured command task (e.g., `process_document`) into a stream.
  - *Trade-off*: Clear state flow and centralized processing logic.

---

## Trade-offs
- **Guaranteed Processing vs Ingestion Speed**: Implementing message acknowledgements (ACKs) and DLQ retries guarantees that every document is processed, at the cost of slight messaging overhead.
- **Memory Storage vs Persistence**: Storing file binaries in the queue creates large memory bloat. We pass references (`document_id`, `file_path`) and fetch the binary from MongoDB/GridFS inside the worker.

---

## Production Considerations
- **Backpressure**: If a tenant uploads 1,000 files, it could starve other tenants. We implement a fair-share streaming worker mechanism or multiple consumer groups to avoid queue starvation.
- **Idempotency**: Workers must be idempotent. If a task is retried, reprocessing the same document should replace the existing vectors in Qdrant rather than appending duplicates.

---

## Implementation Notes
- The event schema includes: `event_id`, `timestamp`, `tenant_id`, `workspace_id`, `document_id`, `retry_count`.
- Workers check if the document is still in `PENDING` state before processing.

---

## Common Mistakes
- **Passing Large Payloads**: Pushing raw PDF bytes inside the Redis queue.
- **Losing Message Context**: Failing to preserve trace IDs across boundaries, breaking observability and logging.

---

## Interview Questions
1. **Q: How does this system handle backpressure?**
   *A: Redis Streams allow us to monitor queue length using `XLEN`. We can horizontally scale workers by spinning up more container instances in our consumer group when the queue size crosses a specified threshold.*
2. **Q: What is the difference between Pub/Sub and Message Streams?**
   *A: Pub/Sub is fire-and-forget. If no consumers are online, the message is lost. Message Streams (like Redis Streams) are persistent. Messages remain in the stream until consumed and acknowledged, allowing offline consumers to catch up.*
