import time
import threading
import numpy as np
from typing import Optional, Callable, List
from scipy.io import wavfile
from audioburst.config import Config
from audioburst.protocol.frame import Frame
from audioburst.protocol.serializer import decode_packet, find_packet_boundaries
from audioburst.protocol.session import SessionManager
from audioburst.modem.demod import MultiToneDemodulator
from audioburst.modem.sampler import AudioSampler
from audioburst.rx.sync import SyncDetector
from audioburst.rx.decoder import Decoder
from audioburst.utils.logger import log


class Receiver:
    def __init__(self, config: Config):
        self.config=config
        self.demodulator=MultiToneDemodulator(config.audio)
        self.sampler=AudioSampler(config.audio)
        self.sync_detector=SyncDetector(config.audio)
        self.decoder=Decoder(config)
        self.session_manager=SessionManager(timeout=60.0)
        self._running=False
        self._thread: Optional[threading.Thread]=None
        self._progress_callback: Optional[Callable]=None
        self._complete_callback: Optional[Callable]=None
        self._captured_audio: List[np.ndarray]=[]
        self._lock=threading.Lock()

    def set_progress_callback(self, callback: Callable) -> None:
        self._progress_callback=callback

    def set_complete_callback(self, callback: Callable) -> None:
        self._complete_callback=callback

    def _process_audio_chunk(self, audio: np.ndarray) -> List[Frame]:
        data_start=self.sync_detector.auto_sync(audio)
        if data_start is None:
            silence_samples=int(self.config.audio.sample_rate * 0.1)
            preamble_samples=int(self.config.audio.sample_rate * 0.001 * self.config.packet.preamble_length)
            sync_samples=int(self.config.audio.sample_rate * 0.02)
            data_start=silence_samples + preamble_samples + sync_samples
        data_audio=audio[data_start:]
        symbols=self.demodulator.decode_stream(data_audio)
        if not symbols:
            return []
        raw_data=b''.join(symbols)
        boundaries=find_packet_boundaries(raw_data)
        frames=[]
        for start, end in boundaries:
            packet=raw_data[start:end]
            frame=decode_packet(packet)
            if frame is not None:
                frames.append(frame)
        return frames

    def _run_loop(self) -> None:
        self.sampler.start()
        log.info("Receiver listening for transmissions...")
        buffer=np.array([], dtype=np.float32)
        min_process_size=self.demodulator.samples_per_symbol * 4
        while self._running:
            chunk=self.sampler.read(timeout=0.5)
            if chunk is not None:
                buffer=np.concatenate([buffer, chunk])
                with self._lock:
                    self._captured_audio.append(chunk)
            if len(buffer) >= min_process_size:
                if self.demodulator.detect_signal_presence(buffer):
                    data_start=self.sync_detector.auto_sync(buffer)
                    if data_start is not None and data_start < len(buffer):
                        data_audio=buffer[data_start:]
                        frames=self._process_audio_chunk(data_audio)
                        for frame in frames:
                            self.session_manager.add_packet(
                                frame.session_id,
                                frame.seq_id,
                                frame.total_packets,
                                frame.enc_type,
                                frame.payload,
                            )
                            if self._progress_callback:
                                session=self.session_manager.get_session(frame.session_id)
                                if session:
                                    self._progress_callback(
                                        len(session.received_packets),
                                        session.total_packets,
                                    )
                        buffer=np.array([], dtype=np.float32)
                else:
                    if len(buffer) > self.demodulator.sample_rate * 5:
                        buffer=buffer[-self.demodulator.sample_rate * 2:]
        self.sampler.stop()

    def start_listening(self) -> None:
        if self._running:
            return
        self._running=True
        self._thread=threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop_listening(self) -> None:
        self._running=False
        if self._thread:
            self._thread.join(timeout=2.0)
        self.sampler.stop()

    def listen_blocking(self, timeout: float=30.0) -> Optional[bytes]:
        self.sampler.start()
        log.info(f"Listening for {timeout}s...")
        buffer=np.array([], dtype=np.float32)
        deadline=time.time() + timeout
        min_process_size=self.demodulator.samples_per_symbol * 4
        all_frames: List[Frame]=[]
        while time.time() < deadline:
            chunk=self.sampler.read(timeout=0.5)
            if chunk is not None:
                buffer=np.concatenate([buffer, chunk])
            if len(buffer) >= min_process_size:
                if self.demodulator.detect_signal_presence(buffer):
                    data_start=self.sync_detector.auto_sync(buffer)
                    if data_start is not None and data_start < len(buffer):
                        data_audio=buffer[data_start:]
                        frames=self._process_audio_chunk(data_audio)
                        all_frames.extend(frames)
                        buffer=np.array([], dtype=np.float32)
                        if frames:
                            deadline=time.time() + 5.0
                else:
                    if len(buffer) > self.demodulator.sample_rate * 5:
                        buffer=buffer[-self.demodulator.sample_rate * 2:]
        self.sampler.stop()
        if not all_frames:
            log.warning("No frames received")
            return None
        log.info(f"Received {len(all_frames)} frames")
        return self.decoder.reconstruct_data(all_frames)

    def receive_and_save(self, output_dir: str, timeout: float=30.0) -> Optional[str]:
        data=self.listen_blocking(timeout)
        if data is None:
            return None
        return self.decoder.save_received_data(data, output_dir)

    def decode_from_wav(self, wav_path: str) -> Optional[bytes]:
        try:
            sample_rate, audio=wavfile.read(wav_path)
        except Exception as e:
            log.error(f"Failed to read WAV file {wav_path}: {e}")
            return None
        if audio.ndim > 1:
            audio=audio.mean(axis=1)
        audio=audio.astype(np.float32)
        if np.max(np.abs(audio)) > 0:
            audio=audio / np.max(np.abs(audio))
        log.info(f"Loaded WAV: {wav_path} ({len(audio)} samples @ {sample_rate} Hz)")
        if sample_rate != self.config.audio.sample_rate:
            log.warning(f"WAV sample rate {sample_rate} differs from config {self.config.audio.sample_rate}")
        frames=self._process_audio_chunk(audio)
        if not frames:
            log.warning("No frames decoded from WAV file")
            return None
        log.info(f"Decoded {len(frames)} frames from WAV")
        return self.decoder.reconstruct_data(frames)

    def receive_from_wav(self, wav_path: str, output_dir: str) -> Optional[str]:
        data=self.decode_from_wav(wav_path)
        if data is None:
            return None
        return self.decoder.save_received_data(data, output_dir)

    def get_captured_audio(self) -> np.ndarray:
        with self._lock:
            if not self._captured_audio:
                return np.array([], dtype=np.float32)
            return np.concatenate(self._captured_audio)

    def clear_captured_audio(self) -> None:
        with self._lock:
            self._captured_audio.clear()
