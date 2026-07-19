# System Architecture - KnowledgeOS

## Why This Design Exists
The System Architecture defines the deployment topology, network boundaries, container layout, and host resource utilization. KnowledgeOS needs to execute in a decoupled, production-grade microservices environment where web API, message queue, databases, and parser workers are containerized.

---

## Alternative Approaches
- **Single VM Monolith**: Deploying all services inside a single large server with custom systemd units.
  - *Trade-off*: Easy setup initially, but scaling worker threads starves MongoDB resources, and updating individual services requires VM downtime.
- **Containerized Orchestration (Selected)**: Running Docker containers connected via standard virtual networks.
  - *Trade-off*: Requires docker engine configuration, but provides reproducible dev environments and direct path to Kubernetes.

---

## Trade-offs
- **Shared Docker Volumes vs S3/GridFS**: Storing files in a shared Docker volume limits the service to single-node deployments. Using MongoDB GridFS (or an S3 bucket clone) allows workers to run on separate physical nodes without complex network filesystem mount configurations.

---

## Production Considerations
- **Resource Constraints**:
  - Worker container: Allocate 2-4 CPU cores and 4GB RAM minimum (due to Docling / Hugging Face model execution).
  - MongoDB container: Require high disk IOPS (SSD-backed storage).
  - Valkey container: Require high memory speed, configured with `maxmemory` eviction policies.

---

## Implementation Notes
- Containers communicate using internal hostnames: `mongodb:27017`, `valkey:6379`, `qdrant:6333`.
- Internal services are not mapped directly to host ports, making them accessible only via the internal network.

---

## Common Mistakes
- **Exposing Internal Ports**: Exposing database ports (e.g. `27017` or `6379`) to `0.0.0.0` on the host, exposing critical databases to the public web.
- **Running Containers as Root**: Not specifying user permissions inside Dockerfile, allowing processes to execute as root.

---

## Interview Questions
1. **Q: How do containers communicate in Docker Compose, and how is network security configured?**
   *A: Docker Compose automatically creates a single bridge network for the services. Services resolve each other using their service names as hostnames. To secure the network, we avoid mapping database ports to the host (`ports` block) and only expose Nginx.*
2. **Q: What is the impact of placing limits on CPU and Memory inside Docker Compose?**
   *A: It prevents a single service, such as a heavy PDF worker running OCR, from consuming all CPU cycles and memory, which would otherwise crash critical databases or cause the API node to stop responding.*
