import numpy as np
from typing import Optional, Tuple
from audioburst.config import AudioConfig
from audioburst.utils.logger import log


class SyncDetector:
    def __init__(self, config: AudioConfig):
        self.config=config
        self.sample_rate=config.sample_rate
        self.base_freq=config.base_freq
        self.tone_spacing=config.tone_spacing
        self.num_tones=config.tones
        self.symbol_duration=config.symbol_duration
        self.samples_per_symbol=int(self.sample_rate * self.symbol_duration)
        self._frequencies=self._compute_frequencies()
        self._fft_n=self.samples_per_symbol * 8

    def _compute_frequencies(self) -> np.ndarray:
        return np.array([
            self.base_freq + i * self.tone_spacing
            for i in range(self.num_tones)
        ])

    def _tone_energy_ratio(self, chunk: np.ndarray, freq_subset) -> float:
        windowed=chunk * np.hanning(len(chunk))
        fft=np.fft.rfft(windowed, n=self._fft_n)
        freqs=np.fft.rfftfreq(self._fft_n, 1.0 / self.sample_rate)
        magnitudes=np.abs(fft)
        tone_energy=0.0
        for freq in freq_subset:
            idx=np.argmin(np.abs(freqs - freq))
            start=max(0, idx - 4)
            end=min(len(magnitudes), idx + 5)
            tone_energy += np.max(magnitudes[start:end])
        total_energy=np.sum(magnitudes) + 1e-10
        return tone_energy / total_energy

    def detect_preamble(self, audio: np.ndarray, threshold: float=0.02) -> Optional[int]:
        if len(audio) < self.samples_per_symbol * 2:
            return None
        window_size=self.samples_per_symbol
        step=max(window_size // 8, 1)
        best_pos=None
        best_ratio=0.0
        for i in range(0, len(audio) - window_size, step):
            chunk=audio[i:i + window_size].astype(np.float64)
            ratio=self._tone_energy_ratio(chunk, self._frequencies[::2])
            if ratio > best_ratio:
                best_ratio=ratio
                best_pos=i
        if best_pos is not None and best_ratio > threshold:
            return best_pos
        return None

    def find_sync_marker(self, audio: np.ndarray, start_pos: int) -> Optional[int]:
        preamble_samples=int(self.sample_rate * 0.064)
        search_start=start_pos + preamble_samples
        if search_start >= len(audio):
            return None
        window_size=self.samples_per_symbol
        step=max(window_size // 8, 1)
        for i in range(search_start, len(audio) - window_size, step):
            chunk=audio[i:i + window_size].astype(np.float64)
            ratio=self._tone_energy_ratio(chunk, self._frequencies)
            if ratio > 0.03:
                return i
        return None

    def find_data_start(self, audio: np.ndarray) -> Optional[int]:
        preamble_pos=self.detect_preamble(audio)
        if preamble_pos is None:
            return None
        sync_pos=self.find_sync_marker(audio, preamble_pos)
        if sync_pos is None:
            return preamble_pos + self.samples_per_symbol * 3
        sync_samples=int(self.sample_rate * 0.02)
        return sync_pos + sync_samples

    def auto_sync(self, audio: np.ndarray) -> Optional[int]:
        return self.find_data_start(audio)
