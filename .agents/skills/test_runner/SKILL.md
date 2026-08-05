---
name: test_runner
description: Automated test execution skill. Runs project test suites, analyzes stdout/stderr, extracts stack traces and line numbers, writes logs to .agents/logs/qa_test_results.log, and generates detailed bug reports or success declarations.
---

# Test Runner Skill

## Overview
The `test_runner` skill provides automated test suite execution, log output generation, and error analysis for the QA Tester Agent.

## Core Capabilities & Instructions

### 1. Test Suite Execution
- **Backend Tests**: Run `pytest backend/tests -v` or target test files (`pytest backend/tests/unit/test_auth_unit.py`).
- **Frontend Verification**: Run `npm run lint` or test scripts in `frontend/`.
- **Automated Test Scripts**: If custom automated test scripts are required, create them under `backend/tests/` or `frontend/tests/` and execute them via `terminal_executor`.

### 2. Test Log Generation (`.agents/logs/qa_test_results.log`)
Whenever tests run, write or update the test log at `.agents/logs/qa_test_results.log` using the following structured format:

```text
================================================================================
QA TEST EXECUTION REPORT
Timestamp: <ISO-8601 Timestamp>
Test Suite: <Target Test Suite Name / Path>
================================================================================

SUMMARY:
- Total Tests Run: <Count>
- Passed: <Count>
- Failed: <Count>
- Errors/Crashes: <Count>
- Status: <SUCCESS | FAILURE>

--------------------------------------------------------------------------------
FAILURES & ERRORS:
--------------------------------------------------------------------------------
[FAILURE 1]
- Test File: <file_path>
- Test Function: <function_name>
- Line Number: <line_number>
- Failure Type: <AssertionError / Exception / SyntaxError>
- Exact Error Message: <short_message>

STACK TRACE:
<un-truncated stack trace snippet>

STDOUT / STDERR HIGHLIGHTS:
<relevant logs>
--------------------------------------------------------------------------------

FINAL STATUS STATEMENT:
STATUS: <SUCCESS - ALL TESTS PASSED | FAILURE - BUGS DETECTED>
================================================================================
```

### 3. Log Analysis & Bug Reporting Protocol
- **On Test Failures**:
  1. Extract exact failing file path, line number, exception type, and stack trace.
  2. Append complete details to `.agents/logs/qa_test_results.log`.
  3. Pass a clear, structured bug report to the **Developer Agent** highlighting target root causes and log reference.
- **On All Tests Passing**:
  1. Record clean run in `.agents/logs/qa_test_results.log`.
  2. Output the explicit declaration: `STATUS: SUCCESS - ALL TESTS PASSED`.
