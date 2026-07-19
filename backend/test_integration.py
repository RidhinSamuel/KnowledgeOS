# backend/test_integration.py
import asyncio
import time
import httpx

BASE_URL = "http://localhost:8000/api/v1"

async def run_tests():
    print("🚀 Starting KnowledgeOS Integration Test Suite...")
    
    # Use standard async client
    async with httpx.AsyncClient() as client:
        
        # ----------------------------------------------------
        # 1. Register & Login Tenant A
        # ----------------------------------------------------
        print("\n🔑 Test 1: Registering & logging in Tenant A...")
        email_a = f"tenant_a_{int(time.time())}@example.com"
        reg_resp_a = await client.post(f"{BASE_URL}/auth/register", json={
            "email": email_a,
            "password": "strongpassword123",
            "full_name": "Tenant A Administrator",
            "role": "Owner"
        })
        
        if reg_resp_a.status_code != 201:
            print(f"❌ Failed to register Tenant A: {reg_resp_a.text}")
            return
        
        print("✅ Registered Tenant A successfully!")
        
        login_resp_a = await client.post(f"{BASE_URL}/auth/login", json={
            "email": email_a,
            "password": "strongpassword123"
        })
        
        if login_resp_a.status_code != 200:
            print(f"❌ Failed to login Tenant A: {login_resp_a.text}")
            return
            
        token_a = login_resp_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        print("✅ Logged in Tenant A successfully!")

        # ----------------------------------------------------
        # 2. Register & Login Tenant B
        # ----------------------------------------------------
        print("\n🔑 Test 2: Registering & logging in Tenant B...")
        email_b = f"tenant_b_{int(time.time())}@example.com"
        reg_resp_b = await client.post(f"{BASE_URL}/auth/register", json={
            "email": email_b,
            "password": "anotherpassword456",
            "full_name": "Tenant B User",
            "role": "Owner"
        })
        
        if reg_resp_b.status_code != 201:
            print(f"❌ Failed to register Tenant B: {reg_resp_b.text}")
            return
            
        login_resp_b = await client.post(f"{BASE_URL}/auth/login", json={
            "email": email_b,
            "password": "anotherpassword456"
        })
        
        token_b = login_resp_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}
        print("✅ Logged in Tenant B successfully!")

        # ----------------------------------------------------
        # 3. Create Workspace for Tenant A
        # ----------------------------------------------------
        print("\n📁 Test 3: Creating Workspace for Tenant A...")
        ws_resp_a = await client.post(f"{BASE_URL}/workspaces/", headers=headers_a, json={
            "name": "Finance Analytics",
            "description": "Tenant A Financial audits and logs"
        })
        
        if ws_resp_a.status_code != 201:
            print(f"❌ Failed to create workspace: {ws_resp_a.text}")
            return
            
        ws_a_id = ws_resp_a.json()["id"]
        print(f"✅ Created Workspace A (ID: {ws_a_id})!")

        # ----------------------------------------------------
        # 4. Enforce Multi-Tenant Workspace Boundary (Tenant B cannot access Workspace A)
        # ----------------------------------------------------
        print("\n🛡️ Test 4: Enforcing multi-tenant boundary checks...")
        fail_resp = await client.get(f"{BASE_URL}/workspaces/{ws_a_id}", headers=headers_b)
        
        if fail_resp.status_code == 403:
            print("✅ Multi-tenant isolation verified! Tenant B was forbidden from accessing Workspace A.")
        else:
            print(f"❌ Isolation breach! Tenant B retrieved workspace info with status: {fail_resp.status_code}")
            return

        # ----------------------------------------------------
        # 5. Create Chat Session in Workspace A for Tenant A
        # ----------------------------------------------------
        print("\n💬 Test 5: Creating chat session for Tenant A...")
        session_resp = await client.post(
            f"{BASE_URL}/chat/session?workspace_id={ws_a_id}", 
            headers=headers_a,
            json={"title": "Audit Query Q1"}
        )
        
        if session_resp.status_code != 201:
            print(f"❌ Failed to create chat session: {session_resp.text}")
            return
            
        session_id = session_resp.json()["id"]
        print(f"✅ Created chat session successfully (ID: {session_id})!")

        # ----------------------------------------------------
        # 6. Verify Tenant B cannot create session in Workspace A
        # ----------------------------------------------------
        print("\n🛡️ Test 6: Verifying Tenant B cannot hijack Workspace A chat sessions...")
        fail_session_resp = await client.post(
            f"{BASE_URL}/chat/session?workspace_id={ws_a_id}", 
            headers=headers_b,
            json={"title": "Hacker Session"}
        )
        
        if fail_session_resp.status_code == 403:
            print("✅ Chat session hijacking blocked! Tenant B was forbidden.")
        else:
            print(f"❌ Security failure! Tenant B created session: {fail_session_resp.text}")
            return
            
        # ----------------------------------------------------
        # 7. Document Upload (Mock PDF upload)
        # ----------------------------------------------------
        print("\n📄 Test 7: Uploading document to Workspace A...")
        mock_pdf_content = b"%PDF-1.4 Mock PDF file contents for testing upload streams."
        files = {"file": ("audit_report.pdf", mock_pdf_content, "application/pdf")}
        
        upload_resp = await client.post(
            f"{BASE_URL}/documents/upload?workspace_id={ws_a_id}",
            headers=headers_a,
            files=files
        )
        
        if upload_resp.status_code != 201:
            print(f"❌ File upload failed: {upload_resp.text}")
            return
            
        doc_id = upload_resp.json()["id"]
        print(f"✅ Document uploaded (ID: {doc_id})! Ingestion status is currently {upload_resp.json()['status']}.")

        # ----------------------------------------------------
        # 8. Check Status
        # ----------------------------------------------------
        print("\n🔍 Test 8: Querying document status...")
        status_resp = await client.get(f"{BASE_URL}/documents/{doc_id}", headers=headers_a)
        
        if status_resp.status_code == 200:
            print(f"✅ Query successful. Document status: {status_resp.json()['status']}")
        else:
            print(f"❌ Failed to query status: {status_resp.text}")
            return

        print("\n🎉 All core HTTP integration API tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(run_tests())
