# J.A.R.V.I.S. MARK LVI — SECURITY & THREAT MITIGATION SPECIFICATION

## 1. Cryptographic Safeguards

### A. Windows DPAPI Credential Protection
- All persistent tokens (Meta Graph API access tokens, Google OAuth 2.0 refresh tokens, application secrets) are encrypted before writing to disk using the **Windows Data Protection API (DPAPI)** via `CryptProtectData`.
- Tokens are encrypted with `DPAPI_PREFIX = "dpapi:v1:"`.
- Key material is tied to the active Windows user account and machine hardware hash; files cannot be decrypted if copied to an attacker's machine or read by a different user.
- If DPAPI encryption fails, the system fails closed rather than persisting plaintext tokens.
- All client APIs, logging formatters, and error handlers mask tokens using `mask_token()` (e.g., `EAAB****xyz1`).

### B. User Password Hashing
- User credentials in `core/user_manager.py` are hashed using **PBKDF2-HMAC-SHA256** with 100,000 iterations and a cryptographically random 16-byte salt (`secrets.token_bytes(16)`).
- Raw passwords and salts are never returned in public dictionaries (`to_public_dict()`).

---

## 2. Process Termination & Ownership Security

### A. Strict Process Verification in `installer/stop_jarvis.py`
- When terminating background J.A.R.V.I.S. instances, the process termination engine inspects the verified executable command line and image path of every candidate process.
- **Rules Enforced:**
  1. The PID must resolve to an active process running Python with a script inside `D:\JARVIS-AI\mark_lvi_core` or the verified frozen launcher binary.
  2. The script will **never** kill an unrelated process simply because it occupies port 8000 or 8005.
  3. Non-J.A.R.V.I.S. system processes are strictly ignored.

---

## 3. Data Retention & Uninstall Integrity

### A. Preservation Policy in `installer/uninstall_jarvis.py`
- Uninstallation strictly preserves user data and intellectual property:
  - `data/reels_ledger.json` (Historical posts ledger)
  - `data/instagram_accounts.json` (Account mappings)
  - `data/memory.json` & `data/jarvis_memory.db` (Personal memory and facts)
  - `data/knowledge/documents/` (Imported user knowledge base)
  - `config/api_keys.json` (Configuration preferences)
  - `data/users/` (Isolated multi-user profiles)
- Personal files are never purged without explicit interactive confirmation.

---

## 4. Network & LAN Security Hardening

### A. Anti-Spoofing Client Identification
- When LAN pairing is active, incoming connections are evaluated based on the physical TCP peer socket address (`request.scope["client"][0]`).
- Untrusted headers such as `X-Forwarded-For`, `X-Real-IP`, and `Forwarded` are strictly ignored for security decisions.

### B. Host Header Allowlisting
- Host headers are checked against an explicit allowlist: loopback addresses (`127.0.0.1`, `localhost`, `::1`) and the host PC's verified private LAN interface. Malformed, external, or unrecognized Host headers receive an immediate HTTP 403 Forbidden.

### C. Route Isolation (`_RESTRICTED_LAN_PREFIXES`)
- Remote LAN clients are strictly prevented from accessing administrative and sensitive endpoints:
  - `/api/instagram`
  - `/api/reels`
  - `/api/gym`
  - `/api/n8n`
  - `/api/company`
  - `/api/gmail`
  - `/api/lan-pairing/enable`
  - `/api/local-login`
  - `/api/shutdown`
  - `/config`

### D. Cryptographic LAN Pairing & Authenticated Audio
- **PBKDF2 Key Derivation:** Pairing code is stretched using PBKDF2-HMAC-SHA256 with 200,000 rounds and salt `JARVIS-DASHBOARD-v1` to derive a 32-byte key, mitigating offline brute-force.
- **AES-256-GCM Encrypted Sessions:** Decryption enforces authenticated GCM payload (`nonce[12] || ciphertext || tag`). Any tampered or bit-flipped payload raises `InvalidTag` and is rejected immediately.
- **Action Allowlist Enforcement:** `/api/action` only permits `volume_up`, `volume_down`, `volume_mute`, `lock_screen`, `media_play_pause`, `wake`, and `sleep`. Remote shutdown/restart commands are strictly disallowed.
- **Wake-on-LAN Boundary:** Remote HTTP requests cannot wake an ACPI S5/S3 PC because the HTTP listener is suspended with the operating system; hardware NIC Wake-on-LAN (UDP Magic Packet on port 9) is required for physical machine wake.

---

## 5. External Actions & Human Confirmation Gates

### A. Google OAuth Granular Scopes & Gmail Dispatch
- Basic Google Sign-In requests **only** `openid email profile`, ensuring no email access is granted during standard login.
- Gmail features (`gmail.readonly`, `gmail.compose`, `gmail.send`) require explicit opt-in.
- **Two-Step Human-in-the-Loop Send Gate:**
  1. Step 1: `/api/gmail/preview_send` generates a recipient/subject/body preview and issues a short-lived (180s) single-use cryptographic confirmation token.
  2. Step 2: `/api/gmail/send` requires `confirmed: true` and the exact matching confirmation token. Any unconfirmed or replayed dispatch is immediately blocked.

### B. Instagram Publishing Guard
- The account state for `@mentos_life_gym` is maintained as `UNVERIFIED_BY_META`, ensuring zero unapproved live network uploads occur during automated execution.

---

## 6. Autonomous Desktop Automation Safeguards

### A. Strict Lifecycle & Destructive Action Gating
- `core/computer_agent.py` enforces the lifecycle: `PLAN -> REQUEST PERMISSION -> ACT -> OBSERVE -> VERIFY -> REPORT`.
- Destructive operations (`delete_file`, `remove_folder`, `system_shutdown`, `system_restart`, `kill_process`, `send_email`, `publish_instagram_reel`, `wipe_memory`, `overwrite_file`) cannot execute without explicit confirmation.
- Confirmation requires passing a verified `CONFIRM` authorization token.

### B. Audit Logging & Automated Secret Scrubbing
- Every agentic action is written to `data/computer_agent_audit.log`.
- All outputs are sanitized via regex patterns matching Anthropic API keys (`sk-[a-zA-Z0-9_\-]{20,}`), Meta tokens (`EAA...`), DPAPI payloads (`dpapi:v1:...`), and general key/secret values, replacing them with `[REDACTED_SECRET]`.

### C. Zero Developer Credential Leakage in Distribution Packages
- Automated test `test_release_package_manifest_and_zero_developer_data` enforces that `config/api_keys.json` and developer memories are absent from all distribution packages. All 178 manifest files are verified against SHA-256 hashes.
