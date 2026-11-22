# J.A.R.V.I.S. MARK LVI — VOICE ENGINE UPGRADE ROLLBACK GUIDE

**Document ID:** `docs/VOICE_ROLLBACK_GUIDE.md`  
**System:** J.A.R.V.I.S. MARK LVI Desktop AI Companion  
**Date:** 2026-11-22  
**Status:** FULLY DOCUMENTED & VERIFIED  

---

## 1. BACKUP INVENTORY & ROLLBACK POINTS

Before initiating any voice system modifications, a complete verified snapshot of `D:\JARVIS-AI\mark_lvi_core` was captured and verified:

- **Verified Snapshot Directory:** `D:\JARVIS-AI\backups\backup_pre_voice_master_20261122_184722`
- **Total Files:** 1,167 files (100% matched)
- **Data Integrity:** Exactly 74/74 Reels ledger entries verified in `data/reels_ledger.json`.
- **Git Commit Anchors:**
  - `v56.1.0` candidate release: commit `c03fa69`
  - `v56.0.0` master release: commit `3265594`

---

## 2. EMERGENCY ROLLBACK PROCEDURES

If any unexpected regression occurs, follow these steps to restore the prior stable state:

### Option A: Complete File Restoration from Backup Snapshot

1. **Stop all active J.A.R.V.I.S. processes:**
   ```cmd
   cd /d D:\JARVIS-AI\mark_lvi_core
   stop_jarvis.bat
   ```

2. **Run Restoration Script (Preserves User Data):**
   ```python
   import shutil
   from pathlib import Path

   backup_src = Path(r"D:\JARVIS-AI\backups\backup_pre_voice_master_20261122_184722")
   target_root = Path(r"D:\JARVIS-AI\mark_lvi_core")

   # Overwrite code files while strictly preserving dynamic user databases
   preserve_items = {
       target_root / "data" / "reels_ledger.json",
       target_root / "data" / "memory.json",
       target_root / "config" / "api_keys.json",
   }

   for src_file in backup_src.rglob("*"):
       if src_file.is_file():
           rel = src_file.relative_to(backup_src)
           dst = target_root / rel
           if dst not in preserve_items:
               dst.parent.mkdir(parents=True, exist_ok=True)
               shutil.copy2(src_file, dst)

   print("Rollback complete. Preserved user data and Reels ledger.")
   ```

3. **Verify Integrity:**
   ```cmd
   D:\JARVIS-AI\.venv-jarvis\Scripts\python.exe -m unittest tests/test_skill_router_and_modern_ui.py
   ```

### Option B: Git Reversion to Tag v56.1.0 / v56.0.0

```cmd
cd /d D:\JARVIS-AI\mark_lvi_core
git checkout v56.1.0 -- main.py core/ dashboard/
```

---

## 3. DATA PRESERVATION GUARANTEE

The following assets are protected under the strict preservation policy and will NEVER be overwritten during rollback or migration:
1. `data/reels_ledger.json` (All 74 published and scheduled Reels ledger entries)
2. `data/instagram_accounts.json` (DPAPI encrypted account credentials)
3. `data/memory.json` & `memory/long_term.json` (User facts and preferences)
4. `config/api_keys.json` (Configured local and cloud keys)
5. `data/knowledge/documents/` (Uploaded indexed documents)
