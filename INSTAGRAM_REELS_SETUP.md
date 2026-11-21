# J.A.R.V.I.S. Instagram Reels Automation — Setup & Installation Guide

**Project Root:** `D:\JARVIS-AI\mark_lvi_core`  
**Python Environment:** `D:\JARVIS-AI\.venv-jarvis\Scripts\python.exe`  
**Target Instagram Account:** `@mentos_life_gym` (`17841458094701596`)

---

## 1. System Requirements & Dependencies

The Reels Automation module runs entirely locally on Windows using the dedicated virtual environment `D:\JARVIS-AI\.venv-jarvis`.

### Core Python Packages
- **`av` (PyAV):** Direct bindings to FFmpeg libraries for hardware-accelerated H.264/AAC vertical video encoding and audio muxing.
- **`Pillow` (PIL):** High-performance image drawing, text rasterization, and cover image generation.
- **`pywin32`:** Windows Data Protection API (DPAPI) for encryption/decryption of Meta credentials.
- **`requests` / `httpx`:** Secure HTTPS communication with Meta Graph API (`graph.facebook.com/v26.0`).
- **`fastapi` & `uvicorn`:** Asynchronous web framework hosting the J.A.R.V.I.S. dashboard (Port 8000) and OAuth proxy (Port 8005).

---

## 2. Directory Architecture & Data Stores

All reels assets, configurations, and ledgers reside strictly inside the `D:` drive:

```
D:\JARVIS-AI\mark_lvi_core\
├── config\
│   └── api_keys.json               # DPAPI-encrypted Meta App Secret and API configurations
├── data\
│   ├── instagram_accounts.json     # Encrypted Instagram account state & permissions
│   ├── reels_ledger.json           # Deduplication ledger, post status, and approval tracking
│   └── reels\                      # Generated media storage
│       ├── {reel_id}.mp4           # 9:16 vertical video asset
│       ├── {reel_id}_voice.wav     # Synthesized voiceover audio track
│       └── {reel_id}_cover.jpg     # 9:16 vertical JPEG cover thumbnail
├── core\
│   ├── instagram_manager.py        # Reels engine, video synthesis, validator & approval gates
│   └── meta_oauth.py               # Facebook Login for Business & DPAPI token lifecycle
├── dashboard\
│   ├── server.py                   # FastAPI REST API endpoints
│   └── static\
│       └── app.html                # Interactive dark-theme dashboard UI
└── tools\
    ├── run_oauth_services.py       # Dual background launcher (Port 8000 & 8005)
    └── launch_meta_login.py        # One-click browser authorization initiator
```

---

## 3. Starting the J.A.R.V.I.S. Services

The J.A.R.V.I.S. Reels dashboard and OAuth proxy must run concurrently:

1. **J.A.R.V.I.S. Main Dashboard:** Listening on `http://localhost:8000/`.
2. **Callback-Only Reverse Proxy:** Listening on `http://127.0.0.1:8005/`, forwarding ONLY `/api/instagram/oauth/callback` to port 8000 and blocking all other routes with HTTP 403 Forbidden.

### Launch Command
Execute the unified background service runner:
```powershell
& D:\JARVIS-AI\.venv-jarvis\Scripts\python.exe D:\JARVIS-AI\mark_lvi_core\tools\run_oauth_services.py
```

### Verifying Service Connectivity
Run the following PowerShell check:
```powershell
Get-NetTCPConnection -LocalPort 8000,8005 -State Listen | Select-Object LocalAddress,LocalPort,State
```
Both ports `8000` and `8005` should report `Listen`.

---

## 4. Initiating Meta OAuth Authorization

1. Open the dashboard in your web browser:
   `http://localhost:8000/`
2. Navigate to **Reels** in the left sidebar.
3. Locate the account card for `@mentos_life_gym` and click **Connect Account** → **Meta Unified Login**.
4. The system will open the official Facebook Login dialog:
   `https://www.facebook.com/v26.0/dialog/oauth?client_id=2420740248667467&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Finstagram%2Foauth%2Fcallback&state=...&response_type=code&config_id=1855190429104475`
5. Select the **Mentos Life Gym** business portfolio and grant the requested permissions.
6. Upon completion, Meta redirects to the local callback endpoint, exchanges the code for a permanent access token, encrypts it via DPAPI, and marks the account **CONNECTED**.

---

## 5. Assisted Publishing Workflow (Zero Token Requirement)

If live OAuth authorization is deferred, the built-in **Assisted Publishing Workflow** enables immediate publication:
1. Generate or review a Reel draft in the dashboard.
2. Click **✓ Approve & Publish**.
3. Because the account is `UNVERIFIED_BY_META`, J.A.R.V.I.S. automatically engages assisted mode:
   - The verified 9:16 vertical MP4 video is downloaded or copied to your staging folder.
   - The selected multilingual caption (English, Hindi, or Hinglish) and optimized hashtags are copied directly to your clipboard.
   - The official `@mentos_life_gym` Instagram profile is opened in one click.
   - You simply drag the MP4 and paste the caption into the Instagram app.
