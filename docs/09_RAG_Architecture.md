# RAG Architecture - KnowledgeOS

## Why This Design Exists
Standard LLMs suffer from hallucinations, have static knowledge bases, and lack access to private enterprise documents. Retrieval-Augmented Generation (RAG) grounds LLM responses in real-time, tenant-authorized source materials. 
This RAG architecture is designed to support:
1. **Multi-Tenant Filtered Retrieval**: Queries are restricted to the user's active workspace.
2. **Hybrid Search**: Combine keyword matches (BM25 style) and dense vector matches for high accuracy.
3. **SSE Streaming**: Output text tokens to the user as they are generated to decrease perceived latency.

---

## Alternative Approaches
- **Vanilla Vector Search**:
  - *Trade-off*: Fast, but fails on acronyms, product SKUs, and specific keywords.
- **Hybrid Search + Reranking (Selected)**: Query Qdrant with hybrid vectors (dense semantic + sparse keyword filters), perform payload filtering, and run a local cross-encoder reranker before passing context to the LLM.
  - *Trade-off*: Adds 50-100ms retrieval latency, but increases relevance (NDCG) by up to 30%.

---

## Trade-offs
- **Context Window vs. Cost**: Shoving 20 retrieved chunks into the prompt yields more context but increases LLM API token costs and causes the model to suffer from "lost in the middle" phenomena. We restrict to the top 4-6 highest-scoring chunks and use contextual compression.

---

## Production Considerations
- **LLM Rate-Limiting**: RAG endpoints should gracefully handle provider rate limits (HTTP 429) by implementing exponential backoff or failing back to secondary models.
- **History Management**: System prompt must compress conversation history before retrieving contexts to ensure query-based retrieval is aware of chat history.

---

## Implementation Notes
- Context retrieval uses Qdrant's hybrid search API.
- Prompt templates are compiled with system instructions, retrieved context blocks, and conversation history.
- The FastAPI SSE router streams tokens via an `EventSource` protocol.

---

## Common Mistakes
- **Leaking Workspace Boundaries**: Querying Qdrant globally without workspace filters, allowing user A to retrieve user B's workspace documents.
- **Passing Raw Chat History**: Appending pages of raw history to the model instead of summarizing or selecting the last few messages.

---

## Interview Questions
1. **Q: How does Server-Sent Events (SSE) differ from WebSockets for streaming chat responses?**
   *A: SSE is a lightweight, unidirectional protocol built on standard HTTP/1.1. It is perfect for streaming text from server to client, supports auto-reconnection, and is easy to proxy. WebSockets is bidirectional, more complex, and requires persistent TCP connection management.*
2. **Q: Explain "lost in the middle" and how reranking solves it.**
   *A: LLMs tend to ignore information located in the middle of long prompts. Reranking evaluates the retrieved chunks and places only the most semantically relevant chunks at the very top and bottom of the context block, optimizing model attention.*
