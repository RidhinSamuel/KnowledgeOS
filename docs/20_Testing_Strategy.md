# Testing Strategy - Unit, Integration, & Load Testing

## Why This Design Exists
A reliable enterprise application requires verification pipelines that run automatically on every code push (CI/CD). This testing strategy outlines how to test FastAPI routes, auth validation, Redis stream message loops, and Qdrant retrieval features without relying on external cloud APIs.

---

## Alternative Approaches
- **Mocking All Services**: Simulating database responses using python mocks.
  - *Trade-off*: Fast execution, but misses issues like incorrect mongo syntax or bad qdrant schema configurations.
- **Testcontainers / Integration Testing (Selected)**: Running tests against actual lightweight Docker containers (like `mongomock` or testcontainers) for unit tests, and full docker-compose integration scripts.
  - *Trade-off*: Slightly slower, but guarantees that the system runs identically to production.

---

## Trade-offs
- **Hugging Face Mocking**: Loading real deep learning embedding models during tests slows down CI runs. We override the embedding generator to return static mock vector floats of matching dimensions.

---

## Production Considerations
- **CI/CD Integration**: Run automated `pytest` on every GitHub Pull Request.
- **Coverage targets**: Maintain a minimum of 80% code coverage on core routes (auth, workspaces, documents, chat).

---

## Implementation Notes
- Write test scripts using `pytest` and `httpx.AsyncClient`.
- Use `mongomock` or a dedicated test database namespace in MongoDB.

---

## Common Mistakes
- **Leaking Test Data**: Running tests on the local development databases, erasing user information.
- **Hardcoded Sleep Times**: Using `time.sleep(5)` to wait for workers to process documents. Instead, poll the document status API with a timeout.

---

## Interview Questions
1. **Q: How do you write an integration test for an asynchronous background worker?**
   *A: 1. Start a local MongoDB and Redis instance. 2. Start the worker listener. 3. Upload a sample document via the API client. 4. Run a loop polling the document status until it changes from `PENDING` to `COMPLETED` (or hits a timeout). 5. Assert that vectors are present in the collection.*
2. **Q: How do you mock external LLM calls during tests?**
   *A: In LangChain, we mock the LLM client by using a custom fake LLM class (`FakeMessagesListChatModel` or overriding the API call return value) to return deterministic mock responses.*
