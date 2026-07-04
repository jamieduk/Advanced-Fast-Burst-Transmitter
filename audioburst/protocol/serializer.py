import struct
import base64
from typing import List, Optional
from audioburst.config import PacketConfig
from audioburst.protocol.frame import Frame


PREAMBLE=bytes([0xAA] * 16)
SYNC_HEADER=bytes([0xAB, 0xCD, 0xEF, 0x01])
END_MARKER=bytes([0xBA, 0xDC, 0xFE, 0x02])


def encode_frame(frame: Frame, config: PacketConfig) -> bytes:
    raw=frame.serialize(config)
    encoded=base64.b64encode(raw)
    packet=PREAMBLE + SYNC_HEADER + encoded + END_MARKER
    return packet


def decode_packet(packet: bytes) -> Optional[Frame]:
    try:
        pre_idx=packet.find(PREAMBLE)
        if pre_idx == -1:
            return None
        sync_idx=packet.find(SYNC_HEADER, pre_idx + len(PREAMBLE))
        if sync_idx == -1:
            return None
        data_start=sync_idx + len(SYNC_HEADER)
        end_idx=packet.find(END_MARKER, data_start)
        if end_idx == -1:
            return None
        encoded=packet[data_start:end_idx]
        raw=base64.b64decode(encoded)
        config=PacketConfig()
        return Frame.deserialize(raw, config)
    except Exception:
        return None


def find_packet_boundaries(data: bytes) -> List[tuple]:
    boundaries=[]
    pos=0
    while True:
        pre_idx=data.find(PREAMBLE, pos)
        if pre_idx == -1:
            break
        sync_idx=data.find(SYNC_HEADER, pre_idx + len(PREAMBLE))
        if sync_idx == -1:
            pos=pre_idx + 1
            continue
        end_idx=data.find(END_MARKER, sync_idx + len(SYNC_HEADER))
        if end_idx == -1:
            pos=pre_idx + 1
            continue
        boundaries.append((pre_idx, end_idx + len(END_MARKER)))
        pos=end_idx + len(END_MARKER)
    return boundaries
