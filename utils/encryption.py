import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_fernet = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key_hex = os.getenv("ENCRYPTION_KEY", "")
        if not key_hex:
            key_hex = Fernet.generate_key().decode()
        if len(key_hex) == 64:
            raw = bytes.fromhex(key_hex)
            key = base64.urlsafe_b64encode(raw)
        else:
            key = key_hex.encode() if isinstance(key_hex, str) else key_hex
        _fernet = Fernet(key)
    return _fernet


def encrypt_value(plaintext: str) -> str:
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
