---
name: file_modifier
description: Modify source code files adhering to industry standard coding practices, thorough comments, and documentation. Prepares and commits changes locally upon module completion.
---

# File Modifier Skill

## Overview
The `file_modifier` skill governs how source code modifications, bug fixes, and feature implementations are written, documented, and version-controlled.

## Guidelines & Best Practices

### 1. Pre-Change Explanation
- Always briefly explain proposed code changes and rationale before modifying files.
- Highlight the target root cause when fixing bugs based on QA test reports.

### 2. Industry Standard Coding Practices
- **Clean Architecture & Design**: Maintain separation of concerns, DRY (Don't Repeat Yourself), and SOLID principles.
- **Defensive Programming**: Validate inputs, handle edge cases, and avoid silent failures or swallow exceptions.
- **Strict Typing & Structure**: Use type hints (e.g., Python `typing`, TypeScript/JSDoc) and appropriate design patterns.
- **Documentation & Comments**:
  - Provide comprehensive docstrings for classes, functions, and modules.
  - Add inline comments for non-obvious business logic, algorithms, or complex handlers.
  - Retain existing unrelated comments and docstrings.

### 3. Reading QA Feedback
- Inspect `.agents/logs/qa_test_results.log` to extract exact failure locations, line numbers, error types, and stack traces provided by the QA Agent before attempting code edits.

### 4. Git Commit Protocol
- After developing or fixing a module, create a local git commit:
  - Stage relevant files: `git add <files>`
  - Commit with a clear, descriptive message: `git commit -m "feat/fix: <description>"`
- **Git Sync Rule**: Do NOT push commits directly to GitHub via remote API calls while local git tracking is active. Always perform local workspace updates and local terminal git commits.

### 5. Handoff to QA
- Once module changes are written and locally committed, pass control to the **QA Tester Agent** for test verification and final automated testing.
