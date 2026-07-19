# Observability - Metrics, Logs, & Traces

## Why This Design Exists
In distributed microservices, identifying the source of latency or failure across service boundaries is extremely difficult. Observability designs establish a unified trace-id passed from HTTP calls through message queues to background workers.
This design incorporates:
1. **Structured Logging (Structlog)**: JSON format logs for machine parsing (ElasticSearch/Loki) and easy debugging.
2. **Metrics Collection (Prometheus & Grafana)**: Real-time graphs tracking request rate, queue size, parser latencies, and memory.
3. **OpenTelemetry Tracing**: End-to-end tracing showing how long database queries, vector updates, and LLM requests take.

---

## Alternative Approaches
- **Print Statement Debugging**:
  - *Trade-off*: Inefficient in production; lacks context (timestamps, trace-ids, file line numbers).
- **Standard Library `logging` Module**:
  - *Trade-off*: Harder to output structured JSON format log lines cleanly compared to `structlog` without verbose boilerplate.
- **OpenTelemetry + Prometheus/Grafana (Selected)**: Industry standards for observability, providing high resolution trace visualization.
  - *Trade-off*: Higher setup complexity.

---

## Trade-offs
- **Sampling Rates**: In high-throughput systems, tracing 100% of queries creates substantial logging overhead and cloud costs. We default to tracing 100% in development and 10% sampling in production.

---

## Production Considerations
- **Log Levels**: Use `INFO` for standard microservice logs and `ERROR` for warnings/tracebacks. Avoid logging personal identifiable information (PII) like names or document text.
- **Alerting thresholds**: Set alerts on worker queue depth (queue > 100 entries for 5 mins) and API error rates (> 1% responses are HTTP 5xx).

---

## Implementation Notes
- Structlog is configured to output JSON formatting in production, and pretty colors in development.
- The `TraceContextPropagator` is used to pass the OpenTelemetry `traceparent` header through Redis Stream payloads.

---

## Common Mistakes
- **Logging Sensitive Data**: Printing raw PDF contents or passwords to stdout.
- **Losing Tracing Context**: Spawning thread pool executors without copying the active context, rendering trace logs disconnected.

---

## Interview Questions
1. **Q: How do you trace a request across an asynchronous queue barrier?**
   *A: We extract the OpenTelemetry span context (trace-id, span-id) from the active FastAPI thread, serialize it into the Redis Stream message metadata, and deserialize it inside the worker before initiating the processing span.*
2. **Q: What are the three pillars of observability?**
   *A: Metrics (aggregates over time like CPU, throughput), Logs (discrete events with context like errors or status updates), and Traces (end-to-end flow of requests across multiple services).*
