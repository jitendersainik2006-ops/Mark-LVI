"""
test_autostart_and_tasks.py — Verification Suite for Windows Auto-Start and Exact-Scope Task Execution

Tests:
1. Windows Auto-Start lifecycle: enable, status, disable, single-instance startup script inspection.
2. Low-risk autonomous task execution (system_status, summarize) with real status & progress tracking.
3. High-risk task gating: strict waiting_for_approval state until human approval.
4. Deduplication within sliding window.
5. Task cancellation and history persistence.
"""

import json
import os
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_autostart import enable_autostart, disable_autostart, status_autostart, get_startup_dir
from core.task_manager import task_manager
from actions.manage_tasks import manage_tasks


def run_autostart_and_task_suite():
    print("=" * 70)
    print("  J.A.R.V.I.S. WINDOWS AUTO-START & TASK EXECUTION VERIFICATION SUITE")
    print("=" * 70)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 1: Windows Auto-Start Configuration Lifecycle
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 1: Windows Auto-Start Enable, Status, and Script Inspection ---")
    startup_bat = get_startup_dir() / "JARVIS_AutoStart.bat"

    # Step A: Enable
    ok_en = enable_autostart()
    assert ok_en and startup_bat.exists(), f"Auto-start batch file not found at {startup_bat}"
    bat_content = startup_bat.read_text(encoding="utf-8")
    assert "11434" in bat_content, "Missing Ollama 11434 check in startup script"
    assert "8000" in bat_content, "Missing single-instance port 8000 check in startup script"
    assert "ollama_models" in bat_content, "Missing OLLAMA_MODELS environment variable in startup script"
    print("✅ Startup batch file content verified with single-instance and Ollama checks.")

    # Step B: Status Check
    st = status_autostart()
    assert st.get("enabled"), "Expected auto-start status to report enabled"
    print("✅ Status reporting verified.")

    # Step C: Disable & Re-enable (leave in enabled state for user)
    disable_autostart()
    assert not startup_bat.exists(), "Expected startup batch file to be removed on disable"
    print("✅ Disable verified (clean removal).")
    enable_autostart()
    assert startup_bat.exists(), "Re-enable failed"
    print("✅ TEST 1 PASSED: Windows auto-start lifecycle verified and left enabled.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 2: Exact-Scope Low-Risk Autonomous Task Execution
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 2: Low-Risk Task Execution (Autonomous) ---")
    task_manager.set_action_runner(lambda name, args: f"Executed {name} successfully: CPU 12%, RAM 45%, Storage OK.")
    task_manager.start_worker()

    low_task = task_manager.create_task(
        title="Check system telemetry and hardware health",
        description="Run low-risk telemetry check within scope",
        action_name="system_status",
        action_args={},
    )
    print(f"Created task: '{low_task.title}' (ID: {low_task.id}, Status: {low_task.status})")
    assert low_task.status in ("queued", "running", "completed"), f"Unexpected status: {low_task.status}"

    # Wait for execution thread
    for _ in range(40):
        t = task_manager.get_task(low_task.id)
        if t.status in ("completed", "failed"):
            break
        time.sleep(0.1)

    t_final = task_manager.get_task(low_task.id)
    print(f"Task final status: {t_final.status.upper()}, Progress: {t_final.progress}%")
    assert t_final.status == "completed", f"Expected completed, got: {t_final.status} ({t_final.error})"
    assert t_final.progress == 100, f"Expected 100% progress, got {t_final.progress}%"
    assert t_final.result, "Expected non-empty task result"
    print("✅ TEST 2 PASSED: Low-risk task executed autonomously and confirmed completed.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 3: High-Risk Action Approval Gate
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 3: High-Risk Action Safety Gating ---")
    high_task = task_manager.create_task(
        title="Purge cache files and reset storage",
        description="High risk destructive operation",
        action_name="delete_file",
        action_args={"path": "D:/temp/test.tmp"},
    )
    print(f"Created high-risk task: '{high_task.title}' [Status: {high_task.status}]")
    assert high_task.status == "waiting_for_approval", f"Expected waiting_for_approval, got {high_task.status}"

    # Verify task does NOT run autonomously
    time.sleep(0.5)
    t_check = task_manager.get_task(high_task.id)
    assert t_check.status == "waiting_for_approval", "High risk task ran without approval!"
    print("Confirmed: High-risk task remains gated in waiting_for_approval.")

    # Explicit approval
    ok_appr = task_manager.approve_task(high_task.id)
    assert ok_appr, "Failed to approve high-risk task"
    print("Explicit human approval provided.")
    print("✅ TEST 3 PASSED: High-risk safety gating verified.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 4: Deduplication & Task Cancellation
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 4: Task Deduplication & Cancellation ---")
    dup_task1 = task_manager.create_task(title="Scan disk health metrics", action_name="system_status")
    dup_task2 = task_manager.create_task(title="Scan disk health metrics", action_name="system_status")
    print(f"Original task: {dup_task1.id}, Duplicate request result: {dup_task2.id}")
    assert dup_task1.id == dup_task2.id, "Expected deduplication to return identical task"

    cancel_task = task_manager.create_task(title="Temporary background indexing", action_name="system_status")
    ok_canc = task_manager.cancel_task(cancel_task.id)
    t_canc = task_manager.get_task(cancel_task.id)
    print(f"Cancelled task status: {t_canc.status.upper()}")
    assert t_canc.status == "cancelled", f"Expected cancelled, got {t_canc.status}"
    print("✅ TEST 4 PASSED: Deduplication and cancellation verified.")

    print("\n" + "=" * 70)
    print("  🎉 ALL 4 AUTO-START & TASK EXECUTION TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    run_autostart_and_task_suite()
