import os
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum


class TXMode(Enum):
    FAST="fast"
    BALANCED="balanced"
    ROBUST="robust"
    STEALTH="stealth"


class RXMode(Enum):
    AUTO="auto"
    MANUAL="manual"
    AGGRESSIVE="aggressive"


class EncryptionMode(Enum):
    NONE="none"
    PSK="psk"
    PUBLIC_KEY="public_key"
    OTP="otp"


@dataclass
class AudioConfig:
    sample_rate: int=48000
    tones: int=8
    symbol_rate: float=100.0
    symbol_duration: float=0.01
    base_freq: float=1000.0
    tone_spacing: float=600.0
    amplitude: float=0.8
    bits_per_tone: int=4
    channels: int=1
    dtype: str="float32"


@dataclass
class PacketConfig:
    preamble_length: int=64
    sync_pattern: List[int]=field(default_factory=lambda: [1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0])
    max_payload_size: int=1024
    session_id_bytes: int=4
    seq_id_bytes: int=4
    total_packets_bytes: int=4
    enc_type_bytes: int=1
    payload_length_bytes: int=2
    crc_bytes: int=4
    end_marker: List[int]=field(default_factory=lambda: [0, 0, 1, 1, 1, 1, 0, 0])


@dataclass
class FECConfig:
    enabled: bool=True
    redundancy: float=0.2
    rs_n: int=255
    rs_k: int=223
    interleave_depth: int=4


@dataclass
class CryptoConfig:
    mode: str="none"
    psk_key_file: str="keys/psk.key"
    rsa_private_key_file: str="keys/private.pem"
    rsa_public_key_file: str="keys/public.pem"
    otp_key_file: str="keys/otp.key"
    pbkdf2_iterations: int=600000
    argon2_memory_cost: int=65536
    argon2_time_cost: int=3
    argon2_parallelism: int=4
    secure_wipe: bool=True


@dataclass
class PathConfig:
    output_dir: str="output"
    received_dir: str="received"
    saved_dir: str="saved"
    keys_dir: str="keys"
    temp_dir: str="temp"
    logs_dir: str="logs"


@dataclass
class DebugConfig:
    enabled: bool=False
    log_level: str="INFO"
    log_to_file: bool=True
    log_file: str="logs/audioburst.log"
    dump_raw_audio: bool=False
    dump_packets: bool=False


@dataclass
class Config:
    audio: AudioConfig=field(default_factory=AudioConfig)
    packet: PacketConfig=field(default_factory=PacketConfig)
    fec: FECConfig=field(default_factory=FECConfig)
    crypto: CryptoConfig=field(default_factory=CryptoConfig)
    paths: PathConfig=field(default_factory=PathConfig)
    debug: DebugConfig=field(default_factory=DebugConfig)
    tx_mode: str="balanced"
    rx_mode: str="auto"
    compression: bool=True
    compression_level: int=6
    multiprocessing: bool=True
    max_workers: int=4
    save_to_wav: bool=True
    mute_sound: bool=False
    confirm_send: bool=True

    def to_dict(self) -> Dict[str, Any]:
        result={}
        for field_name, field_value in asdict(self).items():
            if isinstance(field_value, dict):
                result[field_name]=field_value
            elif hasattr(field_value, '__dataclass_fields__'):
                result[field_name]=asdict(field_value)
            else:
                result[field_name]=field_value
        return result

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'Config':
        with open(filepath, 'r') as f:
            data=json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        config=cls()
        for key, value in data.items():
            if hasattr(config, key):
                attr=getattr(config, key)
                if hasattr(attr, '__dataclass_fields__') and isinstance(value, dict):
                    field_type=type(attr)
                    setattr(config, key, field_type(**value))
                else:
                    setattr(config, key, value)
        return config

    def apply_mode(self, mode: str) -> None:
        self.tx_mode=mode
        if mode == "fast":
            self.audio.tones=32
            self.audio.symbol_rate=200.0
            self.audio.symbol_duration=0.005
            self.audio.tone_spacing=400.0
            self.fec.redundancy=0.1
            self.fec.enabled=True
            self.audio.amplitude=0.9
        elif mode == "balanced":
            self.audio.tones=8
            self.audio.symbol_rate=100.0
            self.audio.symbol_duration=0.01
            self.audio.tone_spacing=600.0
            self.fec.redundancy=0.2
            self.fec.enabled=True
            self.audio.amplitude=0.8
        elif mode == "robust":
            self.audio.tones=4
            self.audio.symbol_rate=50.0
            self.audio.symbol_duration=0.02
            self.audio.tone_spacing=800.0
            self.fec.redundancy=0.5
            self.fec.enabled=True
            self.audio.amplitude=0.8
        elif mode == "stealth":
            self.audio.tones=4
            self.audio.symbol_rate=25.0
            self.audio.symbol_duration=0.04
            self.audio.tone_spacing=800.0
            self.fec.redundancy=0.3
            self.fec.enabled=True
            self.audio.amplitude=0.2


DEFAULT_CONFIG=Config()
