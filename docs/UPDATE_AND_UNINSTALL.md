# J.A.R.V.I.S. MARK LVI — UPDATE AND UNINSTALL GUIDE

**Application:** J.A.R.V.I.S. Mark LVI Core  
**Platform:** Windows 10 / Windows 11 (64-bit x64)

---

## 1. UPDATING J.A.R.V.I.S. MARK LVI

Upgrades are designed to be seamless, non-destructive, and preserve all personal memories, chat history, custom workflows, and configured integrations.

### Step 1: Gracefully Stop Running Services
Before applying any updates, stop all active J.A.R.V.I.S. instances and background services:
```cmd
stop_jarvis.bat
```
Verify that port `8000` is free:
```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
```

### Step 2: Create a Backup of User Data
Always back up your local user data directory before updating:
```powershell
Copy-Item -Path "data" -Destination "..\backup_jarvis_data_$(Get-Date -Format 'yyyyMMdd_HHmmss')" -Recurse
```

### Step 3: Apply the Update

#### Option A — Via Git (Developer / Source Install):
```cmd
git fetch origin
git pull origin main
```
If dependencies were updated:
```cmd
..\.venv-jarvis\Scripts\python.exe -m pip install -r requirements.txt
```

#### Option B — Via Release Archive (Standalone / Portable):
1. Extract the new release package to a temporary folder.
2. Copy over all updated application files (`core/`, `dashboard/`, `actions/`, `providers/`, `tools/`, `installer/`).
3. **DO NOT overwrite** your existing `data/` or `config/` folders.

### Step 4: Verify Post-Update State
Launch the application:
```cmd
launch_jarvis.bat
```
Navigate to `http://127.0.0.1:8000/app` and verify:
- Previous chat sessions and memories are present.
- Status indicators display green.
- Voice models and audio devices are operational.

---

## 2. UNINSTALLING J.A.R.V.I.S. MARK LVI

J.A.R.V.I.S. provides a clean, user-controlled uninstallation process with zero hidden registry hooks or orphan services.

### Method 1: Automated Script Uninstallation (Recommended)

1. Double-click **`uninstall_jarvis.bat`** in your application directory.
2. The uninstaller will:
   - Gracefully terminate any running J.A.R.V.I.S. processes (PID termination on port 8000).
   - Remove the Windows Startup launcher (`JARVIS_AutoStart.bat` from `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`).
   - Remove Desktop shortcuts (`J.A.R.V.I.S. Mark LVI.lnk`).
   - Remove Start Menu program group shortcuts.
3. You will be prompted:
   ```
   Do you want to delete personal memories, uploaded documents, and local database? [Y/N]:
   ```
   - Press **N** to keep your data safe for future re-installations.
   - Press **Y** to completely purge all local application data.

### Method 2: Manual Removal Checklist

If removing manually:
1. Stop the application via Task Manager or `stop_jarvis.bat`.
2. Delete the Windows Startup entry:
   `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\JARVIS_AutoStart.bat`
3. Delete Desktop shortcut:
   `%USERPROFILE%\Desktop\J.A.R.V.I.S. Mark LVI.lnk`
4. Delete Start Menu shortcut:
   `%APPDATA%\Microsoft\Windows\Start Menu\Programs\J.A.R.V.I.S. Mark LVI`
5. Delete the application installation folder (e.g. `C:\JARVIS-AI` or `D:\JARVIS-AI`).
6. (Optional) Remove Ollama models if no longer needed:
   `%USERPROFILE%\.ollama\models` or custom models directory.

---

## 3. SUPPORT & ASSISTANCE

If you encounter issues during update or uninstallation, refer to:
- [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [docs/INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)
