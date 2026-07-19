# Failure Recovery & Resilience

## Why This Design Exists
In distributed systems, failures are inevitable (network disconnects, database timeouts, corrupted PDFs crashing worker threads, external LLM API outages). 
This failure recovery architecture is designed to prevent data loss, ensure self-healing of services, and keep the user interface updated on failures.

---

## Alternative Approaches
- **Immediate Failure (Fail-Fast)**: If a step fails, the task aborts and the document is marked as failed.
  - *Trade-off*: Simpler code, but creates poor user experience when transient network issues abort uploads.
- **Retry with Exponential Backoff + DLQ (Selected)**: If processing fails, retry up to a limit (e.g. 3 times) with delays. On persistent failure, move to a Dead Letter Queue (DLQ) and update status in MongoDB.
  - *Trade-off*: Requires keeping track of retry states, but ensures reliability.

---

## Trade-offs
- **Automatic vs Manual Recovery for DLQ**: Forcing manual retry from DLQ ensures humans review corrupted PDFs, but increases operations load. We implement automatic retry for network errors and manual DLQ review for structural PDF corruption.

---

## Production Considerations
- **Valkey Persistence**: Configure `appendonly yes` and `appendfsync everysec` in Redis/Valkey to ensure streams are not lost on system power loss.
- **Graceful Shutdown**: Workers must listen to `SIGTERM` signals and finish processing the active document before exiting.

---

## Implementation Notes
- If an exception is caught in the worker:
  1. Increment retry counter.
  2. If `retry_count < MAX_RETRIES`, re-add task to stream with a delay.
  3. If `retry_count >= MAX_RETRIES`, save traceback to MongoDB document `error_log`, mark status as `FAILED`, publish to DLQ stream.

---

## Common Mistakes
- **Infinite Retry Loops**: Retrying a corrupted PDF forever, locking up workers.
- **Acknowledge before completion**: Running `XACK` on Redis Stream as soon as the message is read. If the worker crashes, the task is lost. Only ACK after database indexing is complete.

---

## Interview Questions
1. **Q: What is a Dead Letter Queue (DLQ) and when is a message sent there?**
   *A: A DLQ is a secondary message queue. When a task fails repeatedly (exceeds max retries) due to non-transient errors (like a corrupted file or parse crash), it is moved to the DLQ to prevent blocking the main queue.*
2. **Q: How does a worker handle graceful shutdown?**
   *A: The worker registers signal handlers for `SIGINT` and `SIGTERM`. When received, it stops polling Redis for new messages, finishes processing the current file, sends the ACK (if successful), and then exits cleanly.*
