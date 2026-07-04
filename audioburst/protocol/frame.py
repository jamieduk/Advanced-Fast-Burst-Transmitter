import struct
from dataclasses import dataclass
from typing import Optional, List
from audioburst.config import PacketConfig


@dataclass
class Frame:
    session_id: int
    seq_id: int
    total_packets: int
    enc_type: int
    payload: bytes
    crc: int=0

    def serialize(self, config: PacketConfig) -> bytes:
        payload_len=len(self.payload)
        header=struct.pack(
            '>IIIBH',
            self.session_id,
            self.seq_id,
            self.total_packets,
            self.enc_type,
            payload_len
        )
        frame_data=header + self.payload
        crc_val=self.crc if self.crc else 0
        frame_data += struct.pack('>I', crc_val)
        return frame_data

    @classmethod
    def deserialize(cls, data: bytes, config: PacketConfig) -> Optional['Frame']:
        header_size=4 + 4 + 4 + 1 + 2
        if len(data) < header_size + 4:
            return None
        session_id, seq_id, total_packets, enc_type, payload_len=struct.unpack(
            '>IIIBH', data[:header_size]
        )
        payload_start=header_size
        payload_end=payload_start + payload_len
        if payload_end + 4 > len(data):
            return None
        payload=data[payload_start:payload_end]
        crc=struct.unpack('>I', data[payload_end:payload_end + 4])[0]
        return cls(
            session_id=session_id,
            seq_id=seq_id,
            total_packets=total_packets,
            enc_type=enc_type,
            payload=payload,
            crc=crc
        )

    def __repr__(self) -> str:
        return f"Frame(sid={self.session_id}, seq={self.seq_id}/{self.total_packets}, enc={self.enc_type}, len={len(self.payload)})"
