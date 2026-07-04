import time
import os
import struct
import numpy as np
from typing import Optional, Callable
from scipy.io import wavfile
from audioburst.config import Config, EncryptionMode
from audioburst.protocol.frame import Frame
from audioburst.protocol.serializer import encode_frame
from audioburst.protocol.session import SessionManager
from audioburst.modem.multitone import MultiToneGenerator
from audioburst.modem.sampler import AudioPlayer
from audioburst.tx.encoder import encode_payload, chunk_for_transmission, create_metadata_packet
from audioburst.tx.file_loader import prepare_transmission_data
from audioburst.fec.reedsolomon import ReedSolomonEncoder
from audioburst.fec.crc import crc32
from audioburst.crypto.aes import aes_encrypt, load_aes_key, derive_key_from_passphrase
from audioburst.crypto.rsa import hybrid_encrypt, load_key_file
from audioburst.crypto.otp import otp_encrypt, load_otp_key
from audioburst.utils.helpers import generate_session_id, generate_nonce, ensure_dir, timestamp_str
from audioburst.utils.logger import log


class Transmitter:
    def __init__(self, config: Config):
        self.config=config
        self.generator=MultiToneGenerator(config.audio)
        self.player=AudioPlayer(config.audio)
        self.rs_encoder=ReedSolomonEncoder(config.fec.rs_n, config.fec.rs_k)
        self._progress_callback: Optional[Callable]=None

    def set_progress_callback(self, callback: Callable) -> None:
        self._progress_callback=callback

    def _encrypt_payload(self, data: bytes) -> bytes:
        mode=self.config.crypto.mode
        if mode == EncryptionMode.NONE.value:
            return data
        elif mode == EncryptionMode.PSK.value:
            key=load_aes_key(self.config.crypto.psk_key_file)
            return aes_encrypt(key, data)
        elif mode == EncryptionMode.PUBLIC_KEY.value:
            pub_key=load_key_file(self.config.crypto.rsa_public_key_file)
            return hybrid_encrypt(pub_key, data)
        elif mode == EncryptionMode.OTP.value:
            key=load_otp_key(self.config.crypto.otp_key_file)
            result=otp_encrypt(key, data)
            if result is None:
                log.error("OTP encryption failed")
                return data
            return result
        return data

    def _get_enc_type(self) -> int:
        mode=self.config.crypto.mode
        if mode == EncryptionMode.NONE.value:
            return 0
        elif mode == EncryptionMode.PSK.value:
            return 1
        elif mode == EncryptionMode.PUBLIC_KEY.value:
            return 2
        elif mode == EncryptionMode.OTP.value:
            return 3
        return 0

    def _build_frames(self, data: bytes, session_id: int) -> list:
        encoded=encode_payload(data, self.config)
        encrypted=self._encrypt_payload(encoded)
        max_payload=self.config.packet.max_payload_size
        if self.config.fec.enabled:
            max_payload=max_payload * self.config.fec.rs_k // self.config.fec.rs_n
        chunks=chunk_for_transmission(encrypted, max_payload)
        total=len(chunks)
        frames=[]
        for i, chunk in enumerate(chunks):
            crc_val=crc32(chunk)
            if self.config.fec.enabled:
                chunk=self.rs_encoder.encode(chunk)
            frame=Frame(
                session_id=session_id,
                seq_id=i,
                total_packets=total,
                enc_type=self._get_enc_type(),
                payload=chunk,
                crc=crc_val,
            )
            frames.append(frame)
        return frames

    def _build_audio_signal(self, frames: list) -> np.ndarray:
        preamble=self.generator.generate_preamble(self.config.packet.preamble_length)
        sync=self.generator.generate_sync()
        silence=self.generator.generate_silence(0.1)
        parts=[silence, preamble, sync]
        bytes_per_symbol=(self.generator.num_tones + 7) // 8
        for frame in frames:
            packet=encode_frame(frame, self.config.packet)
            data_chunks=[
                packet[j:j + bytes_per_symbol].ljust(bytes_per_symbol, b'\x00')
                for j in range(0, len(packet), bytes_per_symbol)
            ]
            signal=self.generator.encode_stream(data_chunks)
            parts.append(signal)
        parts.append(silence)
        return np.concatenate(parts).astype(np.float32)

    def _save_to_wav(self, signal: np.ndarray, name: str) -> str:
        saved_dir=self.config.paths.saved_dir
        ensure_dir(saved_dir)
        ts=timestamp_str()
        safe_name=name.replace('/', '_').replace(' ', '_')
        filepath=os.path.join(saved_dir, f"{safe_name}_{ts}.wav")
        normalized=signal / max(np.max(np.abs(signal)), 1e-10)
        normalized=(normalized * 0.9).astype(np.float32)
        wavfile.write(filepath, self.config.audio.sample_rate, normalized)
        log.info(f"Audio saved to WAV: {filepath}")
        return filepath

    def _self_test_wav(self, wav_path: str, original_data: bytes) -> bool:
        try:
            from audioburst.rx.receiver import Receiver
            rx=Receiver(self.config)
            decoded=rx.decode_from_wav(wav_path)
            if decoded is None:
                log.error("Self-test FAILED: could not decode WAV")
                return False
            if decoded != original_data:
                log.error(f"Self-test FAILED: data mismatch (expected {len(original_data)} bytes, got {len(decoded)} bytes)")
                return False
            log.info("Self-test PASSED: WAV decodes correctly")
            return True
        except Exception as e:
            log.error(f"Self-test FAILED: {e}")
            return False

    def _transmit_frames(self, frames: list, name: str="transmission", original_data: bytes=b"") -> None:
        total=len(frames)
        log.info(f"Transmitting {total} frames...")
        signal=self._build_audio_signal(frames)
        wav_path=None
        if self.config.save_to_wav:
            wav_path=self._save_to_wav(signal, name)
            if original_data:
                if not self._self_test_wav(wav_path, original_data):
                    log.error("WAV file may be corrupted — self-test failed")
        if not self.config.mute_sound:
            self.player.start()
            self.player.play(signal)
            self.player.stop()
        else:
            log.info("Sound muted — skipping audio playback")
        log.info("Transmission complete")

    def send_file(self, filepath: str) -> bool:
        data, name, is_folder=prepare_transmission_data(filepath)
        if not data:
            log.error(f"No data to send from: {filepath}")
            return False
        log.info(f"Sending: {name} ({len(data)} bytes, folder={is_folder})")
        session_id=generate_session_id()
        meta=create_metadata_packet(name, len(data), is_folder)
        full_data=struct.pack('>I', len(meta)) + meta + data
        frames=self._build_frames(full_data, session_id)
        self._transmit_frames(frames, name, full_data)
        return True

    def send_text(self, text: str) -> bool:
        data=text.encode('utf-8')
        log.info(f"Sending text message: {len(data)} bytes")
        session_id=generate_session_id()
        meta=create_metadata_packet("message.txt", len(data), False)
        full_data=struct.pack('>I', len(meta)) + meta + data
        frames=self._build_frames(full_data, session_id)
        self._transmit_frames(frames, "text_message", full_data)
        return True

    def send_raw_data(self, data: bytes, name: str="data.bin") -> bool:
        log.info(f"Sending raw data: {name} ({len(data)} bytes)")
        session_id=generate_session_id()
        meta=create_metadata_packet(name, len(data), False)
        full_data=struct.pack('>I', len(meta)) + meta + data
        frames=self._build_frames(full_data, session_id)
        self._transmit_frames(frames, name, full_data)
        return True
