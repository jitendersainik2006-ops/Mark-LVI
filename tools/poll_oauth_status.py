import json
from pathlib import Path

p = Path("D:/JARVIS-AI/mark_lvi_core/data/instagram_accounts.json")
if p.exists():
    d = json.loads(p.read_text(encoding="utf-8"))
    mentos = d.get("mentos_life_gym", {})
    print(f"Status: {mentos.get('status')}")
    print(f"Username: @{mentos.get('username')}")
    print(f"User ID: {mentos.get('instagram_user_id')}")
    print(f"Page ID: {mentos.get('facebook_page_id')}")
    print(f"Permissions: {mentos.get('permissions')}")
    print(f"Connected At: {mentos.get('connected_at')}")
else:
    print("File not found")
