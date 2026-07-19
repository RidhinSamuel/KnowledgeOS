# backend/test_e2e_live.py
"""
KnowledgeOS - Live End-to-End Integration Tests
================================================
Runs against the ACTUAL running Docker stack (no mocks).
Tests the full flow: Register → Login → Workspace → Upload PDF → Status Poll → Chat

Requirements:
  - Docker stack must be running: docker compose up -d
  - Backend must be healthy at http://localhost:8000

Usage:
  python backend/test_e2e_live.py
  python backend/test_e2e_live.py --base-url http://localhost:8000

Generates a real PDF using reportlab (or falls back to plain bytes if not installed).
"""
import asyncio
import io
import json
import os
import sys
import time
import argparse
import httpx

# ─── Config ──────────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 30.0

TEST_USER = {
    "email": f"e2e_test_{int(time.time())}@knowledgeos.test",
    "password": "TestPass#123",
    "full_name": "E2E Test User",
    "role": "Owner"
}

# ANSI colors for terminal output
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

passed = 0
failed = 0
errors = []

def ok(msg):
    global passed
    passed += 1
    print(f"  {GREEN}✓{RESET} {msg}")

def fail(msg, detail=""):
    global failed
    failed += 1
    errors.append(f"{msg}: {detail}")
    print(f"  {RED}✗{RESET} {msg}")
    if detail:
        print(f"    {YELLOW}→ {detail}{RESET}")

def section(title):
    print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*60}{RESET}")

# ─── PDF Generator ───────────────────────────────────────────────────────────
def make_test_pdf() -> bytes:
    """Create a minimal but real PDF with knowledge content for ingestion testing."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, 780, "KnowledgeOS Test Document")
        c.setFont("Helvetica", 11)
        lines = [
            "This document is used for automated end-to-end testing.",
            "",
            "Key Facts:",
            "- KnowledgeOS is a multi-tenant RAG knowledge base platform.",
            "- It uses Qdrant as a vector database for semantic search.",
            "- MongoDB stores document metadata and chat sessions.",
            "- Redis Streams power the async document ingestion pipeline.",
            "- The system supports multiple workspaces with role-based access.",
            "",
            "Architecture:",
            "The backend is built with FastAPI and supports Server-Sent Events (SSE).",
            "Workers process PDFs using LlamaParse for accurate text extraction.",
            "Semantic chunking uses cosine similarity to group related sentences.",
            "GraphRAG extracts entities and relationships to reduce LLM token usage.",
            "",
            "GraphRAG Token Savings:",
            "Traditional RAG sends 5 raw chunks (2000+ tokens) per query.",
            "GraphRAG reduces this to ~300 tokens using knowledge graph summaries.",
            "This achieves approximately 87% token reduction per query.",
        ]
        y = 750
        for line in lines:
            c.drawString(72, y, line)
            y -= 18
        c.save()
        return buf.getvalue()
    except ImportError:
        # Fallback: minimal valid PDF bytes without reportlab
        # This is a real, standards-compliant 1-page PDF
        pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 120>>stream
BT
/F1 12 Tf
72 720 Td
(KnowledgeOS Test Document - Multi-Tenant RAG Platform) Tj
0 -20 Td
(This PDF tests the full ingestion pipeline end to end.) Tj
ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000274 00000 n 
0000000446 00000 n 
trailer<</Size 6/Root 1 0 R>>
startxref
523
%%EOF"""
        return pdf_content

