# J.A.R.V.I.S. MARK LVI — UNINSTALLATION & DATA RETENTION GUIDE

This document explains how to safely remove J.A.R.V.I.S. Mark LVI from your Windows computer.

---

## 1. DEFAULT UNINSTALLATION (PRESERVES USER DATA)

When you decide to uninstall J.A.R.V.I.S., the uninstaller distinguishes between **Application Code** and **Personal User Data**:

### What Is Removed by Default:
- Verified J.A.R.V.I.S. background processes (gracefully shut down).
- Desktop Shortcut (`J.A.R.V.I.S. Mark LVI.lnk`).
- Windows Start Menu Shortcut (`J.A.R.V.I.S. Mark LVI.lnk`).

### What Is PRESERVED by Default:
- **Personal Memories & Facts:** `memory/long_term.json`, `data/jarvis_memory.db`.
- **Knowledge Documents:** `data/knowledge/documents/` (all user-uploaded PDFs, notes, text files).
- **Task Ledgers & Content Records:** `data/reels_ledger.json`, `data/reminders.json`.
- **Configuration & Integration Keys:** `config/api_keys.json`.

This ensures that if you reinstall J.A.R.V.I.S. in the future or upgrade to a newer release, your assistant will immediately remember you and retain your personal preferences.

---

## 2. STANDARD UNINSTALL STEPS

1. Double-click **`uninstall_jarvis.bat`** in your installation folder.
2. The prompt will ask:
   ```text
   Are you sure you want to uninstall J.A.R.V.I.S.? (Y/N):
   ```
3. Type `Y` and press Enter.
4. Shortcuts are cleanly removed, processes are shut down, and confirmation is displayed.

---

## 3. COMPLETE PURGE (OPTIONAL / EXPLICIT USER ACTION)

If you are decommissioning the computer or wish to permanently erase all memories and user data:
1. Run:
   ```cmd
   python installer/uninstall_jarvis.py --purge-data
   ```
2. The uninstaller will issue a critical safety warning:
   ```text
   Are you ABSOLUTELY sure you want to permanently delete all personal data? (Type 'PERMANENTLY DELETE'):
   ```
3. Type `PERMANENTLY DELETE` to purge all local files.
4. Delete the remaining installation directory manually from File Explorer.
