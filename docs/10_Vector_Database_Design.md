# Vector Database Design - Qdrant

## Why This Design Exists
Retrieval performance and reliability depend on how data is indexed in the vector database. We use Qdrant due to its first-class support for:
1. **Payload-based Multi-Tenancy**: Filtering vectors by metadata in O(1) time before semantic distance calculations.
2. **Hybrid Search**: Storing dense embeddings alongside sparse vectors in the same collection.
3. **Rust-based Engine**: Sub-millisecond search latencies on millions of vectors.

---

## Alternative Approaches
- **Database-per-Tenant Collections**: Creating a unique Qdrant collection for each workspace.
  - *Trade-off*: Becomes extremely expensive as collection numbers scale; each collection consumes dedicated RAM and creates system files.
- **Single Collection with Payload Filtering (Selected)**: Indexing all documents into a single collection, using `workspace_id` as a payload property.
  - *Trade-off*: Requires indexing payload fields (`keyword` index), but allows the database to easily scale to millions of tenants.

---

## Trade-offs
- **Cosine vs. Euclidean Distance**: Cosine similarity is selected. Since we use normalized Hugging Face embeddings, Cosine similarity scales values cleanly between `-1` and `1`, making threshold filtering easy.

---

## Production Considerations
- **Indexing Payloads**: Create a `keyword` index on `workspace_id` and `user_id` inside Qdrant. Without this, Qdrant does full collection scans before checking payloads, causing query latency to explode as database size grows.
- **HNSW Index Parameters**: Optimize `m` and `ef_construct` for vector search precision vs build time.

---

## Implementation Notes
- Qdrant Collection Name: `knowledge_chunks`.
- Vector payload structure:
  ```json
  {
    "workspace_id": "string",
    "user_id": "string",
    "document_id": "string",
    "text": "string",
    "page_number": 12
  }
  ```

---

## Common Mistakes
- **No Payload Index**: Querying with filters without setting payload field schemas in Qdrant, converting index searches into full table scans.
- **Mismatching Dimensions**: Generating 768-dimension embeddings but defining Qdrant collection with 384 dimensions.

---

## Interview Questions
1. **Q: How does Qdrant guarantee multi-tenancy isolation at the index level?**
   *A: Qdrant uses payload indexing. During search, a query filter `{"workspace_id": "XYZ"}` is processed first. Qdrant's search engine restricts the HNSW graph traversal solely to nodes that match the filter, ensuring zero tenant leakage.*
2. **Q: What is the difference between dense and sparse vectors, and why do we use both?**
   *A: Dense vectors (e.g. 384 dimensions) capture abstract semantic meanings (e.g., matching "dog" and "canine"). Sparse vectors (e.g., BM25) capture exact keywords (e.g. matching "serial number SN-998"). Hybrid search combines both scores to retrieve the best of both worlds.*