# ─── Test Runner ─────────────────────────────────────────────────────────────
async def run_tests(base_url: str):
    global BASE_URL
    BASE_URL = f"{base_url}/api/v1"

    print(f"\n{BOLD}KnowledgeOS Live E2E Test Suite{RESET}")
    print(f"Target: {CYAN}{base_url}{RESET}")
    print(f"Time:   {time.strftime('%Y-%m-%d %H:%M:%S')}")

    async with httpx.AsyncClient(base_url=base_url, timeout=TIMEOUT) as client:

        # ── 1. Health Check ───────────────────────────────────────────────────
        section("1. Health Check")
        try:
            r = await client.get("/healthz")
            if r.status_code == 200 and r.json().get("status") in ("healthy", "unhealthy"):
                ok(f"Health endpoint responding — status: {r.json()['status']}")
                services = r.json().get("services", {})
                for svc, state in services.items():
                    if state == "online":
                        ok(f"  Service '{svc}' is {state}")
                    else:
                        fail(f"  Service '{svc}' is {state}")
            else:
                fail("Health endpoint returned unexpected response", str(r.text[:200]))
        except Exception as e:
            fail("Health endpoint not reachable", str(e))
            print(f"\n{RED}Cannot reach backend. Is Docker running?{RESET}")
            print("  Run: docker compose up -d")
            return

        # ── 2. Auth: Register ─────────────────────────────────────────────────
        section("2. Authentication")
        token = None
        try:
            r = await client.post("/api/v1/auth/register", json=TEST_USER)
            if r.status_code == 201:
                ok(f"Registered user: {TEST_USER['email']}")
            elif r.status_code == 400 and "already exists" in r.text:
                ok(f"User already exists (re-run), continuing")
            else:
                fail("Registration failed", f"HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            fail("Register request failed", str(e))

        # Login
        try:
            r = await client.post("/api/v1/auth/login", json={
                "email": TEST_USER["email"],
                "password": TEST_USER["password"]
            })
            if r.status_code == 200 and "access_token" in r.json():
                token = r.json()["access_token"]
                ok(f"Login successful — JWT token acquired")
            else:
                fail("Login failed", f"HTTP {r.status_code}: {r.text[:200]}")
                return
        except Exception as e:
            fail("Login request failed", str(e))
            return

        headers = {"Authorization": f"Bearer {token}"}

        # Verify token rejected on wrong password
        r = await client.post("/api/v1/auth/login", json={
            "email": TEST_USER["email"],
            "password": "WrongPassword!"
        })
        if r.status_code in (401, 400):
            ok("Rejected invalid password correctly")
        else:
            fail("Invalid password was not rejected", f"HTTP {r.status_code}")

        # ── 3. Workspace CRUD ─────────────────────────────────────────────────
        section("3. Workspace Management")
        workspace_id = None
        try:
            r = await client.post("/api/v1/workspaces/",
                headers=headers,
                json={"name": f"E2E Test Workspace {int(time.time())}", "description": "Automated test"}
            )
            if r.status_code == 201:
                workspace_id = r.json().get("_id") or r.json().get("id")
                ok(f"Workspace created — ID: {workspace_id[:8]}...")
            else:
                fail("Workspace creation failed", f"HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            fail("Workspace create request failed", str(e))

        # List workspaces
        if workspace_id:
            r = await client.get("/api/v1/workspaces/", headers=headers)
            if r.status_code == 200 and len(r.json()) > 0:
                ok(f"Listed {len(r.json())} workspace(s)")
            else:
                fail("Workspace list failed", f"HTTP {r.status_code}")

        # ── 4. Tenant Isolation ───────────────────────────────────────────────
        section("4. Multi-Tenant Isolation")
        if workspace_id:
            # Register a second tenant
            tenant2 = {
                "email": f"tenant2_{int(time.time())}@knowledgeos.test",
                "password": "Tenant2Pass#456",
                "full_name": "Tenant Two",
                "role": "Owner"
            }
            r = await client.post("/api/v1/auth/register", json=tenant2)
            r2_login = await client.post("/api/v1/auth/login", json={
                "email": tenant2["email"],
                "password": tenant2["password"]
            })
            if r2_login.status_code == 200:
                token2 = r2_login.json()["access_token"]
                headers2 = {"Authorization": f"Bearer {token2}"}

                # Tenant 2 should NOT be able to access Tenant 1's workspace
                r = await client.get(f"/api/v1/workspaces/{workspace_id}", headers=headers2)
                if r.status_code in (403, 404):
                    ok("Tenant isolation works — Tenant 2 blocked from Tenant 1's workspace")
                else:
                    fail("Tenant isolation FAILED", f"HTTP {r.status_code} — Tenant 2 accessed Tenant 1 data!")
            else:
                fail("Second tenant registration failed", r2_login.text[:100])

        # ── 5. Document Upload ────────────────────────────────────────────────
        section("5. Document Upload & Ingestion")
        document_id = None
        if workspace_id:
            pdf_bytes = make_test_pdf()
            pdf_name = "test_knowledge_doc.pdf"
            print(f"  Generated test PDF ({len(pdf_bytes)} bytes)")

            try:
                r = await client.post(
                    f"/api/v1/documents/upload?workspace_id={workspace_id}",
                    headers=headers,
                    files={"file": (pdf_name, pdf_bytes, "application/pdf")}
                )
                if r.status_code == 201:
                    doc = r.json()
                    document_id = doc.get("_id") or doc.get("id")
                    ok(f"PDF uploaded — Doc ID: {document_id[:8]}... Status: {doc.get('status')}")
                else:
                    fail("PDF upload failed", f"HTTP {r.status_code}: {r.text[:300]}")
            except Exception as e:
                fail("PDF upload request failed", str(e))

        # ── 6. Status Polling ─────────────────────────────────────────────────
        section("6. Document Processing Status Poll")
        if document_id:
            print(f"  Polling for processing status (max 90s)...")
            final_status = None
            for attempt in range(18):  # 18 × 5s = 90s max
                await asyncio.sleep(5)
                try:
                    r = await client.get(f"/api/v1/documents/{document_id}", headers=headers)
                    if r.status_code == 200:
                        status = r.json().get("status")
                        print(f"  [{attempt+1}/18] Status: {status}")
                        if status in ("COMPLETED", "FAILED"):
                            final_status = status
                            break
                except Exception:
                    pass

            if final_status == "COMPLETED":
                ok("Document indexed successfully — COMPLETED")
            elif final_status == "FAILED":
                fail("Document indexing FAILED", "Check worker logs: docker compose logs worker")
            else:
                fail("Document indexing timed out", "Status never reached COMPLETED/FAILED in 90s")

        # ── 7. Chat Session & Streaming ───────────────────────────────────────
        section("7. Chat Session & SSE Streaming")
        session_id = None
        if workspace_id:
            try:
                r = await client.post(
                    f"/api/v1/chat/session?workspace_id={workspace_id}",
                    headers=headers,
                    json={"title": "E2E Test Session"}
                )
                if r.status_code == 201:
                    session_id = r.json().get("_id") or r.json().get("id")
                    ok(f"Chat session created — ID: {session_id[:8]}...")
                else:
                    fail("Chat session creation failed", f"HTTP {r.status_code}: {r.text[:200]}")
            except Exception as e:
                fail("Chat session request failed", str(e))

        if session_id:
            try:
                # Use streaming=True to consume SSE properly
                tokens_received = []
                sources_received = []
                error_received = None

                async with client.stream(
                    "POST",
                    f"/api/v1/chat/session/{session_id}/stream",
                    headers={**headers, "Accept": "text/event-stream"},
                    json={"prompt": "What is this document about? Summarize the key facts."}
                ) as response:
                    if response.status_code != 200:
                        fail("Chat stream endpoint rejected request", f"HTTP {response.status_code}")
                    else:
                        async for line in response.aiter_lines():
                            line = line.strip()
                            if not line.startswith("data: "):
                                continue
                            raw = line[6:]
                            if raw == "[DONE]":
                                break
                            try:
                                event = json.loads(raw)
                                if event.get("event") == "token":
                                    tokens_received.append(event["data"])
                                elif event.get("event") == "sources":
                                    sources_received = event["data"]
                                elif event.get("event") == "error":
                                    error_received = event["data"]
                            except json.JSONDecodeError:
                                pass

                full_response = "".join(tokens_received)
                if full_response:
                    ok(f"SSE streaming worked — {len(tokens_received)} tokens, {len(full_response)} chars")
                    ok(f"Response preview: {full_response[:120].strip()}...")
                else:
                    fail("SSE stream returned no tokens", error_received or "Empty response")

                if sources_received:
                    ok(f"Sources returned: {len(sources_received)} document citations")
                else:
                    print(f"  {YELLOW}⚠ No sources returned (document may not be indexed yet){RESET}")

            except Exception as e:
                fail("Chat streaming request failed", str(e))

    # ── Summary ───────────────────────────────────────────────────────────────
    total = passed + failed
    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  RESULTS: {GREEN}{passed} passed{RESET}{BOLD}, {RED}{failed} failed{RESET}{BOLD} / {total} total{RESET}")
    print(f"{BOLD}{'═'*60}{RESET}")

    if errors:
        print(f"\n{RED}Failures:{RESET}")
        for err in errors:
            print(f"  {RED}✗ {err}{RESET}")

    if failed == 0:
        print(f"\n{GREEN}{BOLD}  🎉 All tests passed! Stack is healthy.{RESET}")
    else:
        print(f"\n{YELLOW}  Tip: docker compose logs --follow for details{RESET}")

    return failed == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KnowledgeOS Live E2E Test Suite")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    args = parser.parse_args()

    try:
        import httpx
    except ImportError:
        print("Installing httpx...")
        os.system(f"{sys.executable} -m pip install httpx")
        import httpx

    success = asyncio.run(run_tests(args.base_url))
    sys.exit(0 if success else 1)
