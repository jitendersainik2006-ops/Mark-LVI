# J.A.R.V.I.S. Mark LVI Core — Permanent Domain Migration Plan

**Future Permanent Hostname:** `jarvis.theblackintel.com`  
**Local Ingress Target:** `http://127.0.0.1:8005` (Hardened Callback Proxy Only)  
**Permanent Callback URI:** `https://jarvis.theblackintel.com/api/instagram/oauth/callback`  
**Status:** **`WAITING FOR ADMIN`**  

---

## 1. Strict Project Separation Notice

> [!IMPORTANT]
> J.A.R.V.I.S. is a separate personal automation project. Black Intel has granted permission exclusively for the use of the subdomain `jarvis.theblackintel.com`.  
> - No access to Black Intel's Cloudflare account, DNS zone settings, repositories, or servers is assumed or required by J.A.R.V.I.S.  
> - Only an authorized Black Intel domain administrator may perform actual DNS, Cloudflare Zero Trust, or domain configurations.  
> - Black Intel infrastructure is NOT to be used as J.A.R.V.I.S. backend hosting.

---

## 2. Configuration Abstraction (Zero Code Rewrite)

J.A.R.V.I.S. incorporates an automated domain abstraction engine:
- Method [`configure_custom_domain_callback()`](file:///D:/JARVIS-AI/mark_lvi_core/core/meta_oauth.py) validates FQDN format, extracts base domain (`theblackintel.com`), updates `config/api_keys.json`, and asserts exact URI equality.
- Method [`save_redirect_uri()`](file:///D:/JARVIS-AI/mark_lvi_core/core/meta_oauth.py) saves any valid HTTPS redirect URI safely.
- [`tools/launch_meta_login.py`](file:///D:/JARVIS-AI/mark_lvi_core/tools/launch_meta_login.py) dynamically extracts the domain and callback URI from the live authorization URL, requiring zero code adjustments when migrating domains.

---

## 3. Migration Execution Steps for Administrator

### Step 1: Cloudflare Named Tunnel Setup (Black Intel Administrator)
1. In Cloudflare Zero Trust Dashboard: Create a Named Tunnel pointing to `http://127.0.0.1:8005`.
2. Public Hostname: `jarvis.theblackintel.com` -> Service: `HTTP` -> URL: `127.0.0.1:8005`.
3. DNS: Cloudflare creates CNAME `jarvis` pointing to `<tunnel-uuid>.cfargotunnel.com` (Proxied).

### Step 2: Meta Developer Console Update (Meta Administrator)
1. **App Settings -> Basic -> App Domains:** Add `jarvis.theblackintel.com` (and `theblackintel.com`). Click **Save Changes**.
2. **Facebook Login for Business -> Settings -> Valid OAuth Redirect URIs:** Add  
   `https://jarvis.theblackintel.com/api/instagram/oauth/callback`. Click **Save Changes**.

### Step 3: Switch J.A.R.V.I.S. Configuration to Permanent Domain
```powershell
& "D:\JARVIS-AI\.venv-jarvis\Scripts\python.exe" -c "from core.meta_oauth import meta_oauth; meta_oauth.configure_custom_domain_callback('jarvis.theblackintel.com', confirm=True)"
```

### Step 4: Verification & Rollback Procedure
- **Verification:** Run `curl -I https://jarvis.theblackintel.com/api/instagram/oauth/callback`. Expected: Returns backend proxy response (or 502 if proxy is offline, proving the route reaches port 8005).
- **Rollback Procedure:** If the permanent domain needs to be rolled back to a Quick Tunnel or local dev URI:
  ```powershell
  # Rollback to Quick Tunnel
  & "D:\JARVIS-AI\.venv-jarvis\Scripts\python.exe" -c "from core.meta_oauth import meta_oauth; meta_oauth.configure_quick_tunnel_callback('<subdomain>.trycloudflare.com', confirm=True)"
  ```
