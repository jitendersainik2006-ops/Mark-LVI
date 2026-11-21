import json
from pathlib import Path

p = Path("D:/JARVIS-AI/mark_lvi_core/config/api_keys.json")
if not p.exists():
    print("File does not exist")
    exit(0)

d = json.loads(p.read_text(encoding="utf-8"))
print("Keys:", list(d.keys()))
meta = d.get("meta_app", {})
print("meta_app keys:", list(meta.keys()))
for k, v in meta.items():
    if "secret" in k:
        print(f"  {k}: length={len(str(v))}, is_dpapi={str(v).startswith('dpapi:v1:')}")
    else:
        print(f"  {k}: {v}")
