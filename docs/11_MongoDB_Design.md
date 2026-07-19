# MongoDB Design - Motor Async Driver

## Why This Design Exists
While vectors belong in Qdrant, relational and transactional metadata (Users, Workspaces, Chat Sessions, Message Logs, Document Ingestion status) belong in a document store. 
We use MongoDB because:
1. **Dynamic Document Schemas**: Flexible JSON structures accommodate changing layout metadata from parsers.
2. **Motor Async Driver**: High-performance, non-blocking Python driver that integrates with FastAPI's event loop.
3. **GridFS**: Native handling of binary files above the 16MB document limit.

---

## Alternative Approaches
- **PostgreSQL**:
  - *Trade-off*: Strict schema and excellent ACID guarantees. However, mapping dynamic OCR metadata blocks and nested chunk tables requires complex migrations.
- **MongoDB (Selected)**:
  - *Trade-off*: Lacks complex multi-table joins (which we don't need), but allows us to store user configurations, parsing logs, and conversation graphs in a natural JSON format.

---

## Trade-offs
- **Referential Integrity**: MongoDB does not enforce foreign keys. We must handle relational validation (e.g. ensuring a workspace exists before linking a document to it) at the FastAPI application layer.

---

## Production Considerations
- **Indexing**: Define unique compound indexes on:
  - Users: `email` (unique).
  - Workspaces: `owner_id` and `name` (unique).
  - Documents: `workspace_id` and `filename`.
  - Sessions: `workspace_id`.
- **Connection Pools**: Configure Motor's `maxPoolSize` to support high concurrency, and ensure connections are reused.

---

## Implementation Notes
- Collections: `users`, `workspaces`, `documents`, `chat_sessions`, `messages`.
- Binary Storage: Use Motor GridFS for storing uploaded PDF binaries. This allows worker microservices to fetch files cleanly over the network.

---

## Common Mistakes
- **Doing Sync Operations in Motor**: Forgetting to `await` database operations, causing silent execution failure or blocking.
- **No Indexing**: Querying sessions by `user_id` without creating an index, causing full database scans on every API chat load.

---

## Interview Questions
1. **Q: Why do we use Motor instead of the standard PyMongo driver?**
   *A: PyMongo is synchronous and blocks the thread while waiting for database queries, which ruins FastAPI's performance. Motor uses `tornado` or `asyncio` to perform non-blocking database queries, allowing the server to handle other requests while waiting for MongoDB.*
2. **Q: How does GridFS handle large files in MongoDB?**
   *A: GridFS splits files into two collections: `fs.files` (storing file metadata) and `fs.chunks` (storing the binary blocks, typically 255KB each). Motor provides async streams to read and write these blocks.*
