# J.A.R.V.I.S. MARK LVI — DOMAIN & REVERSE PROXY DEPLOYMENT PLAN
## Dedicated Production Gateway for `jarvis.theblackintel.com`

**Target Domain:** `jarvis.theblackintel.com` (associated with `blackintel.com` / `theblackintel.com`)  
**Status:** ARCHITECTURAL SPECIFICATION & DEPLOYMENT BLUEPRINT  
**Version:** 1.0  
**Project:** J.A.R.V.I.S. Mark LVI Core  

---

## 1. Architecture Overview

J.A.R.V.I.S. Mark LVI is designed to run securely on a local Windows workstation while allowing optional, hardened remote access for paired mobile devices (Android) and operator dashboards.

To deploy under `jarvis.theblackintel.com` without compromising local security:
1. **Zero Direct Port Exposure:** Local backend ports (`8000`, `8001`, `8005`, `11434`) must NEVER be exposed directly via port-forwarding on residential routers.
2. **Encrypted Ingress Tunnel:** Traffic is routed through an authenticated Cloudflare Tunnel (`cloudflared`) or secure WireGuard/VPS reverse proxy terminating TLS at the edge.
3. **Strict Route Segregation:** Only approved dashboard routes and OAuth callbacks are exposed; backend debug utilities and Ollama daemon are strictly bound to `127.0.0.1`.

```
                    Internet
                       │
       ┌───────────────▼───────────────┐
       │   jarvis.theblackintel.com    │
       │   Cloudflare Edge (SSL/TLS)   │
       │   WAF / DDoS / Rate Limiting  │
       └───────────────┬───────────────┘
                       │ Encrypted Tunnel (cloudflared)
                       ▼
       ┌───────────────────────────────┐
       │   Local Windows Workstation   │
       │                               │
       │  ┌─────────────────────────┐  │
       │  │ Reverse Proxy / Ingress │  │
       │  └────────────┬────────────┘  │
       │               │               │
       │  ┌────────────▼────────────┐  │
       │  │ J.A.R.V.I.S. Server     │  │
       │  │ (Port 8001 - HTTPS/WSS) │  │
       │  └────────────┬────────────┘  │
       │               │               │
       │  ┌────────────▼────────────┐  │
       │  │ Local Ollama (11434)    │  │
       │  │ (Bound to 127.0.0.1)    │  │
       │  └─────────────────────────┘  │
       └───────────────────────────────┘
```

---

## 2. DNS & Subdomain Configuration

### 2.1 Cloudflare DNS Records
Configure the following in the Cloudflare DNS dashboard for `theblackintel.com`:

| Type | Name | Target / Content | Proxy Status | TTL |
|---|---|---|---|---|
| `CNAME` | `jarvis` | `<tunnel-uuid>.cfargotunnel.com` | Proxied (Orange Cloud) | Auto |

### 2.2 Security Benefits of Proxied DNS
- **Hides Workstation IP:** Public DNS never resolves to the workstation's real public IPv4/IPv6.
- **Edge TLS 1.3:** Enforces modern cipher suites and HTTP/3 support automatically.
- **Automatic DDoS Protection:** Blocks syn floods, volumetric attacks, and automated vulnerability scanners before traffic reaches the workstation.

---

## 3. Cloudflare Tunnel Ingress Configuration (`config.yml`)

The tunnel is run locally on the Windows workstation as a service:

```yaml
tunnel: <TUNNEL_UUID>
credentials-file: C:\ProgramData\cloudflared\<TUNNEL_UUID>.json

ingress:
  # 1. Instagram OAuth Callback (60s isolated proxy)
  - hostname: jarvis.theblackintel.com
    path: /api/instagram/oauth/callback
    service: http://127.0.0.1:8005

  # 2. Main Dashboard & WebSocket Audio Streams
  - hostname: jarvis.theblackintel.com
    service: https://127.0.0.1:8001
    originRequest:
      noTLSVerify: true  # Accepts local self-signed certificate

  # 3. Catch-all fallback
  - service: http_status:404
```

---

## 4. Alternative: Nginx Reverse Proxy Template

If using a dedicated VPS reverse proxy instead of Cloudflare Tunnel:

```nginx
server {
    listen 443 ssl http2;
    server_name jarvis.theblackintel.com;

    # SSL Certificates (Let's Encrypt / Certbot)
    ssl_certificate /etc/letsencrypt/live/jarvis.theblackintel.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/jarvis.theblackintel.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Client body size limit
    client_max_body_size 500M;

    # WebSocket & Dashboard Proxy
    location / {
        proxy_pass https://127.0.0.1:8001;
        proxy_ssl_verify off;

        # WebSocket Upgrade
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Forwarded Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for streaming voice
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # Isolated OAuth Proxy
    location /api/instagram/oauth/callback {
        proxy_pass http://127.0.0.1:8005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 5. Security & Isolation Safeguards

1. **Authentication Enforcement:**
   - Every request to `/api/*` requires a valid Bearer token or session token generated via PBKDF2 authentication.
   - Unauthenticated requests receive immediate `HTTP 401 Unauthorized`.
2. **Local Daemon Isolation:**
   - Ollama (`127.0.0.1:11434`) is never proxied or forwarded. All LLM queries originate internally from `dashboard/server.py`.
3. **Data Protection at Rest:**
   - Meta Graph API access tokens and user credentials remain encrypted using Windows DPAPI (`dpapi:v1:...`). Even if traffic through the reverse proxy was intercepted, tokens cannot be decrypted without the workstation's private DPAPI machine master key.
4. **Emergency Disconnect:**
   - To immediately terminate all remote access without taking down the local companion:
     ```powershell
     Stop-Service cloudflared
     ```
   - Local access via `https://127.0.0.1:8001` or LAN pairing remains 100% functional.

---

## 6. Pre-Flight Deployment Checklist

- [x] Self-signed certificate generator verified (`dashboard/server.py`).
- [x] Dual-layer encryption (TLS + AES-256-GCM) verified.
- [x] OAuth proxy port separation (8005) verified.
- [x] WebSocket streaming routes (`/ws` and `/ws/phone-audio`) verified.
- [x] PBKDF2 authentication gate verified with brute-force rate-limiting.
- [ ] Operator: Acquire Cloudflare Tunnel or VPS ingress point for `jarvis.theblackintel.com`.
- [ ] Operator: Run `cloudflared service install` on Windows workstation.
