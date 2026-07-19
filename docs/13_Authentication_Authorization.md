# Authentication & Authorization - RBAC & Multi-Tenancy

## Why This Design Exists
KnowledgeOS stores sensitive corporate knowledge. In a SaaS platform, a single tenant leakage incident is catastrophic. This authentication and authorization design enforces strict tenant separation and Role-Based Access Control (RBAC) at the route layer.

---

## Alternative Approaches
- **External Auth Provider (Auth0 / Firebase)**:
  - *Trade-off*: Low code complexity, but adds third-party dependency, subscription costs, and introduces outbound latency on every request.
- **Custom Local JWT Auth (Selected)**: Password hashing with bcrypt, JWT token issuing with short-lived access tokens, long-lived refresh tokens, and in-database session blacklisting.
  - *Trade-off*: Requires robust security code, but operates offline, runs inside Docker, has zero cost, and is completely customizable.

---

## Trade-offs
- **Stateless JWTs vs. Session DB**: Stateless JWTs avoid querying MongoDB on every API request. The trade-off is that token revocation requires short expiry windows (e.g. 15 minutes) or a Redis-based token blacklist.

---

## Production Considerations
- **Environment Secrets**: Never commit the JWT secret keys. Generate them dynamically or load them from a protected `.env`.
- **Role Hierarchy**: Define roles clearly:
  - `Viewer`: Can only query vectors and read conversations.
  - `Editor`: Can upload, edit metadata, and delete documents.
  - `Owner`: Can manage workspace users and billing.

---

## Implementation Notes
- Passwords must be hashed using `passlib` with `bcrypt`.
- JWT payloads contain: `sub` (user_id), `exp`, `role`, `workspaces` (array of allowed workspace IDs).
- Workspace routes must run a dependency resolver verifying `workspace_id` is inside the token claims.

---

## Common Mistakes
- **Storing JWT Secrets in Code**: Hardcoding the JWT key inside `config.py`.
- **JWT Signature Bypass**: Accepting unsigned tokens or failing to verify the signature algorithm.

---

## Interview Questions
1. **Q: How does a Refresh Token flow improve security?**
   *A: It allows access tokens to be extremely short-lived (e.g., 15 minutes). If an access token is intercepted, it expires quickly. The refresh token (stored securely on the client) is exchanged to obtain a new access token, reducing risk.*
2. **Q: What is RBAC and how is it implemented in FastAPI?**
   *A: Role-Based Access Control (RBAC) restricts access to endpoints based on user roles. In FastAPI, we implement this using dependency injection functions, e.g. `Depends(check_role(["Owner", "Editor"]))`, raising an HTTP 403 Forbidden exception on failure.*
