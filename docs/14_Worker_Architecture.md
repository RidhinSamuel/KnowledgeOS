# Worker Architecture - Ingestion Processing

## Why This Design Exists
PDF layout parsing (Docling), text extraction, and vector embedding are highly resource-intensive and CPU-bound operations. Python's Global Interpreter Lock (GIL) can block execution if CPU tasks run in the main thread. 
This worker architecture runs in dedicated containerized instances, consuming tasks from Redis Streams asynchronously using `asyncio` and offloading heavy CPU execution to separate thread pools or sub-processes.

---

## Alternative Approaches
- **Celery / Forking Worker**: Runs tasks by spawning new subprocesses for every execution.
  - *Trade-off*: Good isolation, but spawns heavy processes which slows down execution and uses excessive RAM.
- **Asyncio Worker + Executor Pools (Selected)**: The worker handles the I/O event loop (listening to Redis, downloading documents) and delegates CPU parsing (Docling, PyMuPDF, embeddings) to a thread pool executor.
  - *Trade-off*: Keeps memory footprint flat and handles database I/O concurrently.

---

## Trade-offs
- **Process vs Thread Pool**: Thread pools are lightweight but subject to GIL. Since libraries like Hugging Face (tokenizers) and PyMuPDF release the GIL during native execution, thread pools work extremely well for these libraries without the memory overhead of process pools.

---

## Production Considerations
- **Concurrency Tuning**: Set the size of the worker's thread pool executor based on the available CPU cores of the container (e.g. `n_cores * 2`).
- **Heartbeat & Liveness**: Workers must periodically report their status to Redis/Mongo to ensure they are alive.

---

## Implementation Notes
- The worker runs an infinite loop reading `stream:document_ingestion`.
- It uses `run_in_executor` to isolate CPU-intensive methods:
  ```python
  loop = asyncio.get_running_loop()
  result = await loop.run_in_executor(None, parse_document, file_bytes)
  ```

---

## Common Mistakes
- **Neglecting the GIL**: Running a loop that does heavy string manipulation directly in the async event loop, freezing all concurrent network checks.
- **Loading models per task**: Instantiating the SentenceTransformer embedding model inside the parse function, adding a 5-second model load delay to every task.

---

## Interview Questions
1. **Q: How does `asyncio` interact with thread pools for CPU-heavy tasks?**
   *A: Asyncio is single-threaded. CPU-heavy tasks block the thread, freezing the event loop. We use `loop.run_in_executor(executor, func)` to offload the block to a background OS thread. This allows the asyncio event loop to continue processing network requests.*
2. **Q: What is the impact of PyTorch/SentenceTransformers on worker container sizes?**
   *A: These models use deep learning weights, inflating Docker image size. We use multi-stage builds, separate pip caches, and pre-download model weights into the container image to prevent latency during startup.*
