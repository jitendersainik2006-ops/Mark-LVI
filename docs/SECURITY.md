# J.A.R.V.I.S. Mark LVI — Security & Privacy Architecture

This document defines the security controls, threat models, and privacy protections implemented in J.A.R.V.I.S. Mark LVI Core.

---

## 1. Core Security Principles

1. **Local-First & Data Sovereignty:** Personal memories, documents, calendar entries, and chat logs reside exclusively on the user's local disk in `data/`. No personal data is sent to external cloud telemetry.
2. **Zero Hardcoded Credentials:** No API keys, passwords, client secrets, or auth tokens are committed to source control or hardcoded in scripts.
3. **Least Privilege & Role-Based Access:** All background tasks and computer operations operate under least privilege. Destructive operations require explicit interactive human approval.
4. **Default-Deny Ingress:** All external network entry points default to `403 Forbidden` unless strictly allowlisted.

---

## 2. Secrets & Credential Protection

### A. Windows DPAPI Encryption at Rest
- Sensitive tokens (Meta SUAT/EAAG tokens) are encrypted via Windows Data Protection API (`core/crypto_storage.py`).
- Ciphertext is prefixed with `dpapi:v1:`. Only the logged-in Windows user account can decrypt these secrets.

### B. Automated Credential Scrubbing
Conversational memory (`memory/memory_manager.py`), knowledge ingestion (`core/knowledge_manager.py`), and computer agent audit logging (`core/computer_agent.py`) pass all text through rigorous regex scrubbers:
- `sk-[a-zA-Z0-9_\-]{20,}` (OpenAI / Anthropic keys)
- `AIza[0-9A-Za-z\-_]{30,45}` (Google API keys)
- `EAA[A-Za-z0-9]{15,}` (Meta tokens)
- `dpapi:v1:[A-Za-z0-9+/=]+` (DPAPI ciphertext)
- `password|token|secret\s*[:=]\s*[^\s,;]+`

---

## 3. Network Isolation & Reverse Proxy Guardrail

```text
External Internet
       │
       ▼ (HTTPS)
Cloudflare Named Tunnel (jarvis.theblackintel.com)
       │
       ▼ (HTTP loopback)
127.0.0.1:8005 (tools/oauth_callback_proxy.py)
       │
       ├── Path: /api/instagram/oauth/callback  -->  FORWARD to 127.0.0.1:8000
       │
       └── ALL OTHER PATHS (/, /app, /api/*)     -->  BLOCK (HTTP 403 Forbidden)
```

- **Port 8000 (Backend API & Dashboard):** Bound strictly to `127.0.0.1`. Never referenced in external tunnel configurations.
- **Port 8005 (Proxy):** Enforces route allowlisting, rejecting all attempts to access the dashboard, API, or WebSocket over the internet.

---

## 4. Computer Agent Consequential Action Gating

Any agentic action classified under `DESTRUCTIVE_ACTIONS` triggers an interactive confirmation requirement:
- Deleting files or directories
- Terminating processes
- Replaying or initiating Instagram publishing
- Sending outbound emails
- System shutdown or restart

Actions cannot proceed until the user explicitly issues confirmation (`CONFIRM`, `YES`, `APPROVE`). All attempts are recorded with timestamps in `data/computer_agent_audit.log`.
