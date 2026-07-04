import os
import secrets
from typing import Optional
from audioburst.utils.helpers import secure_wipe
from audioburst.utils.logger import log


def generate_otp_key(length: int) -> bytes:
    return secrets.token_bytes(length)


def otp_encrypt(key: bytes, plaintext: bytes) -> Optional[bytes]:
    if len(key) < len(plaintext):
        log.error(f"OTP key too short: need {len(plaintext)} bytes, have {len(key)}")
        return None
    result=bytes(a ^ b for a, b in zip(plaintext, key[:len(plaintext)]))
    return result


def otp_decrypt(key: bytes, ciphertext: bytes) -> Optional[bytes]:
    return otp_encrypt(key, ciphertext)


def save_otp_key(key: bytes, filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, 'wb') as f:
        f.write(key)
    os.chmod(filepath, 0o600)


def load_otp_key(filepath: str) -> bytes:
    with open(filepath, 'rb') as f:
        return f.read()


def check_key_reuse(key: bytes, used_offset: int, needed: int) -> bool:
    if used_offset + needed > len(key):
        log.warning("OTP key reuse detected! This breaks OTP security guarantees.")
        return True
    return False
