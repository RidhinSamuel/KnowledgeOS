# Scaling Strategy - Horizontal & Vertical

## Why This Design Exists
As SaaS platforms grow, they experience traffic spikes (e.g. concurrent document uploads, search queries). The system must scale horizontally without modifications to the code. Decoupling tasks using Redis Streams allows scaling workers independently from the backend API.

---

## Alternative Approaches
- **Vertical Scaling (Scale Up)**: Running on a larger server with more RAM and CPU.
  - *Trade-off*: Simpler operation, but limited by physical hardware limits and represents a single point of failure.
- **Horizontal Scaling (Scale Out) (Selected)**: Adding more container instances.
  - *Trade-off*: Requires load balancing and distributed data store management, but scales infinitely.

---

## Trade-offs
- **Worker Scale vs Database Bottlenecks**: Scaling workers from 1 to 20 instances increases PDF processing speed, but can overwhelm MongoDB and Qdrant with concurrent writes. We implement database connection pools and rate-limit worker thread sizes to balance load.

---

## Production Considerations
- **Stateless APIs**: Ensure the FastAPI application stores no local state (e.g., sessions, local uploads). Any state must belong in MongoDB, Redis, or Qdrant.
- **Qdrant Multi-Tenancy Scaling**: Scale Qdrant using shards and replicas, isolating large enterprise tenants to dedicated nodes if necessary.

---

## Implementation Notes
- Scale workers horizontally in Docker Compose using:
  `docker compose up -d --scale worker=4`
- Redis stream partitioning: Split queue streams by tenant if one tenant's load starves other tenants.

---

## Common Mistakes
- **Session Locking**: Storing user sessions in FastAPI RAM instead of Redis, preventing requests from routing to other instances.
- **Unbounded Scaling**: Scaling worker containers without CPU/Memory limits, causing host starvation and crash.

---

## Interview Questions
1. **Q: How does a stateless API design enable horizontal scaling?**
   *A: Since the API holds no state, a request from User A can be served by Instance 1, and the next request by Instance 2. A load balancer can distribute traffic evenly without needing sticky sessions.*
2. **Q: How do you scale database connections when scaling microservice instances?**
   *A: Every container has a local connection pool. We must configure the database (MongoDB/Redis) to accept max connections equal to `number_of_containers * connection_pool_size`. If we scale containers, we must increase the database server's socket limits.*
