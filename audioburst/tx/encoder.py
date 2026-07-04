import base64
import zlib
import struct
from typing import List, Optional
from audioburst.config import Config
from audioburst.utils.logger import log


def base64_encode(data: bytes) -> bytes:
    return base64.b64encode(data)


def base64_decode(data: bytes) -> Optional[bytes]:
    try:
        return base64.b64decode(data)
    except Exception:
        log.error("Base64 decode failed")
        return None


def compress_data(data: bytes, level: int=6) -> bytes:
    compressed=zlib.compress(data, level)
    if len(compressed) < len(data):
        return b'\x01' + struct.pack('>I', len(data)) + compressed
    return b'\x00' + struct.pack('>I', len(data)) + data


def decompress_data(data: bytes) -> Optional[bytes]:
    if len(data) < 5:
        return None
    flag=data[0]
    original_len=struct.unpack('>I', data[1:5])[0]
    payload=data[5:]
    if flag == 0x01:
        try:
            return zlib.decompress(payload)[:original_len]
        except Exception:
            log.error("Decompression failed")
            return None
    return payload[:original_len]


def encode_payload(data: bytes, config: Config) -> bytes:
    if config.compression:
        data=compress_data(data, config.compression_level)
    encoded=base64_encode(data)
    return encoded


def decode_payload(data: bytes, config: Config) -> Optional[bytes]:
    decoded=base64_decode(data)
    if decoded is None:
        return None
    if config.compression:
        return decompress_data(decoded)
    return decoded


def chunk_for_transmission(data: bytes, max_chunk_size: int) -> List[bytes]:
    return [data[i:i + max_chunk_size] for i in range(0, len(data), max_chunk_size)]


def create_metadata_packet(filename: str, file_size: int, is_folder: bool=False) -> bytes:
    meta={
        'filename': filename,
        'file_size': file_size,
        'is_folder': is_folder,
    }
    import json
    return json.dumps(meta).encode('utf-8')
