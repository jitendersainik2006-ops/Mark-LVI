"""
test_phase1_to_phase5.py — Comprehensive Verification Suite

Validates Phase 1 through Phase 5 additions:
1. Core Prompt & Reasoning enhancements (multilingual rules, multi-step decomposition, ambiguous clarifying questions).
2. Persistent Personal Memory (credential filtering, source tracking, assumptions vs user facts, edit/delete/toggle).
3. Background Task Manager (task lifecycle, allowlist vs approval gate, deduplication, persistence).
4. Discovered Action Tools (manage_memory, manage_tasks TOOL schemas and handlers).
5. Dashboard REST APIs & Security (FastAPI endpoints for tasks & memory with authentication).
"""

import os
import sys
import json
import time
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def test_phase1_prompt():
    print("\n--- TEST 1: Phase 1 Prompt & Multilingual Guidelines ---")
    prompt_file = ROOT / "core" / "prompt.txt"
    assert prompt_file.exists(), "prompt.txt not found"
    content = prompt_file.read_text(encoding="utf-8")

    assert "ASK a short, direct clarifying question first" in content, "JUDGEMENT clarifying question rule missing"
    assert "CONVERSATION CONTEXT & REASONING" in content, "Context & reasoning section missing"
    assert "break the problem down into logical, sequential steps" in content, "Sequential decomposition rule missing"
    assert "ENGLISH:" in content, "English language rule missing"
    assert "HINDI" in content, "Hindi language rule missing"
    assert "HINGLISH:" in content, "Hinglish language rule missing"
    assert "Never ask the user for information, parameters, or choices they already provided" in content, "Context continuity rule missing"
    print("✅ Prompt enhancements verified: Judgment clarification, multi-step decomposition, English/Hindi/Hinglish, and context rules present.")

def test_phase2_memory():
    import tempfile
    import memory.memory_manager as mm
    temp_mem = Path(tempfile.gettempdir()) / "test_long_term.json"
    if temp_mem.exists():
        try: temp_mem.unlink()
        except: pass
    mm.MEMORY_PATH = temp_mem

    from memory.memory_manager import (
        contains_credentials,
        redact_credentials,
        is_memory_enabled,
        set_memory_enabled,
        remember,
        forget,
        edit_memory,
        delete_memory,
        all_entries_for_ui,
        format_memory_for_prompt,
        search_memory,
    )

    set_memory_enabled(True)

    # 1. Credential detection & redaction
    assert contains_credentials("sk-proj-1234567890abcdef1234567890"), "Failed to detect OpenAI key pattern"
    assert contains_credentials("AIzaSyA123456789012345678901234567890"), "Failed to detect Gemini key pattern"
    assert contains_credentials("password: secretpassword123"), "Failed to detect password pattern"
    assert not contains_credentials("My favorite color is dark blue"), "False positive on normal text"

    redacted = redact_credentials("Here is my secret password: mysecret123 and sk-1234567890123456789012")
    assert "[REDACTED_CREDENTIAL]" in redacted, "Credential was not redacted"
    assert "mysecret123" not in redacted, "Secret leaked in redacted text"

    # 2. Source tracking (user_fact vs assumption)
    remember("test_user_food", "Biryani", category="preferences", source="user_fact")
    remember("test_inferred_job", "Software Engineer", category="identity", source="inferred")

    entries = all_entries_for_ui()
    user_entry = next((e for e in entries if e["key"] == "test_user_food"), None)
    inferred_entry = next((e for e in entries if e["key"] == "test_inferred_job"), None)

    assert user_entry is not None, "User fact was not saved"
    assert user_entry["source"] == "user_fact", f"Expected source user_fact, got {user_entry['source']}"
    assert inferred_entry is not None, "Inferred fact was not saved"
    assert inferred_entry["source"] == "inferred", f"Expected source inferred, got {inferred_entry['source']}"

    # Verify assumption tag in prompt
    memory_dict = {
        "identity": {"test_inferred_job": {"value": "Software Engineer", "source": "inferred"}},
        "preferences": {"test_user_food": {"value": "Biryani", "source": "user_fact"}},
    }
    prompt_block = format_memory_for_prompt(memory_dict)
    assert "[unconfirmed assumption]" in prompt_block, "Inferred assumption tag missing in prompt block"

    # 3. Memory edit & delete
    ok_edit = edit_memory("preferences", "test_user_food", "Tacos", source="user_fact")
    assert ok_edit, "edit_memory returned False"
    assert "Tacos" in search_memory("test_user_food"), "Updated memory value not reflected in search"

    ok_del = delete_memory("preferences", "test_user_food")
    assert ok_del, "delete_memory returned False"
    delete_memory("identity", "test_inferred_job")

    # 4. Toggle memory
    set_memory_enabled(False)
    assert not is_memory_enabled(), "is_memory_enabled() should return False"
    assert format_memory_for_prompt(memory_dict) == "", "format_memory_for_prompt should return empty string when disabled"
    assert "disabled" in search_memory("anything").lower(), "search_memory should report disabled"

    # Restore memory enabled
    set_memory_enabled(True)
    assert is_memory_enabled(), "is_memory_enabled() should return True after re-enabling"
    print("✅ Memory subsystem verified: Credential redaction, source tracking, prompt formatting, edit/delete, and toggle controls working perfectly.")

