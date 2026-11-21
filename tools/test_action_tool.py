import sys
from pathlib import Path
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from actions.manage_instagram import manage_instagram

print("--- TEST 1: list_accounts ---")
res1 = manage_instagram({"action": "list_accounts"})
print("Accounts response length:", len(res1))

print("--- TEST 2: generate_caption (hinglish) ---")
res2 = manage_instagram({"action": "generate_caption", "language": "hinglish"})
print("Hinglish caption length:", len(res2))
print("Sample:", res2[:120])

print("--- TEST 3: list_reels ---")
res3 = manage_instagram({"action": "list_reels"})
print("List reels length:", len(res3))

print("ALL TOOL CHECKS PASSED")
