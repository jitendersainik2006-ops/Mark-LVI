# J.A.R.V.I.S. MARK LVI — UPDATE & MIGRATION GUIDE

This document explains the safe update and rollback mechanism for J.A.R.V.I.S. Mark LVI.

---

## 1. UPDATE PHILOSOPHY & SAFETY GUARANTEES

J.A.R.V.I.S. Mark LVI enforces strict safety invariants during updates:
1. **Never Overwrites User Data:** Your personal memories (`memory/`), conversation histories, uploaded documents (`data/knowledge/`), and credentials (`config/api_keys.json`) are completely untouched.
2. **Pre-Update Automatic Snapshot:** Before any application files are updated, an automated backup of existing core modules is saved to `backups/pre_update_<version>_<timestamp>/`.
3. **SHA-256 Package Integrity:** Update packages are checked against `SHA256_MANIFEST.txt` before installation. Any modified or corrupted file aborts the update immediately.
4. **Zero Silent External Downloads:** Updates are initiated only with explicit user consent.

---

## 2. HOW TO APPLY AN UPDATE

### Method A: One-Click Update Package
1. Download the new release package (e.g. `JARVIS_Mark_LVI_Update_v56.x.zip`).
2. Extract the package into a temporary folder.
3. Open a terminal or Command Prompt in your J.A.R.V.I.S. installation directory.
4. Run:
   ```cmd
   python installer/updater.py --apply "C:\path\to\extracted_update"
   ```
5. The updater will:
   - Validate all file hashes against the manifest.
   - Create a pre-update snapshot.
   - Replace application code modules safely.
   - Update `config/version.json`.
6. Restart J.A.R.V.I.S. via `launch_jarvis.bat`.

---

## 3. HOW TO ROLL BACK AN UPDATE

If an update causes incompatibility with your local environment:
1. Stop running J.A.R.V.I.S. processes using `stop_jarvis.bat`.
2. Locate your pre-update snapshot folder inside `backups/` (e.g. `backups/pre_update_56.1.0_20261119/`).
3. Run the rollback command:
   ```cmd
   python installer/updater.py --rollback "backups/pre_update_56.1.0_20261119"
   ```
4. All application code modules will be reverted to the exact pre-update state.
5. Restart J.A.R.V.I.S. via `launch_jarvis.bat`.
