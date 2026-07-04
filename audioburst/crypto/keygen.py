import os
import hashlib
from typing import Tuple
from audioburst.crypto.aes import generate_aes_key, save_aes_key, key_fingerprint
from audioburst.crypto.rsa import generate_rsa_keypair, save_key_file
from audioburst.crypto.otp import generate_otp_key, save_otp_key
from audioburst.utils.logger import log


def generate_all_keys(keys_dir: str) -> dict:
    os.makedirs(keys_dir, exist_ok=True)
    results={}

    aes_key=generate_aes_key()
    aes_path=os.path.join(keys_dir, "psk.key")
    save_aes_key(aes_key, aes_path)
    results['psk']={'path': aes_path, 'fingerprint': key_fingerprint(aes_key)}
    log.info(f"PSK key saved: {aes_path}")

    private_pem, public_pem=generate_rsa_keypair()
    priv_path=os.path.join(keys_dir, "private.pem")
    pub_path=os.path.join(keys_dir, "public.pem")
    save_key_file(private_pem, priv_path)
    save_key_file(public_pem, pub_path)
    results['rsa_private']={'path': priv_path}
    results['rsa_public']={'path': pub_path}
    log.info(f"RSA keypair saved: {priv_path}, {pub_path}")

    otp_key=generate_otp_key(1024 * 1024)
    otp_path=os.path.join(keys_dir, "otp.key")
    save_otp_key(otp_key, otp_path)
    results['otp']={'path': otp_path, 'size': len(otp_key)}
    log.info(f"OTP key saved: {otp_path} ({len(otp_key)} bytes)")

    return results


def display_key_info(keys_dir: str) -> None:
    print("\n=== Key Information ===")
    for filename in os.listdir(keys_dir):
        filepath=os.path.join(keys_dir, filename)
        if os.path.isfile(filepath):
            size=os.path.getsize(filepath)
            with open(filepath, 'rb') as f:
                data=f.read()
            fp=hashlib.sha256(data).hexdigest()[:16]
            print(f"  {filename}: {size} bytes, fingerprint: {fp}")
    print()
