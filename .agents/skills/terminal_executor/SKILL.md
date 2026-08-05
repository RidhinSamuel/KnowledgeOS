---
name: terminal_executor
description: Execute terminal commands safely for running test suites, executing build tools, running lint checks, and managing local git commits.
---

# Terminal Executor Skill

## Overview
The `terminal_executor` skill governs command execution in the workspace terminal environment for testing, building, running custom scripts, and version control operations.

## Guidelines & Best Practices

### 1. Command Execution Protocol
- Always specify explicit working directory `Cwd`.
- Do NOT use `cd` in command lines. Specify working directory via environment or `Cwd` tool parameter.
- Limit output length for commands that produce long outputs.
- Never ignore non-zero exit codes or silent command errors.

### 2. Environment & Project Commands
- **Backend Testing**: `pytest backend/tests`
- **Frontend Linting**: `npm run lint` (inside `frontend/`)
- **Git Commit Workflow**:
  - `git add <files>`
  - `git commit -m "<message>"`

### 3. Background & Long-Running Tasks
- For long-running commands, use background execution.
- Rely on system notifications when tasks complete rather than polling status loops.
