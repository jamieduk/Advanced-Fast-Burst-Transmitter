import numpy as np
import sounddevice as sd
import queue
import threading
import time
from typing import Optional, Callable
from audioburst.config import AudioConfig
from audioburst.utils.logger import log


class AudioSampler:
    def __init__(self, config: AudioConfig):
        self.config=config
        self.sample_rate=config.sample_rate
        self.channels=config.channels
        self.dtype=np.float32
        self._buffer=queue.Queue(maxsize=1000)
        self._stream: Optional[sd.InputStream]=None
        self._running=False
        self._thread: Optional[threading.Thread]=None
        self._callback: Optional[Callable]=None
        self._total_samples=0

    def _audio_callback(self, indata: np.ndarray, frames: int,
                         time_info, status) -> None:
        if status:
            log.warning(f"Audio input status: {status}")
        try:
            self._buffer.put_nowait(indata.copy().flatten())
            self._total_samples += frames
        except queue.Full:
            pass

    def start(self, device: Optional[int]=None) -> None:
        if self._running:
            return
        self._running=True
        self._stream=sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            device=device,
            callback=self._audio_callback,
            blocksize=int(self.sample_rate * 0.05),
        )
        self._stream.start()
        log.info(f"Audio capture started: {self.sample_rate} Hz, {self.channels} ch")

    def stop(self) -> None:
        self._running=False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream=None
        log.info("Audio capture stopped")

    def read(self, timeout: float=1.0) -> Optional[np.ndarray]:
        try:
            return self._buffer.get(timeout=timeout)
        except queue.Empty:
            return None

    def read_all(self) -> np.ndarray:
        chunks=[]
        while True:
            chunk=self.read(timeout=0.1)
            if chunk is None:
                break
            chunks.append(chunk)
        if not chunks:
            return np.array([], dtype=self.dtype)
        return np.concatenate(chunks)

    def read_samples(self, num_samples: int, timeout: float=5.0) -> Optional[np.ndarray]:
        chunks=[]
        collected=0
        deadline=time.time() + timeout
        while collected < num_samples and time.time() < deadline:
            chunk=self.read(timeout=0.1)
            if chunk is not None:
                chunks.append(chunk)
                collected += len(chunk)
        if not chunks:
            return None
        result=np.concatenate(chunks)
        return result[:num_samples]

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def total_samples_captured(self) -> int:
        return self._total_samples


class AudioPlayer:
    def __init__(self, config: AudioConfig):
        self.config=config
        self.sample_rate=config.sample_rate
        self.channels=config.channels
        self.dtype=np.float32
        self._stream: Optional[sd.OutputStream]=None
        self._running=False

    def start(self, device: Optional[int]=None) -> None:
        if self._running:
            return
        self._running=True
        self._stream=sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            device=device,
            blocksize=int(self.sample_rate * 0.05),
        )
        self._stream.start()
        log.info(f"Audio playback started: {self.sample_rate} Hz")

    def stop(self) -> None:
        self._running=False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream=None
        log.info("Audio playback stopped")

    def play(self, audio: np.ndarray) -> None:
        if self._stream is None:
            self.start()
        if audio.ndim == 1:
            audio=audio.reshape(-1, 1)
        self._stream.write(audio.astype(self.dtype))

    def play_blocking(self, audio: np.ndarray) -> None:
        if audio.ndim == 1:
            audio=audio.reshape(-1, 1)
        sd.play(audio.astype(self.dtype), samplerate=self.sample_rate)
        sd.wait()

    @property
    def is_running(self) -> bool:
        return self._running


def list_audio_devices() -> list:
    devices=sd.query_devices()
    result=[]
    for i, dev in enumerate(devices):
        result.append({
            'index': i,
            'name': dev['name'],
            'inputs': dev['max_input_channels'],
            'outputs': dev['max_output_channels'],
            'default_samplerate': dev['default_samplerate'],
        })
    return result


def print_audio_devices() -> None:
    print("\n=== Audio Devices ===")
    for dev in list_audio_devices():
        io=""
        if dev['inputs'] > 0:
            io += f"IN({dev['inputs']}) "
        if dev['outputs'] > 0:
            io += f"OUT({dev['outputs']}) "
        print(f"  [{dev['index']}] {dev['name']} {io}@{dev['default_samplerate']}Hz")
    print()
