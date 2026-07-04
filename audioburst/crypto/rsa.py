import os
import secrets
from typing import Tuple, Optional
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from audioburst.utils.helpers import generate_nonce
from audioburst.utils.logger import log


def generate_rsa_keypair(key_size: int=4096) -> Tuple[bytes, bytes]:
    private_key=rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )
    public_key=private_key.public_key()
    private_pem=private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem=public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def load_private_key(pem_data: bytes) -> rsa.RSAPrivateKey:
    return serialization.load_pem_private_key(pem_data, password=None)


def load_public_key(pem_data: bytes) -> rsa.RSAPublicKey:
    return serialization.load_pem_public_key(pem_data)


def rsa_encrypt_session_key(public_key_pem: bytes, session_key: bytes) -> bytes:
    pub_key=load_public_key(public_key_pem)
    encrypted=pub_key.encrypt(
        session_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return encrypted


def rsa_decrypt_session_key(private_key_pem: bytes, encrypted_key: bytes) -> Optional[bytes]:
    try:
        priv_key=load_private_key(private_key_pem)
        return priv_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except Exception:
        log.error("RSA session key decryption failed")
        return None


def hybrid_encrypt(public_key_pem: bytes, plaintext: bytes) -> bytes:
    session_key=AESGCM.generate_key(bit_length=256)
    encrypted_key=rsa_encrypt_session_key(public_key_pem, session_key)
    nonce=generate_nonce(12)
    aesgcm=AESGCM(session_key)
    ciphertext=aesgcm.encrypt(nonce, plaintext, None)
    key_len=len(encrypted_key).to_bytes(2, 'big')
    return key_len + encrypted_key + nonce + ciphertext


def hybrid_decrypt(private_key_pem: bytes, data: bytes) -> Optional[bytes]:
    try:
        key_len=int.from_bytes(data[:2], 'big')
        encrypted_key=data[2:2 + key_len]
        nonce=data[2 + key_len:2 + key_len + 12]
        ciphertext=data[2 + key_len + 12:]
        session_key=rsa_decrypt_session_key(private_key_pem, encrypted_key)
        if session_key is None:
            return None
        aesgcm=AESGCM(session_key)
        return aesgcm.decrypt(nonce, ciphertext, None)
    except Exception:
        log.error("Hybrid decryption failed")
        return None


def save_key_file(data: bytes, filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, 'wb') as f:
        f.write(data)
    os.chmod(filepath, 0o600)


def load_key_file(filepath: str) -> bytes:
    with open(filepath, 'rb') as f:
        return f.read()
