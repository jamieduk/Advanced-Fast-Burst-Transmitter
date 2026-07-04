import struct
from typing import List, Optional
from audioburst.utils.logger import log

try:
    from reedsolo import RSCodec, ReedSolomonError
    HAS_REEDSOLO=True
except ImportError:
    HAS_REEDSOLO=False
    log.warning("reedsolo not installed. Install with: pip install reedsolo")


class ReedSolomonEncoder:
    def __init__(self, n: int=255, k: int=223):
        self.n=n
        self.k=k
        self.nsym=n - k
        if HAS_REEDSOLO:
            self._codec=RSCodec(self.nsym)
        else:
            self._codec=None

    def encode(self, data: bytes) -> bytes:
        if self._codec is None:
            return data
        try:
            return bytes(self._codec.encode(bytearray(data)))
        except Exception as e:
            log.error(f"RS encode error: {e}")
            return data

    def decode(self, data: bytes) -> Optional[bytes]:
        if self._codec is None:
            return data
        try:
            decoded, _, _=self._codec.decode(bytearray(data))
            return bytes(decoded)
        except ReedSolomonError:
            log.error("RS decode failed: too many errors to correct")
            return None
        except Exception as e:
            log.error(f"RS decode error: {e}")
            return None

    def encode_blocks(self, data: bytes, block_size: int) -> List[bytes]:
        blocks=[]
        for i in range(0, len(data), block_size):
            block=data[i:i + block_size]
            if len(block) < block_size:
                block=block + b'\x00' * (block_size - len(block))
            encoded=self.encode(block)
            blocks.append(encoded)
        return blocks

    def decode_blocks(self, blocks: List[bytes], original_length: int,
                      block_size: int) -> Optional[bytes]:
        decoded_blocks=[]
        for block in blocks:
            result=self.decode(block)
            if result is None:
                return None
            decoded_blocks.append(result[:block_size])
        data=b''.join(decoded_blocks)
        return data[:original_length]
