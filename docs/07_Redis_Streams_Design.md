# Redis Streams Design - KnowledgeOS

## Why This Design Exists
Using RQ or Celery introduces extensive dependencies and heavy worker libraries. Redis Streams (available in Valkey and Redis 5.0+) provide a native, high-performance messaging interface directly inside our existing cache layer. This design implements consumer groups, enabling load balancing across multiple worker processes, message tracking, acknowledgements, and dead-letter processing.

---

## Alternative Approaches
- **Celery / RabbitMQ**:
  - *Trade-off*: Highly robust but adds RabbitMQ operational overhead and Celery's complex scheduling configuration.
- **Redis List (LPUSH/BRPOP)**:
  - *Trade-off*: Simpler queue, but lacks native consumer group scaling, multi-consumer load balancing, message safety (no ACK, messages are lost if worker crashes during task), and visibility into pending tasks.
- **Redis Streams (Selected)**:
  - *Trade-off*: Native to Redis, provides consumer groups, explicit ACKs via `XACK`, pending entries tracking via `XPENDING`, and is extremely fast.

---

## Trade-offs
- **Custom Worker Loop**: Since we aren't using Celery, we must write our own Python listener loop handling connection resilience, worker crashes, message claims, and backoff retries. The reward is a lightweight, dependency-free container that starts in milliseconds.

---

## Production Considerations
- **Memory Footprint**: Stream length should be capped using `XADD ... MAXLEN ~ 10000` to prevent unbounded memory growth.
- **Stale Consumers**: Periodic maintenance loops should run `XPENDING` and claim messages that have been in pending state for too long using `XCLAIM`.

---

## Implementation Notes
- Stream name: `stream:document_ingestion`.
- Consumer group: `group:ingestion_workers`.
- CLI commands:
  - Create group: `XGROUP CREATE stream:document_ingestion group:ingestion_workers $ MKSTREAM`
  - Read: `XREADGROUP GROUP group:ingestion_workers worker_1 COUNT 1 BLOCK 2000 STREAMS stream:document_ingestion >`
  - Ack: `XACK stream:document_ingestion group:ingestion_workers <message_id>`

---

## Common Mistakes
- **Forgetting to XACK**: If a worker processes a task but forgets to ACK it, the message remains in the Pending Entries List (PEL). On worker restart, this task will be re-delivered, causing infinite reprocessing loops.
- **Blocking inside XREAD**: Blocking the async stream loop with sync I/O.

---

## Interview Questions
1. **Q: Explain how XACK, XPENDING, and XCLAIM work together to prevent message loss.**
   *A: When a worker reads a message, Redis adds it to the Pending Entries List (PEL). On completion, `XACK` removes it from PEL. If a worker crashes, `XPENDING` reveals that the message is stuck. Another worker can run `XCLAIM` to take ownership of the message and process it.*
2. **Q: How does the system implement a Dead-Letter Queue (DLQ)?**
   *A: When a worker catches an exception during processing, it increments a `retry_count` in the message payload. If the retry count exceeds a threshold (e.g., 3), the worker publishes the event to `stream:dlq`, runs `XACK` on the original stream, and alerts the system.*
# 
