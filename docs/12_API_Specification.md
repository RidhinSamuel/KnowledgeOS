# API Specification - KnowledgeOS

## Why This Design Exists
A clean, documented API contract is essential for client integration (frontend, CLI tools, external integrations). It defines endpoint routes, HTTP methods, headers, schemas, and return statuses.

---

## Alternative Approaches
- **Auto-generated API Docs (Selected)**: Utilizing FastAPI's automatic Swagger/OpenAPI spec generation.
  - *Trade-off*: Requires maintaining accurate Pydantic models, but keeps documentation dynamically synchronized with the source code.

---

## Trade-offs
- **Bearer Tokens in Headers vs Cookies**: We use JWTs in standard HTTP Authorization Bearer headers. This is stateless, mobile-friendly, and avoids CSRF issues natively, though it requires client-side storage management.

---

## Production Considerations
- **Version Routing**: Prefix all API endpoints with `/api/v1` to allow smooth backwards-compatible releases.
- **Payload Limits**: Restrict file upload sizes via FastAPI dependencies to prevent DDoS via large disk writes.

---

## Implementation Notes
- Core REST Endpoints:
  - `POST /api/v1/auth/register` - Tenant register.
  - `POST /api/v1/auth/login` - Retrieve Access & Refresh tokens.
  - `POST /api/v1/auth/refresh` - Swap refresh token for access token.
  - `GET /api/v1/workspaces` - Retrieve user workspaces.
  - `POST /api/v1/workspaces` - Create a workspace.
  - `POST /api/v1/documents/upload` - Upload document to workspace.
  - `GET /api/v1/documents/{document_id}` - Check parsing status.
  - `POST /api/v1/chat/stream` - SSE chat response.

---

## Common Mistakes
- **No Path Validation**: Allowing access to workspaces without verifying the user is a member of that workspace path parameter.
- **Insecure File Handling**: Accepting files with unsanitized names (e.g. `../../etc/passwd`), exposing directory traversal attacks.

---

## Interview Questions
1. **Q: How does FastAPI translate Pydantic models into OpenAPI documentation?**
   *A: FastAPI inspects the Python type hints and Pydantic field definitions, parses them into JSON Schema drafts, and mounts a dynamic `/docs` route rendering Swagger UI.*
2. **Q: How is Server-Sent Events (SSE) represented in the API response headers?**
   *A: The response must return `Content-Type: text/event-stream` and keeping the connection alive using `Cache-Control: no-cache` and `Connection: keep-alive` headers.*
