import struct
import zlib
from typing import Optional
from audioburst.utils.logger import log


def crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def crc32_bytes(data: bytes) -> bytes:
    return struct.pack('>I', crc32(data))


def verify_crc32(data: bytes, expected_crc: int) -> bool:
    actual=crc32(data)
    return actual == expected_crc


def crc32_hex(data: bytes) -> str:
    return f"{crc32(data):08X}"


def append_crc32(data: bytes) -> bytes:
    return data + crc32_bytes(data)


def extract_and_verify(data: bytes) -> Optional[bytes]:
    if len(data) < 4:
        return None
    payload=data[:-4]
    expected=struct.unpack('>I', data[-4:])[0]
    if verify_crc32(payload, expected):
        return payload
    log.error("CRC32 verification failed")
    return None
