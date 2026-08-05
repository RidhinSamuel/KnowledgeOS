---
name: container_tester
description: Build, deploy, and verify containerized stack applications. Manages container lifecycle, inspects backend/frontend container logs, and asserts service readiness.
---

# Container Tester Skill

## Overview
The `container_tester` skill governs building Docker containers, deploying services, monitoring container runtime statuses, and inspecting backend/frontend container logs.

## Guidelines & Best Practices

### 1. Container Deployment Workflow
- Execute container stack build and background startup:
  ```bash
  docker compose down && docker compose up --build -d
  ```
- Monitor running container services:
  ```bash
  docker compose ps
  ```

### 2. Service & Port Verification
- **Backend Container**: Port `8000` (Healthcheck endpoint: `http://localhost:8000/healthz`)
- **Frontend Container**: Port `5173` or `80` (HTTP web interface)
- **Database/Worker Services**: MongoDB (`27017`), Redis/Valkey (`6379`), Qdrant (`6333`)

### 3. Log Inspection & Troubleshooting
- Inspect container output streams if any container fails to boot or returns errors:
  ```bash
  docker compose logs backend
  docker compose logs frontend
  docker compose logs worker
  ```
- Record error logs in `.agents/logs/devops_build.log`.
- Route container failure details back to Developer Agent for code or configuration fixes.
