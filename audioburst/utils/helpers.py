import os
import struct
import hashlib
import secrets
import time
from typing import Tuple, Optional


def generate_session_id() -> int:
    return secrets.randbits(32)


def generate_nonce(length: int=12) -> bytes:
    return secrets.token_bytes(length)


def bytes_to_int_be(data: bytes) -> int:
    return int.from_bytes(data, 'big')


def int_to_bytes_be(value: int, length: int) -> bytes:
    return value.to_bytes(length, 'big')


def secure_wipe(data: bytearray) -> None:
    for i in range(len(data)):
        data[i]=0


def file_checksum(filepath: str, algorithm: str="sha256") -> str:
    h=hashlib.new(algorithm)
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def timestamp_str() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def chunk_data(data: bytes, chunk_size: int) -> list:
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]


def interleave_blocks(blocks: list, depth: int) -> list:
    if depth <= 1:
        return blocks
    result=[]
    for i in range(0, len(blocks), depth):
        group=blocks[i:i + depth]
        max_len=max(len(b) for b in group)
        for j in range(max_len):
            for b in group:
                if j < len(b):
                    result.append(bytes([b[j]]))
    return result


def deinterleave_blocks(blocks: list, original_count: int, depth: int) -> list:
    if depth <= 1:
        return blocks
    result=[bytearray() for _ in range(original_count)]
    idx=0
    group_count=(original_count + depth - 1) // depth
    for g in range(group_count):
        group_size=min(depth, original_count - g * depth)
        max_len=0
        for b_idx in range(group_size):
            max_len=max(max_len, len(blocks[idx + b_idx]) if idx + b_idx < len(blocks) else 0)
        for j in range(max_len):
            for b_idx in range(group_size):
                if idx < len(blocks) and j < len(blocks[idx]):
                    result[g * depth + b_idx].append(blocks[idx][j])
                idx += 1
    return [bytes(r) for r in result]
