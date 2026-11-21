import sys
sys.path.insert(0, "D:/JARVIS-AI/mark_lvi_core")
from core.meta_oauth import meta_oauth

url, state = meta_oauth.get_authorization_url()
print(f"AUTH_URL: {url}")
print(f"STATE: {state}")
