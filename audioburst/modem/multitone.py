import numpy as np
from typing import List, Optional
from audioburst.config import AudioConfig
from audioburst.utils.logger import log


class MultiToneGenerator:
    def __init__(self, config: AudioConfig):
        self.config=config
        self.sample_rate=config.sample_rate
        self.base_freq=config.base_freq
        self.tone_spacing=config.tone_spacing
        self.num_tones=config.tones
        self.amplitude=config.amplitude
        self.bits_per_tone=config.bits_per_tone
        self.symbol_duration=config.symbol_duration
        self.samples_per_symbol=int(self.sample_rate * self.symbol_duration)
        self._frequencies=self._compute_frequencies()
        self._t=np.arange(self.samples_per_symbol) / self.sample_rate

    def _compute_frequencies(self) -> np.ndarray:
        return np.array([
            self.base_freq + i * self.tone_spacing
            for i in range(self.num_tones)
        ])

    def encode_symbol(self, data: bytes) -> np.ndarray:
        signal=np.zeros(self.samples_per_symbol, dtype=np.float32)
        bits=int.from_bytes(data[: (self.num_tones + 7) // 8], 'big')
        tone_amp=self.amplitude / max(1, self.num_tones)
        for i in range(self.num_tones):
            if bits & (1 << (self.num_tones - 1 - i)):
                freq=self._frequencies[i]
                signal += tone_amp * np.sin(
                    2.0 * np.pi * freq * self._t,
                    dtype=np.float32
                )
        return signal.astype(np.float32)

    def encode_stream(self, data_chunks: List[bytes]) -> np.ndarray:
        total_samples=len(data_chunks) * self.samples_per_symbol
        signal=np.zeros(total_samples, dtype=np.float32)
        for idx, chunk in enumerate(data_chunks):
            start=idx * self.samples_per_symbol
            end=start + self.samples_per_symbol
            signal[start:end]=self.encode_symbol(chunk)
        return signal

    def generate_preamble(self, length: int=64) -> np.ndarray:
        samples=int(self.sample_rate * 0.001 * length)
        t=np.arange(samples) / self.sample_rate
        signal=np.zeros(samples, dtype=np.float32)
        tone_amp=self.amplitude / max(1, self.num_tones)
        for freq in self._frequencies[::2]:
            signal += tone_amp * np.sin(2.0 * np.pi * freq * t, dtype=np.float32)
        return signal.astype(np.float32)

    def generate_sync(self) -> np.ndarray:
        samples=int(self.sample_rate * 0.02)
        t=np.arange(samples) / self.sample_rate
        signal=np.zeros(samples, dtype=np.float32)
        tone_amp=self.amplitude / max(1, self.num_tones)
        for i, freq in enumerate(self._frequencies):
            signal += tone_amp * np.sin(2.0 * np.pi * freq * t + i * 0.5, dtype=np.float32)
        return signal.astype(np.float32)

    def generate_silence(self, duration: float=0.05) -> np.ndarray:
        samples=int(self.sample_rate * duration)
        return np.zeros(samples, dtype=np.float32)

    @property
    def frequencies(self) -> np.ndarray:
        return self._frequencies
