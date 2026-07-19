# Docker Deployment - Microservices Orchestration

## Why This Design Exists
Deploying microservices directly on bare-metal servers introduces configuration drift (differences in libraries, drivers, Python versions). Containerization using Docker guarantees consistency across development, testing, and production environments, making deployment predictable and reproducible.

---

## Alternative Approaches
- **Kubernetes (K8s)**:
  - *Trade-off*: Highly scalable, but requires immense operational overhead, DNS management, and ingress configuration.
- **Docker Compose (Selected)**: Simplified, single-node multi-container orchestration.
  - *Trade-off*: Limited to single-node deployments, but perfect for development, testing, and initial staging deployments.

---

## Trade-offs
- **Dev-ready Compose vs. Production separation**: Our compose configuration runs database instances alongside applications. In a large production system, databases should be offloaded to managed services (e.g. Atlas MongoDB, managed Qdrant cloud).

---

## Production Considerations
- **Multi-Stage Builds**:
  - Stage 1: Build dependencies and download model weights.
  - Stage 2: Copy only runtime dependencies and application source code, drastically reducing final image size.
- **Nginx Reverse Proxy**: Place Nginx in front of FastAPI to handle TLS termination, limit request sizes, and load-balance.

---

## Implementation Notes
- All services are bound to the internal `knowledge-net` network.
- Only port `80` (Nginx) is mapped to the host's physical network interface.

---

## Common Mistakes
- **Saving State in Containers**: Forgetting to persist MongoDB, Redis, and Qdrant storage directories using Docker volumes, causing data loss on container restart.
- **Putting Secrets in Dockerfile**: Using `ENV JWT_SECRET=xyz` in Dockerfile, making it visible to anyone who has access to the image registry.

---

## Interview Questions
1. **Q: Why are multi-stage Docker builds useful?**
   *A: Multi-stage builds compile packages (e.g., C++ bindings for PyMuPDF) in a builder image, and copy only the final built binaries to the release image. This results in smaller images, faster downloads, and reduced security vulnerabilities.*
2. **Q: How does Nginx reverse proxy protect FastAPI from slow client attacks?**
   *A: Nginx buffers incoming requests. If a client transmits bytes slowly, Nginx buffers the request fully before passing it to FastAPI in milliseconds, preventing FastAPI workers from being blocked by slow clients.*
