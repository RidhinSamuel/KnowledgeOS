# Low-Level Architecture - KnowledgeOS

## Why This Design Exists
The Low-Level Architecture (LLA) details the layout, data structures, and interactions within the python codebase. It ensures developers understand module separation, dependency injection patterns in FastAPI, and consumer routing in workers.

---

## Alternative Approaches
- **Procedural Routing**: Bundling business logic, database queries, and route logic inside single route files.
  - *Trade-off*: Hard to test, duplicate code, and difficult to adapt to framework changes.
- **Clean Layered Architecture (Selected)**: Separating controllers (endpoints), core utilities (security, config), schemas (Pydantic), documents (Mongo models), and external clients (Qdrant, Redis).
  - *Trade-off*: Write more boilerplate upfront, but codebase remains modular and testable.

---

## Trade-offs
- **Dependency Injection (DI) vs Globals**: Using FastAPI's `Depends` system for DB sessions and user authorization. This makes unit testing trivial by allowing session mock overrides.

---

## Production Considerations
- **Connection Pools**: Redis and Motor connections must be initialized on startup using FastAPI lifespan events, rather than re-creating clients on every request.
- **Pydantic Model Validation**: Enforce strict validation rules (like regex on email, strength check on passwords) on incoming API requests.

---

## Implementation Notes
- **Directory Layout**:
  - `backend/app/core/`: Application settings, security, DB connections.
  - `backend/app/api/`: Endpoint routers.
  - `backend/app/models/`: Declarative representation of domain models.
  - `backend/app/services/`: Reusable business logic (e.g., chat orchestration, token management).

---

## Common Mistakes
- **Leaking DB Sessions**: Instantiating client connections globally and forgetting to close them.
- **Circulate Imports**: Importing route handlers into model classes. Use schemas to isolate data models.

---

## Interview Questions
1. **Q: How does FastAPI's lifespan yield work for database connections?**
   *A: Lifespan is a context manager. On startup, we initialize client pools (Motor, Valkey, Qdrant). The yield suspends execution while the app runs. On shutdown, it resumes, letting us close connection pools cleanly.*
2. **Q: How do you mock database dependencies during unit testing?**
   *A: In pytest, we can use FastAPI's `app.dependency_overrides` dictionary to replace live DB session dependencies with mocks or memory databases.*
