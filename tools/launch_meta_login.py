import urllib.request
import json
import webbrowser
import sys

# 1. Acquire local login token
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/local-login',
    data=b'{}',
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    tok = data['token']

# 2. Request live OAuth authorization URL with registered CSRF state
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/instagram/oauth/authorize',
    headers={'Authorization': f'Bearer {tok}'}
)
with urllib.request.urlopen(req) as resp:
    auth_data = json.loads(resp.read().decode())
    auth_url = auth_data['auth_url']
    state = auth_data['state']

parsed_auth = urllib.parse.urlparse(auth_url)
qparams = urllib.parse.parse_qs(parsed_auth.query)

client_id = qparams.get('client_id', ['1462879891932217'])[0]
config_id = qparams.get('config_id', ['4274466502813863'])[0]
cb_uri = qparams.get('redirect_uri', [''])[0]
cb_host = urllib.parse.urlparse(cb_uri).netloc if cb_uri else 'unknown'

masked_state = f"{state[:4]}...{state[-4:]}" if len(state) > 8 else "***"

print("=" * 75)
print("  J.A.R.V.I.S. META UNIFIED LOGIN LAUNCHER")
print("=" * 75)
print(f"Meta App ID      : {client_id}")
print(f"Config ID        : {config_id}")
print(f"Registered State : {masked_state} (Single-use, 600s TTL)")
print(f"Callback URI     : {cb_uri}")
print(f"App Domain       : {cb_host} (Must be in App Settings -> Basic -> App Domains)")
print(f"Target Account   : @mentos_life_gym (ID: 17841458094701596)")
print("=" * 75)

if "--print-only" in sys.argv:
    print("\n[Safe Mode] Authorization URL generated (--print-only specified):")
    print(auth_url)
elif "--no-browser" in sys.argv:
    print("\n[Safe Mode] Browser auto-launch skipped (--no-browser specified).")
    print(auth_url)
else:
    print("\nLaunching browser for official Meta consent...")
    webbrowser.open(auth_url)
    print("Browser successfully opened.")


