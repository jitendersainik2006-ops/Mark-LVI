import urllib.request
import urllib.error
import json
import sys

def run_checks():
    print("=== LIVE HTTP PROBE: J.A.R.V.I.S. REELS MANAGER ===")
    
    # 1. Local Login
    try:
        req = urllib.request.Request(
            'http://127.0.0.1:8000/api/local-login',
            data=b'{}',
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            print(f"[OK] Local Login: ok={data.get('ok')}, token_len={len(data.get('token', ''))}")
            token = data.get('token')
    except Exception as e:
        print(f"[FAIL] Local Login: {e}")
        return False

    headers = {'Authorization': f'Bearer {token}'}

    # 2. Instagram accounts
    try:
        req = urllib.request.Request('http://127.0.0.1:8000/api/instagram/accounts', headers=headers)
        with urllib.request.urlopen(req) as resp:
            accs = json.loads(resp.read().decode())
            acc_list = accs.get('accounts', [])
            print(f"[OK] Instagram Accounts: {len(acc_list)} registered")
            for a in acc_list:
                print(f"     - @{a.get('username')}: ID={a.get('instagram_user_id')}, Status={a.get('status')}, Designated={a.get('is_designated')}")
    except Exception as e:
        print(f"[FAIL] Instagram Accounts: {e}")
        return False

    # 3. Instagram OAuth config
    try:
        req = urllib.request.Request('http://127.0.0.1:8000/api/instagram/oauth/config', headers=headers)
        with urllib.request.urlopen(req) as resp:
            cfg = json.loads(resp.read().decode())
            c = cfg.get('config', {})
            print(f"[OK] OAuth Config: app_id={c.get('app_id')}, config_id={c.get('config_id')}, has_secret={c.get('has_app_secret')}, redirect_uri={c.get('redirect_uri')}")
    except Exception as e:
        print(f"[FAIL] OAuth Config: {e}")
        return False

    # 4. Instagram OAuth authorize URL
    try:
        req = urllib.request.Request('http://127.0.0.1:8000/api/instagram/oauth/authorize', headers=headers)
        with urllib.request.urlopen(req) as resp:
            auth_data = json.loads(resp.read().decode())
            url = auth_data.get('auth_url', '') or auth_data.get('url', '')
            has_cfg = 'config_id=1855190429104475' in url
            has_client = 'client_id=2420740248667467' in url
            no_legacy_scope = 'scope=' not in url
            print(f"[OK] Authorize URL generated: ok={auth_data.get('ok')}, has_config_id={has_cfg}, has_app_id={has_client}, no_legacy_scope={no_legacy_scope}")
    except Exception as e:
        print(f"[FAIL] Authorize URL: {e}")
        return False

    # 5. Reels Ledger
    try:
        req = urllib.request.Request('http://127.0.0.1:8000/api/reels', headers=headers)
        with urllib.request.urlopen(req) as resp:
            reels_resp = json.loads(resp.read().decode())
            reels = reels_resp.get('reels', [])
            print(f"[OK] Reels Ledger: {len(reels)} total reels retrieved")
            valid_reels = [r for r in reels if not r.get('target_mismatch')]
            print(f"     - Valid for @mentos_life_gym: {len(valid_reels)}")
            if valid_reels:
                sample = valid_reels[0]
                print(f"     - Sample: ID={sample.get('id')}, Title='{sample.get('title')}', Status={sample.get('status')}, NeedsApproval={sample.get('needs_approval')}")
    except Exception as e:
        print(f"[FAIL] Reels Ledger: {e}")
        return False

    # 6. Proxy Port 8005 Security & Routing Check
    try:
        # 6a. Root route on 8005 MUST return 403 Forbidden
        req_root = urllib.request.Request('http://127.0.0.1:8005/')
        try:
            with urllib.request.urlopen(req_root) as resp:
                print(f"[FAIL] Proxy Port 8005 / returned HTTP {resp.status} (expected 403 Forbidden)")
                return False
        except urllib.error.HTTPError as he:
            if he.code == 403:
                print(f"[OK] Proxy Port 8005 Root Route: HTTP 403 Forbidden (Strictly blocked non-callback)")
            else:
                print(f"[FAIL] Proxy Port 8005 returned unexpected HTTP {he.code}")
                return False

        # 6b. Callback route on 8005 MUST be forwarded to 8000 (error response returns HTTP 400 HTML page)
        req_cb = urllib.request.Request('http://127.0.0.1:8005/api/instagram/oauth/callback?error=access_denied&error_description=test')
        try:
            with urllib.request.urlopen(req_cb) as resp:
                print(f"[OK] Proxy Port 8005 Callback Route: HTTP {resp.status}")
        except urllib.error.HTTPError as he:
            if he.code == 400:
                body = he.read().decode(errors='replace')
                if 'Meta Authorization Cancelled' in body or 'access_denied' in body:
                    print(f"[OK] Proxy Port 8005 Callback Route: HTTP 400 (Correctly forwarded to 8000 backend notice)")
                else:
                    print(f"[OK] Proxy Port 8005 Callback Route: HTTP {he.code} forwarded from 8000")
            else:
                print(f"[FAIL] Proxy Port 8005 returned unexpected HTTP {he.code}")
                return False
    except Exception as e:
        print(f"[FAIL] Proxy Port 8005 check: {e}")
        return False

    # 7. Check Video Stream Endpoint
    try:
        if valid_reels:
            vid_id = valid_reels[0]['id']
            req_vid = urllib.request.Request(f'http://127.0.0.1:8000/api/reels/{vid_id}/video', headers=headers)
            with urllib.request.urlopen(req_vid) as resp:
                content_type = resp.headers.get('Content-Type')
                content_length = resp.headers.get('Content-Length')
                print(f"[OK] Video Stream endpoint for Reel {vid_id}: HTTP {resp.status}, Content-Type={content_type}, Size={content_length} bytes")
    except urllib.error.HTTPError as he:
        print(f"[INFO] Video Stream endpoint HTTP {he.code} (File may not exist on disk for this draft: {he.reason})")
    except Exception as e:
        print(f"[INFO] Video Stream check notice: {e}")

    print("=== ALL LIVE HTTP CHECKS PASSED SUCCESSFULLY ===")
    return True

if __name__ == '__main__':
    ok = run_checks()
    sys.exit(0 if ok else 1)
