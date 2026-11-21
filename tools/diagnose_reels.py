import json
from pathlib import Path

ledger_path = Path("D:/JARVIS-AI/mark_lvi_core/data/reels_ledger.json")
reels_dir = Path("D:/JARVIS-AI/mark_lvi_core/data/reels")

if not ledger_path.exists():
    print("reels_ledger.json does not exist!")
    exit(1)

with open(ledger_path, "r", encoding="utf-8") as f:
    reels = json.load(f)

print(f"Total reels in ledger: {len(reels)}")
files_in_dir = list(reels_dir.glob("*"))
print(f"Total files in data/reels/: {len(files_in_dir)}")
mp4_files = list(reels_dir.glob("*.mp4"))
print(f"MP4 files in data/reels/: {len(mp4_files)}")

for mf in mp4_files:
    print(f"  MP4: {mf.name}, size: {mf.stat().st_size} bytes")

print("\n--- Inspecting ALL reels in ledger ---")
bad_reels = []
for r_id, r in reels.items():
    vp = Path(r.get("video_path", "")) if r.get("video_path") else None
    v_exists = vp.exists() if vp else False
    v_size = vp.stat().st_size if v_exists else 0
    st = r.get("status")
    if not v_exists or v_size == 0 or st in ("waiting_for_approval", "generating", "render_failed"):
        print(f"ID: {r_id} | Status: {st} | Exists: {v_exists} | Size: {v_size} | Path: {r.get('video_path')}")
        if not v_exists or v_size == 0:
            bad_reels.append(r_id)

print(f"\nTotal bad reels (missing or 0 bytes): {len(bad_reels)}")
