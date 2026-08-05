---
name: file_viewer
description: Inspect source code files, Dockerfiles, docker-compose configurations, infrastructure manifests, environment files, and build logs safely without modifying workspace files.
---

# File Viewer Skill

## Overview
The `file_viewer` skill governs read-only file inspection for infrastructure manifests, configuration files, and system logs across the workspace.

## Guidelines & Best Practices

### 1. Target Configuration Files
- **Dockerfiles**: `Dockerfile.backend`, `Dockerfile.frontend`, `Dockerfile.worker`, `Dockerfile`
- **Compose Files**: `docker-compose.yml`, `docker-compose.override.yml`
- **Infrastructure & Proxy Configs**: `infra/nginx/default.conf`, Kubernetes/Helm manifests, environment templates (`.env.example`)
- **Build & System Logs**: `.agents/logs/devops_build.log`, `.agents/logs/qa_test_results.log`

### 2. Inspection Workflow
- Always inspect exact lines of configuration files to detect changes, syntax issues, or exposed port mappings before building images.
- Examine container build logs and health check outputs when diagnosing container initialization failures.
- Do NOT alter or mutate files using this skill. Use read-only inspection tools (`view_file`, `grep_search`).
