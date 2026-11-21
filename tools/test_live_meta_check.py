import sys
sys.path.insert(0, "D:/JARVIS-AI/mark_lvi_core")
from core.instagram_manager import instagram_manager
from core.meta_oauth import meta_oauth

acc = instagram_manager.get_reels_account()
print(f"Designated account: @{acc.username}, ID: {acc.instagram_user_id}, Status: {acc.status}")

# Test resolving token in memory
raw_tok = meta_oauth._resolve_token(acc.access_token)
print(f"Decrypted token available: {bool(raw_tok)}, prefix: {raw_tok[:10]}...")

# Test inspecting token validity with Meta
validity = meta_oauth.inspect_token_validity(acc.access_token)
print(f"Meta Token Validity: {validity}")

# Test permissions with Meta
perms = meta_oauth.inspect_permissions(acc.access_token)
print(f"Meta Permissions: {perms}")

# Test verifying account identity with Meta
identity = meta_oauth.verify_account_identity(acc.access_token, target_username="mentos_life_gym")
print(f"Meta Identity Verification: {identity}")
