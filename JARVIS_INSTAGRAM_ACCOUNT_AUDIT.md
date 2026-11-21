# J.A.R.V.I.S. Mark LVI Core — Instagram Account Integration & Audit

**Target Account:** `@mentos_life_gym`  
**Authoritative Instagram Account ID:** `17841458094701596`  
**Linked Facebook Page ID:** `100998877665544`  
**Account Verification Status:** **`UNVERIFIED (PENDING LIVE META GRANT)`**  
**Publishing Status:** **`DISABLED`**  

---

## 1. Account Identity & Eligibility Requirements

| Verification Dimension | Requirement | Current Project State |
| :--- | :--- | :--- |
| **Account Type** | Instagram Professional (Business or Creator) | Configured for `@mentos_life_gym`. |
| **Facebook Page Linkage** | Connected to Facebook Page ID `100998877665544` | Configured in `data/instagram_accounts.json`. |
| **Target Account Locking** | Reject publishing if account does not match target | Enforced in `core/instagram_manager.py` (L300-L335). |
| **Live Token Status** | Active 60-day token verified via `/debug_token` | UNVERIFIED (stale token requires admin refresh). |
| **Token Storage** | Encrypted using Windows DPAPI | VERIFIED (`dpapi:v1:...`). |

---

## 2. Dynamic Account Discovery Workflow

When the administrator completes Meta OAuth in the browser:
1. J.A.R.V.I.S. receives the authorization `code` at `/api/instagram/oauth/callback`.
2. Exchanges `code` for a long-lived User Access Token.
3. Queries Graph API endpoint `GET /me/accounts?fields=id,name,access_token,instagram_business_account{id,username,name}`.
4. Searches returned pages for `instagram_business_account.id == 17841458094701596` or `username == "mentos_life_gym"`.
5. Upon confirmation:
   - Updates `data/instagram_accounts.json` with the Page Access Token (DPAPI encrypted).
   - Marks account as `CONNECTED_VERIFIED`.
   - Records `verified_at` timestamp.
6. If the target account is not found in the Meta payload:
   - Rejects account binding with explicit error notification.
   - Prevents unauthorized account takeover.
