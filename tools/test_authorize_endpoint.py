import urllib.request
import json

# Local login to get token
req = urllib.request.Request('http://127.0.0.1:8000/api/local-login', data=b'{}', headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    tok = data['token']

# Check authorize endpoint
req = urllib.request.Request('http://127.0.0.1:8000/api/instagram/oauth/authorize', headers={'Authorization': f'Bearer {tok}'})
with urllib.request.urlopen(req) as resp:
    auth_res = json.loads(resp.read().decode())
    print("Authorize response:")
    print("  ok:", auth_res.get("ok"))
    print("  state:", auth_res.get("state"))
    print("  auth_url:", auth_res.get("auth_url"))