def test_phase3_task_manager():
    print("\n--- TEST 3: Phase 3 Persistent Task Manager & Execution Engine ---")
    from core.task_manager import TaskManager
    import tempfile
    test_file = Path(tempfile.gettempdir()) / "test_tasks.json"
    if test_file.exists():
        try: test_file.unlink()
        except: pass

    tm = TaskManager(tasks_file=test_file)



    # 1. Low-risk routine task (Autonomous execution allowlist)
    t1 = tm.create_task(
        title="Check system health",
        action_name="system_status",
        action_args={},
        priority="low"
    )
    assert t1.status == "queued", f"Expected low-risk task to be queued, got {t1.status}"

    # 2. High-risk consequential task (Approval gate)
    t2 = tm.create_task(
        title="Delete temp files",
        action_name="delete_file",
        action_args={"path": "C:/temp/test.txt"},
        priority="high"
    )
    assert t2.status == "waiting_for_approval", f"Expected high-risk task to be waiting_for_approval, got {t2.status}"

    # 3. Human approval gate
    ok_approve = tm.approve_task(t2.id)
    assert ok_approve, "approve_task returned False"
    t2_updated = tm.get_task(t2.id)
    assert t2_updated.status == "queued", f"Expected approved task to be queued, got {t2_updated.status}"

    # 4. Task cancellation
    ok_cancel = tm.cancel_task(t1.id)
    assert ok_cancel, "cancel_task returned False"
    assert tm.get_task(t1.id).status == "cancelled", "Expected task to be cancelled"

    # 5. Task deduplication (rapid duplicate calls within window)
    t3 = tm.create_task(title="Search latest Python release", action_name="web_search", action_args={"query": "python 3.13"})
    t3_dup = tm.create_task(title="Search latest Python release", action_name="web_search", action_args={"query": "python 3.13"})
    assert t3.id == t3_dup.id, f"Deduplication failed: created two distinct tasks ({t3.id} vs {t3_dup.id})"

    # 6. Persistence across reloads
    tm2 = TaskManager(tasks_file=test_file)
    reloaded = tm2.get_task(t3.id)
    assert reloaded is not None, "Task was not persisted to disk"
    assert reloaded.title == "Search latest Python release", "Persisted task data corrupted"

    # Cleanup test file
    if test_file.exists():
        test_file.unlink()

    print("✅ Task Manager verified: Task lifecycle, allowlist vs approval gate, deduplication, and persistence working properly.")

def test_phase4_action_tools():
    print("\n--- TEST 4: Action Tools Discovery & Execution ---")
    from actions.manage_memory import TOOL as MEM_TOOL, manage_memory
    from actions.manage_tasks import TOOL as TASK_TOOL, manage_tasks

    assert MEM_TOOL["name"] == "manage_memory", "manage_memory name mismatch"
    assert callable(MEM_TOOL["handler"]), "manage_memory handler not callable"

    assert TASK_TOOL["name"] == "manage_tasks", "manage_tasks name mismatch"
    assert callable(TASK_TOOL["handler"]), "manage_tasks handler not callable"

    # Test handlers
    status_resp = manage_memory({"action": "status"})
    assert "Personal memory is currently" in status_resp, f"Unexpected manage_memory status response: {status_resp}"

    task_list_resp = manage_tasks({"action": "list", "filter": "all"})
    assert "task" in task_list_resp.lower(), f"Unexpected manage_tasks list response: {task_list_resp}"

    print("✅ Action tools verified: manage_memory and manage_tasks tools are valid and responsive.")

