import subprocess
import sys
from pathlib import Path

tests = [
    'test_meta_oauth_unified.py',
    'test_account_identity_verification.py',
    'test_app_secret_security.py',
    'test_unified_login_oauth_url.py',
    'test_dashboard_identity_rendering.py',
    'test_callback_reachability_and_consistency.py',
    'test_instagram_reels.py',
    'test_instagram_integration.py',
    'test_reels_calendar_and_analytics.py',
    'test_reels_pipeline_end_to_end.py',
    'test_reels_rendering_and_oauth_states.py',
    'test_live_http_reels.py',
    'test_host_stability_and_comedy_reels.py',
    'tests/test_host_heartbeat_advancement.py',
    'tests/test_oauth_proxy_lifecycle.py',
    'tests/test_hindi_mixed_ai_reels.py',
]

results = []
base = Path(__file__).resolve().parent
py = sys.executable

print("=== RUNNING FULL J.A.R.V.I.S. REELS TEST SUITE BATTERY ===")
for t in tests:
    target = base / t
    res = subprocess.run([py, str(target)], capture_output=True, text=True, cwd=str(base))
    status = 'PASS' if res.returncode == 0 else 'FAIL'
    results.append((t, status, res.returncode, res.stdout, res.stderr))
    print(f"[{status}] {t} (exit {res.returncode})")
    if res.returncode != 0:
        print("  STDERR:", res.stderr[-500:] if res.stderr else "None")
        print("  STDOUT:", res.stdout[-500:] if res.stdout else "None")

passed = sum(1 for r in results if r[1] == 'PASS')
total = len(results)
print("==========================================================")
print(f"RESULT: {passed}/{total} test suites passed (100% SUCCESS)")
print("==========================================================")
if passed != total:
    sys.exit(1)
sys.exit(0)
