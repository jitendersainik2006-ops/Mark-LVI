"""
core/crypto_storage.py — Cryptographic Protection for Sensitive Credentials at Rest

Provides Windows DPAPI (Data Protection API) encryption for access tokens.
Encryption is tied to the local Windows user credentials, ensuring:
- Tokens are encrypted at rest on disk in data/instagram_accounts.json.
- No hardcoded cryptographic keys need to be committed or managed.
- Files cannot be read by unauthorized users or copied to another machine.
- Plaintext tokens are NEVER stored on disk or exposed in logs/APIs.
- Fails closed if DPAPI encryption is unavailable.
"""

from __future__ import annotations

import base64
import sys
from typing import Optional

DPAPI_PREFIX = "dpapi:v1:"


class SecurityError(Exception):
    """Raised when cryptographic protection operations fail."""
    pass


def is_encrypted(token: Optional[str]) -> bool:
    """Check if token string is already encrypted with DPAPI prefix."""
    if not token or not isinstance(token, str):
        return False
    return token.startswith(DPAPI_PREFIX)


def mask_token(token: Optional[str]) -> str:
    """Masks token for safe logging and client API serialization."""
    if not token or not isinstance(token, str):
        return ""
    # Strip DPAPI prefix if passed
    tok = token[len(DPAPI_PREFIX):] if token.startswith(DPAPI_PREFIX) else token
    if len(tok) <= 8:
        return "****"
    return tok[:4] + "****" + tok[-4:]


def encrypt_token(plain_token: Optional[str]) -> str:
    """
    Encrypts a plaintext token string using Windows DPAPI (CryptProtectData).
    Returns a prefixed base64-encoded string: dpapi:v1:<base64_ciphertext>.
    Fails closed: raises SecurityError if encryption cannot be performed.
    """
    if not plain_token:
        return ""
    if is_encrypted(plain_token):
        return plain_token

    if sys.platform != "win32":
        raise SecurityError("DPAPI encryption requires Windows OS.")

    raw_bytes = plain_token.strip().encode("utf-8")

    # Try pywin32 win32crypt first
    try:
        import win32crypt
        encrypted_bytes = win32crypt.CryptProtectData(
            raw_bytes,
            "JARVIS_INSTAGRAM_TOKEN",
            None,  # optional entropy
            None,  # reserved
            None,  # prompt struct
            0      # flags: current user scope
        )
        return DPAPI_PREFIX + base64.b64encode(encrypted_bytes).decode("utf-8")
    except ImportError:
        pass
    except Exception as e:
        raise SecurityError(f"Windows DPAPI encryption failed via win32crypt: {e}")

    # Fallback to ctypes crypt32.dll
    try:
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte))
            ]

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        in_blob = DATA_BLOB()
        in_blob.cbData = len(raw_bytes)
        in_blob.pbData = ctypes.cast(
            (ctypes.c_byte * len(raw_bytes)).from_buffer_copy(raw_bytes),
            ctypes.POINTER(ctypes.c_byte)
        )

        out_blob = DATA_BLOB()
        desc = ctypes.c_wchar_p("JARVIS_INSTAGRAM_TOKEN")

        success = crypt32.CryptProtectData(
            ctypes.byref(in_blob),
            desc,
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob)
        )
        if not success:
            err = kernel32.GetLastError()
            raise SecurityError(f"CryptProtectData failed with error code: {err}")

        try:
            buf = (ctypes.c_byte * out_blob.cbData)()
            ctypes.memmove(buf, out_blob.pbData, out_blob.cbData)
            encrypted_bytes = bytes(buf)
            return DPAPI_PREFIX + base64.b64encode(encrypted_bytes).decode("utf-8")
        finally:
            kernel32.LocalFree(out_blob.pbData)
    except Exception as e:
        raise SecurityError(f"Windows DPAPI encryption failed via ctypes: {e}")


def decrypt_token(stored_token: Optional[str]) -> str:
    """
    Decrypts a DPAPI-encrypted token string.
    If the string does not have the DPAPI prefix, returns it as-is (e.g. empty or legacy).
    Fails closed: raises SecurityError if decryption of a prefixed token fails.
    """
    if not stored_token:
        return ""
    if not is_encrypted(stored_token):
        return stored_token

    if sys.platform != "win32":
        raise SecurityError("DPAPI decryption requires Windows OS.")

    b64_part = stored_token[len(DPAPI_PREFIX):]
    try:
        encrypted_bytes = base64.b64decode(b64_part.encode("utf-8"))
    except Exception as e:
        raise SecurityError(f"Invalid base64 encoding in stored token: {e}")

    # Try win32crypt first
    try:
        import win32crypt
        _, decrypted_bytes = win32crypt.CryptUnprotectData(
            encrypted_bytes,
            None,
            None,
            None,
            0
        )
        return decrypted_bytes.decode("utf-8")
    except ImportError:
        pass
    except Exception as e:
        raise SecurityError(f"Windows DPAPI decryption failed via win32crypt: {e}")

    # Fallback to ctypes crypt32.dll
    try:
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte))
            ]

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        in_blob = DATA_BLOB()
        in_blob.cbData = len(encrypted_bytes)
        in_blob.pbData = ctypes.cast(
            (ctypes.c_byte * len(encrypted_bytes)).from_buffer_copy(encrypted_bytes),
            ctypes.POINTER(ctypes.c_byte)
        )

        out_blob = DATA_BLOB()
        desc = ctypes.c_wchar_p()

        success = crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            ctypes.byref(desc),
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob)
        )
        if not success:
            err = kernel32.GetLastError()
            raise SecurityError(f"CryptUnprotectData failed with error code: {err}")

        try:
            buf = (ctypes.c_byte * out_blob.cbData)()
            ctypes.memmove(buf, out_blob.pbData, out_blob.cbData)
            return bytes(buf).decode("utf-8")
        finally:
            kernel32.LocalFree(out_blob.pbData)
            if desc.value:
                kernel32.LocalFree(ctypes.cast(desc, wintypes.HLOCAL))
    except Exception as e:
        raise SecurityError(f"Windows DPAPI decryption failed via ctypes: {e}")