def test_phase5_dashboard_api():
    print("\n--- TEST 5: Dashboard Server API & Auth Gate ---")
    import json
    import time
    import tempfile
    from dashboard.server import DashboardServer
    import core.task_manager as ctm
    import memory.memory_manager as mm

    ctm.task_manager._tasks_file = Path(tempfile.gettempdir()) / "test_api_tasks.json"
    ctm.task_manager._tasks = {}
    mm.MEMORY_PATH = Path(tempfile.gettempdir()) / "test_api_memory.json"

    def run_coro(coro):
        stack = [coro]
        result = None
        while stack:
            current = stack[-1]
            try:
                val = current.send(result)
                if hasattr(val, "send"):
                    stack.append(val)
                    result = None
                else:
                    result = val
            except StopIteration as exc:
                stack.pop()
                result = exc.value
        return result

    server = DashboardServer()

    def find_endpoint(path, method):
        for r in server.app.routes:
            if r.path == path and method in getattr(r, "methods", []):
                return r.endpoint
        return None

    class MockRequest:
        def __init__(self, headers=None, json_data=None):
            self.headers = headers or {}
            self._json_data = json_data or {}
            self.client = type("Client", (), {"host": "127.0.0.1"})()

        async def json(self):
            return self._json_data

    get_tasks = find_endpoint("/api/tasks", "GET")
    get_memory = find_endpoint("/api/memory", "GET")
    create_task = find_endpoint("/api/tasks", "POST")
    cancel_task = find_endpoint("/api/tasks/{task_id}/cancel", "POST")
    save_memory = find_endpoint("/api/memory", "POST")
    toggle_memory = find_endpoint("/api/memory/toggle", "POST")

    # 1. Unauthenticated requests must receive 401
    unauth_req = MockRequest()
    resp_unauth_tasks = run_coro(get_tasks(unauth_req))
    assert resp_unauth_tasks.status_code == 401, f"Expected 401 for unauthenticated /api/tasks, got {resp_unauth_tasks.status_code}"

    resp_unauth_mem = run_coro(get_memory(unauth_req))
    assert resp_unauth_mem.status_code == 401, f"Expected 401 for unauthenticated /api/memory, got {resp_unauth_mem.status_code}"

    # 2. Authenticated requests with token
    test_token = "test_bearer_token_12345"
    server._tokens[test_token] = time.time()
    server._token_keys[test_token] = "TESTKEY1"
    auth_headers = {"authorization": f"Bearer {test_token}"}

    # Test GET /api/tasks
    auth_req = MockRequest(headers=auth_headers)
    resp_tasks = run_coro(get_tasks(auth_req))
    assert resp_tasks.status_code == 200, f"Expected 200 for authenticated /api/tasks, got {resp_tasks.status_code}"
    tasks_data = json.loads(resp_tasks.body.decode("utf-8"))
    assert tasks_data.get("ok") is True, f"Response ok field not True: {tasks_data}"
    assert "tasks" in tasks_data, "tasks field missing in response"

    # Test POST /api/tasks (Create task)
    create_req = MockRequest(
        headers=auth_headers,
        json_data={"title": "Dashboard Test Task", "priority": "high", "description": "API verification"}
    )
    resp_create = run_coro(create_task(create_req))
    assert resp_create.status_code == 200, f"Failed to create task via API: {resp_create.body}"
    created_task = json.loads(resp_create.body.decode("utf-8"))["task"]
    task_id = created_task["id"]

    # Test POST /api/tasks/{task_id}/cancel
    cancel_req = MockRequest(headers=auth_headers)
    resp_cancel = run_coro(cancel_task(task_id, cancel_req))
    assert resp_cancel.status_code == 200, f"Failed to cancel task via API: {resp_cancel.body}"

    # Test GET /api/memory
    resp_mem = run_coro(get_memory(auth_req))
    assert resp_mem.status_code == 200, f"Expected 200 for authenticated /api/memory, got {resp_mem.status_code}"
    mem_data = json.loads(resp_mem.body.decode("utf-8"))
    assert mem_data.get("ok") is True, f"Response ok field not True: {mem_data}"
    assert "entries" in mem_data, "entries field missing in response"

    # Test POST /api/memory (Credential security blocking)
    leak_req = MockRequest(
        headers=auth_headers,
        json_data={"category": "secrets", "key": "bad_key", "value": "AIzaSyD-fake-key-for-test-34567890123"}
    )
    resp_leak = run_coro(save_memory(leak_req))
    assert resp_leak.status_code == 400, "API allowed saving credential pattern!"

    # Test POST /api/memory (Valid memory entry)
    save_req = MockRequest(
        headers=auth_headers,
        json_data={"category": "user_preferences", "key": "editor", "value": "VSCode", "source": "user_fact"}
    )
    resp_save = run_coro(save_memory(save_req))
    assert resp_save.status_code == 200, f"Failed to save valid memory: {resp_save.body}"

    # Test POST /api/memory/toggle
    toggle_req = MockRequest(headers=auth_headers, json_data={"enabled": False})
    resp_toggle = run_coro(toggle_memory(toggle_req))
    assert resp_toggle.status_code == 200, f"Failed to toggle memory: {resp_toggle.body}"
    assert json.loads(resp_toggle.body.decode("utf-8"))["enabled"] is False

    # Restore memory enabled to True
    from memory.memory_manager import set_memory_enabled
    set_memory_enabled(True)

    print("✅ Dashboard REST APIs verified: Token auth gating, /api/tasks endpoints, and /api/memory endpoints validated.")

if __name__ == "__main__":
    test_phase1_prompt()
    test_phase2_memory()
    test_phase3_task_manager()
    test_phase4_action_tools()
    test_phase5_dashboard_api()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! PHASES 1 THROUGH 5 FULLY OPERATIONAL.")
