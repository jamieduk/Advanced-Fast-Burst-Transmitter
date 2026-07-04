import os
import hashlib
import secrets
from typing import Tuple, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from audioburst.utils.helpers import generate_nonce, secure_wipe
from audioburst.utils.logger import log


def derive_key_from_passphrase(passphrase: str, salt: Optional[bytes]=None,
                                iterations: int=600000) -> Tuple[bytes, bytes]:
    if salt is None:
        salt=secrets.token_bytes(16)
    kdf=PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    key=kdf.derive(passphrase.encode('utf-8'))
    return key, salt


def aes_encrypt(key: bytes, plaintext: bytes) -> bytes:
    nonce=generate_nonce(12)
    aesgcm=AESGCM(key)
    ciphertext=aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def aes_decrypt(key: bytes, data: bytes) -> Optional[bytes]:
    if len(data) < 28:
        return None
    nonce=data[:12]
    ciphertext=data[12:]
    try:
        aesgcm=AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)
    except Exception:
        log.error("AES-GCM decryption failed: authentication tag mismatch")
        return None


def generate_aes_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def save_aes_key(key: bytes, filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, 'wb') as f:
        f.write(key)
    os.chmod(filepath, 0o600)


def load_aes_key(filepath: str) -> bytes:
    with open(filepath, 'rb') as f:
        return f.read()


def key_fingerprint(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()[:16]
