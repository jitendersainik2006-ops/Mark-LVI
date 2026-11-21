import sys
sys.path.insert(0, "D:/JARVIS-AI/mark_lvi_core")
from core.meta_oauth import meta_oauth

cfg = meta_oauth._load_meta_config()
dec = cfg.get("app_secret", "")
print(f"App secret configured: {bool(dec)}")
print(f"App secret length: {len(dec)}")
print(f"Is hex: {all(c in '0123456789abcdefABCDEF' for c in dec)}")
print(f"Is placeholder: {'placeholder' in dec.lower() or 'secret' in dec.lower() or 'meta' in dec.lower()}")
