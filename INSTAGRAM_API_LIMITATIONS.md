# Instagram Reels Graph API — Limitations, Video Specifications & Fallback Workflows

**Project Root:** `D:\JARVIS-AI\mark_lvi_core`  
**Target Account:** `@mentos_life_gym` (`17841458094701596`)  
**Meta API Version:** Graph API `v26.0`

---

## 1. Official Meta Reels Publishing Specifications

To publish Instagram Reels programmatically through the Meta Graph API container workflow (`POST /v26.0/{ig-user-id}/media` followed by `POST /v26.0/{ig-user-id}/media_publish`), media assets must comply with strict encoding criteria:

| Parameter | Official Meta Specification | J.A.R.V.I.S. Compliance Engine |
| :--- | :--- | :--- |
| **Container Format** | MP4 or MOV (with fast-start `moov` atom at front) | MP4 container produced via PyAV |
| **Aspect Ratio** | 9:16 (0.5625 aspect ratio; tolerance 0.05) | Strict 9:16 (1080x1920 or 720x1280) |
| **Video Codec** | H.264 (AVC) Baseline, Main, or High Profile | H.264 High Profile |
| **Audio Codec** | AAC, stereo or mono, 44.1 kHz or 48 kHz | AAC stereo, 44.1 kHz |
| **Frame Rate** | 24 fps to 60 fps | 30 fps |
| **Video Duration** | Minimum 3 seconds, Maximum 900 seconds (15 min) | 16.5 seconds standard educational format |
| **File Size Limit** | 100 MB max for direct container upload | Average 1.2 MB to 2.5 MB (ultra-efficient) |
| **Bitrate Limits** | Max video bitrate: 25 Mbps; audio: 128 kbps | Video: ~1.2 Mbps; Audio: 128 kbps AAC |

---

## 2. API Rate Limits & Operational Restrictions

### 1. Daily Publication Ceiling
Meta enforces an account-level publishing rate limit of **25 Reels or posts within any rolling 24-hour window**. J.A.R.V.I.S. enforces a local safety governor allowing a maximum of 4 scheduled Reels per day to protect account algorithmic standing.

### 2. Video Hosting Requirement for Container Ingestion
Meta's `POST /{ig-user-id}/media?media_type=REELS&video_url=<URL>` requires the `video_url` to be publicly accessible over HTTPS by Meta's crawler servers.
- A local URL (`http://localhost:8000/...`) cannot be fetched directly by Meta's remote crawlers without an active public HTTPS tunnel or signed public storage bucket.
- Exposing the entire J.A.R.V.I.S. dashboard publicly is strictly prohibited by security rules.

### 3. Asynchronous Container Processing
After creating a Reels container, Meta transcode workers take between 5 and 60 seconds to process the video before `STATUS_CODE: FINISHED` is reached. Publishing must poll container status before issuing `media_publish`.

---

## 3. The Assisted Publishing Workflow (High-Availability Fallback)

To ensure creators can publish on schedule regardless of Meta API outages, rate limits, network tunnels, or pending OAuth authorizations, J.A.R.V.I.S. includes the **Assisted Publishing Workflow**.

### How It Works:
1. When a user approves a Reel for publication:
   - J.A.R.V.I.S. inspects token status and endpoint reachability.
   - If the account is `UNVERIFIED_BY_META` or Meta's API is unreachable, the system automatically transitions the Reel to `PUBLISHED_ASSISTED`.
2. The user is provided with:
   - **One-Click MP4 Download:** Pre-validated 9:16 vertical video saved to local disk.
   - **One-Click Clipboard Copy:** Multilingual caption and tags formatted ready for paste.
   - **One-Click Profile Open:** Direct link opening `https://www.instagram.com/mentos_life_gym/`.
3. The creator uploads the ready asset directly through Instagram Mobile or Desktop in seconds.
4. The ledger permanently records the post as `published_assisted`, maintaining chronological consistency and post deduplication.
