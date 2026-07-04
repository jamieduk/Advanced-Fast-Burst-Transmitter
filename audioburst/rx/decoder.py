import struct
import json
import os
from typing import Optional, List, Tuple
from audioburst.config import Config, EncryptionMode
from audioburst.protocol.frame import Frame
from audioburst.fec.reedsolomon import ReedSolomonEncoder
from audioburst.fec.crc import verify_crc32
from audioburst.tx.encoder import decode_payload
from audioburst.tx.file_loader import unpack_folder
from audioburst.crypto.aes import aes_decrypt, load_aes_key
from audioburst.crypto.rsa import hybrid_decrypt, load_key_file
from audioburst.crypto.otp import otp_decrypt, load_otp_key
from audioburst.utils.helpers import ensure_dir
from audioburst.utils.logger import log


class Decoder:
    def __init__(self, config: Config):
        self.config=config
        self.rs_encoder=ReedSolomonEncoder(config.fec.rs_n, config.fec.rs_k)

    def _decrypt_payload(self, data: bytes, enc_type: int) -> Optional[bytes]:
        if enc_type == 0:
            return data
        elif enc_type == 1:
            key=load_aes_key(self.config.crypto.psk_key_file)
            return aes_decrypt(key, data)
        elif enc_type == 2:
            priv_key=load_key_file(self.config.crypto.rsa_private_key_file)
            return hybrid_decrypt(priv_key, data)
        elif enc_type == 3:
            key=load_otp_key(self.config.crypto.otp_key_file)
            return otp_decrypt(key, data)
        return data

    def _fec_decode(self, data: bytes) -> Optional[bytes]:
        if not self.config.fec.enabled:
            return data
        return self.rs_encoder.decode(data)

    def decode_frame(self, frame: Frame) -> Optional[bytes]:
        payload=frame.payload
        if self.config.fec.enabled:
            payload=self._fec_decode(payload)
            if payload is None:
                log.error(f"FEC decode failed for frame {frame.seq_id}")
                return None
        if not verify_crc32(payload, frame.crc):
            log.error(f"CRC check failed for frame {frame.seq_id}")
            return None
        decrypted=self._decrypt_payload(payload, frame.enc_type)
        if decrypted is None:
            log.error(f"Decryption failed for frame {frame.seq_id}")
            return None
        decoded=decode_payload(decrypted, self.config)
        return decoded

    def reconstruct_data(self, frames: List[Frame]) -> Optional[bytes]:
        sorted_frames=sorted(frames, key=lambda f: f.seq_id)
        seen=set()
        unique_frames=[]
        for f in sorted_frames:
            if f.seq_id not in seen:
                seen.add(f.seq_id)
                unique_frames.append(f)
        payloads=[]
        for frame in unique_frames:
            result=self.decode_frame(frame)
            if result is not None:
                payloads.append(result)
        if not payloads:
            return None
        return b''.join(payloads)

    def extract_metadata(self, data: bytes) -> Tuple[str, int, bool, bytes]:
        if len(data) < 4:
            return "unknown.bin", 0, False, data
        meta_len=struct.unpack('>I', data[:4])[0]
        if meta_len > len(data) - 4:
            return "unknown.bin", 0, False, data
        meta_bytes=data[4:4 + meta_len]
        try:
            meta=json.loads(meta_bytes.decode('utf-8'))
        except Exception:
            return "unknown.bin", 0, False, data[4:]
        filename=meta.get('filename', 'unknown.bin')
        file_size=meta.get('file_size', 0)
        is_folder=meta.get('is_folder', False)
        payload=data[4 + meta_len:]
        return filename, file_size, is_folder, payload

    def save_received_data(self, data: bytes, output_dir: str) -> Optional[str]:
        filename, file_size, is_folder, payload=self.extract_metadata(data)
        ensure_dir(output_dir)
        if is_folder:
            folder_name=filename.replace('.tar', '').replace('.gz', '').replace('.tgz', '')
            extract_dir=os.path.join(output_dir, folder_name)
            ensure_dir(extract_dir)
            if unpack_folder(payload, extract_dir):
                log.info(f"Folder extracted to: {extract_dir}")
                return extract_dir
            return None
        else:
            filepath=os.path.join(output_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(payload[:file_size] if file_size > 0 else payload)
            log.info(f"File saved to: {filepath}")
            return filepath
