# Security & Compliance - Tenant Isolation

## Why This Design Exists
Multi-tenant SaaS products are primary targets for data extraction attacks. This security document provides the coding guidelines, encryption policies, and isolation strategies to keep KnowledgeOS resilient.

---

## Alternative Approaches
- **Physical Isolation**: Deploying dedicated servers for each tenant.
  - *Trade-off*: Impractical for small-to-medium businesses due to cost.
- **Logical Isolation (Selected)**: Logical workspace segregation, JWT enforcement, CORS configuration, input sanitization, and strict vector filtering.
  - *Trade-off*: Requires continuous monitoring and unit-testing, but allows high-density resource utilization.

---

## Trade-offs
- **Bcrypt Hashing Rounds**: High work factors (e.g. 14 rounds) improve password strength against brute-force attacks but increase API response time on login. We use a standard work factor of 12 as a balance.

---

## Production Considerations
- **Environment Secrets**: Secrets (like JWT keys, database passwords, and API keys) are injected into containers at runtime from `.env` files.
- **Data Encryption**:
  - In Transit: Enforce HTTPS using Nginx with TLS 1.3.
  - At Rest: MongoDB and Qdrant storage directories should use volume-level disk encryption (e.g., LUKS or AWS EBS encryption).

---

## Implementation Notes
- Set secure headers in Nginx: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Content-Security-Policy`.
- File upload filenames are stripped and randomized using UUIDs to prevent directory traversal attacks (e.g. `../../../path`).

---

## Common Mistakes
- **SQL / NoSQL Injection**: Building raw database query strings. Always use parameterized queries (Motor / PyMongo query builders).
- **Exposing Tracebacks in API**: Returning raw python tracebacks in HTTP 500 error responses, which reveals package structures to potential attackers.

---

## Interview Questions
1. **Q: How does the system prevent Directory Traversal attacks during file uploads?**
   *A: When a file is uploaded, the original name is sanitized. We discard the user-controlled file path, save the file using a generated UUID name on disk/GridFS, and store the mapping in MongoDB.*
2. **Q: How is cross-tenant leakage prevented in Qdrant hybrid searches?**
   *A: Every query filter is constructed programmatically inside a dependency resolver that extracts the tenant's `workspace_id` from the JWT token. The filter is appended directly to the vector query, ensuring Qdrant never returns nodes from other workspaces.*
